import asyncio
import logging
import sys

from telethon import events
from telethon.errors import FloodWaitError

import config
import state
from db.init import init_db
from parser.client import create_client, on_new_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

RECONNECT_DELAY = 10
CREDENTIALS_RETRY = 30


async def run_parser_loop() -> None:
    """Wait for credentials, then run the Telethon reconnect loop.

    If credentials are missing the loop retries every 30 s so the dashboard
    can be used to configure them without restarting the binary.
    """
    while True:
        # Try to build the client; retry until credentials are configured.
        try:
            client = await create_client()
        except RuntimeError as exc:
            logger.warning(
                "%s  — retrying in %ds. "
                "Configure credentials at http://localhost:8000/settings",
                exc, CREDENTIALS_RETRY,
            )
            try:
                await asyncio.sleep(CREDENTIALS_RETRY)
            except asyncio.CancelledError:
                return
            continue
        except asyncio.CancelledError:
            return

        @client.on(events.NewMessage)
        async def handler(event):
            try:
                await on_new_message(event, client)
            except FloodWaitError as e:
                logger.warning("FloodWait: sleeping %ds", e.seconds)
                await asyncio.sleep(e.seconds)
            except Exception as exc:
                logger.exception("Unhandled error in message handler: %s", exc)

        try:
            while True:
                try:
                    logger.info("Connecting to Telegram...")
                    await client.start()
                    state.tg_client = client  # expose to dashboard routes
                    logger.info("Parser running. Listening for messages...")
                    await client.run_until_disconnected()
                except (ConnectionError, TimeoutError, OSError) as exc:
                    state.tg_client = None
                    logger.error("Network error: %s — reconnecting in %ds", exc, RECONNECT_DELAY)
                    await asyncio.sleep(RECONNECT_DELAY)
                except KeyboardInterrupt:
                    logger.info("Shutting down.")
                    return
        except asyncio.CancelledError:
            pass
        finally:
            state.tg_client = None
            await client.disconnect()
        return


async def main() -> None:
    await init_db(config.DB_PATH)
    await run_parser_loop()


if __name__ == "__main__":
    asyncio.run(main())
