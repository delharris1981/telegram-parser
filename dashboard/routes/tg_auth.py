from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from telethon.errors import SessionPasswordNeededError

from dashboard.auth import require_auth
from db.operations import get_tg_session, save_tg_session
from parser.client import create_client

router = APIRouter()

_pending: dict[str, dict] = {}  # username -> {client, phone, phone_code_hash}


class PhoneIn(BaseModel):
    phone: str


class CodeIn(BaseModel):
    code: str


class PasswordIn(BaseModel):
    password: str


@router.get("/api/auth/telegram/status")
async def tg_status(user: dict = Depends(require_auth)):
    session = await get_tg_session(user["db_path"])
    return {"authenticated": bool(session)}


@router.post("/api/auth/telegram/send-code")
async def send_code(body: PhoneIn, user: dict = Depends(require_auth)):
    old = _pending.pop(user["username"], None)
    if old:
        try:
            await old["client"].disconnect()
        except Exception:
            pass

    client = await create_client(user["db_path"])
    await client.connect()
    try:
        result = await client.send_code_request(body.phone)
    except Exception as exc:
        await client.disconnect()
        raise HTTPException(400, str(exc))

    _pending[user["username"]] = {
        "client": client,
        "phone": body.phone,
        "phone_code_hash": result.phone_code_hash,
    }
    return {"status": "code_sent"}


@router.post("/api/auth/telegram/verify-code")
async def verify_code(body: CodeIn, user: dict = Depends(require_auth)):
    pending = _pending.get(user["username"])
    if not pending:
        raise HTTPException(400, "No pending auth — send code first")

    try:
        await pending["client"].sign_in(
            pending["phone"], body.code,
            phone_code_hash=pending["phone_code_hash"],
        )
    except SessionPasswordNeededError:
        return {"status": "2fa_required"}
    except Exception as exc:
        raise HTTPException(400, str(exc))

    session_str = pending["client"].session.save()
    await pending["client"].disconnect()
    _pending.pop(user["username"], None)
    await save_tg_session(user["db_path"], session_str)
    return {"status": "ok"}


@router.post("/api/auth/telegram/verify-password")
async def verify_password(body: PasswordIn, user: dict = Depends(require_auth)):
    pending = _pending.get(user["username"])
    if not pending:
        raise HTTPException(400, "No pending auth — send code first")

    try:
        await pending["client"].sign_in(password=body.password)
    except Exception as exc:
        raise HTTPException(400, str(exc))

    session_str = pending["client"].session.save()
    await pending["client"].disconnect()
    _pending.pop(user["username"], None)
    await save_tg_session(user["db_path"], session_str)
    return {"status": "ok"}
