import { useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Message } from "../../types";

interface Props {
  message: Message;
  onReply: (msg: Message) => void;
  canModerate?: boolean; // true if current user is admin/owner of this room
}

export default function MessageItem({ message, onReply, canModerate = false }: Props) {
  const { currentUser } = useStore();
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);

  const isOwn = message.sender_id === currentUser?.id;
  const canDelete = isOwn || canModerate;

  const handleEdit = async () => {
    try {
      await api.put(`/messages/${message.id}`, { content: editContent });
      setEditing(false);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this message?")) return;
    try {
      await api.delete(`/messages/${message.id}`);
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (message.is_deleted) {
    return (
      <div className="px-4 py-1 text-gray-400 italic text-sm">
        [Message deleted]
      </div>
    );
  }

  const time = new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className={`group px-4 py-1 hover:bg-gray-50 flex gap-3`}>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="font-medium text-sm text-blue-700">{message.sender_username || "Unknown"}</span>
          <span className="text-xs text-gray-400">{time}</span>
          {message.edited_at && <span className="text-xs text-gray-400 italic">(edited)</span>}
        </div>

        {message.reply_to_id && message.reply_to_preview && (
          <div className="border-l-2 border-blue-400 pl-2 mb-1 text-xs text-gray-500 truncate">
            ↩ {message.reply_to_preview}
          </div>
        )}

        {editing ? (
          <div className="mt-1">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full border rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              rows={3}
            />
            <div className="flex gap-2 mt-1">
              <button onClick={handleEdit} className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700">Save</button>
              <button onClick={() => setEditing(false)} className="text-xs bg-gray-200 px-2 py-1 rounded hover:bg-gray-300">Cancel</button>
            </div>
          </div>
        ) : (
          <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        )}

        {message.attachments.length > 0 && (
          <div className="mt-1 space-y-1">
            {message.attachments.map((att) => (
              <div key={att.id} className="flex items-center gap-2 bg-gray-100 rounded p-2 text-sm">
                {att.mime_type.startsWith("image/") ? (
                  <a href={`/api/files/${att.id}`} target="_blank" rel="noopener noreferrer">
                    <img
                      src={`/api/files/${att.id}`}
                      alt={att.original_name}
                      className="max-h-48 rounded cursor-pointer"
                    />
                  </a>
                ) : (
                  <a
                    href={`/api/files/${att.id}`}
                    download={att.original_name}
                    className="flex items-center gap-2 hover:underline text-blue-600"
                  >
                    <span>📎</span>
                    <span>{att.original_name}</span>
                    <span className="text-gray-400">({Math.round(att.size / 1024)}KB)</span>
                  </a>
                )}
                {att.comment && <span className="text-gray-500 text-xs">— {att.comment}</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="opacity-0 group-hover:opacity-100 flex gap-1 text-xs">
        <button onClick={() => onReply(message)} className="text-gray-400 hover:text-blue-600 px-1" title="Reply">↩</button>
        {isOwn && (
          <button onClick={() => setEditing(true)} className="text-gray-400 hover:text-yellow-600 px-1" title="Edit">✏️</button>
        )}
        {canDelete && (
          <button onClick={handleDelete} className="text-gray-400 hover:text-red-600 px-1" title="Delete">🗑️</button>
        )}
      </div>
    </div>
  );
}
