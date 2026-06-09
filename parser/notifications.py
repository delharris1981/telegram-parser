import html
import logging
from typing import Optional

from parser.handlers import build_profile_link

logger = logging.getLogger(__name__)


def build_notification_text(
    keyword: str,
    group_title: Optional[str],
    username: Optional[str],
    sender_id: int,
    first_name: Optional[str],
    comment: str,
) -> str:
    profile_link = build_profile_link(username=username, sender_id=sender_id)
    safe_comment = html.escape(comment)
    safe_group = html.escape(group_title or "Unknown Group")
    safe_name = html.escape(first_name or "")
    safe_keyword = html.escape(keyword)
    return (
        f"<b>Keyword hit:</b> <code>{safe_keyword}</code>\n"
        f"<b>Group:</b> {safe_group}\n"
        f"<b>User:</b> {safe_name} {profile_link}\n"
        f"<b>Message:</b>\n{safe_comment}"
    )


async def send_notification(client, destination: str, text: str) -> None:
    try:
        await client.send_message(destination, text, parse_mode="html")
    except Exception as exc:
        logger.warning("Failed to send notification to %s: %s", destination, exc)
