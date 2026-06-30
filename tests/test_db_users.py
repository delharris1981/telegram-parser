import pytest
import pytest_asyncio
from db.users import (
    init_users_db, create_user, get_user_by_username,
    get_user_by_id, list_users, delete_user, update_password,
)


@pytest_asyncio.fixture
async def users_db(tmp_path):
    path = str(tmp_path / "users.db")
    await init_users_db(path)
    return path


@pytest.mark.asyncio
async def test_create_and_fetch_user(users_db):
    uid = await create_user(users_db, "alice", "hash123", "data/alice/telelistener.db")
    user = await get_user_by_username(users_db, "alice")
    assert user is not None
    assert user["id"] == uid
    assert user["username"] == "alice"
    assert user["password_hash"] == "hash123"
    assert user["db_path"] == "data/alice/telelistener.db"


@pytest.mark.asyncio
async def test_get_user_by_id(users_db):
    uid = await create_user(users_db, "bob", "h", "data/bob/telelistener.db")
    user = await get_user_by_id(users_db, uid)
    assert user is not None
    assert user["username"] == "bob"


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_none(users_db):
    assert await get_user_by_username(users_db, "nobody") is None
    assert await get_user_by_id(users_db, 9999) is None


@pytest.mark.asyncio
async def test_list_users(users_db):
    await create_user(users_db, "u1", "h", "d1")
    await create_user(users_db, "u2", "h", "d2")
    users = await list_users(users_db)
    assert len(users) == 2
    assert users[0]["username"] == "u1"


@pytest.mark.asyncio
async def test_delete_user(users_db):
    uid = await create_user(users_db, "carol", "h", "d")
    await delete_user(users_db, uid)
    assert await get_user_by_id(users_db, uid) is None


@pytest.mark.asyncio
async def test_update_password(users_db):
    uid = await create_user(users_db, "dave", "old_hash", "d")
    await update_password(users_db, uid, "new_hash")
    user = await get_user_by_id(users_db, uid)
    assert user["password_hash"] == "new_hash"
