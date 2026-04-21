export type PresenceStatus = "online" | "afk" | "offline";
export type RoomVisibility = "public" | "private";
export type RoomMemberRole = "owner" | "admin" | "member";
export type FriendshipStatus = "pending" | "accepted" | "rejected";

export interface User {
  id: string;
  email: string;
  username: string;
  created_at: string;
  presence?: PresenceStatus;
}

export interface SessionInfo {
  id: string;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  last_seen: string;
  is_current: boolean;
}

export interface Room {
  id: string;
  name: string;
  description: string;
  visibility: RoomVisibility;
  owner_id: string;
  created_at: string;
  member_count: number;
}

export interface RoomMember {
  user_id: string;
  username: string;
  role: RoomMemberRole;
  presence?: PresenceStatus;
}

export interface RoomBan {
  user_id: string;
  username: string;
  banned_by_username: string | null;
  banned_at: string;
}

export interface Attachment {
  id: string;
  original_name: string;
  mime_type: string;
  size: number;
  comment: string | null;
}

export interface Message {
  id: string;
  room_id: string | null;
  dialog_id: string | null;
  sender_id: string | null;
  sender_username: string | null;
  content: string;
  reply_to_id: string | null;
  reply_to_preview: string | null;
  is_deleted: boolean;
  edited_at: string | null;
  created_at: string;
  attachments: Attachment[];
}

export interface Friendship {
  id: string;
  requester_id: string;
  requester_username: string;
  recipient_id: string;
  recipient_username: string;
  status: FriendshipStatus;
  message: string | null;
  created_at: string;
}

export interface Friend {
  user_id: string;
  username: string;
  presence?: PresenceStatus;
}

export interface Dialog {
  id: string;
  other_user_id: string;
  other_username: string;
  other_presence?: PresenceStatus;
  unread_count: number;
}

export interface UnreadCount {
  room_id: string | null;
  dialog_id: string | null;
  count: number;
}

export type WSEvent =
  | { type: "message.new"; message: Message }
  | { type: "message.edited"; message: Message }
  | { type: "message.deleted"; message_id: string; room_id: string | null; dialog_id: string | null }
  | { type: "presence.update"; user_id: string; status: PresenceStatus }
  | { type: "presence.self"; status: PresenceStatus }
  | { type: "friend.request"; friendship: Friendship }
  | { type: "friend.accepted"; by_username: string }
  | { type: "room.invitation"; invitation_id: string; room_id: string; room_name: string };
