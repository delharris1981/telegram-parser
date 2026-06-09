import pytest
from db.operations import (
    add_keyword, list_keywords, delete_keyword,
    add_monitored_group, list_monitored_groups, get_group_by_telegram_id,
    add_hit, list_hits,
    get_settings, update_settings,
)


@pytest.mark.asyncio
async def test_add_and_list_keywords(test_db):
    await add_keyword(test_db, "купить")
    await add_keyword(test_db, "продать")
    keywords = await list_keywords(test_db)
    phrases = [k["phrase"] for k in keywords]
    assert "купить" in phrases
    assert "продать" in phrases


@pytest.mark.asyncio
async def test_add_duplicate_keyword_is_ignored(test_db):
    await add_keyword(test_db, "купить")
    await add_keyword(test_db, "купить")  # must not raise
    keywords = await list_keywords(test_db)
    assert len([k for k in keywords if k["phrase"] == "купить"]) == 1


@pytest.mark.asyncio
async def test_delete_keyword(test_db):
    await add_keyword(test_db, "тест")
    keywords = await list_keywords(test_db)
    kid = next(k["id"] for k in keywords if k["phrase"] == "тест")
    await delete_keyword(test_db, kid)
    keywords = await list_keywords(test_db)
    assert not any(k["phrase"] == "тест" for k in keywords)


@pytest.mark.asyncio
async def test_add_and_get_monitored_group(test_db):
    await add_monitored_group(test_db, telegram_id=100, title="Тест Чат", handle="test_chat")
    group = await get_group_by_telegram_id(test_db, 100)
    assert group["title"] == "Тест Чат"
    assert group["handle"] == "test_chat"


@pytest.mark.asyncio
async def test_add_group_duplicate_ignored(test_db):
    await add_monitored_group(test_db, telegram_id=200, title="Чат", handle=None)
    await add_monitored_group(test_db, telegram_id=200, title="Чат 2", handle=None)
    groups = await list_monitored_groups(test_db)
    assert len([g for g in groups if g["telegram_id"] == 200]) == 1


@pytest.mark.asyncio
async def test_add_hit_and_list(test_db):
    await add_monitored_group(test_db, telegram_id=300, title="Источник", handle=None)
    group = await get_group_by_telegram_id(test_db, 300)
    await add_hit(
        test_db,
        group_id=group["id"],
        sender_id=99,
        username="ivan",
        first_name="Иван",
        original_comment="купить квартиру",
        keyword_matched="купить",
    )
    hits = await list_hits(test_db, limit=10)
    assert len(hits) == 1
    assert hits[0]["username"] == "ivan"
    assert hits[0]["keyword_matched"] == "купить"


@pytest.mark.asyncio
async def test_get_and_update_settings(test_db):
    settings = await get_settings(test_db)
    assert settings["tg_notifications_enabled"] == 0
    assert settings["tg_notification_destination"] == "me"
    await update_settings(test_db, enabled=1, destination="@mybot")
    settings = await get_settings(test_db)
    assert settings["tg_notifications_enabled"] == 1
    assert settings["tg_notification_destination"] == "@mybot"
