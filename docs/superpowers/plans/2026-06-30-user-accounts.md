# User Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full multi-tenant user accounts where each user gets their own isolated SQLite database, session-cookie auth, per-user Telegram parser, and admin UI — with the existing production DB becoming the seeded admin user's DB.

**Architecture:** A central `data/users.db` stores accounts (username, bcrypt hash, db_path). Session cookies (Starlette `SessionMiddleware`) replace HTTP Basic auth. Per-user Telegram clients are managed by `parser/manager.py` and started on demand from the dashboard. Existing code already passes `db_path` as a parameter throughout — tasks route it from the session instead of `config.DB_PATH`.

**Tech Stack:** FastAPI, Starlette SessionMiddleware, aiosqlite, passlib[bcrypt], itsdangerous, Jinja2, Telethon

## Global Constraints

- Python 3.11+; all async DB calls use `aiosqlite`
- Passwords hashed with `passlib[bcrypt]` — never stored plain
- `SESSION_SECRET` env var required; warn and fall back to `"dev-secret-change-me"` if unset
- `USERS_DB_PATH` env var defaults to `"data/users.db"`
- `config.DB_PATH` env var continues to identify the existing admin user's DB path
- Existing production DB is **never modified** — it becomes `admin.db_path` in the seed
- All tests use `pytest` + `pytest-asyncio`; no new test frameworks
- Commit to `dev` branch after every task

---

### Task 1: Add dependencies and create `db/users.py`

**Files:**
- Modify: `requirements.txt`
- Create: `db/users.py`
- Create: `tests/test_db_users.py`

**Interfaces:**
- Produces:
  - `init_users_db(users_db_path: str) -> None`
  - `create_user(users_db_path: str, username: str, password_hash: str, db_path: str) -> int` (returns new user id)
  - `get_user_by_username(users_db_path: str, username: str) -> Optional[dict]`
  - `get_user_by_id(users_db_path: str, user_id: int) -> Optional[dict]`
  - `list_users(users_db_path: str) -> list[dict]`
  - `delete_user(users_db_path: str, user_id: int) -> None`
  - `update_password(users_db_path: str, user_id: int, password_hash: str) -> None`

- [ ] **Step 1: Add dependencies to `requirements.txt`**

```text
passlib[bcrypt]==1.7.4
itsdangerous==2.2.0
```

Add both lines after the existing entries. Then run:
```bash
pip install passlib[bcrypt]==1.7.4 itsdangerous==2.2.0
```

- [ ] **Step 2: Write failing tests in `tests/test_db_users.py`**

```python
import pytest
import pytest_asyncio
from db.users import (
    init_users_db, create_user, get_user_by_username,
    get_user_by_id, list_users, delete_user, update_password,
)


@pytest_asyncio.fixture
async def users_db(tmp_path):
    path = str(tmp_path / "users.db")
    await init_users_db(path)
    return path


@pytest.mark.asyncio
async def test_create_and_fetch_user(users_db):
    uid = await create_user(users_db, "alice", "hash123", "data/alice/telelistener.db")
    user = await get_user_by_username(users_db, "alice")
    assert user is not None
    assert user["id"] == uid
    assert user["username"] == "alice"
    assert user["password_hash"] == "hash123"
    assert user["db_path"] == "data/alice/telelistener.db"


@pytest.mark.asyncio
async def test_get_user_by_id(users_db):
    uid = await create_user(users_db, "bob", "h", "data/bob/telelistener.db")
    user = await get_user_by_id(users_db, uid)
    assert user is not None
    assert user["username"] == "bob"


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_none(users_db):
    assert await get_user_by_username(users_db, "nobody") is None
    assert await get_user_by_id(users_db, 9999) is None


@pytest.mark.asyncio
async def test_list_users(users_db):
    await create_user(users_db, "u1", "h", "d1")
    await create_user(users_db, "u2", "h", "d2")
    users = await list_users(users_db)
    assert len(users) == 2
    assert users[0]["username"] == "u1"


@pytest.mark.asyncio
async def test_delete_user(users_db):
    uid = await create_user(users_db, "carol", "h", "d")
    await delete_user(users_db, uid)
    assert await get_user_by_id(users_db, uid) is None


@pytest.mark.asyncio
async def test_update_password(users_db):
    uid = await create_user(users_db, "dave", "old_hash", "d")
    await update_password(users_db, uid, "new_hash")
    user = await get_user_by_id(users_db, uid)
    assert user["password_hash"] == "new_hash"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_db_users.py -v
```
Expected: `ModuleNotFoundError: No module named 'db.users'`

- [ ] **Step 4: Create `db/users.py`**

```python
import pathlib
from typing import Optional
import aiosqlite

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    db_path       TEXT NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_users_db(users_db_path: str) -> None:
    pathlib.Path(users_db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(users_db_path, timeout=10.0) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def create_user(
    users_db_path: str, username: str, password_hash: str, db_path: str
) -> int:
    async with aiosqlite.connect(users_db_path, timeout=10.0) as db:
        cursor = await db.execute(
            "INSERT INTO users (username, password_hash, db_path) VALUES (?, ?, ?)",
            (username, password_hash, db_path),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_by_username(users_db_path: str, username: str) -> Optional[dict]:
    async with aiosqlite.connect(users_db_path, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, password_hash, db_path, created_at FROM users WHERE username=?",
            (username,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_id(users_db_path: str, user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(users_db_path, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, password_hash, db_path, created_at FROM users WHERE id=?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_users(users_db_path: str) -> list[dict]:
    async with aiosqlite.connect(users_db_path, timeout=10.0) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, db_path, created_at FROM users ORDER BY id"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_user(users_db_path: str, user_id: int) -> None:
    async with aiosqlite.connect(users_db_path, timeout=10.0) as db:
        await db.execute("DELETE FROM users WHERE id=?", (user_id,))
        await db.commit()


async def update_password(users_db_path: str, user_id: int, password_hash: str) -> None:
    async with aiosqlite.connect(users_db_path, timeout=10.0) as db:
        await db.execute(
            "UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id)
        )
        await db.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_db_users.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt db/users.py tests/test_db_users.py
git commit -m "feat: add db/users.py with bcrypt user account CRUD"
```

---

### Task 2: Update `config.py` and refactor `state.py`

**Files:**
- Modify: `config.py`
- Modify: `state.py`

**Interfaces:**
- Produces (config.py):
  - `config.SESSION_SECRET: str`
  - `config.USERS_DB_PATH: str`
- Produces (state.py):
  - `state.get_client(username: str) -> Optional[TelegramClient]`
  - `state.set_client(username: str, client: TelegramClient) -> None`
  - `state.clear_client(username: str) -> None`

- [ ] **Step 1: Add `SESSION_SECRET` and `USERS_DB_PATH` to `config.py`**

Add these lines after the `DASHBOARD_PASSWORD` block:

```python
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
if not SESSION_SECRET:
    import warnings
    warnings.warn(
        "SESSION_SECRET is not set. Sessions will not be secure. "
        "Set a strong random value via the SESSION_SECRET environment variable.",
        stacklevel=2,
    )
SESSION_SECRET = SESSION_SECRET or "dev-secret-change-me"

USERS_DB_PATH = os.getenv("USERS_DB_PATH", "data/users.db")
```

- [ ] **Step 2: Replace `state.py` with per-user dict**

Full replacement of `state.py`:

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add config.py state.py
git commit -m "feat: add SESSION_SECRET/USERS_DB_PATH to config; refactor state to per-user dict"
```

---

### Task 3: Rewrite `dashboard/auth.py` — session cookie auth

**Files:**
- Modify: `dashboard/auth.py`

**Interfaces:**
- Consumes: `state.get_client(username)` from Task 2
- Produces:
  - `require_auth(request: Request) -> dict` — returns `{"user_id": int, "username": str, "db_path": str}`; raises `HTTPException(303, headers={"Location": "/login"})` if not authenticated
  - `require_admin(user: dict = Depends(require_auth)) -> dict` — raises `HTTPException(403)` if `user["user_id"] != 1`
  - `get_db_path(user: dict = Depends(require_auth)) -> str`
  - `get_tg_client(user: dict = Depends(require_auth)) -> Optional[TelegramClient]`

- [ ] **Step 1: Rewrite `dashboard/auth.py`**

```python
from typing import Optional
from fastapi import Depends, HTTPException, Request
import state


def require_auth(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin(user: dict = Depends(require_auth)) -> dict:
    if user.get("user_id") != 1:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def get_db_path(user: dict = Depends(require_auth)) -> str:
    return user["db_path"]


def get_tg_client(user: dict = Depends(require_auth)) -> Optional[object]:
    return state.get_client(user["username"])
```

- [ ] **Step 2: Update `tests/conftest.py`** to add session env vars (must come before any app import)

Replace the full contents of `tests/conftest.py`:

```python
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.setdefault("SESSION_SECRET", "test-secret-key")
os.environ.setdefault("USERS_DB_PATH", os.path.join(_tmp, "test_users.db"))
os.environ.setdefault("DB_PATH", os.path.join(_tmp, "test_admin.db"))
os.environ.setdefault("DASHBOARD_USERNAME", "testuser")
os.environ.setdefault("DASHBOARD_PASSWORD", "testpass")

import pytest_asyncio
from db.init import init_db


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return db_path
```

- [ ] **Step 3: Rewrite `tests/test_dashboard_auth.py`**

```python
import os
# env vars already set by conftest.py

import pytest
from fastapi.testclient import TestClient
from dashboard.main import app


def test_unauthenticated_redirects_to_login():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/", allow_redirects=False)
        assert r.status_code == 303
        assert "/login" in r.headers.get("location", "")


def test_login_with_wrong_credentials_returns_400():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post("/login", data={"username": "testuser", "password": "wrongpassword"})
        assert r.status_code == 400


def test_login_with_correct_credentials_redirects_to_root():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post(
            "/login",
            data={"username": os.environ["DASHBOARD_USERNAME"], "password": os.environ["DASHBOARD_PASSWORD"]},
            allow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers.get("location") == "/"


def test_authenticated_request_returns_200():
    with TestClient(app, raise_server_exceptions=False) as c:
        c.post(
            "/login",
            data={"username": os.environ["DASHBOARD_USERNAME"], "password": os.environ["DASHBOARD_PASSWORD"]},
        )
        r = c.get("/")
        assert r.status_code == 200
```

- [ ] **Step 4: Run the auth tests** (they will fail until Task 4 completes — that's expected at this stage; verify they at least import cleanly)

```bash
pytest tests/test_dashboard_auth.py -v 2>&1 | head -30
```

Expected: import errors or failures related to missing `SessionMiddleware` / login route — that's fine, we add those in Task 4.

- [ ] **Step 5: Commit**

```bash
git add dashboard/auth.py tests/conftest.py tests/test_dashboard_auth.py
git commit -m "feat: rewrite dashboard auth to session cookies; update test scaffolding"
```

---

### Task 4: Overhaul `dashboard/main.py` — SessionMiddleware, login/logout, lifespan seed, templates

**Files:**
- Modify: `dashboard/main.py`
- Modify: `dashboard/templates/base.html`
- Create: `dashboard/templates/login.html`

**Interfaces:**
- Consumes: `init_users_db`, `get_user_by_username`, `create_user` from `db/users.py` (Task 1); `require_auth`, `require_admin` from `dashboard/auth.py` (Task 3); `config.SESSION_SECRET`, `config.USERS_DB_PATH`, `config.DB_PATH`, `config.DASHBOARD_USERNAME`, `config.DASHBOARD_PASSWORD` from Task 2
- Produces:
  - FastAPI app with `SessionMiddleware`
  - `GET /login` → renders `login.html`
  - `POST /login` (form: `username`, `password`) → validates against users.db, sets session, 303 → `/`
  - `GET /logout` → clears session, 303 → `/login`
  - Page routes `/`, `/keywords`, `/groups`, `/settings` pass `{"user": user}` to templates
  - Page routes `/admin/users`, `/account` (added in Task 8)
  - Lifespan: calls `init_users_db`, seeds admin if table empty

- [ ] **Step 1: Replace `dashboard/main.py`**

```python
import sys
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext

import config
from dashboard.auth import require_auth, require_admin
from dashboard.routes import hits, keywords, groups
from dashboard.routes import settings as settings_router
from db.users import init_users_db, get_user_by_username, create_user
from db.init import init_db

if getattr(sys, "frozen", False):
    BASE_DIR = pathlib.Path(sys._MEIPASS) / "dashboard"
else:
    BASE_DIR = pathlib.Path(__file__).parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_users_db(config.USERS_DB_PATH)
    existing = await get_user_by_username(config.USERS_DB_PATH, config.DASHBOARD_USERNAME)
    if not existing:
        await init_db(config.DB_PATH)
        await create_user(
            config.USERS_DB_PATH,
            config.DASHBOARD_USERNAME,
            _pwd.hash(config.DASHBOARD_PASSWORD),
            config.DB_PATH,
        )
    yield


app = FastAPI(title="TeleListener Dashboard", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)

app.include_router(hits.router)
app.include_router(keywords.router)
app.include_router(groups.router)
app.include_router(settings_router.router)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = await get_user_by_username(config.USERS_DB_PATH, username)
    if not user or not _pwd.verify(password, user["password_hash"]):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid username or password"},
            status_code=400,
        )
    request.session["user"] = {
        "user_id": user["id"],
        "username": user["username"],
        "db_path": user["db_path"],
    }
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "index.html", {"user": user})


@app.get("/keywords", response_class=HTMLResponse)
async def keywords_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "keywords.html", {"user": user})


@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "groups.html", {"user": user})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "settings.html", {"user": user})
```

Note: `/admin/users` and `/account` routes are added in Task 8 once admin router exists. Add these imports at that point:
```python
from dashboard.routes import admin as admin_router
from dashboard.routes import parser as parser_router
```

- [ ] **Step 2: Create `dashboard/templates/login.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TeleListener — Sign In</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --primary: #2563eb; --primary-h: #1d4ed8;
      --bg: #f1f5f9; --surface: #ffffff;
      --border: #e2e8f0; --text: #0f172a; --danger: #dc2626;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      background: var(--bg); color: var(--text);
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
    }
    .card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 36px; width: 360px;
    }
    .logo { display: flex; align-items: center; gap: 10px; margin-bottom: 28px; }
    .logo-box {
      width: 32px; height: 32px; background: var(--primary);
      border-radius: 8px; display: flex; align-items: center;
      justify-content: center; font-weight: 800; font-size: 14px; color: #fff;
    }
    .logo-name { font-weight: 700; font-size: 16px; }
    h2 { font-size: 18px; font-weight: 700; margin-bottom: 22px; }
    label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 5px; }
    .form-group { margin-bottom: 16px; }
    input[type=text], input[type=password] {
      width: 100%; padding: 8px 11px; border: 1px solid var(--border);
      border-radius: 7px; font-size: 13px; outline: none;
      transition: border .14s, box-shadow .14s;
    }
    input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
    .btn {
      width: 100%; padding: 9px; background: var(--primary); color: #fff;
      border: none; border-radius: 7px; font-size: 14px; font-weight: 600;
      cursor: pointer; margin-top: 4px; transition: background .14s;
    }
    .btn:hover { background: var(--primary-h); }
    .error {
      background: #fef2f2; color: var(--danger); border: 1px solid #fecaca;
      border-radius: 7px; padding: 10px 14px; font-size: 13px; margin-bottom: 16px;
    }
  </style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-box">TL</div>
    <span class="logo-name">TeleListener</span>
  </div>
  <h2>Sign in</h2>
  {% if error %}
  <div class="error">{{ error }}</div>
  {% endif %}
  <form method="post" action="/login">
    <div class="form-group">
      <label for="username">Username</label>
      <input type="text" id="username" name="username" required autofocus>
    </div>
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" name="password" required>
    </div>
    <button type="submit" class="btn">Sign in</button>
  </form>
</div>
</body>
</html>
```

- [ ] **Step 3: Update `dashboard/templates/base.html` nav**

In `base.html`, replace the nav section from `<div class="nav-gap"></div>` through `</nav>` with:

```html
  <div class="nav-gap"></div>
  {% if user is defined and user and user.user_id == 1 %}
  <a href="/admin/users" class="nav-link" id="nl-admin">Admin</a>
  {% endif %}
  <a href="/account" class="nav-link" id="nl-acct">{{ user.username if user is defined and user else '' }}</a>
  <a href="/logout" class="nav-link" style="color:#64748b;">Logout</a>
  <div class="nav-pill" id="parser-pill" style="cursor:pointer;" onclick="toggleParser()" title="Click to start/stop parser">
    <div class="pulse" id="ps-dot"></div><span id="ps-label">—</span>
  </div>
</nav>
```

In the `<script>` block of `base.html`, add after the nav-highlight block:

```js
  // Parser status
  let _parserRunning = false;
  async function loadParserStatus() {
    try {
      const r = await fetch('/api/parser/status').then(r => r.json());
      _parserRunning = r.status === 'running';
      document.getElementById('ps-dot').style.background = _parserRunning ? '#22c55e' : '#94a3b8';
      document.getElementById('ps-label').textContent = _parserRunning ? 'Live' : 'Stopped';
    } catch (_) {}
  }
  async function toggleParser() {
    const ep = _parserRunning ? '/api/parser/stop' : '/api/parser/start';
    await fetch(ep, { method: 'POST' }).catch(() => {});
    await loadParserStatus();
  }
  loadParserStatus();
  setInterval(loadParserStatus, 30000);
```

Also add to the nav-highlight block (after the existing `else if` lines):

```js
  else if (_p.startsWith('/admin'))   document.getElementById('nl-admin')?.classList.add('active');
  else if (_p.startsWith('/account')) document.getElementById('nl-acct')?.classList.add('active');
```

- [ ] **Step 4: Run the auth tests**

```bash
pytest tests/test_dashboard_auth.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard/main.py dashboard/templates/login.html dashboard/templates/base.html
git commit -m "feat: add SessionMiddleware, login/logout routes, admin seed on startup"
```

---

### Task 5: Update existing routes to use `get_db_path` / `get_tg_client`

**Files:**
- Modify: `dashboard/routes/hits.py`
- Modify: `dashboard/routes/keywords.py`
- Modify: `dashboard/routes/groups.py`
- Modify: `dashboard/routes/settings.py`

**Interfaces:**
- Consumes: `get_db_path`, `get_tg_client` from `dashboard/auth.py` (Task 3)
- All `config.DB_PATH` references replaced with `db_path: str = Depends(get_db_path)`
- All `state.tg_client` references replaced with `client = Depends(get_tg_client)`

- [ ] **Step 1: Replace `dashboard/routes/hits.py`**

```python
from fastapi import APIRouter, Depends
import config
from dashboard.auth import get_db_path
from db.operations import list_hits, count_hits, count_keywords, count_groups
from dashboard.sanitize import sanitize

router = APIRouter()


@router.get("/api/hits")
async def get_hits(limit: int = 100, db_path: str = Depends(get_db_path)):
    hits = await list_hits(db_path, limit=limit)
    for hit in hits:
        hit["original_comment"] = sanitize(hit.get("original_comment") or "")
    return hits


@router.get("/api/stats")
async def get_stats(db_path: str = Depends(get_db_path)):
    return {
        "hits": await count_hits(db_path),
        "keywords": await count_keywords(db_path),
        "groups": await count_groups(db_path),
    }
```

- [ ] **Step 2: Replace `dashboard/routes/keywords.py`**

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from dashboard.auth import get_db_path
from db.operations import list_keywords, add_keyword, update_keyword, delete_keyword

router = APIRouter()


class KeywordIn(BaseModel):
    phrase: str


@router.get("/api/keywords")
async def get_keywords(db_path: str = Depends(get_db_path)):
    return await list_keywords(db_path)


@router.post("/api/keywords")
async def create_keyword(body: KeywordIn, db_path: str = Depends(get_db_path)):
    await add_keyword(db_path, body.phrase.strip())
    return {"status": "ok"}


@router.put("/api/keywords/{keyword_id}")
async def edit_keyword(keyword_id: int, body: KeywordIn, db_path: str = Depends(get_db_path)):
    await update_keyword(db_path, keyword_id, body.phrase.strip())
    return {"status": "ok"}


@router.delete("/api/keywords/{keyword_id}")
async def remove_keyword(keyword_id: int, db_path: str = Depends(get_db_path)):
    await delete_keyword(db_path, keyword_id)
    return {"status": "ok"}
```

- [ ] **Step 3: Replace `dashboard/routes/settings.py`**

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from dashboard.auth import get_db_path
from db.operations import (
    get_settings, update_settings, get_api_config, update_api_config,
    get_auto_discovery_settings, update_auto_discovery_settings,
)

router = APIRouter()


class NotifSettingsIn(BaseModel):
    tg_notifications_enabled: int
    tg_notification_destination: str


class ApiConfigIn(BaseModel):
    api_id: int
    api_hash: str
    session_name: str
    proxy_type: str
    proxy_host: str
    proxy_port: int


class AutoDiscoveryIn(BaseModel):
    auto_discovery_enabled: int
    auto_discovery_min_members: int
    auto_discovery_interval_hours: int


@router.get("/api/settings")
async def read_settings(db_path: str = Depends(get_db_path)):
    return await get_settings(db_path)


@router.post("/api/settings")
async def write_settings(body: NotifSettingsIn, db_path: str = Depends(get_db_path)):
    await update_settings(db_path, body.tg_notifications_enabled, body.tg_notification_destination)
    return {"status": "ok"}


@router.get("/api/settings/api-config")
async def read_api_config(db_path: str = Depends(get_db_path)):
    row = await get_api_config(db_path)
    if row is None:
        return {"api_id": 0, "api_hash": "", "session_name": "telelistener",
                "proxy_type": "", "proxy_host": "", "proxy_port": 0}
    return row


@router.post("/api/settings/api-config")
async def write_api_config(body: ApiConfigIn, db_path: str = Depends(get_db_path)):
    await update_api_config(
        db_path,
        body.api_id,
        body.api_hash,
        body.session_name or "telelistener",
        body.proxy_type,
        body.proxy_host,
        body.proxy_port,
    )
    return {"status": "ok"}


@router.get("/api/settings/auto-discovery")
async def read_auto_discovery(db_path: str = Depends(get_db_path)):
    return await get_auto_discovery_settings(db_path)


@router.post("/api/settings/auto-discovery")
async def write_auto_discovery(body: AutoDiscoveryIn, db_path: str = Depends(get_db_path)):
    await update_auto_discovery_settings(
        db_path,
        body.auto_discovery_enabled,
        body.auto_discovery_min_members,
        body.auto_discovery_interval_hours,
    )
    return {"status": "ok"}
```

- [ ] **Step 4: Replace `dashboard/routes/groups.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from telethon.tl.types import Channel, Chat
from dashboard.auth import get_db_path, get_tg_client
from db.operations import (
    list_monitored_groups,
    add_joined_group, list_joined_groups, remove_joined_group,
    list_joined_group_telegram_ids,
)

router = APIRouter()


class JoinIn(BaseModel):
    handle: str
    title: str = ""
    telegram_id: int = 0
    member_count: int = 0


@router.get("/api/groups")
async def get_groups(db_path: str = Depends(get_db_path)):
    return await list_monitored_groups(db_path)


@router.get("/api/groups/joined")
async def get_joined(db_path: str = Depends(get_db_path)):
    return await list_joined_groups(db_path)


@router.delete("/api/groups/joined/{group_id}")
async def leave_group(
    group_id: int,
    db_path: str = Depends(get_db_path),
    client=Depends(get_tg_client),
):
    groups = await list_joined_groups(db_path)
    group = next((g for g in groups if g["id"] == group_id), None)
    if not group:
        raise HTTPException(404, "Group not found")
    if client:
        try:
            from telethon.tl.functions.channels import LeaveChannelRequest
            entity = await client.get_entity(int(group["telegram_id"]))
            await client(LeaveChannelRequest(entity))
        except Exception as exc:
            raise HTTPException(500, f"Could not leave group: {exc}")
    await remove_joined_group(db_path, group_id)
    return {"status": "ok"}


@router.post("/api/groups/sync")
async def sync_groups(db_path: str = Depends(get_db_path), client=Depends(get_tg_client)):
    if client is None:
        raise HTTPException(503, "Parser not connected to Telegram — configure credentials first")
    try:
        dialogs = await client.get_dialogs()
    except Exception as exc:
        raise HTTPException(500, str(exc))
    existing_ids = await list_joined_group_telegram_ids(db_path)
    added = 0
    for dialog in dialogs:
        entity = dialog.entity
        if not isinstance(entity, (Channel, Chat)):
            continue
        telegram_id = entity.id
        if telegram_id in existing_ids:
            continue
        title = getattr(entity, "title", "") or ""
        handle = getattr(entity, "username", None) or ""
        member_count = getattr(entity, "participants_count", 0) or 0
        await add_joined_group(db_path, telegram_id, title, handle, member_count)
        existing_ids.add(telegram_id)
        added += 1
    return {"synced": added}


@router.get("/api/groups/search")
async def search_groups(q: str, db_path: str = Depends(get_db_path), client=Depends(get_tg_client)):
    if client is None:
        raise HTTPException(503, "Parser not connected to Telegram — configure credentials first")
    try:
        from telethon.tl.functions.contacts import SearchRequest
        result = await client(SearchRequest(q=q, limit=25))
    except Exception as exc:
        raise HTTPException(500, str(exc))
    out = []
    for chat in result.chats:
        username = getattr(chat, "username", None)
        if not username:
            continue
        out.append({
            "telegram_id": chat.id,
            "title": getattr(chat, "title", ""),
            "handle": username,
            "member_count": getattr(chat, "participants_count", None),
            "is_channel": getattr(chat, "broadcast", False),
        })
    return out


@router.post("/api/groups/join")
async def join_group(body: JoinIn, db_path: str = Depends(get_db_path), client=Depends(get_tg_client)):
    if client is None:
        raise HTTPException(503, "Parser not connected to Telegram — configure credentials first")
    handle = body.handle.lstrip("@").strip()
    try:
        from telethon.tl.functions.channels import JoinChannelRequest
        entity = await client.get_entity(handle)
        await client(JoinChannelRequest(entity))
        entity = await client.get_entity(handle)
        telegram_id = entity.id
        title = getattr(entity, "title", handle)
        member_count = getattr(entity, "participants_count", None)
        if member_count is None:
            member_count = body.member_count or 0
    except Exception as exc:
        raise HTTPException(500, f"Could not join group: {exc}")
    await add_joined_group(db_path, telegram_id, title, handle, member_count)
    return {"status": "ok", "title": title, "telegram_id": telegram_id}
```

- [ ] **Step 5: Update `tests/test_routes_hits.py`** — replace HTTP Basic auth with session login

```python
import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from dashboard.main import app

_USERNAME = os.environ.get("DASHBOARD_USERNAME", "testuser")
_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "testpass")


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
    with TestClient(app) as c:
        c.post("/login", data={"username": _USERNAME, "password": _PASSWORD})
        with patch("dashboard.routes.hits.list_hits", new=AsyncMock(return_value=mock_hits)):
            r = c.get("/api/hits")
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
    with TestClient(app) as c:
        c.post("/login", data={"username": _USERNAME, "password": _PASSWORD})
        with patch("dashboard.routes.hits.list_hits", new=AsyncMock(return_value=mock_hits)):
            r = c.get("/api/hits")
    assert "<script>" not in r.text


def test_hits_api_requires_auth():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/hits", allow_redirects=False)
        assert r.status_code == 303
```

- [ ] **Step 6: Update `tests/test_routes_management.py`** — replace HTTP Basic auth with session login

```python
import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from dashboard.main import app

_USERNAME = os.environ.get("DASHBOARD_USERNAME", "testuser")
_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "testpass")


def _login(c):
    c.post("/login", data={"username": _USERNAME, "password": _PASSWORD})


def test_list_keywords():
    mock_kws = [{"id": 1, "phrase": "купить", "created_at": "2024-01-01"}]
    with TestClient(app) as c:
        _login(c)
        with patch("dashboard.routes.keywords.list_keywords", new=AsyncMock(return_value=mock_kws)):
            r = c.get("/api/keywords")
    assert r.status_code == 200
    assert r.json()[0]["phrase"] == "купить"


def test_add_keyword():
    with TestClient(app) as c:
        _login(c)
        with patch("dashboard.routes.keywords.add_keyword", new=AsyncMock()) as mock_add:
            r = c.post("/api/keywords", json={"phrase": "продать"})
    assert r.status_code == 200
    mock_add.assert_awaited_once()


def test_delete_keyword():
    with TestClient(app) as c:
        _login(c)
        with patch("dashboard.routes.keywords.delete_keyword", new=AsyncMock()) as mock_del:
            r = c.delete("/api/keywords/5")
    assert r.status_code == 200
    mock_del.assert_awaited_once()


def test_get_settings():
    mock_s = {"id": 1, "tg_notifications_enabled": 0, "tg_notification_destination": "me"}
    with TestClient(app) as c:
        _login(c)
        with patch("dashboard.routes.settings.get_settings", new=AsyncMock(return_value=mock_s)):
            r = c.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["tg_notification_destination"] == "me"


def test_update_settings():
    with TestClient(app) as c:
        _login(c)
        with patch("dashboard.routes.settings.update_settings", new=AsyncMock()) as mock_upd:
            r = c.post(
                "/api/settings",
                json={"tg_notifications_enabled": 1, "tg_notification_destination": "@mybot"},
            )
    assert r.status_code == 200
    mock_upd.assert_awaited_once()


def test_list_groups():
    mock_g = [{"id": 1, "telegram_id": 100, "title": "Чат", "handle": "test", "joined_at": "2024-01-01"}]
    with TestClient(app) as c:
        _login(c)
        with patch("dashboard.routes.groups.list_monitored_groups", new=AsyncMock(return_value=mock_g)):
            r = c.get("/api/groups")
    assert r.status_code == 200
    assert r.json()[0]["title"] == "Чат"
```

- [ ] **Step 7: Run all route tests**

```bash
pytest tests/test_dashboard_auth.py tests/test_routes_hits.py tests/test_routes_management.py -v
```
Expected: all tests PASS

- [ ] **Step 8: Commit**

```bash
git add dashboard/routes/hits.py dashboard/routes/keywords.py \
        dashboard/routes/groups.py dashboard/routes/settings.py \
        tests/test_routes_hits.py tests/test_routes_management.py
git commit -m "feat: replace config.DB_PATH with session-based get_db_path in all routes"
```

---

### Task 6: Refactor `parser/client.py` and `parser/main.py` to accept `db_path`

**Files:**
- Modify: `parser/client.py`
- Modify: `parser/main.py`

**Interfaces:**
- Produces:
  - `create_client(db_path: str) -> TelegramClient`
  - `on_new_message(event, client: TelegramClient, db_path: str) -> None`
  - `run_retention_purge(db_path: str) -> None`
  - `run_auto_discovery(client, db_path: str) -> None`
  - `run_parser_loop(username: str, db_path: str) -> None`

- [ ] **Step 1: Replace `parser/client.py`**

```python
import logging
import pathlib
from typing import Optional
from telethon import TelegramClient
from telethon.errors import FloodWaitError

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
    session_name = (
        (db_cfg["session_name"] if db_cfg and db_cfg["session_name"] else None)
        or config.SESSION_NAME
    )

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

    session_dir = str(pathlib.Path(db_path).parent)
    session_path = f"{session_dir}/{session_name}"
    return TelegramClient(session_path, api_id, api_hash, proxy=proxy)


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
```

- [ ] **Step 2: Replace `parser/main.py`**

```python
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
```

- [ ] **Step 3: Run existing parser tests to check nothing broke**

```bash
pytest tests/test_handlers.py tests/test_notifications.py tests/test_auto_join.py -v
```
Expected: all PASS (these tests don't touch `create_client` or `run_parser_loop` directly)

- [ ] **Step 4: Commit**

```bash
git add parser/client.py parser/main.py
git commit -m "feat: refactor parser client and loop to accept db_path param per user"
```

---

### Task 7: Create `parser/manager.py` and `dashboard/routes/parser.py`

**Files:**
- Create: `parser/manager.py`
- Create: `dashboard/routes/parser.py`
- Modify: `dashboard/main.py` (add parser router import)

**Interfaces:**
- Consumes: `run_parser_loop(username, db_path)` from Task 6; `state.clear_client` from Task 2
- Produces:
  - `start_parser(username: str, db_path: str) -> None`
  - `stop_parser(username: str) -> None`
  - `parser_status(username: str) -> str` — returns `"running"` or `"stopped"`
  - `GET /api/parser/status` → `{"status": "running"|"stopped"}`
  - `POST /api/parser/start` → `{"status": "started"}`
  - `POST /api/parser/stop` → `{"status": "stopped"}`

- [ ] **Step 1: Write failing test**

```python
# tests/test_parser_manager.py
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from parser.manager import start_parser, stop_parser, parser_status


@pytest.mark.asyncio
async def test_parser_status_stopped_by_default():
    assert parser_status("nouser") == "stopped"


@pytest.mark.asyncio
async def test_start_and_stop_parser():
    async def fake_loop(username, db_path):
        await asyncio.sleep(999)

    with patch("parser.manager.run_parser_loop", side_effect=fake_loop), \
         patch("parser.manager.init_db", new=AsyncMock()):
        await start_parser("alice", "data/alice/telelistener.db")
        assert parser_status("alice") == "running"
        await stop_parser("alice")
        assert parser_status("alice") == "stopped"


@pytest.mark.asyncio
async def test_start_parser_idempotent():
    async def fake_loop(username, db_path):
        await asyncio.sleep(999)

    with patch("parser.manager.run_parser_loop", side_effect=fake_loop), \
         patch("parser.manager.init_db", new=AsyncMock()):
        await start_parser("bob", "data/bob/telelistener.db")
        await start_parser("bob", "data/bob/telelistener.db")  # second call is no-op
        assert parser_status("bob") == "running"
        await stop_parser("bob")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_parser_manager.py -v
```
Expected: `ModuleNotFoundError: No module named 'parser.manager'`

- [ ] **Step 3: Create `parser/manager.py`**

```python
import asyncio
import state
from db.init import init_db
from parser.main import run_parser_loop

_tasks: dict[str, asyncio.Task] = {}


async def start_parser(username: str, db_path: str) -> None:
    task = _tasks.get(username)
    if task and not task.done():
        return  # already running
    await init_db(db_path)
    _tasks[username] = asyncio.create_task(
        run_parser_loop(username, db_path),
        name=f"parser-{username}",
    )


async def stop_parser(username: str) -> None:
    task = _tasks.pop(username, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    state.clear_client(username)


def parser_status(username: str) -> str:
    task = _tasks.get(username)
    return "running" if (task and not task.done()) else "stopped"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_parser_manager.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Create `dashboard/routes/parser.py`**

```python
from fastapi import APIRouter, Depends
from dashboard.auth import require_auth
from parser import manager

router = APIRouter()


@router.get("/api/parser/status")
async def status(user: dict = Depends(require_auth)):
    return {"status": manager.parser_status(user["username"])}


@router.post("/api/parser/start")
async def start(user: dict = Depends(require_auth)):
    await manager.start_parser(user["username"], user["db_path"])
    return {"status": "started"}


@router.post("/api/parser/stop")
async def stop(user: dict = Depends(require_auth)):
    await manager.stop_parser(user["username"])
    return {"status": "stopped"}
```

- [ ] **Step 6: Add parser router to `dashboard/main.py`**

Add to the imports section:
```python
from dashboard.routes import parser as parser_router
```

Add after the existing `app.include_router(settings_router.router)` line:
```python
app.include_router(parser_router.router)
```

- [ ] **Step 7: Run full test suite**

```bash
pytest -v
```
Expected: all existing tests PASS

- [ ] **Step 8: Commit**

```bash
git add parser/manager.py dashboard/routes/parser.py dashboard/main.py \
        tests/test_parser_manager.py
git commit -m "feat: add per-user parser manager and /api/parser/* endpoints"
```

---

### Task 8: Admin routes, account route, and UI templates

**Files:**
- Create: `dashboard/routes/admin.py`
- Create: `dashboard/templates/admin_users.html`
- Create: `dashboard/templates/account.html`
- Modify: `dashboard/main.py` (add admin router + new page routes)

**Interfaces:**
- Consumes: `require_admin`, `require_auth` (Task 3); `create_user`, `list_users`, `delete_user`, `update_password`, `get_user_by_id` (Task 1); `manager.stop_parser`, `manager.parser_status` (Task 7)
- Produces:
  - `GET /api/admin/users` → `[{id, username, db_path, created_at, parser_status}]`
  - `POST /api/admin/users` (body: `{username, password}`) → creates user + initializes their DB
  - `DELETE /api/admin/users/{user_id}` → stops parser + deletes user record
  - `POST /api/admin/users/{user_id}/password` (body: `{password}`) → resets password
  - `POST /api/account/password` (body: `{password}`) → changes own password
  - `GET /admin/users` page (admin only)
  - `GET /account` page

- [ ] **Step 1: Create `dashboard/routes/admin.py`**

```python
import pathlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
import config
from dashboard.auth import require_auth, require_admin
from db.users import create_user, list_users, delete_user, update_password, get_user_by_id
from db.init import init_db
from parser import manager

router = APIRouter()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CreateUserIn(BaseModel):
    username: str
    password: str


class PasswordIn(BaseModel):
    password: str


@router.get("/api/admin/users")
async def api_list_users(_: dict = Depends(require_admin)):
    users = await list_users(config.USERS_DB_PATH)
    return [
        {**u, "parser_status": manager.parser_status(u["username"])}
        for u in users
    ]


@router.post("/api/admin/users")
async def api_create_user(body: CreateUserIn, _: dict = Depends(require_admin)):
    db_path = str(pathlib.Path("data") / body.username / "telelistener.db")
    await init_db(db_path)
    await create_user(config.USERS_DB_PATH, body.username, _pwd.hash(body.password), db_path)
    return {"status": "ok"}


@router.delete("/api/admin/users/{user_id}")
async def api_delete_user(user_id: int, _: dict = Depends(require_admin)):
    if user_id == 1:
        raise HTTPException(400, "Cannot delete the admin account")
    user = await get_user_by_id(config.USERS_DB_PATH, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await manager.stop_parser(user["username"])
    await delete_user(config.USERS_DB_PATH, user_id)
    return {"status": "ok"}


@router.post("/api/admin/users/{user_id}/password")
async def api_reset_password(user_id: int, body: PasswordIn, _: dict = Depends(require_admin)):
    user = await get_user_by_id(config.USERS_DB_PATH, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await update_password(config.USERS_DB_PATH, user_id, _pwd.hash(body.password))
    return {"status": "ok"}


@router.post("/api/account/password")
async def api_change_own_password(body: PasswordIn, user: dict = Depends(require_auth)):
    await update_password(config.USERS_DB_PATH, user["user_id"], _pwd.hash(body.password))
    return {"status": "ok"}
```

- [ ] **Step 2: Create `dashboard/templates/admin_users.html`**

```html
{% extends "base.html" %}
{% block content %}
<div class="page-hd">
  <div class="page-title">User Management</div>
  <div class="page-sub">Create and manage dashboard accounts</div>
</div>

<div class="card">
  <div class="card-head"><span class="card-title">Users</span></div>
  <div class="tbl-wrap" id="user-list">
    <div class="empty"><div class="empty-msg">Loading…</div></div>
  </div>
</div>

<div class="card">
  <div class="card-head"><span class="card-title">Create User</span></div>
  <div class="card-body">
    <div class="form-row">
      <div class="form-group">
        <label for="new-username">Username</label>
        <input type="text" id="new-username" placeholder="alice">
      </div>
      <div class="form-group">
        <label for="new-password">Password</label>
        <input type="password" id="new-password" placeholder="••••••••">
      </div>
    </div>
    <button class="btn btn-primary" onclick="createUser()">Create User</button>
  </div>
</div>

<script>
async function loadUsers() {
  try {
    const users = await fetch('/api/admin/users').then(r => r.json());
    const el = document.getElementById('user-list');
    if (!users.length) {
      el.innerHTML = '<div class="empty"><div class="empty-msg">No users.</div></div>';
      return;
    }
    const rows = users.map(u => `<tr>
      <td class="fw-600">${u.username}</td>
      <td class="text-muted text-xs">${u.db_path}</td>
      <td><span class="badge ${u.parser_status === 'running' ? 'badge-green' : 'badge-slate'}">${u.parser_status}</span></td>
      <td class="text-muted text-xs">${fmt(u.created_at)}</td>
      <td style="white-space:nowrap;">
        <button class="btn btn-outline btn-xs" onclick="resetPw(${u.id})">Reset PW</button>
        ${u.id !== 1 ? `<button class="btn btn-danger btn-xs" style="margin-left:6px;" onclick="delUser(${u.id})">Delete</button>` : ''}
      </td>
    </tr>`).join('');
    el.innerHTML = `<table>
      <thead><tr><th>Username</th><th>DB Path</th><th>Parser</th><th>Created</th><th>Actions</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  } catch (_) {}
}

async function createUser() {
  const username = document.getElementById('new-username').value.trim();
  const password = document.getElementById('new-password').value;
  if (!username || !password) { toast('Username and password required', false); return; }
  const r = await fetch('/api/admin/users', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username, password}),
  });
  if (r.ok) {
    document.getElementById('new-username').value = '';
    document.getElementById('new-password').value = '';
    toast('User created');
    loadUsers();
  } else {
    const err = await r.json().catch(() => ({}));
    toast(err.detail || 'Failed to create user', false);
  }
}

async function delUser(id) {
  if (!confirm('Delete this user? Their data files remain on disk.')) return;
  const r = await fetch('/api/admin/users/' + id, {method: 'DELETE'});
  r.ok ? (toast('User deleted'), loadUsers()) : toast('Failed', false);
}

async function resetPw(id) {
  const pw = prompt('New password for user ' + id + ':');
  if (!pw) return;
  const r = await fetch('/api/admin/users/' + id + '/password', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({password: pw}),
  });
  r.ok ? toast('Password updated') : toast('Failed', false);
}

loadUsers();
</script>
{% endblock %}
```

- [ ] **Step 3: Create `dashboard/templates/account.html`**

```html
{% extends "base.html" %}
{% block content %}
<div class="page-hd">
  <div class="page-title">Account</div>
  <div class="page-sub">{{ user.username }}</div>
</div>

<div class="card" style="max-width: 420px;">
  <div class="card-head"><span class="card-title">Change Password</span></div>
  <div class="card-body">
    <div class="form-group">
      <label for="new-pw">New Password</label>
      <input type="password" id="new-pw" placeholder="••••••••">
    </div>
    <div class="form-group">
      <label for="confirm-pw">Confirm Password</label>
      <input type="password" id="confirm-pw" placeholder="••••••••">
    </div>
    <button class="btn btn-primary" onclick="changePw()">Update Password</button>
  </div>
</div>

<script>
async function changePw() {
  const pw = document.getElementById('new-pw').value;
  const conf = document.getElementById('confirm-pw').value;
  if (!pw) { toast('Enter a new password', false); return; }
  if (pw !== conf) { toast('Passwords do not match', false); return; }
  const r = await fetch('/api/account/password', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({password: pw}),
  });
  if (r.ok) {
    toast('Password updated');
    document.getElementById('new-pw').value = '';
    document.getElementById('confirm-pw').value = '';
  } else {
    toast('Failed to update password', false);
  }
}
</script>
{% endblock %}
```

- [ ] **Step 4: Add admin router and new page routes to `dashboard/main.py`**

Add to imports:
```python
from dashboard.routes import admin as admin_router
```

Add after the `parser_router` include line:
```python
app.include_router(admin_router.router)
```

Add new page routes (after the `/settings` route):
```python
@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, user: dict = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin_users.html", {"user": user})


@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "account.html", {"user": user})
```

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add dashboard/routes/admin.py dashboard/templates/admin_users.html \
        dashboard/templates/account.html dashboard/main.py
git commit -m "feat: add admin user management routes and UI; account password change"
```

---

### Task 9: Update top-level `main.py` and push

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Replace `main.py`**

The combined entry point no longer auto-starts the parser (users start it from the dashboard). DB init and user seeding now happen inside the FastAPI lifespan.

```python
"""Combined entry point: runs the Telegram parser and web dashboard in one process."""
import asyncio
import logging
import sys

import uvicorn

from dashboard.main import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def _run() -> None:
    uv_config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(uv_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(_run())
```

- [ ] **Step 2: Run full test suite one final time**

```bash
pytest -v
```
Expected: all tests PASS

- [ ] **Step 3: Bump VERSION and update CHANGELOG**

Change `VERSION` from `2.2` to `2.3`.

Add to `CHANGELOG.md` under `## [Unreleased]`:

```markdown
## [2.3] – 2026-06-30

### Added
- **Multi-tenant user accounts** – each user gets a fully isolated SQLite database for their keywords, groups, hits, and Telegram API credentials.
- **Session cookie auth** – HTTP Basic auth replaced with a proper login form and signed session cookies (`starlette.middleware.sessions.SessionMiddleware`).
- **Per-user Telegram parser** – `parser/manager.py` manages one Telethon client per user, started on demand from the dashboard nav.
- **Admin UI** – `/admin/users` page for the first account (id=1): create users, delete users, reset passwords.
- **Account page** – `/account` for all users: change own password.
- **Zero-migration production DB** – existing DB becomes the admin user's DB, seeded from `DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD` env vars on first boot.

### Changed
- `dashboard/auth.py`: rewritten — removed HTTP Basic, added `require_auth`, `require_admin`, `get_db_path`, `get_tg_client` FastAPI dependencies.
- `dashboard/main.py`: added `SessionMiddleware`, FastAPI lifespan for admin seed, login/logout routes, user context passed to all templates.
- `dashboard/routes/*.py`: all routes now receive `db_path` from session via `Depends(get_db_path)`.
- `parser/client.py`, `parser/main.py`: `db_path` passed as parameter rather than read from global config.
- `state.py`: refactored from single `tg_client` to per-user `_clients` dict.
- `main.py`: parser no longer auto-starts; users start it from the dashboard.

### New env vars
- `SESSION_SECRET` – required for session cookie signing (warns and falls back to insecure default if unset)
- `USERS_DB_PATH` – path to the central users database (default: `data/users.db`)
```

- [ ] **Step 4: Commit and push to dev**

```bash
git add main.py VERSION CHANGELOG.md
git commit -m "feat: complete user accounts — per-user DB, session auth, parser manager (v2.3)"
git push origin dev
```
