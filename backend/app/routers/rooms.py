from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    Room,
    RoomBan,
    RoomInvitation,
    RoomMember,
    RoomMemberRole,
    RoomVisibility,
    User,
)
from app.schemas import (
    InviteRequest,
    RoomBanOut,
    RoomCreate,
    RoomMemberOut,
    RoomOut,
    RoomUpdate,
)

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def _room_to_out(room: Room, member_count: int = 0) -> RoomOut:
    return RoomOut(
        id=room.id,
        name=room.name,
        description=room.description,
        visibility=room.visibility,
        owner_id=room.owner_id,
        created_at=room.created_at,
        member_count=member_count,
    )


async def _get_member_role(db: AsyncSession, room_id: str, user_id: str) -> RoomMemberRole | None:
    result = await db.execute(
        select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
    )
    m = result.scalar_one_or_none()
    return m.role if m else None


async def _require_admin(db: AsyncSession, room_id: str, user_id: str) -> RoomMember:
    result = await db.execute(
        select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
    )
    m = result.scalar_one_or_none()
    if not m or m.role not in (RoomMemberRole.admin, RoomMemberRole.owner):
        raise HTTPException(403, "Admin required")
    return m


@router.get("", response_model=list[RoomOut])
async def list_public_rooms(
    search: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Room).where(Room.visibility == RoomVisibility.public)
    if search:
        q = q.where(Room.name.ilike(f"%{search}%"))
    result = await db.execute(q)
    rooms = result.scalars().all()

    out = []
    for room in rooms:
        cnt = await db.execute(select(func.count()).where(RoomMember.room_id == room.id))
        out.append(_room_to_out(room, cnt.scalar()))
    return out


@router.get("/mine", response_model=list[RoomOut])
async def list_my_rooms(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Room)
        .join(RoomMember, Room.id == RoomMember.room_id)
        .where(RoomMember.user_id == user.id)
    )
    rooms = result.scalars().all()
    out = []
    for room in rooms:
        cnt = await db.execute(select(func.count()).where(RoomMember.room_id == room.id))
        out.append(_room_to_out(room, cnt.scalar()))
    return out


@router.post("", response_model=RoomOut, status_code=201)
async def create_room(
    body: RoomCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await db.execute(select(Room).where(Room.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Room name already taken")

    room = Room(name=body.name, description=body.description, visibility=body.visibility, owner_id=user.id)
    db.add(room)
    await db.flush()

    member = RoomMember(room_id=room.id, user_id=user.id, role=RoomMemberRole.owner)
    db.add(member)
    await db.commit()
    await db.refresh(room)
    return _room_to_out(room, 1)


@router.get("/{room_id}", response_model=RoomOut)
async def get_room(room_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")

    role = await _get_member_role(db, room_id, user.id)
    if room.visibility == RoomVisibility.private and role is None:
        raise HTTPException(403, "Not a member")

    cnt = await db.execute(select(func.count()).where(RoomMember.room_id == room.id))
    return _room_to_out(room, cnt.scalar())


@router.put("/{room_id}", response_model=RoomOut)
async def update_room(
    room_id: str,
    body: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")

    await _require_admin(db, room_id, user.id)

    if body.name is not None:
        existing = await db.execute(select(Room).where(Room.name == body.name, Room.id != room_id))
        if existing.scalar_one_or_none():
            raise HTTPException(400, "Room name already taken")
        room.name = body.name
    if body.description is not None:
        room.description = body.description
    if body.visibility is not None:
        room.visibility = body.visibility

    await db.commit()
    await db.refresh(room)
    cnt = await db.execute(select(func.count()).where(RoomMember.room_id == room.id))
    return _room_to_out(room, cnt.scalar())


@router.delete("/{room_id}")
async def delete_room(room_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")
    if room.owner_id != user.id:
        raise HTTPException(403, "Only owner can delete room")

    await db.delete(room)
    await db.commit()
    return {"ok": True}


@router.post("/{room_id}/join")
async def join_room(room_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")
    if room.visibility == RoomVisibility.private:
        raise HTTPException(403, "Private room — invitation required")

    ban = await db.execute(select(RoomBan).where(RoomBan.room_id == room_id, RoomBan.user_id == user.id))
    if ban.scalar_one_or_none():
        raise HTTPException(403, "You are banned from this room")

    existing = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user.id))
    if not existing.scalar_one_or_none():
        db.add(RoomMember(room_id=room_id, user_id=user.id, role=RoomMemberRole.member))
        await db.commit()
    return {"ok": True}


@router.post("/{room_id}/leave")
async def leave_room(room_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")
    if room.owner_id == user.id:
        raise HTTPException(400, "Owner cannot leave — delete the room instead")

    result2 = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user.id))
    m = result2.scalar_one_or_none()
    if m:
        await db.delete(m)
        await db.commit()
    return {"ok": True}


@router.get("/{room_id}/members", response_model=list[RoomMemberOut])
async def list_members(room_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    role = await _get_member_role(db, room_id, user.id)
    if role is None:
        raise HTTPException(403, "Not a member")

    result = await db.execute(
        select(RoomMember, User)
        .join(User, RoomMember.user_id == User.id)
        .where(RoomMember.room_id == room_id)
    )
    rows = result.all()
    return [RoomMemberOut(user_id=u.id, username=u.username, role=m.role) for m, u in rows]


@router.post("/{room_id}/members/{user_id}/admin")
async def promote_admin(
    room_id: str, user_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await _require_admin(db, room_id, user.id)
    result = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Member not found")
    if m.role == RoomMemberRole.owner:
        raise HTTPException(400, "Cannot change owner role")
    m.role = RoomMemberRole.admin
    await db.commit()
    return {"ok": True}


@router.delete("/{room_id}/members/{user_id}/admin")
async def demote_admin(
    room_id: str, user_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result_my = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user.id))
    my = result_my.scalar_one_or_none()
    if not my or my.role not in (RoomMemberRole.admin, RoomMemberRole.owner):
        raise HTTPException(403, "Admin required")

    result = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Member not found")
    if m.role == RoomMemberRole.owner:
        raise HTTPException(400, "Cannot demote owner")

    # Only owner can demote other admins
    room_result = await db.execute(select(Room).where(Room.id == room_id))
    room = room_result.scalar_one_or_none()
    if m.role == RoomMemberRole.admin and room.owner_id != user.id:
        raise HTTPException(403, "Only owner can remove admins")

    m.role = RoomMemberRole.member
    await db.commit()
    return {"ok": True}


@router.delete("/{room_id}/members/{user_id}")
async def remove_member(
    room_id: str, user_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await _require_admin(db, room_id, user.id)

    room_result = await db.execute(select(Room).where(Room.id == room_id))
    room = room_result.scalar_one_or_none()
    if room.owner_id == user_id:
        raise HTTPException(400, "Cannot remove owner")

    result = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id))
    m = result.scalar_one_or_none()
    if m:
        await db.delete(m)

    # Add to ban list
    existing_ban = await db.execute(select(RoomBan).where(RoomBan.room_id == room_id, RoomBan.user_id == user_id))
    if not existing_ban.scalar_one_or_none():
        db.add(RoomBan(room_id=room_id, user_id=user_id, banned_by=user.id))
    await db.commit()
    return {"ok": True}


@router.get("/{room_id}/bans", response_model=list[RoomBanOut])
async def list_bans(room_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_admin(db, room_id, user.id)

    result = await db.execute(
        select(RoomBan, User)
        .join(User, RoomBan.user_id == User.id)
        .where(RoomBan.room_id == room_id)
    )
    rows = result.all()
    out = []
    for ban, banned_user in rows:
        banner_name = None
        if ban.banned_by:
            r = await db.execute(select(User).where(User.id == ban.banned_by))
            banner = r.scalar_one_or_none()
            banner_name = banner.username if banner else None
        out.append(
            RoomBanOut(
                user_id=banned_user.id,
                username=banned_user.username,
                banned_by_username=banner_name,
                banned_at=ban.banned_at,
            )
        )
    return out


@router.post("/{room_id}/bans/{user_id}")
async def ban_user(
    room_id: str, user_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await _require_admin(db, room_id, user.id)

    room_result = await db.execute(select(Room).where(Room.id == room_id))
    room = room_result.scalar_one_or_none()
    if room.owner_id == user_id:
        raise HTTPException(400, "Cannot ban owner")

    # Remove from members
    result = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id))
    m = result.scalar_one_or_none()
    if m:
        await db.delete(m)

    existing_ban = await db.execute(select(RoomBan).where(RoomBan.room_id == room_id, RoomBan.user_id == user_id))
    if not existing_ban.scalar_one_or_none():
        db.add(RoomBan(room_id=room_id, user_id=user_id, banned_by=user.id))
    await db.commit()
    return {"ok": True}


@router.delete("/{room_id}/bans/{user_id}")
async def unban_user(
    room_id: str, user_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    await _require_admin(db, room_id, user.id)
    result = await db.execute(select(RoomBan).where(RoomBan.room_id == room_id, RoomBan.user_id == user_id))
    ban = result.scalar_one_or_none()
    if ban:
        await db.delete(ban)
        await db.commit()
    return {"ok": True}


@router.post("/{room_id}/invite")
async def invite_user(
    room_id: str,
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    role = await _get_member_role(db, room_id, user.id)
    if role is None:
        raise HTTPException(403, "Not a member")

    result = await db.execute(select(User).where(User.username == body.username))
    invitee = result.scalar_one_or_none()
    if not invitee:
        raise HTTPException(404, "User not found")

    ban = await db.execute(select(RoomBan).where(RoomBan.room_id == room_id, RoomBan.user_id == invitee.id))
    if ban.scalar_one_or_none():
        raise HTTPException(400, "User is banned from this room")

    existing_member = await db.execute(
        select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == invitee.id)
    )
    if existing_member.scalar_one_or_none():
        return {"ok": True, "message": "Already a member"}

    existing_invite = await db.execute(
        select(RoomInvitation).where(
            RoomInvitation.room_id == room_id, RoomInvitation.invited_user_id == invitee.id
        )
    )
    if not existing_invite.scalar_one_or_none():
        room_result = await db.execute(select(Room).where(Room.id == room_id))
        room = room_result.scalar_one_or_none()
        inv = RoomInvitation(room_id=room_id, invited_user_id=invitee.id, invited_by=user.id)
        db.add(inv)
        await db.commit()
        await db.refresh(inv)
        from app.ws_manager import manager
        await manager.send_to_user(invitee.id, {
            "type": "room.invitation",
            "invitation_id": inv.id,
            "room_id": room_id,
            "room_name": room.name if room else "",
        })
    return {"ok": True}


@router.get("/{room_id}/invitations")
async def list_invitations(room_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_admin(db, room_id, user.id)
    result = await db.execute(
        select(RoomInvitation, User)
        .join(User, RoomInvitation.invited_user_id == User.id)
        .where(RoomInvitation.room_id == room_id)
    )
    rows = result.all()
    return [{"user_id": u.id, "username": u.username, "created_at": inv.created_at} for inv, u in rows]


@router.post("/{room_id}/invitations/accept")
async def accept_invitation(room_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(RoomInvitation).where(
            RoomInvitation.room_id == room_id, RoomInvitation.invited_user_id == user.id
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invitation not found")

    ban = await db.execute(select(RoomBan).where(RoomBan.room_id == room_id, RoomBan.user_id == user.id))
    if ban.scalar_one_or_none():
        raise HTTPException(403, "You are banned from this room")

    existing = await db.execute(select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user.id))
    if not existing.scalar_one_or_none():
        db.add(RoomMember(room_id=room_id, user_id=user.id, role=RoomMemberRole.member))
    await db.delete(inv)
    await db.commit()
    return {"ok": True}


@router.get("/invitations/mine")
async def my_invitations(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(RoomInvitation, Room)
        .join(Room, RoomInvitation.room_id == Room.id)
        .where(RoomInvitation.invited_user_id == user.id)
    )
    rows = result.all()
    return [
        {"invitation_id": inv.id, "room_id": r.id, "room_name": r.name, "created_at": inv.created_at}
        for inv, r in rows
    ]
