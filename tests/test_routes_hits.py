import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from dashboard.main import app

_USERNAME = os.environ.get("DASHBOARD_USERNAME", "testuser")
_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "testpass")


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
    with TestClient(app) as c:
        c.post("/login", data={"username": _USERNAME, "password": _PASSWORD})
        with patch("dashboard.routes.hits.list_hits", new=AsyncMock(return_value=mock_hits)):
            r = c.get("/api/hits")
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
    with TestClient(app) as c:
        c.post("/login", data={"username": _USERNAME, "password": _PASSWORD})
        with patch("dashboard.routes.hits.list_hits", new=AsyncMock(return_value=mock_hits)):
            r = c.get("/api/hits")
    assert "<script>" not in r.text


def test_hits_api_requires_auth():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/hits", allow_redirects=False)
        assert r.status_code == 303
