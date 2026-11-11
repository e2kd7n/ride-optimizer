# Backend bug hunt and code review: ride-optimizer

> **Follow-up (2026-11-10).** Each finding below has a status line added after the review: fixed (commit or PR), or the GitHub issue that tracks it. The rest of the text is the review as written on 2026-11-08; line numbers are as of that date and may have drifted. Remaining work is grouped under the epics #654 (Pi memory and compute), #662 (background jobs and thread safety), #669 (frontend correctness) and #676 (dead code, CI and structure).

Date: 2026-11-08. Scope: `app/` (factory, container, blueprints, services), `src/`, `cron/`, `launch.py`, `wsgi.py`, `gunicorn.conf.py`, `Dockerfile`. Read-only review at `main` @ 092a305.

The deployment model shapes the severity calls: one gunicorn worker with 4 gthreads, behind Caddy on the Pi, LAN-only, no app-level auth. Strava API access is inactive, so `data/cache/activities.json` can't be rebuilt from Strava. Every finding below comes from reading the code. Items marked **Plausible** depend on runtime behaviour I could not observe (for example, how the Pi behaves or how Strava responds).

## Test suite status

> **Status (2026-11-10):** The stale `TestExplorationRouteExcludeParam` tests, the order-dependent integration test and the CI `--ignore` list: #677.

`venv/Scripts/python.exe -m pytest -q` on Windows: **1489 passed, 9 failed, 22 errors, 11 skipped** (98 s).

| Failure | Cause | Real bug? |
|---|---|---|
| `test_api.py::TestExplorationRouteExcludeParam` (3) | The tests expect `compute_route(..., exclude=...)`, but the blueprint now also passes `bounds=None` (commit 81e3bb5). | Stale tests. The CI suite is red on these unless CI skips them. |
| `test_chat.py` (1 failure, 21 errors) | `anthropic` is not installed in the local venv. It is in `requirements.txt`. | Local environment only. |
| `test_json_storage::test_file_permissions`, `test_logging_config` perms (3), `test_cron_jobs::test_install_script_executable` | POSIX permission bits on Windows. | Windows-only. |
| `test_integration::test_route_extraction_and_grouping` (error) | Passes when run alone. | **Order-dependent / flaky test**. Worth isolating. |
| (log noise) `route_analyzer.py:1313` writes emoji to `geocoding_progress.txt` without `encoding='utf-8'` | cp1252 on Windows. On Linux/Pi it's fine (UTF-8 locale). | Low (dev only). |

No pyflakes/ruff/flake8 in the venv, so no static lint was run.

---

## Findings (most severe first)

### H1. `cache_cleanup` cron deletes `route_groups_cache.json` after 30 idle days, which resets group IDs that favourites and saved plans refer to (High)

> **Status (2026-11-10):** Fixed in `f5b1e09`. The groups and similarity caches are now kept indefinitely.
- `cron/cache_cleanup.py:66-97` deletes any `cache/*.json` whose mtime is older than its retention: `route_groups_cache` 30 days, `route_similarity_cache` 90 days.
- `src/route_analyzer.py:633-645`: on a perfect cache hit (no new or removed activities), `group_similar_routes()` returns the cached groups **without rewriting the file**, so its mtime never moves.
- `src/route_analyzer.py:881-895`: stable group IDs (#614) come *only* from `self.groups_cache` (that file). Its docstring says the IDs are what "saved plans and favourites refer to", and that a retired ID is never reused.
- **Failure scenario:** Strava is gone, so the nightly analysis sees no new rides. After 30 days the 03:00 cleanup deletes `route_groups_cache.json`. The next analysis regroups from scratch with no predecessors. IDs are renumbered and names are regenerated (extra Nominatim geocoding). `favorite_routes.json` and `saved_plans.json` then silently point at different routes or at nothing, and the "never reuse a retired ID" guarantee breaks. After 90 days the similarity cache goes too, which forces a full O(n²) pairwise recompute on the Pi.
- **Fix:** exclude `route_groups_cache` and `route_similarity_cache` from age-based cleanup (treat them like `geocoding`), or base cleanup on a "last read" timestamp. At minimum, `os.utime()` the groups cache on a cache hit.

### H2. Reading the *local* gear cache requires a successful Strava auth/refresh (High, Plausible on the Pi)

> **Status (2026-11-10):** Fixed in `f5b1e09` (new `cache_fetcher` that never touches Strava).
- `app/services/analysis_service.py:100-105`: the `data_fetcher` property calls `_ensure_authenticated()`, which calls `get_authenticated_client()`. That refreshes the token over the network when the access token has expired (every 6 h) and raises on failure. `_data_fetcher` stays `None` after a failure, so **every** call retries.
- Callers that only need local files:
  - `data_bp.py:457` (`GET /api/activities`)
  - `stats_bp.py:414` (`GET /api/stats/gear`)
  - `container.py:332` (chat `list_gear`)
  - `integrations_bp.py:315-321` (Garmin sync merge into the cache)
- **Failure scenario:** with the Strava app inactive (#628 says `ApplicationInactive`), or with `config/credentials.json` absent, each of these does a blocking Strava token call. Then:
  - `/api/activities` and `/api/stats/gear` raise, and the user gets a 500.
  - the chat's gear tool errors.
  - **Garmin sync fails outright** with a Strava auth error, even though it never needs Strava.
- **Fix:** build a `StravaDataFetcher` for cache-only use without a client (`StravaDataFetcher(None, config)`), or move `load_cached_gear`/`load_cached_activities`/`cache_activities` to module-level functions. Authenticate only for `fetch_*`/`backfill_*`.

### H3. `DELETE /api/user/data` wipes the irreplaceable `activities.json` with only CSRF in the way (High)

> **Status (2026-11-10):** Fixed in `f5b1e09`. Deletion is off unless `ALLOW_USER_DATA_DELETION=true` and needs the exact phrase "DELETE ALL MY DATA".
- `app/api/core_bp.py:140-178`. The app has no authentication, and `/api/csrf-token` hands a token to any LAN client. A `{"confirm": true}` body deletes every `data/*.json`, `data/cache/activities.json` and `config/credentials.json`. Nothing is backed up first, and the deletes take no locks.
- **Failure scenario:** a stray script, a misclick, or any device on the LAN removes the only copy of 8k activities, which Strava can no longer re-supply. The nightly `~/backups` copy limits the damage to at most one day.
- It is also incomplete as a GDPR erase: it leaves `cache/route_similarity_cache.json`, `cache/route_groups_cache.json`, the weather caches (GPS keys), `data/cache/tile_index_*.json`, water caches, `config/.garmin_tokens`, the intervals creds and the TrainerRoad feed.
- **Fix:** move `activities.json` to a timestamped backup (0600) instead of unlinking it, or require a typed confirmation and a server-side env flag. Either remove the other PII caches too or document the gaps.

### M1. Stopping an analysis publishes partial route groups to Commute/Planner (Medium)

> **Status (2026-11-10):** Fixed by #663 (PR #683).
- `analysis_service.py:541` assigns `self._route_groups = route_analyzer.group_similar_routes()` **before** the stop check at :544. `route_analyzer.py:671-676` returns partial groups on stop and doesn't save them (#612), but the in-memory service now holds them.
- `data_bp.py:139-152` then calls `container.refresh_services('commute', 'planner')` unconditionally, which rebuilds CommuteService from the partial or empty groups.
- **Failure scenario:** the user clicks "Stop" during grouping. The home page's commute recommendations and the routes library show a fraction of the routes, or none, until the next full analysis or a restart.
- **Fix:** keep grouping results in locals and assign to `self._route_groups`/`_long_rides`/locations only after a full successful run. Also skip `refresh_services` when the result is `stopped` or `error`.

### M2. Analysis errors are reported to the UI as "Done" (Medium)

> **Status (2026-11-10):** Fixed by #663 (PR #683).
- `run_full_analysis` catches every exception and returns `{'status': 'error', ...}` (`analysis_service.py:595-605`). `data_bp.py:133-140` marks the job `status='done'` with the label "Done — 0 activities". It also calls `refresh_services`.
- `cron/daily_analysis.py:186-192` already works around this. The browser does not.
- **Fix:** in `_run`, if `result.get('status') == 'error'`, set `status='error'`. Do the same for the fetch and backfill follow-up analyses (`data_bp.py:255`, `:340`), which ignore the return value entirely.

### M3. Background job state can stick at "running" forever (Medium)

> **Status (2026-11-10):** Garmin `days` case fixed in `f5b1e09`. General fix (`claim_job` plus a teardown hook) in #664 (PR #683).
- `JobState.try_start()` sets `status='running'` before input parsing (`app/jobs/job_state.py`). Uncaught exceptions after that point leave the job locked until restart:
  - `integrations_bp.py:310`: `int(data.get('days', 90))` raises ValueError on `"abc"` and returns a 500. `garmin_sync` then answers 409 `already_running` forever. A negative `days` is also accepted.
  - `data_bp.py:214`: `int(data.get('limit', 1000))` behaves the same way, and `limit` has no upper bound.
  - Any exception in `container.initialise()` or `svc.is_connected()` after `try_start`, in all six job endpoints.
- **Fix:** parse and validate before `try_start`, or wrap the post-start section in `try/except: job.reset(idle); raise`.

### M4. Activities-cache thundering herd: up to 4 parallel parses of a ~75 MB JSON after every write (Medium, memory/OOM)

> **Status (2026-11-10):** #655.
- `app/api/activity_cache.py:49-64` takes no single-flight lock. When the mtime changes (any fetch, Garmin sync or gear backfill), each concurrent request that misses parses the whole file and builds every `Activity` object at the same time.
- Other full parses of the same file:
  - `data_fetcher.is_cache_valid()` and `_get_cache_age_days()`: two more full `json.load` calls just to read `timestamp` (`data_fetcher.py:597-633`).
  - `data_bp.py:221-246`: two more.
  - `CoverageTracker._load_activities`.
  - `analysis_service` (it opens the file twice at :420-423).
- The analysis cache already got a lock for exactly this reason (`analysis_service.py:116-121`).
- **Fix:** take a per-stamp load lock in `load_cached_activities` (double-checked). Read `timestamp`/`count` from a small sidecar or from `JSONStorage.read_cached`. Drop the duplicate open at `analysis_service.py:420`.

### M5. Chat request can hold a gunicorn thread for about 14 minutes, and rate limits are effectively global (Medium)

> **Status (2026-11-10):** Fixed in `c1fa669`: chat has an overall 150 s budget, and ProxyFix makes rate limits per client again.
- `chat_service.py:115-158` makes up to `max_tool_iterations+1 = 7` API calls. Each one has `timeout=60` and `max_retries=1`, so the worst case is about 14 minutes with no overall deadline. With 4 threads, a few slow chats starve the app.
- `app/extensions.py`: `key_func=get_remote_address`, and there is no `ProxyFix` in `factory.py`/`wsgi.py`. Behind Caddy every client is `127.0.0.1`, so each "per-IP" limit (for example 10/min on chat, connect and analyze) is shared by everyone. `request.is_secure` is also always False, so the app's HSTS branch never fires (Caddy may set HSTS itself) and `url_for(_external=True)` builds `http://` Strava redirect URIs.
- **Fix:** add an overall wall-clock budget to `chat()` (check elapsed time before each `_create`), or lower `max_retries` to 0. Add `werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1)`, since Caddy is the only hop.

### M6. Chunked ORS routes bypass the per-request wall-clock budget (Medium)

> **Status (2026-11-10):** #667.
- `exploration_service.py:536-537` and `606-657`: `_compute_chunked_route` calls `compute_route()` once per 50-waypoint chunk, and each call gets a **fresh** `ors_max_wait_seconds` (40 s) deadline. A 250-waypoint request is 6 chunks, so it can take about 4 minutes. Each chunk can also make several ORS calls (profile fallback, unfenced retry, up to 10 unroutable-drop retries).
- That holds one of 4 threads and can burn ORS's 40 req/min quota in one click.
- **Fix:** compute one deadline in the outer call and pass it into each chunk.

### M7. `WeatherFetcher` caches are mutated from 4 threads without a lock; file writes aren't atomic (Medium)

> **Status (2026-11-10):** #666.
- `src/weather_fetcher.py:211-245`: `_find_cached_weather` runs `del self.cache[k]` over a `list()` snapshot. Two threads expiring the same key raise `KeyError`, which is outside any try in `get_current_conditions` (:505).
- `_save_cache` (:171-190) iterates `self.cache.items()` while another thread inserts, which raises `RuntimeError: dictionary changed size during iteration` (swallowed, so the save is lost). It writes with plain `open(path,'w')`: a concurrent writer, or the `weather_refresh` cron in another process, can truncate or interleave the file, and the cache silently resets to empty on the next load. The forecast and AQI caches have the same pattern.
- **Fix:** add a `threading.Lock` around cache dict access, and write through `JSONStorage` (atomic plus 0600) or temp-file plus `os.replace`.

### M8. Tile index never drops deleted activities (Medium; blocks #632 and #637)

> **Status (2026-11-10):** #659.
- `coverage_tracker.py:1000-1056`: `new_ids = current_ids - indexed_ids` only **adds**. IDs removed from `activities.json` (cross-source dedupe, manual cleanup, the planned #628 deletes) keep contributing tiles until someone runs the manual "Clear Cache" `hard_invalidate_caches()`.
- `first_ridden` is also wrong: on a fresh build, activities come in `start_date`-descending order (`data_fetcher.py:516`), so a tile's `first_ridden` is the **newest** ride, and later rides never lower it. Nothing reads the field today (dead data). Fix it or drop it, since it also bloats `tile_index_*.json` along with the per-tile `activity_ids` lists.
- **Fix:** when `indexed_ids - current_ids` is non-empty, rebuild (or subtract, using the per-tile `activity_ids`). Compute `first_ridden` as min().

### M9. Garmin sync merge re-writes every existing activity from a stale snapshot (Medium)

> **Status (2026-11-10):** Fixed in `f5b1e09`.
- `integrations_bp.py:316-321` loads `existing` outside the lock, then calls `cache_activities(existing + new_acts)`. Inside the mutator every `existing` record is "updated" (`data_fetcher.py:495-498`) with the stale copy.
- **Failure scenario:** a gear-ID backfill or a Strava fetch commits while the Garmin sync is downloading polylines, which takes minutes. The Garmin merge then overwrites those records with their pre-backfill versions, and `gear_id` patches are lost.
- **Fix:** pass only `new_acts` to `cache_activities()`. The mutator already merges against what's on disk and does the cross-source dedupe.

### M10. `write_env` (runtime_overrides.env) is an unlocked, non-atomic read-modify-write (Medium, Plausible link to "Pi .env gets wiped")

> **Status (2026-11-10):** Fixed in `c1fa669` (locked, atomic write with 0600 permissions).
- `app/credentials/env_helpers.py:54-78`. Two concurrent writers lose one write: ORS connect, location save and Strava setup each run on a different gthread. A truncating `write_text` can also be read half-written, and a crash mid-write truncates the file. Either way `HOME_LATITUDE`/`HOME_LONGITUDE` can disappear, which matches the known "HOME_LATITUDE keeps disappearing" symptom. I can't prove it's the root cause.
- **Fix:** take a module lock or a `fcntl` lock on a sidecar file, and write to a temp file then `os.replace`, chmod 0600 before the rename.

### M11. GarminService uses garth's process-global client; tokens are written without 0600 (Medium)

> **Status (2026-11-10):** Timeout, token permissions and login lock fixed in `c1fa669`. Private client and `GarminClient` interface: #636 (PR #683). Moving off garth: #682.
- `garmin_service.py`: `garth.resume/login/connectapi` all act on the module-global `garth.client`. Status checks, sync and connect run on different gthreads, and a connect during a sync swaps credentials mid-run.
- `garth.save()` writes `oauth1_token.json`/`oauth2_token.json` with the default umask. `token_dir.mkdir()` has no mode, unlike every other credential store (`IntervalsCredStore` and `SecureTokenStorage` chmod 0600).
- There is no timeout: `garth.configure(timeout=...)` is never called (#630 notes an expired-token refresh hung forever).
- **Fix:** use a per-service `garth.Client()` instance guarded by a lock. Chmod the token dir to 0700 and its files to 0600 after `save()`, and configure a timeout.

### M12. Container refresh is unlocked and publishes half-initialised services (Medium)

> **Status (2026-11-10):** #665.
- `container.py:200-225`: `_init_commute` assigns `self.commute_service = CommuteService(...)` and only then runs `_load_commute_data()` / `initialize()`. Requests in that window see a service with no route groups. `_init_planner` has the same pattern.
- `refresh_services()` takes no lock, so a settings save, a finishing analysis thread and a Strava callback can rebuild the same service concurrently.
- **Fix:** build into a local variable, initialise it, then assign. Serialise `refresh_services` with a lock.

### L1. `sanitize_address` is overly broad everywhere it's used, not just in chat (Low-Med; root cause of #621)

> **Status (2026-11-10):** The prefix-matching half was fixed with #621 (`99d63f8`). Still too broad because of `re.IGNORECASE`: #688.
- `pii_sanitizer.py:73-80`: `re.IGNORECASE` makes `[A-Z][a-z]+` match any word, and there is no trailing `\b`, so `St`/`Dr`/`Pl`/`Ct`/`Way` match word prefixes. For example, `"100 Mile Strava"` becomes `[STREET]rava`, and `"2 Laps Plus"` becomes `[STREET]us`. The same function runs over all logs via `sanitize_log_message`, so log lines get mangled too. See #621 for the chat-specific corruption.

### L2. NaN bboxes pass validation (Low)

> **Status (2026-11-10):** Fixed in `c1fa669`.
- `planner_bp.py:44-52`: `request.args.get(..., type=float)` accepts `nan`, and every comparison with NaN is False, so `_validate_bbox` passes. `/exploration/tiles` and `/exploration/roadless-tiles` then do NaN math, and roadless can fire an Overpass request. `verify-tiles` and `new-tiles` coordinates have no range or finite check.
- **Fix:** add `math.isfinite` plus range checks, as `_validate_route_bounds` already does.

### L3. Mixed timestamp formats in `start_date` (Low)

> **Status (2026-11-10):** #679.
- Garmin activities store local `"YYYY-MM-DD HH:MM:SS"` in `start_date` (`data_fetcher.py:154`). Strava stores UTC `...Z`.
- String sorts mix the two (`data_fetcher.py:516`, `/api/activities` `date_desc`, `/api/cache-info` earliest/latest). Code that treats `start_date` as UTC (stats fallback `astimezone()`) is off by the UTC offset for Garmin rides.
- **Fix:** normalise Garmin `start_date` to UTC ISO using `startTimeGMT`.

### L4. Garmin and Strava IDs share one key space (Low, Plausible)

> **Status (2026-11-10):** #679.
- `cache_activities` merges by `act.id` (`data_fetcher.py:495`). Both platforms use about 10–11 digit integers. A collision would let a Garmin ride silently *replace* a Strava ride.
- **Fix:** key by `(source, id)`, or namespace Garmin IDs.

### L5. `/api/activities` and `/api/stats/calendar` edge cases (Low)

> **Status (2026-11-10):** #679.
- A negative `limit` slices oddly (`data_bp.py:418`).
- `distance`/`average_speed` of `None` (possible for Garmin non-distance activities) raises TypeError in `_serialize` and the sort, and returns a 500.
- `year=0` makes `calendar.monthrange` raise and return a 500 (`stats_bp.py:356`).

### L6. `JSONStorage.update()` hands `default` to the mutator when the file is corrupt (Low)

> **Status (2026-11-10):** #668.
- `json_storage.py:390-400`. For `saved_plans.json` this silently replaces a corrupt but recoverable file with `[new_plan]`. `data_fetcher.cache_activities` guards against this explicitly. Other callers (`core_bp` plans) do not.
- **Fix:** raise, or back up the corrupt file, instead of passing `default` when the file exists but can't be parsed.
- Also: `delete()` takes no `_locked`, and the Windows `read()` takes a lock on the data file itself, which blocks writers' `replace` for up to 2 s. That's harmless on the Pi.

### L7. `SettingsService.update_settings` and cron `job_history.json` use read-then-write instead of `storage.update()` (Low)

> **Status (2026-11-10):** #668.
- `settings_service.py:65-85` and `cron/daily_analysis.py:84-88`. Concurrent writers lose updates.

### L8. Strava status endpoint does a network refresh on every poll (Low)

> **Status (2026-11-10):** Network refresh on every poll: #680. Unescaped callback `error` and `setup_verify` treating 5xx as valid: fixed in `c1fa669`.
- `strava_bp.py:44-63` posts to `oauth/token` (15 s timeout) on every `/api/strava/status` call once the access token has expired. With the Strava app inactive, every Settings page load pays that cost and holds a thread. `strava_callback` also reflects `error` unescaped into the redirect query string (`:95`).
- `setup_verify` treats any non-401 response, including 5xx, as "Credentials appear valid" (`:235`).

### L9. Other low items

> **Status (2026-11-10):** `secret_key` permissions fixed in `c1fa669`. Healthcheck triggering the full init: #658. `merge_cache` default and `save_plan` validation and growth: #668. ORS `0.0` timeout and pruned-key caching: #667. Empty `app/` directories: #678.
- `factory.py:35-38`: `secret_key` is written with umask perms, then chmodded (a brief window). Use `os.open(..., 0o600)`.
- `Dockerfile` HEALTHCHECK `start-period=180s, timeout=10s` hits `/api/status`, which triggers the full lazy `container.initialise()`. The gunicorn comment says that takes minutes on the Pi, so the container can be marked unhealthy during cold boot.
- `fetch_activities(merge_cache=False)` by default *replaces* the cache with the fetched batch (`data_fetcher.py:448`). Both current callers pass `True`, but the default is a data-loss footgun given the Strava sunset. Flip the default.
- ORS: `_budget_timeout()` can return `0.0`, and requests/urllib3 reject a timeout of 0 with `ValueError`, which `get_route` doesn't catch (`ors_client.py:107-112`). A narrow race. Also, a result after an unroutable-waypoint drop is cached only under the pruned key, so repeating the original request always costs 2 ORS calls.
- `save_plan` stores `distance`/`duration`/`elevation` unvalidated (any JSON), and `saved_plans.json` grows without bound.
- Dead directories: `app/models/`, `app/routes/` and `app/scheduler/` contain only `__pycache__`.

## Things checked and found OK
- `JSONStorage` sidecar locking, the atomic rename, 0600 permissions and filename validation. The `read_cached` stamp race errs on the safe side.
- `cache_activities` mutator (merge inside the lock, refuses to overwrite an unreadable cache, cross-source dedupe).
- `TrainerRoadService` feed SSRF guard (scheme check, private-IP rejection, IP pinning, no redirects).
- Exploration route cache locking (#577), the semaphore, and the per-zoom tile-index locks with copy-on-write.
- `route_comparison` metric math (shared lat0, metre projection, symmetric p95/coverage).
- Strava OAuth state check. CSP and security headers.

## Test gaps for risky code

> **Status (2026-11-10):** Tests now exist for H1 (`test_cron_jobs`), M1/M2 (`test_analysis_service`, PR #683), M10 (`test_security_hardening`) and the #621 round trip (`test_chat`). Some of these files are still skipped in CI until #677 lands. The `WeatherFetcher` concurrency test belongs with #666.
- No test that an analysis stopped mid-run, or a failed one, leaves the existing groups and CommuteService untouched (M1, M2).
- No test for `cache_cleanup` against the route-analyzer cache files (H1).
- No test that cache-only endpoints work with no Strava credentials, or with refresh failing (H2).
- No concurrency test for `WeatherFetcher` (M7) or `write_env` (M10).
- No round-trip test that chat tool output parses with `json.loads` (#621).
- The exploration exclude-param tests are stale (they now fail).

---

## Release issue review (0.22.0, backend items)

All writes were comments; I edited no issue bodies. Each issue's existing scope text was accurate enough that review notes fit better as a comment. I changed no labels, milestones or assignees, and closed nothing. Before posting, I checked each issue for an existing review comment, so nothing was posted twice. Comment sources are in `scratchpad/issues/<N>.md`.

| Issue | State found | Action | Key content |
|---|---|---|---|
| #621 P1 PII sanitizer corrupts chat JSON | Not fixed | [comment](https://github.com/e2kd7n/ride-optimizer/issues/621#issuecomment-6729744342) | Root cause, two bugs: (1) `chat_tools.py:233` sanitizes *serialized* JSON (`→` digits); (2) `sanitize_address` uses `IGNORECASE` and has no trailing `\b`, so "100 Mile Strava" becomes "[STREET]rava" (also hits logs). Fix: sanitize string leaves before `json.dumps(..., ensure_ascii=False)`, drop the address pass from chat, tighten the regex for logs, add a round-trip test. P1 confirmed; size S. |
| #629 duplicate detection | Not started | [comment](https://github.com/e2kd7n/ride-optimizer/issues/629#issuecomment-6729746435) | Garmin `start_date` is local and Strava's is UTC; key by `(source,id)`; centre-based (non-transitive) grouping; time-window sweep instead of O(n²). Size M. |
| #630 Garmin full history | Not started | [comment](https://github.com/e2kd7n/ride-optimizer/issues/630#issuecomment-6729746915) | Keep the listing metadata-only (per-activity polyline fetch = 8.5k calls); no `garth.configure(timeout)` anywhere; bugs to fix alongside: global garth client (not thread-safe), token files not 0600, Garmin sync depends on Strava auth (H2), job stuck on bad `days` (M3), stale-snapshot merge (M9). Recommend settling #636 first. |
| #631 resumable runner | Not started | [comment](https://github.com/e2kd7n/ride-optimizer/issues/631#issuecomment-6729747504) | No persisted queue exists; `in_progress` before the call plus verify-on-resume; `try_start` pitfall; garth lock shared with sync; persist `paused_until`; explicit resume hook (lazy container). Size L. |
| #632 cache reconcile + regroup | Not started | [comment](https://github.com/e2kd7n/ride-optimizer/issues/632#issuecomment-6729747955) | Regroup handles removals; the tile index does NOT (needs hard invalidate or subtraction); don't reuse the Garmin merge path; back up inside the `update()` lock with a removal cap; cron cache_cleanup hazard (H1). Size M. |
| #589 RWGPS auth | Not started | [comment](https://github.com/e2kd7n/ride-optimizer/issues/589#issuecomment-6729748377) | Don't copy `IntervalsCredStore` verbatim (silent key regeneration, non-atomic write); limiter is effectively global behind Caddy; header-dict tokens evade `sanitize_token`. Size S–M. |
| #590 RWGPS import | Not started | [comment](https://github.com/e2kd7n/ride-optimizer/issues/590#issuecomment-6729748882) | Cached track_points must go through JSONStorage (0600); don't page in request threads; namespace IDs (`rwgps:`) to avoid clashing with route-group IDs used by favourites; validate points. |
| #593 RWGPS publish | Not started | [comment](https://github.com/e2kd7n/ride-optimizer/issues/593#issuecomment-6729749482) | Hand-written, escaped GPX; poll the async task in a background job; guard against double-publish with a persisted `published_route_id`; CSRF-only, so the confirm step is the real safeguard. Recommend leaving it out of 0.22.0 unless #591/#592 ship. |
| #637 yard/übersquadrat (backend) | **Partly done on origin/main** (`f8dd27a`: server-side `find_yard`, returned on every tiles response) | [comment](https://github.com/e2kd7n/ride-optimizer/issues/637#issuecomment-6729763745) | Status table: yard done; übersquadrat, the endpoint, prewarm and persistence missing. Blocker: the tile index doesn't drop deleted activities (M8). Payload bloat from sending the yard on every pan; NumPy DP for übersquadrat. Recommend keeping it open and ticking off the yard half in the body. |

**Note on upstream drift:** my local checkout is at `092a305`. `origin/main` is 6 commits ahead (`0ccde24`, `5d91dec`, `640ccff`, `f8dd27a`, plus docs), all Explore-related. I didn't fetch, per the read-only rule. Through `gh api` I checked that M6 (chunked ORS deadline) and L2 (NaN bbox) still apply upstream. The stale `TestExplorationRouteExcludeParam` tests weren't touched upstream either.
