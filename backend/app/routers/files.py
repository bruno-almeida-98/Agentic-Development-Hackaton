import os
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Attachment, Dialog, Message, RoomMember, User
from app.routers.messages import _msg_to_out

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    message_id: str = Form(...),
    comment: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")
    if msg.sender_id != user.id:
        raise HTTPException(403, "Not your message")

    content = await file.read()
    size = len(content)

    mime_type = file.content_type or "application/octet-stream"
    is_image = mime_type.startswith("image/")
    max_size = settings.MAX_IMAGE_SIZE if is_image else settings.MAX_FILE_SIZE

    if size > max_size:
        limit_mb = max_size // (1024 * 1024)
        raise HTTPException(400, f"File too large (max {limit_mb}MB)")

    ext = os.path.splitext(file.filename or "")[1]
    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    attachment = Attachment(
        message_id=message_id,
        original_name=file.filename or stored_name,
        file_path=stored_name,
        mime_type=mime_type,
        size=size,
        comment=comment or None,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    # Broadcast updated message with attachments
    from sqlalchemy.orm import selectinload
    refreshed = await db.execute(
        select(Message).options(selectinload(Message.attachments)).where(Message.id == message_id)
    )
    updated_msg = refreshed.scalar_one_or_none()
    if updated_msg:
        sender = await db.execute(select(User).where(User.id == updated_msg.sender_id))
        sender_user = sender.scalar_one_or_none()
        payload = {
            "type": "message.edited",
            "message": _msg_to_out(updated_msg, sender_user.username if sender_user else None).model_dump(mode="json"),
        }
        from app.ws_manager import manager
        if updated_msg.room_id:
            members_r = await db.execute(select(RoomMember).where(RoomMember.room_id == updated_msg.room_id))
            member_ids = [m.user_id for m in members_r.scalars().all()]
            for uid in member_ids:
                await manager.send_to_user(uid, payload)
        elif updated_msg.dialog_id:
            await manager.broadcast_dialog(updated_msg.dialog_id, payload, db)

    return {
        "id": attachment.id,
        "original_name": attachment.original_name,
        "mime_type": attachment.mime_type,
        "size": attachment.size,
        "comment": attachment.comment,
    }


@router.get("/{attachment_id}")
async def download_file(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    att = result.scalar_one_or_none()
    if not att:
        raise HTTPException(404, "File not found")

    msg_result = await db.execute(select(Message).where(Message.id == att.message_id))
    msg = msg_result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")

    # Check access
    if msg.room_id:
        member = await db.execute(
            select(RoomMember).where(RoomMember.room_id == msg.room_id, RoomMember.user_id == user.id)
        )
        if not member.scalar_one_or_none():
            raise HTTPException(403, "No access")
    elif msg.dialog_id:
        dialog = await db.execute(
            select(Dialog).where(
                Dialog.id == msg.dialog_id,
                (Dialog.user1_id == user.id) | (Dialog.user2_id == user.id),
            )
        )
        if not dialog.scalar_one_or_none():
            raise HTTPException(403, "No access")

    file_path = os.path.join(settings.UPLOAD_DIR, att.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found on disk")

    return FileResponse(
        path=file_path,
        filename=att.original_name,
        media_type=att.mime_type,
    )
