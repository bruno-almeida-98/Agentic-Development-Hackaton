from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models import FriendshipStatus, PresenceStatus, RoomMemberRole, RoomVisibility

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    keep_signed_in: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime
    presence: PresenceStatus | None = PresenceStatus.offline

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: str
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    last_seen: datetime
    is_current: bool = False

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------


class RoomCreate(BaseModel):
    name: str
    description: str = ""
    visibility: RoomVisibility = RoomVisibility.public


class RoomUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: RoomVisibility | None = None


class RoomOut(BaseModel):
    id: str
    name: str
    description: str
    visibility: RoomVisibility
    owner_id: str
    created_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class RoomMemberOut(BaseModel):
    user_id: str
    username: str
    role: RoomMemberRole
    presence: PresenceStatus | None = PresenceStatus.offline

    model_config = {"from_attributes": True}


class RoomBanOut(BaseModel):
    user_id: str
    username: str
    banned_by_username: str | None
    banned_at: datetime

    model_config = {"from_attributes": True}


class InviteRequest(BaseModel):
    username: str


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class AttachmentOut(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size: int
    comment: str | None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    room_id: str | None
    dialog_id: str | None
    sender_id: str | None
    sender_username: str | None
    content: str
    reply_to_id: str | None
    reply_to_preview: str | None
    is_deleted: bool
    edited_at: datetime | None
    created_at: datetime
    attachments: list[AttachmentOut] = []

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str
    reply_to_id: str | None = None


class MessageEdit(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Friends
# ---------------------------------------------------------------------------


class FriendRequestCreate(BaseModel):
    username: str
    message: str | None = None


class FriendshipOut(BaseModel):
    id: str
    requester_id: str
    requester_username: str
    recipient_id: str
    recipient_username: str
    status: FriendshipStatus
    message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FriendOut(BaseModel):
    user_id: str
    username: str
    presence: PresenceStatus | None = PresenceStatus.offline

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------


class DialogOut(BaseModel):
    id: str
    other_user_id: str
    other_username: str
    other_presence: PresenceStatus | None = PresenceStatus.offline
    unread_count: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Unread
# ---------------------------------------------------------------------------


class UnreadOut(BaseModel):
    room_id: str | None = None
    dialog_id: str | None = None
    count: int
