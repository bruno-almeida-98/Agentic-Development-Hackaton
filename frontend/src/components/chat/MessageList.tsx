import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Message } from "../../types";
import MessageItem from "./MessageItem";

interface Props {
  chatKey: string;
  fetchUrl: string;
  onReply: (msg: Message) => void;
  canModerate?: boolean;
}

export default function MessageList({ chatKey, fetchUrl, onReply, canModerate = false }: Props) {
  const { messages, setMessages, prependMessages, clearUnread } = useStore();
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [atBottom, setAtBottom] = useState(true);

  const msgs = messages[chatKey] || [];

  const loadMessages = useCallback(async (before?: string) => {
    if (loading) return;
    setLoading(true);
    try {
      const url = before ? `${fetchUrl}?before=${before}&limit=50` : `${fetchUrl}?limit=50`;
      const data = await api.get<Message[]>(url);
      if (!before) {
        setMessages(chatKey, data);
      } else {
        prependMessages(chatKey, data);
      }
      setHasMore(data.length === 50);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [chatKey, fetchUrl, loading]);

  useEffect(() => {
    setMessages(chatKey, []);
    setHasMore(true);
    loadMessages();
    clearUnread(chatKey);
  }, [chatKey]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (atBottom && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [msgs.length, atBottom]);

  const handleScroll = () => {
    const el = listRef.current;
    if (!el) return;
    const bottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
    setAtBottom(bottom);

    // Load more when near top
    if (el.scrollTop < 100 && hasMore && !loading && msgs.length > 0) {
      loadMessages(msgs[0]?.id);
    }
  };

  return (
    <div
      ref={listRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto scrollbar-thin py-2"
    >
      {loading && msgs.length === 0 && (
        <div className="flex justify-center py-8 text-gray-400">Loading...</div>
      )}
      {hasMore && msgs.length > 0 && (
        <div className="flex justify-center py-2">
          <button
            onClick={() => loadMessages(msgs[0]?.id)}
            disabled={loading}
            className="text-sm text-blue-600 hover:underline disabled:opacity-50"
          >
            {loading ? "Loading..." : "Load older messages"}
          </button>
        </div>
      )}
      {msgs.length === 0 && !loading && (
        <div className="flex justify-center py-8 text-gray-400 text-sm">
          No messages yet. Say hello!
        </div>
      )}
      {msgs.map((msg) => (
        <MessageItem key={msg.id} message={msg} onReply={onReply} canModerate={canModerate} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
