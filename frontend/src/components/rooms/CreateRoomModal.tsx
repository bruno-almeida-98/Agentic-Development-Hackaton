import { useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Room } from "../../types";
import Modal from "../common/Modal";

interface Props { onClose: () => void; }

export default function CreateRoomModal({ onClose }: Props) {
  const { upsertRoom, setActiveRoom } = useStore();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<"public" | "private">("public");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const room = await api.post<Room>("/rooms", { name, description, visibility });
      upsertRoom(room);
      setActiveRoom(room.id);
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Create Room" onClose={onClose} size="sm">
      <form onSubmit={submit} className="space-y-4">
        {error && <div className="bg-red-50 text-red-600 rounded p-2 text-sm">{error}</div>}
        <div>
          <label className="block text-sm font-medium mb-1">Room name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={3}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Visibility</label>
          <div className="flex gap-4">
            {(["public", "private"] as const).map((v) => (
              <label key={v} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  value={v}
                  checked={visibility === v}
                  onChange={() => setVisibility(v)}
                />
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </label>
            ))}
          </div>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white rounded py-2 font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Creating..." : "Create room"}
        </button>
      </form>
    </Modal>
  );
}
