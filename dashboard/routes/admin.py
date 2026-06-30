import pathlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
import config
from dashboard.auth import require_auth, require_admin
from db.users import create_user, list_users, delete_user, update_password, get_user_by_id
from db.init import init_db
from parser import manager

router = APIRouter()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CreateUserIn(BaseModel):
    username: str
    password: str


class PasswordIn(BaseModel):
    password: str


@router.get("/api/admin/users")
async def api_list_users(_: dict = Depends(require_admin)):
    users = await list_users(config.USERS_DB_PATH)
    return [
        {**u, "parser_status": manager.parser_status(u["username"])}
        for u in users
    ]


@router.post("/api/admin/users")
async def api_create_user(body: CreateUserIn, _: dict = Depends(require_admin)):
    db_path = str(pathlib.Path("data") / body.username / "telelistener.db")
    await init_db(db_path)
    await create_user(config.USERS_DB_PATH, body.username, _pwd.hash(body.password), db_path)
    return {"status": "ok"}


@router.delete("/api/admin/users/{user_id}")
async def api_delete_user(user_id: int, _: dict = Depends(require_admin)):
    if user_id == 1:
        raise HTTPException(400, "Cannot delete the admin account")
    user = await get_user_by_id(config.USERS_DB_PATH, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await manager.stop_parser(user["username"])
    await delete_user(config.USERS_DB_PATH, user_id)
    return {"status": "ok"}


@router.post("/api/admin/users/{user_id}/password")
async def api_reset_password(user_id: int, body: PasswordIn, _: dict = Depends(require_admin)):
    user = await get_user_by_id(config.USERS_DB_PATH, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await update_password(config.USERS_DB_PATH, user_id, _pwd.hash(body.password))
    return {"status": "ok"}


@router.post("/api/account/password")
async def api_change_own_password(body: PasswordIn, user: dict = Depends(require_auth)):
    await update_password(config.USERS_DB_PATH, user["user_id"], _pwd.hash(body.password))
    return {"status": "ok"}
