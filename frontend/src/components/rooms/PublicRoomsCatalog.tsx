import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Room } from "../../types";
import Modal from "../common/Modal";

interface Props { onClose: () => void; }

export default function PublicRoomsCatalog({ onClose }: Props) {
  const { upsertRoom, setActiveRoom } = useStore();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const fetch = async (q?: string) => {
    setLoading(true);
    try {
      const data = await api.get<Room[]>(`/rooms${q ? `?search=${encodeURIComponent(q)}` : ""}`);
      setRooms(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch(); }, []);

  const join = async (room: Room) => {
    try {
      await api.post(`/rooms/${room.id}/join`);
      upsertRoom(room);
      setActiveRoom(room.id);
      onClose();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <Modal title="Public Rooms" onClose={onClose} size="lg">
      <div className="space-y-4">
        <div className="flex gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetch(search)}
            placeholder="Search rooms..."
            className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button onClick={() => fetch(search)} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Search
          </button>
        </div>

        {loading && <div className="text-center text-gray-400 py-4">Loading...</div>}
        <div className="space-y-2">
          {rooms.map((room) => (
            <div key={room.id} className="border rounded-lg p-3 flex items-start justify-between hover:bg-gray-50">
              <div className="flex-1 min-w-0">
                <div className="font-medium">#{room.name}</div>
                <div className="text-sm text-gray-500">{room.description || "No description"}</div>
                <div className="text-xs text-gray-400 mt-1">{room.member_count} members</div>
              </div>
              <button
                onClick={() => join(room)}
                className="ml-3 bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 flex-shrink-0"
              >
                Join
              </button>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
}
