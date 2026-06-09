from fastapi import APIRouter
import config
from db.operations import list_monitored_groups

router = APIRouter()


@router.get("/api/groups")
async def get_groups():
    return await list_monitored_groups(config.DB_PATH)
