import pytest
from httpx import AsyncClient


async def setup_user(client: AsyncClient, email: str, username: str):
    await client.post("/api/auth/register", json={
        "email": email, "username": username, "password": "pw", "confirm_password": "pw"
    })
    await client.post("/api/auth/login", json={"email": email, "password": "pw"})


@pytest.mark.asyncio
async def test_send_and_get_room_messages(client: AsyncClient):
    await setup_user(client, "msg@test.com", "msguser")
    room = await client.post("/api/rooms", json={"name": "msg-room", "visibility": "public", "description": ""})
    room_id = room.json()["id"]

    send = await client.post(f"/api/rooms/{room_id}/messages", json={"content": "Hello world"})
    assert send.status_code == 201
    assert send.json()["content"] == "Hello world"

    msgs = await client.get(f"/api/rooms/{room_id}/messages")
    assert msgs.status_code == 200
    assert len(msgs.json()) == 1


@pytest.mark.asyncio
async def test_message_too_long(client: AsyncClient):
    await setup_user(client, "long@test.com", "longuser")
    room = await client.post("/api/rooms", json={"name": "long-room", "visibility": "public", "description": ""})
    room_id = room.json()["id"]
    long_content = "x" * (3 * 1024 + 1)
    res = await client.post(f"/api/rooms/{room_id}/messages", json={"content": long_content})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_edit_own_message(client: AsyncClient):
    await setup_user(client, "edit@test.com", "edituser")
    room = await client.post("/api/rooms", json={"name": "edit-room", "visibility": "public", "description": ""})
    room_id = room.json()["id"]
    msg = await client.post(f"/api/rooms/{room_id}/messages", json={"content": "original"})
    msg_id = msg.json()["id"]

    edited = await client.put(f"/api/messages/{msg_id}", json={"content": "edited"})
    assert edited.status_code == 200
    assert edited.json()["content"] == "edited"
    assert edited.json()["edited_at"] is not None


@pytest.mark.asyncio
async def test_delete_message(client: AsyncClient):
    await setup_user(client, "delmsg@test.com", "delmsguser")
    room = await client.post("/api/rooms", json={"name": "delmsg-room", "visibility": "public", "description": ""})
    room_id = room.json()["id"]
    msg = await client.post(f"/api/rooms/{room_id}/messages", json={"content": "delete me"})
    msg_id = msg.json()["id"]

    res = await client.delete(f"/api/messages/{msg_id}")
    assert res.status_code == 200

    msgs = await client.get(f"/api/rooms/{room_id}/messages")
    deleted = next((m for m in msgs.json() if m["id"] == msg_id), None)
    assert deleted is not None
    assert deleted["is_deleted"] is True
