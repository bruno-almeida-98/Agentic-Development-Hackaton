import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useStore } from "../../store";
import type { Friend, Friendship, User } from "../../types";
import Modal from "../common/Modal";
import PresenceDot from "../common/PresenceDot";

interface Props { onClose: () => void; }

export default function ContactsModal({ onClose }: Props) {
  const { friends, setFriends, pendingRequests, setPendingRequests, presence, dialogs, setActiveDialog } = useStore();
  const [tab, setTab] = useState<"friends" | "requests" | "add">("friends");
  const [searchUsername, setSearchUsername] = useState("");
  const [requestMsg, setRequestMsg] = useState("");
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  const reload = () => {
    api.get<Friend[]>("/friends").then(setFriends).catch(() => {});
    api.get<Friendship[]>("/friends/requests").then(setPendingRequests).catch(() => {});
  };

  useEffect(() => { reload(); }, []);

  const search = async () => {
    if (!searchUsername.trim()) return;
    try {
      const results = await api.get<User[]>(`/users/search?q=${encodeURIComponent(searchUsername)}`);
      setSearchResults(results);
      setSearched(true);
    } catch {}
  };

  const sendRequest = async (username: string) => {
    setError("");
    try {
      await api.post("/friends/requests", { username, message: requestMsg || undefined });
      setSearchUsername("");
      setSearchResults([]);
      setRequestMsg("");
      reload();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const respond = async (id: string, action: "accept" | "reject") => {
    await api.put(`/friends/requests/${id}?action=${action}`);
    reload();
  };

  const removeFriend = async (userId: string) => {
    if (!confirm("Remove this friend?")) return;
    await api.delete(`/friends/${userId}`);
    reload();
  };

  const openDialog = (friend: Friend) => {
    const dialog = dialogs.find((d) => d.other_user_id === friend.user_id);
    if (dialog) setActiveDialog(dialog.id);
    onClose();
  };

  const received = pendingRequests.filter((r) => r.recipient_id === useStore.getState().currentUser?.id);
  const sent = pendingRequests.filter((r) => r.requester_id === useStore.getState().currentUser?.id);

  return (
    <Modal title="Contacts" onClose={onClose} size="md">
      <div className="flex gap-1 mb-4">
        {([
          { key: "friends", label: `Friends (${friends.length})` },
          { key: "requests", label: `Requests (${received.length})` },
          { key: "add", label: "Add friend" },
        ] as const).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-1.5 rounded text-sm ${tab === t.key ? "bg-blue-600 text-white" : "bg-gray-100 hover:bg-gray-200"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "friends" && (
        <div className="space-y-1">
          {friends.length === 0 && <div className="text-gray-400 text-sm">No friends yet</div>}
          {friends.map((f) => (
            <div key={f.user_id} className="flex items-center gap-3 p-2 rounded hover:bg-gray-50">
              <PresenceDot status={presence[f.user_id] || f.presence} />
              <span className="flex-1 text-sm font-medium">{f.username}</span>
              <button onClick={() => openDialog(f)} className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded hover:bg-blue-100">Message</button>
              <button onClick={() => removeFriend(f.user_id)} className="text-xs text-red-500 hover:underline">Remove</button>
            </div>
          ))}
        </div>
      )}

      {tab === "requests" && (
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-semibold mb-2">Received</h3>
            {received.length === 0 && <div className="text-gray-400 text-sm">No pending requests</div>}
            {received.map((r) => (
              <div key={r.id} className="flex items-center gap-2 p-2 rounded bg-gray-50 mb-1">
                <span className="flex-1 text-sm">
                  <strong>{r.requester_username}</strong>
                  {r.message && <span className="text-gray-500"> — {r.message}</span>}
                </span>
                <button onClick={() => respond(r.id, "accept")} className="text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700">Accept</button>
                <button onClick={() => respond(r.id, "reject")} className="text-xs bg-gray-200 px-2 py-1 rounded hover:bg-gray-300">Reject</button>
              </div>
            ))}
          </div>
          <div>
            <h3 className="text-sm font-semibold mb-2">Sent</h3>
            {sent.length === 0 && <div className="text-gray-400 text-sm">No sent requests</div>}
            {sent.map((r) => (
              <div key={r.id} className="flex items-center gap-2 p-2 rounded bg-gray-50 mb-1 text-sm">
                <span className="flex-1">To <strong>{r.recipient_username}</strong></span>
                <span className="text-yellow-600 text-xs">Pending</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "add" && (
        <div className="space-y-4">
          {error && <div className="bg-red-50 text-red-600 rounded p-2 text-sm">{error}</div>}
          <div className="flex gap-2">
            <input
              value={searchUsername}
              onChange={(e) => setSearchUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Search by username"
              className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button onClick={search} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Search</button>
          </div>
          <textarea
            value={requestMsg}
            onChange={(e) => setRequestMsg(e.target.value)}
            placeholder="Optional message..."
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            rows={2}
          />
          <div className="space-y-1">
            {searched && searchResults.length === 0 && (
              <div className="text-gray-400 text-sm text-center py-2">No users found</div>
            )}
            {searchResults.map((u) => (
              <div key={u.id} className="flex items-center gap-2 p-2 rounded hover:bg-gray-50">
                <span className="flex-1 text-sm">{u.username}</span>
                <button onClick={() => sendRequest(u.username)} className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700">
                  Add friend
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  );
}
