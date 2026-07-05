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

**Stack:** Flask 3 backend + vanilla JS/HTML frontend (no SSR — all pages are static HTML in `static/`).

**Frontend** (`static/`): Ten HTML pages served statically (`index`, `commute`, `compare`, `explore`, `reports`, `route-detail`, `routes`, `settings`, `setup`, `weather`; `test-error-handling.html` is a manual dev harness, not a product page). Each page has a corresponding JS module in `static/js/`. Leaflet 1.9.4 handles maps; Bootstrap 5.3 handles UI. There is no JS build step. `static/js/api-client.js` wraps all `fetch` calls to the Flask API.

**Backend** (`launch.py` + `app/`): `launch.py` is the main Flask server defining API endpoints. Business logic lives in `app/services/` — ten service classes: `AnalysisService`, `CommuteService`, `PlannerService`, `RouteLibraryService`, `WeatherService`, `TrainerRoadService`, `GarminService`, `ExplorationService` (ORS route/tile-coverage computation), `GeocodingService` (forward geocoding via Nominatim), `SettingsService` (user preference persistence). Services use a two-step init pattern: constructor then `.initialize()`. The `maps_api` Blueprint (`app/api/maps_api.py`) serves map-tile endpoints under `/api/maps`.

**Core analysis** (`src/`): The heavy lifting for route analysis. `src/route_analyzer.py` (~73KB) is the central engine using Fréchet distance (via `similaritymeasures`) for route similarity matching. `src/data_fetcher.py` handles Strava API calls with rate-limit retry. `src/json_storage.py` is the current persistence layer (SQLite migration planned — Issue #131). Activity data is cached under `data/cache/`.

**Privacy:** `src/pii_sanitizer.py` redacts GPS coordinates, addresses, user IDs, and tokens from all logs. `src/secure_cache.py` encrypts cached data.

**Config:** `config/config.yaml` controls optimization weights, feature flags, and location detection thresholds.

## Unexposed Backend Capabilities

These backend components are fully implemented but have no API endpoints or frontend UI yet. Wire them up before building new versions of the same functionality.

### PlannerService (`app/services/planner_service.py`)

Weather-optimized long ride recommendation engine. Initialized at startup (`_planner_service` in `launch.py`) but never called from any route.

**Available methods:**
- `get_recommendations(forecast_days, min_distance, max_distance, location)` — Scores all long rides against a multi-day weather forecast and returns ranked recommendations per day. Each ride gets a composite score from weather (50%), route variety/freshness (30%), and location proximity (20%). Returns the best day and top 5 rides per day.
- `get_rides_near_location(lat, lon, radius_miles, limit)` — Spatial search for rides near a point. Requires `geopy`.
- `get_ride_details(ride_id)` — Full ride detail lookup from the in-memory long ride list.
- `analyze_long_ride(distance, duration, date)` — Standalone ride analysis: difficulty scoring, weather suitability, and actionable recommendations/warnings for a planned ride.
- `generate_long_rides_map(long_rides, home_location)` — Generates a Folium HTML map with weather-segmented route coloring, forecast markers, and layer controls.

**To wire up:** Add endpoints in `launch.py` that call `_planner_service.<method>()` (follows the same pattern as `_route_library_service` or `_weather_service`). The service needs `.initialize(long_rides)` called with the analyzed long ride list — check how `_analysis_service` feeds data to other services after analysis completes.

### `/api/routes/search` endpoint (`launch.py`)

A server-side route search endpoint exists but the frontend ignores it — the routes page fetches all routes via `/api/routes` and filters client-side in `routes.js`. The endpoint works and is rate-limited, but is redundant unless the route count grows large enough to justify server-side filtering.

## Key Patterns

- When editing UI: touch `static/*.html`, `static/js/*.js`, `static/css/main.css`, and API endpoints in `launch.py`.
- When adding business logic: add to or extend an `app/services/` class; keep heavy data processing in `src/`.
- `main.py` is a deprecated CLI tool — do not extend it for web features.
- SQLAlchemy models exist in `app/models/` but are not yet wired to a database; persistence still goes through `src/json_storage.py`.
- Background jobs are managed by APScheduler via `app/scheduler/`.
