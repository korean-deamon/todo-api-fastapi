from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager

from uvicorn import lifespan

from app.models import ToDoCreate, ToDoUpdate, UserOut, UserCreate
from app.db import engine, Base, get_db
from app.db_models import ToDoDB, User

from app.auth import hashed_password, verify_password, create_access_token, get_current_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/todo")
async def read_todo(db : AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    result = await db.execute(select(ToDoDB).filter(ToDoDB.owner_id == current_user.id))
    return result.scalars().all()

@app.post("/create_todo")
async def create_todo(
        todo: ToDoCreate,
        db: AsyncSession = Depends(get_db),
        current_user: str = Depends(get_current_user)
):
    new_todo = ToDoDB(
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        owner_id=current_user.id
    )
    db.add(new_todo)
    await db.commit()
    await db.refresh(new_todo)
    return new_todo

@app.get("/todos/{todo_id}")
async def get_todo_by_id(todo_id: int, db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    result = await db.execute(
        select(ToDoDB).filter(ToDoDB.id == todo_id, ToDoDB.owner_id == current_user.id)
    )
    todo = result.scalars().first()

    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return todo

@app.put("/todos/{todo_id}")
async def put_todo_by_id(todo_id: int, todo: ToDoUpdate, db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    result = await db.execute(select(ToDoDB).filter(ToDoDB.id == todo_id, ToDoDB.owner_id == current_user.id))
    existing_todo = result.scalars().first()
    if existing_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    todo_update = todo.model_dump(exclude_unset=True)
    for key, value in todo_update.items():
        setattr(existing_todo, key, value)

    await db.commit()
    await db.refresh(existing_todo)

    return existing_todo

@app.delete("/todos/{todo_id}")
async def delete_todo_by_id(todo_id: int, db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    result = await db.execute(select(ToDoDB).filter(ToDoDB.id == todo_id, ToDoDB.owner_id == current_user.id))
    existing_todo = result.scalars().first()
    if existing_todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await db.delete(existing_todo)
    await db.commit()

    return existing_todo

@app.post("/register", response_model=UserOut)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.username == user_in.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    new_user = User(
        username=user_in.username,
        hashed_password=hashed_password(user_in.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    access_token = create_access_token(
        data={"sub": form_data.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}