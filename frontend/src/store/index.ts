import { create } from "zustand";
import type {
  Dialog,
  Friend,
  Friendship,
  Message,
  PresenceStatus,
  Room,
  UnreadCount,
  User,
} from "../types";

export interface RoomInvitation {
  invitation_id: string;
  room_id: string;
  room_name: string;
}

interface ChatState {
  // Auth
  currentUser: User | null;
  setCurrentUser: (u: User | null) => void;

  // Active view
  activeRoomId: string | null;
  activeDialogId: string | null;
  activeDirectUserId: string | null;   // DM before first message (no dialog yet)
  activeDirectUsername: string | null;
  setActiveRoom: (id: string | null) => void;
  setActiveDialog: (id: string | null) => void;
  setActiveDirect: (userId: string, username: string) => void;

  // Rooms
  myRooms: Room[];
  setMyRooms: (rooms: Room[]) => void;
  upsertRoom: (room: Room) => void;
  removeRoom: (id: string) => void;

  // Messages
  messages: Record<string, Message[]>; // key = room_id or dialog_id
  setMessages: (key: string, msgs: Message[]) => void;
  prependMessages: (key: string, msgs: Message[]) => void;
  addMessage: (key: string, msg: Message) => void;
  updateMessage: (key: string, msg: Message) => void;
  deleteMessage: (key: string, msgId: string) => void;

  // Friends
  friends: Friend[];
  setFriends: (f: Friend[]) => void;
  pendingRequests: Friendship[];
  setPendingRequests: (r: Friendship[]) => void;

  // Dialogs
  dialogs: Dialog[];
  setDialogs: (d: Dialog[]) => void;

  // Presence
  presence: Record<string, PresenceStatus>;
  setPresence: (userId: string, status: PresenceStatus) => void;

  // Unread
  unread: Record<string, number>; // room_id or dialog_id -> count
  setUnread: (key: string, count: number) => void;
  clearUnread: (key: string) => void;

  // Room invitations
  roomInvitations: RoomInvitation[];
  setRoomInvitations: (invs: RoomInvitation[]) => void;
  addRoomInvitation: (inv: RoomInvitation) => void;
  removeRoomInvitation: (invitationId: string) => void;
}

export const useStore = create<ChatState>((set) => ({
  currentUser: null,
  setCurrentUser: (u) => set({ currentUser: u }),

  activeRoomId: null,
  activeDialogId: null,
  activeDirectUserId: null,
  activeDirectUsername: null,
  setActiveRoom: (id) => set({ activeRoomId: id, activeDialogId: null, activeDirectUserId: null, activeDirectUsername: null }),
  setActiveDialog: (id) => set({ activeDialogId: id, activeRoomId: null, activeDirectUserId: null, activeDirectUsername: null }),
  setActiveDirect: (userId, username) => set({ activeDirectUserId: userId, activeDirectUsername: username, activeRoomId: null, activeDialogId: null }),

  myRooms: [],
  setMyRooms: (rooms) => set({ myRooms: rooms }),
  upsertRoom: (room) =>
    set((s) => ({
      myRooms: s.myRooms.find((r) => r.id === room.id)
        ? s.myRooms.map((r) => (r.id === room.id ? room : r))
        : [...s.myRooms, room],
    })),
  removeRoom: (id) => set((s) => ({ myRooms: s.myRooms.filter((r) => r.id !== id) })),

  messages: {},
  setMessages: (key, msgs) => set((s) => ({ messages: { ...s.messages, [key]: msgs } })),
  prependMessages: (key, msgs) =>
    set((s) => ({ messages: { ...s.messages, [key]: [...msgs, ...(s.messages[key] || [])] } })),
  addMessage: (key, msg) =>
    set((s) => {
      if ((s.messages[key] || []).some((m) => m.id === msg.id)) return s;
      return { messages: { ...s.messages, [key]: [...(s.messages[key] || []), msg] } };
    }),
  updateMessage: (key, msg) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [key]: (s.messages[key] || []).map((m) => (m.id === msg.id ? msg : m)),
      },
    })),
  deleteMessage: (key, msgId) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [key]: (s.messages[key] || []).map((m) =>
          m.id === msgId ? { ...m, is_deleted: true, content: "" } : m
        ),
      },
    })),

  friends: [],
  setFriends: (f) =>
    set((s) => ({
      friends: f,
      presence: {
        ...s.presence,
        ...Object.fromEntries(f.filter((fr) => fr.presence).map((fr) => [fr.user_id, fr.presence!])),
      },
    })),
  pendingRequests: [],
  setPendingRequests: (r) => set({ pendingRequests: r }),

  dialogs: [],
  setDialogs: (d) =>
    set((s) => ({
      dialogs: d,
      presence: {
        ...s.presence,
        ...Object.fromEntries(d.filter((dl) => dl.other_presence).map((dl) => [dl.other_user_id, dl.other_presence!])),
      },
    })),

  presence: {},
  setPresence: (userId, status) =>
    set((s) => ({ presence: { ...s.presence, [userId]: status } })),

  unread: {},
  setUnread: (key, count) => set((s) => ({ unread: { ...s.unread, [key]: count } })),
  clearUnread: (key) => set((s) => ({ unread: { ...s.unread, [key]: 0 } })),

  roomInvitations: [],
  setRoomInvitations: (invs) => set({ roomInvitations: invs }),
  addRoomInvitation: (inv) => set((s) => ({
    roomInvitations: s.roomInvitations.some((i) => i.invitation_id === inv.invitation_id)
      ? s.roomInvitations
      : [...s.roomInvitations, inv],
  })),
  removeRoomInvitation: (id) => set((s) => ({
    roomInvitations: s.roomInvitations.filter((i) => i.invitation_id !== id),
  })),
}));
