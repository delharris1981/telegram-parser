import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.setdefault("SESSION_SECRET", "test-secret-key")
os.environ.setdefault("USERS_DB_PATH", os.path.join(_tmp, "test_users.db"))
os.environ.setdefault("DB_PATH", os.path.join(_tmp, "test_admin.db"))
os.environ.setdefault("DASHBOARD_USERNAME", "testuser")
os.environ.setdefault("DASHBOARD_PASSWORD", "testpass")

# ponytail: passlib 1.7.4 is incompatible with bcrypt >= 4.0 (detect_wrap_bug is
# a closure, not patchable). Swap _pwd to sha256_crypt for tests only.
# Remove when passlib >= 1.7.5 ships or bcrypt is pinned < 4.
from passlib.context import CryptContext
import dashboard.main as _main
_main._pwd = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

import pytest_asyncio
from db.init import init_db


@pytest_asyncio.fixture
async def test_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return db_path
