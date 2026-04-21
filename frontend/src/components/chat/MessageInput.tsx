import { useRef, useState } from "react";
import { api } from "../../api/client";
import type { Message } from "../../types";

interface Props {
  onSend: (content: string, replyToId?: string, files?: File[]) => Promise<void>;
  replyTo: Message | null;
  onClearReply: () => void;
}

export default function MessageInput({ onSend, replyTo, onClearReply }: Props) {
  const [content, setContent] = useState("");
  const [sending, setSending] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async () => {
    const text = content.trim();
    if (!text && pendingFiles.length === 0) return;
    setSending(true);
    try {
      await onSend(text || " ", replyTo?.id, pendingFiles.length > 0 ? pendingFiles : undefined);
      setContent("");
      onClearReply();
      setPendingFiles([]);
    } catch {
      // handled by parent
    } finally {
      setSending(false);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].kind === "file") {
        const file = items[i].getAsFile();
        if (file) setPendingFiles((f) => [...f, file]);
      }
    }
  };

  return (
    <div className="border-t bg-white px-4 py-3">
      {replyTo && (
        <div className="flex items-center gap-2 mb-2 bg-blue-50 rounded px-3 py-1.5 text-sm">
          <span className="text-blue-600">↩ Replying to {replyTo.sender_username}:</span>
          <span className="text-gray-600 truncate flex-1">{replyTo.content}</span>
          <button onClick={onClearReply} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
      )}

      {pendingFiles.length > 0 && (
        <div className="flex gap-2 mb-2 flex-wrap">
          {pendingFiles.map((f, i) => (
            <div key={i} className="flex items-center gap-1 bg-gray-100 rounded px-2 py-1 text-xs">
              <span>📎 {f.name}</span>
              <button onClick={() => setPendingFiles((files) => files.filter((_, j) => j !== i))}>✕</button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2">
        <div className="flex gap-1">
          <button
            onClick={() => fileRef.current?.click()}
            className="text-gray-400 hover:text-blue-600 p-1.5 rounded"
            title="Attach file"
          >
            📎
          </button>
          <input
            ref={fileRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) setPendingFiles((f) => [...f, ...Array.from(e.target.files!)]);
              e.target.value = "";
            }}
          />
        </div>

        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder="Type a message... (Shift+Enter for newline)"
          className="flex-1 border rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm max-h-32"
          rows={1}
          style={{ minHeight: "40px" }}
        />

        <button
          onClick={handleSend}
          disabled={sending}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 font-medium hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          Send
        </button>
      </div>
    </div>
  );
}
