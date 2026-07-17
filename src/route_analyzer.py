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
from concurrent.futures import ProcessPoolExecutor
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
    passes_prefilter_deg, frechet_similarity_deg,
    hausdorff_percentile_similarity_deg, commute_similarity_score,
)

logger = SecureLogger(__name__)

try:
    import similaritymeasures
    FRECHET_AVAILABLE = True
except ImportError:
    FRECHET_AVAILABLE = False
    logger.warning("similaritymeasures not available, using Hausdorff distance only")


def _similarity_worker(args):
    """
    Module-level worker for ProcessPoolExecutor.

    Computes Fréchet+Hausdorff similarity between a pivot route and a batch of
    candidates. Must be a top-level function so it is picklable on all platforms.

    args: (pivot_coords, candidates, frechet_available, hausdorff_percentile)
      pivot_coords       – list of [lat, lon] pairs for the pivot route
      candidates         – list of (original_idx, cache_key, candidate_coords)
      frechet_available  – bool
      hausdorff_percentile – float (e.g. 95.0)

    Returns list of (original_idx, cache_key, similarity_score).
    """
    import numpy as np
    from .route_comparison import commute_similarity_score

    pivot_coords, candidates, frechet_available, hausdorff_percentile = args
    pivot = np.array(pivot_coords)
    results = []

    for (original_idx, cache_key, candidate_coords) in candidates:
        candidate = np.array(candidate_coords)
        score = commute_similarity_score(
            pivot, candidate,
            percentile=hausdorff_percentile,
            frechet_available=frechet_available,
        )
        results.append((original_idx, cache_key, score))

    return results


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
    path_length_deg: Optional[float] = None  # sum of segment lengths in degrees (cheap proxy for distance)

    def compute_geometry(self):
        """Populate bbox, centroid, and path_length_deg from coordinates."""
        coords = self.coordinates
        if not coords:
            return
        arr = np.array(coords)
        self.bbox = (float(arr[:, 0].min()), float(arr[:, 1].min()),
                     float(arr[:, 0].max()), float(arr[:, 1].max()))
        self.centroid = (float(arr[:, 0].mean()), float(arr[:, 1].mean()))
        if len(arr) > 1:
            diffs = np.diff(arr, axis=0)
            self.path_length_deg = float(np.sqrt((diffs ** 2).sum(axis=1)).sum())
        else:
            self.path_length_deg = 0.0


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
            force_reanalysis: If True, clear cache and reprocess all routes
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
        self.similarity_threshold = config.get('route_analysis.similarity_threshold', 0.85)
        self.route_namer = RouteNamer(config)
        self.force_reanalysis = force_reanalysis
        
        # Initialize caches
        self.cache_dir = Path(cache_dir) if cache_dir is not None else Path('cache')
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / 'route_similarity_cache.json'
        self.similarity_cache = self._load_similarity_cache()
        
        # Route grouping cache
        self.groups_cache_file = self.cache_dir / 'route_groups_cache.json'
        
        # Clear cache if force reanalysis
        if force_reanalysis and self.groups_cache_file.exists():
            tqdm.write("   🗑️  Clearing route groups cache (force reanalysis)")
            self.groups_cache_file.unlink()
            self.groups_cache = {}
        else:
            self.groups_cache = self._load_groups_cache()
        
        # Background geocoding thread and subprocess
        self._geocoding_thread = None
        self._geocoding_lock = threading.Lock()
        self._terminal_process = None

        # Active ProcessPoolExecutor for route-similarity comparisons, set for the
        # duration of group_similar_routes(). Held on the instance (rather than
        # passed purely as a local) so a broken pool can be replaced mid-run and
        # the replacement stays visible across both direction passes.
        self._executor: Optional[ProcessPoolExecutor] = None
        
    def _load_similarity_cache(self) -> Dict[str, float]:
        """Load similarity cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded {len(cache)} cached similarity calculations")
                return cache
            except Exception as e:
                logger.warning(f"Failed to load similarity cache: {e}")
                return {}
        return {}
    
    def _save_similarity_cache(self):
        """Save similarity cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.similarity_cache, f)
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
                        'path_length_deg': group.representative_route.path_length_deg,
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
                            'path_length_deg': r.path_length_deg,
                        }
                        for r in group.routes
                    ]
                }
                serialized_groups.append(serialized_group)
            
            cache_data = {
                'activity_ids': activity_ids,
                'groups': serialized_groups,
                'similarity_threshold': self.similarity_threshold,
                'algorithm': 'frechet' if FRECHET_AVAILABLE else 'hausdorff',
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
            path_length_deg=data.get('path_length_deg'),
        )
        if route.bbox is None:
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
    
    def _generate_cache_key(self, routes: List[Route]) -> str:
        """
        Generate cache key based on route activity IDs and config.
        
        Args:
            routes: List of routes
            
        Returns:
            Cache key string
        """
        # Sort activity IDs for consistent key
        activity_ids = sorted([r.activity_id for r in routes])
        
        # Include similarity threshold and algorithm version in key
        key_data = {
            'activity_ids': activity_ids,
            'similarity_threshold': self.similarity_threshold,
            'algorithm': 'frechet' if FRECHET_AVAILABLE else 'hausdorff',
            'version': '2.0'  # Increment when algorithm changes
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _get_route_hash(self, route: Route) -> str:
        """
        Generate a unique hash for a route based on its coordinates.
        
        Args:
            route: Route object
            
        Returns:
            Hash string
        """
        # Create a string representation of coordinates (first, middle, last points)
        coords = route.coordinates
        if len(coords) > 10:
            # Sample points to keep hash manageable
            sample_coords = [coords[0], coords[len(coords)//4], coords[len(coords)//2],
                           coords[3*len(coords)//4], coords[-1]]
        else:
            sample_coords = coords
        
        coord_str = ','.join([f"{lat:.6f},{lon:.6f}" for lat, lon in sample_coords])
        return hashlib.sha256(coord_str.encode()).hexdigest()[:16]
    
    def _get_cache_key(self, route1: Route, route2: Route) -> str:
        """
        Generate cache key for a route pair.
        
        Args:
            route1: First route
            route2: Second route
            
        Returns:
            Cache key string
        """
        hash1 = self._get_route_hash(route1)
        hash2 = self._get_route_hash(route2)
        # Sort hashes to ensure same key regardless of order
        return f"{min(hash1, hash2)}_{max(hash1, hash2)}"

    @staticmethod
    def _passes_geometric_filter(route1: 'Route', route2: 'Route',
                                 length_ratio_max: float = 2.0,
                                 centroid_max_deg: float = 0.02,
                                 bbox_overlap_min: float = 0.3) -> bool:
        """Fast geometric pre-filter — returns False if routes are obviously dissimilar.

        Delegates to the shared route_comparison.passes_prefilter_deg, using
        Route's precomputed bbox/centroid/path_length_deg (see
        Route.compute_geometry) rather than recomputing geometry from full
        coordinate arrays on every candidate pair.
        """
        return passes_prefilter_deg(
            route1.bbox, route1.centroid, route1.path_length_deg,
            route2.bbox, route2.centroid, route2.path_length_deg,
            length_ratio_max=length_ratio_max,
            centroid_max_deg=centroid_max_deg,
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
        
        for activity in self.activities:
            if not activity.polyline:
                continue
            
            # Determine route direction
            route_direction = self._determine_direction(activity)
            
            if route_direction is None:
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
        
        return routes
    
    def _determine_direction(self, activity: Activity) -> str:
        """
        Determine if route is home-to-work or work-to-home.
        
        Args:
            activity: Activity object
            
        Returns:
            'home_to_work', 'work_to_home', or None
        """
        if not activity.start_latlng or not activity.end_latlng:
            return None
        
        # Calculate distances
        start_to_home = geodesic(activity.start_latlng, (self.home.lat, self.home.lon)).meters
        start_to_work = geodesic(activity.start_latlng, (self.work.lat, self.work.lon)).meters
        end_to_home = geodesic(activity.end_latlng, (self.home.lat, self.home.lon)).meters
        end_to_work = geodesic(activity.end_latlng, (self.work.lat, self.work.lon)).meters
        
        # Use larger radius for matching (500m)
        max_distance = 500
        
        # Check if starts near home and ends near work
        if start_to_home < max_distance and end_to_work < max_distance:
            return 'home_to_work'
        
        # Check if starts near work and ends near home
        if start_to_work < max_distance and end_to_home < max_distance:
            return 'work_to_home'
        
        return None
    
    def calculate_route_similarity(self, route1: Route, route2: Route) -> float:
        """
        Calculate similarity between two routes using Fréchet distance as primary metric.
        
        Fréchet distance is superior for route comparison because:
        - Considers the order of points (path similarity, like walking a dog)
        - Better captures whether routes follow the same path
        - More robust to GPS sampling differences
        
        Hausdorff is used as a secondary validation check.
        
        Results are cached to avoid expensive recalculations.
        
        Args:
            route1: First route
            route2: Second route
            
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        # Check cache first
        cache_key = self._get_cache_key(route1, route2)
        if cache_key in self.similarity_cache:
            logger.debug(f"Using cached similarity for {cache_key}")
            return self.similarity_cache[cache_key]
        
        # Calculate similarity
        coords1 = np.array(route1.coordinates)
        coords2 = np.array(route2.coordinates)
        
        # Calculate Fréchet distance (primary metric)
        if FRECHET_AVAILABLE:
            frechet_sim = self._calculate_frechet_similarity(coords1, coords2)
            
            # Calculate Hausdorff as secondary validation
            hausdorff_sim = self._calculate_hausdorff_similarity(coords1, coords2)
            
            # Use Fréchet as primary, but require Hausdorff to not strongly disagree
            # If Hausdorff is very low (<0.50), it indicates routes are spatially far apart
            if hausdorff_sim < 0.50:
                # Routes are too far apart spatially, reduce Fréchet score
                combined_similarity = frechet_sim * 0.7  # Penalize by 30%
                logger.debug(f"Fréchet: {frechet_sim:.3f}, Hausdorff: {hausdorff_sim:.3f} (spatial disagreement), Combined: {combined_similarity:.3f}")
            else:
                # Hausdorff agrees or is neutral, use Fréchet as-is
                combined_similarity = frechet_sim
                logger.debug(f"Fréchet: {frechet_sim:.3f} (primary), Hausdorff: {hausdorff_sim:.3f} (validates)")
        else:
            # Fallback to Hausdorff if Fréchet not available
            combined_similarity = self._calculate_hausdorff_similarity(coords1, coords2)
            logger.debug(f"Hausdorff only (Fréchet unavailable): {combined_similarity:.3f}")
        
        # Cache the result
        self.similarity_cache[cache_key] = combined_similarity
        
        return combined_similarity
    
    def _calculate_hausdorff_similarity(self, coords1: np.ndarray, coords2: np.ndarray) -> float:
        """
        Calculate similarity using percentile-based Hausdorff distance.
        
        Instead of using the maximum deviation (which is sensitive to outliers),
        uses the Nth percentile of deviations. This allows X% of points to be
        outliers (GPS glitches, brief detours) while still detecting substantive
        route differences.
        
        Args:
            coords1: First route coordinates
            coords2: Second route coordinates
            
        Returns:
            Similarity score (0-1)
        """
        # Get percentile from config (default 95.0 = ignore worst 5% of deviations)
        percentile = self.config.get('route_analysis.outlier_tolerance_percentile', 95.0)

        # Delegates to the shared route_comparison implementation (also used by
        # _similarity_worker, the ProcessPoolExecutor path) so both the sequential
        # and parallel grouping paths stay on identical math.
        return hausdorff_percentile_similarity_deg(coords1, coords2, percentile=percentile)

    def _calculate_frechet_similarity(self, coords1: np.ndarray, coords2: np.ndarray) -> float:
        """
        Calculate similarity using Fréchet distance.

        Fréchet distance considers the order of points, like walking a dog on a leash.
        It's better at detecting routes that follow the same path vs routes that are
        spatially close but follow different paths.

        Args:
            coords1: First route coordinates
            coords2: Second route coordinates

        Returns:
            Similarity score (0-1)
        """
        try:
            # Delegates to the shared route_comparison implementation (also used by
            # _similarity_worker, the ProcessPoolExecutor path).
            return frechet_similarity_deg(coords1, coords2)
        except Exception as e:
            logger.warning(f"Fréchet distance calculation failed: {e}, falling back to Hausdorff")
            return self._calculate_hausdorff_similarity(coords1, coords2)
    
    def group_similar_routes(self, routes: List[Route] = None) -> List[RouteGroup]:
        """
        Group similar routes with intelligent caching and incremental analysis.
        
        Uses cached groups when possible, only processes new routes incrementally,
        and only uses parallelism when beneficial (>100 new routes).
        
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
        
        # Check for cached groups
        if not self.force_reanalysis and self.groups_cache:
            cached_activity_ids = set(self.groups_cache.get('activity_ids', []))
            current_activity_ids = set(r.activity_id for r in routes)
            
            # Check if we can use incremental analysis
            new_activity_ids = current_activity_ids - cached_activity_ids
            removed_activity_ids = cached_activity_ids - current_activity_ids
            
            if not new_activity_ids and not removed_activity_ids:
                # Perfect cache hit - no changes
                tqdm.write("   💾 Using cached route groups (instant!)")
                cached_groups = self._deserialize_groups(self.groups_cache['groups'])
                logger.info(f"Loaded {len(cached_groups)} route groups from cache")
                return cached_groups
            
            elif new_activity_ids and not removed_activity_ids:
                # Incremental analysis - only new routes
                tqdm.write(f"   ⚡ Incremental analysis: {len(new_activity_ids)} new routes")
                new_routes = [r for r in routes if r.activity_id in new_activity_ids]
                cached_groups = self._deserialize_groups(self.groups_cache['groups'])
                
                # Merge new routes into existing groups
                updated_groups = self._merge_new_routes(cached_groups, new_routes)
                
                # Save updated cache
                all_activity_ids = list(current_activity_ids)
                self._save_groups_cache_with_ids(all_activity_ids, updated_groups)
                self._save_similarity_cache()
                
                return updated_groups
            
            else:
                # Routes removed or config changed - full reanalysis needed
                if removed_activity_ids:
                    removed_pct = (len(removed_activity_ids) / len(cached_activity_ids) * 100
                                   if cached_activity_ids else 0)
                    msg = (f"Full reanalysis: {len(removed_activity_ids)} of "
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
                    tqdm.write(f"   🔄 Full reanalysis: {len(removed_activity_ids)} routes removed")
                else:
                    tqdm.write("   🔄 Full reanalysis: configuration changed")
        
        # Full analysis (no cache or force reanalysis)
        tqdm.write(f"   🔄 Full analysis: {len(routes)} routes")
        
        # Separate by direction
        home_to_work = [r for r in routes if r.direction == 'home_to_work']
        work_to_home = [r for r in routes if r.direction == 'work_to_home']

        groups = []
        grand_total = len(home_to_work) + len(work_to_home)

        # Parallelise the inner comparison loop across n_workers processes.
        # The outer (pivot) loop remains sequential because each iteration
        # depends on which routes the previous one removed.
        # With a single worker a pool would only fork one extra copy of the
        # numpy stack for zero parallelism (a real cost on the Pi), so run
        # the sequential path instead.
        self._executor = (ProcessPoolExecutor(max_workers=self.n_workers)
                          if self.n_workers > 1 else None)
        try:
            if home_to_work:
                tqdm.write(f"   → Processing {len(home_to_work)} home→work routes "
                           f"({self.n_workers} workers)")
                htw_groups = self._group_routes_by_similarity(
                    home_to_work, 'home_to_work',
                    offset=0, total=grand_total, executor=self._executor)
                groups.extend(htw_groups)
                tqdm.write(f"   ✓ {len(htw_groups)} groups")

            if work_to_home:
                tqdm.write(f"   → Processing {len(work_to_home)} work→home routes "
                           f"({self.n_workers} workers)")
                wth_groups = self._group_routes_by_similarity(
                    work_to_home, 'work_to_home',
                    offset=len(home_to_work), total=grand_total, executor=self._executor)
                groups.extend(wth_groups)
                tqdm.write(f"   ✓ {len(wth_groups)} groups")
        finally:
            if self._executor is not None:
                self._executor.shutdown(wait=False, cancel_futures=True)
                self._executor = None

        tqdm.write(f"   Total: {len(groups)} groups")
        logger.info(f"Created {len(groups)} route groups from {len(routes)} routes")
        
        # Mark plus routes (routes >15% longer than median)
        groups = self._mark_plus_routes(groups)
        
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
    
    def _merge_new_routes(self, existing_groups: List[RouteGroup],
                         new_routes: List[Route]) -> List[RouteGroup]:
        """
        Merge new routes into existing groups incrementally.
        
        Args:
            existing_groups: Existing route groups from cache
            new_routes: New routes to merge
            
        Returns:
            Updated list of route groups
        """
        if not new_routes:
            return existing_groups
        
        tqdm.write(f"   → Merging {len(new_routes)} new routes into {len(existing_groups)} groups")
        
        # Separate new routes by direction
        new_htw = [r for r in new_routes if r.direction == 'home_to_work']
        new_wth = [r for r in new_routes if r.direction == 'work_to_home']
        
        # Separate existing groups by direction
        htw_groups = [g for g in existing_groups if g.direction == 'home_to_work']
        wth_groups = [g for g in existing_groups if g.direction == 'work_to_home']
        
        # Merge each direction
        updated_groups = []
        
        if new_htw:
            updated_htw = self._merge_routes_into_groups(htw_groups, new_htw, 'home_to_work')
            updated_groups.extend(updated_htw)
            tqdm.write(f"   ✓ Merged into {len(updated_htw)} home→work groups")
        else:
            updated_groups.extend(htw_groups)
        
        if new_wth:
            updated_wth = self._merge_routes_into_groups(wth_groups, new_wth, 'work_to_home')
            updated_groups.extend(updated_wth)
            tqdm.write(f"   ✓ Merged into {len(updated_wth)} work→home groups")
        else:
            updated_groups.extend(wth_groups)
        
        # Re-mark plus routes after merge
        updated_groups = self._mark_plus_routes(updated_groups)
        
        return updated_groups
    
    def _merge_routes_into_groups(self, groups: List[RouteGroup],
                                  new_routes: List[Route],
                                  direction: str) -> List[RouteGroup]:
        """
        Merge new routes into existing groups for a specific direction.
        
        Args:
            groups: Existing route groups
            new_routes: New routes to merge
            direction: Route direction
            
        Returns:
            Updated list of route groups
        """
        if not new_routes:
            return groups
        
        # Try to match each new route to existing groups
        unmatched_routes = []
        
        for route in new_routes:
            matched = False
            best_similarity = 0
            best_group_idx = -1
            
            # Find best matching group
            for idx, group in enumerate(groups):
                if not self._passes_geometric_filter(route, group.representative_route):
                    continue
                similarity = self.calculate_route_similarity(
                    route, group.representative_route
                )
                if similarity >= self.similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_group_idx = idx
                    matched = True
            
            if matched:
                # Add to existing group
                groups[best_group_idx].routes.append(route)
                groups[best_group_idx].frequency += 1
                # Update representative if needed (keep median)
                groups[best_group_idx].representative_route = self._select_representative_route(
                    groups[best_group_idx].routes
                )
            else:
                unmatched_routes.append(route)
        
        # Create new groups for unmatched routes
        if unmatched_routes:
            new_groups = self._group_routes_by_similarity(unmatched_routes, direction)
            # Renumber new group IDs to avoid conflicts
            next_id = len(groups)
            for group in new_groups:
                group.id = f"{direction}_{next_id}"
                next_id += 1
            groups.extend(new_groups)
        
        # Re-sort by frequency
        groups.sort(key=lambda g: g.frequency, reverse=True)
        
        return groups
    
    def _mark_plus_routes(self, groups: List[RouteGroup]) -> List[RouteGroup]:
        """
        Mark route groups that are significantly longer than typical commutes.
        
        A "plus route" is one where the distance is >15% above the median distance
        for that direction (home_to_work or work_to_home).
        
        Args:
            groups: List of route groups
            
        Returns:
            Updated list of route groups with is_plus_route flag set
        """
        if not groups:
            return groups
        
        # Separate by direction
        htw_groups = [g for g in groups if g.direction == 'home_to_work']
        wth_groups = [g for g in groups if g.direction == 'work_to_home']
        
        # Calculate median distance for each direction
        for direction_groups in [htw_groups, wth_groups]:
            if not direction_groups:
                continue
            
            # Get all distances
            distances = []
            for group in direction_groups:
                for route in group.routes:
                    distances.append(route.distance)
            
            if not distances:
                continue
            
            # Calculate median
            median_distance = np.median(distances)
            threshold = median_distance * 1.15  # 15% above median
            
            direction = direction_groups[0].direction
            direction_label = direction.replace('_', '→')
            
            # Mark groups where representative route exceeds threshold
            plus_count = 0
            for group in direction_groups:
                if group.representative_route.distance > threshold:
                    group.is_plus_route = True
                    # Also mark individual routes
                    for route in group.routes:
                        if route.distance > threshold:
                            route.is_plus_route = True
                    plus_count += 1
            
            if plus_count > 0:
                tqdm.write(f"   ⭐ {plus_count} {direction_label} PLUS routes")
                tqdm.write(f"      (>{median_distance/1000:.1f}km + 15%)")

        return groups

    def _submit_similarity_tasks(self, task_args: List[Tuple]) -> List[Tuple[int, str, float]]:
        """Submit a batch of _similarity_worker tasks to self._executor and collect results.

        Raises BrokenProcessPool if a worker dies outright instead of returning normally.
        """
        futures = [self._executor.submit(_similarity_worker, args) for args in task_args]
        results = []
        for fut in futures:
            results.extend(fut.result())
        return results

    def _group_routes_by_similarity(self, routes: List[Route], direction: str,
                                    offset: int = 0, total: int = 0,
                                    executor: Optional[Any] = None) -> List[RouteGroup]:
        """
        Group routes by similarity using threshold-based clustering.
        Route naming is deferred to background thread for performance.

        The outer loop is sequential (each pivot depends on prior removals).
        The inner comparison loop is parallelised via the provided executor:
        uncached pairs are split into n_workers chunks and dispatched as a
        single round-trip per pivot, then results are merged back into the
        instance similarity cache.

        Args:
            routes:    Routes to group.
            direction: Route direction label.
            offset:    Routes already consumed in previous direction (for progress).
            total:     Grand total across both directions (for progress percentage).
            executor:  ProcessPoolExecutor to use for parallel comparisons, or None
                       to run sequentially.
        """
        debug_logger = SecureLogger('debug')

        if not routes:
            return []

        n = len(routes)
        debug_logger.info(f"Starting similarity grouping for {n} {direction} routes")

        # Upper-bound on comparisons (worst case: no grouping occurs)
        comparisons_estimated = n * (n - 1) // 2
        hausdorff_percentile = self.config.get('route_analysis.outlier_tolerance_percentile', 95.0)

        groups = []
        ungrouped = routes.copy()
        group_id = 0
        total_comparisons = 0
        routes_consumed = 0
        grand_total = total or n

        # Minimum uncached candidates per pivot to bother parallelising.
        # Below this the IPC round-trip cost exceeds the compute savings.
        MIN_PARALLEL = 8
        total_filtered = 0

        while ungrouped:
            current = ungrouped.pop(0)
            group = [current]
            routes_consumed += 1

            # ---- Separate cached from uncached candidates ----
            cached_similarities: Dict[int, float] = {}
            uncached: List[Tuple[int, str, List]] = []  # (idx, cache_key, coords)
            skipped_by_filter = 0

            for i, route in enumerate(ungrouped):
                cache_key = self._get_cache_key(current, route)
                if cache_key in self.similarity_cache:
                    cached_similarities[i] = self.similarity_cache[cache_key]
                elif not self._passes_geometric_filter(current, route):
                    self.similarity_cache[cache_key] = 0.0
                    cached_similarities[i] = 0.0
                    skipped_by_filter += 1
                    total_filtered += 1
                else:
                    uncached.append((i, cache_key, route.coordinates))

            # ---- Dispatch uncached comparisons ----
            if executor is not None and len(uncached) >= MIN_PARALLEL:
                # Split into n_workers chunks for a single round-trip per pivot
                chunk_size = max(1, len(uncached) // self.n_workers)
                chunks = [uncached[j:j + chunk_size]
                          for j in range(0, len(uncached), chunk_size)]
                pivot_coords = list(current.coordinates)
                task_args = [
                    (pivot_coords, chunk, FRECHET_AVAILABLE, hausdorff_percentile)
                    for chunk in chunks
                ]
                try:
                    results = self._submit_similarity_tasks(task_args)
                except BrokenProcessPool:
                    # A worker died outright (segfault/OOM/killed) rather than raising
                    # a normal exception. Restart the pool once and retry this pivot's
                    # comparisons — if it dies again, let the exception propagate.
                    debug_logger.warning(
                        "Worker process died mid-comparison; restarting the pool "
                        "and retrying this pivot once."
                    )
                    self._executor.shutdown(wait=False, cancel_futures=True)
                    self._executor = ProcessPoolExecutor(max_workers=self.n_workers)
                    results = self._submit_similarity_tasks(task_args)
                for (idx, ck, score) in results:
                    self.similarity_cache[ck] = score
                    cached_similarities[idx] = score
            else:
                # Sequential fallback (small batches or no executor)
                for (i, cache_key, _) in uncached:
                    score = self.calculate_route_similarity(current, ungrouped[i])
                    cached_similarities[i] = score

            total_comparisons += len(ungrouped)

            # ---- Find matches ----
            to_remove = []
            for i, similarity in cached_similarities.items():
                if similarity >= self.similarity_threshold:
                    group.append(ungrouped[i])
                    to_remove.append(i)

            for i in reversed(sorted(to_remove)):
                ungrouped.pop(i)

            debug_logger.info(
                f"Group {group_id}: {len(group)} routes, "
                f"{len(ungrouped)} remaining, {total_comparisons} total comparisons"
                + (f" ({skipped_by_filter} skipped by geo filter)" if skipped_by_filter else "")
            )

            # ---- Emit progress ----
            if self.progress_callback:
                try:
                    self.progress_callback(
                        offset + routes_consumed, grand_total, direction,
                        total_comparisons, comparisons_estimated,
                    )
                except Exception:
                    pass

            direction_label = "to Work" if direction == "home_to_work" else "to Home"
            route_group = RouteGroup(
                id=f"{direction}_{group_id}",
                direction=direction,
                routes=group,
                representative_route=self._select_representative_route(group),
                frequency=len(group),
                name=f"Route {group_id} {direction_label}",
            )
            groups.append(route_group)
            group_id += 1

            if self.stop_check and self.stop_check():
                break

        groups.sort(key=lambda g: g.frequency, reverse=True)

        expensive_comparisons = total_comparisons - total_filtered
        filter_pct = (total_filtered / total_comparisons * 100) if total_comparisons else 0
        debug_logger.info(
            f"Grouping complete for {n} {direction} routes: "
            f"{len(groups)} groups, {total_comparisons} comparisons "
            f"({total_filtered} filtered [{filter_pct:.0f}%], "
            f"{expensive_comparisons} expensive)"
        )

        return groups

    def _select_representative_route(self, routes: List[Route]) -> Route:
        """
        Select representative route from group (median by duration).
        
        Args:
            routes: List of routes in group
            
        Returns:
            Representative Route object
        """
        # Sort by duration
        sorted_routes = sorted(routes, key=lambda r: r.duration)
        
        # Return median route
        median_idx = len(sorted_routes) // 2
        return sorted_routes[median_idx]
    
    def calculate_route_metrics(self, route_group: RouteGroup) -> RouteMetrics:
        """
        Calculate metrics for a route group.
        
        Args:
            route_group: RouteGroup object
            
        Returns:
            RouteMetrics object
        """
        routes = route_group.routes
        
        # Calculate averages
        durations = [r.duration for r in routes]
        distances = [r.distance for r in routes]
        speeds = [r.average_speed for r in routes]
        elevations = [r.elevation_gain for r in routes]
        
        avg_duration = np.mean(durations)
        std_duration = np.std(durations)
        avg_distance = np.mean(distances)
        avg_speed = np.mean(speeds)
        avg_elevation = np.mean(elevations)
        
        # Calculate consistency score (1 - coefficient of variation)
        if avg_duration > 0:
            cv = std_duration / avg_duration
            consistency_score = max(0, 1 - cv)
        else:
            consistency_score = 0
        
        return RouteMetrics(
            avg_duration=avg_duration,
            std_duration=std_duration,
            avg_distance=avg_distance,
            avg_speed=avg_speed,
            avg_elevation=avg_elevation,
            consistency_score=consistency_score,
            usage_frequency=len(routes)
        )
    
    def get_route_statistics(self, route_group: RouteGroup) -> Dict[str, Any]:
        """
        Get detailed statistics for a route group.
        
        Args:
            route_group: RouteGroup object
            
        Returns:
            Dictionary of statistics
        """
        metrics = self.calculate_route_metrics(route_group)
        
        return {
            'id': route_group.id,
            'direction': route_group.direction,
            'frequency': route_group.frequency,
            'avg_duration_min': metrics.avg_duration / 60,
            'std_duration_min': metrics.std_duration / 60,
            'avg_distance_km': metrics.avg_distance / 1000,
            'avg_speed_kmh': metrics.avg_speed * 3.6,
            'avg_elevation_m': metrics.avg_elevation,
            'consistency_score': metrics.consistency_score
        }
    
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
        if self.interactive:
            tqdm.write("  A new terminal window will open to show progress.\n")
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
        """
        from collections import defaultdict

        # Build name → [group] map
        by_name: Dict[str, List[RouteGroup]] = defaultdict(list)
        for g in all_groups_for_direction:
            if g.name:
                by_name[g.name].append(g)

        for name, clashing in by_name.items():
            if len(clashing) <= 1:
                continue

            # ---- Pass 1: terrain disambiguation ----
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

            terrain_labels = [_terrain_label(g) for g in clashing]
            if len(set(terrain_labels)) > 1:
                for g, label in zip(clashing, terrain_labels):
                    g.name = f"{name} — {label}"
                continue

            # ---- Pass 2: distance bracket disambiguation ----
            distances = [g.representative_route.distance or 0 for g in clashing]
            median_dist = sorted(distances)[len(distances) // 2]

            if len(set(distances)) > 1:
                def _dist_label(d: float) -> str:
                    return 'short' if d < median_dist else 'long'

                dist_labels = [_dist_label(d) for d in distances]
                if len(set(dist_labels)) > 1:
                    for g, label in zip(clashing, dist_labels):
                        g.name = f"{name} — {label}"
                    continue

            # ---- Pass 3: ordinal fallback ----
            # Keep the first group's name intact; suffix the rest
            for idx, g in enumerate(clashing[1:], start=2):
                g.name = f"{name} #{idx}"

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

