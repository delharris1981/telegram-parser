import sys
import pathlib
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dashboard.auth import require_auth
from dashboard.routes import hits, keywords, groups
from dashboard.routes import settings as settings_router

# In a PyInstaller one-file binary, __file__ resolves to the temp extraction dir.
if getattr(sys, "frozen", False):
    BASE_DIR = pathlib.Path(sys._MEIPASS) / "dashboard"
else:
    BASE_DIR = pathlib.Path(__file__).parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="TeleListener Dashboard")

app.include_router(hits.router, dependencies=[Depends(require_auth)])
app.include_router(keywords.router, dependencies=[Depends(require_auth)])
app.include_router(groups.router, dependencies=[Depends(require_auth)])
app.include_router(settings_router.router, dependencies=[Depends(require_auth)])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _user: str = Depends(require_auth)):
    return templates.TemplateResponse(request, "index.html")


@app.get("/keywords", response_class=HTMLResponse)
async def keywords_page(request: Request, _user: str = Depends(require_auth)):
    return templates.TemplateResponse(request, "keywords.html")


@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request, _user: str = Depends(require_auth)):
    return templates.TemplateResponse(request, "groups.html")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, _user: str = Depends(require_auth)):
    return templates.TemplateResponse(request, "settings.html")
