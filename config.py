import os

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "telelistener")
KEYWORDS = [k.strip() for k in os.getenv("KEYWORDS", "").split(",") if k.strip()]
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
_raw_password = os.getenv("DASHBOARD_PASSWORD", "")
if not _raw_password or _raw_password == "changeme":
    import warnings
    warnings.warn(
        "DASHBOARD_PASSWORD is not set or is the insecure default 'changeme'. "
        "Set a strong password via the DASHBOARD_PASSWORD environment variable.",
        stacklevel=2,
    )
DASHBOARD_PASSWORD = _raw_password or "changeme"
DB_PATH = os.getenv("DB_PATH", "db/telelistener.db")

_proxy_type = os.getenv("PROXY_TYPE", "").lower()
_proxy_host = os.getenv("PROXY_HOST", "")
_proxy_port = os.getenv("PROXY_PORT", "")

PROXY = None
if _proxy_type and _proxy_host and _proxy_port:
    PROXY = (_proxy_type, _proxy_host, int(_proxy_port))
