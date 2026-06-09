import asyncio
import logging
import sys

from telethon import events
from telethon.errors import FloodWaitError

import config
from db.init import init_db
from parser.client import create_client, on_new_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

RECONNECT_DELAY = 10


async def main() -> None:
    await init_db(config.DB_PATH)
    client = create_client()

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            await on_new_message(event, client)
        except FloodWaitError as e:
            logger.warning("FloodWait: sleeping %ds", e.seconds)
            await asyncio.sleep(e.seconds)
        except Exception as exc:
            logger.exception("Unhandled error in message handler: %s", exc)

    while True:
        try:
            logger.info("Connecting to Telegram...")
            await client.start()
            logger.info("Parser running. Listening for messages...")
            await client.run_until_disconnected()
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.error("Network error: %s — reconnecting in %ds", exc, RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            break

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
