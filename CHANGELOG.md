# Changelog

All notable changes to TeleListener are documented here.

## [Unreleased]

## [1.0] – 2026-06-09

### Added
- **Single combined binary** – parser and dashboard now ship as one `telelistener` executable built with PyInstaller. Start both services with a single command.
- **API credentials in dashboard** – Telegram API ID, API Hash, session name, and proxy settings are now configurable directly from the Settings page. No `.env` editing required after first launch.
- **Automatic GitHub Releases** – every push to `main` builds macOS and Windows binaries and publishes a versioned GitHub Release with both files attached.
- **Merged Docker setup** – `Dockerfile` and `docker-compose.yml` now run the full stack as a single service on port 8000.

### Changed
- `parser/main.py`: extracted `run_parser_loop(client)` so the combined entry point can start the parser loop alongside uvicorn without a duplicate `init_db` call.
- `dashboard/main.py`: template path resolves correctly inside a PyInstaller frozen binary via `sys._MEIPASS`.
- `parser/client.py`: `create_client()` is now `async` and reads credentials from the DB (with `.env` fallback).
- `db/init.py`: `settings` table extended with `api_id`, `api_hash`, `session_name`, `proxy_type`, `proxy_host`, `proxy_port`; migration runs automatically on existing databases.

### Infrastructure
- `telelistener.spec`: PyInstaller spec bundles Jinja2 templates and all required hidden imports for uvicorn, anyio, and Telethon.
- `VERSION`: base version file (`1.0`); patch number is the CI run number (`1.0.<N>`).
