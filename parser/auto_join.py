import asyncio
import logging
import random
from typing import Optional

from parser.handlers import has_cyrillic

logger = logging.getLogger(__name__)

JOIN_DELAY_MIN = 60
JOIN_DELAY_MAX = 300


def compute_backoff_delay(attempt: int, base: float = 2.0, cap: float = 300.0) -> float:
    deterministic = min(cap, base * (2 ** attempt))
    jitter = random.uniform(0, deterministic * 0.5)
    return min(cap, deterministic + jitter)


def is_russian_group(title: Optional[str], description: Optional[str]) -> bool:
    combined = " ".join(filter(None, [title, description]))
    return has_cyrillic(combined)


async def _try_join(client, handle: str) -> bool:
    try:
        from telethon.tl.functions.channels import JoinChannelRequest
        entity = await client.get_entity(handle)
        await client(JoinChannelRequest(entity))
        logger.info("Joined group: %s", handle)
        return True
    except Exception as exc:
        logger.warning("Failed to join %s: %s", handle, exc)
        return False


async def join_groups_with_flood_protection(client, handles: list[str]) -> None:
    for i, handle in enumerate(handles):
        for attempt in range(5):
            if await _try_join(client, handle):
                break
            wait = compute_backoff_delay(attempt)
            logger.info("Backoff %.1fs (attempt %d) for %s", wait, attempt + 1, handle)
            await asyncio.sleep(wait)
        if i < len(handles) - 1:
            delay = random.uniform(JOIN_DELAY_MIN, JOIN_DELAY_MAX)
            logger.info("Anti-flood: sleeping %.1fs", delay)
            await asyncio.sleep(delay)
