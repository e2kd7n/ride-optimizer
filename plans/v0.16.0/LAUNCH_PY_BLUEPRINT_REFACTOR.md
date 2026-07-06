# Plan: `launch.py` Blueprint Refactor

**Target release:** v0.16.0  
**Scope:** Structural refactor only — no behaviour changes, no new features  
**Status:** Draft

---

## 1. Problem Statement

`launch.py` has grown to **3,404 lines and 65 route handlers**. It contains:

- All routes registered directly on `app` (no structure)
- Infrastructure utilities (`_IntervalsCredStore`, `_read_env`, `_write_env`, `_env_path`) living inside a route file
- Business logic helpers (`_enrich_commute_recommendation`, `_get_transit_recommendation`) that belong in services
- All mutable job state (`_analysis_job`, `_fetch_job`, stop flags) as module-level globals
- Process-management helpers (`kill_existing_server`, `server_status`, pid helpers) mixed into API code

This makes navigation, testing, and incremental contribution increasingly expensive. The refactor moves `launch.py` to a thin **~150-line entry point** that creates the app, registers blueprints, and starts the server — nothing more.

---

## 2. Target File Layout

```
launch.py                          # ~150 lines: app factory, blueprint registration, CLI entry
app/
  factory.py                       # create_app() — Flask app factory
  container.py                     # ServiceContainer: owns all service instances + init logic
  api/
    maps_api.py                    # (unchanged — already a Blueprint)
    weather_bp.py                  # /api/weather/*
    commute_bp.py                  # /api/commute, /api/recommendation, /api/workout-options
    routes_bp.py                   # /api/routes/*
    planner_bp.py                  # /api/planner/*, /api/exploration/*, /api/geocode
    strava_bp.py                   # /api/strava/*, /api/setup/*
    integrations_bp.py             # /api/intervals/*, /api/ors/*, /api/garmin/*, /api/trainerroad/*
    data_bp.py                     # /api/analyze/*, /api/fetch/*, /api/cache-info, /api/activities
    stats_bp.py                    # /api/stats/*
    core_bp.py                     # /api/status, /api/settings/*, /api/plans/*, /api/user/*,
                                   #   /api/csrf-token
  jobs/
    job_state.py                   # Thread-safe JobState + JobRegistry (replaces module globals)
  credentials/
    intervals_creds.py             # _IntervalsCredStore (extracted verbatim)
    env_helpers.py                 # _env_path, _read_env, _write_env (extracted verbatim)
  process/
    server_control.py              # kill_existing_server, server_status, pid helpers
```

Nothing in `src/` or `app/services/` changes.

---

## 3. Concurrency Improvement: Parallel Service Initialisation

### Current behaviour
[`initialize_services()`](launch.py:205) starts all services **serially**:
`WeatherService` → `TrainerRoadService` → `RouteLibraryService` → `AnalysisService` → `CommuteService` → `PlannerService`

Services that have no dependency on each other still wait in line.

### Dependency graph

```
WeatherService        ──┐
TrainerRoadService    ──┤──► CommuteService ──► (done)
RouteLibraryService   ──┘
AnalysisService       ──────► CommuteService, PlannerService
PlannerService        ← AnalysisService
SettingsService       (already eager, no change)
```

**Wave 1** (fully independent, run in parallel):
- `WeatherService`
- `TrainerRoadService`
- `RouteLibraryService`

**Wave 2** (after Wave 1 finishes):
- `AnalysisService(weather_service=...)` — needs WeatherService

**Wave 3** (after Wave 2 finishes):
- `CommuteService(weather_service, trainerroad_service, settings_service)`
- `PlannerService(weather_service)`

### Implementation

`app/container.py` uses `concurrent.futures.ThreadPoolExecutor` for Wave 1, then constructs Wave 2 and 3 serially once their dependencies are ready:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

class ServiceContainer:
    def initialise(self) -> None:
        if self._initialised:
            return

        # Wave 1 — fully independent services
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(self._init_weather): 'weather',
                pool.submit(self._init_trainerroad): 'trainerroad',
                pool.submit(self._init_route_library): 'route_library',
            }
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as exc:
                    logger.warning("Wave-1 service failed: %s", exc)

        # Wave 2 — depends on WeatherService
        self._init_analysis()

        # Wave 3 — depends on Wave 1 + Wave 2
        with ThreadPoolExecutor(max_workers=2) as pool:
            pool.submit(self._init_commute).result()   # must complete before marking done
            pool.submit(self._init_planner).result()

        self._initialised = True
```

On a cold start with I/O-bound service constructors this is a measurable win (on Pi hardware, network calls during init are the bottleneck). On a warm start with all cached data it is near-zero cost.

> **Note on GIL:** service initialisation is primarily I/O-bound (reading JSON files, network pings to external APIs). `ThreadPoolExecutor` is sufficient; no need for `ProcessPoolExecutor`.

---

## 4. Thread-Safe Job State

### Current problem
`_analysis_job` and `_fetch_job` are plain dicts mutated from both the request thread and background `threading.Thread` workers. `_analysis_stop_requested` is a bare `bool` global. This is technically safe in CPython due to the GIL on small dict assignments, but it is fragile and hard to test.

### Replacement: `app/jobs/job_state.py`

```python
import threading
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class JobState:
    """Thread-safe job state bag."""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _data: Dict[str, Any] = field(default_factory=dict)

    def update(self, **kwargs) -> None:
        with self._lock:
            self._data.update(kwargs)

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._data)

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def reset(self, initial: dict) -> None:
        with self._lock:
            self._data = dict(initial)


class JobRegistry:
    """Holds named jobs; accessible from any blueprint via the app container."""
    def __init__(self):
        self.analysis = JobState()
        self.fetch    = JobState()
        self.analysis_stop = threading.Event()  # replaces bare bool
```

`JobRegistry` is owned by `ServiceContainer` and injected into any blueprint that needs it via Flask's `current_app.container`.

---

## 5. Blueprint Structure Detail

Each blueprint file follows the same template:
- Module-level `bp = Blueprint(...)` with a `url_prefix`
- Imports the container via `current_app.container`
- No module-level globals
- Rate-limit decorators via `limiter` (passed in at registration or via `app.extensions['limiter']`)

### 5.1 `app/api/weather_bp.py`

| Route | Handler |
|---|---|
| `GET /api/weather` | `get_weather` |
| `GET /api/weather/commute-windows` | `get_commute_windows` |
| `GET /api/weather/hourly` | `get_hourly_forecast` |
| `GET /api/weather/forecast` | `get_weather_forecast` |

Helper `_degrees_to_cardinal` moves here (private to module).

### 5.2 `app/api/commute_bp.py`

| Route | Handler |
|---|---|
| `GET /api/recommendation` | `get_recommendation` |
| `GET /api/commute` | `get_commute` |
| `GET /api/commute/map` | `get_commute_map` |
| `GET /api/workout-options` | `get_workout_options` |

Helpers `_enrich_commute_recommendation` and `_get_transit_recommendation` move here (private to module). These are pure transformations on service output — they require no service references — so they stay as module-level helpers, not methods on `CommuteService`. *(If a future PR wants to push them into the service, that's a separate concern.)*

### 5.3 `app/api/routes_bp.py`

| Route | Handler |
|---|---|
| `GET /api/routes` | `get_routes` |
| `GET /api/routes/status` | `get_routes_status` |
| `GET /api/routes/search` | `search_routes` |
| `GET /api/routes/<route_id>` | `get_route_detail` |

### 5.4 `app/api/planner_bp.py`

| Route | Handler |
|---|---|
| `GET /api/planner/recommendations` | `planner_recommendations` |
| `GET /api/planner/rides/nearby` | `planner_rides_nearby` |
| `GET /api/planner/rides/<ride_id>` | `planner_ride_detail` |
| `POST /api/planner/analyze` | `planner_analyze` |
| `GET /api/exploration/tiles` | `exploration_tiles` |
| `GET /api/exploration/roads` | `exploration_roads` |
| `POST /api/exploration/invalidate` | `exploration_invalidate` |
| `POST /api/exploration/route` | `exploration_route` |
| `GET /api/geocode` | `geocode` |

### 5.5 `app/api/strava_bp.py`

| Route | Handler |
|---|---|
| `GET /api/strava/status` | `strava_status` |
| `GET /api/strava/connect` | `strava_connect` |
| `GET /api/strava/callback` | `strava_callback` |
| `POST /api/strava/disconnect` | `strava_disconnect` |
| `GET /api/setup/status` | `setup_status` |
| `POST /api/setup/credentials` | `setup_credentials` |
| `POST /api/setup/verify` | `setup_verify` |

`_env_path`, `_read_env`, `_write_env` move to `app/credentials/env_helpers.py`; imported here.

### 5.6 `app/api/integrations_bp.py`

| Route | Handler |
|---|---|
| `GET /api/intervals/status` | `intervals_status` |
| `POST /api/intervals/connect` | `intervals_connect` |
| `POST /api/intervals/disconnect` | `intervals_disconnect` |
| `GET /api/ors/status` | `ors_status` |
| `POST /api/ors/connect` | `ors_connect` |
| `POST /api/ors/disconnect` | `ors_disconnect` |
| `GET /api/garmin/status` | `garmin_status` |
| `POST /api/garmin/connect` | `garmin_connect` |
| `POST /api/garmin/disconnect` | `garmin_disconnect` |
| `POST /api/garmin/sync` | `garmin_sync` |
| `GET /api/trainerroad/status` | `trainerroad_status` |
| `POST /api/trainerroad/connect` | `trainerroad_connect` |
| `POST /api/trainerroad/sync` | `trainerroad_sync` |
| `POST /api/trainerroad/disconnect` | `trainerroad_disconnect` |
| `GET /api/trainerroad/workouts` | `trainerroad_workouts` |
| `GET /api/trainerroad/today` | `trainerroad_today` |

`_IntervalsCredStore` moves to `app/credentials/intervals_creds.py`.

### 5.7 `app/api/data_bp.py`

| Route | Handler |
|---|---|
| `POST /api/analyze` | `trigger_analysis` |
| `GET /api/analyze/status` | `get_analyze_status` |
| `POST /api/analyze/stop` | `stop_analysis` |
| `POST /api/fetch` | `trigger_fetch` |
| `GET /api/fetch/status` | `get_fetch_status` |
| `GET /api/cache-info` | `get_cache_info` |
| `GET /api/activities` | `get_activities` |

Background thread workers (`_run` closures) become named top-level functions inside this module for testability.

### 5.8 `app/api/stats_bp.py`

| Route | Handler |
|---|---|
| `GET /api/stats` | `get_stats` |
| `GET /api/stats/gear` | `get_gear_stats` |
| `POST /api/stats/refresh-gear` | `refresh_gear` |
| `POST /api/stats/backfill-gear-ids` | `backfill_gear_ids` |
| `GET /api/stats/backfill-gear-ids/status` | `get_backfill_status` |

All stat helper functions (`_load_activities_for_stats`, `_filter_activities_by_period`, `_compute_summary`, `_compute_records`, `_compute_speed_distribution`, `_compute_elevation_distribution`) move here as private module functions.

### 5.9 `app/api/core_bp.py`

| Route | Handler |
|---|---|
| `GET /api/csrf-token` | `get_csrf_token` |
| `GET /api/status` | `get_status` |
| `GET /api/settings` | `get_settings` |
| `PUT /api/settings` | `update_settings` |
| `DELETE /api/settings` | `reset_settings` |
| `DELETE /api/user/data` | `delete_user_data` |
| `GET /api/plans` | `get_plans` |
| `POST /api/plans` | `save_plan` |
| `DELETE /api/plans/<plan_id>` | `delete_plan` |

---

## 6. `app/factory.py` — App Factory

```python
def create_app(config_overrides: dict | None = None) -> Flask:
    """Flask application factory."""
    app = Flask(__name__, static_folder='../static', static_url_path='')
    _configure_app(app, config_overrides)
    _init_extensions(app)        # csrf, limiter
    _register_blueprints(app)    # all bp imports here
    _register_error_handlers(app)
    _register_static_routes(app)
    return app
```

`ServiceContainer` is instantiated once and stored on `app.container`. Blueprints access it via `current_app.container`.

---

## 7. Revised `launch.py` (entry point only)

After refactor, `launch.py` does:
1. Import `create_app` from `app.factory`
2. Parse `--serve` / `--stop` / `--status` CLI flags
3. Call `create_app()` to get the Flask `app`
4. Start Waitress (or Flask dev server) + browser opener

All process management helpers move to `app/process/server_control.py`; `launch.py` just calls `kill_existing_server()` / `server_status()` imported from there.

Estimated size: **~120 lines**.

---

## 8. Implementation Phases

Each phase is independently mergeable; the app stays functional throughout.

| Phase | Work | Risk |
|---|---|---|
| **1 — Scaffolding** | Create `app/container.py`, `app/factory.py`, `app/jobs/job_state.py`, `app/credentials/`, `app/process/` with stubs. No route changes yet. | Low |
| **2 — Extract infrastructure** | Move `_IntervalsCredStore`, `_read_env/write_env`, pid helpers out of `launch.py` into new modules. Update imports in `launch.py`. | Low |
| **3 — Parallel service init** | Implement `ServiceContainer.initialise()` with `ThreadPoolExecutor` Wave 1/2/3. Replace `initialize_services()` in `launch.py` with `app.container.initialise()`. | Medium — test carefully on Pi |
| **4 — Blueprints (one at a time)** | Extract blueprints in this order (lowest-risk first): `stats_bp` → `routes_bp` → `weather_bp` → `planner_bp` → `core_bp` → `commute_bp` → `data_bp` → `integrations_bp` → `strava_bp`. Each is a separate PR. | Low per BP |
| **5 — Thin `launch.py`** | Replace inline app construction with `create_app()`, move process helpers, reduce to ~120 lines. | Low |
| **6 — Cleanup** | Remove now-dead code in `launch.py`, update `app/routes_DEPRECATED_FLASK/` tombstone, update `AGENTS.md` architecture section. | Low |

> **Testing checkpoint per phase:** run the full test suite + a manual smoke-test of `/api/status`, `/api/commute`, and `/api/weather` before merging.

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Blueprint `limiter` access — `@limiter.limit(...)` decorators need the `Limiter` instance | Store limiter on `app.extensions['limiter']`; blueprints access via `current_app.extensions['limiter']`. Alternatively, move limits to `app/factory.py` as a `limits` dict keyed by endpoint name. |
| `csrf.exempt` on individual routes | `CSRFProtect` supports per-blueprint exemptions; apply at registration. |
| Module-level globals in route handlers (`global _analysis_job`, etc.) | Replaced by `JobRegistry` on `app.container`; blueprints read/write via `current_app.container.jobs`. No global state outside `ServiceContainer`. |
| Circular imports between blueprints and container | Blueprints import only `current_app` from Flask (runtime lookup), never from each other or from `app.factory`. |
| Thread safety of `_services_initialized` reset after analysis | `ServiceContainer` exposes `container.reset_initialisation()` called at end of analysis/fetch jobs; replaces `_services_initialized = False`. |

---

## 10. Out of Scope

- Pushing `_enrich_commute_recommendation` into `CommuteService` (separate service refactor)
- Async Flask / ASGI migration
- Adding new tests (existing tests pass; new tests can be added per-feature as usual)
- Changing any API contract or response shape
- Touching `src/` or `app/services/`
