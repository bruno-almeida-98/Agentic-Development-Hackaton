import os
from unittest.mock import AsyncMock, MagicMock, patch

# Must be set before any app imports so pydantic-settings picks it up
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DB_URL, echo=False, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db

# Patch ws_manager so tests don't need Redis
_mock_manager = MagicMock()
_mock_manager.startup = AsyncMock()
_mock_manager.shutdown = AsyncMock()
_mock_manager.broadcast_room = AsyncMock()
_mock_manager.broadcast_dialog = AsyncMock()
_mock_manager.send_to_user = AsyncMock()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    with patch("app.main.manager", _mock_manager), \
         patch("app.ws_manager.manager", _mock_manager):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(setup_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
