import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from parser.manager import start_parser, stop_parser, parser_status


@pytest.mark.asyncio
async def test_parser_status_stopped_by_default():
    assert parser_status("nouser") == "stopped"


@pytest.mark.asyncio
async def test_start_and_stop_parser():
    async def fake_loop(username, db_path):
        await asyncio.sleep(999)

    with patch("parser.manager.run_parser_loop", side_effect=fake_loop), \
         patch("parser.manager.init_db", new=AsyncMock()):
        await start_parser("alice", "data/alice/telelistener.db")
        assert parser_status("alice") == "running"
        await stop_parser("alice")
        assert parser_status("alice") == "stopped"


@pytest.mark.asyncio
async def test_start_parser_idempotent():
    async def fake_loop(username, db_path):
        await asyncio.sleep(999)

    with patch("parser.manager.run_parser_loop", side_effect=fake_loop), \
         patch("parser.manager.init_db", new=AsyncMock()):
        await start_parser("bob", "data/bob/telelistener.db")
        await start_parser("bob", "data/bob/telelistener.db")  # second call is no-op
        assert parser_status("bob") == "running"
        await stop_parser("bob")
