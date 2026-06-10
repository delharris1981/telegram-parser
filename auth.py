"""Interactive Telegram authentication helper.

Run this inside the container to complete first-time phone/code auth:

    docker exec -it telegram-telelistener-1 python auth.py
"""
import asyncio
import os
import sys

import config
from db.init import init_db
from db.operations import get_api_config
from telethon import TelegramClient


async def main() -> None:
    await init_db(config.DB_PATH)
    cfg = await get_api_config(config.DB_PATH)

    # Prefer DB values; fall back to environment variables
    api_id = (cfg.get("api_id") if cfg else None) or config.API_ID or 0
    api_hash = (cfg.get("api_hash") if cfg else None) or config.API_HASH or ""
    session_name = (cfg.get("session_name") if cfg else None) or "telelistener"

    if not api_id or not api_hash:
        print(
            "No API credentials found.\n"
            "Go to http://<server-ip>:8000/settings and save your API ID and API Hash first,\n"
            "then re-run this script."
        )
        sys.exit(1)

    session_path = os.path.join("data", session_name)
    print(f"Using session: {session_path}")
    print("You will be prompted for your phone number and the code Telegram sends you.\n")

    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.start()
    me = await client.get_me()
    print(f"\nAuthenticated as: {me.first_name} (@{me.username})")
    print("Session saved. Restart the container to start monitoring:\n")
    print("    docker-compose restart")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
