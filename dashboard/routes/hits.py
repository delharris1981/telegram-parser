from fastapi import APIRouter
import config
from db.operations import list_hits
from dashboard.sanitize import sanitize

router = APIRouter()


@router.get("/api/hits")
async def get_hits(limit: int = 100):
    hits = await list_hits(config.DB_PATH, limit=limit)
    for hit in hits:
        hit["original_comment"] = sanitize(hit.get("original_comment") or "")
    return hits
