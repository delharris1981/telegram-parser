import sqlite3
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from dashboard.main import app
from dashboard.auth import require_auth

_SQLITE_MAGIC = b"SQLite format 3\x00"


def _set_settings(db_path, enabled, destination):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE settings SET tg_notifications_enabled=?, tg_notification_destination=? WHERE id=1",
        (enabled, destination),
    )
    conn.commit()
    conn.close()


def _set_tg_session(db_path, session_str):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE settings SET tg_session=? WHERE id=1", (session_str,))
    conn.commit()
    conn.close()


@pytest_asyncio.fixture
async def client(test_db):
    user = {"user_id": 99, "username": "backupuser", "db_path": test_db}
    app.dependency_overrides[require_auth] = lambda: user
    with TestClient(app) as c:
        yield c, test_db, user
    app.dependency_overrides.pop(require_auth, None)


def test_export_returns_sqlite_file(client):
    c, db_path, _ = client
    r = c.get("/api/backup/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"
    assert len(r.content) > 0
    assert r.content[:16] == _SQLITE_MAGIC


def test_import_rejects_non_sqlite_file(client):
    c, _, _ = client
    r = c.post("/api/backup/import", files={"file": ("bad.db", b"not a db", "application/octet-stream")})
    assert r.status_code == 400


def test_import_round_trip_preserves_data(client):
    c, db_path, _ = client

    _set_settings(db_path, 1, "@restored_dest")

    with patch("parser.manager.stop_parser", new=AsyncMock()), \
         patch("parser.manager.start_parser", new=AsyncMock()):
        exported = c.get("/api/backup/export")
        assert exported.status_code == 200
        backup_bytes = exported.content

        # mutate the live db so we can tell import actually restored the backup
        _set_settings(db_path, 0, "@overwritten")

        r = c.post("/api/backup/import", files={"file": ("backup.db", backup_bytes, "application/octet-stream")})
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    r = c.get("/api/settings")
    assert r.status_code == 200
    settings = r.json()
    assert settings["tg_notification_destination"] == "@restored_dest"
    assert settings["tg_notifications_enabled"] == 1


def test_import_stops_parser_and_restarts_if_session_present(client):
    c, db_path, user = client
    _set_tg_session(db_path, "session-string")

    exported = c.get("/api/backup/export")
    backup_bytes = exported.content

    with patch("parser.manager.stop_parser", new=AsyncMock()) as mock_stop, \
         patch("parser.manager.start_parser", new=AsyncMock()) as mock_start:
        r = c.post("/api/backup/import", files={"file": ("backup.db", backup_bytes, "application/octet-stream")})
        assert r.status_code == 200
        mock_stop.assert_awaited_once_with(user["username"])
        mock_start.assert_awaited_once_with(user["username"], db_path)


def test_import_does_not_restart_parser_without_session(client):
    c, db_path, user = client
    # ensure no session saved (fresh test_db has empty tg_session by default)
    exported = c.get("/api/backup/export")
    backup_bytes = exported.content

    with patch("parser.manager.stop_parser", new=AsyncMock()) as mock_stop, \
         patch("parser.manager.start_parser", new=AsyncMock()) as mock_start:
        r = c.post("/api/backup/import", files={"file": ("backup.db", backup_bytes, "application/octet-stream")})
        assert r.status_code == 200
        mock_stop.assert_awaited_once_with(user["username"])
        mock_start.assert_not_awaited()
