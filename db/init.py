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
