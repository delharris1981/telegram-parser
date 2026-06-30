from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from telethon import TelegramClient

_clients: dict[str, "TelegramClient"] = {}


def get_client(username: str) -> Optional["TelegramClient"]:
    return _clients.get(username)


def set_client(username: str, client: "TelegramClient") -> None:
    _clients[username] = client


def clear_client(username: str) -> None:
    _clients.pop(username, None)
