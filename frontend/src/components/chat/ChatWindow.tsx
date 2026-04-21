import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Message, RoomMember } from "../../types";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

interface Props {
  type: "room" | "dialog" | "direct";
  id: string;
  title: string;
  subtitle?: string;
  otherUserId?: string; // for dialog type: the other participant's user_id
}

export default function ChatWindow({ type, id, title, subtitle, otherUserId }: Props) {
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const { currentUser, setActiveDialog, setDialogs, addMessage, updateMessage, setMyRooms, setActiveRoom, clearUnread } = useStore();
  const [canModerate, setCanModerate] = useState(false);
  const [isOwner, setIsOwner] = useState(false);

  useEffect(() => {
    if (type !== "room") return;
    api.get<RoomMember[]>(`/rooms/${id}/members`).then((members) => {
      const me = members.find((m) => m.user_id === currentUser?.id);
      setCanModerate(me?.role === "admin" || me?.role === "owner");
      setIsOwner(me?.role === "owner");
    }).catch(() => {});
  }, [id, type, currentUser?.id]);

  const handleLeave = async () => {
    if (!confirm("Leave this room?")) return;
    try {
      await api.post(`/rooms/${id}/leave`, {});
      const rooms = await api.get<any[]>("/rooms/mine");
      setMyRooms(rooms);
      setActiveRoom(null);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const fetchUrl = type === "room"
    ? `/rooms/${id}/messages`
    : type === "dialog"
    ? `/dialogs/${id}/messages`
    : null;

  const uploadFiles = async (messageId: string, files: File[]) => {
    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      form.append("message_id", messageId);
      await api.postForm(`/files/upload`, form);
    }
  };

  const handleSend = async (content: string, replyToId?: string, files?: File[]) => {
    try {
      if (type === "room") {
        const msg = await api.post<Message>(`/rooms/${id}/messages`, { content, reply_to_id: replyToId || null });
        addMessage(id, msg);
        clearUnread(id);
        if (files?.length) {
          await uploadFiles(msg.id, files);
          // reload message with attachments
          const refreshed = await api.get<Message[]>(`/rooms/${id}/messages?limit=1`);
          if (refreshed[0]?.id === msg.id) updateMessage(id, refreshed[0]);
        }
      } else if (type === "dialog") {
        const targetUserId = otherUserId || id;
        const msg = await api.post<Message>(`/dialogs/${targetUserId}/send`, { content, reply_to_id: replyToId || null });
        if (files?.length) {
          await uploadFiles(msg.id, files);
          const refreshed = await api.get<Message[]>(`/dialogs/${id}/messages?limit=1`);
          if (refreshed[0]?.id === msg.id) updateMessage(id, refreshed[0]);
          else addMessage(id, msg);
        } else {
          addMessage(id, msg);
        }
      } else {
        const msg = await api.post<Message>(`/dialogs/${id}/send`, { content, reply_to_id: replyToId || null });
        const dialogs = await api.get<{ id: string; other_user_id: string; other_username: string; unread_count: number }[]>("/dialogs");
        setDialogs(dialogs);
        const dialog = dialogs.find((d) => d.other_user_id === id);
        if (dialog) {
          if (files?.length) {
            await uploadFiles(msg.id, files);
            const refreshed = await api.get<Message[]>(`/dialogs/${dialog.id}/messages?limit=1`);
            addMessage(dialog.id, refreshed[0] ?? msg);
          } else {
            addMessage(dialog.id, msg);
          }
          setActiveDialog(dialog.id);
        }
      }
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="border-b px-4 py-3 bg-white flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-lg">{title}</h2>
          {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
        {type === "room" && !isOwner && (
          <button
            onClick={handleLeave}
            className="text-sm text-red-500 hover:text-red-700 px-3 py-1 rounded border border-red-200 hover:border-red-400"
          >
            Leave
          </button>
        )}
      </div>

      {fetchUrl ? (
        <MessageList
          chatKey={id}
          fetchUrl={fetchUrl}
          onReply={setReplyTo}
          canModerate={canModerate}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
          No messages yet. Say hello!
        </div>
      )}

      <MessageInput
        onSend={handleSend}
        replyTo={replyTo}
        onClearReply={() => setReplyTo(null)}
      />
    </div>
  );
}
