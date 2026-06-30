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
