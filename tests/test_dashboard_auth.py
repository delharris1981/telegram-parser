import os
# env vars already set by conftest.py

import pytest
from fastapi.testclient import TestClient
from dashboard.main import app


def test_unauthenticated_redirects_to_login():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/", allow_redirects=False)
        assert r.status_code == 303
        assert "/login" in r.headers.get("location", "")


def test_login_with_wrong_credentials_returns_400():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post("/login", data={"username": "testuser", "password": "wrongpassword"})
        assert r.status_code == 400


def test_login_with_correct_credentials_redirects_to_root():
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post(
            "/login",
            data={"username": os.environ["DASHBOARD_USERNAME"], "password": os.environ["DASHBOARD_PASSWORD"]},
            allow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers.get("location") == "/"


def test_authenticated_request_returns_200():
    with TestClient(app, raise_server_exceptions=False) as c:
        c.post(
            "/login",
            data={"username": os.environ["DASHBOARD_USERNAME"], "password": os.environ["DASHBOARD_PASSWORD"]},
        )
        r = c.get("/")
        assert r.status_code == 200
