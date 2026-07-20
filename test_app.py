import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


from app.app import app
from app.db import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def override_get_db():
    async with TestingSessionLocal() as db:
        yield db


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_register_success(client):
    await client.post('/register', json={"username": "carol", "password": "pass123"})
    response = await client.post('/login', data={"username": "carol", "password": "pass123"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    await client.post("/register", json={"username": "bob", "password": "pass123"})
    response = await client.post("/register", json={"username": "bob", "password": "pass456"})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/register", json={"username": "carol", "password": "correctpass"})
    response = await client.post("/login", data={"username": "carol", "password": "correctpass"})
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/register", json={"username": "dave", "password": "correctpass"})
    response = await client.post("/login", data={"username": "dave", "password": "wrongpass"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_register_no_password_leak(client):
    response = await client.post("/register", json={"username": "eve", "password": "secret123"})
    assert "hashed_password" not in response.json()

@pytest.mark.asyncio
async def test_create_todo_required_authentication(client):
    response = await client.post("/create_todo", json={"title" : "test todo", "description" : "desc"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_todo_with_authentication(client):
    await client.post("/register", json={"username": "carol", "password": "pass123"})
    login_response = await client.post("/login", data={"username": "carol", "password": "pass123"})
    token = login_response.json()["access_token"]

    response = await client.post(
        "/create_todo",
        json={"title" : "test todo", "description" : "desc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "test todo"

@pytest.mark.asyncio
async def test_get_todo_by_id_not_found(client):
    await client.post("/register", json={"username": "greg", "password": "pass123"})
    login_response = await client.post("/login", data={"username": "greg", "password": "pass123"})
    token = login_response.json()["access_token"]

    response = await client.get(
        "/todos/9999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_user_cannot_access_others_todo(client):
    # User A yaratadi
    await client.post("/register", json={"username": "userA", "password": "pass123"})
    login_a = await client.post("/login", data={"username": "userA", "password": "pass123"})
    token_a = login_a.json()["access_token"]

    create_response = await client.post(
        "/create_todo",
        json={"title": "A ning maxfiy todo'si", "description": "desc"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    todo_id = create_response.json()["id"]

    # User B login qiladi
    await client.post("/register", json={"username": "userB", "password": "pass456"})
    login_b = await client.post("/login", data={"username": "userB", "password": "pass456"})
    token_b = login_b.json()["access_token"]

    # User B, A'ning todo'sini ko'rishga urinadi
    response = await client.get(
        f"/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_todo_success(client):
    await client.post("/register", json={"username": "helen", "password": "pass123"})
    login_response = await client.post("/login", data={"username": "helen", "password": "pass123"})
    token = login_response.json()["access_token"]

    create_response = await client.post(
        "/create_todo",
        json={"title": "old title", "description": "desc"},
        headers={"Authorization": f"Bearer {token}"}
    )
    todo_id = create_response.json()["id"]

    update_response = await client.put(
        f"/todos/{todo_id}",
        json={"title": "new title"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "new title"


@pytest.mark.asyncio
async def test_delete_todo_success(client):
    await client.post("/register", json={"username": "ivan", "password": "pass123"})
    login_response = await client.post("/login", data={"username": "ivan", "password": "pass123"})
    token = login_response.json()["access_token"]

    create_response = await client.post(
        "/create_todo",
        json={"title": "to be deleted", "description": "desc"},
        headers={"Authorization": f"Bearer {token}"}
    )
    todo_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_response.status_code == 200

    get_response = await client.get(
        f"/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_token(client):
    response = await client.get(
        "/todo",
        headers={"Authorization": "Bearer noto'g'ri_token_bu_yerda"}
    )
    assert response.status_code == 401