import html
import re
from typing import Optional

_CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")
_SPAM_LINK_RE = re.compile(r"t\.me/(?:joinchat/|\+)\S+")


def has_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC_RE.search(text))


def is_spam_link(text: str) -> bool:
    return bool(_SPAM_LINK_RE.search(text))


def find_keyword_match(text: str, keywords: list[str]) -> Optional[str]:
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            return kw
    return None


def build_profile_link(username: Optional[str], sender_id: int) -> str:
    if username:
        safe = html.escape(username)
        return f'<a href="https://t.me/{safe}" target="_blank">@{safe}</a>'
    return f'<a href="tg://user?id={sender_id}">[No Username - Click to Chat]</a>'
