from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db import Base

class ToDoDB(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True, unique=True)
    title = Column(String)
    description = Column(String)
    completed = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    priority = Column(Integer, default=1)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, unique=True)
    username = Column(String)
    hashed_password = Column(String)
    