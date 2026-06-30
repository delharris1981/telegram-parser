# User Accounts Design — TeleListener-RU

**Date:** 2026-06-30  
**Status:** Approved

## Overview

Add full multi-tenant user accounts to the TeleListener dashboard. Each user gets completely isolated data (keywords, groups, hits, API credentials) stored in their own SQLite database file. The existing production database is untouched — it becomes the admin user's DB.

## 1. Data Layer

### Central `data/users.db`

A new SQLite file at `data/users.db` holds only user account records:

```sql
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,        -- bcrypt via passlib
    db_path       TEXT NOT NULL,        -- e.g. data/alice/telelistener.db
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Per-user data DBs

Each user has their own `data/{username}/telelistener.db`, initialized with the existing `init_db` schema. No schema changes to any existing table.

### Seeding from env vars

On first boot, if `users.db` is empty and `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` env vars are set, the app auto-creates the admin user with `db_path = data/telelistener.db` (the existing production DB). This preserves all existing data with zero migration.

New users created via the admin UI get a fresh DB at `data/{username}/telelistener.db`.

## 2. Auth & Sessions

### Replacing HTTP Basic

`dashboard/auth.py` is rewritten. HTTP Basic auth is removed. The new flow:

- `GET /login` — renders login form
- `POST /login` — validates username + bcrypt hash against `users.db`, sets a signed session cookie containing `user_id`, `username`, `db_path`
- `GET /logout` — clears the session cookie, redirects to `/login`
- `require_auth` dependency — reads session cookie; if missing/invalid, redirects to `/login` (302) instead of returning 401

`SessionMiddleware` from Starlette (already a FastAPI transitive dependency) handles cookie signing. Secret key is read from a `SESSION_SECRET` env var (required; app refuses to start without it).

### db_path in request scope

All existing routes currently use `config.DB_PATH`. After this change they pull `db_path` from the session via a `get_db_path` dependency. No route logic changes — only the dependency source changes.

### New template

One new `templates/login.html` — a plain HTML form, no JS framework.

## 3. Parser Manager

### Current state

One global Telethon client started at process boot, connected to a single Telegram account.

### New design

`parser/manager.py` — a module-level dict:

```python
_clients: dict[str, asyncio.Task] = {}  # keyed by username
```

Two new API endpoints (auth-protected):

- `POST /api/parser/start` — reads API credentials from the session user's DB, spawns their Telethon client as an asyncio task, stores in `_clients[username]`
- `POST /api/parser/stop` — cancels and removes the task for the session user

The existing `parser/main.py` loop is unchanged except it accepts `db_path` as a parameter instead of reading from global config.

**Lifecycle:** Clients live in process memory. A server restart stops all parsers. Users restart their parser from a status indicator on the dashboard.

**Isolation:** Each client's event handler writes hits only to that user's `db_path`. No cross-user data access.

## 4. User Management UI

### `/admin/users` (admin only)

Visible only to the user with `id=1` in `users.db`. Features:

- List all users: username, DB path, parser status (running / stopped)
- Create user form: username + password → creates `data/{username}/telelistener.db`, runs `init_db`, inserts row into `users.db`
- Delete user: stops parser if running, removes from `users.db`. Data DB is left on disk (not deleted — safer).

### `/account` (all users)

- Change own password form

### Admin password reset

Admin can set a new password for any user from `/admin/users`.

## 5. Migration Path

| Step | What happens |
|------|-------------|
| Deploy new version | `users.db` doesn't exist yet |
| First boot | App detects empty `users.db`, reads `DASHBOARD_USERNAME` + `DASHBOARD_PASSWORD` env vars, creates admin user with `db_path = data/telelistener.db` |
| Existing data | Untouched — admin user's DB is the existing production file |
| New users | Admin creates via `/admin/users` UI |

## 6. New Dependencies

| Package | Purpose |
|---------|---------|
| `passlib[bcrypt]` | Password hashing |

`starlette` (SessionMiddleware) is already installed via FastAPI — no new install needed.

## 7. Files Affected

| File | Change |
|------|--------|
| `db/users.py` | New — users.db init + CRUD |
| `dashboard/auth.py` | Rewrite — HTTP Basic → session cookie |
| `dashboard/main.py` | Add SessionMiddleware, seed admin on startup |
| `parser/manager.py` | New — per-user client lifecycle |
| `parser/main.py` | Accept `db_path` param instead of global config |
| `dashboard/routes/*.py` | Switch `config.DB_PATH` → `get_db_path()` dependency |
| `dashboard/routes/admin.py` | New — user management endpoints |
| `dashboard/templates/login.html` | New |
| `dashboard/templates/admin_users.html` | New |
| `dashboard/templates/account.html` | New |
| `config.py` | Add `SESSION_SECRET`, `USERS_DB_PATH` |
