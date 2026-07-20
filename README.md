# To-Do List API

A simple, async REST API for managing personal to-do items, built with **FastAPI**, **SQLAlchemy (async)**, **PostgreSQL**, and **JWT authentication**. Each user can only see and manage their own to-dos.

## Features

- User registration and login with hashed passwords (bcrypt)
- JWT-based authentication (Bearer token)
- Full CRUD for to-do items (create, read, update, delete)
- Per-user data isolation — a user cannot access another user's to-dos
- Fully asynchronous request handling (async SQLAlchemy + asyncpg)
- PostgreSQL database, run via Docker Compose
- Async test suite with pytest, pytest-asyncio, and httpx

## Tech Stack

| Component      | Technology                          |
|-----------------|--------------------------------------|
| Framework       | FastAPI                              |
| Database        | PostgreSQL                           |
| ORM             | SQLAlchemy 2.0 (async)               |
| DB Driver       | asyncpg                              |
| Auth            | JWT (python-jose) + OAuth2PasswordBearer |
| Password Hashing| passlib (bcrypt)                     |
| Validation      | Pydantic v2                          |
| Testing         | pytest, pytest-asyncio, httpx        |
| Package Manager | uv                                   |

## Project Structure

```
To-Do List API/
├── app/
│   ├── app.py         # FastAPI app, routes (register, login, todo CRUD)
│   ├── auth.py         # Password hashing, JWT creation/validation, current-user dependency
│   ├── db.py            # Async engine/session setup, get_db dependency
│   ├── db_models.py     # SQLAlchemy ORM models (User, ToDoDB)
│   └── models.py        # Pydantic schemas (request/response bodies)
├── main.py               # Uvicorn entry point
├── test_app.py           # Async test suite
├── docker-compose.yml     # PostgreSQL container
├── pyproject.toml        # Project dependencies
└── .env                    # Environment variables (not committed)
```

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd "To-Do List API"
uv sync
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
ALGORITHMS=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=postgresql+asyncpg://todouser:todopass123@localhost:5432/tododb
TEST_DATABASE_URL=postgresql+asyncpg://todouser:todopass123@localhost:5432/test_tododb
```

Generate a strong `SECRET_KEY`, for example:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start PostgreSQL

```bash
docker compose up -d
```

This starts a Postgres container with the `tododb` database (credentials match `docker-compose.yml`). If you plan to run the test suite, also create the test database:

```bash
docker exec -it todo_postgres psql -U todouser -d tododb -c "CREATE DATABASE test_tododb;"
```

### 4. Run the API

```bash
uv run main.py
```

The API will be available at `http://localhost:8000`. Interactive docs (Swagger UI) at `http://localhost:8000/docs`.

## Running Tests

```bash
uv run pytest test_app.py -v
```

Tests run against `TEST_DATABASE_URL` and create/drop all tables around each test for isolation.

## API Endpoints

| Method | Endpoint            | Auth required | Description                          |
|--------|----------------------|:--------------:|----------------------------------------|
| POST   | `/register`           | No             | Create a new user account             |
| POST   | `/login`               | No             | Log in, returns a JWT access token    |
| GET    | `/todo`                 | Yes            | List all to-dos owned by the current user |
| POST   | `/create_todo`         | Yes            | Create a new to-do                    |
| GET    | `/todos/{todo_id}`     | Yes            | Get a single to-do by ID (own only)   |
| PUT    | `/todos/{todo_id}`     | Yes            | Update a to-do (own only)             |
| DELETE | `/todos/{todo_id}`     | Yes            | Delete a to-do (own only)             |

## Authentication Flow

1. **Register** a user:

   ```bash
   curl -X POST http://localhost:8000/register \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "strongpassword"}'
   ```

2. **Log in** to get a token (note: this endpoint expects form data, not JSON):

   ```bash
   curl -X POST http://localhost:8000/login \
     -d "username=alice&password=strongpassword"
   ```

   Response:

   ```json
   { "access_token": "<jwt-token>", "token_type": "bearer" }
   ```

3. Use the token to access protected endpoints:

   ```bash
   curl -X POST http://localhost:8000/create_todo \
     -H "Authorization: Bearer <jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"title": "Buy groceries", "description": "Milk, eggs, bread"}'
   ```

## Notes

- Passwords are never returned in API responses (`UserOut` response model excludes `hashed_password`).
- To-dos are scoped to the authenticated user via `owner_id`; requesting another user's to-do returns `404 Not Found` (not `403`), to avoid leaking whether the resource exists.
- `.env` and `.claude/settings.local.json` are excluded from version control — never commit real secrets.
