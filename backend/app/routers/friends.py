from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Friendship, FriendshipStatus, User, UserBan
from app.presence import get_presence_many
from app.schemas import FriendOut, FriendRequestCreate, FriendshipOut

router = APIRouter(prefix="/api/friends", tags=["friends"])


def _fs_to_out(fs: Friendship, requester: User, recipient: User) -> FriendshipOut:
    return FriendshipOut(
        id=fs.id,
        requester_id=fs.requester_id,
        requester_username=requester.username,
        recipient_id=fs.recipient_id,
        recipient_username=recipient.username,
        status=fs.status,
        message=fs.message,
        created_at=fs.created_at,
    )


@router.get("", response_model=list[FriendOut])
async def list_friends(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == FriendshipStatus.accepted,
            (Friendship.requester_id == user.id) | (Friendship.recipient_id == user.id),
        )
    )
    friendships = result.scalars().all()
    out = []
    for fs in friendships:
        other_id = fs.recipient_id if fs.requester_id == user.id else fs.requester_id
        r = await db.execute(select(User).where(User.id == other_id))
        other = r.scalar_one_or_none()
        if other:
            out.append(FriendOut(user_id=other.id, username=other.username))
    if out:
        presence_map = await get_presence_many([f.user_id for f in out])
        for f in out:
            f.presence = presence_map.get(f.user_id, "offline")
    return out


@router.get("/requests", response_model=list[FriendshipOut])
async def list_requests(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == FriendshipStatus.pending,
            (Friendship.requester_id == user.id) | (Friendship.recipient_id == user.id),
        )
    )
    friendships = result.scalars().all()
    out = []
    for fs in friendships:
        r1 = await db.execute(select(User).where(User.id == fs.requester_id))
        r2 = await db.execute(select(User).where(User.id == fs.recipient_id))
        req = r1.scalar_one_or_none()
        rec = r2.scalar_one_or_none()
        if req and rec:
            out.append(_fs_to_out(fs, req, rec))
    return out


@router.post("/requests", response_model=FriendshipOut, status_code=201)
async def send_friend_request(
    body: FriendRequestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(User).where(User.username == body.username))
    target = r.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == user.id:
        raise HTTPException(400, "Cannot befriend yourself")

    ban = await db.execute(
        select(UserBan).where(
            ((UserBan.banner_id == user.id) & (UserBan.banned_id == target.id))
            | ((UserBan.banner_id == target.id) & (UserBan.banned_id == user.id))
        )
    )
    if ban.scalar_one_or_none():
        raise HTTPException(400, "Cannot send request — ban in effect")

    existing = await db.execute(
        select(Friendship).where(
            ((Friendship.requester_id == user.id) & (Friendship.recipient_id == target.id))
            | ((Friendship.requester_id == target.id) & (Friendship.recipient_id == user.id))
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Friend request already exists")

    fs = Friendship(requester_id=user.id, recipient_id=target.id, message=body.message)
    db.add(fs)
    await db.commit()
    await db.refresh(fs)

    from app.ws_manager import manager
    await manager.send_to_user(target.id, {
        "type": "friend.request",
        "friendship": _fs_to_out(fs, user, target).model_dump(mode="json"),
    })

    return _fs_to_out(fs, user, target)


@router.put("/requests/{request_id}")
async def respond_to_request(
    request_id: str,
    action: str,  # "accept" or "reject"
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(Friendship.id == request_id, Friendship.recipient_id == user.id)
    )
    fs = result.scalar_one_or_none()
    if not fs:
        raise HTTPException(404, "Request not found")

    if action == "accept":
        fs.status = FriendshipStatus.accepted
        await db.commit()

        r = await db.execute(select(User).where(User.id == fs.requester_id))
        r.scalar_one_or_none()

        from app.ws_manager import manager
        await manager.send_to_user(fs.requester_id, {"type": "friend.accepted", "by_username": user.username})
        return {"ok": True, "status": "accepted"}
    elif action == "reject":
        await db.delete(fs)
        await db.commit()
        return {"ok": True, "status": "rejected"}
    else:
        raise HTTPException(400, "Invalid action")


@router.delete("/{user_id}")
async def remove_friend(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == FriendshipStatus.accepted,
            ((Friendship.requester_id == user.id) & (Friendship.recipient_id == user_id))
            | ((Friendship.requester_id == user_id) & (Friendship.recipient_id == user.id)),
        )
    )
    fs = result.scalar_one_or_none()
    if fs:
        await db.delete(fs)
        await db.commit()
    return {"ok": True}


@router.post("/bans/{user_id}")
async def ban_user(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id == user.id:
        raise HTTPException(400, "Cannot ban yourself")

    # Remove friendship
    result = await db.execute(
        select(Friendship).where(
            ((Friendship.requester_id == user.id) & (Friendship.recipient_id == user_id))
            | ((Friendship.requester_id == user_id) & (Friendship.recipient_id == user.id))
        )
    )
    fs = result.scalar_one_or_none()
    if fs:
        await db.delete(fs)

    existing_ban = await db.execute(
        select(UserBan).where(UserBan.banner_id == user.id, UserBan.banned_id == user_id)
    )
    if not existing_ban.scalar_one_or_none():
        db.add(UserBan(banner_id=user.id, banned_id=user_id))

    await db.commit()
    return {"ok": True}


@router.delete("/bans/{user_id}")
async def unban_user(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserBan).where(UserBan.banner_id == user.id, UserBan.banned_id == user_id)
    )
    ban = result.scalar_one_or_none()
    if ban:
        await db.delete(ban)
        await db.commit()
    return {"ok": True}


@router.get("/bans", response_model=list)
async def list_bans(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserBan).where(UserBan.banner_id == user.id))
    bans = result.scalars().all()
    out = []
    for ban in bans:
        r = await db.execute(select(User).where(User.id == ban.banned_id))
        banned_user = r.scalar_one_or_none()
        if banned_user:
            out.append({"user_id": banned_user.id, "username": banned_user.username})
    return out
