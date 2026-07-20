from pydantic import BaseModel, ConfigDict
from typing import Optional


class ToDo(BaseModel):
    id: int
    title: str
    description: str = ""
    completed: bool = False

class ToDoCreate(BaseModel):
    title: str
    description: str = ""
    completed: bool = False

class ToDoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class UserOut(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    username: str
    password: str