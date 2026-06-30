from fastapi import APIRouter, Depends
from pydantic import BaseModel
from dashboard.auth import get_db_path
from db.operations import list_keywords, add_keyword, update_keyword, delete_keyword

router = APIRouter()


class KeywordIn(BaseModel):
    phrase: str


@router.get("/api/keywords")
async def get_keywords(db_path: str = Depends(get_db_path)):
    return await list_keywords(db_path)


@router.post("/api/keywords")
async def create_keyword(body: KeywordIn, db_path: str = Depends(get_db_path)):
    await add_keyword(db_path, body.phrase.strip())
    return {"status": "ok"}


@router.put("/api/keywords/{keyword_id}")
async def edit_keyword(keyword_id: int, body: KeywordIn, db_path: str = Depends(get_db_path)):
    await update_keyword(db_path, keyword_id, body.phrase.strip())
    return {"status": "ok"}


@router.delete("/api/keywords/{keyword_id}")
async def remove_keyword(keyword_id: int, db_path: str = Depends(get_db_path)):
    await delete_keyword(db_path, keyword_id)
    return {"status": "ok"}
