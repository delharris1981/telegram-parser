from fastapi import APIRouter, Depends
from dashboard.auth import require_auth
from parser import manager

router = APIRouter()


@router.get("/api/parser/status")
async def status(user: dict = Depends(require_auth)):
    return {"status": manager.parser_status(user["username"])}


@router.post("/api/parser/start")
async def start(user: dict = Depends(require_auth)):
    await manager.start_parser(user["username"], user["db_path"])
    return {"status": "started"}


@router.post("/api/parser/stop")
async def stop(user: dict = Depends(require_auth)):
    await manager.stop_parser(user["username"])
    return {"status": "stopped"}
