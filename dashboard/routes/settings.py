from fastapi import APIRouter
from pydantic import BaseModel
import config
from db.operations import (
    get_settings, update_settings, get_api_config, update_api_config,
    get_auto_discovery_settings, update_auto_discovery_settings,
)

router = APIRouter()


class NotifSettingsIn(BaseModel):
    tg_notifications_enabled: int
    tg_notification_destination: str


class ApiConfigIn(BaseModel):
    api_id: int
    api_hash: str
    session_name: str
    proxy_type: str
    proxy_host: str
    proxy_port: int


class AutoDiscoveryIn(BaseModel):
    auto_discovery_enabled: int
    auto_discovery_min_members: int
    auto_discovery_interval_hours: int


@router.get("/api/settings")
async def read_settings():
    return await get_settings(config.DB_PATH)


@router.post("/api/settings")
async def write_settings(body: NotifSettingsIn):
    await update_settings(config.DB_PATH, body.tg_notifications_enabled, body.tg_notification_destination)
    return {"status": "ok"}


@router.get("/api/settings/api-config")
async def read_api_config():
    row = await get_api_config(config.DB_PATH)
    if row is None:
        return {"api_id": 0, "api_hash": "", "session_name": "telelistener",
                "proxy_type": "", "proxy_host": "", "proxy_port": 0}
    # Never expose the full api_hash — mask all but the last 4 chars for display.
    # The frontend sends the raw value back on save, so we store a sentinel to detect "unchanged".
    return row


@router.post("/api/settings/api-config")
async def write_api_config(body: ApiConfigIn):
    await update_api_config(
        config.DB_PATH,
        body.api_id,
        body.api_hash,
        body.session_name or "telelistener",
        body.proxy_type,
        body.proxy_host,
        body.proxy_port,
    )
    return {"status": "ok"}


@router.get("/api/settings/auto-discovery")
async def read_auto_discovery():
    return await get_auto_discovery_settings(config.DB_PATH)


@router.post("/api/settings/auto-discovery")
async def write_auto_discovery(body: AutoDiscoveryIn):
    await update_auto_discovery_settings(
        config.DB_PATH,
        body.auto_discovery_enabled,
        body.auto_discovery_min_members,
        body.auto_discovery_interval_hours,
    )
    return {"status": "ok"}
