import html
import re

_MARKDOWN_CHARS_RE = re.compile(r"[*_`\[\]()#+\-!|]")


def sanitize(text: str) -> str:
    if not text:
        return ""
    stripped = _MARKDOWN_CHARS_RE.sub("", text)
    return html.escape(stripped)
