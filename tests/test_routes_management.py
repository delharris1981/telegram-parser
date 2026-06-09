import os
os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "pass")
os.environ.setdefault("DB_PATH", ":memory:")

import base64
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from dashboard.main import app

_client = TestClient(app)

_AUTH = {"Authorization": "Basic " + base64.b64encode(b"admin:pass").decode()}


def _patched_auth():
    return patch.multiple(
        "config",
        DASHBOARD_USERNAME="admin",
        DASHBOARD_PASSWORD="pass",
    )


# --- Keywords ---

def test_list_keywords():
    mock_kws = [{"id": 1, "phrase": "купить", "created_at": "2024-01-01"}]
    with _patched_auth(), patch("dashboard.routes.keywords.list_keywords", new=AsyncMock(return_value=mock_kws)):
        r = _client.get("/api/keywords", headers=_AUTH)
    assert r.status_code == 200
    assert r.json()[0]["phrase"] == "купить"


def test_add_keyword():
    with _patched_auth(), patch("dashboard.routes.keywords.add_keyword", new=AsyncMock()) as mock_add:
        r = _client.post("/api/keywords", json={"phrase": "продать"}, headers=_AUTH)
    assert r.status_code == 200
    mock_add.assert_awaited_once()


def test_delete_keyword():
    with _patched_auth(), patch("dashboard.routes.keywords.delete_keyword", new=AsyncMock()) as mock_del:
        r = _client.delete("/api/keywords/5", headers=_AUTH)
    assert r.status_code == 200
    mock_del.assert_awaited_once()


# --- Settings ---

def test_get_settings():
    mock_s = {"id": 1, "tg_notifications_enabled": 0, "tg_notification_destination": "me"}
    with _patched_auth(), patch("dashboard.routes.settings.get_settings", new=AsyncMock(return_value=mock_s)):
        r = _client.get("/api/settings", headers=_AUTH)
    assert r.status_code == 200
    assert r.json()["tg_notification_destination"] == "me"


def test_update_settings():
    with _patched_auth(), patch("dashboard.routes.settings.update_settings", new=AsyncMock()) as mock_upd:
        r = _client.post(
            "/api/settings",
            json={"tg_notifications_enabled": 1, "tg_notification_destination": "@mybot"},
            headers=_AUTH,
        )
    assert r.status_code == 200
    mock_upd.assert_awaited_once()


# --- Groups ---

def test_list_groups():
    mock_g = [{"id": 1, "telegram_id": 100, "title": "Чат", "handle": "test", "joined_at": "2024-01-01"}]
    with _patched_auth(), patch("dashboard.routes.groups.list_monitored_groups", new=AsyncMock(return_value=mock_g)):
        r = _client.get("/api/groups", headers=_AUTH)
    assert r.status_code == 200
    assert r.json()[0]["title"] == "Чат"
