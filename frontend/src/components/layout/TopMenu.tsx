import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { useStore } from "../../store";

interface Props {
  onPublicRooms: () => void;
  onContacts: () => void;
  onSessions: () => void;
  onProfile: () => void;
}

export default function TopMenu({ onPublicRooms, onContacts, onSessions, onProfile }: Props) {
  const { currentUser, setCurrentUser } = useStore();
  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);

  const signOut = async () => {
    await api.post("/auth/logout");
    setCurrentUser(null);
    navigate("/login");
  };

  return (
    <div className="h-12 bg-blue-700 text-white flex items-center px-4 gap-4 flex-shrink-0">
      <span className="font-bold text-lg mr-4">💬 ChatApp</span>
      <button onClick={onPublicRooms} className="text-sm hover:text-blue-200">Public Rooms</button>
      <button onClick={onContacts} className="text-sm hover:text-blue-200">Contacts</button>
      <button onClick={onSessions} className="text-sm hover:text-blue-200">Sessions</button>

      <div className="ml-auto relative">
        <button
          onClick={() => setProfileOpen(!profileOpen)}
          className="flex items-center gap-1 text-sm hover:text-blue-200"
        >
          <span>{currentUser?.username}</span>
          <span>▾</span>
        </button>
        {profileOpen && (
          <div className="absolute right-0 top-full mt-1 bg-white text-gray-800 rounded shadow-lg py-1 w-40 z-50">
            <button onClick={() => { onProfile(); setProfileOpen(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100">Profile</button>
            <button onClick={signOut} className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 text-red-600">Sign out</button>
          </div>
        )}
      </div>
    </div>
  );
}
