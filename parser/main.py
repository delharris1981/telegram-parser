import asyncio
import logging
import sys

from telethon import events
from telethon.errors import FloodWaitError

import state
from db.init import init_db
from db.operations import (
    get_auto_discovery_settings, list_keywords,
    list_joined_group_telegram_ids, add_joined_group, set_auto_discovery_last_run,
    purge_old_hits,
)
from parser.auto_join import join_groups_with_flood_protection, is_russian_group
from parser.client import create_client, on_new_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

RECONNECT_DELAY = 10
CREDENTIALS_RETRY = 30
DISCOVERY_IDLE_CHECK = 300
HIT_RETENTION_DAYS = 7
HIT_RETENTION_INTERVAL = 3600


async def run_retention_purge(db_path: str) -> None:
    while True:
        try:
            deleted = await purge_old_hits(db_path, HIT_RETENTION_DAYS)
            if deleted:
                logger.info("Retention purge: removed %d hit(s) older than %d days.", deleted, HIT_RETENTION_DAYS)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Retention purge error: %s", exc)
        await asyncio.sleep(HIT_RETENTION_INTERVAL)


async def run_auto_discovery(client, db_path: str) -> None:
    logger.info("Auto-discovery task started.")
    while True:
        try:
            settings = await get_auto_discovery_settings(db_path)
            if not settings["auto_discovery_enabled"]:
                await asyncio.sleep(DISCOVERY_IDLE_CHECK)
                continue

            keywords = await list_keywords(db_path)
            if not keywords:
                await asyncio.sleep(DISCOVERY_IDLE_CHECK)
                continue

            min_members = settings["auto_discovery_min_members"] or 0
            existing_ids = await list_joined_group_telegram_ids(db_path)
            candidates: dict[int, dict] = {}

            from telethon.tl.functions.contacts import SearchRequest
            for kw in keywords:
                try:
                    result = await client(SearchRequest(q=kw["phrase"], limit=25))
                    for chat in result.chats:
                        username = getattr(chat, "username", None)
                        if not username:
                            continue
                        tid = chat.id
                        if tid in existing_ids or tid in candidates:
                            continue
                        title = getattr(chat, "title", "") or ""
                        member_count = getattr(chat, "participants_count", 0) or 0
                        if member_count < min_members:
                            continue
                        if not is_russian_group(title, ""):
                            continue
                        candidates[tid] = {"handle": username, "title": title, "member_count": member_count}
                except Exception as exc:
                    logger.warning("Auto-discovery search error for %r: %s", kw["phrase"], exc)

            if candidates:
                logger.info("Auto-discovery: found %d new group(s), joining…", len(candidates))
                handles = [c["handle"] for c in candidates.values()]
                await join_groups_with_flood_protection(client, handles)
                for tid, info in candidates.items():
                    await add_joined_group(db_path, tid, info["title"], info["handle"], info["member_count"])
            else:
                logger.info("Auto-discovery: no new groups found this run.")

            await set_auto_discovery_last_run(db_path)
            interval_secs = (settings["auto_discovery_interval_hours"] or 6) * 3600
            await asyncio.sleep(interval_secs)

        except asyncio.CancelledError:
            logger.info("Auto-discovery task cancelled.")
            raise
        except Exception as exc:
            logger.exception("Auto-discovery unexpected error: %s", exc)
            await asyncio.sleep(DISCOVERY_IDLE_CHECK)


async def run_parser_loop(username: str, db_path: str) -> None:
    """Reconnect loop for a single user's Telethon client."""
    while True:
        try:
            client = await create_client(db_path)
        except RuntimeError as exc:
            logger.warning("%s — retrying in %ds.", exc, CREDENTIALS_RETRY)
            try:
                await asyncio.sleep(CREDENTIALS_RETRY)
            except asyncio.CancelledError:
                return
            continue
        except asyncio.CancelledError:
            return

        @client.on(events.NewMessage)
        async def handler(event):
            try:
                await on_new_message(event, client, db_path)
            except FloodWaitError as e:
                logger.warning("FloodWait: sleeping %ds", e.seconds)
                await asyncio.sleep(e.seconds)
            except Exception as exc:
                logger.exception("Unhandled error in message handler: %s", exc)

        try:
            while True:
                try:
                    logger.info("[%s] Connecting to Telegram...", username)
                    await client.start()
                    state.set_client(username, client)
                    logger.info("[%s] Parser running.", username)
                    retention_task = asyncio.create_task(run_retention_purge(db_path))
                    discovery_task = asyncio.create_task(run_auto_discovery(client, db_path))
                    try:
                        await client.run_until_disconnected()
                    finally:
                        retention_task.cancel()
                        discovery_task.cancel()
                        for t in (retention_task, discovery_task):
                            try:
                                await t
                            except asyncio.CancelledError:
                                pass
                except (ConnectionError, TimeoutError, OSError) as exc:
                    state.clear_client(username)
                    logger.error("[%s] Network error: %s — reconnecting in %ds", username, exc, RECONNECT_DELAY)
                    await asyncio.sleep(RECONNECT_DELAY)
                except KeyboardInterrupt:
                    return
        except asyncio.CancelledError:
            pass
        finally:
            state.clear_client(username)
            await client.disconnect()
        return
