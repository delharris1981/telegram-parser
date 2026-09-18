import asyncio
import state
from db.init import init_db
from parser.main import run_parser_loop

_tasks: dict[str, asyncio.Task] = {}


async def start_parser(username: str, db_path: str) -> None:
    task = _tasks.get(username)
    if task and not task.done():
        return  # already running
    await init_db(db_path)
    _tasks[username] = asyncio.create_task(
        run_parser_loop(username, db_path),
        name=f"parser-{username}",
    )


async def stop_parser(username: str) -> None:
    task = _tasks.pop(username, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    state.clear_client(username)


def parser_status(username: str) -> str:
    task = _tasks.get(username)
    return "running" if (task and not task.done()) else "stopped"


async def rename_parser(old_username: str, new_username: str, db_path: str) -> None:
    # Task/client tracking is keyed by username, so a username change orphans
    # the running task under the old key unless it's restarted under the new one.
    if parser_status(old_username) == "running":
        await stop_parser(old_username)
        await start_parser(new_username, db_path)
