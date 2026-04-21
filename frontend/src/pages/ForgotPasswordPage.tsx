import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [debugToken, setDebugToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const requestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post<any>("/auth/password-reset", { email });
      setDebugToken(res.debug_token || "");
      setSent(true);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const confirmReset = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post<any>(`/auth/password-reset/confirm?token=${debugToken}&new_password=${encodeURIComponent(newPassword)}`);
      setSuccess("Password reset! You can now sign in.");
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow p-8 w-full max-w-sm">
        <h2 className="text-lg font-semibold mb-4">Forgot Password</h2>
        {error && <div className="bg-red-50 text-red-600 rounded p-2 mb-4 text-sm">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 rounded p-2 mb-4 text-sm">{success}</div>}
        {!sent ? (
          <form onSubmit={requestReset} className="space-y-4">
            <p className="text-sm text-gray-600">Enter your email to reset password</p>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <button type="submit" className="w-full bg-blue-600 text-white rounded py-2 hover:bg-blue-700">
              Send reset link
            </button>
          </form>
        ) : (
          <form onSubmit={confirmReset} className="space-y-4">
            <p className="text-sm text-gray-600">
              Reset token (dev mode — would be sent via email in production):
            </p>
            <input
              type="text"
              value={debugToken}
              onChange={(e) => setDebugToken(e.target.value)}
              placeholder="Reset token"
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="New password"
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <button type="submit" className="w-full bg-blue-600 text-white rounded py-2 hover:bg-blue-700">
              Reset password
            </button>
          </form>
        )}
        <p className="text-sm text-center mt-4">
          <Link to="/login" className="text-blue-600 hover:underline">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}
