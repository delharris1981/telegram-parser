import logging
from typing import Optional
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

import config
from db.operations import (
    add_monitored_group, get_group_by_telegram_id,
    add_hit, list_keywords, get_settings, get_api_config,
)
from parser.handlers import has_cyrillic, is_spam_link, find_keyword_match
from parser.notifications import build_notification_text, send_notification

logger = logging.getLogger(__name__)


async def create_client(db_path: str) -> TelegramClient:
    """Build TelegramClient from credentials stored in db_path, with env var fallback."""
    db_cfg = await get_api_config(db_path)

    api_id = (db_cfg["api_id"] if db_cfg and db_cfg["api_id"] else None) or config.API_ID
    api_hash = (db_cfg["api_hash"] if db_cfg and db_cfg["api_hash"] else None) or config.API_HASH

    proxy: Optional[tuple] = None
    if db_cfg and db_cfg["proxy_type"] and db_cfg["proxy_host"] and db_cfg["proxy_port"]:
        proxy = (db_cfg["proxy_type"], db_cfg["proxy_host"], int(db_cfg["proxy_port"]))
    elif config.PROXY:
        proxy = config.PROXY

    if not api_id or not api_hash:
        raise RuntimeError(
            "Telegram API credentials are not configured. "
            "Set them in the dashboard (Settings → API Credentials) or via .env."
        )

    session_str = (db_cfg.get("tg_session") or "") if db_cfg else ""
    return TelegramClient(StringSession(session_str), api_id, api_hash, proxy=proxy)


async def on_new_message(event, client: TelegramClient, db_path: str) -> None:
    msg = event.message
    text = msg.raw_text or ""

    if not has_cyrillic(text):
        return
    if is_spam_link(text):
        return

    sender = await event.get_sender()
    if sender is None:
        sender = await event.get_chat()
    if sender is None:
        return
    if getattr(sender, "bot", False):
        return

    keywords = [k["phrase"] for k in await list_keywords(db_path)]
    matched = find_keyword_match(text, keywords)

    chat = await event.get_chat()
    telegram_id = chat.id
    title = getattr(chat, "title", str(telegram_id))
    handle = getattr(chat, "username", None)

    if matched is None:
        logger.debug("Message from %s — no keyword match", title)
        return

    logger.info("Keyword match: %r in %s", matched, title)

    await add_monitored_group(db_path, telegram_id=telegram_id, title=title, handle=handle)
    group = await get_group_by_telegram_id(db_path, telegram_id)
    if group is None:
        logger.error("group not found after add_monitored_group for telegram_id=%s", telegram_id)
        return

    username = getattr(sender, "username", None)
    first_name = getattr(sender, "first_name", None)
    sender_id = getattr(sender, "id", 0)

    await add_hit(
        db_path,
        group_id=group["id"],
        sender_id=sender_id,
        username=username,
        first_name=first_name,
        original_comment=text,
        keyword_matched=matched,
    )
    logger.info("Hit saved: keyword=%r group=%s user=%s", matched, title, username or sender_id)

    settings = await get_settings(db_path)
    if settings and settings["tg_notifications_enabled"]:
        notification = build_notification_text(
            keyword=matched, group_title=title,
            username=username, sender_id=sender_id,
            first_name=first_name, comment=text,
        )
        await send_notification(client, settings["tg_notification_destination"], notification)
