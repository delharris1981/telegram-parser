# Shared mutable state for the single combined process.
# The parser sets tg_client once a Telethon session is established so that
# dashboard routes can call the Telegram API directly.
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from telethon import TelegramClient

tg_client: Optional["TelegramClient"] = None
