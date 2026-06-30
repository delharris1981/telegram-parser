import sys
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext

import config
from dashboard.auth import require_auth, require_admin
from dashboard.routes import hits, keywords, groups
from dashboard.routes import settings as settings_router
from dashboard.routes import parser as parser_router
from dashboard.routes import admin as admin_router
from db.users import init_users_db, get_user_by_username, create_user
from db.init import init_db

if getattr(sys, "frozen", False):
    BASE_DIR = pathlib.Path(sys._MEIPASS) / "dashboard"
else:
    BASE_DIR = pathlib.Path(__file__).parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_users_db(config.USERS_DB_PATH)
    existing = await get_user_by_username(config.USERS_DB_PATH, config.DASHBOARD_USERNAME)
    if not existing:
        await init_db(config.DB_PATH)
        await create_user(
            config.USERS_DB_PATH,
            config.DASHBOARD_USERNAME,
            _pwd.hash(config.DASHBOARD_PASSWORD),
            config.DB_PATH,
        )
    yield


app = FastAPI(title="TeleListener Dashboard", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)

app.include_router(hits.router)
app.include_router(keywords.router)
app.include_router(groups.router)
app.include_router(settings_router.router)
app.include_router(parser_router.router)
app.include_router(admin_router.router)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = await get_user_by_username(config.USERS_DB_PATH, username)
    if not user or not _pwd.verify(password, user["password_hash"]):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid username or password"},
            status_code=400,
        )
    request.session["user"] = {
        "user_id": user["id"],
        "username": user["username"],
        "db_path": user["db_path"],
    }
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "index.html", {"user": user})


@app.get("/keywords", response_class=HTMLResponse)
async def keywords_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "keywords.html", {"user": user})


@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "groups.html", {"user": user})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "settings.html", {"user": user})


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, user: dict = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin_users.html", {"user": user})


@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse(request, "account.html", {"user": user})
