"""
Analysis Service - Core route analysis and data processing.

This service orchestrates the main analysis workflow:
- Fetching activities from Strava
- Analyzing routes and grouping similar routes
- Processing long rides
- Managing data freshness and caching
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import folium

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
    
    def __init__(self, config: Config):
        """
        Initialize analysis service.
        
        Args:
            config: Configuration object
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
        self.weather_service = WeatherService(config)
    
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
            from src.auth import get_authenticated_client
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
                # TODO: Deserialize RouteGroup objects from JSON
                # For now, store as dict until we implement proper serialization
                self._route_groups = routes_data['route_groups']
                logger.info(f"Loaded {len(self._route_groups)} route groups from cache")
                
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
                # TODO: Deserialize LongRide objects from JSON
                self._long_rides = long_rides_data['long_rides']
                logger.info(f"Loaded {len(self._long_rides)} long rides from cache")
            
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
    
    def _serialize_route_group(self, route_group: RouteGroup) -> Dict[str, Any]:
        """Serialize RouteGroup to JSON-compatible dict."""
        # TODO: Implement proper serialization based on RouteGroup structure
        return {
            'name': getattr(route_group, 'name', 'Unknown'),
            'routes_count': len(getattr(route_group, 'routes', [])),
            # Add more fields as needed
        }
    
    def _serialize_long_ride(self, long_ride: LongRide) -> Dict[str, Any]:
        """Serialize LongRide to JSON-compatible dict."""
        # TODO: Implement proper serialization based on LongRide structure
        return {
            'name': getattr(long_ride, 'name', 'Unknown'),
            'distance': getattr(long_ride, 'distance', 0),
            # Add more fields as needed
        }
    
    def run_full_analysis(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Run complete analysis workflow.
        
        Steps:
        1. Fetch activities from Strava
        2. Find home and work locations
        3. Analyze and group routes
        4. Analyze long rides
        5. Cache results
        
        Args:
            force_refresh: If True, bypass cache and re-fetch data
            
        Returns:
            Dictionary with analysis summary:
            {
                'status': 'success' | 'error',
                'message': str,
                'activities_count': int,
                'route_groups_count': int,
                'long_rides_count': int,
                'analysis_time': str (ISO format),
                'data_freshness': 'fresh' | 'stale',
                'errors': List[str]
            }
        """
        logger.info(f"Starting full analysis (force_refresh={force_refresh})")
        errors = []
        
        try:
            # Step 1: Fetch activities
            logger.info("Fetching activities from Strava...")
            self._activities = self.data_fetcher.fetch_activities(force_refresh=force_refresh)
            logger.info(f"Fetched {len(self._activities)} activities")
            
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
            
            # Step 2: Find locations
            logger.info("Finding home and work locations...")
            location_finder = LocationFinder(self._activities, self.config)
            self._home_location, self._work_location = location_finder.find_locations()
            logger.info(f"Home: {self._home_location.name}, Work: {self._work_location.name}")
            
            # Step 3: Analyze routes
            logger.info("Analyzing and grouping routes...")
            route_analyzer = RouteAnalyzer(
                activities=self._activities,
                home=self._home_location,
                work=self._work_location,
                config=self.config,
                force_reanalysis=force_refresh
            )
            
            self._route_groups = route_analyzer.analyze_routes()
            logger.info(f"Found {len(self._route_groups)} route groups")
            
            # Step 4: Analyze long rides
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
            self._long_rides = long_ride_analyzer.group_similar_rides(long_ride_activities)
            logger.info(f"Found {len(self._long_rides)} unique long rides")
            
            # Step 5: Update analysis time
            self._last_analysis_time = datetime.now()
            
            return {
                'status': 'success',
                'message': 'Analysis completed successfully',
                'activities_count': len(self._activities),
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

# Made with Bob
