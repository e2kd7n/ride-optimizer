# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Please also refer to AGENTS.md for direction. In the event of a conflict - explain the conundrum and ask the user how to proceed. 

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
gunicorn --config gunicorn.conf.py wsgi:app
podman-compose up   # pulls image from GHCR
```

## Environment Setup

The local server where this is deployed can be accessed via ssh admin@pi4 . 

Create a `.env` file with Strava API credentials (required — app exits at startup if missing):
```
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
```

Optionally add an OpenRouteService API key to enable real road-following routes on the Explore page.
The app starts and degrades gracefully without it — the `/api/exploration/route` endpoint returns a
clear "not configured" error instead of crashing:
```
ORS_API_KEY=your_ors_api_key
```
Get a free key at https://openrouteservice.org/dev/#/signup (free tier: 2000 req/day, 40 req/min).

Flask dev config lives in `.flaskenv`. Encrypted OAuth tokens are auto-generated to `config/credentials.json`.

## Architecture

**Stack:** Flask 3 backend + vanilla JS/HTML frontend. Eight pages (`index`, `compare`, `explore`, `reports`, `route-detail`, `routes`, `settings`, `weather`) are Jinja-rendered from `templates/` so the navbar/bottom-nav/theme-init markup lives once in `templates/partials/` instead of being copy-pasted per page (#470); `commute.html`, `setup.html`, and the `test-error-handling.html` dev harness remain plain static files in `static/` since they don't use the shared nav. There is still no client-side JS framework or build step — Jinja only assembles the shared chrome at request time; the app remains a classic server-rendered multi-page app, not an SPA.

**Frontend** (`templates/` + `static/`): `app/factory.py` registers an explicit route per templated page (`render_template(..., active_page=...)`); everything else (JS/CSS/images and the three standalone static pages above) falls through to a catch-all `send_from_directory`. Each page has a corresponding JS module in `static/js/`. Leaflet 1.9.4 handles maps; Bootstrap 5.3 handles UI. `static/js/api-client.js` wraps all `fetch` calls to the Flask API.

**Backend** (`launch.py` + `app/`): `launch.py` is the main Flask server defining API endpoints. Business logic lives in `app/services/` — ten service classes: `AnalysisService`, `CommuteService`, `PlannerService`, `RouteLibraryService`, `WeatherService`, `TrainerRoadService`, `GarminService`, `ExplorationService` (ORS route/tile-coverage computation), `GeocodingService` (forward geocoding via Nominatim), `SettingsService` (user preference persistence). Services use a two-step init pattern: constructor then `.initialize()`. The `maps_api` Blueprint (`app/api/maps_api.py`) serves map-tile endpoints under `/api/maps`.

**Core analysis** (`src/`): The heavy lifting for route analysis. `src/route_analyzer.py` (~73KB) is the central engine using Fréchet distance (via `similaritymeasures`) for route similarity matching. `src/data_fetcher.py` handles Strava API calls with rate-limit retry. `src/json_storage.py` is the current persistence layer (SQLite migration planned — Issue #131). Activity data is cached under `data/cache/`.

**Privacy:** `src/pii_sanitizer.py` redacts GPS coordinates, addresses, user IDs, and tokens from all logs. Cached GPS/location data (activity, weather, and route-similarity caches) is protected via OS file permissions rather than at-rest encryption — every cache writer must set 0o600 (owner read/write only), either automatically via `JSONStorage` or explicitly via `json_storage.secure_chmod()` for the few callers that still bypass it with a bare `json.dump()`. This was a deliberate choice over encrypting caches (`src/secure_cache.py`, removed as dead code) — see `GHSA-ffw6-3927-gq93`.

**Config:** `config/config.yaml` controls optimization weights, feature flags, and location detection thresholds.

## Unexposed Backend Capabilities

### PlannerService — API exists, no UI consumes it

`PlannerService` (`app/services/planner_service.py`) is wired to `/api/planner/recommendations`, `/api/planner/rides/nearby`, `/api/planner/rides/<id>`, and `/api/planner/analyze` (`launch.py`), and `static/js/api-client.js` has matching client methods (`getLongRideRecommendations`, `getRidesNearLocation`, `getLongRideDetails`, `analyzeLongRide`). No page currently calls them — build a planner page/view before adding a competing feature.

One method remains fully unexposed: `generate_long_rides_map(long_rides, home_location)`, which builds a Folium HTML map with weather-segmented route coloring — no endpoint calls it yet.

### `/api/routes/search` endpoint (`launch.py`)

A server-side route search endpoint exists but the frontend ignores it — the routes page fetches all routes via `/api/routes` and filters client-side in `routes.js`. The endpoint works and is rate-limited, but is redundant unless the route count grows large enough to justify server-side filtering.

## Visual Design

**Brand identity:** `docs/designs/FAIR_WEATHER_BRAND_BOOK.md` (adopted 2026-07-05) — logo mark, Day/Night color tokens, type, and reference screens for the current "Fair Weather" identity. `docs/designs/BRAND_CONCEPTS_COMPARISON.html` holds the two alternate directions that were reviewed and not chosen. **Design rules:** `plans/v0.6.0/DESIGN_PRINCIPLES.md` (v2.2) is the living guideline doc — mobile-first, visual hierarchy, color usage, map/controls layout, etc.

`static/css/main.css` and all `static/*.html` pages have been migrated to the Fair Weather Day/Night tokens (colors, navbar, cards, buttons, focus rings) — no pre-rebrand indigo gradient (`#667eea`/`#764ba2`) remains. When touching UI, check the brand book before introducing a new color, icon, or shape rather than reaching for a one-off hardcoded value.

## Key Patterns

- When editing UI: touch `static/*.html`, `static/js/*.js`, `static/css/main.css`, and API endpoints in `launch.py`.
- When adding business logic: add to or extend an `app/services/` class; keep heavy data processing in `src/`.
- `main.py` is a deprecated CLI tool — do not extend it for web features.
- Persistence goes through `src/json_storage.py`; there is no database. `app/models/` and the `apscheduler` dependency are currently unused (no source files / no scheduler wiring exist) — don't assume either is active.
- Scheduled jobs (`cron/daily_analysis.py`, `cache_cleanup.py`, `weather_refresh.py`, `system_health.py`) run via the system crontab, installed with `cron/install_cron.sh` — not via an in-process scheduler.
