from fastapi import APIRouter
from pydantic import BaseModel
import config
from db.operations import get_settings, update_settings

router = APIRouter()


class SettingsIn(BaseModel):
    tg_notifications_enabled: int
    tg_notification_destination: str


@router.get("/api/settings")
async def read_settings():
    return await get_settings(config.DB_PATH)


@router.post("/api/settings")
async def write_settings(body: SettingsIn):
    await update_settings(config.DB_PATH, body.tg_notifications_enabled, body.tg_notification_destination)
    return {"status": "ok"}
