from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
import random
import string


app = FastAPI()
db = {}


class LinkCreate(BaseModel):
    original_url: str


def generate_short_code():
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=6))


@app.get("/")
def hello():
    return {"message": "LinkSpy is alive!"}


@app.post("/links")
def create_link(data: LinkCreate):
    short_code = generate_short_code()
    db[short_code] = data.original_url
    return {"original_url": data.original_url, "short_code": short_code}


@app.get("/{short_code}")
def redirect(short_code: str):
    if short_code not in db:
        raise HTTPException(status_code=404, detail="Link not found")
    original_url = db[short_code]
    return RedirectResponse(url=original_url)
