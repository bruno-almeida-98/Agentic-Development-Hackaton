from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import UnreadCount, User
from app.schemas import UnreadOut, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/search", response_model=list[UserOut])
async def search_users(
    q: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User).where(User.username.ilike(f"%{q}%"), User.id != user.id).limit(20)
    )
    return result.scalars().all()


@router.get("/unread", response_model=list[UnreadOut])
async def get_unread(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UnreadCount).where(UnreadCount.user_id == user.id, UnreadCount.count > 0)
    )
    counts = result.scalars().all()
    return [UnreadOut(room_id=u.room_id, dialog_id=u.dialog_id, count=u.count) for u in counts]


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user
