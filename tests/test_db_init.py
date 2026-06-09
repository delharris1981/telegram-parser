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
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
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
    await init_db(db_path)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM settings")
        row = await cursor.fetchone()
    assert row[0] == 1
