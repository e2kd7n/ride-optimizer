"""
Analysis Service - Core route analysis and data processing.

This service orchestrates the main analysis workflow:
- Fetching activities from Strava
- Analyzing routes and grouping similar routes
- Processing long rides
- Managing data freshness and caching
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from src.data_fetcher import StravaDataFetcher, Activity
from src.route_analyzer import RouteAnalyzer, RouteGroup
from src.long_ride_analyzer import LongRideAnalyzer, LongRide
from src.location_finder import LocationFinder, Location
from src.config import Config
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Service for core route analysis and data processing.
    
    This service provides a clean interface for:
    - Running full analysis (fetch + analyze)
    - Getting analysis status and freshness
    - Accessing analyzed data (route groups, long rides)
    - Managing cache and data lifecycle
    """
    
    def __init__(self, config: Config, weather_service: Optional['WeatherService'] = None):
        """
        Initialize analysis service.

        Args:
            config: Configuration object
            weather_service: Optional pre-built WeatherService instance for dependency injection
        """
        self.config = config

        # Initialize JSON storage
        from src.json_storage import JSONStorage
        self.storage = JSONStorage()
        self._cache_loaded = False

        # Lazy initialization - don't authenticate until needed
        self._strava_client = None
        self._data_fetcher = None

        # Cached analysis results
        self._activities: Optional[List[Activity]] = None
        self._route_groups: Optional[List[RouteGroup]] = None
        self._long_rides: Optional[List[LongRide]] = None
        self._home_location: Optional[Location] = None
        self._work_location: Optional[Location] = None
        self._last_analysis_time: Optional[datetime] = None
        self.weather_service = weather_service or WeatherService(config)
    
    def _ensure_authenticated(self):
        """
        Ensure Strava client is authenticated (lazy initialization).
        
        This method is called only when we need to fetch fresh data from Strava.
        For read-only operations on cached data, authentication is not required.
        
        Returns:
            Authenticated Strava client
            
        Raises:
            ValueError: If authentication fails
        """
        if self._strava_client is None:
            from src.auth_secure import get_authenticated_client
            logger.info("Authenticating with Strava (lazy initialization)...")
            self._strava_client = get_authenticated_client(self.config)
            self._data_fetcher = StravaDataFetcher(self._strava_client, self.config)
            logger.info("Authentication successful")
        
        return self._strava_client
    
    @property
    def data_fetcher(self):
        """Get data fetcher, ensuring authentication first."""
        if self._data_fetcher is None:
            self._ensure_authenticated()
        return self._data_fetcher
    
    def _load_from_cache(self):
        """
        Load analysis results from JSON cache.
        
        This allows the service to serve cached data without requiring
        Strava authentication. Called automatically on first data access.
        """
        if self._cache_loaded:
            return
        
        logger.info("Loading analysis data from cache...")
        
        try:
            # Load analysis status
            status_data = self.storage.read('analysis_status.json', default={})
            
            if status_data.get('last_analysis'):
                self._last_analysis_time = datetime.fromisoformat(status_data['last_analysis'])
            
            # Load route groups
            routes_data = self.storage.read('route_groups.json', default={})
            if routes_data.get('route_groups'):
                try:
                    self._route_groups = [
                        self._deserialize_route_group(rg)
                        for rg in routes_data['route_groups']
                    ]
                    logger.info(f"Loaded {len(self._route_groups)} route groups from cache")
                except Exception as deser_err:
                    logger.warning(f"Could not deserialize route groups (stale format?): {deser_err}")
                    self._route_groups = routes_data['route_groups']
                
                # Extract home and work locations from route groups metadata
                if routes_data.get('home_location'):
                    home_data = routes_data['home_location']
                    self._home_location = Location(
                        lat=home_data['lat'],
                        lon=home_data['lon'],
                        name=home_data.get('name', 'Home'),
                        activity_count=home_data.get('activity_count', 0)
                    )
                    logger.info(f"Loaded home location: {self._home_location.name}")
                
                if routes_data.get('work_location'):
                    work_data = routes_data['work_location']
                    self._work_location = Location(
                        lat=work_data['lat'],
                        lon=work_data['lon'],
                        name=work_data.get('name', 'Work'),
                        activity_count=work_data.get('activity_count', 0)
                    )
                    logger.info(f"Loaded work location: {self._work_location.name}")
            
            # Load long rides
            long_rides_data = self.storage.read('long_rides.json', default={})
            if long_rides_data.get('long_rides'):
                try:
                    self._long_rides = [
                        self._deserialize_long_ride(lr)
                        for lr in long_rides_data['long_rides']
                    ]
                    logger.info(f"Loaded {len(self._long_rides)} long rides from cache")
                except Exception as deser_err:
                    logger.warning(f"Could not deserialize long rides (stale format?): {deser_err}")
                    self._long_rides = long_rides_data['long_rides']
            
            # Load activities count (we don't cache full activity objects)
            if status_data.get('activities_count'):
                logger.info(f"Cache contains {status_data['activities_count']} activities")
            
            self._cache_loaded = True
            logger.info("Cache loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self._cache_loaded = True  # Mark as loaded to avoid retry loops
    
    def _save_to_cache(self):
        """
        Save analysis results to JSON cache.
        
        Called after successful analysis to persist results for offline access.
        """
        logger.info("Saving analysis results to cache...")
        
        try:
            # Save analysis status
            status_data = {
                'last_analysis': self._last_analysis_time.isoformat() if self._last_analysis_time else None,
                'activities_count': len(self._activities) if self._activities else 0,
                'route_groups_count': len(self._route_groups) if self._route_groups else 0,
                'long_rides_count': len(self._long_rides) if self._long_rides else 0,
                'has_data': bool(self._activities and self._route_groups)
            }
            self.storage.write('analysis_status.json', status_data)
            
            # Save route groups with locations
            if self._route_groups:
                routes_data = {
                    'route_groups': [self._serialize_route_group(rg) for rg in self._route_groups],
                    'updated_at': datetime.now().isoformat()
                }
                
                # Add home and work locations to route groups cache
                if self._home_location:
                    routes_data['home_location'] = {
                        'lat': self._home_location.lat,
                        'lon': self._home_location.lon,
                        'name': self._home_location.name,
                        'activity_count': self._home_location.activity_count
                    }
                
                if self._work_location:
                    routes_data['work_location'] = {
                        'lat': self._work_location.lat,
                        'lon': self._work_location.lon,
                        'name': self._work_location.name,
                        'activity_count': self._work_location.activity_count
                    }
                
                self.storage.write('route_groups.json', routes_data)
            
            # Save long rides
            if self._long_rides:
                long_rides_data = {
                    'long_rides': [self._serialize_long_ride(lr) for lr in self._long_rides],
                    'updated_at': datetime.now().isoformat()
                }
                self.storage.write('long_rides.json', long_rides_data)
            
            logger.info("Cache saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}", exc_info=True)
    
    def _serialize_route(self, route) -> Dict[str, Any]:
        """Serialize a Route object to a JSON-compatible dict."""
        return {
            'activity_id': route.activity_id,
            'direction': route.direction,
            'coordinates': route.coordinates,
            'distance': route.distance,
            'duration': route.duration,
            'elevation_gain': route.elevation_gain,
            'timestamp': route.timestamp,
            'average_speed': route.average_speed,
            'activity_name': getattr(route, 'activity_name', ''),
            'is_plus_route': getattr(route, 'is_plus_route', False),
        }

    def _serialize_route_group(self, route_group: RouteGroup) -> Dict[str, Any]:
        """Serialize RouteGroup to JSON-compatible dict."""
        return {
            'id': route_group.id,
            'direction': route_group.direction,
            'routes': [self._serialize_route(r) for r in route_group.routes],
            'representative_route': self._serialize_route(route_group.representative_route),
            'frequency': route_group.frequency,
            'name': route_group.name,
            'is_plus_route': getattr(route_group, 'is_plus_route', False),
            'difficulty': getattr(route_group, 'difficulty', 'Easy'),
        }

    def _deserialize_route(self, data: Dict[str, Any]):
        """Deserialize a Route from a dict."""
        from src.route_analyzer import Route
        return Route(
            activity_id=data['activity_id'],
            direction=data['direction'],
            coordinates=[tuple(c) for c in data.get('coordinates', [])],
            distance=data['distance'],
            duration=data['duration'],
            elevation_gain=data['elevation_gain'],
            timestamp=data['timestamp'],
            average_speed=data['average_speed'],
            activity_name=data.get('activity_name', ''),
            is_plus_route=data.get('is_plus_route', False),
        )

    def _deserialize_route_group(self, data: Dict[str, Any]):
        """Deserialize a RouteGroup from a dict."""
        routes = [self._deserialize_route(r) for r in data.get('routes', [])]
        rep = self._deserialize_route(data['representative_route'])
        return RouteGroup(
            id=data['id'],
            direction=data['direction'],
            routes=routes,
            representative_route=rep,
            frequency=data['frequency'],
            name=data.get('name'),
            is_plus_route=data.get('is_plus_route', False),
            difficulty=data.get('difficulty', 'Easy'),
        )

    def _serialize_long_ride(self, long_ride: LongRide) -> Dict[str, Any]:
        """Serialize LongRide to JSON-compatible dict."""
        return {
            'activity_id': long_ride.activity_id,
            'name': long_ride.name,
            'coordinates': long_ride.coordinates,
            'distance': long_ride.distance,
            'duration': long_ride.duration,
            'elevation_gain': long_ride.elevation_gain,
            'timestamp': long_ride.timestamp,
            'average_speed': long_ride.average_speed,
            'start_location': list(long_ride.start_location),
            'end_location': list(long_ride.end_location),
            'is_loop': long_ride.is_loop,
            'type': long_ride.type,
            'uses': getattr(long_ride, 'uses', 1),
            'activity_ids': getattr(long_ride, 'activity_ids', None),
            'activity_dates': getattr(long_ride, 'activity_dates', None),
            'activity_names': getattr(long_ride, 'activity_names', None),
        }

    def _deserialize_long_ride(self, data: Dict[str, Any]):
        """Deserialize a LongRide from a dict."""
        from src.long_ride_analyzer import LongRide as LR
        return LR(
            activity_id=data['activity_id'],
            name=data['name'],
            coordinates=[tuple(c) for c in data.get('coordinates', [])],
            distance=data['distance'],
            duration=data['duration'],
            elevation_gain=data['elevation_gain'],
            timestamp=data['timestamp'],
            average_speed=data['average_speed'],
            start_location=tuple(data['start_location']),
            end_location=tuple(data['end_location']),
            is_loop=data['is_loop'],
            type=data['type'],
            uses=data.get('uses', 1),
            activity_ids=data.get('activity_ids'),
            activity_dates=data.get('activity_dates'),
            activity_names=data.get('activity_names'),
        )
    
    def run_full_analysis(self, force_refresh: bool = False, skip_strava_fetch: bool = False,
                          after: Optional[datetime] = None, before: Optional[datetime] = None,
                          on_progress=None, stop_check=None) -> Dict[str, Any]:
        """
        Run complete analysis workflow.

        Steps:
        1. Fetch activities from Strava (or load from cache)
        2. Find home and work locations
        3. Analyze and group routes
        4. Analyze long rides
        5. Cache results

        Args:
            force_refresh: If True, bypass cache and re-fetch data from Strava
            skip_strava_fetch: If True, load cached activities as-is without any Strava call
            on_progress: Optional callable(**kwargs) for live status updates
            stop_check: Optional callable() → bool; returns True when caller wants early exit
        """
        def _notify(**kwargs):
            if on_progress:
                try:
                    on_progress(**kwargs)
                except Exception:
                    pass

        def _should_stop():
            return stop_check is not None and stop_check()

        logger.info(f"Starting full analysis (force_refresh={force_refresh}, skip_strava_fetch={skip_strava_fetch})")
        errors = []

        try:
            # Step 1: Fetch or load activities
            if skip_strava_fetch:
                _notify(phase='loading', label='Loading cached activities…')
                cache_path = Path('data/cache/activities.json')
                if not cache_path.exists():
                    return {
                        'status': 'error',
                        'message': 'No cached activities found. Use "Fetch new Strava data" to download activities first.',
                        'activities_count': 0,
                        'route_groups_count': 0,
                        'long_rides_count': 0,
                        'analysis_time': datetime.now().isoformat(),
                        'data_freshness': 'unknown',
                        'errors': ['No cached activities'],
                    }
                logger.info("Loading activities from local cache (no Strava auth required)...")
                with open(cache_path) as f:
                    raw = json.load(f)
                    acts = raw['activities'] if isinstance(raw, dict) else raw
                    self._activities = [Activity.from_dict(a) for a in acts]
            else:
                _notify(phase='fetching', fetched=0, label='Connecting to Strava…')
                logger.info("Fetching activities from Strava...")

                def _fetch_cb(count):
                    _notify(phase='fetching', fetched=count,
                            label=f'Fetching from Strava… {count:,} activities so far')

                self._activities = self.data_fetcher.fetch_activities(
                    use_cache=not force_refresh,
                    after=after,
                    before=before,
                    progress_callback=_fetch_cb,
                )
            logger.info(f"Loaded {len(self._activities)} activities")
            
            if not self._activities:
                return {
                    'status': 'error',
                    'message': 'No activities found',
                    'activities_count': 0,
                    'route_groups_count': 0,
                    'long_rides_count': 0,
                    'analysis_time': datetime.now().isoformat(),
                    'data_freshness': 'unknown',
                    'errors': ['No activities available for analysis']
                }

            total = len(self._activities)

            # Preview: best-effort pipeline on first ~10 activities after a live Strava fetch.
            # Gives the user something to look at while the full analysis runs.
            if not skip_strava_fetch:
                preview_n = min(10, total)
                _notify(phase='processing_preview', fetched=total, preview_count=preview_n,
                        label=f'Processing first {preview_n} of {total:,} activities for preview…')
                try:
                    preview_acts = self._activities[:preview_n]
                    lf = LocationFinder(preview_acts, self.config)
                    h, w = lf.identify_home_work()
                    ra = RouteAnalyzer(activities=preview_acts, home=h, work=w,
                                       config=self.config, force_reanalysis=True)
                    ra.group_similar_routes()
                    logger.info(f"Preview analysis complete on {preview_n} activities")
                except Exception as exc:
                    logger.warning(f"Preview analysis skipped ({exc})")
                _notify(preview_ready=True, preview_count=preview_n,
                        label=f'Preview ready — {total:,} activities fetched, '
                              f'processing {total - preview_n:,} more…')

            # Step 2: Find locations (full dataset)
            _notify(phase='processing', fetched=total,
                    label=f'Detecting your home and work locations…')
            logger.info("Finding home and work locations...")
            location_finder = LocationFinder(self._activities, self.config)
            self._home_location, self._work_location = location_finder.identify_home_work()
            logger.info(f"Home: {self._home_location.name}, Work: {self._work_location.name}")

            # Step 3: Analyze routes
            _notify(phase='processing', fetched=total, routes_done=0, routes_total=0,
                    label=f'Grouping {total:,} activities into routes…')
            logger.info("Analyzing and grouping routes...")

            _grouping_start = datetime.now()
            _eta_smoothed = None

            def _route_progress(done, route_total, direction,
                                comparisons_done=0, comparisons_estimated=0):
                nonlocal _eta_smoothed
                elapsed = (datetime.now() - _grouping_start).total_seconds()
                # Base ETA on comparisons (linear in time) rather than routes
                # consumed (front-loaded — first pivot is the most expensive).
                if comparisons_done > 0 and comparisons_estimated > comparisons_done:
                    raw_eta = elapsed / comparisons_done * (comparisons_estimated - comparisons_done)
                elif done > 0 and route_total > done:
                    raw_eta = elapsed / done * (route_total - done)
                else:
                    raw_eta = None
                if raw_eta is not None:
                    alpha = 0.15
                    _eta_smoothed = raw_eta if _eta_smoothed is None else (
                        alpha * raw_eta + (1 - alpha) * _eta_smoothed
                    )
                eta = int(_eta_smoothed) if _eta_smoothed is not None else None
                pct = int(done / route_total * 100) if route_total > 0 else 0
                _notify(
                    phase='grouping',
                    routes_done=done,
                    routes_total=route_total,
                    eta_secs=eta,
                    label=f'Grouping routes… {done}/{route_total} ({pct}%)'
                    + (f' — {eta // 60}m {eta % 60}s remaining' if eta is not None else ''),
                )

            route_analyzer = RouteAnalyzer(
                activities=self._activities,
                home=self._home_location,
                work=self._work_location,
                config=self.config,
                force_reanalysis=force_refresh,
                progress_callback=_route_progress,
                stop_check=stop_check,
            )

            self._route_groups = route_analyzer.group_similar_routes()
            logger.info(f"Found {len(self._route_groups)} route groups")

            if _should_stop():
                return {'status': 'stopped', 'activities_count': total,
                        'route_groups_count': len(self._route_groups),
                        'long_rides_count': 0, 'errors': []}

            # Step 4: Analyze long rides
            _notify(phase='long_rides', fetched=total, label='Analyzing long rides…')
            logger.info("Analyzing long rides...")
            long_ride_analyzer = LongRideAnalyzer(
                activities=self._activities,
                config=self.config
            )

            # Get commute activities from route groups
            commute_activity_ids = set()
            for group in self._route_groups:
                for route in group.routes:
                    commute_activity_ids.add(route.activity_id)

            commute_activities = [
                a for a in self._activities
                if a.id in commute_activity_ids
            ]

            _, long_ride_activities = long_ride_analyzer.classify_activities(commute_activities)

            def _long_ride_progress(**kwargs):
                _notify(phase='long_rides', fetched=total, **kwargs)

            self._long_rides = long_ride_analyzer.group_similar_rides(
                long_ride_activities, on_progress=_long_ride_progress)
            logger.info(f"Found {len(self._long_rides)} unique long rides")

            # Step 5: Update analysis time and persist results
            self._last_analysis_time = datetime.now()
            self._save_to_cache()

            return {
                'status': 'success',
                'message': 'Analysis completed successfully',
                'activities_count': total,
                'route_groups_count': len(self._route_groups),
                'long_rides_count': len(self._long_rides),
                'analysis_time': self._last_analysis_time.isoformat(),
                'data_freshness': 'fresh',
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Analysis failed: {str(e)}',
                'activities_count': len(self._activities) if self._activities else 0,
                'route_groups_count': 0,
                'long_rides_count': 0,
                'analysis_time': datetime.now().isoformat(),
                'data_freshness': 'unknown',
                'errors': [str(e)]
            }
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """
        Get current analysis status without running analysis.
        
        Returns:
            Dictionary with status information:
            {
                'has_data': bool,
                'last_analysis': str | None (ISO format),
                'activities_count': int,
                'route_groups_count': int,
                'long_rides_count': int,
                'data_age_hours': float | None,
                'is_stale': bool
            }
        """
        # Load cached data if not already loaded
        self._load_from_cache()
        
        # Check if we have route groups (primary indicator of data)
        has_data = (self._route_groups is not None and len(self._route_groups) > 0)
        
        data_age_hours = None
        is_stale = True
        
        if self._last_analysis_time:
            age = datetime.now() - self._last_analysis_time
            data_age_hours = age.total_seconds() / 3600
            # Consider data stale after 24 hours
            is_stale = data_age_hours > 24
        
        return {
            'has_data': has_data,
            'last_analysis': self._last_analysis_time.isoformat() if self._last_analysis_time else None,
            'activities_count': len(self._activities) if self._activities else 0,
            'route_groups_count': len(self._route_groups) if self._route_groups else 0,
            'long_rides_count': len(self._long_rides) if self._long_rides else 0,
            'data_age_hours': data_age_hours,
            'is_stale': is_stale
        }
    
    def get_route_groups(self) -> List[RouteGroup]:
        """
        Get analyzed route groups.
        
        Returns:
            List of RouteGroup objects, or empty list if no analysis has been run
        """
        self._load_from_cache()
        return self._route_groups if self._route_groups else []
    
    def get_long_rides(self) -> List[LongRide]:
        """
        Get analyzed long rides.
        
        Returns:
            List of LongRide objects, or empty list if no analysis has been run
        """
        self._load_from_cache()
        return self._long_rides if self._long_rides else []
    
    def get_activities(self) -> List[Activity]:
        """
        Get all activities.
        
        Returns:
            List of Activity objects, or empty list if no data has been fetched
        """
        self._load_from_cache()
        return self._activities if self._activities else []
    
    def get_locations(self) -> Tuple[Optional[Location], Optional[Location]]:
        """
        Get home and work locations.
        
        Returns:
            Tuple of (home_location, work_location), or (None, None) if not found
        """
        self._load_from_cache()
        return (self._home_location, self._work_location)
    
    def generate_dashboard_overview_map(self) -> Optional[str]:
        """
        Generate overview map for dashboard showing activity heatmap and top routes.

        Returns:
            HTML string of the map, or None if data not available
        """
        import folium  # noqa: F811 — lazy import to avoid startup cost on Pi
        # Load cached data if not already loaded
        self._load_from_cache()
        
        # Check if we have the necessary data
        if not self._route_groups:
            logger.warning("Cannot generate dashboard map: missing route groups")
            return None
        
        # If locations not loaded, try to extract from route groups
        if not self._home_location or not self._work_location:
            logger.info("Locations not in cache, extracting from route groups...")
            self._extract_locations_from_routes()
            
            if not self._home_location or not self._work_location:
                logger.warning("Cannot generate dashboard map: unable to determine locations")
                return None
        
        try:
            from src.visualizer import RouteVisualizer
            from types import SimpleNamespace
            
            logger.info("Generating dashboard overview map...")
            
            # Convert dict route groups to objects for visualizer
            route_group_objects = []
            for group in self._route_groups:
                group_obj = SimpleNamespace(**group)
                
                # Ensure representative_route is also an object
                if isinstance(group.get('representative_route'), dict):
                    group_obj.representative_route = SimpleNamespace(**group['representative_route'])
                
                # Create routes list from representative route
                if not hasattr(group_obj, 'routes') or not group_obj.routes:
                    group_obj.routes = [group_obj.representative_route]
                else:
                    # Convert routes to objects if they're dicts
                    group_obj.routes = [
                        SimpleNamespace(**r) if isinstance(r, dict) else r
                        for r in group_obj.routes
                    ]
                
                route_group_objects.append(group_obj)
            
            # Initialize visualizer with object-based route groups
            visualizer = RouteVisualizer(
                route_groups=route_group_objects,
                home=self._home_location,
                work=self._work_location,
                config=self.config
            )
            
            # Create base map
            visualizer.map = visualizer.create_base_map()
            
            # Add heatmap layer showing activity frequency
            visualizer.add_heatmap_layer()
            
            # Add top 5-10 most frequently used routes
            # Sort route groups by frequency
            sorted_groups = sorted(
                route_group_objects,
                key=lambda g: getattr(g, 'frequency', 0),
                reverse=True
            )
            
            # Limit to top 10 routes for dashboard overview
            top_routes = sorted_groups[:10]
            
            # Color scheme: Green for most frequent, Blue for moderate
            for idx, group in enumerate(top_routes):
                if idx < 3:
                    # Top 3: Green (high frequency)
                    color = '#28a745'
                    weight = 4
                elif idx < 6:
                    # Next 3: Blue (moderate frequency)
                    color = '#007bff'
                    weight = 3
                else:
                    # Remaining: Light blue
                    color = '#6c757d'
                    weight = 2
                
                # Generate route name
                direction = getattr(group, 'direction', 'unknown')
                route_name = f"{direction.replace('_', ' ').title()}"
                if hasattr(group, 'name') and group.name:
                    route_name = group.name
                
                visualizer.add_route_layer(
                    route_group=group,
                    color=color,
                    weight=weight,
                    is_optimal=False,
                    route_name=route_name
                )
            
            # Add home and work markers with activity counts
            visualizer.add_location_markers()
            
            # Add layer control for toggling heatmap and routes
            try:
                self._add_dashboard_weather_overlay(visualizer)
                visualizer.add_weather_display()
            except Exception as weather_error:
                logger.warning(f"Dashboard weather overlay unavailable: {weather_error}")
            
            folium.LayerControl().add_to(visualizer.map)
            
            # Get map HTML - use get_root().render() for proper HTML output
            # _repr_html_() returns iframe-based output for Jupyter, which doesn't work in web apps
            map_html = visualizer.map.get_root().render()
            
            logger.info(f"Dashboard map generated with {len(top_routes)} routes")
            return map_html
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard map: {e}", exc_info=True)
            return None
    
    def _extract_locations_from_routes(self):
        """Extract home and work locations from route group coordinates."""
        if not self._route_groups:
            return
        
        try:
            # Find home_to_work and work_to_home routes
            home_coords = []
            work_coords = []
            
            for group in self._route_groups:
                direction = group.get('direction', '')
                rep_route = group.get('representative_route', {})
                coords = rep_route.get('coordinates', [])
                
                if not coords:
                    continue
                
                if direction == 'home_to_work':
                    # First coordinate is home
                    home_coords.append(coords[0])
                    # Last coordinate is work
                    work_coords.append(coords[-1])
                elif direction == 'work_to_home':
                    # First coordinate is work
                    work_coords.append(coords[0])
                    # Last coordinate is home
                    home_coords.append(coords[-1])
            
            # Average the coordinates to get approximate locations
            if home_coords:
                avg_home_lat = sum(c[0] for c in home_coords) / len(home_coords)
                avg_home_lon = sum(c[1] for c in home_coords) / len(home_coords)
                self._home_location = Location(
                    lat=avg_home_lat,
                    lon=avg_home_lon,
                    name='Home',
                    activity_count=len(home_coords)
                )
                logger.info(f"Extracted home location: ({avg_home_lat:.4f}, {avg_home_lon:.4f})")
            
            if work_coords:
                avg_work_lat = sum(c[0] for c in work_coords) / len(work_coords)
                avg_work_lon = sum(c[1] for c in work_coords) / len(work_coords)
                self._work_location = Location(
                    lat=avg_work_lat,
                    lon=avg_work_lon,
                    name='Work',
                    activity_count=len(work_coords)
                )
                logger.info(f"Extracted work location: ({avg_work_lat:.4f}, {avg_work_lon:.4f})")
                
        except Exception as e:
            logger.error(f"Failed to extract locations from routes: {e}", exc_info=True)
    
    def _add_dashboard_weather_overlay(self, visualizer) -> None:
        """Add toggleable current weather plus short-range forecast markers to the dashboard map."""
        import folium
        if not self._home_location or not self._work_location:
            return
        
        weather_layer = folium.FeatureGroup(name='Weather Overlay', show=False)
        forecast_layer = folium.FeatureGroup(name='24-48h Forecast', show=False)
        
        for label, location in (('Home', self._home_location), ('Work', self._work_location)):
            weather = self.weather_service.get_current_weather(
                location.lat,
                location.lon,
                location_name=label
            )
            if weather:
                popup_html = self._create_weather_popup(label, weather)
                folium.Marker(
                    [location.lat, location.lon],
                    popup=folium.Popup(popup_html, max_width=320),
                    tooltip=f"{label}: {weather.get('conditions', 'Weather')}",
                    icon=folium.Icon(
                        color=self._get_weather_color(weather),
                        icon=self._get_weather_icon(weather),
                        prefix='fa'
                    )
                ).add_to(weather_layer)
            
            forecasts = self.weather_service.fetcher.get_hourly_forecast(location.lat, location.lon, hours=48) or []
            for forecast in (forecasts[:1] + forecasts[23:24] + forecasts[47:48]):
                forecast_popup = self._create_forecast_popup(label, forecast)
                folium.CircleMarker(
                    [location.lat, location.lon],
                    radius=8,
                    color=self._get_forecast_color(forecast),
                    fill=True,
                    fillColor=self._get_forecast_color(forecast),
                    fillOpacity=0.55,
                    weight=2,
                    popup=folium.Popup(forecast_popup, max_width=300),
                    tooltip=f"{label} forecast {forecast.get('timestamp', '')[-5:]}"
                ).add_to(forecast_layer)
        
        if weather_layer._children:
            weather_layer.add_to(visualizer.map)
        if forecast_layer._children:
            forecast_layer.add_to(visualizer.map)
    
    def _get_weather_icon(self, weather: Dict[str, Any]) -> str:
        """Return Font Awesome icon name for current conditions."""
        conditions = str(weather.get('conditions', '')).lower()
        precipitation = weather.get('precipitation_mm', weather.get('precipitation', 0)) or 0
        wind_speed = weather.get('wind_speed_kph', 0) or 0
        
        if 'rain' in conditions or precipitation > 0.5:
            return 'cloud-rain'
        if wind_speed >= 25:
            return 'wind'
        if 'cloud' in conditions or 'overcast' in conditions:
            return 'cloud'
        return 'sun'
    
    def _get_weather_color(self, weather: Dict[str, Any]) -> str:
        """Return semantic marker color for cycling conditions."""
        favorability = str(weather.get('cycling_favorability', '')).lower()
        if favorability == 'favorable':
            return 'green'
        if favorability == 'neutral':
            return 'orange'
        if favorability == 'unfavorable':
            return 'red'
        return 'blue'
    
    def _get_forecast_color(self, forecast: Dict[str, Any]) -> str:
        """Color forecast markers by expected favorability."""
        temp_c = forecast.get('temp_c', 20) or 20
        wind_kph = forecast.get('wind_speed_kph', 0) or 0
        precip_prob = forecast.get('precipitation_prob', 0) or 0
        
        if temp_c < 0 or temp_c > 32 or wind_kph > 30 or precip_prob >= 60:
            return '#dc3545'
        if temp_c < 8 or temp_c > 28 or wind_kph > 20 or precip_prob >= 30:
            return '#ffc107'
        return '#28a745'
    
    def _create_weather_popup(self, label: str, weather: Dict[str, Any]) -> str:
        """Create popup HTML for current weather marker."""
        temp_c = weather.get('temperature_c', weather.get('temp_c'))
        temp_f = weather.get('temperature_f')
        if temp_f is None and temp_c is not None:
            temp_f = temp_c * 9 / 5 + 32
        
        wind_kph = weather.get('wind_speed_kph')
        wind_mph = wind_kph * 0.621371 if wind_kph is not None else None
        precip = weather.get('precipitation_mm', weather.get('precipitation'))
        wind_dir = weather.get('wind_direction_cardinal', weather.get('wind_direction_deg', 'N/A'))
        stale_note = '<div style="margin-top: 6px; color: #856404;">Using cached/stale weather data</div>' if weather.get('is_stale') else ''
        
        return f"""
        <div style="font-family: Arial, sans-serif; min-width: 220px;">
            <h4 style="margin: 0 0 10px 0;">{label} Weather</h4>
            <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                <tr><td><b>Conditions</b></td><td>{weather.get('conditions', 'Unavailable')}</td></tr>
                <tr><td><b>Temperature</b></td><td>{f'{temp_f:.0f}°F' if temp_f is not None else 'N/A'}</td></tr>
                <tr><td><b>Wind</b></td><td>{f'{wind_mph:.0f} mph' if wind_mph is not None else 'N/A'} {wind_dir}</td></tr>
                <tr><td><b>Precip</b></td><td>{f'{float(precip):.1f} mm' if precip is not None else 'N/A'}</td></tr>
            </table>
            {stale_note}
        </div>
        """
    
    def _create_forecast_popup(self, label: str, forecast: Dict[str, Any]) -> str:
        """Create popup HTML for hourly forecast marker."""
        temp_c = forecast.get('temp_c')
        temp_f = temp_c * 9 / 5 + 32 if temp_c is not None else None
        wind_kph = forecast.get('wind_speed_kph')
        wind_mph = wind_kph * 0.621371 if wind_kph is not None else None
        wind_dir = forecast.get('wind_direction_deg', 'N/A')
        precip_prob = forecast.get('precipitation_prob')
        
        return f"""
        <div style="font-family: Arial, sans-serif; min-width: 220px;">
            <h4 style="margin: 0 0 10px 0;">{label} Forecast</h4>
            <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                <tr><td><b>Time</b></td><td>{forecast.get('timestamp', 'N/A')}</td></tr>
                <tr><td><b>Temperature</b></td><td>{f'{temp_f:.0f}°F' if temp_f is not None else 'N/A'}</td></tr>
                <tr><td><b>Wind</b></td><td>{f'{wind_mph:.0f} mph' if wind_mph is not None else 'N/A'} {wind_dir}°</td></tr>
                <tr><td><b>Rain Chance</b></td><td>{f'{float(precip_prob):.0f}%' if precip_prob is not None else 'N/A'}</td></tr>
            </table>
        </div>
        """
    
    def clear_cache(self):
        """Clear all cached analysis data."""
        logger.info("Clearing analysis cache")
        self._activities = None
        self._route_groups = None
        self._long_rides = None
        self._home_location = None
        self._work_location = None
        self._last_analysis_time = None

