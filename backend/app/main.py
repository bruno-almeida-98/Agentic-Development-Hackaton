import json
import logging
import os

logging.basicConfig(level=logging.INFO)

from fastapi import Cookie, FastAPI, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.models import Session, User
from app.routers import auth, files, friends, messages, rooms, users
from app.ws_manager import manager

app = FastAPI(title="ChatApp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(messages.router)
app.include_router(friends.router)
app.include_router(files.router)
app.include_router(users.router)


@app.on_event("startup")
async def startup():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await init_db()
    await manager.startup()


@app.on_event("shutdown")
async def shutdown():
    await manager.shutdown()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_session: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE),
):
    # Authenticate via cookie
    user = None
    if chat_session:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Session).where(Session.token == chat_session))
            session = result.scalar_one_or_none()
            if session:
                r2 = await db.execute(select(User).where(User.id == session.user_id))
                user = r2.scalar_one_or_none()

    if not user:
        logger.warning("WS auth failed: no valid session cookie")
        await websocket.close(code=4001)
        return

    logger.info("WS connected: user=%s", user.username)
    await manager.connect(websocket, user.id)
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            logger.debug("WS msg: user=%s type=%s", user.username, data.get("type"))
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        logger.info("WS disconnected: user=%s", user.username)
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error("WS error for user=%s: %s", user.username, e)
        await manager.disconnect(websocket)
