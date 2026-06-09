import logging
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import asyncio

import config
from db.operations import (
    add_monitored_group, get_group_by_telegram_id,
    add_hit, list_keywords, get_settings,
)
from parser.handlers import has_cyrillic, is_spam_link, find_keyword_match
from parser.notifications import build_notification_text, send_notification

logger = logging.getLogger(__name__)


def create_client() -> TelegramClient:
    return TelegramClient(
        config.SESSION_NAME,
        config.API_ID,
        config.API_HASH,
        proxy=config.PROXY,
    )


async def on_new_message(event, client: TelegramClient) -> None:
    msg = event.message
    text = msg.raw_text or ""

    if not has_cyrillic(text):
        return
    if is_spam_link(text):
        return

    sender = await event.get_sender()
    if sender is None:
        return
    if getattr(sender, "bot", False):
        return

    keywords = [k["phrase"] for k in await list_keywords(config.DB_PATH)]
    matched = find_keyword_match(text, keywords)
    if matched is None:
        return

    chat = await event.get_chat()
    telegram_id = chat.id
    title = getattr(chat, "title", None)
    handle = getattr(chat, "username", None)

    await add_monitored_group(config.DB_PATH, telegram_id=telegram_id, title=title, handle=handle)
    group = await get_group_by_telegram_id(config.DB_PATH, telegram_id)
    if group is None:
        logger.error("group not found after add_monitored_group for telegram_id=%s", telegram_id)
        return

    username = getattr(sender, "username", None)
    first_name = getattr(sender, "first_name", None)
    sender_id = sender.id

    await add_hit(
        config.DB_PATH,
        group_id=group["id"],
        sender_id=sender_id,
        username=username,
        first_name=first_name,
        original_comment=text,
        keyword_matched=matched,
    )
    logger.info("Hit saved: keyword=%s user=%s", matched, username or sender_id)

    settings = await get_settings(config.DB_PATH)
    if settings and settings["tg_notifications_enabled"]:
        notification = build_notification_text(
            keyword=matched,
            group_title=title,
            username=username,
            sender_id=sender_id,
            first_name=first_name,
            comment=text,
        )
        await send_notification(client, settings["tg_notification_destination"], notification)
