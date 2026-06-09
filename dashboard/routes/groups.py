from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import config
import state
from db.operations import (
    list_monitored_groups,
    add_joined_group, list_joined_groups, remove_joined_group,
)

router = APIRouter()


class JoinIn(BaseModel):
    handle: str          # @username or t.me/username
    title: str = ""
    telegram_id: int = 0
    member_count: int = 0


# ── Existing hit-groups ────────────────────────────────────────────
@router.get("/api/groups")
async def get_groups():
    return await list_monitored_groups(config.DB_PATH)


# ── App-managed joined groups ──────────────────────────────────────
@router.get("/api/groups/joined")
async def get_joined():
    return await list_joined_groups(config.DB_PATH)


@router.delete("/api/groups/joined/{group_id}")
async def leave_group(group_id: int):
    client = state.tg_client
    groups = await list_joined_groups(config.DB_PATH)
    group = next((g for g in groups if g["id"] == group_id), None)
    if not group:
        raise HTTPException(404, "Group not found")

    if client:
        try:
            from telethon.tl.functions.channels import LeaveChannelRequest
            entity = await client.get_entity(int(group["telegram_id"]))
            await client(LeaveChannelRequest(entity))
        except Exception as exc:
            raise HTTPException(500, f"Could not leave group: {exc}")

    await remove_joined_group(config.DB_PATH, group_id)
    return {"status": "ok"}


# ── Search public groups ───────────────────────────────────────────
@router.get("/api/groups/search")
async def search_groups(q: str):
    client = state.tg_client
    if client is None:
        raise HTTPException(503, "Parser not connected to Telegram — configure credentials first")

    try:
        from telethon.tl.functions.contacts import SearchRequest
        from telethon.errors import FloodWaitError
        result = await client(SearchRequest(q=q, limit=25))
    except Exception as exc:
        raise HTTPException(500, str(exc))

    out = []
    for chat in result.chats:
        username = getattr(chat, "username", None)
        if not username:
            continue  # skip private / invite-only
        out.append({
            "telegram_id": chat.id,
            "title": getattr(chat, "title", ""),
            "handle": username,
            "member_count": getattr(chat, "participants_count", None),
            "is_channel": getattr(chat, "broadcast", False),
        })
    return out


# ── Join a group ───────────────────────────────────────────────────
@router.post("/api/groups/join")
async def join_group(body: JoinIn):
    client = state.tg_client
    if client is None:
        raise HTTPException(503, "Parser not connected to Telegram — configure credentials first")

    handle = body.handle.lstrip("@").strip()
    try:
        from telethon.tl.functions.channels import JoinChannelRequest
        entity = await client.get_entity(handle)
        await client(JoinChannelRequest(entity))

        telegram_id = entity.id
        title = getattr(entity, "title", handle)
        member_count = getattr(entity, "participants_count", None)
    except Exception as exc:
        raise HTTPException(500, f"Could not join group: {exc}")

    await add_joined_group(config.DB_PATH, telegram_id, title, handle, member_count)
    return {"status": "ok", "title": title, "telegram_id": telegram_id}
