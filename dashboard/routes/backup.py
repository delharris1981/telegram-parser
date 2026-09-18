import os
from datetime import date
import aiosqlite
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from fastapi.responses import FileResponse
from dashboard.auth import get_db_path, require_auth
from db.init import init_db
from db.operations import get_tg_session
from parser import manager

router = APIRouter()

_SQLITE_MAGIC = b"SQLite format 3\x00"


@router.get("/api/backup/export")
async def export_backup(db_path: str = Depends(get_db_path)):
    async with aiosqlite.connect(db_path, timeout=10.0) as db:
        await db.execute("PRAGMA wal_checkpoint(FULL);")
        await db.commit()
    return FileResponse(
        db_path,
        media_type="application/octet-stream",
        filename=f"telelistener-backup-{date.today().isoformat()}.db",
    )


@router.post("/api/backup/import")
async def import_backup(file: UploadFile, user: dict = Depends(require_auth)):
    content = await file.read()
    if content[:16] != _SQLITE_MAGIC:
        raise HTTPException(400, "Not a valid SQLite database file")

    db_path = user["db_path"]
    try:
        await manager.stop_parser(user["username"])

        tmp_path = db_path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(content)
        os.replace(tmp_path, db_path)

        await init_db(db_path)

        if await get_tg_session(db_path):
            await manager.start_parser(user["username"], db_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

    return {"status": "ok"}
