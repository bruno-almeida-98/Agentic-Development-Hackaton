import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient, email: str, username: str, password: str = "password"):
    await client.post("/api/auth/register", json={
        "email": email, "username": username, "password": password, "confirm_password": password
    })
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()


@pytest.mark.asyncio
async def test_create_public_room(client: AsyncClient):
    await register_and_login(client, "room@test.com", "roomuser")
    res = await client.post("/api/rooms", json={"name": "test-room", "description": "A test room", "visibility": "public"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "test-room"
    assert data["visibility"] == "public"


@pytest.mark.asyncio
async def test_room_name_unique(client: AsyncClient):
    await register_and_login(client, "r2@test.com", "r2user")
    await client.post("/api/rooms", json={"name": "unique-room", "description": "", "visibility": "public"})
    res = await client.post("/api/rooms", json={"name": "unique-room", "description": "", "visibility": "public"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_join_and_leave_room(client: AsyncClient):
    await register_and_login(client, "owner@test.com", "owner")
    room_res = await client.post("/api/rooms", json={"name": "joinable", "visibility": "public", "description": ""})
    room_id = room_res.json()["id"]

    # New user joins
    client2 = client  # same client for simplicity, use different session
    await client.post("/api/auth/logout")
    await register_and_login(client, "joiner@test.com", "joiner")
    res = await client.post(f"/api/rooms/{room_id}/join")
    assert res.status_code == 200

    res = await client.post(f"/api/rooms/{room_id}/leave")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_list_my_rooms(client: AsyncClient):
    await register_and_login(client, "my@test.com", "myuser")
    await client.post("/api/rooms", json={"name": "my-room-1", "visibility": "public", "description": ""})
    await client.post("/api/rooms", json={"name": "my-room-2", "visibility": "private", "description": ""})
    res = await client.get("/api/rooms/mine")
    assert res.status_code == 200
    names = [r["name"] for r in res.json()]
    assert "my-room-1" in names
    assert "my-room-2" in names


@pytest.mark.asyncio
async def test_delete_room_owner_only(client: AsyncClient):
    await register_and_login(client, "del@test.com", "deluser")
    room_res = await client.post("/api/rooms", json={"name": "del-room", "visibility": "public", "description": ""})
    room_id = room_res.json()["id"]

    # Second user cannot delete
    await client.post("/api/auth/logout")
    await register_and_login(client, "other@test.com", "otheruser")
    res = await client.delete(f"/api/rooms/{room_id}")
    assert res.status_code == 403
