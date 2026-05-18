# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Development server:**
```bash
python launch.py          # Starts Flask on port 8083, auto-opens browser
python wsgi.py            # Alternative entry point
```

**Tests:**
```bash
pytest                    # Run all tests
pytest tests/test_file.py # Run a single test file
pytest -m unit            # Run by marker (unit, integration, slow, e2e, accessibility, mobile, performance)
pytest --cov=app          # Run with coverage report
```

**Production:**
```bash
gunicorn -w 4 -b 0.0.0.0:8083 wsgi:app
docker-compose up
```

## Environment Setup

Create a `.env` file with Strava API credentials (required — app exits at startup if missing):
```
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
```

Flask dev config lives in `.flaskenv`. Encrypted OAuth tokens are auto-generated to `config/credentials.json`.

## Architecture

**Stack:** Flask 3 backend + vanilla JS/HTML frontend (no SSR — all pages are static HTML in `static/`).

**Frontend** (`static/`): Eight HTML pages served statically. Each page has a corresponding JS module in `static/js/`. Leaflet 1.9.4 handles maps; Bootstrap 5.3 handles UI. There is no JS build step. `static/js/api-client.js` wraps all `fetch` calls to the Flask API.

**Backend** (`launch.py` + `app/`): `launch.py` is the main Flask server defining API endpoints. Business logic lives in `app/services/` (six service classes — `AnalysisService`, `CommuteService`, `PlannerService`, `RouteLibraryService`, `WeatherService`, `TrainerRoadService`). Services use a two-step init pattern: constructor then `.initialize()`. Blueprints for map endpoints are in `app/api/`.

**Core analysis** (`src/`): The heavy lifting for route analysis. `src/route_analyzer.py` (~73KB) is the central engine using Fréchet distance (via `similaritymeasures`) for route similarity matching. `src/data_fetcher.py` handles Strava API calls with rate-limit retry. `src/json_storage.py` is the current persistence layer (SQLite migration planned — Issue #131). Activity data is cached under `data/cache/`.

**Privacy:** `src/pii_sanitizer.py` redacts GPS coordinates, addresses, user IDs, and tokens from all logs. `src/secure_cache.py` encrypts cached data.

**Config:** `config/config.yaml` controls optimization weights, feature flags, and location detection thresholds.

## Key Patterns

- When editing UI: touch `static/*.html`, `static/js/*.js`, `static/css/main.css`, and API endpoints in `launch.py`.
- When adding business logic: add to or extend an `app/services/` class; keep heavy data processing in `src/`.
- `main.py` is a deprecated CLI tool — do not extend it for web features.
- SQLAlchemy models exist in `app/models/` but are not yet wired to a database; persistence still goes through `src/json_storage.py`.
- Background jobs are managed by APScheduler via `app/scheduler/`.
