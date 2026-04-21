import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { useStore } from "../../store";
import Modal from "../common/Modal";

interface Props { onClose: () => void; }

export default function ProfileModal({ onClose }: Props) {
  const { currentUser, setCurrentUser } = useStore();
  const navigate = useNavigate();
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setSuccess("");
    try {
      await api.put("/auth/password", { current_password: currentPwd, new_password: newPwd });
      setSuccess("Password changed successfully");
      setCurrentPwd(""); setNewPwd("");
    } catch (err: any) {
      setError(err.message);
    }
  };

  const deleteAccount = async () => {
    if (!confirm("Delete your account? This cannot be undone.")) return;
    await api.delete("/auth/account");
    setCurrentUser(null);
    navigate("/login");
  };

  return (
    <Modal title="Profile" onClose={onClose} size="sm">
      <div className="space-y-6">
        <div className="text-sm space-y-1">
          <div><strong>Username:</strong> {currentUser?.username}</div>
          <div><strong>Email:</strong> {currentUser?.email}</div>
        </div>

        <div>
          <h3 className="font-medium mb-3">Change Password</h3>
          {error && <div className="bg-red-50 text-red-600 rounded p-2 text-sm mb-2">{error}</div>}
          {success && <div className="bg-green-50 text-green-700 rounded p-2 text-sm mb-2">{success}</div>}
          <form onSubmit={changePassword} className="space-y-3">
            <input
              type="password"
              value={currentPwd}
              onChange={(e) => setCurrentPwd(e.target.value)}
              placeholder="Current password"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              required
            />
            <input
              type="password"
              value={newPwd}
              onChange={(e) => setNewPwd(e.target.value)}
              placeholder="New password"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              required
            />
            <button type="submit" className="w-full bg-blue-600 text-white rounded py-2 text-sm hover:bg-blue-700">
              Change password
            </button>
          </form>
        </div>

        <div className="border-t pt-4">
          <button
            onClick={deleteAccount}
            className="w-full bg-red-600 text-white rounded py-2 text-sm hover:bg-red-700"
          >
            Delete account
          </button>
        </div>
      </div>
    </Modal>
  );
}
