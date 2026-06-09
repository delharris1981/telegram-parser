import os

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "telelistener")
KEYWORDS = [k.strip() for k in os.getenv("KEYWORDS", "").split(",") if k.strip()]
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "changeme")
DB_PATH = os.getenv("DB_PATH", "db/telelistener.db")

_proxy_type = os.getenv("PROXY_TYPE", "").lower()
_proxy_host = os.getenv("PROXY_HOST", "")
_proxy_port = os.getenv("PROXY_PORT", "")

PROXY = None
if _proxy_type and _proxy_host and _proxy_port:
    PROXY = (_proxy_type, _proxy_host, int(_proxy_port))
