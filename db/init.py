import pathlib
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
    tg_notification_destination TEXT NOT NULL DEFAULT 'me',
    api_id INTEGER NOT NULL DEFAULT 0,
    api_hash TEXT NOT NULL DEFAULT '',
    session_name TEXT NOT NULL DEFAULT 'telelistener',
    proxy_type TEXT NOT NULL DEFAULT '',
    proxy_host TEXT NOT NULL DEFAULT '',
    proxy_port INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO settings (id, tg_notifications_enabled, tg_notification_destination,
    api_id, api_hash, session_name, proxy_type, proxy_host, proxy_port)
VALUES (1, 0, 'me', 0, '', 'telelistener', '', '', 0);

CREATE TABLE IF NOT EXISTS joined_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    title TEXT,
    handle TEXT,
    member_count INTEGER,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# Applied once to existing databases that predate the API-config columns.
_MIGRATIONS = [
    "ALTER TABLE settings ADD COLUMN api_id INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE settings ADD COLUMN api_hash TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE settings ADD COLUMN session_name TEXT NOT NULL DEFAULT 'telelistener'",
    "ALTER TABLE settings ADD COLUMN proxy_type TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE settings ADD COLUMN proxy_host TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE settings ADD COLUMN proxy_port INTEGER NOT NULL DEFAULT 0",
]


async def init_db(db_path: str) -> None:
    pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.executescript(SCHEMA)
        await db.commit()
        for sql in _MIGRATIONS:
            try:
                await db.execute(sql)
                await db.commit()
            except Exception:
                pass  # column already exists
