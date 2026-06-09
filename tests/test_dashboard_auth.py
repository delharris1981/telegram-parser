import os
os.environ["DASHBOARD_USERNAME"] = "testuser"
os.environ["DASHBOARD_PASSWORD"] = "testpass"
os.environ["DB_PATH"] = ":memory:"

import base64
import pytest
from fastapi.testclient import TestClient

from dashboard.main import app

client = TestClient(app, raise_server_exceptions=False)


def auth_header(user: str, password: str) -> dict:
    credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def test_unauthenticated_returns_401():
    r = client.get("/")
    assert r.status_code == 401


def test_wrong_credentials_returns_401():
    r = client.get("/", headers=auth_header("wrong", "bad"))
    assert r.status_code == 401


def test_correct_credentials_returns_200():
    r = client.get("/", headers=auth_header("testuser", "testpass"))
    assert r.status_code == 200
