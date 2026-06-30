from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from telethon.tl.types import Channel, Chat
from dashboard.auth import get_db_path, get_tg_client
from db.operations import (
    list_monitored_groups,
    add_joined_group, list_joined_groups, remove_joined_group,
    list_joined_group_telegram_ids,
)

router = APIRouter()


class JoinIn(BaseModel):
    handle: str
    title: str = ""
    telegram_id: int = 0
    member_count: int = 0


@router.get("/api/groups")
async def get_groups(db_path: str = Depends(get_db_path)):
    return await list_monitored_groups(db_path)


@router.get("/api/groups/joined")
async def get_joined(db_path: str = Depends(get_db_path)):
    return await list_joined_groups(db_path)


@router.delete("/api/groups/joined/{group_id}")
async def leave_group(
    group_id: int,
    db_path: str = Depends(get_db_path),
    client=Depends(get_tg_client),
):
    groups = await list_joined_groups(db_path)
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
    await remove_joined_group(db_path, group_id)
    return {"status": "ok"}


@router.post("/api/groups/sync")
async def sync_groups(db_path: str = Depends(get_db_path), client=Depends(get_tg_client)):
    if client is None:
        raise HTTPException(503, "Parser not connected to Telegram — configure credentials first")
    try:
        dialogs = await client.get_dialogs()
    except Exception as exc:
        raise HTTPException(500, str(exc))
    existing_ids = await list_joined_group_telegram_ids(db_path)
    added = 0
    for dialog in dialogs:
        entity = dialog.entity
        if not isinstance(entity, (Channel, Chat)):
            continue
        telegram_id = entity.id
        if telegram_id in existing_ids:
            continue
        title = getattr(entity, "title", "") or ""
        handle = getattr(entity, "username", None) or ""
        member_count = getattr(entity, "participants_count", 0) or 0
        await add_joined_group(db_path, telegram_id, title, handle, member_count)
        existing_ids.add(telegram_id)
        added += 1
    return {"synced": added}


@router.get("/api/groups/search")
async def search_groups(q: str, db_path: str = Depends(get_db_path), client=Depends(get_tg_client)):
    if client is None:
        raise HTTPException(503, "Parser not connected to Telegram — configure credentials first")
    try:
        from telethon.tl.functions.contacts import SearchRequest
        result = await client(SearchRequest(q=q, limit=25))
    except Exception as exc:
        raise HTTPException(500, str(exc))
    out = []
    for chat in result.chats:
        username = getattr(chat, "username", None)
        if not username:
            continue
        out.append({
            "telegram_id": chat.id,
            "title": getattr(chat, "title", ""),
            "handle": username,
            "member_count": getattr(chat, "participants_count", None),
            "is_channel": getattr(chat, "broadcast", False),
        })
    return out


@router.post("/api/groups/join")
async def join_group(body: JoinIn, db_path: str = Depends(get_db_path), client=Depends(get_tg_client)):
    if client is None:
        raise HTTPException(503, "Parser not connected to Telegram — configure credentials first")
    handle = body.handle.lstrip("@").strip()
    try:
        from telethon.tl.functions.channels import JoinChannelRequest
        entity = await client.get_entity(handle)
        await client(JoinChannelRequest(entity))
        entity = await client.get_entity(handle)
        telegram_id = entity.id
        title = getattr(entity, "title", handle)
        member_count = getattr(entity, "participants_count", None)
        if member_count is None:
            member_count = body.member_count or 0
    except Exception as exc:
        raise HTTPException(500, f"Could not join group: {exc}")
    await add_joined_group(db_path, telegram_id, title, handle, member_count)
    return {"status": "ok", "title": title, "telegram_id": telegram_id}
