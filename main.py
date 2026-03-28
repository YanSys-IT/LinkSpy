from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
from sqlalchemy import select
import random
import string

from database import init_db, get_db
from models import Link


@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)


class LinkCreate(BaseModel):
    original_url: str


def generate_short_code():
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=6))


@app.get("/")
def hello():
    return {"message": "LinkSpy is alive!"}


@app.post("/links")
async def create_link(data: LinkCreate, db=Depends(get_db)):
    short_code = generate_short_code()
    link = Link(short_code=short_code, original_url=data.original_url)
    db.add(link)
    await db.commit()
    return {"original_url": data.original_url, "short_code": short_code}


@app.get("/{short_code}")
async def redirect(short_code: str, db=Depends(get_db)):
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return RedirectResponse(url=link.original_url)
