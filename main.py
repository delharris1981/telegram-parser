"""Combined entry point: runs the Telegram parser and web dashboard in one process."""
import asyncio
import logging
import sys

import uvicorn

import config
from db.init import init_db
from parser.main import run_parser_loop
from dashboard.main import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def _run() -> None:
    await init_db(config.DB_PATH)

    uv_config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(uv_config)

    # Dashboard starts immediately; parser loop waits until credentials are set.
    parser_task = asyncio.create_task(run_parser_loop())
    try:
        await server.serve()
    finally:
        parser_task.cancel()
        try:
            await parser_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(_run())
