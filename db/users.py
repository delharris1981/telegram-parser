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
