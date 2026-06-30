from typing import Optional
from fastapi import Depends, HTTPException, Request
import state


def require_auth(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin(user: dict = Depends(require_auth)) -> dict:
    if user.get("user_id") != 1:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def get_db_path(user: dict = Depends(require_auth)) -> str:
    return user["db_path"]


def get_tg_client(user: dict = Depends(require_auth)) -> Optional[object]:
    return state.get_client(user["username"])
