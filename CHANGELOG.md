# Changelog

All notable changes to TeleListener are documented here.

## [Unreleased]

## [1.2] – 2026-06-09

### Added
- **Keyword editing** – each keyword chip now has an inline edit button (✎). Click it, change the phrase, press Enter or Save. Changes take effect immediately.
- **Bulk keyword add** – the Add Keywords panel accepts comma- or newline-separated values so multiple keywords can be added in one action.
- **Stats cards** – the Live Feed page shows Total Hits, Active Keywords, and Groups Monitored at a glance, sourced from the new `GET /api/stats` endpoint.
- **`GET /api/stats`** – returns `{hits, keywords, groups}` counts in a single request.
- **`PUT /api/keywords/{id}`** – new route for renaming an existing keyword.

### Changed
- **Full dashboard redesign** – modern card-based layout, sticky dark nav with brand logo, consistent typography and colour system, relative timestamps ("2m ago"), keyword chips with edit/delete actions, custom toggle for notification switch, responsive on mobile.
- All five templates (`base.html`, `index.html`, `keywords.html`, `groups.html`, `settings.html`) rewritten.

## [1.1] – 2026-06-09

### Fixed
- **Dashboard starts before parser** – the binary no longer crashes on launch if Telegram credentials are not yet configured. The dashboard comes up immediately on port 8000; the parser retries every 30 s and connects automatically once credentials are saved in Settings.
- **DB path in frozen binary** – `config.py` now resolves `DB_PATH` relative to the binary's location (`sys.executable`) when running under PyInstaller, preventing `unable to open database file` errors when launching from a different working directory.
- **DB directory auto-created** – `init_db` calls `mkdir(parents=True, exist_ok=True)` so the `db/` folder is created on first run without manual setup.
- **Windows rename in CI** – switched from `Rename-Item` to `Move-Item` in the GitHub Actions workflow; `Rename-Item` does not accept a destination path, only a bare filename.

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
