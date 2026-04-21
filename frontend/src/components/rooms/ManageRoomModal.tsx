import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Room, RoomBan, RoomMember } from "../../types";
import Modal from "../common/Modal";
import PresenceDot from "../common/PresenceDot";

interface Props {
  room: Room;
  onClose: () => void;
  onDeleted: () => void;
}

type Tab = "members" | "admins" | "banned" | "invitations" | "settings";

export default function ManageRoomModal({ room, onClose, onDeleted }: Props) {
  const { currentUser, removeRoom, presence } = useStore();
  const [tab, setTab] = useState<Tab>("members");
  const [members, setMembers] = useState<RoomMember[]>([]);
  const [bans, setBans] = useState<RoomBan[]>([]);
  const [invitations, setInvitations] = useState<any[]>([]);
  const [memberSearch, setMemberSearch] = useState("");
  const [inviteUsername, setInviteUsername] = useState("");
  const [roomName, setRoomName] = useState(room.name);
  const [roomDesc, setRoomDesc] = useState(room.description);
  const [roomVis, setRoomVis] = useState(room.visibility);
  const [error, setError] = useState("");

  const loadMembers = () => api.get<RoomMember[]>(`/rooms/${room.id}/members`).then(setMembers).catch(() => {});
  const loadBans = () => api.get<RoomBan[]>(`/rooms/${room.id}/bans`).then(setBans).catch(() => {});
  const loadInvitations = () => api.get<any[]>(`/rooms/${room.id}/invitations`).then(setInvitations).catch(() => {});

  useEffect(() => {
    loadMembers();
    loadBans();
    loadInvitations();
  }, [room.id]);

  const myRole = members.find((m) => m.user_id === currentUser?.id)?.role;
  const isOwner = myRole === "owner";

  const filtered = members.filter((m) => m.username.toLowerCase().includes(memberSearch.toLowerCase()));

  const promoteAdmin = async (userId: string) => {
    await api.post(`/rooms/${room.id}/members/${userId}/admin`);
    loadMembers();
  };
  const demoteAdmin = async (userId: string) => {
    await api.delete(`/rooms/${room.id}/members/${userId}/admin`);
    loadMembers();
  };
  const removeMember = async (userId: string) => {
    if (!confirm("Remove and ban this user?")) return;
    await api.delete(`/rooms/${room.id}/members/${userId}`);
    loadMembers();
    loadBans();
  };
  const unban = async (userId: string) => {
    await api.delete(`/rooms/${room.id}/bans/${userId}`);
    loadBans();
  };
  const invite = async () => {
    if (!inviteUsername.trim()) return;
    try {
      await api.post(`/rooms/${room.id}/invite`, { username: inviteUsername.trim() });
      setInviteUsername("");
      loadInvitations();
    } catch (err: any) {
      setError(err.message);
    }
  };
  const saveSettings = async () => {
    try {
      await api.put(`/rooms/${room.id}`, { name: roomName, description: roomDesc, visibility: roomVis });
    } catch (err: any) {
      setError(err.message);
    }
  };
  const deleteRoom = async () => {
    if (!confirm(`Delete room "${room.name}"? This cannot be undone.`)) return;
    await api.delete(`/rooms/${room.id}`);
    removeRoom(room.id);
    onDeleted();
    onClose();
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "members", label: "Members" },
    { key: "admins", label: "Admins" },
    { key: "banned", label: "Banned" },
    { key: "invitations", label: "Invitations" },
    { key: "settings", label: "Settings" },
  ];

  return (
    <Modal title={`Manage Room: #${room.name}`} onClose={onClose} size="lg">
      {error && <div className="bg-red-50 text-red-600 rounded p-2 text-sm mb-3">{error}</div>}
      <div className="flex gap-1 mb-4 flex-wrap">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-1.5 rounded text-sm ${tab === t.key ? "bg-blue-600 text-white" : "bg-gray-100 hover:bg-gray-200"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "members" && (
        <div className="space-y-3">
          <input
            value={memberSearch}
            onChange={(e) => setMemberSearch(e.target.value)}
            placeholder="Search member..."
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <div className="overflow-y-auto max-h-80 space-y-1">
            {filtered.map((m) => (
              <div key={m.user_id} className="flex items-center gap-3 p-2 rounded hover:bg-gray-50 text-sm">
                <PresenceDot status={presence[m.user_id] || m.presence} />
                <span className="flex-1 font-medium">{m.username}</span>
                <span className="text-gray-400 capitalize">{m.role}</span>
                {m.user_id !== currentUser?.id && m.role !== "owner" && (
                  <div className="flex gap-1">
                    {m.role === "member" && (
                      <button onClick={() => promoteAdmin(m.user_id)} className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded hover:bg-blue-100">
                        Make admin
                      </button>
                    )}
                    {m.role === "admin" && isOwner && (
                      <button onClick={() => demoteAdmin(m.user_id)} className="text-xs bg-gray-100 px-2 py-1 rounded hover:bg-gray-200">
                        Remove admin
                      </button>
                    )}
                    <button onClick={() => removeMember(m.user_id)} className="text-xs bg-red-50 text-red-600 px-2 py-1 rounded hover:bg-red-100">
                      Ban
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "admins" && (
        <div className="space-y-2 text-sm">
          {members.filter((m) => m.role !== "member").map((m) => (
            <div key={m.user_id} className="flex items-center gap-3 p-2 rounded bg-gray-50">
              <span className="flex-1 font-medium">{m.username}</span>
              <span className="text-gray-400 capitalize">{m.role}</span>
              {m.role === "admin" && isOwner && (
                <button onClick={() => demoteAdmin(m.user_id)} className="text-xs bg-gray-200 px-2 py-1 rounded hover:bg-gray-300">
                  Remove admin
                </button>
              )}
              {m.role === "owner" && <span className="text-xs text-gray-400">(cannot lose admin)</span>}
            </div>
          ))}
        </div>
      )}

      {tab === "banned" && (
        <div className="space-y-2 text-sm">
          {bans.length === 0 && <div className="text-gray-400">No banned users</div>}
          {bans.map((ban) => (
            <div key={ban.user_id} className="flex items-center gap-3 p-2 rounded bg-gray-50">
              <span className="flex-1 font-medium">{ban.username}</span>
              <span className="text-gray-400 text-xs">banned by {ban.banned_by_username}</span>
              <button onClick={() => unban(ban.user_id)} className="text-xs bg-green-50 text-green-600 px-2 py-1 rounded hover:bg-green-100">
                Unban
              </button>
            </div>
          ))}
        </div>
      )}

      {tab === "invitations" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              value={inviteUsername}
              onChange={(e) => setInviteUsername(e.target.value)}
              placeholder="Username to invite"
              className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button onClick={invite} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
              Send invite
            </button>
          </div>
          <div className="space-y-1 text-sm">
            {invitations.map((inv: any) => (
              <div key={inv.user_id} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                <span>{inv.username}</span>
                <span className="text-gray-400 text-xs">invited</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "settings" && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Room name</label>
            <input value={roomName} onChange={(e) => setRoomName(e.target.value)} className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea value={roomDesc} onChange={(e) => setRoomDesc(e.target.value)} className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" rows={3} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Visibility</label>
            <div className="flex gap-4">
              {(["public", "private"] as const).map((v) => (
                <label key={v} className="flex items-center gap-2 text-sm">
                  <input type="radio" value={v} checked={roomVis === v} onChange={() => setRoomVis(v)} />
                  {v.charAt(0).toUpperCase() + v.slice(1)}
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-between pt-2">
            <button onClick={saveSettings} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
              Save changes
            </button>
            {isOwner && (
              <button onClick={deleteRoom} className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700">
                Delete room
              </button>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
