# Changelog

All notable changes to TeleListener are documented here.

## [Unreleased]

## [1.4] – 2026-06-09

### Added
- **Automatic group discovery** – the parser now runs a background task that periodically searches Telegram for public groups matching the configured keywords. Discovered Russian-language groups (detected via Cyrillic title check) above a configurable member-count threshold are joined automatically using flood-safe delays (60–300 s between each join).
- **Auto-Discovery settings card** – the Settings page has a new "Auto-Discovery" section with an enable toggle, minimum member count field, and search interval (hours). A "Last ran" timestamp updates after each run.
- **New API routes**: `GET /api/settings/auto-discovery`, `POST /api/settings/auto-discovery`.
- **New DB columns** on `settings`: `auto_discovery_enabled`, `auto_discovery_min_members`, `auto_discovery_interval_hours`, `auto_discovery_last_run` — applied via migration to existing databases.

### Changed
- `parser/main.py`: launches `run_auto_discovery(client)` as a concurrent asyncio task after `client.start()`; cancels it cleanly on disconnect.
- `db/operations.py`: added `get_auto_discovery_settings`, `update_auto_discovery_settings`, `set_auto_discovery_last_run`, `list_joined_group_telegram_ids`.

## [1.3] – 2026-06-09

### Added
- **Group search & auto-join** – the Groups page now has a search bar that queries the Telegram API for public groups matching a term. Results show the group name, handle, member count, and type (Group/Channel). One-click Join adds the group to the monitoring list and the account joins it immediately.
- **Leave groups** – joined groups show a Leave button that makes the account leave the Telegram group and removes it from the tracking list.
- **Keyword hit counter** – each joined group displays how many keyword matches have been found inside it.
- **`joined_groups` DB table** – tracks groups the app has joined, independent of the `monitored_groups` (keyword-hit) table.
- **`state.py`** – shared module exposing the live `TelegramClient` to dashboard routes so search/join/leave can be called without restarting.
- **New API routes**: `GET /api/groups/search`, `POST /api/groups/join`, `GET /api/groups/joined`, `DELETE /api/groups/joined/{id}`.

### Changed
- `parser/main.py`: sets `state.tg_client` once connected; clears it on disconnect or error so the dashboard can reflect live connection status.
- `groups.html`: redesigned into three sections — Find Public Groups (search), Joined Groups (app-managed with Leave), Groups with Keyword Hits (auto-populated).

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
