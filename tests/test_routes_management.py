import os
import asyncio
import tempfile
import pathlib
from unittest.mock import AsyncMock, patch
from passlib.context import CryptContext
from fastapi.testclient import TestClient
from dashboard.main import app
import config
from db.users import create_user
from db.init import init_db

_USERNAME = os.environ.get("DASHBOARD_USERNAME", "testuser")
_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "testpass")
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _login(c, username=_USERNAME, password=_PASSWORD):
    c.post("/login", data={"username": username, "password": password})


def _make_user(username, password="pw"):
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "telelistener.db")
    asyncio.run(init_db(db_path))
    return asyncio.run(create_user(config.USERS_DB_PATH, username, _pwd.hash(password), db_path))


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


def test_admin_rename_user():
    uid = _make_user("rename_target")
    with TestClient(app) as c:
        _login(c)
        r = c.post(f"/api/admin/users/{uid}/username", json={"username": "rename_target2"})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_admin_rename_unknown_user_404():
    with TestClient(app) as c:
        _login(c)
        r = c.post("/api/admin/users/99999/username", json={"username": "whoever"})
    assert r.status_code == 404


def test_admin_rename_user_duplicate_400():
    _make_user("existing_name")
    uid = _make_user("to_be_renamed")
    with TestClient(app) as c:
        _login(c)
        r = c.post(f"/api/admin/users/{uid}/username", json={"username": "existing_name"})
    assert r.status_code == 400


def test_account_rename_self_non_admin():
    _make_user("plain_user")
    with TestClient(app) as c:
        _login(c, "plain_user", "pw")
        r = c.post("/api/account/username", json={"username": "plain_user_renamed"})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
