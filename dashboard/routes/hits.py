from fastapi import APIRouter, Depends
from dashboard.auth import get_db_path
from db.operations import list_hits, count_hits, count_keywords, count_groups
from dashboard.sanitize import sanitize

router = APIRouter()


@router.get("/api/hits")
async def get_hits(limit: int = 100, db_path: str = Depends(get_db_path)):
    hits = await list_hits(db_path, limit=limit)
    for hit in hits:
        hit["original_comment"] = sanitize(hit.get("original_comment") or "")
    return hits


@router.get("/api/stats")
async def get_stats(db_path: str = Depends(get_db_path)):
    return {
        "hits": await count_hits(db_path),
        "keywords": await count_keywords(db_path),
        "groups": await count_groups(db_path),
    }
