import os
os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "pass")
os.environ.setdefault("DB_PATH", ":memory:")

import base64
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

import config
from dashboard.main import app

client = TestClient(app)

_USERNAME = "hitsuser"
_PASSWORD = "hitspass"


def auth():
    return {"Authorization": "Basic " + base64.b64encode(f"{_USERNAME}:{_PASSWORD}".encode()).decode()}


def test_hits_api_returns_list():
    mock_hits = [
        {
            "id": 1, "group_title": "Чат", "sender_id": 99,
            "username": "ivan", "first_name": "Иван",
            "original_comment": "купить квартиру",
            "keyword_matched": "купить",
            "captured_at": "2024-01-01 12:00:00",
        }
    ]
    with patch("config.DASHBOARD_USERNAME", _USERNAME), \
         patch("config.DASHBOARD_PASSWORD", _PASSWORD), \
         patch("dashboard.routes.hits.list_hits", new=AsyncMock(return_value=mock_hits)):
        r = client.get("/api/hits", headers=auth())
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["username"] == "ivan"


def test_hits_api_sanitizes_xss():
    mock_hits = [
        {
            "id": 2, "group_title": "Чат", "sender_id": 99,
            "username": None, "first_name": "X",
            "original_comment": "<script>alert(1)</script>",
            "keyword_matched": "купить",
            "captured_at": "2024-01-01 12:00:00",
        }
    ]
    with patch("config.DASHBOARD_USERNAME", _USERNAME), \
         patch("config.DASHBOARD_PASSWORD", _PASSWORD), \
         patch("dashboard.routes.hits.list_hits", new=AsyncMock(return_value=mock_hits)):
        r = client.get("/api/hits", headers=auth())
    assert "<script>" not in r.text


def test_hits_api_requires_auth():
    r = client.get("/api/hits")
    assert r.status_code == 401
