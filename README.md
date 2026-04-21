# ChatApp — Agentic Development Hackathon

A real-time web chat application built for the DataArt Agentic Development Hackathon.

## Features

- **Authentication**: registration, login, multi-session management, password change
- **Public & private rooms**: create, join, leave, search catalog; role-based moderation (owner / admin / member)
- **Room moderation**: ban/unban users, promote/demote admins, invite to private rooms
- **Personal messaging (DMs)**: one-to-one dialogs between friends
- **Contacts/friends**: send/accept/reject requests, block users
- **File & image sharing**: upload attachments (20 MB limit, 3 MB for images), access-controlled download
- **Real-time**: WebSocket-based delivery with Redis pub/sub fan-out across instances
- **Presence**: online / AFK / offline tracking per browser tab (heartbeat every 30 s)
- **Unread counts**: per room and per dialog, reset on open

## Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Backend   | Python 3.11, FastAPI, SQLAlchemy 2.0 (async)   |
| Database  | PostgreSQL 15                                   |
| Cache/RT  | Redis 7 (pub/sub + presence)                    |
| Frontend  | React 18, TypeScript, Vite, Tailwind, Zustand   |
| Server    | nginx (static files + reverse proxy)            |

## Quick Start (Docker / Podman)

The project ships as four services defined in `docker-compose.yml`:
`db` (PostgreSQL), `redis`, `backend` (FastAPI on :8000), `frontend` (nginx on :80).

> **Note**: Docker Desktop requires a license. Use one of the free alternatives below.

### Rancher Desktop / Podman Desktop

1. Install [Rancher Desktop](https://rancherdesktop.io/) **or** [Podman Desktop](https://podman-desktop.io/).
2. Enable the `docker` compatibility shim (Rancher: *Preferences → Container Engine → dockerd*; Podman: enabled by default via `podman-compose`).

```bash
# clone
git clone <repo-url>
cd Agentic-Development-Hackaton

# copy env template and set your secret key
cp .env.example .env

# start all services (use 'docker compose' or 'podman-compose')
docker compose up --build
# OR
podman-compose up --build
```

Open **http://localhost** in your browser.

### Environment variables

Copy `.env.example` to `.env` before first run:

| Variable         | Default                                          | Description                |
|------------------|--------------------------------------------------|----------------------------|
| `DATABASE_URL`   | `postgresql+asyncpg://chat:chat@db:5432/chatdb`  | PostgreSQL connection       |
| `REDIS_URL`      | `redis://redis:6379`                             | Redis connection            |
| `SECRET_KEY`     | `change-me-in-production`                        | Random secret for tokens    |
| `UPLOAD_DIR`     | `/uploads`                                       | File upload directory       |

## Local Development (without containers)

### Prerequisites

- Python 3.11+
- Node 20+
- PostgreSQL 15 running locally
- Redis 7 running locally

### Backend

```bash
cd backend

# install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# install dependencies and run
export DATABASE_URL="postgresql+asyncpg://chat:chat@localhost:5432/chatdb"
export REDIS_URL="redis://localhost:6379"

uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # Vite dev server on http://localhost:5173
```

The Vite dev proxy forwards `/api` and `/ws` to `http://localhost:8000`.

## Running Tests

```bash
cd backend
# tests use an in-memory SQLite DB — no PostgreSQL or Redis needed
uv run --extra dev pytest tests/ -v
```

All 17 tests cover: auth flows, room management, and message CRUD.

## Code Quality

```bash
cd backend
uv run --extra dev ruff check app/    # lint
uv run --extra dev ruff format app/   # format
```

## Architecture

```
browser
  │  HTTP /api/*  ──►  nginx  ──►  FastAPI (backend:8000)
  │  WS  /ws      ──►  nginx  ──►  FastAPI WebSocket endpoint
  │
  └── Static files served by nginx (React SPA)

FastAPI
  ├── Routers: auth, rooms, messages, friends, files, users
  ├── WebSocket manager (per-connection state + Redis pub/sub)
  ├── Presence tracker (Redis hash per user, per-tab TTL)
  └── SQLAlchemy async ORM → PostgreSQL

Redis
  ├── ws:room:{id}       — broadcast to all room subscribers
  ├── ws:user:{id}       — direct message to a user
  ├── presence_updates   — presence change events
  └── user_tabs:{id}     — active tab registry (TTL 300s)
```

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── config.py       # pydantic-settings
│   │   ├── database.py     # SQLAlchemy async engine
│   │   ├── models.py       # all ORM models
│   │   ├── schemas.py      # Pydantic request/response schemas
│   │   ├── deps.py         # auth dependencies
│   │   ├── security.py     # bcrypt + token generation
│   │   ├── presence.py     # Redis presence tracking
│   │   ├── ws_manager.py   # WebSocket connection manager
│   │   ├── main.py         # FastAPI app + WebSocket endpoint
│   │   └── routers/        # auth, rooms, messages, friends, files, users
│   ├── tests/              # pytest tests
│   └── pyproject.toml      # deps + ruff + pytest config
├── frontend/
│   ├── src/
│   │   ├── api/            # fetch client
│   │   ├── store/          # Zustand global state
│   │   ├── hooks/          # useWebSocket
│   │   ├── components/     # chat, rooms, friends, admin, layout
│   │   └── pages/          # Login, Register, ChatLayout
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── .env.example
```
