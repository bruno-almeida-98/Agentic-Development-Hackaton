import { useEffect, useState } from "react";
import { api } from "../api/client";
import SessionsModal from "../components/admin/SessionsModal";
import ProfileModal from "../components/admin/ProfileModal";
import ChatWindow from "../components/chat/ChatWindow";
import ContactsModal from "../components/friends/ContactsModal";
import PresenceDot from "../components/common/PresenceDot";
import TopMenu from "../components/layout/TopMenu";
import Sidebar from "../components/layout/Sidebar";
import MembersPanel from "../components/layout/MembersPanel";
import CreateRoomModal from "../components/rooms/CreateRoomModal";
import ManageRoomModal from "../components/rooms/ManageRoomModal";
import PublicRoomsCatalog from "../components/rooms/PublicRoomsCatalog";
import { useWebSocket } from "../hooks/useWebSocket";
import { useStore } from "../store";
import type { Dialog, Friend, Friendship, Room, UnreadCount } from "../types";

type Modal = "publicRooms" | "createRoom" | "manageRoom" | "contacts" | "sessions" | "profile" | "invite" | null;

export default function ChatLayout() {
  const {
    activeRoomId,
    activeDialogId,
    activeDirectUserId,
    activeDirectUsername,
    myRooms,
    setMyRooms,
    setFriends,
    setPendingRequests,
    setDialogs,
    setUnread,
    dialogs,
  } = useStore();
  const [modal, setModal] = useState<Modal>(null);
  const { subscribeRoom } = useWebSocket();

  const fetchUnread = () => {
    api.get<UnreadCount[]>("/users/unread").then((counts) => {
      counts.forEach((u) => {
        if (u.room_id) setUnread(u.room_id, u.count);
        if (u.dialog_id) setUnread(u.dialog_id, u.count);
      });
    }).catch(() => {});
  };

  useEffect(() => {
    api.get<Friend[]>("/friends").then(setFriends).catch(() => {});
    api.get<Friendship[]>("/friends/requests").then(setPendingRequests).catch(() => {});
    api.get<Dialog[]>("/dialogs").then(setDialogs).catch(() => {});
    api.get<Room[]>("/rooms/mine").then((rooms) => {
      setMyRooms(rooms);
    }).catch(() => {});
    fetchUnread();

    const unreadInterval = setInterval(fetchUnread, 2_000);
    return () => clearInterval(unreadInterval);
  }, []);

  useEffect(() => {
    if (activeRoomId) subscribeRoom(activeRoomId);
  }, [activeRoomId]);

  // Subscribe to all rooms so unread counts update in real-time
  useEffect(() => {
    myRooms.forEach((r) => subscribeRoom(r.id));
  }, [myRooms]);

  const activeRoom = myRooms.find((r) => r.id === activeRoomId);
  const activeDialog = dialogs.find((d) => d.id === activeDialogId);

  return (
    <div className="h-screen flex flex-col">
      <TopMenu
        onPublicRooms={() => setModal("publicRooms")}
        onContacts={() => setModal("contacts")}
        onSessions={() => setModal("sessions")}
        onProfile={() => setModal("profile")}
      />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar onCreateRoom={() => setModal("createRoom")} />

        <main className="flex-1 overflow-hidden">
          {activeRoomId && activeRoom ? (
            <ChatWindow
              key={activeRoomId}
              type="room"
              id={activeRoomId}
              title={`#${activeRoom.name}`}
              subtitle={activeRoom.description}
            />
          ) : activeDialogId && activeDialog ? (
            <ChatWindow
              key={activeDialogId}
              type="dialog"
              id={activeDialogId}
              title={activeDialog.other_username}
              otherUserId={activeDialog.other_user_id}
            />
          ) : activeDirectUserId && activeDirectUsername ? (
            <ChatWindow
              key={activeDirectUserId}
              type="direct"
              id={activeDirectUserId}
              title={activeDirectUsername}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400">
              <div className="text-center">
                <div className="text-5xl mb-4">💬</div>
                <div className="text-xl font-medium">Welcome to ChatApp</div>
                <div className="text-sm mt-2">Select a room or contact to start chatting</div>
              </div>
            </div>
          )}
        </main>

        {activeRoom && (
          <MembersPanel
            room={activeRoom}
            onManage={() => setModal("manageRoom")}
            onInvite={() => setModal("invite")}
          />
        )}
      </div>

      {/* Modals */}
      {modal === "publicRooms" && <PublicRoomsCatalog onClose={() => setModal(null)} />}
      {modal === "createRoom" && <CreateRoomModal onClose={() => setModal(null)} />}
      {modal === "manageRoom" && activeRoom && (
        <ManageRoomModal
          room={activeRoom}
          onClose={() => setModal(null)}
          onDeleted={() => {}}
        />
      )}
      {modal === "invite" && activeRoom && (
        <InviteModal room={activeRoom} onClose={() => setModal(null)} />
      )}
      {modal === "contacts" && <ContactsModal onClose={() => setModal(null)} />}
      {modal === "sessions" && <SessionsModal onClose={() => setModal(null)} />}
      {modal === "profile" && <ProfileModal onClose={() => setModal(null)} />}
    </div>
  );
}

function InviteModal({ room, onClose }: { room: Room; onClose: () => void }) {
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const invite = async () => {
    setError(""); setSuccess("");
    try {
      await api.post(`/rooms/${room.id}/invite`, { username: username.trim() });
      setSuccess(`Invitation sent to ${username}`);
      setUsername("");
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
        <div className="flex justify-between mb-4">
          <h2 className="font-semibold">Invite to #{room.name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        {error && <div className="bg-red-50 text-red-600 rounded p-2 text-sm mb-3">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 rounded p-2 text-sm mb-3">{success}</div>}
        <div className="flex gap-2">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && invite()}
            placeholder="Username"
            className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button onClick={invite} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Invite
          </button>
        </div>
      </div>
    </div>
  );
}
