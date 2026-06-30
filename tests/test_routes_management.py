import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from dashboard.main import app

_USERNAME = os.environ.get("DASHBOARD_USERNAME", "testuser")
_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "testpass")


def _login(c):
    c.post("/login", data={"username": _USERNAME, "password": _PASSWORD})


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
