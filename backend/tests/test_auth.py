import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    res = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123",
        "confirm_password": "password123",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    body = {"email": "dup@example.com", "username": "user1", "password": "pw", "confirm_password": "pw"}
    await client.post("/api/auth/register", json=body)
    body["username"] = "user2"
    res = await client.post("/api/auth/register", json=body)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "a@a.com", "username": "same", "password": "pw", "confirm_password": "pw"})
    res = await client.post("/api/auth/register", json={"email": "b@b.com", "username": "same", "password": "pw", "confirm_password": "pw"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_login_and_me(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "login@test.com", "username": "loginuser",
        "password": "mypassword", "confirm_password": "mypassword"
    })
    res = await client.post("/api/auth/login", json={"email": "login@test.com", "password": "mypassword"})
    assert res.status_code == 200

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "loginuser"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "fail@test.com", "username": "failuser",
        "password": "correct", "confirm_password": "correct"
    })
    res = await client.post("/api/auth/login", json={"email": "fail@test.com", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "lo@lo.com", "username": "logoutuser", "password": "pw", "confirm_password": "pw"})
    await client.post("/api/auth/login", json={"email": "lo@lo.com", "password": "pw"})
    res = await client.post("/api/auth/logout")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_password_mismatch(client: AsyncClient):
    res = await client.post("/api/auth/register", json={
        "email": "mismatch@test.com", "username": "mismatch",
        "password": "abc", "confirm_password": "xyz"
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_unauthenticated_me(client: AsyncClient):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401
