"""WebSocket connection manager with Redis pub/sub fan-out."""
import asyncio
import contextlib
import json
import logging
import uuid
from collections import defaultdict

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.presence import get_redis, tab_connect, tab_disconnect, tab_heartbeat

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # user_id -> set of WebSocket connections
        self._user_connections: dict[str, set[WebSocket]] = defaultdict(set)
        # websocket -> (user_id, tab_id)
        self._ws_meta: dict[WebSocket, tuple[str, str]] = {}
        # room_id -> set of user_ids currently in the room
        self._room_users: dict[str, set[str]] = defaultdict(set)
        self._pubsub_task: asyncio.Task | None = None

    async def startup(self):
        self._pubsub_task = asyncio.create_task(self._listen_pubsub())

    async def shutdown(self):
        if self._pubsub_task:
            self._pubsub_task.cancel()

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        await websocket.accept()
        tab_id = str(uuid.uuid4())
        self._user_connections[user_id].add(websocket)
        self._ws_meta[websocket] = (user_id, tab_id)
        await tab_connect(user_id, tab_id)
        logger.info("WS connect: user=%s tab=%s total_users=%d", user_id, tab_id, len(self._user_connections))
        return tab_id

    async def disconnect(self, websocket: WebSocket):
        meta = self._ws_meta.pop(websocket, None)
        if meta:
            user_id, tab_id = meta
            self._user_connections[user_id].discard(websocket)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
                # Remove user from all rooms
                for room_id in list(self._room_users.keys()):
                    self._room_users[room_id].discard(user_id)
            await tab_disconnect(user_id, tab_id)

    async def subscribe_room(self, websocket: WebSocket, room_id: str):
        meta = self._ws_meta.get(websocket)
        if meta:
            user_id, _ = meta
            self._room_users[room_id].add(user_id)

    async def handle_message(self, websocket: WebSocket, data: dict):
        meta = self._ws_meta.get(websocket)
        if not meta:
            return
        user_id, tab_id = meta

        msg_type = data.get("type")

        if msg_type == "heartbeat":
            active = data.get("active", True)
            status = await tab_heartbeat(user_id, tab_id, active)
            await self.send_to_user(user_id, {"type": "presence.self", "status": status})

        elif msg_type == "subscribe.room":
            room_id = data.get("room_id")
            if room_id:
                await self.subscribe_room(websocket, room_id)

        elif msg_type == "unsubscribe.room":
            room_id = data.get("room_id")
            if room_id:
                self._room_users[room_id].discard(user_id)

    async def send_to_user(self, user_id: str, payload: dict):
        conns = list(self._user_connections.get(user_id, []))
        text = json.dumps(payload)
        sent = False
        for ws in conns:
            try:
                await ws.send_text(text)
                sent = True
            except Exception as e:
                logger.warning("send_to_user ws.send_text failed: user=%s err=%s", user_id, e)
        if not sent:
            # No local connections or all failed — publish to Redis for other instances
            r = get_redis()
            await r.publish(f"ws:user:{user_id}", text)

    async def broadcast_room(self, room_id: str, payload: dict):
        text = json.dumps(payload)
        # Send to locally connected users in this room
        for user_id in list(self._room_users.get(room_id, [])):
            for ws in list(self._user_connections.get(user_id, [])):
                with contextlib.suppress(Exception):
                    await ws.send_text(text)
        # Also publish to Redis for other server instances
        r = get_redis()
        await r.publish(f"ws:room:{room_id}", text)

    async def broadcast_dialog(self, dialog_id: str, payload: dict, db: AsyncSession):
        from app.models import Dialog

        result = await db.execute(select(Dialog).where(Dialog.id == dialog_id))
        dialog = result.scalar_one_or_none()
        if dialog:
            await self.send_to_user(dialog.user1_id, payload)
            await self.send_to_user(dialog.user2_id, payload)

    async def broadcast_presence(self, user_id: str, status: str):
        payload = json.dumps({"type": "presence.update", "user_id": user_id, "status": status})
        # Broadcast to all connected users (they filter relevant ones client-side)
        for _uid, conns in list(self._user_connections.items()):
            for ws in list(conns):
                with contextlib.suppress(Exception):
                    await ws.send_text(payload)

    async def _listen_pubsub(self):
        r = get_redis()
        pubsub = r.pubsub()
        # Use psubscribe for wildcards and subscribe for exact channels
        await pubsub.psubscribe("ws:room:*", "ws:user:*")
        await pubsub.subscribe("presence_updates")

        async for message in pubsub.listen():
            if message["type"] not in ("message", "pmessage"):
                continue
            try:
                channel = message.get("channel", "") or ""
                data = json.loads(message["data"])

                if channel == "presence_updates":
                    user_id = data.get("user_id")
                    status = data.get("status")
                    if user_id and status:
                        await self.broadcast_presence(user_id, status)

                elif channel.startswith("ws:user:"):
                    user_id = channel.split("ws:user:")[1]
                    conns = list(self._user_connections.get(user_id, []))
                    text = json.dumps(data)
                    for ws in conns:
                        with contextlib.suppress(Exception):
                            await ws.send_text(text)

                elif channel.startswith("ws:room:"):
                    room_id = channel.split("ws:room:")[1]
                    text = json.dumps(data)
                    for user_id in list(self._room_users.get(room_id, [])):
                        for ws in list(self._user_connections.get(user_id, [])):
                            with contextlib.suppress(Exception):
                                await ws.send_text(text)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("pubsub error: %s", e)


manager = ConnectionManager()
