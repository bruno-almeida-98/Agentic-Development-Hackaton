
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_session, get_current_user
from app.models import Session, User
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    UserOut,
)
from app.security import generate_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if body.password != body.confirm_password:
        raise HTTPException(400, "Passwords do not match")
    if len(body.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")

    existing_email = await db.execute(select(User).where(User.email == body.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    existing_user = await db.execute(select(User).where(User.username == body.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(400, "Username already taken")

    user = User(email=body.email, username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = generate_token()
    session = Session(
        user_id=user.id,
        token=token,
        user_agent=request.headers.get("user-agent", "")[:512],
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    await db.commit()

    max_age = 60 * 60 * 24 * 365 if body.keep_signed_in else None
    response.set_cookie(
        key=settings.SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=max_age,
    )
    return {"id": user.id, "username": user.username, "email": user.email}


@router.post("/logout")
async def logout(
    response: Response,
    current_session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    await db.delete(current_session)
    await db.commit()
    response.delete_cookie(settings.SESSION_COOKIE)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    chat_session: str | None = Cookie(default=None, alias=settings.SESSION_COOKIE),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.user_id == user.id))
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        out.append(
            SessionOut(
                id=s.id,
                user_agent=s.user_agent,
                ip_address=s.ip_address,
                created_at=s.created_at,
                last_seen=s.last_seen,
                is_current=(s.token == chat_session),
            )
        )
    return out


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id, Session.user_id == user.id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")
    await db.delete(session)
    await db.commit()
    return {"ok": True}


@router.put("/password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Wrong current password")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}


@router.post("/password-reset")
async def request_password_reset(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    # For hackathon: just return a reset token directly (no email)
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "If that email exists, a reset link was sent"}
    reset_token = generate_token()
    # Store token in session table reusing it (simple approach for hackathon)
    # In production use a dedicated table with TTL
    session = Session(user_id=user.id, token=f"reset_{reset_token}", user_agent="password-reset")
    db.add(session)
    await db.commit()
    return {"message": "If that email exists, a reset link was sent", "debug_token": reset_token}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.token == f"reset_{token}"))
    reset_session = result.scalar_one_or_none()
    if not reset_session:
        raise HTTPException(400, "Invalid or expired token")

    result2 = await db.execute(select(User).where(User.id == reset_session.user_id))
    user = result2.scalar_one_or_none()
    if not user:
        raise HTTPException(400, "User not found")

    user.password_hash = hash_password(new_password)
    await db.delete(reset_session)
    await db.commit()
    return {"ok": True}


@router.delete("/account")
async def delete_account(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    from app.models import Room, RoomMember

    # Delete rooms owned by this user (cascade handles messages/files)
    owned = await db.execute(select(Room).where(Room.owner_id == user.id))
    for room in owned.scalars().all():
        await db.delete(room)

    # Remove from other rooms
    memberships = await db.execute(select(RoomMember).where(RoomMember.user_id == user.id))
    for m in memberships.scalars().all():
        await db.delete(m)

    await db.delete(user)
    await db.commit()
    response.delete_cookie(settings.SESSION_COOKIE)
    return {"ok": True}
