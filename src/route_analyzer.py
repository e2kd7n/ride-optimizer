"""
Route analysis module.

Extracts, groups, and analyzes route variants between home and work.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
import json
import hashlib
import threading
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, asdict

import numpy as np
from scipy.spatial.distance import directed_hausdorff
from geopy.distance import geodesic
import polyline
from tqdm import tqdm

from .data_fetcher import Activity
from .location_finder import Location
from .route_namer import RouteNamer

logger = logging.getLogger(__name__)

try:
    import similaritymeasures
    FRECHET_AVAILABLE = True
except ImportError:
    FRECHET_AVAILABLE = False
    logger.warning("similaritymeasures not available, using Hausdorff distance only")


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
                 work: Location, config, n_workers=2, force_reanalysis=False):
        """
        Initialize route analyzer.
        
        Args:
            activities: List of Activity objects
            home: Home location
            work: Work location
            config: Configuration object
            n_workers: Number of parallel workers for route grouping (1-8)
            force_reanalysis: If True, clear cache and reprocess all routes
        """
        self.activities = activities
        self.home = home
        self.work = work
        self.config = config
        self.n_workers = max(1, min(8, n_workers))  # Clamp between 1 and 8
        self.similarity_threshold = config.get('route_analysis.similarity_threshold', 0.85)
        self.route_namer = RouteNamer(config)
        self.force_reanalysis = force_reanalysis
        
        # Initialize caches
        self.cache_dir = Path('cache')
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
    
    def _save_groups_cache(self, cache_key: str, groups: List[RouteGroup]):
        """Save route groups cache to disk (legacy method)."""
        # Extract activity IDs from groups
        activity_ids = []
        for group in groups:
            for route in group.routes:
                if route.activity_id not in activity_ids:
                    activity_ids.append(route.activity_id)
        self._save_groups_cache_with_ids(activity_ids, groups)
    
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
                        'is_plus_route': group.representative_route.is_plus_route
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
                            'is_plus_route': r.is_plus_route
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
            logger.info(f"Saved {len(groups)} route groups to cache ({len(activity_ids)} activities)")
        except Exception as e:
            logger.warning(f"Failed to save groups cache: {e}")
    
    def _deserialize_groups(self, serialized_groups: List[Dict]) -> List[RouteGroup]:
        """Deserialize route groups from JSON format."""
        groups = []
        for sg in serialized_groups:
            # Deserialize representative route
            rep_data = sg['representative_route']
            representative = Route(
                activity_id=rep_data['activity_id'],
                direction=rep_data['direction'],
                coordinates=[(lat, lon) for lat, lon in rep_data['coordinates']],
                distance=rep_data['distance'],
                duration=rep_data['duration'],
                elevation_gain=rep_data['elevation_gain'],
                timestamp=rep_data['timestamp'],
                average_speed=rep_data['average_speed'],
                is_plus_route=rep_data['is_plus_route']
            )
            
            # Deserialize routes
            routes = []
            for r_data in sg['routes']:
                route = Route(
                    activity_id=r_data['activity_id'],
                    direction=r_data['direction'],
                    coordinates=[(lat, lon) for lat, lon in r_data['coordinates']],
                    distance=r_data['distance'],
                    duration=r_data['duration'],
                    elevation_gain=r_data['elevation_gain'],
                    timestamp=r_data['timestamp'],
                    average_speed=r_data['average_speed'],
                    is_plus_route=r_data['is_plus_route']
                )
                routes.append(route)
            
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
        from scipy.spatial.distance import cdist
        
        # Get percentile from config (default 95.0 = ignore worst 5% of deviations)
        percentile = self.config.get('route_analysis.outlier_tolerance_percentile', 95.0)
        
        # Distance from each point in coords1 to nearest point in coords2
        distances_1_to_2 = cdist(coords1, coords2).min(axis=1)
        
        # Distance from each point in coords2 to nearest point in coords1
        distances_2_to_1 = cdist(coords2, coords1).min(axis=1)
        
        # Use percentile instead of max to tolerate outliers
        percentile_dist_1 = np.percentile(distances_1_to_2, percentile)
        percentile_dist_2 = np.percentile(distances_2_to_1, percentile)
        
        # Take the larger of the two percentile distances
        percentile_dist = max(percentile_dist_1, percentile_dist_2)
        
        # Convert degrees to meters (approximate)
        # At Chicago's latitude (~42°), 1 degree ≈ 111km latitude, ~82km longitude
        # Using 111km as conservative estimate
        normalized_dist = percentile_dist * 111000
        
        # Convert to similarity score (0-1)
        # Routes are considered similar if percentile deviation is within 200m
        distance_threshold = 200  # meters
        similarity = 1 / (1 + normalized_dist / distance_threshold)
        
        return similarity
    
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
            # Calculate Fréchet distance
            # Note: similaritymeasures expects (n, 2) arrays
            frechet_dist = similaritymeasures.frechet_dist(coords1, coords2)
            
            # Convert degrees to meters
            normalized_dist = frechet_dist * 111000
            
            # Convert to similarity score
            # Fréchet distance is typically larger than Hausdorff, so use larger threshold
            distance_threshold = 300  # meters - allow more variation for path-based comparison
            similarity = 1 / (1 + normalized_dist / distance_threshold)
            
            return similarity
            
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
                    tqdm.write(f"   🔄 Full reanalysis: {len(removed_activity_ids)} routes removed")
                else:
                    tqdm.write("   🔄 Full reanalysis: configuration changed")
        
        # Full analysis (no cache or force reanalysis)
        tqdm.write(f"   🔄 Full analysis: {len(routes)} routes")
        
        # Separate by direction
        home_to_work = [r for r in routes if r.direction == 'home_to_work']
        work_to_home = [r for r in routes if r.direction == 'work_to_home']
        
        # Sequential processing (parallel removed - adds overhead without benefit)
        groups = []
        
        if home_to_work:
            tqdm.write(f"   → Processing {len(home_to_work)} home→work routes")
            htw_groups = self._group_routes_by_similarity(home_to_work, 'home_to_work')
            groups.extend(htw_groups)
            tqdm.write(f"   ✓ {len(htw_groups)} groups")
        
        if work_to_home:
            tqdm.write(f"   → Processing {len(work_to_home)} work→home routes")
            wth_groups = self._group_routes_by_similarity(work_to_home, 'work_to_home')
            groups.extend(wth_groups)
            tqdm.write(f"   ✓ {len(wth_groups)} groups")
        
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
        if self.config and self.config.get('route_analysis.enable_geocoding', True):
            self._start_background_geocoding(groups, auto_approve=False)
        
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
    
    def _group_routes_by_similarity(self, routes: List[Route], direction: str) -> List[RouteGroup]:
        """
        Group routes by similarity using threshold-based clustering.
        Route naming is deferred to background thread for performance.
        
        Args:
            routes: List of routes
            direction: Route direction
            
        Returns:
            List of RouteGroup objects (with temporary names)
        """
        # Get debug logger
        debug_logger = logging.getLogger('debug')
        
        if not routes:
            return []
        
        debug_logger.info(f"Starting similarity grouping for {len(routes)} {direction} routes")
        debug_logger.info(f"Similarity threshold: {self.similarity_threshold}")
        
        groups = []
        ungrouped = routes.copy()
        group_id = 0
        total_comparisons = 0
        
        while ungrouped:
            # Start new group with first ungrouped route
            current = ungrouped.pop(0)
            group = [current]
            
            debug_logger.debug(f"Group {group_id}: Starting with route {current.activity_id}, {len(ungrouped)} routes remaining")
            
            # Find similar routes
            to_remove = []
            comparisons_this_group = 0
            for i, route in enumerate(ungrouped):
                similarity = self.calculate_route_similarity(current, route)
                comparisons_this_group += 1
                total_comparisons += 1
                
                if similarity >= self.similarity_threshold:
                    group.append(route)
                    to_remove.append(i)
                    debug_logger.debug(f"  Route {route.activity_id} matched (similarity: {similarity:.3f})")
                
                # Log progress every 50 comparisons
                if comparisons_this_group % 50 == 0:
                    debug_logger.info(f"  Group {group_id}: {comparisons_this_group} comparisons, {len(group)} routes matched so far")
            
            debug_logger.info(f"Group {group_id}: Matched {len(group)} routes after {comparisons_this_group} comparisons")
            
            # Remove grouped routes
            for i in reversed(to_remove):
                ungrouped.pop(i)
            
            # Create route group
            representative = self._select_representative_route(group)
            
            # Generate route ID
            route_id = f"{direction}_{group_id}"
            
            debug_logger.info(f"Created group {route_id} with {len(group)} routes")
            
            # Use simple temporary name (geocoding deferred to background)
            direction_label = "to Work" if direction == "home_to_work" else "to Home"
            route_name = f"Route {group_id} {direction_label}"
            
            route_group = RouteGroup(
                id=route_id,
                direction=direction,
                routes=group,
                representative_route=representative,
                frequency=len(group),
                name=route_name
            )
            
            groups.append(route_group)
            group_id += 1
        
        # Sort by frequency
        groups.sort(key=lambda g: g.frequency, reverse=True)
        
        return groups
    
    @staticmethod
    def _group_routes_by_similarity_static(routes: List[Route], direction: str, 
                                          similarity_threshold: float,
                                          similarity_cache: Dict[str, float]) -> List[RouteGroup]:
        """
        Static method for parallel route grouping.
        
        This is a static method so it can be pickled for multiprocessing.
        
        Args:
            routes: List of routes to group
            direction: Route direction
            similarity_threshold: Similarity threshold for grouping
            similarity_cache: Cached similarity calculations
            
        Returns:
            List of RouteGroup objects
        """
        if not routes:
            return []
        
        groups = []
        ungrouped = routes.copy()
        group_id = 0
        
        # Helper function to calculate similarity (simplified for static context)
        def calc_similarity(route1: Route, route2: Route) -> float:
            # Check cache first
            cache_key = f"{route1.activity_id}_{route2.activity_id}"
            if cache_key in similarity_cache:
                return similarity_cache[cache_key]
            
            # Calculate Fréchet distance if available
            coords1 = np.array(route1.coordinates)
            coords2 = np.array(route2.coordinates)
            
            if FRECHET_AVAILABLE:
                try:
                    frechet_dist = similaritymeasures.frechet_dist(coords1, coords2)
                    normalized_dist = frechet_dist * 111000
                    distance_threshold = 200
                    similarity = 1 / (1 + normalized_dist / distance_threshold)
                    return similarity
                except (ValueError, IndexError, TypeError) as e:
                    logger.debug(f"Fréchet distance calculation failed, falling back to Hausdorff: {e}")
                    pass
            
            # Fallback to Hausdorff
            dist_forward = directed_hausdorff(coords1, coords2)[0]
            dist_backward = directed_hausdorff(coords2, coords1)[0]
            max_dist = max(dist_forward, dist_backward)
            normalized_dist = max_dist * 111000
            distance_threshold = 200
            similarity = 1 / (1 + normalized_dist / distance_threshold)
            return similarity
        
        while ungrouped:
            # Start new group with first ungrouped route
            current = ungrouped.pop(0)
            group = [current]
            
            # Find similar routes
            to_remove = []
            for i, route in enumerate(ungrouped):
                similarity = calc_similarity(current, route)
                if similarity >= similarity_threshold:
                    group.append(route)
                    to_remove.append(i)
            
            # Remove grouped routes
            for i in reversed(to_remove):
                ungrouped.pop(i)
            
            # Select representative route (median by duration)
            sorted_routes = sorted(group, key=lambda r: r.duration)
            representative = sorted_routes[len(sorted_routes) // 2]
            
            # Create route group
            route_id = f"{direction}_{group_id}"
            route_name = f"Route {group_id}"
            
            route_group = RouteGroup(
                id=route_id,
                direction=direction,
                routes=group,
                representative_route=representative,
                frequency=len(group),
                name=route_name
            )
            
            groups.append(route_group)
            group_id += 1
        
        # Sort by frequency
        groups.sort(key=lambda g: g.frequency, reverse=True)
        
        return groups
    
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
    
    def _start_background_geocoding(self, groups: List[RouteGroup], auto_approve: bool = False) -> None:
        """
        Start background thread to geocode route names.
        This allows route grouping to complete quickly while geocoding happens in parallel.
        Opens a new terminal window to show geocoding progress.
        
        Args:
            groups: List of RouteGroup objects to geocode
            auto_approve: If True, skip user prompt (for automated runs)
        """
        # Don't start if geocoding is disabled
        if self.config and not self.config.get('route_analysis.enable_geocoding', True):
            logger.info("Geocoding disabled in config, skipping background geocoding")
            return
        
        # Check if we're currently rate limited
        import os
        rate_limit_file = os.path.join(self.cache_dir, "geocoding_rate_limit.json")
        if os.path.exists(rate_limit_file):
            try:
                import json
                from datetime import datetime
                with open(rate_limit_file, 'r') as f:
                    rate_limit_data = json.load(f)
                blocked_until_str = rate_limit_data.get('blocked_until')
                if blocked_until_str:
                    blocked_until = datetime.fromisoformat(blocked_until_str)
                    if datetime.now() < blocked_until:
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
            except Exception as e:
                logger.warning(f"Failed to check rate limit file: {e}")
        
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
        tqdm.write("  A new terminal window will open to show progress.\n")
        
        self._geocoding_thread = threading.Thread(
            target=self._geocode_routes_background,
            args=(groups,),
            daemon=True,
            name="RouteGeocoding"
        )
        self._geocoding_thread.start()
        
        # Open a new terminal window to show progress
        self._open_geocoding_terminal(routes_needing_geocoding)
    
    def _open_geocoding_terminal(self, total_routes: int) -> None:
        """
        Open a new terminal window to show geocoding progress.
        Creates a progress file that the terminal monitors.
        
        Args:
            total_routes: Total number of routes being geocoded
        """
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
                except Exception:
                    pass  # Ignore errors in background thread
            
            # Start in a daemon thread so it doesn't block exit
            terminal_thread = threading.Thread(target=start_terminal, daemon=True)
            terminal_thread.start()
            # Don't wait for the thread - let it run independently
            # The terminal window will remain open for the user to monitor
            
        except Exception as e:
            logger.warning(f"Could not open geocoding terminal: {e}")
            # Not critical, continue anyway
    
    def cleanup(self) -> None:
        """
        Clean up resources including background threads and subprocesses.
        Should be called when the analyzer is no longer needed.
        """
        # Wait for geocoding thread to complete (with timeout)
        if self._geocoding_thread and self._geocoding_thread.is_alive():
            logger.info("Waiting for background geocoding to complete...")
            self._geocoding_thread.join(timeout=5.0)
            if self._geocoding_thread.is_alive():
                logger.warning("Background geocoding still running after timeout")
        
        # Terminal process is detached and managed by the OS
        # No subprocess reference stored, so nothing to clean up
    
    def _geocode_routes_synchronous(self, groups: List[RouteGroup]) -> None:
        """
        Geocode route names synchronously (blocking).
        This ensures names are available before saving cache.
        
        Args:
            groups: List of RouteGroup objects to geocode
        """
        from tqdm import tqdm
        
        # Filter groups that need geocoding (have temporary names)
        groups_to_geocode = [g for g in groups if g.name and ("Route" in g.name and ("to Work" in g.name or "to Home" in g.name))]
        
        if not groups_to_geocode:
            logger.info("All routes already have geocoded names")
            return
        
        logger.info(f"Geocoding {len(groups_to_geocode)} route groups synchronously")
        
        # Geocode with progress bar
        for group in tqdm(groups_to_geocode, desc="Geocoding routes", unit="route"):
            try:
                # Generate descriptive route name using RouteNamer
                route_name = self.route_namer.name_route(
                    group.representative_route.coordinates,
                    group.id,
                    group.direction
                )
                
                # Update the group name
                group.name = route_name
                
            except Exception as e:
                logger.warning(f"Failed to geocode route {group.id}: {e}")
                # Keep the temporary name on failure
        
        logger.info(f"Geocoding complete: {len(groups_to_geocode)} routes named")
    
    def _geocode_routes_background(self, groups: List[RouteGroup]) -> None:
        """
        Background worker that geocodes route names and updates the cache.
        Runs in a separate thread to not block the main analysis.
        Writes progress to a file with timestamps and concise output (2 lines per route).
        
        Args:
            groups: List of RouteGroup objects to geocode
        """
        from datetime import datetime
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
            except:
                pass
            
            geocoded_count = 0
            failed_count = 0
            
            # Phase 1: Geocode routes with concise progress
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"[{timestamp()}] Phase 1/2: Geocoding route names\n")
                    f.write(f"{'-'*70}\n")
            except:
                pass
            
            for i, group in enumerate(groups_to_geocode, 1):
                try:
                    # Generate descriptive route name using RouteNamer
                    route_name = self.route_namer.name_route(
                        group.representative_route.coordinates,
                        group.id,
                        group.direction
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
                                resume_time = datetime.now() + datetime.timedelta(hours=4)
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
            
            # Phase 2: Saving caches
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"\n{'-'*70}\n")
                    f.write(f"[{timestamp()}] Phase 2/4: Saving geocoding cache\n")
                    f.write(f"{'-'*70}\n")
            except:
                pass
            
            self.route_namer._save_cache()
            logger.info("Geocoding cache saved to disk")
            
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"[{timestamp()}] ✓ Geocoding cache saved\n")
            except:
                pass
            
            # Phase 3: Save route groups cache with updated names
            try:
                with open(progress_file, 'a') as f:
                    f.write(f"\n{'-'*70}\n")
                    f.write(f"[{timestamp()}] Phase 3/4: Saving route groups cache with updated names\n")
                    f.write(f"{'-'*70}\n")
            except:
                pass
            
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
            except:
                pass
            
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
            except:
                pass
            
            migration_success = False
            try:
                # Run migration script to copy data to web app directory
                import subprocess
                result = subprocess.run(
                    [sys.executable, 'scripts/migrate_cache_to_json_storage.py'],
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
                    except:
                        pass
                else:
                    logger.warning(f"Migration script failed: {result.stderr}")
                    try:
                        with open(progress_file, 'a') as f:
                            f.write(f"[{timestamp()}] ⚠️  Migration failed (see logs)\n")
                    except:
                        pass
            except Exception as e:
                logger.warning(f"Failed to run migration script: {e}")
                try:
                    with open(progress_file, 'a') as f:
                        f.write(f"[{timestamp()}] ⚠️  Migration error: {str(e)[:50]}\n")
                except:
                    pass
            
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
            except:
                pass
            
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
    def _check_geocoding_status(self, groups: List[RouteGroup]) -> None:
        """
        Check geocoding status and notify user if incomplete.
        
        Args:
            groups: List of route groups to check
        """
        from tqdm import tqdm
        
        # Count routes with generic names
        generic_names = sum(1 for g in groups if g.name and ("Route" in g.name and ("to Work" in g.name or "to Home" in g.name)))
        total_routes = len(groups)
        geocoded_routes = total_routes - generic_names
        
        # Only show status if there are routes with generic names
        if generic_names > 0:
            # Check if geocoding is actually running
            geocoding_running = self._geocoding_thread and self._geocoding_thread.is_alive()
            
            tqdm.write("\n" + "="*60)
            tqdm.write("📍 ROUTE NAMING STATUS")
            tqdm.write("="*60)
            tqdm.write(f"Routes with descriptive names: {geocoded_routes}/{total_routes}")
            tqdm.write(f"Routes with generic names: {generic_names}/{total_routes}")
            
            if geocoding_running:
                # Geocoding is actively running
                if generic_names == total_routes:
                    tqdm.write("\n⚠️  No routes have been geocoded yet.")
                    tqdm.write("   Background geocoding is running in a separate terminal.")
                else:
                    tqdm.write(f"\n⚠️  Geocoding is incomplete ({geocoded_routes}/{total_routes} routes named).")
                    tqdm.write("   Background geocoding is continuing in a separate terminal.")
                
                tqdm.write("\n💡 To see updated route names:")
                tqdm.write("   1. Wait for geocoding to complete (check the geocoding terminal)")
                tqdm.write("   2. Re-run the analysis")
                tqdm.write("   3. The report will then show descriptive route names")
            else:
                # Geocoding is not running (blocked, disabled, or user declined)
                tqdm.write(f"\n⚠️  {generic_names} routes still have generic names.")
                tqdm.write("   Background geocoding was not started (rate limited, disabled, or declined).")
                
                tqdm.write("\n💡 To geocode route names:")
                tqdm.write("   • If rate limited: wait for the block to expire, then re-run analysis")
                tqdm.write("   • If disabled: enable geocoding in config and re-run analysis")
                tqdm.write("   • If declined: re-run analysis and accept the geocoding prompt")
            
            tqdm.write("="*60 + "\n")
    
    
    def wait_for_geocoding(self, timeout: float = None) -> bool:
        """
        Wait for background geocoding to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)
            
        Returns:
            True if geocoding completed, False if timeout
        """
        if not self._geocoding_thread:
            return True
        
        self._geocoding_thread.join(timeout=timeout)
        return not self._geocoding_thread.is_alive()
    
    def is_geocoding_complete(self) -> bool:
        """
        Check if background geocoding is complete.
        
        Returns:
            True if no geocoding thread or thread has finished
        """
        return not self._geocoding_thread or not self._geocoding_thread.is_alive()

# Made with Bob
