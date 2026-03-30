from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
from sqlalchemy import select
import random
import string

from database import init_db, get_db
from models import Link, User
from auth import hash_password, verify_password, create_access_token, decode_access_token


@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class LinkCreate(BaseModel):
    original_url: str


class UserCreate(BaseModel):
    username: str
    password: str


def generate_short_code():
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=6))


async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.get("/")
def hello():
    return {"message": "LinkSpy is alive!"}


@app.post("/register")
async def register(data: UserCreate, db=Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(username=data.username, hashed_password=hash_password(data.password))
    db.add(user)
    await db.commit()
    return {"message": "User created successfully"}


@app.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/links")
async def create_link(data: LinkCreate, db=Depends(get_db), current_user: User = Depends(get_current_user)):
    short_code = generate_short_code()
    link = Link(short_code=short_code, original_url=data.original_url, owner_id=current_user.id)
    db.add(link)
    await db.commit()
    return {"original_url": data.original_url, "short_code": short_code}


@app.get("/links")
async def get_my_links(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Link).where(Link.owner_id == current_user.id))
    links = result.scalars().all()
    return [{"short_code": l.short_code, "original_url": l.original_url, "click_count": l.click_count} for l in links]


@app.delete("/links/{short_code}")
async def delete_link(short_code: str, db=Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your link")
    await db.delete(link)
    await db.commit()
    return {"message": "Link deleted"}


@app.get("/{short_code}")
async def redirect(short_code: str, db=Depends(get_db)):
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    link.click_count += 1
    await db.commit()
    return RedirectResponse(url=link.original_url)
