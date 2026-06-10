# TeleListener-RU

A Telegram keyword monitoring UserBot with a FastAPI web dashboard. Monitors public Russian Telegram groups for keyword matches, captures sender profiles and messages, stores results in a local SQLite database, and dispatches real-time Telegram notifications.

**Ships as a single self-contained binary** — no Python or dependencies required on the target machine.

---

## Features

- **Keyword monitoring** — case-insensitive substring matching across public Russian Telegram groups
- **Auto-discovery** — automatically searches Telegram using your keywords and joins matching Russian groups on a configurable schedule (no manual searching required)
- **Russian-language gatekeeper** — Cyrillic regex filter skips non-Russian messages instantly
- **Spam filtering** — ignores bot senders and broadcast invite links
- **Auto-join with flood protection** — exponential backoff + randomised 60–300 s delays between joins
- **Web dashboard** — live hits feed, keyword management, group viewer, settings — all in a browser
- **Inline credential setup** — enter API credentials directly in the Settings page; no `.env` editing
- **Telegram notifications** — optional real-time alerts to any handle, group ID, or `me` (Saved Messages)
- **Proxy support** — SOCKS5 / HTTP proxy configurable from the dashboard
- **SQLite WAL mode** — safe concurrent access between the parser and the dashboard
- **Docker Compose** — one command to run the full stack
- **Pre-built Docker images** — published to GitHub Container Registry on every release
- **GitHub Actions CI** — auto-builds standalone macOS and Windows binaries and Docker images on every push

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  telelistener (binary)                │
│                                                      │
│   ┌─────────────────────┐   ┌────────────────────┐  │
│   │ Telethon parser loop │   │ FastAPI dashboard  │  │
│   │  (asyncio task)     │   │  (uvicorn server)  │  │
│   └──────────┬──────────┘   └────────┬───────────┘  │
│              │                       │               │
│              └──────── SQLite ───────┘               │
│                    telelistener.db                   │
└──────────────────────────────────────────────────────┘
```

Both services run in the same process on the same asyncio event loop. The dashboard starts immediately on port 8000; the parser retries every 30 s until credentials are saved.

---

## Installation

### Option A — macOS (pre-built binary)

1. Go to the [Releases](https://github.com/delharris1981/telegram-parser/releases) page and download `telelistener-macos`.
2. Open Terminal and make the file executable:
   ```bash
   chmod +x ~/Downloads/telelistener-macos
   ```
3. Run it:
   ```bash
   ~/Downloads/telelistener-macos
   ```
   > **Gatekeeper warning?** If macOS blocks the binary, right-click it in Finder → Open → Open. You only need to do this once.
4. The dashboard starts on **[http://localhost:8000](http://localhost:8000)** — open it in your browser and follow the [First-time setup](#first-time-setup) steps below.

The database and session file are stored in a `db/` folder next to the binary.

---

### Option B — Windows (pre-built binary)

1. Go to the [Releases](https://github.com/delharris1981/telegram-parser/releases) page and download `telelistener-windows.exe`.
2. Double-click the `.exe` to run it. A console window will open.
3. Open **[http://localhost:8000](http://localhost:8000)** in your browser and follow the [First-time setup](#first-time-setup) steps.

> **Windows Defender warning?** Click "More info" → "Run anyway". The binary is unsigned but safe — you can review the source and build it yourself (see [Building binaries](#building-binaries)).

The database and session file are stored in a `db\` folder next to the `.exe`.

---

### Option C — Docker

Docker is the recommended approach for running TeleListener on a server. Pre-built images are published to the GitHub Container Registry on every release — no cloning or building required.

**Requirements:** Docker + Docker Compose

#### C1 — Pull the pre-built image (recommended)

Create a `docker-compose.yml` in an empty folder:

```yaml
version: "3.9"

services:
  telelistener:
    image: ghcr.io/delharris1981/telegram-parser:latest
    volumes:
      - db_data:/app/data
    ports:
      - "8000:8000"
    restart: unless-stopped

volumes:
  db_data:
```

Then start it:

```bash
docker-compose up
```

The dashboard is available at **[http://localhost:8000](http://localhost:8000)**.

To pin to a specific release instead of `latest`, replace the tag (e.g. `ghcr.io/delharris1981/telegram-parser:v1.4.42`). All available tags are listed on the [packages page](https://github.com/delharris1981?tab=packages).

#### C2 — Build from source

```bash
git clone https://github.com/delharris1981/telegram-parser.git
cd telegram-parser
docker-compose up --build
```

---

> **First-time Telegram authentication:** Telethon requires an interactive phone + code login on the very first run. Keep the terminal open (do **not** use `-d` on first launch) and follow the prompts that appear after you save your API credentials in Settings. Once the session file is written, you can restart with `docker-compose up -d` for headless operation.

The database is stored in a named Docker volume (`db_data`) so it survives container restarts.

**Useful commands:**

```bash
# Pull the latest image
docker pull ghcr.io/delharris1981/telegram-parser:latest

# Start in background (after first auth is done)
docker-compose up -d

# View live logs
docker-compose logs -f

# Stop
docker-compose down

# Stop and delete the database volume (full reset)
docker-compose down -v
```

---

### Option D — Run from source

Use this for development or when you want full control on a VPS.

**Requirements:** Python 3.11+

```bash
git clone https://github.com/delharris1981/telegram-parser.git
cd telegram-parser
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 main.py
```

The dashboard starts on **[http://localhost:8000](http://localhost:8000)**.

---

### Option E — Self-hosting on a VPS (Linux server)

Running TeleListener on a Linux VPS (Ubuntu/Debian) with Docker is the simplest approach. The pre-built image means you don't need to clone the repo or install Python.

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Create a working directory
mkdir telelistener && cd telelistener

# Create docker-compose.yml
cat > docker-compose.yml <<'EOF'
version: "3.9"

services:
  telelistener:
    image: ghcr.io/delharris1981/telegram-parser:latest
    volumes:
      - db_data:/app/data
    ports:
      - "8000:8000"
    restart: unless-stopped

volumes:
  db_data:
EOF

docker-compose up
```

Complete first-time Telegram authentication in the terminal (phone + SMS code), then detach:

```bash
# Ctrl+C to stop, then restart in background
docker-compose up -d
```

To update to the latest image in future:

```bash
docker-compose pull && docker-compose up -d
```

**Expose the dashboard publicly** (optional) using a reverse proxy. Example with nginx:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Add HTTPS with Certbot:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## First-time setup

This applies to all installation methods.

### 1. Get Telegram API credentials

Visit [my.telegram.org/apps](https://my.telegram.org/apps), log in with your Telegram account, and create an app. Note the **API ID** (a number) and **API Hash** (a 32-character hex string).

### 2. Enter credentials in the dashboard

1. Open **[http://localhost:8000/settings](http://localhost:8000/settings)**
2. Fill in your **API ID**, **API Hash**, and **Session Name** (any name, e.g. `telelistener`)
3. Click **Save Credentials**

The parser will attempt to connect within 30 seconds.

### 3. Authenticate with Telegram

When the parser connects for the first time, Telethon will prompt you in the **terminal** (or console window):

```
Enter phone number:  +44712345678
Enter code:          12345
```

Enter your phone number in international format, then the code Telegram sends you. The session is saved to the `db/` folder — you won't need to do this again.

### 4. Add keywords

Open **[http://localhost:8000/keywords](http://localhost:8000/keywords)** and add the Russian phrases you want to monitor. You can paste multiple keywords at once (comma or newline separated).

### 5. Find groups to monitor

**Manually:** Go to **[http://localhost:8000/groups](http://localhost:8000/groups)**, search for public groups by keyword, and click **Join** to start monitoring them.

**Automatically:** Enable **Auto-Discovery** in Settings (see below).

---

## Auto-Discovery

Auto-Discovery removes the need to manually search for groups. When enabled, the parser runs a background task that:

1. Takes each of your configured keywords and searches Telegram for matching public groups
2. Filters for Russian-language groups (Cyrillic title check) above your minimum member count
3. Automatically joins new groups using flood-safe delays (60–300 s between each join)
4. Records joined groups in the dashboard immediately

**To configure:**

1. Go to **Settings → Auto-Discovery**
2. Toggle **Enable Automatic Group Discovery** on
3. Set **Minimum Members** (groups below this are skipped — default: 500)
4. Set **Interval (hours)** (how often to run — default: 6)
5. Click **Save Auto-Discovery**

The "Last ran" timestamp updates after each discovery run.

---

## Dashboard

| Page | URL | Description |
|---|---|---|
| Live Feed | `/` | Auto-refreshing keyword hits with stats cards (total hits, active keywords, groups monitored) |
| Keywords | `/keywords` | Add / edit / delete monitored keywords. Bulk add with comma or newline separation. |
| Groups | `/groups` | Search and join public groups manually; view auto-joined groups with hit counts; leave groups |
| Settings | `/settings` | API credentials, notifications, auto-discovery configuration |

---

## Telegram Notifications

When enabled in Settings, the parser sends an HTML-formatted message after every keyword hit:

```
Keyword hit: купить
Group: Недвижимость МСК
User: Иван @ivan_petrov
Message:
Хочу купить квартиру в центре
```

Set **Notification Destination** to `me` to receive alerts in your own Saved Messages, or enter any username, group ID, or channel handle.

---

## Database schema

```sql
keywords          (id, phrase, created_at)
monitored_groups  (id, telegram_id, title, handle, joined_at)
parsed_hits       (id, group_id, sender_id, username, first_name,
                   original_comment, keyword_matched, captured_at)
joined_groups     (id, telegram_id, title, handle, member_count, joined_at)
settings          (id, tg_notifications_enabled, tg_notification_destination,
                   api_id, api_hash, session_name, proxy_type, proxy_host, proxy_port,
                   auto_discovery_enabled, auto_discovery_min_members,
                   auto_discovery_interval_hours, auto_discovery_last_run)
```

SQLite is configured in **WAL mode** so the parser and dashboard can access the database concurrently without locking conflicts.

---

## Building binaries and Docker images

GitHub Actions builds both standalone binaries and Docker images automatically on every push to `main`.

- **Binaries** — download the latest from the [Releases](https://github.com/delharris1981/telegram-parser/releases) page.
- **Docker images** — published to the [GitHub Container Registry](https://github.com/delharris1981?tab=packages) as `ghcr.io/delharris1981/telegram-parser:latest`.

To build a binary locally:

```bash
pip install -r requirements.txt
pyinstaller telelistener.spec
# Output: dist/telelistener  (macOS/Linux)  or  dist/telelistener.exe  (Windows)
```

To build the Docker image locally:

```bash
docker build -t telelistener .
docker run -p 8000:8000 -v telelistener_db:/app/data telelistener
```

---

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

58 tests covering the database layer, message handlers, keyword detection, notification formatting, and auto-join backoff logic.

---

## Security notes

- All user-supplied content (messages, usernames, group titles) is HTML-escaped before rendering in the dashboard
- The `.session` file grants full access to your Telegram account — keep it private and never commit it
- Deploy behind a reverse proxy (nginx / Caddy) with HTTPS when exposing the dashboard on a public server
- The `db/` folder contains your session and database — back it up regularly on a server deployment
