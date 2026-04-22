# ChatApp — Development Story

DataArt Agentic Development Hackathon · 2026-04-21 / 2026-04-22

---

## Session 1 — Initial build

### Prompt — 2026-04-21 (morning)

Build a full real-time chat application for the hackathon. Requirements: auth, public/private rooms, DMs, friends, file sharing, presence, unread counts. Stack: FastAPI + PostgreSQL + Redis + React + TypeScript + Tailwind + Docker. Consider the documentation as the main guide and use the transciption file as an second source. Create file test to validate all the implementation.

**Claude built:**
- FastAPI backend with SQLAlchemy 2.0 async ORM
- PostgreSQL models: User, Session, Room, RoomMember, Dialog, Message, Friendship, UnreadCount
- Redis presence system with per-tab TTL tracking
- WebSocket manager with Redis pub/sub fan-out
- React 18 + Vite + Zustand frontend
- All REST routes: auth, rooms, messages, friends, files, users
- nginx reverse proxy + Docker Compose setup

---

## Session 2 — Bug fixes and real-time issues

### Prompt — 2026-04-21

> "AFK is also broken — sometimes I'm online but it shows me as offline"

**Root cause:** Chrome throttles background tab `setInterval` from 30s to 60–120s. With `TAB_TTL=120s`, the Redis `tab_active` key expired between throttled heartbeats.

**Fix:**
- `presence.py`: `TAB_TTL` 120s → 300s
- `tab_connect` now always publishes presence on connect (not only on status change)
- `useWebSocket.ts`: `trackActivity` sends immediate heartbeat when user returns after AFK

---

### Prompt — 2026-04-21

> "Group room message notifications are not showing up"

**Iteration 1:** Added Redis fallback in `ws_manager.send_to_user` — did not fix.

**Iteration 2:** Added `addMessage` optimistically in `ChatWindow` on HTTP POST — did not fix.

**Iteration 3 (root cause):** SQLAlchemy `expire_on_commit=True` expires ORM objects after `db.commit()`. Accessing `user.username` after commit in async context breaks the WS send loop silently.

**Fix:** Capture `sender_username = user.username` and `sender_id = user.id` **before** `db.commit()` in `messages.py`. Applied to `send_room_message`, `send_direct_message`, and `edit_message`.

---

### Prompt — 2026-04-21

> "Still not working — I had to refresh the page to see notifications"

**Fix:** Added 2-second polling loop in `ChatLayout.tsx` as reliable fallback for unread counts (WS alone was not enough for all cases).

---

### Prompt — 2026-04-21

> "It takes a few seconds but it's updating now"
> "Can you reduce that time? To 2 seconds?"
> "That's good now"

Polling interval confirmed working at 2s.

---

### Prompt — 2026-04-21

> "We already tested all of these [AFK, paste, moderation, invite, block, sessions]. Everything working"

All features validated by manual testing.

---

## Session 3 — Pre-commit cleanup and security review

### Prompt — 2026-04-21

> "Review the changed files and discard anything that is not essential to the application's functionality"

**Claude reviewed and removed:**
- All `console.log / console.debug / console.warn` from frontend WS hook
- All `logger.debug` lines from backend (kept `logger.warning` and `logger.info`)
- `ws.onerror` handler (redundant with `onclose`)

---

### Prompt — 2026-04-21

> "Also check that we are not committing any keys or anything that could be a security vulnerability"

**Security review result:**
- No real secrets in tracked files
- `SECRET_KEY` in `docker-compose.yml` is a placeholder for local dev — acceptable for hackathon
- `.env` is gitignored; `.env.example` has no real values
- `backend/uploads/` test files were NOT gitignored — fixed by adding `backend/uploads/*` to `.gitignore`

---

### Prompt — 2026-04-21

> "Looking at the requirements and how the system works, did we meet all of them?"

Full requirements checklist reviewed. All items confirmed implemented except email-based password reset (requires external SMTP). User decided to skip it.

---

## Session 4 — Final commit and push

### Prompt — 2026-04-22

> "Yes, make sure everything is correct and ready, including for other people to test — review the docker-compose"

**Final pre-commit fixes:**
- `README.md`: corrected "TTL 90s" → "TTL 300s" and removed stale `requirements.txt` reference
- `.gitignore`: added `backend/uploads/*` + `!backend/uploads/.gitkeep`
- Created `uploads/.gitkeep` and `backend/uploads/.gitkeep` to track empty directories
- Removed `backend/requirements.txt` (redundant with `pyproject.toml` after uv migration)

**Commit:** `82a7dfa` — 66 files, 9914 insertions  
**Pushed:** `main` → `github.com/bruno-almeida-98/Agentic-Development-Hackaton`

---

## Key technical lessons

| Problem | Root cause | Fix |
|---|---|---|
| Presence showing offline | Chrome background tab throttles `setInterval` 30s → 120s; TTL=120s expired | `TAB_TTL` 120s → 300s |
| Group room notifications missing | SQLAlchemy `expire_on_commit=True` expired `user` object after `db.commit()` | Capture username/id before commit |
| Add friend button invisible | Tailwind JIT didn't scan `opacity-0 group-hover:opacity-100` dynamic classes | Remove opacity classes; always visible |
| Unread counts unreliable via WS | WS delivery not guaranteed under all conditions | 2s polling fallback in `ChatLayout` |
