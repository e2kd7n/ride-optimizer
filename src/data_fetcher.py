"""
Data fetching module.

Handles retrieving and caching activity data from Strava API.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from stravalib.client import Client
import polyline

from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)


@dataclass
class Activity:
    """Represents a Strava activity."""
    id: int
    name: str
    type: str
    sport_type: Optional[str] = None  # More specific type (e.g., 'GravelRide', 'Ride')
    start_date: Optional[str] = None  # ISO format
    distance: float = 0.0  # meters
    moving_time: int = 0  # seconds
    elapsed_time: int = 0  # seconds
    total_elevation_gain: float = 0.0  # meters
    start_latlng: Optional[tuple] = None
    end_latlng: Optional[tuple] = None
    polyline: Optional[str] = None  # encoded polyline
    average_speed: float = 0.0  # m/s
    max_speed: float = 0.0  # m/s
    gear_id: Optional[str] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[float] = None
    average_watts: Optional[float] = None
    kilojoules: Optional[float] = None
    suffer_score: Optional[int] = None
    achievement_count: int = 0
    pr_count: int = 0
    kudos_count: int = 0

    @classmethod
    def from_strava_activity(cls, activity, use_detailed_polyline=False):
        """
        Create Activity from Strava API activity object.
        
        Args:
            activity: Strava activity object
            use_detailed_polyline: If True, use detailed polyline instead of summary
        """
        # Helper function to convert time to seconds
        def to_seconds(time_obj):
            if time_obj is None:
                return 0
            # Handle both timedelta and Duration objects
            if hasattr(time_obj, 'total_seconds'):
                return int(time_obj.total_seconds())
            elif hasattr(time_obj, 'seconds'):
                return int(time_obj.seconds)
            else:
                # Assume it's already an integer
                return int(time_obj)
        
        # Choose polyline based on parameter
        # Detailed polyline is only available from get_activity() endpoint
        # Summary polyline is available from get_activities() list endpoint
        if use_detailed_polyline and activity.map and hasattr(activity.map, 'polyline'):
            polyline_data = activity.map.polyline
        elif activity.map:
            polyline_data = activity.map.summary_polyline
        else:
            polyline_data = None
        
        def _opt_float(val):
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        def _opt_int(val):
            try:
                return int(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        return cls(
            id=activity.id,
            name=activity.name,
            type=str(activity.type) if activity.type else "Unknown",
            sport_type=str(getattr(activity.sport_type, 'root', activity.sport_type)) if hasattr(activity, 'sport_type') and activity.sport_type else None,
            start_date=activity.start_date.isoformat() if activity.start_date else None,
            distance=float(activity.distance) if activity.distance else 0.0,
            moving_time=to_seconds(activity.moving_time),
            elapsed_time=to_seconds(activity.elapsed_time),
            total_elevation_gain=float(activity.total_elevation_gain) if activity.total_elevation_gain else 0.0,
            start_latlng=tuple(activity.start_latlng) if activity.start_latlng else None,
            end_latlng=tuple(activity.end_latlng) if activity.end_latlng else None,
            polyline=polyline_data,
            average_speed=float(activity.average_speed) if activity.average_speed else 0.0,
            max_speed=float(activity.max_speed) if activity.max_speed else 0.0,
            gear_id=str(getattr(activity, 'gear_id', None)) if getattr(activity, 'gear_id', None) else None,
            average_heartrate=_opt_float(getattr(activity, 'average_heartrate', None)),
            max_heartrate=_opt_float(getattr(activity, 'max_heartrate', None)),
            average_watts=_opt_float(getattr(activity, 'average_watts', None)),
            kilojoules=_opt_float(getattr(activity, 'kilojoules', None)),
            suffer_score=_opt_int(getattr(activity, 'suffer_score', None)),
            achievement_count=_opt_int(getattr(activity, 'achievement_count', None)) or 0,
            pr_count=_opt_int(getattr(activity, 'pr_count', None)) or 0,
            kudos_count=_opt_int(getattr(activity, 'kudos_count', None)) or 0,
        )
    
    @classmethod
    def from_garmin_activity(cls, ga: Dict[str, Any]):
        """Create Activity from a garth activity dict."""
        start_lat = ga.get('startLatitude')
        start_lon = ga.get('startLongitude')
        end_lat = ga.get('endLatitude')
        end_lon = ga.get('endLongitude')

        sport_map = {
            'cycling': 'Ride',
            'road_biking': 'Ride',
            'gravel_cycling': 'GravelRide',
            'mountain_biking': 'Ride',
            'virtual_ride': 'VirtualRide',
            'indoor_cycling': 'VirtualRide',
            'running': 'Run',
            'trail_running': 'Run',
            'walking': 'Walk',
            'hiking': 'Hike',
        }
        raw_type = (ga.get('activityType', {}).get('typeKey', '') or '').lower()
        sport_type = sport_map.get(raw_type, 'Ride')

        return cls(
            id=ga.get('activityId', 0),
            name=ga.get('activityName', 'Garmin Activity'),
            type=sport_type,
            sport_type=sport_type,
            start_date=ga.get('startTimeLocal'),
            distance=ga.get('distance', 0.0),
            moving_time=int(ga.get('movingDuration') or ga.get('duration') or 0),
            elapsed_time=int(ga.get('duration', 0)),
            total_elevation_gain=ga.get('elevationGain', 0.0),
            start_latlng=(start_lat, start_lon) if start_lat and start_lon else None,
            end_latlng=(end_lat, end_lon) if end_lat and end_lon else None,
            polyline=None,
            average_speed=ga.get('averageSpeed', 0.0),
            max_speed=ga.get('maxSpeed', 0.0),
            average_heartrate=ga.get('averageHR'),
            max_heartrate=ga.get('maxHR'),
            average_watts=ga.get('avgPower'),
            kilojoules=None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create Activity from dictionary."""
        # Convert tuples back from lists, handling nested structure from Strava API
        def extract_latlng(latlng_data):
            if not latlng_data:
                return None
            # Handle nested structure: [['root', [lat, lon]]]
            if isinstance(latlng_data, list) and len(latlng_data) > 0:
                if isinstance(latlng_data[0], list) and len(latlng_data[0]) > 1:
                    # Extract from nested structure
                    coords = latlng_data[0][1]
                    if isinstance(coords, list) and len(coords) >= 2:
                        return tuple(coords)
                # Simple list [lat, lon]
                elif len(latlng_data) >= 2 and isinstance(latlng_data[0], (int, float)):
                    return tuple(latlng_data)
            return None
        
        if data.get('start_latlng'):
            data['start_latlng'] = extract_latlng(data['start_latlng'])
        if data.get('end_latlng'):
            data['end_latlng'] = extract_latlng(data['end_latlng'])
        return cls(**data)


class StravaDataFetcher:
    """Fetches and caches activity data from Strava API."""
    
    def __init__(self, client: Client, config, use_test_cache: bool = False):
        """
        Initialize data fetcher.
        
        Args:
            client: Authenticated Strava client
            config: Configuration object
            use_test_cache: If True, use test cache instead of production cache
        """
        self.client = client
        self.config = config
        self.use_test_cache = use_test_cache
        
        # Use separate cache paths for test and production data
        if use_test_cache:
            self.cache_path = Path("data/cache/activities_test.json")
            logger.info("Using TEST cache: data/cache/activities_test.json")
        else:
            self.cache_path = Path("data/cache/activities.json")
        
    def fetch_activities(self, limit: Optional[int] = None,
                        after: Optional[datetime] = None,
                        before: Optional[datetime] = None,
                        use_cache: bool = True,
                        progress_callback=None,
                        merge_cache: bool = False) -> List[Activity]:
        """
        Fetch activities from Strava API.

        Args:
            limit: Maximum number of activities to fetch (default from config or 500)
            after: Only fetch activities after this date
            before: Only fetch activities before this date
            use_cache: If True, check cache first and return cached data if valid (default: True)
            progress_callback: Optional callable(fetched_count) called after each activity

        Returns:
            List of Activity objects
        """
        if limit is None:
            limit = self.config.get('data_fetching.max_activities', 500)
        
        # Check cache first if enabled and no date filters specified
        if use_cache and not after and not before:
            if self.is_cache_valid():
                print("\n" + "="*70)
                print("💾 USING CACHED ACTIVITIES")
                print("="*70)
                cached_activities = self.load_cached_activities()
                cache_age_days = self._get_cache_age_days()
                print(f"Cache age: {cache_age_days:.1f} days")
                print(f"Total activities in cache: {len(cached_activities)}")
                print("="*70 + "\n")
                logger.info(f"Using valid cache with {len(cached_activities)} activities (age: {cache_age_days:.1f} days)")
                return cached_activities
            else:
                if self.cache_path.exists():
                    cache_age_days = self._get_cache_age_days()
                    print("\n" + "="*70)
                    print("⚠️  CACHE EXPIRED")
                    print("="*70)
                    print(f"Cache age: {cache_age_days:.1f} days")
                    print(f"Max cache age: {self.config.get('data_fetching.cache_duration_days', 7)} days")
                    print("Fetching fresh data from Strava...")
                    print("="*70 + "\n")
                    logger.info(f"Cache expired (age: {cache_age_days:.1f} days), fetching from Strava")
        
        # Print fetch parameters
        print("\n" + "="*70)
        print("📥 FETCHING ACTIVITIES FROM STRAVA")
        print("="*70)
        print(f"Max activities to fetch: {limit}")
        if after and before:
            print(f"Date range: {after.date()} to {before.date()}")
        elif after:
            print(f"Fetching activities after: {after.date()}")
        elif before:
            print(f"Fetching activities before: {before.date()}")
        else:
            print("Fetching most recent activities")
        print("="*70 + "\n")
        
        logger.info(f"Fetching up to {limit} activities from Strava...")
        
        activities = []
        earliest_date = None
        latest_date = None
        
        try:
            strava_activities = self.client.get_activities(limit=limit, after=after, before=before)
            
            processed_count = 0
            for activity in strava_activities:
                    try:
                        act = Activity.from_strava_activity(activity)
                        
                        # If before date specified, filter activities (make before timezone-aware for comparison)
                        if before and act.start_date:
                            act_date = datetime.fromisoformat(act.start_date.replace('Z', '+00:00'))
                            # Make before date timezone-aware (UTC) for comparison
                            from datetime import timezone
                            before_aware = before.replace(tzinfo=timezone.utc)
                            if act_date > before_aware:
                                continue  # Skip activities after the before date
                        
                        activities.append(act)
                        processed_count += 1

                        if progress_callback:
                            progress_callback(processed_count)

                        # Show progress every 100 activities
                        if processed_count % 100 == 0:
                            print(f"  Fetched {processed_count} activities so far...")
                        
                        # Track date range
                        if act.start_date:
                            try:
                                act_date = datetime.fromisoformat(act.start_date.replace('Z', '+00:00'))
                                if earliest_date is None or act_date < earliest_date:
                                    earliest_date = act_date
                                if latest_date is None or act_date > latest_date:
                                    latest_date = act_date
                            except (ValueError, AttributeError) as e:
                                logger.debug(f"Failed to parse activity date: {e}")
                                pass
                                
                    except Exception as e:
                        logger.warning(f"Failed to process activity_id={activity.id}: {e}")
                        continue
            
            # Print fetch results
            print(f"✓ Fetched {len(activities)} activities from Strava")
            if earliest_date and latest_date:
                print(f"  Date range: {earliest_date.date()} to {latest_date.date()}")
            print()
            
            logger.info(f"Fetched {len(activities)} activities")

            # Persist to disk so reanalyze-cached-data mode picks up fresh data
            if activities:
                self.cache_activities(activities, merge=merge_cache)

        except Exception as e:
            logger.error(f"Failed to fetch activities: {e}")
            raise

        return activities
    
    def get_activity_details(self, activity_id: int) -> Optional[Activity]:
        """
        Get detailed information for a specific activity.
        
        Args:
            activity_id: Strava activity ID
            
        Returns:
            Activity object or None
        """
        try:
            activity = self.client.get_activity(activity_id)
            return Activity.from_strava_activity(activity, use_detailed_polyline=True)
        except Exception as e:
            logger.error(f"Failed to fetch activity {activity_id}: {e}")
            return None
    
    def enrich_activities_with_detailed_polylines(self, activities: List[Activity]) -> List[Activity]:
        """
        Fetch detailed polylines for activities that only have summary polylines.
        This makes an additional API call per activity, so use sparingly.
        
        Args:
            activities: List of Activity objects with summary polylines
            
        Returns:
            List of Activity objects with detailed polylines
        """
        enriched_activities = []
        
        logger.info(f"Fetching detailed polylines for {len(activities)} activities...")
        
        for i, activity in enumerate(activities):
            try:
                # Fetch detailed activity data
                detailed_activity = self.client.get_activity(activity.id)
                enriched = Activity.from_strava_activity(detailed_activity, use_detailed_polyline=True)
                enriched_activities.append(enriched)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Enriched {i + 1}/{len(activities)} activities")
                    
            except Exception as e:
                logger.warning(f"Failed to enrich activity_id={activity.id}: {e}")
                # Keep original activity if enrichment fails
                enriched_activities.append(activity)
                continue
        
        logger.info(f"Successfully enriched {len(enriched_activities)} activities with detailed polylines")
        return enriched_activities
    
    def cache_activities(self, activities: List[Activity], merge: bool = True) -> dict:
        """
        Save activities to cache file.
        
        Args:
            activities: List of Activity objects to cache
            merge: If True, merge with existing cache (default). If False, replace cache.
            
        Returns:
            Dictionary with cache statistics: {
                'new': int,
                'updated': int,
                'total': int,
                'previous_total': int
            }
        """
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        stats = {
            'new': 0,
            'updated': 0,
            'total': 0,
            'previous_total': 0
        }
        
        if merge and self.cache_path.exists():
            # Load existing cache
            try:
                existing_activities = self.load_cached_activities()
                stats['previous_total'] = len(existing_activities)
                logger.info(f"Loaded {len(existing_activities)} existing activities from cache")
                
                # Create a dict of existing activities by ID for fast lookup
                existing_by_id = {act.id: act for act in existing_activities}
                
                # Add new activities, replacing any duplicates
                for act in activities:
                    if act.id in existing_by_id:
                        stats['updated'] += 1
                    else:
                        stats['new'] += 1
                    existing_by_id[act.id] = act
                
                # Convert back to list and sort by date (newest first)
                merged_activities = list(existing_by_id.values())
                merged_activities.sort(key=lambda x: x.start_date or "", reverse=True)
                
                stats['total'] = len(merged_activities)
                
                print("="*70)
                print("💾 CACHE UPDATE SUMMARY")
                print("="*70)
                print(f"Previous cache size: {stats['previous_total']} activities")
                print(f"New activities added: {stats['new']}")
                print(f"Existing activities updated: {stats['updated']}")
                print(f"Total cache size: {stats['total']} activities")
                print(f"Net change: +{stats['total'] - stats['previous_total']} activities")
                print("="*70 + "\n")
                
                logger.info(f"Merged cache: {stats['new']} new, {stats['updated']} updated, {stats['total']} total")
                activities = merged_activities
                
            except Exception as e:
                logger.warning(f"Failed to merge with existing cache: {e}. Replacing cache.")
                stats['new'] = len(activities)
                stats['total'] = len(activities)
        else:
            # Not merging or no existing cache
            stats['new'] = len(activities)
            stats['total'] = len(activities)
            
            print("="*70)
            print("💾 CACHE CREATED")
            print("="*70)
            print(f"Total activities cached: {stats['total']}")
            print("="*70 + "\n")
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'count': len(activities),
            'activities': [act.to_dict() for act in activities]
        }
        
        with open(self.cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Cached {len(activities)} activities to {self.cache_path}")
        
        return stats
    
    def load_cached_activities(self) -> List[Activity]:
        """
        Load activities from cache file.
        
        Returns:
            List of Activity objects
        """
        if not self.cache_path.exists():
            logger.warning("No cache file found")
            return []
        
        with open(self.cache_path, 'r') as f:
            cache_data = json.load(f)
        
        activities = [Activity.from_dict(act) for act in cache_data['activities']]
        
        logger.info(f"Loaded {len(activities)} activities from cache")
        logger.info(f"Cache timestamp: {cache_data['timestamp']}")
        
        return activities
    
    def is_cache_valid(self) -> bool:
        """
        Check if cache is still valid based on cache duration.
        
        Returns:
            True if cache is valid, False otherwise
        """
        if not self.cache_path.exists():
            return False
        
        with open(self.cache_path, 'r') as f:
            cache_data = json.load(f)
        
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        cache_duration = timedelta(days=self.config.get('data_fetching.cache_duration_days', 7))
        
        return datetime.now() - cache_time < cache_duration
    
    def _get_cache_age_days(self) -> float:
        """
        Get the age of the cache in days.
        
        Returns:
            Age of cache in days, or 0 if cache doesn't exist
        """
        if not self.cache_path.exists():
            return 0.0
        
        try:
            with open(self.cache_path, 'r') as f:
                cache_data = json.load(f)
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            age = datetime.now() - cache_time
            return age.total_seconds() / 86400  # Convert to days
        except Exception as e:
            logger.warning(f"Failed to get cache age: {e}")
            return 0.0
    
    def filter_commute_activities(self, activities: List[Activity]) -> List[Activity]:
        """
        Filter activities to find potential commutes.
        
        Args:
            activities: List of Activity objects
            
        Returns:
            Filtered list of Activity objects
        """
        min_distance = self.config.get('route_filtering.min_distance_km', 2) * 1000  # Convert to meters
        max_distance = self.config.get('route_filtering.max_distance_km', 30) * 1000
        activity_types = self.config.get('route_filtering.activity_types', ['Ride', 'EBikeRide'])
        exclude_virtual = self.config.get('route_filtering.exclude_virtual', True)
        
        # Commute name patterns
        commute_keywords = ['work', 'commute', 'to work', 'from work', 'home from work']
        
        filtered = []
        
        for activity in activities:
            # Check if activity name contains commute keywords
            activity_name_lower = activity.name.lower() if activity.name else ""
            is_commute_name = any(keyword in activity_name_lower for keyword in commute_keywords)
            
            # If it doesn't have a commute-related name, skip it
            if not is_commute_name:
                continue
            
            # Check activity type (more lenient for commutes)
            if activity.type not in activity_types and 'Ride' not in activity.type:
                continue
            
            # Check distance (use wider range for commutes)
            if activity.distance < min_distance or activity.distance > max_distance:
                continue
            
            # Check for GPS data
            if not activity.start_latlng or not activity.end_latlng:
                continue
            
            # Check for polyline
            if not activity.polyline:
                continue
            
            # Exclude virtual rides
            if exclude_virtual and 'virtual' in activity_name_lower:
                continue
            
            filtered.append(activity)
        
        logger.info(f"Filtered {len(filtered)} potential commute activities from {len(activities)} total")
        
        return filtered
    
    def decode_polyline(self, encoded: str) -> List[tuple]:
        """
        Decode polyline string to list of coordinates.

        Args:
            encoded: Encoded polyline string

        Returns:
            List of (lat, lon) tuples
        """
        return polyline.decode(encoded)

    # ------------------------------------------------------------------
    # Gear (bikes / shoes) — fetched from the athlete profile
    # ------------------------------------------------------------------

    @property
    def _gear_cache_path(self) -> Path:
        return self.cache_path.parent / 'gear.json'

    def fetch_athlete_gear(self) -> Dict[str, Any]:
        """
        Fetch the authenticated athlete's bikes and shoes from Strava and cache.

        Returns:
            Dict with 'bikes' and 'shoes' lists, each item a gear dict.
        """
        try:
            athlete = self.client.get_athlete()
            bikes = []
            for g in (athlete.bikes or []):
                bikes.append({
                    'id': str(g.id),
                    'name': g.name or '',
                    'type': 'bike',
                    'brand_name': getattr(g, 'brand_name', '') or '',
                    'model_name': getattr(g, 'model_name', '') or '',
                    'primary': bool(getattr(g, 'primary', False)),
                    'strava_distance_m': float(g.distance) if g.distance else 0.0,
                })
            shoes = []
            for g in (athlete.shoes or []):
                shoes.append({
                    'id': str(g.id),
                    'name': g.name or '',
                    'type': 'shoe',
                    'brand_name': getattr(g, 'brand_name', '') or '',
                    'model_name': getattr(g, 'model_name', '') or '',
                    'primary': bool(getattr(g, 'primary', False)),
                    'strava_distance_m': float(g.distance) if g.distance else 0.0,
                })
            data = {
                'timestamp': datetime.now().isoformat(),
                'bikes': bikes,
                'shoes': shoes,
            }
            self._gear_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._gear_cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Cached {len(bikes)} bikes and {len(shoes)} shoes")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch athlete gear: {e}")
            raise

    def load_cached_gear(self) -> Optional[Dict[str, Any]]:
        """Load gear from cache. Returns None if cache doesn't exist."""
        if not self._gear_cache_path.exists():
            return None
        try:
            with open(self._gear_cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load gear cache: {e}")
            return None

    def backfill_gear_ids(self, progress_callback=None) -> Dict[str, Any]:
        """
        Patch gear_id on cached activities that are missing it, without a full re-fetch.

        Strava's list endpoint returns gear_id on every SummaryActivity, so we page
        through get_activities() and update only the gear_id field for each matching
        cached activity.  200 activities per API page — no per-activity detail calls.

        Returns:
            Dict with 'updated', 'skipped', 'total_cached' counts.
        """
        if not self.cache_path.exists():
            return {'updated': 0, 'skipped': 0, 'total_cached': 0}

        # Load cache into a mutable dict keyed by activity id
        with open(self.cache_path, 'r') as f:
            cache_data = json.load(f)

        by_id: Dict[int, dict] = {a['id']: a for a in cache_data.get('activities', [])}
        missing_ids = {aid for aid, a in by_id.items() if not a.get('gear_id')}

        if not missing_ids:
            logger.info("All cached activities already have gear_id — nothing to backfill")
            return {'updated': 0, 'skipped': len(by_id), 'total_cached': len(by_id)}

        logger.info(f"Backfilling gear_id for {len(missing_ids)} of {len(by_id)} cached activities")

        updated = 0
        fetched = 0

        try:
            # Page through list endpoint — gear_id is on SummaryActivity
            for activity in self.client.get_activities(limit=len(by_id) + 50):
                fetched += 1
                aid = activity.id
                raw_gear = getattr(activity, 'gear_id', None)
                gear_id = str(raw_gear) if raw_gear else None

                if aid in by_id and not by_id[aid].get('gear_id') and gear_id:
                    by_id[aid]['gear_id'] = gear_id
                    updated += 1

                if progress_callback:
                    progress_callback(fetched, updated)

                # Stop once we've covered all activities in the cache
                if fetched >= len(by_id) + 10:
                    break

        except Exception as e:
            logger.error(f"Backfill failed after {fetched} activities: {e}")
            raise

        # Write updated cache back
        cache_data['activities'] = list(by_id.values())
        cache_data['timestamp'] = datetime.now().isoformat()
        with open(self.cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)

        logger.info(f"Backfill complete: {updated} updated, {fetched} fetched from Strava")
        return {'updated': updated, 'skipped': len(by_id) - updated, 'total_cached': len(by_id)}

