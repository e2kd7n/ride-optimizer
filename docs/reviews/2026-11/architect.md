# ride-optimizer: Architecture Review (2026-11-08)

> **Follow-up (2026-11-10).** Each finding below has a status line added after the review: fixed (commit or PR), or the GitHub issue that tracks it. The rest of the text is the review as written on 2026-11-08; line numbers are as of that date and may have drifted. Remaining work is grouped under the epics #654 (Pi memory and compute), #662 (background jobs and thread safety), #669 (frontend correctness) and #676 (dead code, CI and structure).

Scope: app/, src/, static/js, templates, cron/, config/, Dockerfile, gunicorn.conf.py, scripts/, CI. This was a read-only review. I ran the CI-excluded service and API tests from the console; the working tree stayed clean. All line numbers are as of commit `092a305`.

## What the product is for

The app is a personal cycling decision tool on a Raspberry Pi 4. It answers three questions:

- **Which commute should I ride today?** Route grouping plus weather.
- **Where should I ride to collect new tiles?** Explore.
- **What have I done?** Reports, stats and the ride chat.

Everything depends on one asset, the activity history in `data/cache/activities.json`. Two facts change what matters most right now:

- **Strava API access is inactive.** Issue #628 records `ApplicationInactive`, and memory notes say activities.json is now irreplaceable.
- **Garmin, through garth, is now the only working ingest path,** and garth is deprecated (#636). `GarminService.fetch_activities` (app/services/garmin_service.py:92-118) already pulls tracks per activity (`_fetch_polyline`, :120-150). So the app's data supply depends on an unmaintained library that is installed unpinned (requirements.txt:23 `garth>=0.4.0`; the Dockerfile installs requirements.txt, not `requirements.lock.txt`).

Effort is going into broad P3 epics: Data Cleanup (#628), RideWithGPS (#594) and yard/übersquadrat (#641). Meanwhile the core loop (ingest → analyse → recommend/explore) has unresolved correctness and robustness gaps (#619, #620, #621-#625).

---

## Top 10 recommendations (prioritised)

| # | Recommendation | Area | Impact | Effort | Tracked in |
|---|---|---|---|---|---|
| 1 | Make the ingest path safe and source-agnostic: pin or wrap garth behind a `GarminClient` interface with a timeout, build the image from `requirements.lock.txt`, and do nightly multi-source ingest (#636, #619, #620) | Effectiveness | **High** | S–M | Done (PR #683, PR #685); #682 |
| 2 | Store route geometry compactly in `route_groups.json`/`long_rides.json` (encoded polyline, decoded lazily), not full `[[lat,lon],...]` for every route in every group; drop `indent=2` for cache files | Memory/CPU | **High** | M | #656 |
| 3 | Keep one in-process activity store, not three or four parsed copies of activities.json; read route groups once (not again in maps_api); drop `AnalysisService._activities` after a run; add `slots=True` to `Activity` | Memory | **High** | M | #655 |
| 4 | Run the nightly analysis in its own process (`podman exec … python -m …`), not as a thread inside the single gunicorn worker; the worker reloads results by mtime | Memory/robustness | **High** | M | #657 |
| 5 | Fix cold boot: add a cheap `/healthz`, start `initialise()` on a boot thread, and stop `/api/status` and the container healthcheck from triggering a blocking full init that holds 1 of 4 request threads each | Robustness | **High** | S | #658 |
| 6 | Compact the tile index: integer keys, drop the per-tile `activity_ids` lists, and give bbox queries a spatial bucket instead of scanning every tile with `split(",")` | CPU/memory | Med–High | S–M | #659 |
| 7 | Go ahead with the own-router plan, sequenced so M0 and M2 (roadless tiles from the graph, which removes Overpass) come first. Freeze new investment in the ORS `refineRoute` stages and `exploration-worker.js` heuristics. Build new objectives (yard, übersquadrat, RWGPS) as planner-agnostic scorers | Effectiveness | **High** | L | #643 (M0 #645 and M2 #647 first) |
| 8 | Delete or quarantine dead and CLI-era code: `main.py` + `src/optimizer.py` + most of `src/visualizer.py`, the macOS-terminal/migration-subprocess geocoding code in `route_analyzer.py`, `PlannerService.generate_long_rides_map`, and the orphan `data/ride_optimizer.db`. Replace the Folium commute iframe with the existing `/api/maps` Leaflet JSON | Maintainability | Med | M | #678, #681 |
| 9 | CI hygiene: fix the stale `--ignore` list (6 of its files don't exist, and it excludes about 200 passing tests), fix the 3 failing `test_api` tests, use a multi-stage Dockerfile without gcc/g++ | Quality | Med | S | #677 |
| 10 | SQLite (#131), phased: activities plus tile index first (UPSERT ingest, indexed range queries), then route-group membership. Use it as the vehicle for #2, #3 and #6, not as a big-bang rewrite | Persistence | High (long-term) | L | #131 |

---

## 1. Effectiveness toward the product goal

### 1.1 The data source is the critical risk, not features (High, S–M)

> **Status (2026-11-10):** Done: `GarminClient` interface, private client with timeout, pinned garth (#636), multi-source sync (#619, #620), all in PR #683. Image built from the lock file in PR #685. Moving off garth: #682, which cross-links #607.

- Strava ingest is dead, so Garmin is the only live source. `GarminService` calls the global `garth` module directly in every method: app/services/garmin_service.py:39-44 (`garth.resume`, `garth.client`), :54-60 (`garth.login`), :95-100 and :130-133 (`garth.connectapi`). That causes three problems:
  - There is no seam for swapping libraries.
  - It relies on module-global client state, which is shared across gthread request threads and background jobs.
  - There is no `garth.configure(timeout=…)` anywhere in the file. #628 reports that an expired-token refresh hung indefinitely. In a 4-thread worker, that permanently takes one thread out of service.
- The Dockerfile runs `pip install -r requirements.txt` (Dockerfile:28-33), which has floor-only pins (`garth>=0.4.0`). The checked-in `requirements.lock.txt` (`garth==0.8.0`) is never used for the image. A garth release that breaks or removes itself would land on the Pi at the next auto-update.
- Recommendations:
  - Build from the lock file.
  - Add a thin `GarminClient` protocol with a timeout.
  - Treat #636 as blocking for anything that adds Garmin writes (#631).
  - #607 (official Garmin API) and #636 overlap; merge them or cross-link them.

### 1.2 Release scope is misallocated

> **Status (2026-11-10):** Applied in the 0.22.0/0.23.0 triage (`b1768a9`).

0.22.0 holds three P3 epics (#628, #594, #641) plus #636. Meanwhile:

- #620 (nightly multi-source pull) and #619 ("Backfill this month" fails without Strava) are unassigned P2s.
- With Strava gone, these are what keep commute recommendations and Explore coverage fed.

Recommendations:

- Pull #619, #620 and #623 (gear cache emptied) into 0.22.0.
- Move #594 and its children out to a future milestone.
- Reduce #628 to #629 + #630 + #636 for this release. The epic itself calls its ongoing value "real but modest".

### 1.3 Dead and duplicate subsystems

> **Status (2026-11-10):** Dead code, the duplicate `long_rides:` key, the stale Dockerfile comment and the CLAUDE.md drift: #678. Folium commute map: #681. Rejecting duplicate config keys at load: #687.

| Item | Evidence | Recommendation |
|---|---|---|
| `main.py` (CLI) + `legacy/` | main.py:59-68 imports `RouteOptimizer`, `RouteVisualizer`, `ReportGenerator` | Move to `legacy/` or delete. It is the only thing keeping `src/optimizer.py` alive. |
| `src/optimizer.py` (464 lines) | No import from app/ or cron/; only main.py and tests/test_optimizer.py | Delete with main.py. |
| `src/visualizer.py` (1,329 lines, Folium) | The web app uses only `create_base_map`, `add_location_markers`, `add_weather_display` (app/services/commute_service.py:256-349) and `add_light_basemap` (app/services/planner_service.py:20) | Render the commute map with Leaflet from `/api/maps/commute` (app/api/maps_api.py already exists), then drop Folium. Today `/api/commute/map` rebuilds the Folium HTML on every request with no cache (app/api/commute_bp.py:458-512). |
| `PlannerService.generate_long_rides_map` | app/services/planner_service.py:940-1115, no caller | Delete. |
| PlannerService endpoints | CLAUDE.md says no page calls them, but static/js/dashboard.js:883 calls `getLongRideRecommendations`. The other three endpoints (`/planner/rides/nearby`, `/rides/<id>`, `/analyze`, app/api/planner_bp.py:89-160) are still unconsumed | Fix the CLAUDE.md drift. Don't build a "planner page". Fold any remaining long-ride planning into own-router/RWGPS discussions. |
| CLI-era code in the core engine | src/route_analyzer.py:1097-1160 opens a macOS Terminal through osascript. :1282-1540 runs background geocoding that shells out to `scripts/migrate_cache_to_json_storage.py` (:1484), but `scripts/` isn't copied into the image (Dockerfile:35-42), so that step always fails in production | Remove. Naming belongs in `route_namer.py`, driven by `AnalysisService`. Roughly 40% of route_analyzer.py is not grouping logic. |
| `data/ride_optimizer.db` | 147 KB SQLite file with no code reference (no `sqlite3` import in app/src/cron/scripts) | Delete it, or make it the start of #131. |
| config.yaml duplicate key | `long_rides:` appears at config/config.yaml:50 (empty) and :112 | PyYAML silently keeps the last value. Remove line 50 and reject duplicate keys at load time. |

### 1.4 What would most improve the rider's outcomes

> **Status (2026-11-10):** #620, #621 and #622 are fixed. #624 is still open. Explore: own-router epic #643.

1. Reliable automatic ingest from whichever source works (#620), so recommendations and coverage are never stale.
2. Explore quality: fewer turns and no cluster leftovers. The own-router design (plans/own-router/ARCHITECTURE.md) is the right long-term bet for a Pi deployment because it moves planning to the browser. Its M2 milestone alone removes the Overpass dependency behind the water outages.
3. Data correctness in Reports and chat (#621 tool JSON corrupted by the PII sanitizer, #622 non-ride totals, #624 GPS-glitch records). These are small fixes that users see.

---

## 2. Compute efficiency

### 2.1 Cold start and init (High, S)

> **Status (2026-11-10):** #658.

- `ServiceContainer.initialise()` runs lazily on the first request (app/container.py:76-91), and `_init_lock` serialises callers (:68-72). The gunicorn comment says boot now takes "minutes" on the Pi (gunicorn.conf.py, `timeout = 600` comment).
- `/api/status` calls `container.initialise()` (app/api/core_bp.py:49-53). It is the container HEALTHCHECK (Dockerfile:51-52) and the pi4 status probe.
- During boot, every probe and page load blocks on `_init_lock` while holding one of only 4 gthread threads. Two probes plus one page load leave one thread for everything else, including static assets.
- Recommendations:
  - Add `/healthz`, which returns 200 without initialising.
  - Make `/api/status` report "warming" while `_initialised` is False.
  - Start `initialise()` on a daemon thread from `create_app()` (or a gunicorn `post_worker_init` hook) so boot doesn't wait for a user.

### 2.2 Per-request scans

> **Status (2026-11-10):** Tile scans: #659. Full parse just to read the count: #655. Stats memoisation not filed; the review judged it acceptable as is.

- **Tile coverage bbox query** (src/coverage_tracker.py:1129-1135) iterates every indexed tile and runs `key.split(",")` plus two `int()` calls per tile, at up to 60 requests a minute (app/api/planner_bp.py:164). The code notes 65k+ tiles at z14 in production (coverage_tracker.py:113-124), and z17 is far larger. Use integer keys plus a coarse bucket dict (for example keyed by `(tx>>6, ty>>6)`) so a viewport touches only its buckets. That turns O(all tiles) into O(tiles in view).
- **`get_tile_coverage_all`** (:1158-1190) re-splits every key twice.
- **`/api/fetch` job** parses all of activities.json only to read `count` (app/api/data_bp.py:219-225). Use the shared `load_cached_activities()`, or store the count in `analysis_status.json`.
- **Stats endpoints** (app/api/stats_bp.py:255-445) run O(n) Python passes over about 8k objects per request. That is acceptable. Memoise per mtime if Reports feels slow.

### 2.3 Analysis hot path

> **Status (2026-11-10):** #656 (feed the sparse candidates straight to the clustering).

- Commute grouping (src/route_analyzer.py:697-760) is now well designed:
  - exact cheap prefilter (`possible_match_pairs`)
  - persistent similarity cache
  - optional ProcessPool
- It builds a dense `np.zeros((n, n))` score matrix per direction (:740-746) and then extracts the upper triangle (:872-878). At n=3k that is about 72 MB of float64 transient per direction, which is significant on a 1.5 GB container (docker-compose.yml:61 `mem_limit: 1536m`). The sparse `candidates` list is already in hand; feed it straight to `cluster_by_centres`, which already takes an edge iterator.
- `ANALYSIS_N_WORKERS=1` on the Pi is right (app/services/analysis_service.py:30-39). Forking a ProcessPool from a 200+ MB worker would double resident memory.

### 2.4 Blocking I/O on request threads

> **Status (2026-11-10):** garth timeout fixed in `c1fa669` and #636. Folium map rebuilt on every request: #678 and #681.

- ORS calls are well guarded: a semaphore of 2 (app/services/exploration_service.py:100-101), wall-clock budgets (:563, :679-683) and route rate limits (planner_bp.py:346).
- Overpass moved to background downloads (9ab942a).
- The remaining unguarded risk is garth calls with no timeout (1.1).
- The commute Folium map is CPU-bound HTML generation on every home-page load (commute_bp.py:458-512). Cache it per (route_groups mtime, weather hour), or drop it as in item 8.

### 2.5 Explore client-side

> **Status (2026-11-10):** #661 (client caches) and the own-router epic #643.

- static/js/explore.js is 2,744 lines. `refineRoute` runs five stages that each make another ORS round trip (own-router doc §1).
- Each round trip costs ORS quota and a Pi thread for up to `ors_timeout_seconds`.
- The own-router plan moves this work to the browser, which is the right call for a Pi.

---

## 3. Memory efficiency

### 3.1 Duplicate copies of the same data (High)

> **Status (2026-11-10):** #655.

| Copy | Where | Form |
|---|---|---|
| activities #1 | app/api/activity_cache.py:26-64 | `Activity` dataclasses, all types (no `__slots__`, src/data_fetcher.py:25-52) |
| activities #2 | src/coverage_tracker.py:828-855 | raw dicts (ride types), held forever in `_activities_cache` |
| activities #3 | app/services/analysis_service.py:405-425 | `Activity` objects kept in `self._activities` after every run, never released |
| activities #4 (transient) | app/api/data_bp.py:219-225 | whole-file parse only to get a count |
| route groups #1 | app/services/analysis_service.py:135-145 | deserialised `RouteGroup`/`Route` objects |
| route groups #2 | app/api/maps_api.py:22-31 | `read_cached` raw dict of the whole route_groups.json, kept in the module-level `_READ_CACHE` |
| route groups #3 (fallback) | app/services/route_library_service.py:91-112 | raw dicts when no AnalysisService |

- A JSON file of about 75 MB (container.py:66-70 comment) typically expands 5-10x when parsed into Python lists of floats.
- Holding route groups twice (#1 and #2) is probably the largest single waste in the worker. The "~220MB" app figure in gunicorn.conf.py's `preload_app` comment is consistent with that.
- Recommendations:
  - `maps_api` reads from `container.analysis_service.get_route_groups()`.
  - `CoverageTracker` takes an activities provider (`load_cached_activities`) and keeps only `(id, start_date, polyline)`.
  - Add `@dataclass(slots=True)` to `Activity`; on Python 3.11 that is a one-line change.
  - Set `self._activities = None` at the end of `run_full_analysis`.

### 3.2 Geometry storage (High, M)

> **Status (2026-11-10):** #656.

- `_serialize_route` writes full decoded coordinates for every route in every group, plus the representative route again (analysis_service.py:250-276).
- Long rides do the same (:309-315).
- JSONStorage writes with `indent=2` (src/json_storage.py:340), which adds about 30-40% whitespace to multi-MB files and slows parsing.
- Recommendations:
  - Store Google-encoded polylines (already the format in activities.json).
  - Decode lazily, only for the representative route or detail endpoints.
  - Drop `indent` for cache files.
- That shrinks route_groups.json and its parsed footprint several-fold, and cold boot with it.

### 3.3 Tile index (Med–High, S–M)

> **Status (2026-11-10):** #659.

- Each tile is a `"x,y"` string key mapped to `{"first_ridden": str, "activity_ids": [..]}` (coverage_tracker.py:1029-1041). That is about 300-400 B per tile, plus list growth on heavily ridden commute tiles.
- Nothing reads the per-tile `activity_ids`. Incremental bookkeeping uses `indexed_activity_ids`, and responses send only keys (coverage_tracker.py:113-124).
- Recommendations:
  - Store `{int_key: first_ridden_ordinal}`.
  - Keep `indexed_activity_ids` as is.
- In-memory and on-disk size should drop roughly 3-5x.

### 3.4 Worker and thread model

> **Status (2026-11-10):** #657. Stale "512MB" Dockerfile comment: #678.

The single gthread worker with `preload_app=False` and `max_requests=0` is right for the 1.5 GB container limit (gunicorn.conf.py; docker-compose.yml:61). Note the Dockerfile comment (Dockerfile:8-9) still says "512MB container", which is stale. The catch is that CPython rarely returns heap after the nightly analysis peak: the worker keeps its high-water mark until it restarts. Two options:

- **Preferred (item 4): run analysis in a separate process.** `cron/daily_analysis.py` already triggers analysis over HTTP (cron/daily_analysis.py:94-120). It could instead run `podman exec <ctr> python -m app.jobs.analyze`. That job writes outputs through JSONStorage and exits, freeing all of its memory. The worker reloads by mtime, the way `activity_cache` already does.
- **Minimum:** release `_activities` and call `gc.collect()` after the run.

The separate process also fixes the documented failure where a worker restart kills in-memory job state mid-run (gunicorn.conf.py `max_requests` comment; cron/daily_analysis.py:56-61).

### 3.5 Dockerfile

> **Status (2026-11-10):** Lock file: PR #685. Multi-stage build: #677.

- gcc and g++ stay in the final image (Dockerfile:19-21). Use a multi-stage build. That gives a smaller image and a faster Pi pull; it doesn't change RSS.
- The image doesn't use the lock file (1.1).

---

## 4. Persistence and structure

### 4.1 JSON vs SQLite (#131)

> **Status (2026-11-10):** #131.

What JSON costs today:

- activities.json is rewritten whole on every fetch (coverage_tracker.py:964-966: "merged-and-resorted whole on every fetch").
- Every file is parsed whole on boot.
- There are three ad hoc mtime memo layers (`activity_cache`, `JSONStorage.read_cached`, coverage `_activities_cache`), each with its own invalidation. `invalidate_caches` (coverage_tracker.py:1655-1679) must be called from three data_bp sites.

Recommended phasing, each step shippable:

1. `activities` table (id, source, type, start_date, distance, …, polyline) with indexes on start_date and type. Stats and chat queries become SQL. Ingest becomes an UPSERT, and the backup's ">2% drop" guard becomes a count query.
2. `tile_visit(zoom, tx, ty, first_ridden)` plus `indexed_activity(zoom, id)`. Viewport queries become indexed range scans, and the in-memory index goes away.
3. `route_group` plus `route_group_member(group_id, activity_id, is_plus)`. Geometry comes from `activities.polyline`, which removes the duplicate geometry in 3.2.

Keep `JSONStorage` for small settings and credential files. SQLite in WAL mode fits one worker writing while a cron process reads.

### 4.2 Service boundaries and coupling

> **Status (2026-11-10):** #686.

- `AnalysisService` is the de facto data repository: RouteLibrary, Commute and Planner all read through it (container.py:178-246). Make that explicit as a `RideRepository` (activities, groups, long rides and locations, reloaded on mtime). Then:
  - `activity_cache`, `maps_api.load_route_groups` and `CoverageTracker._load_activities` become thin consumers.
  - `refresh_services` (container.py:121-152) mostly turns into "repository reloaded".
- Blueprints and the chat gear source reach into `analysis_service.data_fetcher`, a property that forces Strava auth (analysis_service.py:100-105; container.py:325-327). With Strava inactive, chat's gear lookup attempts Strava auth. Gear should come from the cache file directly (related to #623).
- `ExplorationService` and `ChatService` are lazily built outside the init waves. That is fine, but ExplorationService holds its own activities copy (3.1).

### 4.3 Config sprawl

> **Status (2026-11-10):** #687.

- config/config.yaml (160 lines) mixes three things: live config, CLI-only settings (`output:`, :126-129) and Folium colours (`visualization:`, :101-110).
- It also has the duplicate `long_rides` key.
- Exploration rate limits are read with inline defaults at every call site (planner_bp.py:164-421). That gives two sources of truth for every default.
- Recommendation: one typed schema (marshmallow is already a dependency) that validates at startup and holds the defaults. Delete the CLI sections with main.py.

### 4.4 Testing strategy gaps

> **Status (2026-11-10):** CI ignore list and stale tests: #677. Explore benchmark: #644.

CI (.github/workflows/docker-publish.yml:51-67) `--ignore`s 14 paths:

- Six don't exist (`test_routes_*.py` ×5, `test_map_advanced_features.py`).
- The remaining excluded service and API suites mostly pass. Running `test_analysis_service`, `test_commute_service`, `test_route_library_service` and `test_api` locally gave **200 passed, 3 failed**. All three failures are in `test_api.py::TestExplorationRouteExcludeParam`, which is real drift in `/api/exploration/route`.

So the service layer and main API surface are untested in CI. Recommendations:

- Remove the stale ignores.
- Fix the 3 tests.
- Gate only genuinely slow or networked suites behind markers.

Commute matching has a benchmark (scripts/matching_benchmark/), but Explore doesn't. Check in `scripts/explore_benchmark/` (own-router doc §6) before more refine-stage tuning, so turns, U-turns and cluster leftovers are measured, not eyeballed.

---

## Release issue review

> **Status (2026-11-10):** The milestone and priority recommendations were applied in `b1768a9`.

Each issue was checked against the code and git log. Actions taken: **edited (appended "Architecture review (2026-11-08)" section, original text kept)** #594 and #514, where a stated assumption was wrong (GPX code does exist; Fréchet is gone). **Commented** on #641, #628, #591, #635 and #636. All posts succeeded on the first try and end with an automated-review line. No labels, milestones, priorities or assignees were changed; recommendations are below.

| Issue | Finding | Recommended change |
|---|---|---|
| #641 Explore yard/übersquadrat epic | Nothing implemented: no yard or übersquadrat code anywhere in static/js, app or src; children #637-#640 are all open. It has no P-label. #638 and #639 would add heuristics to `exploration-worker.js` Phase 1, which own-router M5/M7 retires. Yard needs full-history coverage, not the viewport bbox. | Add P3. Do #637 and #640 (planner-independent) now. Spec #638/#639 as objective functions both planners can call. |
| #628 Data Cleanup epic | Not started (no `src/duplicate_audit.py`). It deepens the garth dependency on the only live ingest path. Runner jobs as in-process threads die on a worker restart (the same failure as the nightly analysis). | Keep #629, #630 and #636 in 0.22.0. Move #631-#634 to the next release. Gate #631 on #636 and a durable job store. |
| #594 RWGPS epic | Not started. The epic says no GPX code exists, but explore.js has a client-side GPX export (static/js/explore.js:2655-2680). It overlaps own-router: route modification wants a local graph. | Move to a future milestone. #589 + #590 are the only independent checkpoint. |
| #591 RWGPS algorithm | A server-side Python port would be a third route planner, running on the Pi. | Defer until own-router M3/M4, then specify it as a constrained re-plan in the browser planner. |
| #635 Strava automation spike | Headless Chromium (300-500 MB resident) next to a gunicorn worker that already peaks at several hundred MB during analysis leaves no headroom in the 1536m container (docker-compose.yml:61). | Keep P4. Default to no-go; desktop-side only if pursued. |
| #636 garth deprecated | Garmin is now the only live ingest. requirements.txt is unpinned, and the image ignores the lock. No timeout, no seam (module-global `garth` calls). It duplicates #607. | Raise to P1. Immediate steps: build from the lock, add a timeout, add a `GarminClient` wrapper. Merge #607 into it or cross-link. |
| #514 Pi Zero cluster | The premise is outdated: matching no longer uses Fréchet or `similaritymeasures` (removed with #613). Analysis memory, not CPU, is the binding constraint. Zero Ws have 512 MB each, less than one analysis run needs. | Close as superseded by running analysis out of process (item 4), or leave at P4. |
