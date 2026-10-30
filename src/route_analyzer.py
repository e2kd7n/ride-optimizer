"""
Route analysis module.

Extracts, groups, and analyzes route variants between home and work.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

from .secure_logger import SecureLogger
import json
import hashlib
import os
import threading
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

import numpy as np
from geopy.distance import geodesic
import polyline
from tqdm import tqdm

from .data_fetcher import Activity
from .location_finder import Location
from .route_namer import RouteNamer, check_rate_limit_file
from .json_storage import secure_chmod
from .route_comparison import (
    PreparedTrack, passes_commute_prefilter, possible_match_pairs,
    prepared_deviation_metrics, track_deviation_metrics, match_score, route_geometry,
)

logger = SecureLogger(__name__)

# Bump SIMILARITY_CACHE_VERSION whenever the pairwise score's math or the route
# hash changes, and GROUPS_CACHE_VERSION whenever grouping logic changes, so stale
# on-disk results from the old code are discarded instead of silently reused (#612).
SIMILARITY_CACHE_VERSION = 4
GROUPS_CACHE_VERSION = 4

DIRECTIONS = ('home_to_work', 'work_to_home')
DIRECTION_LABELS = {'home_to_work': 'home→work', 'work_to_home': 'work→home'}
PLUS_ROUTE_FACTOR = 1.15


def is_labelled_plus(activity_name: Optional[str]) -> bool:
    """Whether the rider marked a commute as extended ("Ride to work +")."""
    return '+' in (activity_name or '')


# Below this many uncached comparisons a process pool costs more than it saves.
MIN_PARALLEL_PAIRS = 200
MIN_PAIRS_PER_CHUNK = 25
# Commute direction needs both ends within this of home/work; a ride with both
# ends within NEAR_MISS_M of them (but not that close) is counted as unclassified.
ENDPOINT_RADIUS_M = 500
NEAR_MISS_M = 2000

# Per-process state for _pair_metrics_worker, set by _init_pair_worker: each
# direction's route coordinates and lat0, and the tracks prepared so far.
_worker_coords: Dict[str, list] = {}
_worker_lat0s: Dict[str, float] = {}
_worker_tracks: Dict[Tuple[str, int], PreparedTrack] = {}


def _init_pair_worker(coords_by_direction, lat0_by_direction):
    global _worker_coords, _worker_lat0s, _worker_tracks
    _worker_coords, _worker_lat0s, _worker_tracks = coords_by_direction, lat0_by_direction, {}


def _worker_track(direction: str, index: int) -> PreparedTrack:
    key = (direction, index)
    if key not in _worker_tracks:
        _worker_tracks[key] = PreparedTrack(_worker_coords[direction][index],
                                            _worker_lat0s[direction])
    return _worker_tracks[key]


def _pair_metrics_worker(chunk):
    """
    Module-level worker for ProcessPoolExecutor (must be picklable).

    chunk: (direction, [(i, j), ...]) indices into that direction's routes.
    Returns (direction, [(i, j, [p95_m, coverage] or None), ...]). None means
    the comparison failed; the caller logs it and treats it as no match.
    """
    direction, pairs = chunk
    results = []
    for i, j in pairs:
        try:
            metrics = list(prepared_deviation_metrics(_worker_track(direction, i),
                                                      _worker_track(direction, j)))
        except Exception:
            metrics = None
        results.append((i, j, metrics))
    return direction, results


@dataclass
class Route:
    """Represents a single route."""
    activity_id: int
    direction: str  # "home_to_work" or "work_to_home"
    coordinates: List[Tuple[float, float]]
    distance: float  # meters
    duration: int  # seconds
    elevation_gain: float  # meters
    timestamp: str  # ISO format
    average_speed: float  # m/s
    activity_name: str = ""  # Name of the activity from Strava
    is_plus_route: bool = False  # True if distance is >25% above median
    bbox: Optional[Tuple[float, float, float, float]] = None  # (min_lat, min_lon, max_lat, max_lon)
    centroid: Optional[Tuple[float, float]] = None  # (lat, lon)
    path_length_m: Optional[float] = None  # polyline length, cos(lat)-corrected

    def compute_geometry(self):
        """Populate bbox, centroid, and path_length_m from coordinates."""
        if not self.coordinates:
            return
        self.bbox, self.centroid, self.path_length_m = route_geometry(self.coordinates)


@dataclass
class RouteGroup:
    """Represents a group of similar routes."""
    id: str
    direction: str
    routes: List[Route]
    representative_route: Route
    frequency: int
    name: Optional[str] = None
    is_plus_route: bool = False  # True if this is a "plus route" group
    difficulty: str = 'Easy'  # Difficulty rating: 'Easy', 'Moderate', 'Hard', or 'Very Hard'
    
    
@dataclass
class RouteMetrics:
    """Metrics for a route group."""
    avg_duration: float  # seconds
    std_duration: float
    avg_distance: float  # meters
    avg_speed: float  # m/s
    avg_elevation: float  # meters
    consistency_score: float  # 0-1, higher is more consistent
    usage_frequency: int


class RouteAnalyzer:
    """Analyzes and groups routes between home and work."""
    
    def __init__(self, activities: List[Activity], home: Location,
                 work: Location, config, n_workers=2, force_reanalysis=False,
                 progress_callback=None, stop_check=None, cache_dir=None,
                 interactive=False, enable_geocoding=None):
        """
        Initialize route analyzer.

        Args:
            activities: List of Activity objects
            home: Home location
            work: Work location
            cache_dir: Directory for cache files (default: 'cache'). Overridable
                so tests with force_reanalysis=True don't unlink the real cache.
            config: Configuration object
            n_workers: Number of parallel workers for route grouping (1-8)
            force_reanalysis: If True, regroup every route instead of reusing the
                cached groups (cached pair metrics and group IDs are still used)
            progress_callback: Optional callable(routes_done, routes_total, direction, ...)
            stop_check: Optional callable() → bool; returns True when caller wants early exit
            interactive: If True, background geocoding prompts for approval on stdin and
                opens a Terminal.app window (macOS) to show progress. Only appropriate for
                the CLI entry point (main.py) running attached to a real terminal — the web
                service always constructs with the default False so a server-side analysis
                run never pops up desktop windows or blocks on stdin.
            enable_geocoding: Overrides the `route_analysis.enable_geocoding` config value
                for this instance when not None. Used to force-disable geocoding for
                throwaway analyzer instances (e.g. the preview pass) regardless of config.
        """
        self.activities = activities
        self.home = home
        self.work = work
        self.config = config
        self.n_workers = max(1, min(8, n_workers))  # Clamp between 1 and 8
        self.progress_callback = progress_callback
        self.stop_check = stop_check
        self.interactive = interactive
        self._enable_geocoding_override = enable_geocoding
        # Match rule (#613): see route_comparison.track_deviation_metrics.
        self.max_p95_deviation_m = float(config.get('route_analysis.max_p95_deviation_m', 100.0))
        self.min_coverage = float(config.get('route_analysis.min_coverage', 0.85))
        self.route_namer = RouteNamer(config)
        self.force_reanalysis = force_reanalysis
        
        # Initialize caches
        self.cache_dir = Path(cache_dir) if cache_dir is not None else Path('cache')
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / 'route_similarity_cache.json'
        self.similarity_cache = self._load_similarity_cache()
        
        # Route grouping cache
        self.groups_cache_file = self.cache_dir / 'route_groups_cache.json'
        
        # Loaded even under force_reanalysis, which regroups instead of reusing
        # it: the regroup still takes its group IDs and names from it (#614).
        self.groups_cache = self._load_groups_cache()
        
        # Background geocoding thread and subprocess
        self._geocoding_thread = None
        self._geocoding_lock = threading.Lock()
        self._terminal_process = None

        # Set when stop_check ends a grouping pass early; a partial result must
        # not be saved as the groups cache (#612).
        self._stopped_early = False

        # Rides between home and work that extract_routes couldn't classify (C10).
        self.unclassified_count = 0

    def _load_similarity_cache(self) -> Dict[str, List[float]]:
        """Load similarity cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                if cache.get('version') != SIMILARITY_CACHE_VERSION:
                    # Includes the pre-#612 unversioned format: a flat {key: score} dict.
                    logger.info("Discarding similarity cache from an older scoring version")
                    return {}
                metrics = cache.get('metrics', {})
                logger.info(f"Loaded {len(metrics)} cached similarity calculations")
                return metrics
            except Exception as e:
                logger.warning(f"Failed to load similarity cache: {e}")
                return {}
        return {}

    def _save_similarity_cache(self):
        """Save similarity cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({'version': SIMILARITY_CACHE_VERSION, 'metrics': self.similarity_cache}, f)
            secure_chmod(self.cache_file)
            logger.info(f"Saved {len(self.similarity_cache)} similarity calculations to cache")
        except Exception as e:
            logger.warning(f"Failed to save similarity cache: {e}")
    
    def _load_groups_cache(self) -> Dict[str, Any]:
        """Load route groups cache from disk."""
        if self.groups_cache_file.exists():
            try:
                with open(self.groups_cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded route groups cache (key: {cache.get('cache_key', 'unknown')[:8]}...)")
                return cache
            except Exception as e:
                logger.warning(f"Failed to load groups cache: {e}")
                return {}
        return {}

    def _groups_cache_config(self) -> Dict[str, Any]:
        """Everything besides the activity set that the cached groups depend on.

        A cached grouping is only reused when this matches exactly, so changing
        the threshold or the matching code forces a regroup (#612).
        """
        return {
            'groups_cache_version': GROUPS_CACHE_VERSION,
            'similarity_cache_version': SIMILARITY_CACHE_VERSION,
            'max_p95_deviation_m': self.max_p95_deviation_m,
            'min_coverage': self.min_coverage,
        }

    def _groups_cache_reusable(self, routes: List[Route]) -> bool:
        """True if the cached groups were built under the current config, and every
        cached activity that's still present still has the same direction (a
        home/work change can flip directions without changing the activity set)."""
        if self.groups_cache.get('config') != self._groups_cache_config():
            return False
        cached_directions = self.groups_cache.get('directions', {})
        return all(cached_directions.get(str(r.activity_id), r.direction) == r.direction
                   for r in routes)

    def _save_groups_cache_with_ids(self, activity_ids: List[int], groups: List[RouteGroup]):
        """Save route groups cache to disk with activity ID tracking."""
        try:
            # Serialize groups to JSON-compatible format
            serialized_groups = []
            for group in groups:
                serialized_group = {
                    'id': group.id,
                    'direction': group.direction,
                    'frequency': group.frequency,
                    'name': group.name,
                    'is_plus_route': group.is_plus_route,
                    'representative_route': {
                        'activity_id': group.representative_route.activity_id,
                        'direction': group.representative_route.direction,
                        'coordinates': group.representative_route.coordinates,
                        'distance': group.representative_route.distance,
                        'duration': group.representative_route.duration,
                        'elevation_gain': group.representative_route.elevation_gain,
                        'timestamp': group.representative_route.timestamp,
                        'average_speed': group.representative_route.average_speed,
                        'is_plus_route': group.representative_route.is_plus_route,
                        'bbox': group.representative_route.bbox,
                        'centroid': group.representative_route.centroid,
                        'path_length_m': group.representative_route.path_length_m,
                    },
                    'routes': [
                        {
                            'activity_id': r.activity_id,
                            'direction': r.direction,
                            'coordinates': r.coordinates,
                            'distance': r.distance,
                            'duration': r.duration,
                            'elevation_gain': r.elevation_gain,
                            'timestamp': r.timestamp,
                            'average_speed': r.average_speed,
                            'is_plus_route': r.is_plus_route,
                            'bbox': r.bbox,
                            'centroid': r.centroid,
                            'path_length_m': r.path_length_m,
                        }
                        for r in group.routes
                    ]
                }
                serialized_groups.append(serialized_group)
            
            cache_data = {
                'activity_ids': activity_ids,
                'groups': serialized_groups,
                'config': self._groups_cache_config(),
                'directions': {str(r.activity_id): r.direction
                               for group in groups for r in group.routes},
                'timestamp': str(np.datetime64('now'))
            }
            
            with open(self.groups_cache_file, 'w') as f:
                json.dump(cache_data, f)
            secure_chmod(self.groups_cache_file)
            logger.info(f"Saved {len(groups)} route groups to cache ({len(activity_ids)} activities)")
        except Exception as e:
            logger.warning(f"Failed to save groups cache: {e}")
    
    @staticmethod
    def _deserialize_route(data: Dict) -> Route:
        """Deserialize a single Route from JSON, recomputing geometry if absent."""
        route = Route(
            activity_id=data['activity_id'],
            direction=data['direction'],
            coordinates=[(lat, lon) for lat, lon in data['coordinates']],
            distance=data['distance'],
            duration=data['duration'],
            elevation_gain=data['elevation_gain'],
            timestamp=data['timestamp'],
            average_speed=data['average_speed'],
            is_plus_route=data.get('is_plus_route', False),
            bbox=tuple(data['bbox']) if data.get('bbox') else None,
            centroid=tuple(data['centroid']) if data.get('centroid') else None,
            path_length_m=data.get('path_length_m'),
        )
        if route.bbox is None or route.path_length_m is None:
            route.compute_geometry()
        return route

    def _deserialize_groups(self, serialized_groups: List[Dict]) -> List[RouteGroup]:
        """Deserialize route groups from JSON format."""
        groups = []
        for sg in serialized_groups:
            representative = self._deserialize_route(sg['representative_route'])
            routes = [self._deserialize_route(r_data) for r_data in sg['routes']]
            
            # Create route group
            group = RouteGroup(
                id=sg['id'],
                direction=sg['direction'],
                routes=routes,
                representative_route=representative,
                frequency=sg['frequency'],
                name=sg['name'],
                is_plus_route=sg['is_plus_route']
            )
            groups.append(group)
        
        return groups
    
    def _get_route_hash(self, route: Route) -> str:
        """
        Generate a unique hash for a route based on its coordinates.
        
        Args:
            route: Route object
            
        Returns:
            Hash string
        """
        # Hash the full geometry: a 5-point sample let two different tracks that
        # agree at those points share cached scores (#612).
        coords = np.asarray(route.coordinates, dtype=np.float64)
        return hashlib.sha256(coords.tobytes()).hexdigest()[:16]
    
    def _get_cache_key(self, route1: Route, route2: Route) -> str:
        """
        Generate cache key for a route pair.
        
        Args:
            route1: First route
            route2: Second route
            
        Returns:
            Cache key string
        """
        return self._pair_key(self._get_route_hash(route1), self._get_route_hash(route2))

    @staticmethod
    def _pair_key(hash1: str, hash2: str) -> str:
        # Sort hashes to ensure same key regardless of order
        return f"{min(hash1, hash2)}_{max(hash1, hash2)}"

    @staticmethod
    def _passes_geometric_filter(route1: 'Route', route2: 'Route',
                                 length_ratio_max: float = 2.0,
                                 centroid_max_m: float = 2000.0,
                                 bbox_overlap_min: float = 0.3) -> bool:
        """Fast geometric pre-filter — returns False if routes are obviously dissimilar.

        Delegates to the shared route_comparison.passes_commute_prefilter, using
        Route's precomputed bbox/centroid/path_length_m (see
        Route.compute_geometry) rather than recomputing geometry from full
        coordinate arrays on every candidate pair.
        """
        return passes_commute_prefilter(
            route1.bbox, route1.centroid, route1.path_length_m,
            route2.bbox, route2.centroid, route2.path_length_m,
            length_ratio_max=length_ratio_max,
            centroid_max_m=centroid_max_m,
            bbox_overlap_min=bbox_overlap_min,
        )
    def extract_routes(self, direction: str = 'both') -> List[Route]:
        """
        Extract routes between home and work.
        
        Args:
            direction: 'home_to_work', 'work_to_home', or 'both'
            
        Returns:
            List of Route objects
        """
        routes = []
        self.unclassified_count = 0

        for activity in self.activities:
            if not activity.polyline:
                continue

            # Determine route direction
            route_direction, near_miss = self._classify_direction(activity)

            if route_direction is None:
                self.unclassified_count += near_miss
                continue
            
            if direction != 'both' and route_direction != direction:
                continue
            
            # Decode polyline
            try:
                coordinates = polyline.decode(activity.polyline)
            except Exception as e:
                logger.warning(f"Failed to decode polyline for activity {activity.id}: {e}")
                continue
            
            # Create route object
            route = Route(
                activity_id=activity.id,
                direction=route_direction,
                coordinates=coordinates,
                distance=activity.distance,
                duration=activity.moving_time,
                elevation_gain=activity.total_elevation_gain,
                timestamp=activity.start_date,
                average_speed=activity.average_speed,
                activity_name=activity.name
            )
            route.compute_geometry()

            routes.append(route)
        
        logger.info(f"Extracted {len(routes)} routes (direction: {direction})")
        if self.unclassified_count:
            logger.info(f"{self.unclassified_count} rides run between home and work but "
                        f"don't start and end within {ENDPOINT_RADIUS_M} m of them, so "
                        f"they aren't grouped as commutes (unclassified)")
        
        return routes
    
    def _determine_direction(self, activity: Activity) -> str:
        """
        Determine if route is home-to-work or work-to-home.
        
        Args:
            activity: Activity object
            
        Returns:
            'home_to_work', 'work_to_home', or None
        """
        return self._classify_direction(activity)[0]

    def _classify_direction(self, activity: Activity) -> Tuple[Optional[str], bool]:
        """(direction or None, near_miss). near_miss is True for a ride that isn't
        classified but has both ends within NEAR_MISS_M of home and work — likely
        a commute trimmed by a privacy zone or ended at a mid-route stop (C10)."""
        if not activity.start_latlng or not activity.end_latlng:
            return None, False

        home, work = (self.home.lat, self.home.lon), (self.work.lat, self.work.lon)
        start_to_home = geodesic(activity.start_latlng, home).meters
        start_to_work = geodesic(activity.start_latlng, work).meters
        end_to_home = geodesic(activity.end_latlng, home).meters
        end_to_work = geodesic(activity.end_latlng, work).meters

        if start_to_home < ENDPOINT_RADIUS_M and end_to_work < ENDPOINT_RADIUS_M:
            return 'home_to_work', False
        if start_to_work < ENDPOINT_RADIUS_M and end_to_home < ENDPOINT_RADIUS_M:
            return 'work_to_home', False
        near_miss = (max(start_to_home, end_to_work) < NEAR_MISS_M
                     or max(start_to_work, end_to_home) < NEAR_MISS_M)
        return None, near_miss
    
    def calculate_route_similarity(self, route1: Route, route2: Route) -> float:
        """
        Match score for two routes: >= 1.0 means they are the same route (see
        route_comparison.match_score), and higher means a closer match.

        The underlying (p95 deviation, coverage) metrics are cached rather than
        the score, so a threshold change re-decides without recomputing. A failed
        comparison is logged and scored 0.0 (not cached) rather than silently
        switching to a different metric.
        """
        cache_key = self._get_cache_key(route1, route2)
        metrics = self.similarity_cache.get(cache_key)
        if metrics is None:
            try:
                metrics = list(track_deviation_metrics(route1.coordinates, route2.coordinates))
            except Exception as e:
                logger.warning(f"Route comparison failed, treating as no match: {e}")
                return 0.0
            self.similarity_cache[cache_key] = metrics
        return self._score(metrics)

    def _score(self, metrics: List[float]) -> float:
        p95_m, coverage = metrics
        return match_score(p95_m, coverage, self.max_p95_deviation_m, self.min_coverage)

    @staticmethod
    def _is_match(score: float) -> bool:
        return score >= 1.0

    def group_similar_routes(self, routes: List[Route] = None) -> List[RouteGroup]:
        """
        Group routes that are the same route (see route_comparison.match_score).

        Returns the cached groups when the ride set and config are unchanged.
        Otherwise every ride is regrouped: the grouping is a pure function of
        the pairwise metrics, so an incremental run (new rides, cached metrics
        for the old pairs) gives exactly the groups a full recompute would
        (#614). Group IDs and names carry over from the previous groups.

        Args:
            routes: List of routes to group (if None, extracts all routes)

        Returns:
            List of RouteGroup objects
        """
        if routes is None:
            routes = self.extract_routes()

        if not routes:
            logger.warning("No routes to group")
            return []

        self._stopped_early = False

        # Check for cached groups
        if not self.force_reanalysis and self.groups_cache:
            cached_activity_ids = set(self.groups_cache.get('activity_ids', []))
            current_activity_ids = set(r.activity_id for r in routes)
            new_activity_ids = current_activity_ids - cached_activity_ids
            removed_activity_ids = cached_activity_ids - current_activity_ids

            if not self._groups_cache_reusable(routes):
                # Threshold, matching code or ride directions changed since the
                # cache was built — reusing it would keep the old grouping (#612).
                logger.info("Regrouping: route grouping configuration changed")
                tqdm.write("   🔄 Regrouping: configuration changed")

            elif not new_activity_ids and not removed_activity_ids:
                # Perfect cache hit - no changes
                tqdm.write("   💾 Using cached route groups (instant!)")
                cached_groups = self._deserialize_groups(self.groups_cache['groups'])
                logger.info(f"Loaded {len(cached_groups)} route groups from cache")
                # Cheap, and keeps the flags current if the PLUS rule changed.
                return self._mark_plus_routes(cached_groups)

            elif removed_activity_ids:
                removed_pct = (len(removed_activity_ids) / len(cached_activity_ids) * 100
                               if cached_activity_ids else 0)
                msg = (f"Regrouping: {len(removed_activity_ids)} of "
                       f"{len(cached_activity_ids)} previously-cached activities are "
                       f"no longer present ({removed_pct:.0f}%) — route groups cache "
                       f"will be rebuilt from the smaller activity set.")
                if removed_pct >= 10:
                    logger.warning(
                        msg + " This is a large drop — verify activities.json wasn't "
                        "unexpectedly truncated (e.g. by a failed merge) rather than "
                        "genuinely pruned before trusting the rebuilt cache."
                    )
                else:
                    logger.info(msg)
                tqdm.write(f"   🔄 Regrouping: {len(removed_activity_ids)} routes removed")

            else:
                tqdm.write(f"   ⚡ Incremental analysis: {len(new_activity_ids)} new routes "
                           f"(earlier comparisons come from the cache)")

        tqdm.write(f"   🔄 Grouping {len(routes)} routes ({self.n_workers} workers)")
        groups = self._regroup(routes)

        if self._stopped_early:
            # Partial result: saving it would record the rides never reached as
            # already grouped, and the next run's cache hit would drop them for
            # good (#612). The similarity cache is still valid and keeps the
            # rerun cheap.
            self._save_similarity_cache()
            return groups

        tqdm.write(f"   Total: {len(groups)} groups")
        logger.info(f"Created {len(groups)} route groups from {len(routes)} routes")

        # Save to cache immediately with temporary names
        # (geocoding will happen in background and update cache when complete)
        activity_ids = [r.activity_id for r in routes]
        self._save_groups_cache_with_ids(activity_ids, groups)

        # Start background geocoding (non-blocking)
        # This will update the cache and regenerate the report when complete
        if self._geocoding_enabled():
            self._start_background_geocoding(groups, auto_approve=not self.interactive)

        # Save similarity cache after grouping
        self._save_similarity_cache()

        return groups

    def _regroup(self, routes: List[Route]) -> List[RouteGroup]:
        """Group every route from scratch, per direction, reusing cached metrics.

        1. Each route is projected and resampled once (PreparedTrack).
        2. possible_match_pairs rules out, exactly and cheaply, the pairs that
           can't match; only the rest need the slow exact metric.
        3. Uncached metrics are computed (in parallel when worthwhile).
        4. _cluster_by_centres groups the routes from the match graph.

        Routes are sorted by activity ID first, so the result doesn't depend on
        input order. Returns [] if stop_check ends the run early.
        """
        by_direction = {}
        for direction in DIRECTIONS:
            rs = sorted((r for r in routes if r.direction == direction),
                        key=lambda r: r.activity_id)
            if rs:
                by_direction[direction] = rs

        lat0s, tracks, hashes, candidates = {}, {}, {}, {}
        for direction, rs in by_direction.items():
            lat0s[direction] = self._shared_lat0(rs)
            tracks[direction] = [self._prepare_track(r, lat0s[direction]) for r in rs]
            hashes[direction] = [self._get_route_hash(r) for r in rs]
            valid = [k for k, t in enumerate(tracks[direction]) if t is not None]
            pairs = possible_match_pairs([tracks[direction][k] for k in valid],
                                         self.max_p95_deviation_m, self.min_coverage)
            candidates[direction] = [(valid[i], valid[j]) for i, j in pairs]

        todo = [(direction, i, j)
                for direction, pairs in candidates.items() for i, j in pairs
                if self._pair_key(hashes[direction][i], hashes[direction][j])
                not in self.similarity_cache]
        n_candidates = sum(len(p) for p in candidates.values())
        tqdm.write(f"   → {n_candidates} possible matches to check, "
                   f"{n_candidates - len(todo)} already cached")

        if not self._compute_pair_metrics(todo, by_direction, lat0s, tracks, hashes):
            self._stopped_early = True
            return []

        groups = []
        for direction, rs in by_direction.items():
            n = len(rs)
            scores = np.zeros((n, n))
            for i, j in candidates[direction]:
                metrics = self.similarity_cache.get(
                    self._pair_key(hashes[direction][i], hashes[direction][j]))
                if metrics is not None:  # None: the comparison failed, so no match
                    scores[i, j] = scores[j, i] = self._score(metrics)
            direction_groups = [
                RouteGroup(id='', direction=direction, routes=[rs[k] for k in members],
                           representative_route=rs[centre], frequency=len(members))
                for centre, members in self._cluster_by_centres(scores)
            ]
            tqdm.write(f"   ✓ {DIRECTION_LABELS[direction]}: {n} routes → "
                       f"{len(direction_groups)} groups")
            groups.extend(direction_groups)

        self._assign_group_ids(groups)
        self._mark_plus_routes(groups)
        groups.sort(key=lambda g: (DIRECTIONS.index(g.direction), -g.frequency, g.id))
        return groups

    @staticmethod
    def _shared_lat0(routes: List[Route]) -> float:
        """Projection latitude shared by one direction's routes: the median
        centroid latitude, rounded to 0.1° so that adding rides almost never
        moves it. Any lat0 within a few tenths of a degree changes deviations
        by well under a metre."""
        lats = [r.centroid[0] for r in routes if r.centroid is not None]
        return round(float(np.median(lats)), 1) if lats else 0.0

    @staticmethod
    def _prepare_track(route: Route, lat0: float) -> Optional[PreparedTrack]:
        try:
            return PreparedTrack(route.coordinates, lat0)
        except Exception as e:
            logger.warning(f"Route activity_id={route.activity_id} has no usable track, "
                           f"so it can't match another route: {e}")
            return None

    def _compute_pair_metrics(self, todo, by_direction, lat0s, tracks, hashes) -> bool:
        """Compute the (p95, coverage) metrics of every (direction, i, j) in todo
        into self.similarity_cache, reporting progress as it goes.

        Failed comparisons are logged and left uncached, so they count as no
        match. Returns False if stop_check asked to stop.
        """
        total = len(todo)
        grand_total = sum(len(rs) for rs in by_direction.values())

        def report(done):
            if self.progress_callback:
                try:
                    self.progress_callback(
                        grand_total if total == 0 else int(grand_total * done / total),
                        grand_total, todo[min(done, total - 1)][0] if total else '',
                        done, total)
                except Exception:
                    pass

        if not todo:
            report(0)
            return True

        def store(direction, results):
            for i, j, metrics in results:
                if metrics is None:
                    logger.warning("Route comparison failed, treating as no match")
                    continue
                self.similarity_cache[self._pair_key(
                    hashes[direction][i], hashes[direction][j])] = metrics

        # Chunks small enough for steady progress and stop checks, each within
        # one direction.
        chunk_size = max(MIN_PAIRS_PER_CHUNK, -(-total // (self.n_workers * 16)))
        chunks = [(direction, [(i, j) for d, i, j in todo[k:k + chunk_size]
                               if d == direction])
                  for k in range(0, total, chunk_size)
                  for direction in DIRECTIONS]
        chunks = [c for c in chunks if c[1]]

        def run_in_process(pending):
            done_here = 0
            for direction, pairs in pending:
                ts = tracks[direction]
                results = []
                for i, j in pairs:
                    try:
                        metrics = list(prepared_deviation_metrics(ts[i], ts[j]))
                    except Exception:
                        metrics = None
                    results.append((i, j, metrics))
                store(direction, results)
                done_here += len(pairs)
                yield done_here

        done = 0
        if self.n_workers > 1 and total >= MIN_PARALLEL_PAIRS:
            coords = {d: [r.coordinates for r in rs] for d, rs in by_direction.items()}
            executor = ProcessPoolExecutor(max_workers=self.n_workers,
                                           initializer=_init_pair_worker,
                                           initargs=(coords, lat0s))
            futures = {executor.submit(_pair_metrics_worker, c): c for c in chunks}
            remaining = dict(futures)
            try:
                for fut in as_completed(futures):
                    direction, results = fut.result()
                    store(direction, results)
                    del remaining[fut]
                    done += len(results)
                    report(done)
                    if self.stop_check and self.stop_check():
                        return False
            except BrokenProcessPool:
                # A worker died outright (segfault/OOM/killed) rather than raising.
                # Finish what's left in this process rather than fail the run.
                logger.warning("A comparison worker process died; finishing the "
                               f"remaining {len(remaining)} chunks in-process")
                base = done
                for done_here in run_in_process(list(remaining.values())):
                    report(base + done_here)
                    if self.stop_check and self.stop_check():
                        return False
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
        else:
            for done in run_in_process(chunks):
                report(done)
                if self.stop_check and self.stop_check():
                    return False
        return True

    @staticmethod
    def _cluster_by_centres(scores: np.ndarray) -> List[Tuple[int, List[int]]]:
        """Group indices into [(centre, members)], given symmetric match scores
        (0 where a pair can't match).

        Repeatedly takes the ungrouped route that matches the most other
        ungrouped routes as a centre, and groups it with every ungrouped route
        that matches it (Butina clustering). Ties go to the higher total match
        score, then the lower index — with routes sorted by activity ID the
        result doesn't depend on input order (#614). Every member matches its
        group's centre, so a group can't chain into a different route, and the
        centre is the group's representative.
        """
        n = len(scores)
        match = scores >= 1.0
        np.fill_diagonal(match, True)
        ungrouped = np.ones(n, dtype=bool)
        result = []
        while ungrouped.any():
            live = match & ungrouped[None, :]
            degree = live.sum(axis=1)
            total_score = np.where(live, scores, 0.0).sum(axis=1)
            candidates = np.flatnonzero(ungrouped)
            # lexsort: last key is primary; ties fall to the lowest index.
            order = np.lexsort((candidates, -total_score[candidates], -degree[candidates]))
            centre = int(candidates[order[0]])
            members = np.flatnonzero(match[centre] & ungrouped)
            ungrouped[members] = False
            result.append((centre, [int(m) for m in members]))
        return result

    def _assign_group_ids(self, groups: List[RouteGroup]) -> None:
        """Give each group a stable ID and name (#614).

        A group takes the ID (and name) of the previous group it shares the most
        rides with, so IDs — which saved plans and favourites refer to — survive
        a regroup, an incremental run, and a threshold change. Groups with no
        predecessor get the next unused number in their direction, never a
        retired one, so an old ID can't come to mean a different route.
        """
        previous = {}
        for g in (self.groups_cache or {}).get('groups', []):
            previous[g['id']] = (g['direction'],
                                 {r['activity_id'] for r in g.get('routes', [])},
                                 g.get('name'))

        claims = []
        for k, group in enumerate(groups):
            members = {r.activity_id for r in group.routes}
            for old_id, (direction, old_members, _) in previous.items():
                overlap = len(members & old_members)
                if direction == group.direction and overlap:
                    claims.append((-overlap, old_id, min(members), k))
        taken_ids, assigned = set(), {}
        for _, old_id, _, k in sorted(claims):
            if old_id not in taken_ids and k not in assigned:
                taken_ids.add(old_id)
                assigned[k] = old_id

        next_number = {}
        for old_id, (direction, _, _) in previous.items():
            suffix = old_id[len(direction) + 1:]
            if old_id.startswith(direction + '_') and suffix.isdigit():
                next_number[direction] = max(next_number.get(direction, 0), int(suffix) + 1)
        new_groups = sorted((k for k in range(len(groups)) if k not in assigned),
                            key=lambda k: (-groups[k].frequency,
                                           min(r.activity_id for r in groups[k].routes)))
        for k in new_groups:
            direction = groups[k].direction
            number = next_number.get(direction, 0)
            next_number[direction] = number + 1
            assigned[k] = f"{direction}_{number}"

        for k, group in enumerate(groups):
            group.id = assigned[k]
            old = previous.get(group.id)
            if old and old[2]:
                group.name = old[2]
            else:
                direction_label = "to Work" if group.direction == "home_to_work" else "to Home"
                group.name = f"Route {group.id.rsplit('_', 1)[-1]} {direction_label}"

    def _mark_plus_routes(self, groups: List[RouteGroup]) -> List[RouteGroup]:
        """
        Flag longer-than-usual routes. Flags are recomputed from scratch on
        every call (#614), so they never stick from an earlier run.

        - A group is a "plus route" when its representative is >15% longer than
          the median commute in that direction (all rides pooled, so it's the
          typical day's distance), or when most of its rides are labelled plus.
        - A ride is flagged when it's >15% longer than its own group's median,
          or when the rider labelled it plus ("Ride to work +").

        Args:
            groups: List of route groups

        Returns:
            The same groups, with is_plus_route set
        """
        for direction in DIRECTIONS:
            direction_groups = [g for g in groups if g.direction == direction]
            distances = [r.distance for g in direction_groups for r in g.routes]
            if not distances:
                continue
            threshold = np.median(distances) * PLUS_ROUTE_FACTOR

            plus_count = 0
            for group in direction_groups:
                group_threshold = np.median([r.distance for r in group.routes]) * PLUS_ROUTE_FACTOR
                for route in group.routes:
                    route.is_plus_route = bool(
                        route.distance > group_threshold or is_labelled_plus(route.activity_name)
                    )
                labelled = sum(is_labelled_plus(r.activity_name) for r in group.routes)
                group.is_plus_route = bool(
                    group.representative_route.distance > threshold or labelled * 2 > len(group.routes)
                )
                plus_count += group.is_plus_route

            if plus_count > 0:
                tqdm.write(f"   ⭐ {plus_count} {DIRECTION_LABELS[direction]} PLUS routes")
                tqdm.write(f"      (>{threshold / PLUS_ROUTE_FACTOR / 1000:.1f}km + 15%)")

        return groups

    def _geocoding_enabled(self) -> bool:
        """Whether background geocoding should run for this instance.

        The per-instance override (set via the `enable_geocoding` constructor arg) takes
        precedence over the `route_analysis.enable_geocoding` config value, so throwaway
        analyzer instances (e.g. the preview pass) can force geocoding off regardless of
        what the user has configured.
        """
        if self._enable_geocoding_override is not None:
            return self._enable_geocoding_override
        return bool(self.config) and self.config.get('route_analysis.enable_geocoding', True)

    def _start_background_geocoding(self, groups: List[RouteGroup], auto_approve: bool = False) -> None:
        """
        Start background thread to geocode route names.
        This allows route grouping to complete quickly while geocoding happens in parallel.
        Opens a new terminal window to show geocoding progress, but only when
        self.interactive is True (CLI usage) — see __init__.

        Args:
            groups: List of RouteGroup objects to geocode
            auto_approve: If True, skip user prompt (for automated runs)
        """
        # Don't start if geocoding is disabled
        if not self._geocoding_enabled():
            logger.info("Geocoding disabled, skipping background geocoding")
            return

        # Check if we're currently rate limited
        rate_limit_file = os.path.join(self.cache_dir, "geocoding_rate_limit.json")
        blocked_until = check_rate_limit_file(rate_limit_file)
        if blocked_until is not None:
            import time as time_module
            tz_name = time_module.tzname[time_module.daylight]
            blocked_until_formatted = f"{blocked_until.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"

            logger.info(f"Geocoding is rate limited until {blocked_until_formatted}, skipping")
            tqdm.write("\n" + "="*60)
            tqdm.write("⚠️  GEOCODING RATE LIMITED")
            tqdm.write("="*60)
            tqdm.write("Background geocoding is currently paused due to rate limiting.")
            tqdm.write(f"Self-imposed block until: {blocked_until_formatted}")
            tqdm.write("\n💡 Geocoding will automatically resume after the block expires.")
            tqdm.write("   Re-run analysis after that time to geocode route names.")
            tqdm.write("="*60 + "\n")
            return

        # Don't start multiple threads
        if self._geocoding_thread and self._geocoding_thread.is_alive():
            logger.info("Background geocoding already in progress, skipping new geocoding request")
            tqdm.write("\n⚠️  Background geocoding is already running. Check the geocoding terminal for progress.\n")
            return
        
        # Count routes that need geocoding (those with temporary names)
        routes_needing_geocoding = sum(1 for g in groups if g.name and ("Route" in g.name and ("to Work" in g.name or "to Home" in g.name)))
        routes_already_named = len(groups) - routes_needing_geocoding
        
        # Don't start if no routes need geocoding
        if routes_needing_geocoding == 0:
            logger.info("All routes already have geocoded names, skipping background geocoding")
            tqdm.write("\n" + "="*60)
            tqdm.write("✅ ALL ROUTES ALREADY GEOCODED")
            tqdm.write("="*60)
            tqdm.write(f"All {len(groups)} routes already have descriptive names.")
            tqdm.write("No background geocoding needed.")
            tqdm.write("="*60 + "\n")
            return
        
        logger.info(f"Starting background geocoding for {routes_needing_geocoding} route groups")
        
        # Display user-friendly message and prompt for approval
        tqdm.write("\n" + "="*60)
        tqdm.write("🌐 ROUTE NAMING STATUS")
        tqdm.write("="*60)
        tqdm.write(f"✓ {routes_already_named} routes already have geocoded names")
        tqdm.write(f"⏳ {routes_needing_geocoding} routes need geocoding")
        tqdm.write("")
        tqdm.write("📍 Background geocoding will:")
        tqdm.write("   • Run in a separate terminal window")
        tqdm.write("   • Fetch street names from OpenStreetMap")
        tqdm.write("   • Allow you to continue using the report immediately")
        tqdm.write("   • Update route names for future runs")
        tqdm.write("="*60)
        
        # Prompt user for approval unless auto-approved
        if not auto_approve:
            tqdm.write("")
            try:
                response = input("Start background geocoding? [Y/n]: ").strip().lower()
                if response and response not in ['y', 'yes']:
                    tqdm.write("\n⏭️  Skipping background geocoding. Routes will use temporary names.")
                    tqdm.write("   You can re-run analysis later to geocode route names.\n")
                    logger.info("User declined background geocoding")
                    return
            except (EOFError, OSError):
                # Handle non-interactive environments (tests, CI/CD, etc.)
                logger.info("Non-interactive environment detected, auto-approving geocoding")
                tqdm.write("\n✓ Non-interactive mode: auto-approving background geocoding\n")
        
        tqdm.write("\n✓ Starting background geocoding...")
        if self.interactive and sys.platform == 'darwin':
            tqdm.write("  A new terminal window will open to show progress.\n")
        elif self.interactive:
            progress_file = self.cache_dir / 'geocoding_progress.txt'
            tqdm.write(f"  Progress terminal windows are only supported on macOS; "
                       f"track progress in {progress_file}\n")
        else:
            tqdm.write("  Running quietly in the background (non-interactive mode).\n")

        self._geocoding_thread = threading.Thread(
            target=self._geocode_routes_background,
            args=(groups,),
            daemon=True,
            name="RouteGeocoding"
        )
        self._geocoding_thread.start()

        # Only pop open a desktop terminal window for the interactive CLI (main.py).
        # The web service constructs RouteAnalyzer with interactive=False so a server-side
        # analysis run never spawns Terminal.app windows on the host running it.
        if self.interactive:
            self._open_geocoding_terminal(routes_needing_geocoding)
    
    def _open_geocoding_terminal(self, total_routes: int) -> None:
        """
        Open a new terminal window to show geocoding progress.
        Creates a progress file that the terminal monitors.
        
        Args:
            total_routes: Total number of routes being geocoded
        """
        if sys.platform != 'darwin':
            # osascript/Terminal.app is macOS-only; geocoding still proceeds
            # in the background, just without a monitor window.
            logger.debug("Skipping geocoding terminal window: not on macOS")
            return

        try:
            # Create progress file with absolute path
            progress_file = self.cache_dir / 'geocoding_progress.txt'
            progress_file_abs = progress_file.resolve()  # Get absolute path
            
            with open(progress_file, 'w') as f:
                f.write(f"🌐 Route Geocoding Progress\n")
                f.write(f"{'='*60}\n")
                f.write(f"Total routes: {total_routes}\n")
                f.write(f"Progress: 0/{total_routes}\n")
                f.write(f"{'='*60}\n\n")
                f.write("Starting geocoding...\n")
            
            # Open new terminal window with tail command to monitor progress
            # Use osascript on macOS to open Terminal.app
            # Use absolute path to ensure terminal can find the file
            script = f'''
tell application "Terminal"
    do script "echo '🌐 Route Geocoding Monitor'; echo ''; tail -f {progress_file_abs}; echo ''; echo 'Press Ctrl+C to close this window'"
    activate
end tell
'''
            # Start subprocess in a new session to properly detach it
            # Use subprocess.run in background to avoid ResourceWarning
            import threading
            def start_terminal():
                try:
                    subprocess.run(
                        ['osascript', '-e', script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False
                    )
                except Exception as e:
                    # Not critical — geocoding_progress.txt is already being written
                    # unconditionally by _geocode_routes_background, so the user can
                    # still monitor progress by hand even if the terminal never opens.
                    logger.debug(f"Could not open geocoding monitor terminal: {e}")
            
            # Start in a daemon thread so it doesn't block exit
            terminal_thread = threading.Thread(target=start_terminal, daemon=True)
            terminal_thread.start()
            # Don't wait for the thread - let it run independently
            # The terminal window will remain open for the user to monitor
            
        except Exception as e:
            logger.warning(f"Could not open geocoding terminal: {e}")
            # Not critical, continue anyway
    
    @staticmethod
    def _dedupe_route_names(all_groups_for_direction: List[RouteGroup]) -> None:
        """
        Deduplicate route names across *all* groups for a direction (not just the
        current geocoding batch) so that names generated in previous runs cannot
        collide with newly geocoded names.

        Disambiguation priority:
          1. Terrain character (flat / rolling / hilly) if routes differ in terrain
          2. Distance bracket (short / long) if terrain alone doesn't differentiate
          3. Ordinal (#2, #3) as final fallback

        Each pass is applied recursively/exhaustively: if a pass splits a clashing
        group into sub-buckets but one of those sub-buckets still contains more
        than one route (e.g. 5 near-identical routes median-split into 'short'
        and 'long' but one bucket still has 3 members), the remaining passes are
        applied *within that bucket* rather than being skipped for the whole
        group. A final verification pass guarantees no two groups in the same
        direction end up sharing a name, regardless of how they got there.
        """
        from collections import defaultdict

        def _terrain_label(g: RouteGroup) -> str:
            """Derive a terrain label from elevation_gain / distance."""
            rep = g.representative_route
            dist_m = rep.distance or 0
            elev_m = rep.elevation_gain or 0
            if dist_m <= 0:
                return 'flat'
            gain_per_km = elev_m / (dist_m / 1000.0)
            if gain_per_km > 30:
                return 'hilly'
            if gain_per_km > 15:
                return 'rolling'
            return 'flat'

        def _ordinal_fallback(base_name: str, bucket: List[RouteGroup]) -> None:
            """Pass 3: keep the first group's name intact; suffix the rest."""
            if len(bucket) <= 1:
                return
            for idx, g in enumerate(bucket[1:], start=2):
                g.name = f"{base_name} #{idx}"

        def _disambiguate_distance(base_name: str, bucket: List[RouteGroup]) -> None:
            """Pass 2: distance bracket disambiguation, falling through to
            ordinal numbering *per resulting bucket* if a bracket still clashes."""
            if len(bucket) <= 1:
                return

            distances = [g.representative_route.distance or 0 for g in bucket]
            if len(set(distances)) > 1:
                median_dist = sorted(distances)[len(distances) // 2]

                def _dist_label(d: float) -> str:
                    return 'short' if d < median_dist else 'long'

                dist_labels = [_dist_label(d) for d in distances]
                if len(set(dist_labels)) > 1:
                    sub_buckets: Dict[str, List[RouteGroup]] = defaultdict(list)
                    for g, label in zip(bucket, dist_labels):
                        new_name = f"{base_name} — {label}"
                        g.name = new_name
                        sub_buckets[new_name].append(g)
                    for new_name, sub_bucket in sub_buckets.items():
                        if len(sub_bucket) > 1:
                            _ordinal_fallback(new_name, sub_bucket)
                    return

            _ordinal_fallback(base_name, bucket)

        def _disambiguate(base_name: str, bucket: List[RouteGroup]) -> None:
            """Pass 1: terrain disambiguation, falling through to distance-bracket
            disambiguation *per resulting bucket* if a terrain label still clashes."""
            if len(bucket) <= 1:
                return

            terrain_labels = [_terrain_label(g) for g in bucket]
            if len(set(terrain_labels)) > 1:
                sub_buckets: Dict[str, List[RouteGroup]] = defaultdict(list)
                for g, label in zip(bucket, terrain_labels):
                    new_name = f"{base_name} — {label}"
                    g.name = new_name
                    sub_buckets[new_name].append(g)
                for new_name, sub_bucket in sub_buckets.items():
                    if len(sub_bucket) > 1:
                        _disambiguate_distance(new_name, sub_bucket)
                return

            _disambiguate_distance(base_name, bucket)

        # Build name → [group] map
        by_name: Dict[str, List[RouteGroup]] = defaultdict(list)
        for g in all_groups_for_direction:
            if g.name:
                by_name[g.name].append(g)

        for name, clashing in by_name.items():
            if len(clashing) <= 1:
                continue
            _disambiguate(name, clashing)

        # ---- Final verification pass ----
        # Ordinal numbering is the guaranteed last resort, so after all passes
        # no two groups sharing a direction should still have identical names.
        # Enforce that invariant directly rather than trusting it held, so a
        # future change to the passes above can't silently regress into
        # duplicate names again.
        seen_names: set = set()
        for g in all_groups_for_direction:
            if not g.name:
                continue
            if g.name not in seen_names:
                seen_names.add(g.name)
                continue
            idx = 2
            candidate = f"{g.name} #{idx}"
            while candidate in seen_names:
                idx += 1
                candidate = f"{g.name} #{idx}"
            g.name = candidate
            seen_names.add(candidate)

    def _geocode_routes_background(self, groups: List[RouteGroup]) -> None:
        """
        Background worker that geocodes route names and updates the cache.
        Runs in a separate thread to not block the main analysis.
        Writes progress to a file with timestamps and concise output (2 lines per route).
        
        Args:
            groups: List of RouteGroup objects to geocode
        """
        from datetime import datetime, timedelta
        progress_file = self.cache_dir / 'geocoding_progress.txt'
        
        def timestamp():
            """Get current timestamp in HH:MM:SS format"""
            return datetime.now().strftime("%H:%M:%S")
        
        try:
            start_time = datetime.now()
            logger.info(f"Background geocoding started for {len(groups)} groups")
            
            # Filter groups that need geocoding (have temporary names)
            groups_to_geocode = [g for g in groups if g.name and ("Route" in g.name and ("to Work" in g.name or "to Home" in g.name))]
            
            # Write header to progress file with timezone
            try:
                import time as time_module
                tz_name = time_module.tzname[time_module.daylight]
                start_time_formatted = f"{start_time.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"
                
                with open(progress_file, 'w') as f:
                    f.write(f"{'='*70}\n")
                    f.write(f"🌐 ROUTE GEOCODING IN PROGRESS\n")
                    f.write(f"{'='*70}\n")
                    f.write(f"Started: {start_time_formatted}\n")
                    f.write(f"Total routes to geocode: {len(groups_to_geocode)}\n")
                    f.write(f"\n⚠️  RATE LIMITING INFO:\n")
                    f.write(f"• Nominatim enforces 1 request/second maximum\n")
                    f.write(f"• Retries with exponential backoff on timeouts\n")
                    f.write(f"• If rate limited, system will self-impose 4-hour pause\n")
                    f.write(f"• This prevents IP blocks and allows Nominatim to reset\n")
                    f.write(f"{'='*70}\n\n")
                    f.flush()
            except OSError as e:
                logger.debug(f"Failed to write progress file header: {e}")

            geocoded_count = 0
            failed_count = 0
            
            # Phase 1: Geocode routes with concise progress
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"[{timestamp()}] Phase 1/2: Geocoding route names\n")
                    f.write(f"{'-'*70}\n")
            except OSError as e:
                logger.debug(f"Failed to write progress file: {e}")

            for i, group in enumerate(groups_to_geocode, 1):
                try:
                    # Generate descriptive route name using RouteNamer
                    route_name = self.route_namer.name_route(
                        group.representative_route.coordinates,
                        group.id,
                        group.direction,
                        elevation_gain=group.representative_route.elevation_gain,
                        distance=group.representative_route.distance,
                    )
                    
                    # Update the group name with thread safety
                    with self._geocoding_lock:
                        group.name = route_name
                    
                    geocoded_count += 1
                    
                    # Update progress file with concise output (2 lines per route)
                    try:
                        with open(progress_file, 'a') as f:
                            progress_pct = (i / len(groups_to_geocode)) * 100
                            bar_length = 30
                            filled = int(bar_length * i / len(groups_to_geocode))
                            bar = '█' * filled + '░' * (bar_length - filled)
                            # Line 1: Progress bar with timestamp and count
                            f.write(f"[{timestamp()}] [{bar}] {progress_pct:5.1f}% ({i}/{len(groups_to_geocode)})\n")
                            # Line 2: Route name
                            f.write(f"  ✓ {route_name}\n")
                            f.flush()  # Ensure immediate write to disk for visibility
                    except Exception as e:
                        logger.debug(f"Failed to write progress: {e}")
                    
                    if geocoded_count % 10 == 0:
                        logger.info(f"Background geocoding progress: {geocoded_count}/{len(groups_to_geocode)} routes named")
                
                except Exception as e:
                    failed_count += 1
                    error_msg = str(e)
                    error_lower = error_msg.lower()
                    
                    # Check if this is a rate limit error
                    is_rate_limit = 'rate' in error_lower or 'limit' in error_lower or 'blocked' in error_lower
                    
                    logger.warning(f"Failed to geocode route {group.id}: {error_msg}")
                    try:
                        import time as time_module
                        tz_name = time_module.tzname[time_module.daylight]
                        
                        with open(progress_file, 'a') as f:
                            if is_rate_limit:
                                resume_time = datetime.now() + timedelta(hours=4)
                                resume_time_formatted = f"{resume_time.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"
                                
                                f.write(f"\n{'='*70}\n")
                                f.write(f"⚠️  RATE LIMIT DETECTED\n")
                                f.write(f"{'='*70}\n")
                                f.write(f"[{timestamp()}] Nominatim API rate limit hit\n")
                                f.write(f"Route: {group.id[:30]}\n")
                                f.write(f"Error: {error_msg[:60]}\n")
                                f.write(f"\n🛑 SELF-IMPOSING 4-HOUR PAUSE\n")
                                f.write(f"This is a protective measure to prevent IP blocking.\n")
                                f.write(f"Next geocoding attempt after: {resume_time_formatted}\n")
                                f.write(f"\n💡 The next analysis run will automatically wait if needed.\n")
                                f.write(f"{'='*70}\n\n")
                            else:
                                f.write(f"[{timestamp()}] ✗ Failed: {group.id[:30]}\n")
                                f.write(f"     Error: {error_msg[:60]}\n")
                            f.flush()  # Ensure immediate write to disk
                    except Exception as write_error:
                        logger.debug(f"Failed to write error to progress file: {write_error}")
                    
                    # If rate limited, stop geocoding immediately
                    if is_rate_limit:
                        logger.error("Rate limit detected, stopping geocoding")
                        break
            
            # Deduplicate names across all groups (including previously-named ones)
            by_direction: Dict[str, List[RouteGroup]] = {}
            for g in groups:
                by_direction.setdefault(g.direction, []).append(g)
            for direction_groups in by_direction.values():
                self._dedupe_route_names(direction_groups)

            # Phase 2: Saving caches
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"\n{'-'*70}\n")
                    f.write(f"[{timestamp()}] Phase 2/4: Saving geocoding cache\n")
                    f.write(f"{'-'*70}\n")
            except OSError as e:
                logger.debug(f"Failed to write progress file: {e}")

            self.route_namer._save_cache()
            logger.info("Geocoding cache saved to disk")
            
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"[{timestamp()}] ✓ Geocoding cache saved\n")
            except OSError as e:
                logger.debug(f"Failed to write progress file: {e}")
            
            # Phase 3: Save route groups cache with updated names
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"\n{'-'*70}\n")
                    f.write(f"[{timestamp()}] Phase 3/4: Saving route groups cache with updated names\n")
                    f.write(f"{'-'*70}\n")
            except OSError as e:
                logger.debug(f"Failed to write progress file: {e}")
            
            # Extract activity IDs from groups
            activity_ids = []
            for group in groups:
                for route in group.routes:
                    if route.activity_id not in activity_ids:
                        activity_ids.append(route.activity_id)
            
            # Save route groups cache with updated names
            self._save_groups_cache_with_ids(activity_ids, groups)
            logger.info("Route groups cache saved with updated names")
            
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"[{timestamp()}] ✓ Route groups cache saved with {geocoded_count} updated names\n")
            except OSError as e:
                logger.debug(f"Failed to write progress file: {e}")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Background geocoding completed: {geocoded_count}/{len(groups_to_geocode)} routes successfully named")
            
            # Write completion summary with timezone
            # Phase 4: Migrate to web app data directory
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"\n{'-'*70}\n")
                    f.write(f"[{timestamp()}] Phase 4/4: Migrating to web app data directory\n")
                    f.write(f"{'-'*70}\n")
            except OSError as e:
                logger.debug(f"Failed to write progress file: {e}")
            
            migration_success = False
            try:
                # Run migration script to copy data to web app directory
                import subprocess
                result = subprocess.run(
                    [sys.executable, 'scripts/migrate_cache_to_json_storage.py'],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                migration_success = (result.returncode == 0)
                
                if migration_success:
                    logger.info("Successfully migrated geocoded data to web app directory")
                    try:
                        with open(progress_file, 'a') as f:
                            f.write(f"[{timestamp()}] ✓ Data migrated to web app (data/route_groups.json)\n")
                    except OSError as e:
                        logger.debug(f"Failed to write progress file: {e}")
                else:
                    logger.warning(f"Migration script failed: {result.stderr}")
                    try:
                        with open(progress_file, 'a') as f:
                            f.write(f"[{timestamp()}] ⚠️  Migration failed (see logs)\n")
                    except OSError as e:
                        logger.debug(f"Failed to write progress file: {e}")
            except Exception as e:
                logger.warning(f"Failed to run migration script: {e}")
                try:
                    with open(progress_file, 'a') as f:
                        f.write(f"[{timestamp()}] ⚠️  Migration error: {str(e)[:50]}\n")
                except OSError as write_err:
                    logger.debug(f"Failed to write progress file: {write_err}")
            
            # Write completion summary with timezone
            try:
                import time as time_module
                tz_name = time_module.tzname[time_module.daylight]
                end_time_formatted = f"{end_time.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"
                
                with open(progress_file, 'a') as f:
                    f.write(f"\n{'='*70}\n")
                    f.write(f"✅ GEOCODING COMPLETE!\n")
                    f.write(f"{'='*70}\n")
                    f.write(f"Completed: {end_time_formatted}\n")
                    f.write(f"Duration: {duration:.1f} seconds\n")
                    f.write(f"Successfully named: {geocoded_count}/{len(groups_to_geocode)} routes\n")
                    if failed_count > 0:
                        f.write(f"Failed: {failed_count} routes\n")
                    f.write(f"\n✅ Route names have been saved to cache.\n")
                    if migration_success:
                        f.write(f"✅ Geocoded names migrated to web app.\n")
                        f.write(f"\n📋 TO SEE UPDATED ROUTE NAMES:\n")
                        f.write(f"   • Refresh your web dashboard - names are already updated!\n")
                        f.write(f"   • Or re-run: python main.py --analyze\n")
                    else:
                        f.write(f"\n📋 TO SEE UPDATED ROUTE NAMES IN WEB APP:\n")
                        f.write(f"   1. Run: python3 scripts/migrate_cache_to_json_storage.py\n")
                        f.write(f"   2. Refresh your web dashboard\n")
                        f.write(f"\n📋 TO SEE UPDATED ROUTE NAMES IN CLI REPORT:\n")
                        f.write(f"   • Re-run: python main.py --analyze\n")
                    f.write(f"\n💡 The cache has been updated, so the next run will be fast!\n")
                    f.write(f"{'='*70}\n")
            except OSError as e:
                logger.debug(f"Failed to write progress file summary: {e}")

        except Exception as e:
            logger.error(f"Background geocoding thread failed: {e}", exc_info=True)
            error_msg = str(e)
            error_type = type(e).__name__
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"\n{'='*70}\n")
                    f.write(f"❌ GEOCODING FAILED\n")
                    f.write(f"{'='*70}\n")
                    f.write(f"Error Type: {error_type}\n")
                    f.write(f"Error Message: {error_msg}\n")
                    f.write(f"\n💡 Check logs/debug.log for full stack trace.\n")
                    f.write(f"{'='*70}\n")
                    f.flush()
            except Exception as write_error:
                logger.error(f"Failed to write error to progress file: {write_error}")

