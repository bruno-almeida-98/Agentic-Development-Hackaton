import type { PresenceStatus } from "../../types";

const colors: Record<PresenceStatus, string> = {
  online: "bg-green-500",
  afk: "bg-yellow-400",
  offline: "bg-gray-400",
};

export default function PresenceDot({ status }: { status?: PresenceStatus }) {
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 ${colors[status || "offline"]}`}
      title={status || "offline"}
    />
  );
}
