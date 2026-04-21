from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Session, User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    chat_session: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE),
) -> User:
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    result = await db.execute(select(Session).where(Session.token == chat_session))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    result2 = await db.execute(select(User).where(User.id == session.user_id))
    user = result2.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_current_session(
    db: AsyncSession = Depends(get_db),
    chat_session: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE),
) -> Session:
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    result = await db.execute(select(Session).where(Session.token == chat_session))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    return session
