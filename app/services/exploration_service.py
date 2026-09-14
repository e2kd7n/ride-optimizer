"""
Exploration Service — wraps CoverageTracker for API consumption.

Provides tile coverage, road coverage, route computation via ORS, and cache
management following the existing service patterns (constructor + initialize).
"""

from src.secure_logger import SecureLogger
import json
import math
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config_manager import ConfigManager
from src.coverage_tracker import CoverageTracker
from src.json_storage import secure_chmod

logger = SecureLogger(__name__)

# Maps the frontend surface_preference value to an ORS cycling profile.
_SURFACE_TO_PROFILE = {
    "paved": "cycling-road",
    "unpaved": "cycling-mountain",
    "any": "cycling-regular",
}

# ORS surface-value categories used in extras.surface segments.
_PAVED_SURFACE_VALUES = {0, 1, 2, 3, 4, 5, 6}    # asphalt, concrete, paved, ...
_UNPAVED_SURFACE_VALUES = {7, 8, 9, 10, 11, 12}   # gravel, dirt, grass, ...
# Values outside both sets are treated as unknown.

# #575 — "No motorways" road-filter mapping. The frontend's `exclude` param
# (static/js/explore.js's excludeClasses, named for an old OSRM integration)
# sends road-class tokens like "motorway"/"trunk"; ORS's Directions API has
# no such per-class concept, only a coarse options.avoid_features toggle
# whose closest equivalent is "highways". Any exclude token in this set maps
# onto that toggle; every other token (e.g. "ferry" — already covered by
# ors_client.get_route's own default avoid_features, and harmless here) is
# accepted but ignored rather than rejected, since the frontend may send
# tokens with no backend mapping (unpaved is instead handled via
# surface_preference, and "avoid traffic" has no ORS equivalent at all — see
# #575's design note: don't add a param that silently does nothing).
_MOTORWAY_EXCLUDE_TOKENS = frozenset({"motorway", "trunk"})
# Matches ors_client.get_route()'s own default avoid_features so callers that
# pass no exclude get byte-identical behavior to before #575.
_DEFAULT_AVOID_FEATURES = ("ferries",)

# Cap on retained route-memo entries (#482) — each entry holds a full route
# polyline, so an unbounded dict is a slow memory leak on a long-running Pi.
MAX_ROUTE_CACHE_ENTRIES = 200

# Persists the route memo to disk (#532) so it survives process restarts/
# redeploys instead of cold-starting empty and re-hitting ORS's 2000/day
# free-tier quota for routes that were already computed before the restart.
ROUTE_CACHE_FILENAME = "route_cache.json"


class ExplorationService:

    def __init__(self):
        self.config = ConfigManager.get_instance()
        self._tracker = CoverageTracker(self.config)
        # Route memoization: {(waypoints_key, profile): (result_dict, expires_at)}
        # Guarded by _route_cache_lock (#577) — self._route_semaphore allows
        # up to ors_max_concurrent_calls computations to run at once, so a
        # cache write from one thread (_store_route_cache's eviction scan
        # iterates .items()/.keys()) could otherwise race a write from
        # another, raising "dictionary changed size during iteration". Same
        # crash class as the tile-index race fixed in #558, just a plain
        # lock here rather than that fix's copy-on-write per-zoom locks —
        # this is a single flat dict, not per-zoom state, so there's nothing
        # for copy-on-write to buy beyond what one lock already gives us.
        self._route_cache: Dict[tuple, Tuple[dict, float]] = {}
        self._route_cache_lock = threading.Lock()
        # Bounds concurrent ORS "plot road route" calls (#compute_route).
        # Unbounded concurrency was the other half of the thread-starvation
        # freeze: each call already burns up to ors_max_wait_seconds of a
        # gunicorn thread, so a handful of simultaneous requests could tie up
        # every thread (and ORS's own per-minute quota) at once. A hard mutex
        # (one call at a time) fixed that but also serialized legitimate
        # client-side concurrency — e.g. the short/long distance-target
        # variants a single "plot road route" click fires in parallel — so
        # they just queued behind each other for no benefit. A semaphore sized
        # to leave thread headroom (default 2 of GUNICORN_THREADS=4) keeps the
        # starvation protection while letting that concurrency actually help.
        max_concurrent = int(self.config.get("exploration.ors_max_concurrent_calls", 2))
        self._route_semaphore = threading.Semaphore(max_concurrent)
        # Single-fire guard for start_prewarm() (#560) — a cold process
        # builds nothing at startup, so the first live request pays for a
        # full activity-polyline decode synchronously. See start_prewarm().
        self._prewarm_started = False
        self._prewarm_lock = threading.Lock()
        # Background/debounced disk persistence for the route cache (#573).
        # See _schedule_persist() for why this can't just call
        # _persist_route_cache() synchronously from _store_route_cache().
        self._persist_state_lock = threading.Lock()
        self._persist_thread: Optional[threading.Thread] = None
        self._persist_dirty = False

    def initialize(self):
        self._load_route_cache_from_disk()

    def start_prewarm(self) -> None:
        """Kick off a background pre-warm of both zooms' tile index (#560).

        Nothing builds the tile index at startup otherwise — the first
        live Explore request after a cold process (restart/redeploy) pays
        for a full activity-polyline decode synchronously, which can take
        several seconds on a real activity history. This spawns a daemon
        thread that builds TILE_ZOOM's and SQUADRATINHO_ZOOM's index ahead
        of any real request, so by the time a user opens Explore the index
        is already warm — and any request that beats the warm-up still
        gets #563's stale-serving path instead of a multi-second block.

        Single-fire: a second call is a no-op, so callers (e.g.
        ServiceContainer.get_exploration_service()) don't need to track
        whether they've already triggered this. Zooms are warmed
        sequentially, not in parallel — #558's per-zoom locks mean warming
        one zoom doesn't block reads/writes at another, so there's no
        correctness reason to parallelize, and running sequentially avoids
        two full activity-decode passes competing for the same CPU at
        once. A missing data/cache/activities.json is tolerated (
        CoverageTracker._load_activities() already treats that as "no
        activities yet" rather than an error); any other exception is
        caught and logged so a failure here can't silently kill the daemon
        thread or, worse, the caller.
        """
        with self._prewarm_lock:
            if self._prewarm_started:
                return
            self._prewarm_started = True

        thread = threading.Thread(
            target=self._prewarm_worker, name="exploration-prewarm", daemon=True
        )
        thread.start()

    def restart_prewarm(self) -> None:
        """Reset the single-fire pre-warm guard and kick off a fresh
        pre-warm (#576).

        start_prewarm() is single-fire so ordinary callers (e.g.
        ServiceContainer.get_exploration_service()) don't need to track
        whether they've already triggered it — but that means a manual,
        user-initiated cache invalidation (POST /api/exploration/invalidate)
        would otherwise never get a second pre-warm: the guard was already
        tripped at cold-start, so a plain start_prewarm() call after
        invalidation would just no-op, leaving the *next* live coverage
        request to pay for a synchronous rebuild inline — exactly the
        multi-minute-stall failure mode this epic exists to fix. This resets
        the guard first so the following start_prewarm() actually spawns a
        new pre-warm thread.
        """
        with self._prewarm_lock:
            self._prewarm_started = False
        self.start_prewarm()

    def _prewarm_worker(self) -> None:
        from src.coverage_tracker import TILE_ZOOM, SQUADRATINHO_ZOOM

        for zoom in (TILE_ZOOM, SQUADRATINHO_ZOOM):
            try:
                start = time.monotonic()
                self._tracker._build_or_update_tile_index(zoom)
                logger.info(
                    "Pre-warmed tile index (zoom=%d) in %.2fs", zoom, time.monotonic() - start
                )
            except Exception as exc:
                logger.error("Tile index pre-warm failed for zoom=%d: %s", zoom, exc, exc_info=True)

    def get_tile_coverage(
        self,
        bounds: Tuple[float, float, float, float],
        zoom: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            result = self._tracker.get_tile_coverage(bounds, zoom=zoom)
            return {"status": "success", **result.to_dict()}
        except Exception as exc:
            logger.error("Tile coverage failed: %s", exc, exc_info=True)
            return {"status": "error", "message": str(exc)}

    def get_tile_coverage_all(self, zoom: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = self._tracker.get_tile_coverage_all(zoom=zoom)
            return {"status": "success", **result.to_dict()}
        except Exception as exc:
            logger.error("Full tile coverage failed: %s", exc, exc_info=True)
            return {"status": "error", "message": str(exc)}

    def get_road_coverage(
        self,
        bounds: Tuple[float, float, float, float],
    ) -> Dict[str, Any]:
        return self._tracker.get_road_coverage(bounds)

    def get_roadless_tiles(
        self,
        bounds: Tuple[float, float, float, float],
        zoom: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._tracker.get_roadless_tiles(bounds, zoom=zoom)

    def invalidate_caches(self):
        """Soft-invalidate the coverage cache (in-memory only, see #571).
        This is what the automatic post-activity-sync path in data_bp.py
        calls — it does not touch the on-disk tile index."""
        self._tracker.invalidate_caches()

    def hard_invalidate_caches(self):
        """Fully wipe the coverage cache, including the on-disk tile index.
        Not yet wired to any endpoint — intended for an explicit,
        user-initiated "clear my coverage cache" action (#576)."""
        self._tracker.hard_invalidate_caches()

    def _cache_get(self, cache_key: tuple) -> Optional[dict]:
        """Thread-safe read of a non-expired route cache entry, or None
        (#577) — shared by every cache-hit check in compute_route() /
        _compute_route_via_ors() so none of them read self._route_cache
        directly."""
        with self._route_cache_lock:
            cached = self._route_cache.get(cache_key)
        if cached is None:
            return None
        result, expires_at = cached
        if time.monotonic() < expires_at:
            return result
        return None

    def _store_route_cache(self, cache_key: tuple, result: dict, expires_at: float) -> None:
        """Store a route memo entry, evicting expired entries first and then
        the oldest entries if still over the cap (#482).

        Locked end-to-end (#577): self._route_semaphore allows up to
        ors_max_concurrent_calls computations to run at once, so without a
        lock a write here could race an eviction scan from another thread's
        concurrent _store_route_cache() call — "dictionary changed size
        during iteration".
        """
        with self._route_cache_lock:
            now = time.monotonic()
            expired = [k for k, (_, exp) in self._route_cache.items() if exp <= now]
            for k in expired:
                del self._route_cache[k]

            self._route_cache[cache_key] = (result, expires_at)

            if len(self._route_cache) > MAX_ROUTE_CACHE_ENTRIES:
                # dicts preserve insertion order — oldest entries were inserted first.
                overflow = len(self._route_cache) - MAX_ROUTE_CACHE_ENTRIES
                for k in list(self._route_cache.keys())[:overflow]:
                    del self._route_cache[k]

        self._schedule_persist()

    # Minimum spacing between background persist writes when calls keep
    # arriving faster than the disk can be written to (#573).
    ROUTE_CACHE_PERSIST_DEBOUNCE_S = 2.0

    def _schedule_persist(self) -> None:
        """Persist the route cache to disk on a background thread instead of
        inline (#573).

        _store_route_cache() runs while compute_route() still holds one of
        only ``ors_max_concurrent_calls`` (default 2) semaphore slots — the
        route semaphore isn't released (see its `finally`) until
        _compute_route_via_ors() -> _store_route_cache() returns. A
        synchronous full-cache disk write here (up to MAX_ROUTE_CACHE_ENTRIES
        route polylines re-serialized) happened on every successful route,
        inside that scarce concurrency slot — real I/O contention risk on a
        Pi's SD card, and it delayed releasing the slot for no reason a
        caller waiting on it would care about.

        Debounced + coalesced: a burst of route computations (e.g. the
        several ORS calls one "plot road route" interaction can fire, #565)
        share a single background writer rather than spawning one thread per
        route. If a persist is already running (or about to run) when this
        is called, this just marks the cache dirty so that run picks up the
        latest state before exiting instead of spawning a second thread.
        """
        with self._persist_state_lock:
            self._persist_dirty = True
            if self._persist_thread is not None and self._persist_thread.is_alive():
                return
            self._persist_thread = threading.Thread(
                target=self._persist_worker, name="route-cache-persist", daemon=True
            )
            self._persist_thread.start()

    def _persist_worker(self) -> None:
        """Background loop backing _schedule_persist() — writes the cache to
        disk, then re-writes once more if it went dirty again while writing,
        spaced at least ROUTE_CACHE_PERSIST_DEBOUNCE_S apart."""
        while True:
            with self._persist_state_lock:
                self._persist_dirty = False
            try:
                self._persist_route_cache()
            except Exception as exc:
                logger.error("Background route-cache persist failed: %s", exc, exc_info=True)

            with self._persist_state_lock:
                if not self._persist_dirty:
                    self._persist_thread = None
                    return
            time.sleep(self.ROUTE_CACHE_PERSIST_DEBOUNCE_S)

    def _route_cache_path(self) -> Path:
        return self._tracker.cache_dir / ROUTE_CACHE_FILENAME

    def _load_route_cache_from_disk(self) -> None:
        """Populate self._route_cache from disk (#532), so a fresh process
        doesn't re-hit ORS for routes it already computed before a restart."""
        path = self._route_cache_path()
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Route cache at %s is missing/corrupt — starting fresh: %s", path, exc)
            return

        now_wall = time.time()
        now_mono = time.monotonic()
        loaded = 0
        for entry in data.get("entries", []):
            # expires_at was persisted as a wall-clock timestamp — translate
            # the remaining lifetime onto this process's monotonic clock,
            # since time.monotonic() itself is not meaningful across restarts.
            remaining = entry.get("expires_at", 0) - now_wall
            if remaining <= 0:
                continue
            try:
                # avoid_features (#575) is a newer field — default to the
                # pre-#575 behavior (ferries-only) for entries persisted by
                # an older process, so an in-flight restart doesn't just
                # drop them.
                avoid_features = tuple(entry.get("avoid_features") or _DEFAULT_AVOID_FEATURES)
                cache_key = (
                    tuple((round(lat, 6), round(lon, 6)) for lat, lon in entry["waypoints"]),
                    entry["profile"],
                    avoid_features,
                )
            except (KeyError, TypeError, ValueError):
                continue
            with self._route_cache_lock:
                self._route_cache[cache_key] = (entry["result"], now_mono + remaining)
            loaded += 1
        logger.info("Loaded %d cached ORS route(s) from disk", loaded)

    def _persist_route_cache(self) -> None:
        """Write the current (already-capped) in-memory route cache to disk."""
        path = self._route_cache_path()
        now_mono = time.monotonic()
        now_wall = time.time()
        # Snapshot under the lock (#577) — .items() would otherwise iterate
        # the live dict while a concurrent _store_route_cache() call (up to
        # ors_max_concurrent_calls requests can be writing at once) mutates
        # it, raising "dictionary changed size during iteration". The actual
        # disk write below runs unlocked so it doesn't hold up request
        # threads doing in-memory cache reads/writes for the duration of the
        # (much slower) I/O.
        with self._route_cache_lock:
            snapshot = list(self._route_cache.items())

        entries = []
        for (waypoints, profile, avoid_features), (result, expires_at) in snapshot:
            remaining = expires_at - now_mono
            if remaining <= 0:
                continue
            entries.append({
                "waypoints": [list(pt) for pt in waypoints],
                "profile": profile,
                "avoid_features": list(avoid_features),
                "result": result,
                "expires_at": now_wall + remaining,
            })

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.tmp{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump({"entries": entries}, f)
            secure_chmod(tmp_path)
            os.replace(tmp_path, path)
            secure_chmod(path)
        except OSError as exc:
            logger.warning("Failed to persist route cache: %s", exc)
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def verify_tile_claims(
        self,
        coordinates: List[Tuple[float, float]],
        tiles: List[Dict[str, int]],
    ) -> Dict[str, Any]:
        """Check which of the given tiles a route's actual polyline crosses.

        `tiles` targets are only speculative until the road-following route
        is known (a planned "claim" corner may end up snapped to a road that
        never actually enters the tile). This runs the same exact tile-
        crossing math used to score recorded activities against a planned
        route's real coordinates, so the UI can highlight only tiles that
        are genuinely reachable rather than ones a route merely aimed at.
        """
        by_zoom: Dict[int, set] = {}
        for t in tiles:
            by_zoom.setdefault(t["zoom"], set()).add((t["x"], t["y"]))

        claimed: List[Dict[str, int]] = []
        for zoom, wanted in by_zoom.items():
            crossed = self._tracker.tiles_crossed_by_path(coordinates, zoom)
            for x, y in wanted:
                if (x, y) in crossed:
                    claimed.append({"x": x, "y": y, "zoom": zoom})

        return {"status": "success", "claimed": claimed}

    def find_new_tiles(self, coordinates: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Find every tile a route's real polyline crosses that isn't
        already covered by a past activity, at both squadrat and
        squadratinho granularity.

        Phase-1 route planning only aims at a handful of candidate tiles
        chosen from a straight-line heuristic; Phase-2 distance refinement
        (`refineRoute` in explore.js) can then snap the route to roads or
        insert padding waypoints that carry it well outside that planned
        set (#493 follow-up). Checking the planned list alone under-reports
        new tiles whenever the real route diverges from the plan, so this
        instead derives ground truth straight from the routed coordinates.
        """
        from src.coverage_tracker import TILE_ZOOM, SQUADRATINHO_ZOOM

        new_tiles_by_zoom: List[Dict[str, Any]] = []
        for zoom in (TILE_ZOOM, SQUADRATINHO_ZOOM):
            crossed = self._tracker.tiles_crossed_by_path(coordinates, zoom)
            # Use the all-activities coverage (one cache file per zoom, shared
            # across every route) rather than a per-request bounds query —
            # bounds computed from each route's own coordinates would give
            # get_tile_coverage() a near-unique cache key on every call,
            # writing an unbounded number of never-expiring cache files.
            # Let a coverage lookup failure propagate rather than treating it
            # as "nothing visited" — that would report already-ridden tiles
            # as new. Callers (exploration_verify_tiles route, explore.js)
            # already treat a failed request as "couldn't verify" and leave
            # the Phase-1 preview alone rather than trusting a false claim.
            coverage = self._tracker.get_tile_coverage_all(zoom=zoom)
            visited = {tuple(int(v) for v in key.split(",")) for key in coverage.visited}

            new_tiles = crossed - visited
            if new_tiles:
                new_tiles_by_zoom.append({
                    "zoom": zoom,
                    "tiles": [{"x": x, "y": y} for x, y in sorted(new_tiles)],
                })

        return {"status": "success", "newTilesByZoom": new_tiles_by_zoom}

    # ── ORS road routing ─────────────────────────────────────────

    def compute_route(
        self,
        waypoints: List[Tuple[float, float]],
        surface_preference: str = "any",
        exclude: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute a road-following route via ORS for the given waypoints.

        Args:
            waypoints: List of (lat, lon) pairs.
            surface_preference: ``"any"`` | ``"paved"`` | ``"unpaved"``.
            exclude: Road-class tokens to avoid (#575), e.g. ``["motorway"]``
                — only ``"motorway"``/``"trunk"`` have a real ORS mapping
                (options.avoid_features: ["highways"]); anything else is
                accepted but has no effect. ``None``/empty behaves exactly
                as before #575.

        Returns:
            Dict with ``status``, and on success:
            ``coordinates`` (list of [lat, lon]),
            ``distance_km``, ``duration_min``, ``surface_breakdown``.
        """
        profile = _SURFACE_TO_PROFILE.get(surface_preference, "cycling-regular")
        api_key = self.config.get("ors.api_key", "")
        ttl = int(self.config.get("exploration.route_cache_ttl_seconds", 600))

        exclude_tokens = frozenset(
            t.strip().lower() for t in (exclude or []) if isinstance(t, str) and t.strip()
        )
        avoid_features = (
            _DEFAULT_AVOID_FEATURES + ("highways",)
            if exclude_tokens & _MOTORWAY_EXCLUDE_TOKENS
            else _DEFAULT_AVOID_FEATURES
        )
        # Hard wall-clock budget for this call, across queueing behind any
        # in-flight request (below) AND every retry/fallback ORS attempt.
        # Without this, the unroutable-waypoint retry loop (up to 10
        # iterations) could each wait up to ors_timeout_seconds, tying up a
        # gunicorn thread for minutes on a slow/degraded ORS endpoint — with
        # only 4 threads (gunicorn.conf.py), a couple of concurrent
        # point-to-point requests were enough to starve the whole app for
        # every user, not just the one waiting on ORS.
        max_wait = float(self.config.get("exploration.ors_max_wait_seconds", 40))
        deadline = time.monotonic() + max_wait

        if not api_key:
            return {
                "status": "error",
                "message": "Road routing is not configured (ORS_API_KEY missing)",
            }

        # Memoization key — waypoints as a tuple of pairs + profile + the
        # resolved avoid_features (#575), so a "no motorways" request never
        # returns a cached route computed without that constraint (or
        # vice versa).
        cache_key = (
            tuple((round(lat, 6), round(lon, 6)) for lat, lon in waypoints),
            profile,
            avoid_features,
        )
        cached_result = self._cache_get(cache_key)
        if cached_result is not None:
            logger.debug("ORS cache hit for key %s", cache_key)
            return cached_result

        # Only up to `ors_max_concurrent_calls` computations run at once (see
        # self._route_semaphore) — unbounded concurrent ORS calls were the
        # other half of the thread-starvation freeze. Queue behind whichever
        # requests got there first rather than racing all of them; give up
        # gracefully if the queue wait alone would blow the overall budget.
        wait_start = time.monotonic()
        if not self._route_semaphore.acquire(timeout=max(0.0, deadline - time.monotonic())):
            logger.warning("ORS route semaphore wait timed out after %.2fs", time.monotonic() - wait_start)
            return {
                "status": "error",
                "message": "Road routing is busy with another request — try again shortly",
            }
        sem_wait_s = time.monotonic() - wait_start
        if sem_wait_s > 0.05:
            logger.info("ORS route semaphore wait: %.2fs", sem_wait_s)
        try:
            # Another request may have computed (and cached) this exact
            # route while we were waiting for a slot.
            cached_result = self._cache_get(cache_key)
            if cached_result is not None:
                logger.debug("ORS cache hit for key %s (post-queue)", cache_key)
                return cached_result
            call_start = time.monotonic()
            result = self._compute_route_via_ors(
                waypoints, profile, api_key, ttl, deadline, max_wait, cache_key,
                avoid_features=avoid_features,
            )
            logger.info("ORS route computation took %.2fs (status=%s)", time.monotonic() - call_start, result.get("status"))
            return result
        finally:
            self._route_semaphore.release()

    def _compute_route_via_ors(
        self,
        waypoints: List[Tuple[float, float]],
        profile: str,
        api_key: str,
        ttl: int,
        deadline: float,
        max_wait: float,
        cache_key: tuple,
        avoid_features: tuple = _DEFAULT_AVOID_FEATURES,
    ) -> Dict[str, Any]:
        """Run the actual ORS call(s) for compute_route, holding self._route_lock."""
        from src import ors_client

        timeout = int(self.config.get("exploration.ors_timeout_seconds", 15))

        def _budget_timeout() -> float:
            """Per-call timeout capped to whatever's left of the overall budget."""
            return max(0.0, min(timeout, deadline - time.monotonic()))

        # ORS expects [lon, lat] pairs.
        ors_coords = [[lon, lat] for lat, lon in waypoints]
        # #578: this first call used the fixed per-call `timeout` instead of
        # _budget_timeout() — every retry call below already used the
        # budget-capped version, so a request that spent most of its
        # ors_max_wait_seconds budget queueing behind the semaphore could
        # still let this first call run for a full fresh `timeout`,
        # blowing past the overall wall-clock budget compute_route() exists
        # to enforce.
        raw = ors_client.get_route(
            ors_coords, profile, avoid_features=avoid_features, api_key=api_key, timeout=_budget_timeout(),
        )

        # Preferred profile not enabled on this account — fall back to cycling-regular.
        if (
            raw is not None
            and raw.get("_ors_profile_unavailable")
            and profile != "cycling-regular"
            and time.monotonic() < deadline
        ):
            logger.info("Profile %s unavailable, falling back to cycling-regular", profile)
            profile = "cycling-regular"
            raw = ors_client.get_route(
                ors_coords, profile, avoid_features=avoid_features, api_key=api_key, timeout=_budget_timeout(),
            )

        # Unroutable waypoints: drop every interior bad waypoint and retry.
        # "Interior" = not the first (start) or last (end) coordinate.
        # We identify bad waypoints by their [lon, lat] coordinates, not by
        # index, because ORS index numbering can vary across versions.
        # Retry until no interior waypoints remain to drop (guard against loops).
        _drop_attempts = 0
        _timed_out = False
        while raw is not None and raw.get("_ors_unroutable"):
            if time.monotonic() >= deadline:
                _timed_out = True
                break
            bad_coords = {(round(lon, 4), round(lat, 4)) for lon, lat in raw["_ors_unroutable"]}
            # Only drop interior points (preserve first and last).
            interior = ors_coords[1:-1]
            pruned = [c for c in interior if (round(c[0], 4), round(c[1], 4)) not in bad_coords]
            if len(pruned) == len(interior):
                # None of the bad coords matched an interior waypoint — can't fix.
                break
            ors_coords = [ors_coords[0]] + pruned + [ors_coords[-1]]
            logger.info(
                "Dropped %d unroutable interior waypoint(s); retrying with %d coords",
                len(interior) - len(pruned), len(ors_coords),
            )
            _drop_attempts += 1
            if len(ors_coords) < 2 or _drop_attempts > 10:
                break
            # Re-check cache for the pruned list. avoid_features carries over
            # unchanged — dropping an unroutable waypoint doesn't change what
            # road classes the caller asked to avoid (#575).
            cache_key = (
                tuple((round(c[1], 6), round(c[0], 6)) for c in ors_coords),
                profile,
                avoid_features,
            )
            cached_result = self._cache_get(cache_key)
            if cached_result is not None:
                return cached_result
            raw = ors_client.get_route(
                ors_coords, profile, avoid_features=avoid_features, api_key=api_key, timeout=_budget_timeout(),
            )

        if _timed_out:
            logger.warning("ORS route computation exceeded %.0fs budget; giving up gracefully", max_wait)
            return {
                "status": "error",
                "message": "Road routing is taking too long — try again, or a shorter/simpler route",
            }
        if raw is None:
            return {"status": "error", "message": "Road routing request failed"}
        if raw.get("_ors_rate_limited"):
            return {
                "status": "error",
                "message": "Road routing rate limit reached — try again shortly",
            }
        if raw.get("_ors_unroutable") is not None:
            return {"status": "error", "message": "Road routing failed: no routable path near waypoints"}

        try:
            result = self._parse_ors_response(raw)
        except Exception as exc:
            logger.error("Failed to parse ORS response: %s", exc, exc_info=True)
            return {"status": "error", "message": "Unexpected ORS response format"}

        self._store_route_cache(cache_key, result, time.monotonic() + ttl)
        return result

    # ── helpers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_ors_response(raw: dict) -> Dict[str, Any]:
        """Extract coordinates, distance, duration, and surface breakdown."""
        feature = raw["features"][0]
        props = feature["properties"]
        summary = props["summary"]
        geom = feature["geometry"]

        # Coordinates come back as [lon, lat] from ORS; flip to [lat, lon].
        coordinates = [[lat, lon] for lon, lat in geom["coordinates"]]

        distance_km = round(summary["distance"] / 1000, 2)
        duration_min = round(summary["duration"] / 60, 1)

        surface_breakdown = ExplorationService._reduce_surface_extras(props.get("extras", {}))
        is_out_and_back = ExplorationService._is_out_and_back(coordinates)

        return {
            "status": "success",
            "coordinates": coordinates,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "surface_breakdown": surface_breakdown,
            "is_out_and_back": is_out_and_back,
        }

    # Fraction of return-leg points that must fall within OUT_AND_BACK_RADIUS_M
    # of some outbound-leg point for the route to be flagged as out-and-back (#452).
    OUT_AND_BACK_OVERLAP_THRESHOLD = 0.7
    OUT_AND_BACK_RADIUS_M = 150

    @staticmethod
    def _is_out_and_back(coordinates: List[List[float]]) -> bool:
        """Detect a route whose return leg substantially retraces its outbound leg.

        Splits the polyline in half and checks what fraction of return-leg
        points land within ~150m of some outbound-leg point. Real road
        geometry rarely retraces exactly, so this is a proximity match against
        the whole outbound half rather than a point-by-point mirror check —
        that's what lets a genuine loop (distinct corridors both ways) read as
        low-overlap even if the two halves end up near each other briefly.
        """
        if len(coordinates) < 4:
            return False

        mid = len(coordinates) // 2
        outbound, return_leg = coordinates[:mid], coordinates[mid:]
        if not outbound or not return_leg:
            return False

        # Coarse degrees-per-meter conversion is fine at the ~150m scale this
        # threshold operates at — no need for full haversine per point pair.
        lat_ref = coordinates[0][0]
        deg_per_m_lat = 1 / 111_320
        deg_per_m_lon = 1 / (111_320 * max(0.01, abs(math.cos(math.radians(lat_ref)))))
        radius_deg_lat = ExplorationService.OUT_AND_BACK_RADIUS_M * deg_per_m_lat
        radius_deg_lon = ExplorationService.OUT_AND_BACK_RADIUS_M * deg_per_m_lon

        near_count = 0
        for r_lat, r_lon in return_leg:
            for o_lat, o_lon in outbound:
                if abs(r_lat - o_lat) <= radius_deg_lat and abs(r_lon - o_lon) <= radius_deg_lon:
                    near_count += 1
                    break

        return (near_count / len(return_leg)) >= ExplorationService.OUT_AND_BACK_OVERLAP_THRESHOLD

    @staticmethod
    def _reduce_surface_extras(extras: dict) -> Dict[str, Any]:
        """Reduce ORS extras.surface segment array into paved/unpaved/unknown percentages."""
        surface_values = (extras.get("surface") or {}).get("values", [])

        paved_m = 0.0
        unpaved_m = 0.0
        unknown_m = 0.0

        for segment in surface_values:
            # Each entry: [from_idx, to_idx, surface_value]
            if len(segment) < 3:
                continue
            from_idx, to_idx, value = segment[:3]
            # Distance per segment isn't provided in ORS v2, but the coordinate
            # index span is a good proxy for how much of the route it covers.
            span = to_idx - from_idx
            if value in _PAVED_SURFACE_VALUES:
                paved_m += span
            elif value in _UNPAVED_SURFACE_VALUES:
                unpaved_m += span
            else:
                unknown_m += span

        total_span = paved_m + unpaved_m + unknown_m
        if total_span == 0:
            return {"paved_pct": 0, "unpaved_pct": 0, "unknown_pct": 100}

        return {
            "paved_pct": round(paved_m / total_span * 100),
            "unpaved_pct": round(unpaved_m / total_span * 100),
            "unknown_pct": round(unknown_m / total_span * 100),
        }
