import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class PresenceStatus(enum.StrEnum):
    online = "online"
    afk = "afk"
    offline = "offline"


class FriendshipStatus(enum.StrEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class RoomVisibility(enum.StrEnum):
    public = "public"
    private = "private"


class RoomMemberRole(enum.StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    room_memberships: Mapped[list["RoomMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sent_requests: Mapped[list["Friendship"]] = relationship(
        "Friendship", foreign_keys="Friendship.requester_id", back_populates="requester", cascade="all, delete-orphan"
    )
    received_requests: Mapped[list["Friendship"]] = relationship(
        "Friendship", foreign_keys="Friendship.recipient_id", back_populates="recipient", cascade="all, delete-orphan"
    )
    bans_issued: Mapped[list["UserBan"]] = relationship(
        "UserBan", foreign_keys="UserBan.banner_id", back_populates="banner", cascade="all, delete-orphan"
    )
    bans_received: Mapped[list["UserBan"]] = relationship(
        "UserBan", foreign_keys="UserBan.banned_id", back_populates="banned", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[RoomVisibility] = mapped_column(Enum(RoomVisibility), default=RoomVisibility.public)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["RoomMember"]] = relationship(back_populates="room", cascade="all, delete-orphan")
    bans: Mapped[list["RoomBan"]] = relationship(back_populates="room", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship(back_populates="room", cascade="all, delete-orphan")
    invitations: Mapped[list["RoomInvitation"]] = relationship(back_populates="room", cascade="all, delete-orphan")


class RoomMember(Base):
    __tablename__ = "room_members"
    __table_args__ = (UniqueConstraint("room_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[RoomMemberRole] = mapped_column(Enum(RoomMemberRole), default=RoomMemberRole.member)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    room: Mapped["Room"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="room_memberships")


class RoomBan(Base):
    __tablename__ = "room_bans"
    __table_args__ = (UniqueConstraint("room_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    banned_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    banned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    room: Mapped["Room"] = relationship(back_populates="bans")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    banner: Mapped["User"] = relationship("User", foreign_keys=[banned_by])


class RoomInvitation(Base):
    __tablename__ = "room_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    invited_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invited_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    room: Mapped["Room"] = relationship(back_populates="invitations")
    invited_user: Mapped["User"] = relationship("User", foreign_keys=[invited_user_id])
    inviter: Mapped["User"] = relationship("User", foreign_keys=[invited_by])


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True)
    dialog_id: Mapped[str] = mapped_column(ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    reply_to_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    room: Mapped["Room"] = relationship(back_populates="messages")
    dialog: Mapped["Dialog"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id])
    reply_to: Mapped["Message"] = relationship("Message", remote_side="Message.id", foreign_keys=[reply_to_id])
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    message: Mapped["Message"] = relationship(back_populates="attachments")


# ---------------------------------------------------------------------------
# Dialogs (personal chats)
# ---------------------------------------------------------------------------


class Dialog(Base):
    __tablename__ = "dialogs"
    __table_args__ = (UniqueConstraint("user1_id", "user2_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user1_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user1: Mapped["User"] = relationship("User", foreign_keys=[user1_id])
    user2: Mapped["User"] = relationship("User", foreign_keys=[user2_id])
    messages: Mapped[list["Message"]] = relationship(back_populates="dialog", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Social: friendships, user bans
# ---------------------------------------------------------------------------


class Friendship(Base):
    __tablename__ = "friendships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[FriendshipStatus] = mapped_column(Enum(FriendshipStatus), default=FriendshipStatus.pending)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id], back_populates="sent_requests")
    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_id], back_populates="received_requests")


class UserBan(Base):
    __tablename__ = "user_bans"
    __table_args__ = (UniqueConstraint("banner_id", "banned_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    banner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    banned_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    banner: Mapped["User"] = relationship("User", foreign_keys=[banner_id], back_populates="bans_issued")
    banned: Mapped["User"] = relationship("User", foreign_keys=[banned_id], back_populates="bans_received")


# ---------------------------------------------------------------------------
# Unread tracking
# ---------------------------------------------------------------------------


class UnreadCount(Base):
    __tablename__ = "unread_counts"
    __table_args__ = (UniqueConstraint("user_id", "room_id"), UniqueConstraint("user_id", "dialog_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True)
    dialog_id: Mapped[str] = mapped_column(ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=True)
    count: Mapped[int] = mapped_column(BigInteger, default=0)
