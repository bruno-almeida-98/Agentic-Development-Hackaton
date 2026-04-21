from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    Dialog,
    Friendship,
    FriendshipStatus,
    Message,
    RoomMember,
    RoomMemberRole,
    UnreadCount,
    User,
    UserBan,
)
from app.presence import get_presence_many
from app.schemas import MessageCreate, MessageEdit, MessageOut

router = APIRouter(tags=["messages"])


def _msg_to_out(msg: Message, sender_username: str | None = None, reply_preview: str | None = None) -> MessageOut:
    return MessageOut(
        id=msg.id,
        room_id=msg.room_id,
        dialog_id=msg.dialog_id,
        sender_id=msg.sender_id,
        sender_username=sender_username,
        content="" if msg.is_deleted else msg.content,
        reply_to_id=msg.reply_to_id,
        reply_to_preview=reply_preview,
        is_deleted=msg.is_deleted,
        edited_at=msg.edited_at,
        created_at=msg.created_at,
        attachments=[
            {"id": a.id, "original_name": a.original_name, "mime_type": a.mime_type, "size": a.size, "comment": a.comment}
            for a in msg.attachments
        ],
    )


async def _enrich_messages(db: AsyncSession, messages: list[Message]) -> list[MessageOut]:
    out = []
    for msg in messages:
        username = None
        if msg.sender_id:
            r = await db.execute(select(User).where(User.id == msg.sender_id))
            u = r.scalar_one_or_none()
            username = u.username if u else None

        reply_preview = None
        if msg.reply_to_id:
            r = await db.execute(select(Message).where(Message.id == msg.reply_to_id))
            rt = r.scalar_one_or_none()
            if rt and not rt.is_deleted:
                reply_preview = rt.content[:100]

        out.append(_msg_to_out(msg, username, reply_preview))
    return out


# ---------------------------------------------------------------------------
# Room messages
# ---------------------------------------------------------------------------


@router.get("/api/rooms/{room_id}/messages", response_model=list[MessageOut])
async def get_room_messages(
    room_id: str,
    before: str | None = Query(default=None),
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user.id))
    if not member.scalar_one_or_none():
        raise HTTPException(403, "Not a member")

    q = select(Message).options(selectinload(Message.attachments)).where(Message.room_id == room_id)
    if before:
        r = await db.execute(select(Message).where(Message.id == before))
        ref = r.scalar_one_or_none()
        if ref:
            q = q.where(Message.created_at < ref.created_at)
    q = q.order_by(Message.created_at.desc()).limit(limit)
    result = await db.execute(q)
    messages = list(reversed(result.scalars().all()))

    # Mark as read
    await _mark_read(db, user.id, room_id=room_id)
    return await _enrich_messages(db, messages)


@router.post("/api/rooms/{room_id}/messages", response_model=MessageOut, status_code=201)
async def send_room_message(
    room_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(body.content.encode()) > 3 * 1024:
        raise HTTPException(400, "Message too long (max 3KB)")

    member = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user.id))
    if not member.scalar_one_or_none():
        raise HTTPException(403, "Not a member")

    msg = Message(room_id=room_id, sender_id=user.id, content=body.content, reply_to_id=body.reply_to_id)
    db.add(msg)
    await db.flush()
    await db.refresh(msg)

    # Capture before commit — expire_on_commit=True will expire user attrs after commit
    sender_username = user.username
    sender_id = user.id

    # Increment unread for all other members — capture IDs before commit
    members_result = await db.execute(
        select(RoomMember).where(RoomMember.room_id == room_id)
    )
    all_member_ids = [m.user_id for m in members_result.scalars().all()]
    for uid in all_member_ids:
        if uid != sender_id:
            await _increment_unread(db, uid, room_id=room_id)

    await db.commit()
    result2 = await db.execute(
        select(Message).options(selectinload(Message.attachments)).where(Message.id == msg.id)
    )
    msg = result2.scalar_one()

    # Send message.new directly to every room member (not just subscribed)
    from app.ws_manager import manager
    payload = {
        "type": "message.new",
        "message": _msg_to_out(msg, sender_username).model_dump(mode="json"),
    }
    for uid in all_member_ids:
        await manager.send_to_user(uid, payload)

    return _msg_to_out(msg, sender_username)


# ---------------------------------------------------------------------------
# Dialog (personal) messages
# ---------------------------------------------------------------------------


@router.get("/api/dialogs/{dialog_id}/messages", response_model=list[MessageOut])
async def get_dialog_messages(
    dialog_id: str,
    before: str | None = Query(default=None),
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dialog = await db.execute(
        select(Dialog).where(Dialog.id == dialog_id, (Dialog.user1_id == user.id) | (Dialog.user2_id == user.id))
    )
    if not dialog.scalar_one_or_none():
        raise HTTPException(403, "Not a participant")

    q = select(Message).options(selectinload(Message.attachments)).where(Message.dialog_id == dialog_id)
    if before:
        r = await db.execute(select(Message).where(Message.id == before))
        ref = r.scalar_one_or_none()
        if ref:
            q = q.where(Message.created_at < ref.created_at)
    q = q.order_by(Message.created_at.desc()).limit(limit)
    result = await db.execute(q)
    messages = list(reversed(result.scalars().all()))

    await _mark_read(db, user.id, dialog_id=dialog_id)
    return await _enrich_messages(db, messages)


@router.post("/api/dialogs/{other_user_id}/send", response_model=MessageOut, status_code=201)
async def send_direct_message(
    other_user_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(body.content.encode()) > 3 * 1024:
        raise HTTPException(400, "Message too long (max 3KB)")

    # Check friendship
    fs = await db.execute(
        select(Friendship).where(
            Friendship.status == FriendshipStatus.accepted,
            (
                (Friendship.requester_id == user.id) & (Friendship.recipient_id == other_user_id)
                | (Friendship.requester_id == other_user_id) & (Friendship.recipient_id == user.id)
            ),
        )
    )
    if not fs.scalar_one_or_none():
        raise HTTPException(403, "Must be friends to message")

    # Check mutual ban
    ban = await db.execute(
        select(UserBan).where(
            ((UserBan.banner_id == user.id) & (UserBan.banned_id == other_user_id))
            | ((UserBan.banner_id == other_user_id) & (UserBan.banned_id == user.id))
        )
    )
    if ban.scalar_one_or_none():
        raise HTTPException(403, "Messaging is blocked")

    # Get or create dialog (ensure user1_id < user2_id for unique constraint)
    u1, u2 = sorted([user.id, other_user_id])
    dialog_result = await db.execute(select(Dialog).where(Dialog.user1_id == u1, Dialog.user2_id == u2))
    dialog = dialog_result.scalar_one_or_none()
    if not dialog:
        dialog = Dialog(user1_id=u1, user2_id=u2)
        db.add(dialog)
        await db.flush()

    sender_username = user.username
    msg = Message(dialog_id=dialog.id, sender_id=user.id, content=body.content, reply_to_id=body.reply_to_id)
    db.add(msg)
    await db.flush()

    await _increment_unread(db, other_user_id, dialog_id=dialog.id)
    await db.commit()
    result2 = await db.execute(
        select(Message).options(selectinload(Message.attachments)).where(Message.id == msg.id)
    )
    msg = result2.scalar_one()

    from app.ws_manager import manager
    await manager.send_to_user(other_user_id, {
        "type": "message.new",
        "message": _msg_to_out(msg, sender_username).model_dump(mode="json"),
    })

    return _msg_to_out(msg, sender_username)


@router.get("/api/dialogs", response_model=list)
async def list_dialogs(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Dialog).where((Dialog.user1_id == user.id) | (Dialog.user2_id == user.id))
    )
    dialogs = result.scalars().all()
    other_ids = []
    rows = []
    for d in dialogs:
        other_id = d.user2_id if d.user1_id == user.id else d.user1_id
        r = await db.execute(select(User).where(User.id == other_id))
        other = r.scalar_one_or_none()
        if not other:
            continue
        unread_r = await db.execute(
            select(UnreadCount).where(UnreadCount.user_id == user.id, UnreadCount.dialog_id == d.id)
        )
        unread = unread_r.scalar_one_or_none()
        other_ids.append(other_id)
        rows.append((d, other, unread))

    presence_map = await get_presence_many(other_ids) if other_ids else {}
    out = []
    for d, other, unread in rows:
        out.append({
            "id": d.id,
            "other_user_id": other.id,
            "other_username": other.username,
            "other_presence": presence_map.get(other.id, "offline"),
            "unread_count": unread.count if unread else 0,
        })
    return out


# ---------------------------------------------------------------------------
# Message actions
# ---------------------------------------------------------------------------


@router.put("/api/messages/{message_id}", response_model=MessageOut)
async def edit_message(
    message_id: str,
    body: MessageEdit,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")
    if msg.sender_id != user.id:
        raise HTTPException(403, "Not your message")
    if msg.is_deleted:
        raise HTTPException(400, "Cannot edit deleted message")

    if len(body.content.encode()) > 3 * 1024:
        raise HTTPException(400, "Message too long")

    sender_username = user.username
    msg.content = body.content
    msg.edited_at = datetime.now(UTC)
    await db.commit()
    result2 = await db.execute(
        select(Message).options(selectinload(Message.attachments)).where(Message.id == message_id)
    )
    msg = result2.scalar_one()

    from app.ws_manager import manager
    payload = {"type": "message.edited", "message": _msg_to_out(msg, sender_username).model_dump(mode="json")}
    if msg.room_id:
        members_r = await db.execute(select(RoomMember).where(RoomMember.room_id == msg.room_id))
        member_ids = [m.user_id for m in members_r.scalars().all()]
        for uid in member_ids:
            await manager.send_to_user(uid, payload)
    else:
        await manager.broadcast_dialog(msg.dialog_id, payload, db)

    return _msg_to_out(msg, user.username)


@router.delete("/api/messages/{message_id}")
async def delete_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")

    can_delete = msg.sender_id == user.id
    if not can_delete and msg.room_id:
        member = await db.execute(
            select(RoomMember).where(RoomMember.room_id == msg.room_id, RoomMember.user_id == user.id)
        )
        m = member.scalar_one_or_none()
        if m and m.role in (RoomMemberRole.admin, RoomMemberRole.owner):
            can_delete = True

    if not can_delete:
        raise HTTPException(403, "Cannot delete this message")

    msg.is_deleted = True
    msg.content = ""
    await db.commit()

    from app.ws_manager import manager
    payload = {"type": "message.deleted", "message_id": message_id, "room_id": msg.room_id, "dialog_id": msg.dialog_id}
    if msg.room_id:
        members_r = await db.execute(select(RoomMember).where(RoomMember.room_id == msg.room_id))
        member_ids = [m.user_id for m in members_r.scalars().all()]
        for uid in member_ids:
            await manager.send_to_user(uid, payload)
    else:
        await manager.broadcast_dialog(msg.dialog_id, payload, db)

    return {"ok": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _mark_read(db: AsyncSession, user_id: str, room_id: str = None, dialog_id: str = None):
    if room_id:
        result = await db.execute(
            select(UnreadCount).where(UnreadCount.user_id == user_id, UnreadCount.room_id == room_id)
        )
    else:
        result = await db.execute(
            select(UnreadCount).where(UnreadCount.user_id == user_id, UnreadCount.dialog_id == dialog_id)
        )
    u = result.scalar_one_or_none()
    if u:
        u.count = 0
        await db.commit()


async def _increment_unread(db: AsyncSession, user_id: str, room_id: str = None, dialog_id: str = None):
    if room_id:
        result = await db.execute(
            select(UnreadCount).where(UnreadCount.user_id == user_id, UnreadCount.room_id == room_id)
        )
    else:
        result = await db.execute(
            select(UnreadCount).where(UnreadCount.user_id == user_id, UnreadCount.dialog_id == dialog_id)
        )
    u = result.scalar_one_or_none()
    if u:
        u.count += 1
    else:
        u = UnreadCount(user_id=user_id, room_id=room_id, dialog_id=dialog_id, count=1)
        db.add(u)
