import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.setdefault("SESSION_SECRET", "test-secret-key")
os.environ.setdefault("USERS_DB_PATH", os.path.join(_tmp, "test_users.db"))
os.environ.setdefault("DB_PATH", os.path.join(_tmp, "test_admin.db"))
os.environ.setdefault("DASHBOARD_USERNAME", "testuser")
os.environ.setdefault("DASHBOARD_PASSWORD", "testpass")

import pytest_asyncio
from db.init import init_db


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return db_path
