import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { SessionInfo } from "../../types";
import Modal from "../common/Modal";

interface Props { onClose: () => void; }

export default function SessionsModal({ onClose }: Props) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);

  const load = () => api.get<SessionInfo[]>("/auth/sessions").then(setSessions).catch(() => {});
  useEffect(() => { load(); }, []);

  const revoke = async (id: string) => {
    await api.delete(`/auth/sessions/${id}`);
    load();
  };

  return (
    <Modal title="Active Sessions" onClose={onClose} size="md">
      <div className="space-y-2">
        {sessions.map((s) => (
          <div key={s.id} className={`p-3 rounded border ${s.is_current ? "border-blue-300 bg-blue-50" : "border-gray-200"}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm flex-1 min-w-0">
                <div className="font-medium truncate">{s.user_agent || "Unknown browser"}</div>
                <div className="text-gray-500">{s.ip_address || "Unknown IP"}</div>
                <div className="text-xs text-gray-400">
                  Created: {new Date(s.created_at).toLocaleString()}
                  {" | "}Last seen: {new Date(s.last_seen).toLocaleString()}
                </div>
                {s.is_current && <span className="text-xs text-blue-600 font-medium">Current session</span>}
              </div>
              {!s.is_current && (
                <button
                  onClick={() => revoke(s.id)}
                  className="text-xs bg-red-50 text-red-600 px-2 py-1 rounded hover:bg-red-100 flex-shrink-0"
                >
                  Revoke
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
