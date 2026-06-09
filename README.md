# TeleListener-RU

A Telegram keyword monitoring UserBot with a FastAPI web dashboard. Monitors public Russian Telegram groups for keyword matches, captures sender profiles and messages, stores results in a local SQLite database, and dispatches real-time Telegram notifications.

## Features

- **Keyword monitoring** — exact case-insensitive substring matching across public Russian Telegram groups
- **Russian-language gatekeeper** — Cyrillic regex filter skips non-Russian messages instantly (CPU-efficient)
- **Spam filtering** — ignores bot senders and broadcast invite links (`t.me/joinchat/`, `t.me/+`)
- **Auto-join with flood protection** — exponential backoff + randomized 60–300s delays between joins
- **Web dashboard** — live hits feed, keyword management, group viewer, notification settings (HTTP Basic Auth protected)
- **Telegram notifications** — optional real-time alerts sent to any handle, group ID, or `me` (Saved Messages)
- **XSS-safe** — all user content sanitized before rendering in the dashboard
- **Proxy support** — MTProto / SOCKS5 proxy config for regions with DPI throttling
- **SQLite WAL mode** — safe concurrent access between the parser process and the web server
- **Docker Compose** — one command to run both services with a shared database volume
- **GitHub Actions CI** — auto-builds standalone macOS and Windows binaries on every push

---

## Architecture

```
┌─────────────────────┐     SQLite WAL     ┌──────────────────────┐
│   parser/main.py    │ ←────────────────→ │ dashboard/main.py    │
│   (Telethon UserBot)│   telelistener.db   │   (FastAPI + Jinja2) │
└─────────────────────┘                    └──────────────────────┘
         │                                           │
   Telegram API                              Browser / HTTP
```

Three components share one database:
- **`parser/`** — background Telethon UserBot that listens for messages
- **`db/`** — shared SQLite layer (init + CRUD operations)
- **`dashboard/`** — FastAPI web app (API routes + HTML pages)

---

## Quick Start

### Prerequisites

- Python 3.10+
- A Telegram account with API credentials — get them at [my.telegram.org](https://my.telegram.org)

### 1. Clone and install

```bash
git clone https://github.com/delharris1981/telegram-parser.git
cd telegram-parser
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
SESSION_NAME=telelistener
KEYWORDS=купить,продать,квартира
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your_strong_password
DB_PATH=db/telelistener.db
```

Optional proxy (for regions with Telegram throttling):
```env
PROXY_TYPE=socks5
PROXY_HOST=127.0.0.1
PROXY_PORT=1080
```

### 3. Run

**Parser** (in one terminal):
```bash
python -m parser.main
```
On first run, Telethon will prompt for your phone number and verification code to create a session file.

**Dashboard** (in another terminal):
```bash
uvicorn dashboard.main:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000) and log in with your `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`.

---

## Docker Compose

Runs both services with a shared database volume:

```bash
cp .env.example .env   # fill in your credentials
docker-compose up --build
```

> **Note:** On first run the parser needs to authenticate with Telegram interactively. Run `python -m parser.main` once locally to generate the `.session` file, then mount it into the container or copy it to the project root before using Docker.

Dashboard will be available at [http://localhost:8000](http://localhost:8000).

---

## Dashboard Pages

| Page | URL | Description |
|---|---|---|
| Live Feed | `/` | Auto-refreshing table of keyword hits with user profile links |
| Keywords | `/keywords` | Add / delete monitored keywords |
| Groups | `/groups` | View all groups the parser has joined |
| Settings | `/settings` | Toggle Telegram notifications and set destination |

---

## Database Schema

```sql
keywords          (id, phrase, created_at)
monitored_groups  (id, telegram_id, title, handle, joined_at)
parsed_hits       (id, group_id, sender_id, username, first_name,
                   original_comment, keyword_matched, captured_at)
settings          (id, tg_notifications_enabled, tg_notification_destination)
```

SQLite is configured in **WAL mode** with `timeout=10.0` to prevent locking issues between the parser writer and dashboard reader.

---

## Telegram Notifications

When enabled, the parser sends an HTML-formatted message after every keyword hit:

```
Keyword hit: купить
Group: Недвижимость МСК
User: Иван @ivan_petrov
Message:
Хочу купить квартиру в центре
```

Profile links follow the same fallback rules as the dashboard:
- Username available → `https://t.me/username`
- No username → `tg://user?id=123456789`

Routing errors (blocked accounts, invalid destinations) are caught and logged — they never crash the parser.

---

## Building Standalone Binaries

GitHub Actions automatically builds macOS and Windows binaries on every push to `main`. Download them from the **Actions** tab → latest workflow run → **Artifacts**.

To build locally:
```bash
pip install pyinstaller
pyinstaller --onefile --name telelistener-parser parser/main.py
pyinstaller --onefile --name telelistener-dashboard dashboard/main.py
# Binaries output to dist/
```

---

## Running Tests

```bash
pytest tests/ -v
```

58 tests covering the database layer, message handlers, keyword detection, notification formatting, auto-join backoff logic, and all dashboard API routes.

---

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_API_ID` | Yes | — | Telegram API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | Yes | — | Telegram API Hash from my.telegram.org |
| `SESSION_NAME` | No | `telelistener` | Telethon session file name |
| `KEYWORDS` | Yes | — | Comma-separated keywords to monitor |
| `DASHBOARD_USERNAME` | No | `admin` | Dashboard login username |
| `DASHBOARD_PASSWORD` | **Yes** | — | Dashboard login password (required — no default accepted) |
| `DB_PATH` | No | `db/telelistener.db` | Path to SQLite database file |
| `PROXY_TYPE` | No | — | `socks5` or `mtproto` |
| `PROXY_HOST` | No | — | Proxy host |
| `PROXY_PORT` | No | — | Proxy port |

---

## Security Notes

- The dashboard is protected by HTTP Basic Auth using timing-safe comparison (`secrets.compare_digest`)
- All user-supplied content (messages, usernames, group titles) is HTML-escaped before rendering
- The `.env` file and `*.session` files are excluded from Docker images and should never be committed
- Deploy behind a reverse proxy (nginx/Caddy) with HTTPS in production
