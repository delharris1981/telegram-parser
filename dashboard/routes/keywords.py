from fastapi import APIRouter
from pydantic import BaseModel
import config
from db.operations import list_keywords, add_keyword, update_keyword, delete_keyword

router = APIRouter()


class KeywordIn(BaseModel):
    phrase: str


@router.get("/api/keywords")
async def get_keywords():
    return await list_keywords(config.DB_PATH)


@router.post("/api/keywords")
async def create_keyword(body: KeywordIn):
    await add_keyword(config.DB_PATH, body.phrase.strip())
    return {"status": "ok"}


@router.put("/api/keywords/{keyword_id}")
async def edit_keyword(keyword_id: int, body: KeywordIn):
    await update_keyword(config.DB_PATH, keyword_id, body.phrase.strip())
    return {"status": "ok"}


@router.delete("/api/keywords/{keyword_id}")
async def remove_keyword(keyword_id: int):
    await delete_keyword(config.DB_PATH, keyword_id)
    return {"status": "ok"}
