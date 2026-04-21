import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useStore } from "../store";
import type { User } from "../types";

export default function RegisterPage() {
  const navigate = useNavigate();
  const setCurrentUser = useStore((s) => s.setCurrentUser);
  const [form, setForm] = useState({ email: "", username: "", password: "", confirm_password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post<User>("/auth/register", form);
      const user = await api.post<User>("/auth/login", { email: form.email, password: form.password });
      setCurrentUser(user);
      navigate("/");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center text-blue-600">ChatApp</h1>
        <h2 className="text-lg font-semibold mb-4">Register</h2>
        {error && <div className="bg-red-50 text-red-600 rounded p-2 mb-4 text-sm">{error}</div>}
        <form onSubmit={submit} className="space-y-4">
          {[
            { key: "email", label: "Email", type: "email" },
            { key: "username", label: "Username", type: "text" },
            { key: "password", label: "Password", type: "password" },
            { key: "confirm_password", label: "Confirm password", type: "password" },
          ].map(({ key, label, type }) => (
            <div key={key}>
              <label className="block text-sm font-medium mb-1">{label}</label>
              <input
                type={type}
                value={(form as any)[key]}
                onChange={set(key)}
                className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          ))}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white rounded py-2 font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="text-sm text-center mt-4">
          Already have an account?{" "}
          <Link to="/login" className="text-blue-600 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
