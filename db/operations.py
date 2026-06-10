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


async def update_keyword(db_path: str, keyword_id: int, phrase: str) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute("UPDATE keywords SET phrase=? WHERE id=?", (phrase, keyword_id))
        await db.commit()


async def delete_keyword(db_path: str, keyword_id: int) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute("DELETE FROM keywords WHERE id=?", (keyword_id,))
        await db.commit()


# --- Joined Groups (app-managed, searchable from dashboard) ---

async def add_joined_group(
    db_path: str, telegram_id: int, title: Optional[str], handle: Optional[str], member_count: Optional[int]
) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute(
            """INSERT INTO joined_groups (telegram_id, title, handle, member_count)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET title=excluded.title,
               handle=excluded.handle, member_count=excluded.member_count""",
            (telegram_id, title, handle, member_count),
        )
        await db.commit()


async def list_joined_groups(db_path: str) -> list[dict]:
    return await _fetchall(
        db_path,
        """SELECT jg.id, jg.telegram_id, jg.title, jg.handle, jg.member_count,
                  jg.joined_at, COUNT(ph.id) AS hit_count
           FROM joined_groups jg
           LEFT JOIN monitored_groups mg ON mg.telegram_id = jg.telegram_id
           LEFT JOIN parsed_hits ph ON ph.group_id = mg.id
           GROUP BY jg.id
           ORDER BY jg.joined_at DESC""",
    )


async def remove_joined_group(db_path: str, joined_group_id: int) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute("DELETE FROM joined_groups WHERE id=?", (joined_group_id,))
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


async def count_hits(db_path: str) -> int:
    row = await _fetchone(db_path, "SELECT COUNT(*) AS n FROM parsed_hits")
    return (row or {}).get("n", 0)


async def count_keywords(db_path: str) -> int:
    row = await _fetchone(db_path, "SELECT COUNT(*) AS n FROM keywords")
    return (row or {}).get("n", 0)


async def count_groups(db_path: str) -> int:
    row = await _fetchone(db_path, "SELECT COUNT(*) AS n FROM joined_groups")
    return (row or {}).get("n", 0)


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


# --- Auto-discovery settings ---

async def get_auto_discovery_settings(db_path: str) -> dict:
    row = await _fetchone(
        db_path,
        "SELECT auto_discovery_enabled, auto_discovery_min_members, "
        "auto_discovery_interval_hours, auto_discovery_last_run FROM settings WHERE id=1",
    )
    if row is None:
        return {
            "auto_discovery_enabled": 0,
            "auto_discovery_min_members": 500,
            "auto_discovery_interval_hours": 6,
            "auto_discovery_last_run": None,
        }
    return row


async def update_auto_discovery_settings(
    db_path: str, enabled: int, min_members: int, interval_hours: int
) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute(
            "UPDATE settings SET auto_discovery_enabled=?, auto_discovery_min_members=?, "
            "auto_discovery_interval_hours=? WHERE id=1",
            (enabled, min_members, interval_hours),
        )
        await db.commit()


async def set_auto_discovery_last_run(db_path: str) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute(
            "UPDATE settings SET auto_discovery_last_run=CURRENT_TIMESTAMP WHERE id=1"
        )
        await db.commit()


async def list_joined_group_telegram_ids(db_path: str) -> set:
    rows = await _fetchall(db_path, "SELECT telegram_id FROM joined_groups")
    return {r["telegram_id"] for r in rows}


async def purge_old_hits(db_path: str, days: int = 7) -> int:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        cursor = await db.execute(
            "DELETE FROM parsed_hits WHERE captured_at < datetime('now', ? || ' days')",
            (f"-{days}",),
        )
        await db.commit()
        return cursor.rowcount


# --- Settings ---

async def get_settings(db_path: str) -> Optional[dict]:
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


async def get_api_config(db_path: str) -> Optional[dict]:
    return await _fetchone(
        db_path,
        "SELECT api_id, api_hash, session_name, proxy_type, proxy_host, proxy_port FROM settings WHERE id=1",
    )


async def update_api_config(
    db_path: str,
    api_id: int,
    api_hash: str,
    session_name: str,
    proxy_type: str,
    proxy_host: str,
    proxy_port: int,
) -> None:
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute(
            """UPDATE settings SET api_id=?, api_hash=?, session_name=?,
               proxy_type=?, proxy_host=?, proxy_port=? WHERE id=1""",
            (api_id, api_hash, session_name, proxy_type, proxy_host, proxy_port),
        )
        await db.commit()
