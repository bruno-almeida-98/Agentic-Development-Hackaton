import { useCallback, useEffect, useRef } from "react";
import { useStore } from "../store";
import type { WSEvent } from "../types";

// Module-level singleton so only one WS exists across renders
let ws: WebSocket | null = null;
let heartbeatInterval: ReturnType<typeof setInterval> | null = null;
let lastActivity = Date.now();
let pendingSubscriptions: string[] = [];
let isConnecting = false;

const AFK_MS = 60_000;

const trackActivity = () => {
  const wasInactive = Date.now() - lastActivity >= AFK_MS;
  lastActivity = Date.now();
  if (wasInactive && ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "heartbeat", active: true }));
  }
};

function connect(handleEventRef: React.MutableRefObject<(event: WSEvent) => void>) {
  if (ws || isConnecting) return;
  isConnecting = true;

  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${window.location.host}/ws`);

  ws.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data) as WSEvent;
      handleEventRef.current(event);
    } catch { /* ignore */ }
  };

  ws.onopen = () => {
    isConnecting = false;
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    heartbeatInterval = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        const active = Date.now() - lastActivity < AFK_MS;
        ws.send(JSON.stringify({ type: "heartbeat", active }));
      }
    }, 30_000);
    while (pendingSubscriptions.length > 0) {
      const roomId = pendingSubscriptions.shift()!;
      ws!.send(JSON.stringify({ type: "subscribe.room", room_id: roomId }));
    }
  };

  ws.onclose = () => {
    isConnecting = false;
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    heartbeatInterval = null;
    ws = null;
    setTimeout(() => connect(handleEventRef), 3_000);
  };
}

export function useWebSocket() {
  const handleEventRef = useRef<(event: WSEvent) => void>(() => {});

  handleEventRef.current = (event: WSEvent) => {
    const store = useStore.getState();
    switch (event.type) {
      case "message.new": {
        const msg = event.message;
        const key = msg.room_id || msg.dialog_id || "";
        const isActive = store.activeRoomId === msg.room_id || store.activeDialogId === msg.dialog_id;
        store.addMessage(key, msg);
        if (!isActive && msg.sender_id !== store.currentUser?.id) {
          store.setUnread(key, (store.unread[key] || 0) + 1);
        }
        break;
      }
      case "message.edited": {
        const msg = event.message;
        const key = msg.room_id || msg.dialog_id || "";
        store.updateMessage(key, msg);
        break;
      }
      case "message.deleted": {
        const key = event.room_id || event.dialog_id || "";
        if (key) store.deleteMessage(key, event.message_id);
        break;
      }
      case "presence.update":
        store.setPresence(event.user_id, event.status);
        break;
      case "friend.request":
        store.setPendingRequests([...store.pendingRequests, event.friendship]);
        break;
      case "friend.accepted":
        fetch("/api/friends", { credentials: "include" })
          .then((r) => r.json())
          .then((friends) => store.setFriends(friends))
          .catch(() => {});
        break;
      case "room.invitation":
        store.addRoomInvitation({
          invitation_id: event.invitation_id,
          room_id: event.room_id,
          room_name: event.room_name,
        });
        break;
    }
  };

  useEffect(() => {
    connect(handleEventRef);

    window.addEventListener("mousemove", trackActivity);
    window.addEventListener("keydown", trackActivity);
    window.addEventListener("click", trackActivity);

    return () => {
      window.removeEventListener("mousemove", trackActivity);
      window.removeEventListener("keydown", trackActivity);
      window.removeEventListener("click", trackActivity);
    };
  }, []);

  const subscribeRoom = useCallback((roomId: string) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "subscribe.room", room_id: roomId }));
    } else {
      if (!pendingSubscriptions.includes(roomId)) {
        pendingSubscriptions.push(roomId);
      }
    }
  }, []);

  return { subscribeRoom };
}
