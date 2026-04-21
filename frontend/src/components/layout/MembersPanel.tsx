import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Room, RoomMember } from "../../types";
import PresenceDot from "../common/PresenceDot";

interface Props {
  room: Room;
  onManage: () => void;
  onInvite: () => void;
}

export default function MembersPanel({ room, onManage, onInvite }: Props) {
  const { currentUser, presence, friends, setFriends } = useStore();
  const [members, setMembers] = useState<RoomMember[]>([]);
  const [sentRequests, setSentRequests] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.get<RoomMember[]>(`/rooms/${room.id}/members`).then(setMembers).catch(() => {});
  }, [room.id]);

  const isAdmin = members.find((m) => m.user_id === currentUser?.id)?.role;
  const canManage = isAdmin === "owner" || isAdmin === "admin";
  const friendIds = new Set(friends.map((f) => f.user_id));

  const sendFriendRequest = async (username: string, userId: string) => {
    try {
      await api.post("/friends/requests", { username });
      setSentRequests((s) => new Set(s).add(userId));
    } catch {
      // ignore (already sent, etc.)
      setSentRequests((s) => new Set(s).add(userId));
    }
  };

  return (
    <div className="w-48 border-l bg-white flex flex-col h-full">
      <div className="p-3 border-b">
        <h3 className="font-semibold text-sm text-gray-700">#{room.name}</h3>
        <p className="text-xs text-gray-500">{room.visibility}</p>
      </div>

      <div className="p-3 border-b text-xs text-gray-600">
        <div><strong>Owner:</strong> {members.find((m) => m.role === "owner")?.username}</div>
        {members.filter((m) => m.role === "admin").length > 0 && (
          <div className="mt-1">
            <strong>Admins:</strong>{" "}
            {members.filter((m) => m.role === "admin").map((m) => m.username).join(", ")}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Members ({members.length})
        </div>
        {members.map((m) => {
          const isMe = m.user_id === currentUser?.id;
          const isFriend = friendIds.has(m.user_id);
          const requested = sentRequests.has(m.user_id);
          return (
            <div key={m.user_id} className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 group">
              <PresenceDot status={presence[m.user_id] || m.presence} />
              <span className="text-sm flex-1 truncate">{m.username}</span>
              {m.role !== "member" && (
                <span className="text-xs text-blue-500">{m.role}</span>
              )}
              {!isMe && !isFriend && (
                <button
                  onClick={() => sendFriendRequest(m.username, m.user_id)}
                  disabled={requested}
                  title={requested ? "Request sent" : "Add friend"}
                  className="text-xs text-green-600 hover:text-green-800 disabled:text-gray-400"
                >
                  {requested ? "✓" : "+"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      <div className="p-3 border-t space-y-2">
        {canManage && (
          <button
            onClick={onManage}
            className="w-full text-xs bg-gray-100 hover:bg-gray-200 rounded px-2 py-1.5"
          >
            Manage room
          </button>
        )}
        <button
          onClick={onInvite}
          className="w-full text-xs bg-blue-50 hover:bg-blue-100 text-blue-600 rounded px-2 py-1.5"
        >
          Invite user
        </button>
      </div>
    </div>
  );
}
