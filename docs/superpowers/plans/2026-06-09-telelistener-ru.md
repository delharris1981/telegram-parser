# TeleListener-RU Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready Telegram keyword monitoring UserBot (TeleListener-RU) with a FastAPI web dashboard, SQLite WAL storage, live Telegram notifications, Docker orchestration, and GitHub Actions CI/CD.

**Architecture:** Three independent processes share one SQLite database in WAL mode: (1) a Telethon UserBot that continuously monitors public Russian Telegram groups for keyword hits, (2) a FastAPI dashboard for configuration and visualization, and (3) shared `db/` and `config.py` modules imported by both. Docker Compose links the two processes via a shared named volume.

**Tech Stack:** Python 3.11, Telethon 1.36, FastAPI 0.115, Uvicorn, aiosqlite 0.20, Jinja2, python-multipart, httpx, pytest, pytest-asyncio, PyInstaller, Docker, GitHub Actions

---

### Task 1: Project Scaffold, Config, and Database Schema

**Files:**
- Create: `config.py`
- Create: `db/__init__.py`
- Create: `db/init.py`
- Create: `parser/__init__.py`
- Create: `dashboard/__init__.py`
- Create: `dashboard/routes/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db_init.py`
- Create: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: Initialize git and create directory structure**

```bash
cd "/Users/derek/Documents/Projects/Standalone/telegram parser"
git init
mkdir -p parser db dashboard/routes dashboard/templates tests .github/workflows docs/superpowers/plans
touch parser/__init__.py db/__init__.py dashboard/__init__.py dashboard/routes/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
telethon==1.36.0
fastapi==0.115.0
uvicorn[standard]==0.32.0
aiosqlite==0.20.0
jinja2==3.1.4
python-multipart==0.0.12
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
pyinstaller==6.11.0
```

- [ ] **Step 3: Write `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 4: Write `.env.example`**

```bash
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
SESSION_NAME=telelistener
KEYWORDS=купить,продать,квартира
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=changeme
DB_PATH=db/telelistener.db
PROXY_TYPE=
PROXY_HOST=
PROXY_PORT=
```

- [ ] **Step 5: Write `config.py`**

```python
import os

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "telelistener")
KEYWORDS = [k.strip() for k in os.getenv("KEYWORDS", "").split(",") if k.strip()]
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "changeme")
DB_PATH = os.getenv("DB_PATH", "db/telelistener.db")

_proxy_type = os.getenv("PROXY_TYPE", "").lower()
_proxy_host = os.getenv("PROXY_HOST", "")
_proxy_port = os.getenv("PROXY_PORT", "")

PROXY = None
if _proxy_type and _proxy_host and _proxy_port:
    PROXY = (_proxy_type, _proxy_host, int(_proxy_port))
```

- [ ] **Step 6: Write failing test `tests/test_db_init.py`**

```python
import os
import pytest
import aiosqlite

os.environ.setdefault("DB_PATH", ":memory:")

from db.init import init_db


@pytest.mark.asyncio
async def test_wal_mode_is_set(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row[0] == "wal"


@pytest.mark.asyncio
async def test_schema_tables_created(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in await cursor.fetchall()}
    assert tables == {"keywords", "monitored_groups", "parsed_hits", "settings"}


@pytest.mark.asyncio
async def test_settings_seed_row_exists(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT id, tg_notifications_enabled, tg_notification_destination FROM settings WHERE id=1"
        )
        row = await cursor.fetchone()
    assert row == (1, 0, "me")


@pytest.mark.asyncio
async def test_init_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    await init_db(db_path)  # calling twice must not raise
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM settings")
        row = await cursor.fetchone()
    assert row[0] == 1
```

- [ ] **Step 7: Run test to confirm it fails**

```bash
cd "/Users/derek/Documents/Projects/Standalone/telegram parser"
pip install -r requirements.txt -q
pytest tests/test_db_init.py -v 2>&1 | head -30
```
Expected: `ModuleNotFoundError: No module named 'db.init'`

- [ ] **Step 8: Write `db/init.py`**

```python
import aiosqlite

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monitored_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    title TEXT,
    handle TEXT,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parsed_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER REFERENCES monitored_groups(id),
    sender_id INTEGER,
    username TEXT,
    first_name TEXT,
    original_comment TEXT,
    keyword_matched TEXT,
    captured_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    tg_notifications_enabled INTEGER NOT NULL DEFAULT 0,
    tg_notification_destination TEXT NOT NULL DEFAULT 'me'
);

INSERT OR IGNORE INTO settings (id, tg_notifications_enabled, tg_notification_destination)
VALUES (1, 0, 'me');
"""


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.executescript(SCHEMA)
        await db.commit()
```

- [ ] **Step 9: Write `tests/conftest.py`**

```python
import pytest_asyncio
from db.init import init_db


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return db_path
```

- [ ] **Step 10: Run tests to confirm they pass**

```bash
pytest tests/test_db_init.py -v
```
Expected: 4 tests PASS

- [ ] **Step 11: Commit**

```bash
git add config.py db/ tests/ parser/__init__.py dashboard/__init__.py dashboard/routes/__init__.py requirements.txt .env.example pytest.ini
git commit -m "feat: project scaffold, config, and database schema with WAL mode"
```

---

### Task 2: Database CRUD Operations

**Files:**
- Create: `db/operations.py`
- Create: `tests/test_db_operations.py`

- [ ] **Step 1: Write failing tests `tests/test_db_operations.py`**

```python
import pytest
from db.operations import (
    add_keyword, list_keywords, delete_keyword,
    add_monitored_group, list_monitored_groups, get_group_by_telegram_id,
    add_hit, list_hits,
    get_settings, update_settings,
)


@pytest.mark.asyncio
async def test_add_and_list_keywords(test_db):
    await add_keyword(test_db, "купить")
    await add_keyword(test_db, "продать")
    keywords = await list_keywords(test_db)
    phrases = [k["phrase"] for k in keywords]
    assert "купить" in phrases
    assert "продать" in phrases


@pytest.mark.asyncio
async def test_add_duplicate_keyword_is_ignored(test_db):
    await add_keyword(test_db, "купить")
    await add_keyword(test_db, "купить")  # must not raise
    keywords = await list_keywords(test_db)
    assert len([k for k in keywords if k["phrase"] == "купить"]) == 1


@pytest.mark.asyncio
async def test_delete_keyword(test_db):
    await add_keyword(test_db, "тест")
    keywords = await list_keywords(test_db)
    kid = next(k["id"] for k in keywords if k["phrase"] == "тест")
    await delete_keyword(test_db, kid)
    keywords = await list_keywords(test_db)
    assert not any(k["phrase"] == "тест" for k in keywords)


@pytest.mark.asyncio
async def test_add_and_get_monitored_group(test_db):
    await add_monitored_group(test_db, telegram_id=100, title="Тест Чат", handle="test_chat")
    group = await get_group_by_telegram_id(test_db, 100)
    assert group["title"] == "Тест Чат"
    assert group["handle"] == "test_chat"


@pytest.mark.asyncio
async def test_add_group_duplicate_ignored(test_db):
    await add_monitored_group(test_db, telegram_id=200, title="Чат", handle=None)
    await add_monitored_group(test_db, telegram_id=200, title="Чат 2", handle=None)
    groups = await list_monitored_groups(test_db)
    assert len([g for g in groups if g["telegram_id"] == 200]) == 1


@pytest.mark.asyncio
async def test_add_hit_and_list(test_db):
    await add_monitored_group(test_db, telegram_id=300, title="Источник", handle=None)
    group = await get_group_by_telegram_id(test_db, 300)
    await add_hit(
        test_db,
        group_id=group["id"],
        sender_id=99,
        username="ivan",
        first_name="Иван",
        original_comment="купить квартиру",
        keyword_matched="купить",
    )
    hits = await list_hits(test_db, limit=10)
    assert len(hits) == 1
    assert hits[0]["username"] == "ivan"
    assert hits[0]["keyword_matched"] == "купить"


@pytest.mark.asyncio
async def test_get_and_update_settings(test_db):
    settings = await get_settings(test_db)
    assert settings["tg_notifications_enabled"] == 0
    assert settings["tg_notification_destination"] == "me"
    await update_settings(test_db, enabled=1, destination="@mybot")
    settings = await get_settings(test_db)
    assert settings["tg_notifications_enabled"] == 1
    assert settings["tg_notification_destination"] == "@mybot"
```

- [ ] **Step 2: Run test to confirm failure**

```bash
pytest tests/test_db_operations.py -v 2>&1 | head -20
```
Expected: `ImportError: cannot import name 'add_keyword' from 'db.operations'`

- [ ] **Step 3: Write `db/operations.py`**

```python
from typing import Optional
import aiosqlite


async def _fetchall(db_path: str, query: str, params=()) -> list[dict]:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def _fetchone(db_path: str, query: str, params=()) -> Optional[dict]:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None


# --- Keywords ---

async def add_keyword(db_path: str, phrase: str) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute("INSERT OR IGNORE INTO keywords (phrase) VALUES (?)", (phrase,))
        await db.commit()


async def list_keywords(db_path: str) -> list[dict]:
    return await _fetchall(db_path, "SELECT id, phrase, created_at FROM keywords ORDER BY created_at DESC")


async def delete_keyword(db_path: str, keyword_id: int) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute("DELETE FROM keywords WHERE id=?", (keyword_id,))
        await db.commit()


# --- Monitored Groups ---

async def add_monitored_group(
    db_path: str, telegram_id: int, title: Optional[str], handle: Optional[str]
) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute(
            "INSERT OR IGNORE INTO monitored_groups (telegram_id, title, handle) VALUES (?, ?, ?)",
            (telegram_id, title, handle),
        )
        await db.commit()


async def list_monitored_groups(db_path: str) -> list[dict]:
    return await _fetchall(
        db_path,
        "SELECT id, telegram_id, title, handle, joined_at FROM monitored_groups ORDER BY joined_at DESC",
    )


async def get_group_by_telegram_id(db_path: str, telegram_id: int) -> Optional[dict]:
    return await _fetchone(
        db_path,
        "SELECT id, telegram_id, title, handle, joined_at FROM monitored_groups WHERE telegram_id=?",
        (telegram_id,),
    )


# --- Parsed Hits ---

async def add_hit(
    db_path: str,
    group_id: int,
    sender_id: int,
    username: Optional[str],
    first_name: Optional[str],
    original_comment: str,
    keyword_matched: str,
) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute(
            """INSERT INTO parsed_hits
               (group_id, sender_id, username, first_name, original_comment, keyword_matched)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (group_id, sender_id, username, first_name, original_comment, keyword_matched),
        )
        await db.commit()


async def list_hits(db_path: str, limit: int = 100) -> list[dict]:
    return await _fetchall(
        db_path,
        """SELECT ph.id, mg.title AS group_title, ph.sender_id, ph.username, ph.first_name,
                  ph.original_comment, ph.keyword_matched, ph.captured_at
           FROM parsed_hits ph
           LEFT JOIN monitored_groups mg ON mg.id = ph.group_id
           ORDER BY ph.captured_at DESC LIMIT ?""",
        (limit,),
    )


# --- Settings ---

async def get_settings(db_path: str) -> dict:
    return await _fetchone(
        db_path,
        "SELECT id, tg_notifications_enabled, tg_notification_destination FROM settings WHERE id=1",
    )


async def update_settings(db_path: str, enabled: int, destination: str) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute(
            "UPDATE settings SET tg_notifications_enabled=?, tg_notification_destination=? WHERE id=1",
            (enabled, destination),
        )
        await db.commit()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_db_operations.py -v
```
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add db/operations.py tests/test_db_operations.py
git commit -m "feat: database CRUD operations for all four tables"
```

---

### Task 3: Message Handler Utilities — Cyrillic Filter, Keyword Detection, Spam Guard, Profile Links

**Files:**
- Create: `parser/handlers.py`
- Create: `tests/test_handlers.py`

- [ ] **Step 1: Write failing tests `tests/test_handlers.py`**

```python
from parser.handlers import (
    has_cyrillic,
    is_spam_link,
    find_keyword_match,
    build_profile_link,
)


# --- has_cyrillic ---

def test_has_cyrillic_true():
    assert has_cyrillic("Привет мир") is True


def test_has_cyrillic_false_for_latin():
    assert has_cyrillic("Hello world") is False


def test_has_cyrillic_false_for_empty():
    assert has_cyrillic("") is False


def test_has_cyrillic_mixed():
    assert has_cyrillic("Price: 100 рублей") is True


# --- is_spam_link ---

def test_is_spam_link_joinchat():
    assert is_spam_link("Присоединяйся t.me/joinchat/ABC123") is True


def test_is_spam_link_plus_invite():
    assert is_spam_link("Вот ссылка t.me/+XYZ456") is True


def test_is_spam_link_normal_message():
    assert is_spam_link("Хочу купить квартиру в Москве") is False


def test_is_spam_link_regular_tme():
    assert is_spam_link("Мой канал t.me/my_channel") is False


# --- find_keyword_match ---

def test_find_keyword_match_exact():
    assert find_keyword_match("хочу купить квартиру", ["купить", "продать"]) == "купить"


def test_find_keyword_match_case_insensitive():
    assert find_keyword_match("Хочу КУПИТЬ квартиру", ["купить"]) == "купить"


def test_find_keyword_match_no_match():
    assert find_keyword_match("Добрый день", ["купить", "продать"]) is None


def test_find_keyword_match_empty_keywords():
    assert find_keyword_match("купить квартиру", []) is None


# --- build_profile_link ---

def test_build_profile_link_with_username():
    link = build_profile_link(username="ivan_petrov", sender_id=123)
    assert "https://t.me/ivan_petrov" in link
    assert "@ivan_petrov" in link


def test_build_profile_link_without_username():
    link = build_profile_link(username=None, sender_id=456)
    assert "tg://user?id=456" in link
    assert "No Username" in link


def test_build_profile_link_empty_username():
    link = build_profile_link(username="", sender_id=789)
    assert "tg://user?id=789" in link
```

- [ ] **Step 2: Run test to confirm failure**

```bash
pytest tests/test_handlers.py -v 2>&1 | head -20
```
Expected: `ImportError: cannot import name 'has_cyrillic' from 'parser.handlers'`

- [ ] **Step 3: Write `parser/handlers.py`**

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_handlers.py -v
```
Expected: 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add parser/handlers.py tests/test_handlers.py
git commit -m "feat: message handler utilities — Cyrillic filter, keyword detection, spam guard, profile links"
```

---

### Task 4: Auto-Join Logic with Exponential Backoff and Russian Group Filtration

**Files:**
- Create: `parser/auto_join.py`
- Create: `tests/test_auto_join.py`

- [ ] **Step 1: Write failing tests `tests/test_auto_join.py`**

```python
from parser.auto_join import compute_backoff_delay, is_russian_group


# --- compute_backoff_delay ---

def test_backoff_first_attempt_is_positive():
    delay = compute_backoff_delay(attempt=0, base=2.0, cap=300.0)
    assert delay >= 2.0


def test_backoff_increases_with_attempts():
    d0 = compute_backoff_delay(attempt=0, base=2.0, cap=300.0)
    d3 = compute_backoff_delay(attempt=3, base=2.0, cap=300.0)
    assert d3 > d0


def test_backoff_capped_at_max():
    delay = compute_backoff_delay(attempt=50, base=2.0, cap=300.0)
    assert delay <= 300.0


# --- is_russian_group ---

def test_is_russian_group_true_from_title():
    assert is_russian_group(title="Недвижимость Москва", description=None) is True


def test_is_russian_group_true_from_description():
    assert is_russian_group(title="Real Estate", description="Квартиры в Москве") is True


def test_is_russian_group_both_latin():
    assert is_russian_group(title="Real Estate Moscow", description="Apartments for sale") is False


def test_is_russian_group_none_description():
    assert is_russian_group(title="Москва", description=None) is True
```

- [ ] **Step 2: Run test to confirm failure**

```bash
pytest tests/test_auto_join.py -v 2>&1 | head -20
```
Expected: `ImportError: cannot import name 'compute_backoff_delay' from 'parser.auto_join'`

- [ ] **Step 3: Write `parser/auto_join.py`**

```python
import asyncio
import logging
import random
from typing import Optional

from parser.handlers import has_cyrillic

logger = logging.getLogger(__name__)

JOIN_DELAY_MIN = 60
JOIN_DELAY_MAX = 300


def compute_backoff_delay(attempt: int, base: float = 2.0, cap: float = 300.0) -> float:
    jitter = random.uniform(0, base)
    return min(base ** attempt + jitter, cap)


def is_russian_group(title: Optional[str], description: Optional[str]) -> bool:
    combined = " ".join(filter(None, [title, description]))
    return has_cyrillic(combined)


async def _try_join(client, handle: str) -> bool:
    try:
        await client.join_chat(handle)
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_auto_join.py -v
```
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add parser/auto_join.py tests/test_auto_join.py
git commit -m "feat: auto-join logic with exponential backoff and Russian group filtration"
```

---

### Task 5: Telegram Notification Dispatcher

**Files:**
- Create: `parser/notifications.py`
- Create: `tests/test_notifications.py`

- [ ] **Step 1: Write failing tests `tests/test_notifications.py`**

```python
from parser.notifications import build_notification_text


def test_notification_with_username():
    text = build_notification_text(
        keyword="купить",
        group_title="Недвижимость МСК",
        username="ivan_petrov",
        sender_id=111,
        first_name="Иван",
        comment="Хочу купить квартиру",
    )
    assert "купить" in text
    assert "Недвижимость МСК" in text
    assert "https://t.me/ivan_petrov" in text
    assert "@ivan_petrov" in text
    assert "Хочу купить квартиру" in text


def test_notification_without_username_uses_tg_protocol():
    text = build_notification_text(
        keyword="продать",
        group_title="Чат",
        username=None,
        sender_id=222,
        first_name="Аноним",
        comment="Продам гараж",
    )
    assert "tg://user?id=222" in text
    assert "No Username" in text


def test_notification_html_escapes_comment():
    text = build_notification_text(
        keyword="купить",
        group_title="Чат",
        username=None,
        sender_id=333,
        first_name="Тест",
        comment="<script>alert(1)</script>",
    )
    assert "<script>" not in text
    assert "&lt;script&gt;" in text
```

- [ ] **Step 2: Run test to confirm failure**

```bash
pytest tests/test_notifications.py -v 2>&1 | head -15
```
Expected: `ImportError: cannot import name 'build_notification_text'`

- [ ] **Step 3: Write `parser/notifications.py`**

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_notifications.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add parser/notifications.py tests/test_notifications.py
git commit -m "feat: Telegram notification dispatcher with HTML formatting and profile link fallback"
```

---

### Task 6: Telethon Client, Message Event Handler, and Parser Main Loop

**Files:**
- Create: `parser/client.py`
- Create: `parser/main.py`

No unit tests for these files — they require live Telegram API credentials. Correctness is validated end-to-end by running the parser against a real account.

- [ ] **Step 1: Write `parser/client.py`**

```python
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
    if settings["tg_notifications_enabled"]:
        notification = build_notification_text(
            keyword=matched,
            group_title=title,
            username=username,
            sender_id=sender_id,
            first_name=first_name,
            comment=text,
        )
        await send_notification(client, settings["tg_notification_destination"], notification)
```

- [ ] **Step 2: Write `parser/main.py`**

```python
import asyncio
import logging
import sys

from telethon import events
from telethon.errors import FloodWaitError, ConnectionError as TelethonConnectionError

import config
from db.init import init_db
from parser.client import create_client, on_new_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

RECONNECT_DELAY = 10


async def main() -> None:
    await init_db(config.DB_PATH)
    client = create_client()

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            await on_new_message(event, client)
        except FloodWaitError as e:
            logger.warning("FloodWait: sleeping %ds", e.seconds)
            await asyncio.sleep(e.seconds)
        except Exception as exc:
            logger.exception("Unhandled error in message handler: %s", exc)

    while True:
        try:
            logger.info("Connecting to Telegram...")
            await client.start()
            logger.info("Parser running. Listening for messages...")
            await client.run_until_disconnected()
        except (TelethonConnectionError, ConnectionError, TimeoutError) as exc:
            logger.error("Network error: %s — reconnecting in %ds", exc, RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            break

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Commit**

```bash
git add parser/client.py parser/main.py
git commit -m "feat: Telethon client, message event handler, and parser main loop with reconnect"
```

---

### Task 7: FastAPI Dashboard — Core App, HTTP Basic Auth, XSS Sanitizer

**Files:**
- Create: `dashboard/auth.py`
- Create: `dashboard/sanitize.py`
- Create: `dashboard/main.py`
- Create: `tests/test_dashboard_auth.py`

- [ ] **Step 1: Write failing test `tests/test_dashboard_auth.py`**

```python
import os
os.environ["DASHBOARD_USERNAME"] = "testuser"
os.environ["DASHBOARD_PASSWORD"] = "testpass"
os.environ["DB_PATH"] = ":memory:"

import base64
import pytest
from fastapi.testclient import TestClient

from dashboard.main import app

client = TestClient(app, raise_server_exceptions=False)


def auth_header(user: str, password: str) -> dict:
    credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def test_unauthenticated_returns_401():
    r = client.get("/")
    assert r.status_code == 401


def test_wrong_credentials_returns_401():
    r = client.get("/", headers=auth_header("wrong", "bad"))
    assert r.status_code == 401


def test_correct_credentials_returns_200():
    r = client.get("/", headers=auth_header("testuser", "testpass"))
    assert r.status_code == 200
```

- [ ] **Step 2: Run test to confirm failure**

```bash
pytest tests/test_dashboard_auth.py -v 2>&1 | head -20
```
Expected: `ImportError: cannot import name 'app' from 'dashboard.main'`

- [ ] **Step 3: Write `dashboard/auth.py`**

```python
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import config

security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    ok_user = secrets.compare_digest(
        credentials.username.encode(), config.DASHBOARD_USERNAME.encode()
    )
    ok_pass = secrets.compare_digest(
        credentials.password.encode(), config.DASHBOARD_PASSWORD.encode()
    )
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
```

- [ ] **Step 4: Write `dashboard/sanitize.py`**

```python
import html
import re

_MARKDOWN_CHARS_RE = re.compile(r"[*_`\[\]()#+\-!|]")


def sanitize(text: str) -> str:
    if not text:
        return ""
    stripped = _MARKDOWN_CHARS_RE.sub("", text)
    return html.escape(stripped)
```

- [ ] **Step 5: Write initial `dashboard/main.py`**

```python
import pathlib
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dashboard.auth import require_auth
from dashboard.routes import hits, keywords, groups
from dashboard.routes import settings as settings_router

BASE_DIR = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="TeleListener Dashboard")

app.include_router(hits.router, dependencies=[Depends(require_auth)])
app.include_router(keywords.router, dependencies=[Depends(require_auth)])
app.include_router(groups.router, dependencies=[Depends(require_auth)])
app.include_router(settings_router.router, dependencies=[Depends(require_auth)])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _user: str = Depends(require_auth)):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/keywords", response_class=HTMLResponse)
async def keywords_page(request: Request, _user: str = Depends(require_auth)):
    return templates.TemplateResponse("keywords.html", {"request": request})


@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request, _user: str = Depends(require_auth)):
    return templates.TemplateResponse("groups.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, _user: str = Depends(require_auth)):
    return templates.TemplateResponse("settings.html", {"request": request})
```

All four routers (`hits`, `keywords`, `groups`, `settings`) must exist as modules before `dashboard/main.py` can be imported. Create stub files now so the import doesn't crash during the auth test:

`dashboard/routes/hits.py` (stub):
```python
from fastapi import APIRouter
router = APIRouter()
```

`dashboard/routes/keywords.py` (stub):
```python
from fastapi import APIRouter
router = APIRouter()
```

`dashboard/routes/groups.py` (stub):
```python
from fastapi import APIRouter
router = APIRouter()
```

`dashboard/routes/settings.py` (stub):
```python
from fastapi import APIRouter
router = APIRouter()
```

Also create a minimal `dashboard/templates/index.html` so the `/` route doesn't 500:
```html
<!DOCTYPE html><html><body>TeleListener</body></html>
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
pytest tests/test_dashboard_auth.py -v
```
Expected: 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add dashboard/auth.py dashboard/sanitize.py dashboard/main.py dashboard/routes/ dashboard/templates/index.html tests/test_dashboard_auth.py
git commit -m "feat: FastAPI app core with HTTP Basic Auth and XSS sanitizer"
```

---

### Task 8: Dashboard Routes — Hits Feed API and Full Templates

**Files:**
- Modify: `dashboard/routes/hits.py` (replace stub)
- Create: `dashboard/templates/base.html`
- Modify: `dashboard/templates/index.html` (replace stub)
- Create: `tests/test_routes_hits.py`

- [ ] **Step 1: Write failing tests `tests/test_routes_hits.py`**

```python
import os
os.environ["DASHBOARD_USERNAME"] = "admin"
os.environ["DASHBOARD_PASSWORD"] = "pass"
os.environ["DB_PATH"] = ":memory:"

import base64
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from dashboard.main import app

client = TestClient(app)


def auth():
    return {"Authorization": "Basic " + base64.b64encode(b"admin:pass").decode()}


def test_hits_api_returns_list():
    mock_hits = [
        {
            "id": 1, "group_title": "Чат", "sender_id": 99,
            "username": "ivan", "first_name": "Иван",
            "original_comment": "купить квартиру",
            "keyword_matched": "купить",
            "captured_at": "2024-01-01 12:00:00",
        }
    ]
    with patch("dashboard.routes.hits.list_hits", new=AsyncMock(return_value=mock_hits)):
        r = client.get("/api/hits", headers=auth())
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["username"] == "ivan"


def test_hits_api_sanitizes_xss():
    mock_hits = [
        {
            "id": 2, "group_title": "Чат", "sender_id": 99,
            "username": None, "first_name": "X",
            "original_comment": "<script>alert(1)</script>",
            "keyword_matched": "купить",
            "captured_at": "2024-01-01 12:00:00",
        }
    ]
    with patch("dashboard.routes.hits.list_hits", new=AsyncMock(return_value=mock_hits)):
        r = client.get("/api/hits", headers=auth())
    assert "<script>" not in r.text
```

- [ ] **Step 2: Run test to confirm failure**

```bash
pytest tests/test_routes_hits.py -v 2>&1 | head -20
```
Expected: FAIL — stub router returns 404 for `/api/hits`

- [ ] **Step 3: Replace stub `dashboard/routes/hits.py`**

```python
from fastapi import APIRouter
import config
from db.operations import list_hits
from dashboard.sanitize import sanitize

router = APIRouter()


@router.get("/api/hits")
async def get_hits(limit: int = 100):
    hits = await list_hits(config.DB_PATH, limit=limit)
    for hit in hits:
        hit["original_comment"] = sanitize(hit.get("original_comment") or "")
    return hits
```

- [ ] **Step 4: Write `dashboard/templates/base.html`**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TeleListener Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f4f6f9; color: #333; }
    nav { background: #2c3e50; padding: 10px 20px; display: flex; gap: 20px; }
    nav a { color: #ecf0f1; text-decoration: none; font-size: 15px; }
    nav a:hover { text-decoration: underline; }
    .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
    table { width: 100%; border-collapse: collapse; background: #fff; }
    th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; font-size: 13px; }
    th { background: #2c3e50; color: #fff; }
    tr:nth-child(even) { background: #f9f9f9; }
    .keyword-badge { background: #e74c3c; color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 11px; }
    input[type=text], input[type=checkbox] { padding: 6px; border: 1px solid #ccc; border-radius: 4px; }
    input[type=text] { width: 260px; }
    button { padding: 6px 14px; background: #2c3e50; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background: #34495e; }
    #status-msg { color: green; margin-top: 8px; }
  </style>
</head>
<body>
  <nav>
    <a href="/">Live Feed</a>
    <a href="/keywords">Keywords</a>
    <a href="/groups">Groups</a>
    <a href="/settings">Settings</a>
  </nav>
  <div class="container">
    {% block content %}{% endblock %}
  </div>
</body>
</html>
```

- [ ] **Step 5: Replace stub `dashboard/templates/index.html`**

```html
{% extends "base.html" %}
{% block content %}
<h2>Live Keyword Hits</h2>
<div id="feed"><p>Loading…</p></div>

<script>
async function loadFeed() {
  const resp = await fetch('/api/hits?limit=100');
  const hits = await resp.json();
  if (!hits.length) {
    document.getElementById('feed').innerHTML = '<p>No hits yet.</p>';
    return;
  }
  let html = '<table><thead><tr><th>Time</th><th>Group</th><th>User</th><th>Keyword</th><th>Message</th></tr></thead><tbody>';
  hits.forEach(h => {
    const userLink = h.username
      ? `<a href="https://t.me/${h.username}" target="_blank">@${h.username}</a>`
      : `<a href="tg://user?id=${h.sender_id}">[No Username - Click to Chat]</a>`;
    html += `<tr>
      <td>${h.captured_at}</td>
      <td>${h.group_title || ''}</td>
      <td>${h.first_name || ''} ${userLink}</td>
      <td><span class="keyword-badge">${h.keyword_matched}</span></td>
      <td>${h.original_comment}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('feed').innerHTML = html;
}
loadFeed();
setInterval(loadFeed, 10000);
</script>
{% endblock %}
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
pytest tests/test_routes_hits.py -v
```
Expected: 2 tests PASS

- [ ] **Step 7: Commit**

```bash
git add dashboard/routes/hits.py dashboard/templates/base.html dashboard/templates/index.html tests/test_routes_hits.py
git commit -m "feat: hits feed API with XSS sanitization and live dashboard template"
```

---

### Task 9: Dashboard Routes — Keywords, Groups, Settings Management

**Files:**
- Modify: `dashboard/routes/keywords.py` (replace stub)
- Modify: `dashboard/routes/groups.py` (replace stub)
- Modify: `dashboard/routes/settings.py` (replace stub)
- Create: `dashboard/templates/keywords.html`
- Create: `dashboard/templates/groups.html`
- Create: `dashboard/templates/settings.html`
- Create: `tests/test_routes_management.py`

- [ ] **Step 1: Write failing tests `tests/test_routes_management.py`**

```python
import os
os.environ["DASHBOARD_USERNAME"] = "admin"
os.environ["DASHBOARD_PASSWORD"] = "pass"
os.environ["DB_PATH"] = ":memory:"

import base64
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from dashboard.main import app

client = TestClient(app)


def auth():
    return {"Authorization": "Basic " + base64.b64encode(b"admin:pass").decode()}


# Keywords

def test_list_keywords_returns_list():
    mock_kws = [{"id": 1, "phrase": "купить", "created_at": "2024-01-01"}]
    with patch("dashboard.routes.keywords.list_keywords", new=AsyncMock(return_value=mock_kws)):
        r = client.get("/api/keywords", headers=auth())
    assert r.status_code == 200
    assert r.json()[0]["phrase"] == "купить"


def test_add_keyword_calls_db():
    with patch("dashboard.routes.keywords.add_keyword", new=AsyncMock()) as mock_add:
        r = client.post("/api/keywords", json={"phrase": "продать"}, headers=auth())
    assert r.status_code == 200
    mock_add.assert_awaited_once()


def test_delete_keyword_calls_db():
    with patch("dashboard.routes.keywords.delete_keyword", new=AsyncMock()) as mock_del:
        r = client.delete("/api/keywords/5", headers=auth())
    assert r.status_code == 200
    mock_del.assert_awaited_once()


# Settings

def test_get_settings_returns_row():
    mock_s = {"id": 1, "tg_notifications_enabled": 0, "tg_notification_destination": "me"}
    with patch("dashboard.routes.settings.get_settings", new=AsyncMock(return_value=mock_s)):
        r = client.get("/api/settings", headers=auth())
    assert r.status_code == 200
    assert r.json()["tg_notification_destination"] == "me"


def test_update_settings_calls_db():
    with patch("dashboard.routes.settings.update_settings", new=AsyncMock()) as mock_upd:
        r = client.post(
            "/api/settings",
            json={"tg_notifications_enabled": 1, "tg_notification_destination": "@mybot"},
            headers=auth(),
        )
    assert r.status_code == 200
    mock_upd.assert_awaited_once()


# Groups

def test_list_groups_returns_list():
    mock_g = [{"id": 1, "telegram_id": 100, "title": "Чат", "handle": "test", "joined_at": "2024-01-01"}]
    with patch("dashboard.routes.groups.list_monitored_groups", new=AsyncMock(return_value=mock_g)):
        r = client.get("/api/groups", headers=auth())
    assert r.status_code == 200
    assert r.json()[0]["title"] == "Чат"
```

- [ ] **Step 2: Run test to confirm failure**

```bash
pytest tests/test_routes_management.py -v 2>&1 | head -25
```
Expected: FAIL — all three stubs return 404

- [ ] **Step 3: Replace stub `dashboard/routes/keywords.py`**

```python
from fastapi import APIRouter
from pydantic import BaseModel
import config
from db.operations import list_keywords, add_keyword, delete_keyword

router = APIRouter()


class KeywordIn(BaseModel):
    phrase: str


@router.get("/api/keywords")
async def get_keywords():
    return await list_keywords(config.DB_PATH)


@router.post("/api/keywords")
async def create_keyword(body: KeywordIn):
    await add_keyword(config.DB_PATH, body.phrase)
    return {"status": "ok"}


@router.delete("/api/keywords/{keyword_id}")
async def remove_keyword(keyword_id: int):
    await delete_keyword(config.DB_PATH, keyword_id)
    return {"status": "ok"}
```

- [ ] **Step 4: Replace stub `dashboard/routes/groups.py`**

```python
from fastapi import APIRouter
import config
from db.operations import list_monitored_groups

router = APIRouter()


@router.get("/api/groups")
async def get_groups():
    return await list_monitored_groups(config.DB_PATH)
```

- [ ] **Step 5: Replace stub `dashboard/routes/settings.py`**

```python
from fastapi import APIRouter
from pydantic import BaseModel
import config
from db.operations import get_settings, update_settings

router = APIRouter()


class SettingsIn(BaseModel):
    tg_notifications_enabled: int
    tg_notification_destination: str


@router.get("/api/settings")
async def read_settings():
    return await get_settings(config.DB_PATH)


@router.post("/api/settings")
async def write_settings(body: SettingsIn):
    await update_settings(config.DB_PATH, body.tg_notifications_enabled, body.tg_notification_destination)
    return {"status": "ok"}
```

- [ ] **Step 6: Write `dashboard/templates/keywords.html`**

```html
{% extends "base.html" %}
{% block content %}
<h2>Monitored Keywords</h2>
<form id="add-form" style="margin-bottom:16px;display:flex;gap:8px;">
  <input type="text" id="new-phrase" placeholder="e.g. купить" required>
  <button type="submit">Add</button>
</form>
<table>
  <thead><tr><th>ID</th><th>Phrase</th><th>Added</th><th>Action</th></tr></thead>
  <tbody id="kw-body"></tbody>
</table>
<script>
async function load() {
  const r = await fetch('/api/keywords');
  const kws = await r.json();
  document.getElementById('kw-body').innerHTML = kws.map(k =>
    `<tr><td>${k.id}</td><td>${k.phrase}</td><td>${k.created_at}</td>
     <td><button onclick="del(${k.id})">Delete</button></td></tr>`
  ).join('');
}
async function del(id) {
  await fetch('/api/keywords/' + id, {method: 'DELETE'});
  load();
}
document.getElementById('add-form').addEventListener('submit', async e => {
  e.preventDefault();
  const phrase = document.getElementById('new-phrase').value.trim();
  if (!phrase) return;
  await fetch('/api/keywords', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({phrase}),
  });
  document.getElementById('new-phrase').value = '';
  load();
});
load();
</script>
{% endblock %}
```

- [ ] **Step 7: Write `dashboard/templates/groups.html`**

```html
{% extends "base.html" %}
{% block content %}
<h2>Monitored Groups</h2>
<table>
  <thead><tr><th>ID</th><th>Telegram ID</th><th>Title</th><th>Handle</th><th>Joined At</th></tr></thead>
  <tbody id="groups-body"></tbody>
</table>
<script>
fetch('/api/groups').then(r => r.json()).then(gs => {
  document.getElementById('groups-body').innerHTML = gs.map(g =>
    `<tr>
      <td>${g.id}</td>
      <td>${g.telegram_id}</td>
      <td>${g.title || ''}</td>
      <td>${g.handle ? '<a href="https://t.me/' + g.handle + '" target="_blank">@' + g.handle + '</a>' : '-'}</td>
      <td>${g.joined_at}</td>
    </tr>`
  ).join('');
});
</script>
{% endblock %}
```

- [ ] **Step 8: Write `dashboard/templates/settings.html`**

```html
{% extends "base.html" %}
{% block content %}
<h2>Notification Settings</h2>
<div style="max-width:480px;">
  <label style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
    <input type="checkbox" id="notif-toggle">
    Enable Telegram Notifications
  </label>
  <label style="display:block;margin-bottom:6px;">Notification Destination:</label>
  <input type="text" id="notif-dest" placeholder="@handle, user_id, or 'me'">
  <br><br>
  <button onclick="save()">Save</button>
  <p id="status-msg"></p>
</div>
<script>
async function load() {
  const r = await fetch('/api/settings');
  const s = await r.json();
  document.getElementById('notif-toggle').checked = s.tg_notifications_enabled === 1;
  document.getElementById('notif-dest').value = s.tg_notification_destination;
}
async function save() {
  const enabled = document.getElementById('notif-toggle').checked ? 1 : 0;
  const dest = document.getElementById('notif-dest').value.trim();
  await fetch('/api/settings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({tg_notifications_enabled: enabled, tg_notification_destination: dest}),
  });
  document.getElementById('status-msg').textContent = 'Saved!';
  setTimeout(() => { document.getElementById('status-msg').textContent = ''; }, 2000);
}
load();
</script>
{% endblock %}
```

- [ ] **Step 9: Run all management tests and the full suite**

```bash
pytest tests/test_routes_management.py tests/test_routes_hits.py tests/test_dashboard_auth.py -v
```
Expected: All PASS

```bash
pytest tests/ -v --tb=short
```
Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add dashboard/routes/keywords.py dashboard/routes/groups.py dashboard/routes/settings.py \
        dashboard/templates/keywords.html dashboard/templates/groups.html dashboard/templates/settings.html \
        tests/test_routes_management.py
git commit -m "feat: management routes and pages for keywords, groups, and settings with AJAX controls"
```

---

### Task 10: Docker, Docker Compose, and GitHub Actions CI/CD

**Files:**
- Create: `Dockerfile.parser`
- Create: `Dockerfile.dashboard`
- Create: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `.github/workflows/build.yml`

- [ ] **Step 1: Write `Dockerfile.parser`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config.py ./
COPY parser/ parser/
COPY db/ db/
CMD ["python", "-m", "parser.main"]
```

- [ ] **Step 2: Write `Dockerfile.dashboard`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config.py ./
COPY dashboard/ dashboard/
COPY db/ db/
EXPOSE 8000
CMD ["uvicorn", "dashboard.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write `docker-compose.yml`**

```yaml
version: "3.9"

services:
  parser:
    build:
      context: .
      dockerfile: Dockerfile.parser
    env_file: .env
    volumes:
      - db_data:/app/db
    restart: unless-stopped

  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    env_file: .env
    volumes:
      - db_data:/app/db
    ports:
      - "8000:8000"
    restart: unless-stopped
    depends_on:
      - parser

volumes:
  db_data:
```

- [ ] **Step 4: Write `.dockerignore`**

```
__pycache__/
*.pyc
*.pyo
.env
*.session
tests/
.github/
docs/
*.md
dist/
build/
*.spec
```

- [ ] **Step 5: Write `.github/workflows/build.yml`**

```yaml
name: Build and Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --tb=short

  build:
    needs: test
    strategy:
      matrix:
        os: [macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: Build parser binary
        run: pyinstaller --onefile --name telelistener-parser parser/main.py
      - name: Build dashboard binary
        run: pyinstaller --onefile --name telelistener-dashboard dashboard/main.py
      - uses: actions/upload-artifact@v4
        with:
          name: binaries-${{ matrix.os }}
          path: dist/
```

- [ ] **Step 6: Run the full test suite one final time before committing**

```bash
pytest tests/ -v --tb=short
```
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add Dockerfile.parser Dockerfile.dashboard docker-compose.yml .dockerignore .github/workflows/build.yml
git commit -m "feat: Docker containers, Compose orchestration, GitHub Actions CI/CD with PyInstaller binaries"
```

---

## Spec Coverage Checklist

| Requirement | Task |
|---|---|
| Telethon UserBot (not BotFather) | Task 6 |
| Auto-join with exponential backoff | Task 4 |
| Randomized 60–300s anti-flood delay | Task 4 |
| Cyrillic gatekeeper on message text | Task 3 |
| Cyrillic gatekeeper on group title/description | Task 4 |
| Keyword exact case-insensitive match | Task 3 |
| Bot sender filter (`sender.bot`) | Task 6 |
| Spam link filter (`t.me/joinchat/`, `t.me/+`) | Task 3 |
| SQLite WAL mode + `timeout=10.0` | Task 1 |
| Full DB schema — 4 tables | Task 1 |
| Settings seed row `id=1, enabled=0, dest='me'` | Task 1 |
| Profile link with username → `t.me/username` | Task 3 |
| Profile link without username → `tg://user?id=...` | Task 3 |
| XSS sanitization on dashboard | Tasks 7, 8 |
| HTTP Basic Auth | Task 7 |
| Live hits feed with keyword highlight | Task 8 |
| Keywords CRUD in management console | Task 9 |
| Groups visualization | Task 9 |
| Notification toggle + destination field | Task 9 |
| AJAX POST settings (no page refresh) | Task 9 |
| Notification dispatch after every hit | Task 5, 6 |
| HTML notification with matching profile link rules | Task 5 |
| `try/except` around `send_message` | Task 5 |
| Network reconnect logic | Task 6 |
| Proxy config variables (MTProto/SOCKS5) | Task 1 (config.py) |
| No external non-Russian cloud dependencies | Arch (local SQLite only) |
| `requirements.txt` | Task 1 |
| `Dockerfile` + `docker-compose.yml` | Task 10 |
| GitHub Actions multi-platform PyInstaller | Task 10 |
