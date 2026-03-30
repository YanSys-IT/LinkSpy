from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    short_code = Column(String, unique=True, index=True)
    original_url = Column(String)
    click_count = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
