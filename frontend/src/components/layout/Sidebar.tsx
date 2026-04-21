import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Dialog, Room } from "../../types";
import PresenceDot from "../common/PresenceDot";

interface Props {
  onCreateRoom: () => void;
}

export default function Sidebar({ onCreateRoom }: Props) {
  const {
    myRooms, setMyRooms, setActiveRoom, setActiveDialog, setActiveDirect,
    activeRoomId, activeDialogId, activeDirectUserId,
    unread, friends, dialogs, setDialogs, presence,
    roomInvitations, setRoomInvitations, removeRoomInvitation,
  } = useStore();
  const [search, setSearch] = useState("");
  const [roomsOpen, setRoomsOpen] = useState(true);
  const [privateOpen, setPrivateOpen] = useState(true);
  const [contactsOpen, setContactsOpen] = useState(true);

  useEffect(() => {
    api.get<Room[]>("/rooms/mine").then(setMyRooms).catch(() => {});
    api.get<Dialog[]>("/dialogs").then(setDialogs).catch(() => {});
    api.get<{ invitation_id: string; room_id: string; room_name: string }[]>("/rooms/invitations/mine")
      .then(setRoomInvitations).catch(() => {});
  }, []);

  const acceptInvitation = async (inv: { invitation_id: string; room_id: string; room_name: string }) => {
    try {
      await api.post(`/rooms/${inv.room_id}/invitations/accept`, {});
      removeRoomInvitation(inv.invitation_id);
      const rooms = await api.get<Room[]>("/rooms/mine");
      setMyRooms(rooms);
    } catch {
      // ignore
    }
  };

  const publicRooms = myRooms.filter((r) => r.visibility === "public");
  const privateRooms = myRooms.filter((r) => r.visibility === "private");

  const filteredPublic = publicRooms.filter((r) => r.name.toLowerCase().includes(search.toLowerCase()));
  const filteredPrivate = privateRooms.filter((r) => r.name.toLowerCase().includes(search.toLowerCase()));
  const filteredFriends = friends.filter((f) => f.username.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="w-56 bg-sidebar text-white flex flex-col h-full">
      <div className="p-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search..."
          className="w-full bg-sidebar-hover rounded px-2 py-1.5 text-sm placeholder-gray-400 focus:outline-none"
        />
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {/* Pending roomInvitations */}
        {roomInvitations.length > 0 && (
          <div className="px-3 py-2 border-b border-slate-700">
            <div className="text-xs font-semibold text-yellow-400 uppercase tracking-wider mb-1">
              Invitations ({roomInvitations.length})
            </div>
            {roomInvitations.map((inv) => (
              <div key={inv.invitation_id} className="flex items-center justify-between py-1">
                <span className="text-xs text-gray-300 truncate flex-1">🔒 {inv.room_name}</span>
                <button
                  onClick={() => acceptInvitation(inv)}
                  className="text-xs bg-green-600 hover:bg-green-500 text-white px-2 py-0.5 rounded ml-1"
                >
                  Accept
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Public Rooms */}
        <div>
          <button
            onClick={() => setRoomsOpen(!roomsOpen)}
            className="w-full text-left px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-200 flex items-center justify-between"
          >
            Public Rooms
            <span>{roomsOpen ? "▾" : "▸"}</span>
          </button>
          {roomsOpen && filteredPublic.map((room) => (
            <button
              key={room.id}
              onClick={() => setActiveRoom(room.id)}
              className={`w-full text-left px-4 py-1.5 text-sm flex items-center justify-between hover:bg-sidebar-hover ${activeRoomId === room.id ? "bg-sidebar-hover text-white" : "text-gray-300"}`}
            >
              <span className="truncate">#{room.name}</span>
              {(unread[room.id] || 0) > 0 && (
                <span className="bg-red-500 text-white text-xs rounded-full px-1.5 min-w-[18px] text-center">
                  {unread[room.id]}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Private Rooms */}
        {(filteredPrivate.length > 0 || privateRooms.length > 0) && (
          <div>
            <button
              onClick={() => setPrivateOpen(!privateOpen)}
              className="w-full text-left px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-200 flex items-center justify-between"
            >
              Private Rooms
              <span>{privateOpen ? "▾" : "▸"}</span>
            </button>
            {privateOpen && filteredPrivate.map((room) => (
              <button
                key={room.id}
                onClick={() => setActiveRoom(room.id)}
                className={`w-full text-left px-4 py-1.5 text-sm flex items-center justify-between hover:bg-sidebar-hover ${activeRoomId === room.id ? "bg-sidebar-hover text-white" : "text-gray-300"}`}
              >
                <span className="truncate">🔒 {room.name}</span>
                {(unread[room.id] || 0) > 0 && (
                  <span className="bg-red-500 text-white text-xs rounded-full px-1.5 min-w-[18px] text-center">
                    {unread[room.id]}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Contacts */}
        <div>
          <button
            onClick={() => setContactsOpen(!contactsOpen)}
            className="w-full text-left px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-200 flex items-center justify-between mt-2"
          >
            Contacts
            <span>{contactsOpen ? "▾" : "▸"}</span>
          </button>
          {contactsOpen && filteredFriends.map((friend) => {
            const dialog = dialogs.find((d) => d.other_user_id === friend.user_id);
            const isActive = activeDialogId === dialog?.id || activeDirectUserId === friend.user_id;
            return (
              <button
                key={friend.user_id}
                onClick={() => dialog ? setActiveDialog(dialog.id) : setActiveDirect(friend.user_id, friend.username)}
                className={`w-full text-left px-4 py-1.5 text-sm flex items-center gap-2 hover:bg-sidebar-hover ${isActive ? "bg-sidebar-hover text-white" : "text-gray-300"}`}
              >
                <PresenceDot status={presence[friend.user_id] || friend.presence} />
                <span className="truncate flex-1">{friend.username}</span>
                {dialog && (unread[dialog.id] || 0) > 0 && (
                  <span className="bg-red-500 text-white text-xs rounded-full px-1.5 min-w-[18px] text-center">
                    {unread[dialog.id]}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="p-3 border-t border-slate-700">
        <button
          onClick={onCreateRoom}
          className="w-full text-sm text-gray-300 hover:text-white flex items-center gap-2"
        >
          <span>+</span> Create room
        </button>
      </div>
    </div>
  );
}
