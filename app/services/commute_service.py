"""
Commute Service - Next commute recommendations.

This service provides intelligent commute route recommendations based on:
- Time of day (morning/evening commute windows)
- Weather forecasts
- Historical route performance
- Workout fit (TrainerRoad integration)
"""

import logging
from html import escape
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, time, date

import folium

from src.next_commute_recommender import NextCommuteRecommender, CommuteRecommendation
from src.route_analyzer import RouteGroup
from src.location_finder import Location
from src.config import Config
from src.visualizer import RouteVisualizer
from app.services.trainerroad_service import TrainerRoadService
from app.services.weather_service import WeatherService
from app.models.workouts import WorkoutMetadata
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)


class CommuteService:
    """
    Service for next commute recommendations.
    
    Provides:
    - Time-aware commute recommendations
    - Weather-optimized route selection
    - Alternative route suggestions
    - Departure time optimization
    """
    
    def __init__(self, config: Config):
        """
        Initialize commute service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self._recommender: Optional[NextCommuteRecommender] = None
        self.trainerroad_service = TrainerRoadService(config)
        self.weather_service = WeatherService(config)
    
    def initialize(self, route_groups: List[RouteGroup],
                   home_location: Location,
                   work_location: Location,
                   enable_weather: bool = True):
        """
        Initialize the recommender with route data.
        
        Must be called before getting recommendations.
        
        Args:
            route_groups: List of analyzed route groups
            home_location: Home location
            work_location: Work location
            enable_weather: Whether to include weather analysis
        """
        logger.info("Initializing commute recommender")
        
        home_coords = (home_location.lat, home_location.lon)
        work_coords = (work_location.lat, work_location.lon)
        
        self._recommender = NextCommuteRecommender(
            route_groups=route_groups,
            config=self.config,
            home_location=home_coords,
            work_location=work_coords,
            enable_weather=enable_weather
        )
        
        logger.info("Commute recommender initialized")
    
    def get_recommendation(self, direction: Optional[str] = None) -> Dict[str, Any]:
        """
        Get commute recommendation for next ride.
        
        This is the primary recommendation method that wraps get_next_commute()
        functionality. It automatically determines if the next commute is to work
        (morning) or to home (evening) based on current time, unless direction
        is explicitly specified.
        
        Args:
            direction: Optional direction override ("to_work" or "to_home")
            
        Returns:
            Dictionary with recommendation (same format as get_next_commute):
            {
                'status': 'success' | 'error',
                'direction': 'to_work' | 'to_home',
                'time_window': str,
                'route': {
                    'id': str,
                    'name': str,
                    'distance': float,
                    'duration': float,
                    'elevation': float
                },
                'score': float,
                'breakdown': {...},
                'weather': {...},
                'alternatives': List[Dict],
                'is_today': bool
            }
        """
        return self.get_next_commute(direction=direction)
    
    def get_next_commute(self, direction: Optional[str] = None) -> Dict[str, Any]:
        """
        Get recommendation for next commute.
        
        Automatically determines if next commute is to work (morning) or
        to home (evening) based on current time, unless direction is specified.
        
        Args:
            direction: Optional direction override ("to_work" or "to_home")
            
        Returns:
            Dictionary with recommendation:
            {
                'status': 'success' | 'error',
                'direction': 'to_work' | 'to_home',
                'time_window': str,
                'route': {
                    'id': str,
                    'name': str,
                    'distance': float,
                    'duration': float,
                    'elevation': float
                },
                'score': float,
                'breakdown': {
                    'time': float,
                    'distance': float,
                    'safety': float,
                    'weather': float
                },
                'weather': {
                    'temperature': float,
                    'conditions': str,
                    'wind_speed': float,
                    'wind_direction': str,
                    'precipitation': float
                },
                'alternatives': List[Dict],
                'is_today': bool
            }
        """
        if not self._recommender:
            return {
                'status': 'error',
                'message': 'Commute service not initialized. Run analysis first.',
                'direction': None,
                'route': None
            }
        
        try:
            # Get recommendations for both directions
            recommendations = self._recommender.get_next_commute_recommendations()
            
            if not recommendations:
                return {
                    'status': 'error',
                    'message': 'No suitable commute routes found',
                    'direction': direction,
                    'route': None
                }
            
            # If direction specified, return that one
            if direction and direction in recommendations:
                recommendation = recommendations[direction]
                return self._format_recommendation(recommendation)
            
            # Otherwise, determine which one to show based on time
            from datetime import datetime
            current_hour = datetime.now().hour
            
            # Morning (before 10 AM): show to_work
            # Midday (10 AM - 6 PM): show to_home
            # Evening (after 6 PM): show to_work for tomorrow
            if current_hour < 10:
                preferred_direction = 'to_work'
            elif current_hour < 18:
                preferred_direction = 'to_home'
            else:
                preferred_direction = 'to_work'
            
            if preferred_direction in recommendations:
                recommendation = recommendations[preferred_direction]
                return self._format_recommendation(recommendation)
            
            # Fallback: return first available
            first_direction = list(recommendations.keys())[0]
            recommendation = recommendations[first_direction]
            return self._format_recommendation(recommendation)
            
        except Exception as e:
            logger.error(f"Failed to get commute recommendation: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to generate recommendation: {str(e)}',
                'direction': direction,
                'route': None
            }
    
    def get_all_commute_options(self, direction: str) -> Dict[str, Any]:
        """
        Get all available commute options for a direction.
        
        Args:
            direction: "to_work" or "to_home"
            
        Returns:
            Dictionary with all options:
            {
                'status': 'success' | 'error',
                'direction': str,
                'options': List[Dict],  # All routes ranked by score
                'count': int
            }
        """
        if not self._recommender:
            return {
                'status': 'error',
                'message': 'Commute service not initialized',
                'direction': direction,
                'options': [],
                'count': 0
            }
        
        try:
            # Get all recommendations for direction
            recommendations = self._recommender.get_all_recommendations(direction)
            
            options = [
                self._format_recommendation(rec)
                for rec in recommendations
            ]
            
            return {
                'status': 'success',
                'direction': direction,
                'options': options,
                'count': len(options)
            }
            
        except Exception as e:
            logger.error(f"Failed to get commute options: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to get options: {str(e)}',
                'direction': direction,
                'options': [],
                'count': 0
            }
    
    def get_departure_windows(self) -> Dict[str, Any]:
        """
        Get optimal departure time windows for commutes.
        
        Returns:
            Dictionary with time windows:
            {
                'morning': {
                    'start': str (HH:MM),
                    'end': str (HH:MM),
                    'optimal': str (HH:MM)
                },
                'evening': {
                    'start': str (HH:MM),
                    'end': str (HH:MM),
                    'optimal': str (HH:MM)
                }
            }
        """
        if not self._recommender:
            return {
                'morning': {'start': '07:00', 'end': '09:00', 'optimal': '08:00'},
                'evening': {'start': '15:00', 'end': '18:00', 'optimal': '16:30'}
            }
        
        # Get windows from recommender
        morning_start = self._recommender.morning_window_start
        morning_end = self._recommender.morning_window_end
        evening_start = self._recommender.evening_window_start
        evening_end = self._recommender.evening_window_end
        
        return {
            'morning': {
                'start': morning_start.strftime('%H:%M'),
                'end': morning_end.strftime('%H:%M'),
                'optimal': '08:00'  # TODO: Calculate based on weather/traffic
            },
            'evening': {
                'start': evening_start.strftime('%H:%M'),
                'end': evening_end.strftime('%H:%M'),
                'optimal': '16:30'  # TODO: Calculate based on weather/traffic
            }
        }
    
    def _format_recommendation(self, rec: CommuteRecommendation) -> Dict[str, Any]:
        """
        Format a CommuteRecommendation for web consumption.
        
        Args:
            rec: CommuteRecommendation object
            
        Returns:
            Dictionary with formatted recommendation
        """
        route_group = rec.route_group
        
        result = {
            'status': 'success',
            'direction': rec.direction,
            'time_window': rec.time_window,
            'route': {
                'id': route_group.id,
                'name': route_group.name or f"Route {route_group.id}",
                'distance': route_group.representative_route.distance,
                'duration': route_group.representative_route.duration,
                'elevation': route_group.representative_route.elevation_gain,
                'frequency': route_group.frequency,
                'is_plus_route': route_group.is_plus_route,
                'coordinates': route_group.representative_route.coordinates
            },
            'score': rec.score,
            'breakdown': rec.breakdown,
            'is_today': rec.is_today,
            'window_start': rec.window_start.strftime('%H:%M'),
            'window_end': rec.window_end.strftime('%H:%M'),
            'departure_time': rec.window_start.strftime('%I:%M %p').lstrip('0'),
            'confidence': self._get_confidence_label(rec.score)
        }
        
        # Add weather if available
        if rec.forecast_weather:
            result['weather'] = rec.forecast_weather
        
        return result
    
    def generate_comparison_map(self,
                                routes: List[Dict[str, Any]],
                                home_location: Location,
                                work_location: Location) -> Optional[str]:
        """
        Generate an interactive comparison map for all available commute routes.
        
        Args:
            routes: Ranked commute route options from get_all_commute_options()
            home_location: Home location
            work_location: Work location
            
        Returns:
            Folium HTML string or None if generation fails
        """
        if not routes:
            logger.warning("No routes provided for commute comparison map")
            return None
        
        try:
            route_groups = []
            route_lookup = {}
            if self._recommender and getattr(self._recommender, 'route_groups', None):
                for group in self._recommender.route_groups:
                    route_groups.append(group)
                    route_lookup[group.id] = group
            
            visualizer = RouteVisualizer(
                route_groups=route_groups,
                home=home_location,
                work=work_location,
                config=self.config
            )
            
            map_obj = visualizer.create_base_map()
            visualizer.map = map_obj
            
            route_layers = []
            all_bounds = []
            
            for route_option in routes:
                route_data = route_option.get('route', {})
                route_id = route_data.get('id')
                route_group = route_lookup.get(route_id)
                
                if not route_group:
                    logger.warning(f"Skipping commute map route {route_id}: route group not found")
                    continue
                
                coordinates = route_data.get('coordinates') or route_group.representative_route.coordinates
                if not coordinates:
                    logger.warning(f"Skipping commute map route {route_id}: no coordinates")
                    continue
                
                # Use direction-based colors: green for to_work, blue for to_home
                direction = route_option.get('direction', '')
                if direction == 'to_work':
                    color = '#28a745'  # Green
                elif direction == 'to_home':
                    color = '#007bff'  # Blue
                else:
                    # Fallback to score-based color if direction not specified
                    color = self._get_route_color(route_option.get('score', 0))
                
                route_name = route_data.get('name') or route_group.name or f"Route {route_id}"
                popup_html = self._create_comparison_popup(route_option)
                
                # Add route directly to map (not in FeatureGroup) so it can't be toggled off
                # Users control visibility by clicking cards or polylines
                folium.PolyLine(
                    coordinates,
                    color=color,
                    weight=7,
                    opacity=0.85,
                    popup=folium.Popup(popup_html, max_width=320),
                    tooltip=f"{route_name} • {route_option.get('score', 0) * 100:.0f}%",
                    className=f"commute-route route-{route_id} direction-{direction}",
                ).add_to(map_obj)
                
                all_bounds.extend([[lat, lon] for lat, lon in coordinates])
            
            visualizer.map = map_obj
            visualizer.add_location_markers()
            
            folium.Marker(
                [home_location.lat, home_location.lon],
                popup=f"<b>Home</b><br>{escape(home_location.name or 'Home')}",
                tooltip="Home",
                icon=folium.Icon(color='green', icon='home', prefix='fa')
            ).add_to(map_obj)
            
            folium.Marker(
                [work_location.lat, work_location.lon],
                popup=f"<b>Work</b><br>{escape(work_location.name or 'Work')}",
                tooltip="Work",
                icon=folium.Icon(color='blue', icon='briefcase', prefix='fa')
            ).add_to(map_obj)
            
            if all_bounds:
                map_obj.fit_bounds(all_bounds, padding=(30, 30))
            
            try:
                self._add_commute_weather_overlay(
                    map_obj=map_obj,
                    routes=routes,
                    home_location=home_location,
                    work_location=work_location
                )
                visualizer.add_weather_display()
            except Exception as weather_error:
                logger.warning(f"Commute weather overlay unavailable: {weather_error}")
            
            # Add LayerControl collapsed by default, only for map type selection
            # Route visibility is controlled by clicking cards/polylines, not layer control
            folium.LayerControl(collapsed=True).add_to(map_obj)
            
            # Get the HTML and inject JavaScript for route highlighting
            map_html = map_obj._repr_html_()
            
            # Inject JavaScript to handle postMessage for route highlighting
            highlight_script = """
            <script>
            (function() {
                // Listen for messages from parent window to highlight routes
                window.addEventListener('message', function(event) {
                    if (event.data && event.data.type === 'highlightRoute') {
                        highlightRoute(event.data.direction);
                    }
                });
                
                function highlightRoute(direction) {
                    // Find all polylines with direction class
                    const allPolylines = document.querySelectorAll('path.leaflet-interactive');
                    
                    allPolylines.forEach(function(polyline) {
                        const classes = polyline.getAttribute('class') || '';
                        
                        // Check if this polyline matches the selected direction
                        if (classes.includes('direction-' + direction)) {
                            // Highlight: full opacity, thicker stroke
                            polyline.style.opacity = '1.0';
                            polyline.style.strokeOpacity = '1.0';
                            polyline.style.strokeWidth = '8';
                            polyline.style.zIndex = '1000';
                        } else if (classes.includes('direction-')) {
                            // Subdue: reduced opacity, thinner stroke
                            polyline.style.opacity = '0.3';
                            polyline.style.strokeOpacity = '0.3';
                            polyline.style.strokeWidth = '5';
                            polyline.style.zIndex = '1';
                        }
                    });
                }
                
                // Also add click handlers to polylines for direct interaction
                document.addEventListener('DOMContentLoaded', function() {
                    const allPolylines = document.querySelectorAll('path.leaflet-interactive');
                    
                    allPolylines.forEach(function(polyline) {
                        polyline.style.cursor = 'pointer';
                        
                        polyline.addEventListener('click', function() {
                            const classes = this.getAttribute('class') || '';
                            
                            // Extract direction from class
                            const directionMatch = classes.match(/direction-(\\w+)/);
                            if (directionMatch) {
                                highlightRoute(directionMatch[1]);
                                
                                // Notify parent window
                                if (window.parent !== window) {
                                    window.parent.postMessage({
                                        type: 'routeClicked',
                                        direction: directionMatch[1]
                                    }, '*');
                                }
                            }
                        });
                    });
                });
            })();
            </script>
            """
            
            # Insert the script before the closing body tag
            map_html = map_html.replace('</body>', highlight_script + '</body>')
            
            return map_html
            
        except Exception as e:
            logger.error(f"Failed to generate commute comparison map: {e}", exc_info=True)
            return None
    
    def _get_route_color(self, score: float) -> str:
        """Map recommendation score to semantic route color."""
        if score >= 0.85:
            return '#28a745'
        if score >= 0.7:
            return '#007bff'
        if score >= 0.5:
            return '#ffc107'
        return '#dc3545'
    
    def _get_confidence_label(self, score: float) -> str:
        """Convert numeric score to a coarse confidence label."""
        if score >= 0.85:
            return 'high'
        if score >= 0.65:
            return 'medium'
        return 'low'
    
    def _create_comparison_popup(self, route_option: Dict[str, Any]) -> str:
        """Create commute-specific popup HTML for comparison map routes."""
        route = route_option.get('route', {})
        weather = route_option.get('weather') or {}
        route_name = escape(route.get('name', 'Unknown Route'))
        distance_km = route.get('distance', 0) / 1000
        duration_min = route.get('duration', 0) / 60
        elevation_m = route.get('elevation', 0)
        score_pct = route_option.get('score', 0) * 100
        
        conditions = escape(str(weather.get('conditions', 'Unavailable')))
        temperature = weather.get('temperature')
        wind_speed = weather.get('wind_speed')
        precipitation = weather.get('precipitation')
        favorability = escape(str(weather.get('cycling_favorability', 'unknown')).replace('_', ' ').title())
        
        weather_rows = []
        if temperature is not None:
            weather_rows.append(f"<tr><td><b>Temp</b></td><td>{temperature:.0f}°F</td></tr>")
        weather_rows.append(f"<tr><td><b>Conditions</b></td><td>{conditions}</td></tr>")
        if wind_speed is not None:
            weather_rows.append(f"<tr><td><b>Wind</b></td><td>{wind_speed:.0f} mph</td></tr>")
        if precipitation is not None:
            weather_rows.append(f"<tr><td><b>Rain</b></td><td>{precipitation:.0f}%</td></tr>")
        weather_rows.append(f"<tr><td><b>Cycling</b></td><td>{favorability}</td></tr>")
        
        return f"""
        <div style="font-family: Arial, sans-serif; min-width: 240px;">
            <h4 style="margin: 0 0 10px 0;">{route_name}</h4>
            <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                <tr><td><b>Distance</b></td><td>{distance_km:.1f} km</td></tr>
                <tr><td><b>Duration</b></td><td>{duration_min:.0f} min</td></tr>
                <tr><td><b>Elevation</b></td><td>{elevation_m:.0f} m</td></tr>
                <tr><td><b>Score</b></td><td>{score_pct:.0f}%</td></tr>
                {''.join(weather_rows)}
            </table>
            <div style="margin-top: 10px; font-size: 11px; color: #666;">
                Future enhancement (#232): click route to highlight corresponding list item.
            </div>
        </div>
        """
    
    def _add_commute_weather_overlay(self,
                                     map_obj: folium.Map,
                                     routes: List[Dict[str, Any]],
                                     home_location: Location,
                                     work_location: Location) -> None:
        """Add toggleable current weather markers for commute locations and route midpoints."""
        weather_layer = folium.FeatureGroup(name='Weather Overlay', show=False)
        
        key_points: List[Tuple[str, Tuple[float, float], str]] = [
            ('Home', (home_location.lat, home_location.lon), 'home'),
            ('Work', (work_location.lat, work_location.lon), 'work'),
        ]
        
        seen_route_ids = set()
        for route_option in routes:
            route = route_option.get('route', {})
            route_id = route.get('id')
            if route_id in seen_route_ids:
                continue
            seen_route_ids.add(route_id)
            
            coordinates = route.get('coordinates') or []
            if not coordinates:
                continue
            
            midpoint = coordinates[len(coordinates) // 2]
            route_name = route.get('name') or f"Route {route_id}"
            key_points.append((f"{route_name} midpoint", midpoint, 'midpoint'))
        
        seen_locations = set()
        for label, coords, point_type in key_points:
            lat, lon = coords
            dedupe_key = (round(lat, 3), round(lon, 3), point_type)
            if dedupe_key in seen_locations:
                continue
            seen_locations.add(dedupe_key)
            
            weather = self.weather_service.get_current_weather(lat, lon, location_name=label)
            if not weather:
                continue
            
            icon_name, icon_prefix, marker_color = self._get_weather_marker_style(weather)
            popup_html = self._create_weather_popup(label, weather)
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"{label}: {weather.get('conditions', 'Weather')}",
                icon=folium.Icon(color=marker_color, icon=icon_name, prefix=icon_prefix)
            ).add_to(weather_layer)
        
        if weather_layer._children:
            weather_layer.add_to(map_obj)
    
    def _get_weather_marker_style(self, weather: Dict[str, Any]) -> Tuple[str, str, str]:
        """Choose weather marker icon and semantic color from conditions."""
        conditions = str(weather.get('conditions', '')).lower()
        wind_speed = weather.get('wind_speed_kph', weather.get('wind_speed', 0)) or 0
        precipitation = weather.get('precipitation_mm', weather.get('precipitation', 0)) or 0
        favorability = str(weather.get('cycling_favorability', '')).lower()
        
        if 'rain' in conditions or 'shower' in conditions or precipitation > 0.5:
            return ('cloud-rain', 'fa', 'red')
        if wind_speed >= 25:
            return ('flag', 'fa', 'orange')
        if 'cloud' in conditions or 'overcast' in conditions:
            return ('cloud', 'fa', 'blue')
        if favorability == 'favorable':
            return ('sun', 'fa', 'green')
        return ('cloud-sun', 'fa', 'lightgray')
    
    def _create_weather_popup(self, label: str, weather: Dict[str, Any]) -> str:
        """Create compact weather popup for map markers."""
        temperature = weather.get('temperature')
        if temperature is None:
            temp_c = weather.get('temperature_c', weather.get('temp_c'))
            if temp_c is not None:
                temperature = (temp_c * 9 / 5 + 32)
        
        wind_speed = weather.get('wind_speed')
        if wind_speed is None:
            wind_kph = weather.get('wind_speed_kph')
            if wind_kph is not None:
                wind_speed = wind_kph * 0.621371
        
        wind_direction = (
            weather.get('wind_direction_cardinal')
            or weather.get('wind_direction')
            or weather.get('wind_direction_deg')
            or 'N/A'
        )
        precipitation_probability = (
            weather.get('precipitation_probability')
            or weather.get('precipitation_prob')
            or weather.get('precipitation_prob_max')
        )
        precipitation_amount = weather.get('precipitation_mm', weather.get('precipitation'))
        description = escape(str(weather.get('conditions', 'Unavailable')))
        stale_note = '<div style="margin-top: 6px; color: #856404;">Using cached/stale weather data</div>' if weather.get('is_stale') else ''
        
        precip_html = ''
        if precipitation_probability is not None:
            precip_html = f'<tr><td><b>Precip Prob</b></td><td>{float(precipitation_probability):.0f}%</td></tr>'
        elif precipitation_amount is not None:
            precip_html = f'<tr><td><b>Precip</b></td><td>{float(precipitation_amount):.1f} mm</td></tr>'
        
        return f"""
        <div style="font-family: Arial, sans-serif; min-width: 220px;">
            <h4 style="margin: 0 0 10px 0;">{escape(label)}</h4>
            <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                <tr><td><b>Conditions</b></td><td>{description}</td></tr>
                <tr><td><b>Temperature</b></td><td>{f'{float(temperature):.0f}°F' if temperature is not None else 'N/A'}</td></tr>
                <tr><td><b>Wind</b></td><td>{f'{float(wind_speed):.0f} mph' if wind_speed is not None else 'N/A'} {escape(str(wind_direction))}</td></tr>
                {precip_html}
            </table>
            {stale_note}
        </div>
        """

# Made with Bob

    
    def get_workout_aware_commute(self, direction: Optional[str] = None) -> Dict[str, Any]:
        """
        Get workout-aware commute recommendation.
        
        Checks for scheduled workout today and adjusts route recommendation
        to accommodate workout constraints (e.g., longer endurance rides).
        
        Args:
            direction: Optional direction override ("to_work" or "to_home")
            
        Returns:
            Dictionary with workout-aware recommendation including:
            - Standard commute fields
            - workout_fit: Dict with workout information and fit analysis
            - is_workout_extended: bool indicating if route was extended for workout
        """
        # Get today's workout constraints
        today = date.today()
        workout_constraints = self.trainerroad_service.get_workout_constraints(today)
        
        # Get base commute recommendation
        base_rec = self.get_next_commute(direction)
        
        if base_rec['status'] != 'success':
            return base_rec
        
        # If no workout scheduled, return base recommendation
        if not workout_constraints:
            base_rec['workout_fit'] = None
            base_rec['is_workout_extended'] = False
            return base_rec
        
        # Analyze workout fit
        workout_fit = self._analyze_workout_fit(
            base_rec,
            workout_constraints
        )
        
        # Check if route should be extended for workout
        if self._should_extend_for_workout(workout_constraints, base_rec):
            extended_rec = self._extend_route_for_workout(
                base_rec,
                workout_constraints
            )
            if extended_rec:
                extended_rec['workout_fit'] = workout_fit
                extended_rec['is_workout_extended'] = True
                return extended_rec
        
        # Return base recommendation with workout fit analysis
        base_rec['workout_fit'] = workout_fit
        base_rec['is_workout_extended'] = False
        return base_rec
    
    def _analyze_workout_fit(self, 
                            recommendation: Dict[str, Any],
                            constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze how well the commute fits the workout.
        
        Args:
            recommendation: Commute recommendation
            constraints: Workout constraints
            
        Returns:
            Dictionary with fit analysis
        """
        route = recommendation.get('route', {})
        duration_min = route.get('duration', 0)
        
        workout_name = constraints.get('workout_name', 'Unknown Workout')
        workout_type = constraints.get('workout_type', 'Unknown')
        min_duration = constraints.get('min_duration_minutes')
        max_duration = constraints.get('max_duration_minutes')
        indoor_fallback = constraints.get('indoor_fallback', False)
        notes = constraints.get('notes', [])
        
        # Calculate fit score
        fit_score = 0.5  # Base score
        fit_reasons = []
        
        if min_duration and duration_min < min_duration:
            fit_score -= 0.3
            fit_reasons.append(f"Route is {min_duration - duration_min:.0f} min shorter than workout target")
        elif max_duration and duration_min > max_duration:
            fit_score -= 0.2
            fit_reasons.append(f"Route is {duration_min - max_duration:.0f} min longer than recommended")
        else:
            fit_score += 0.3
            fit_reasons.append("Duration matches workout target")
        
        if indoor_fallback:
            fit_score -= 0.2
            fit_reasons.append("High-intensity workout - indoor trainer recommended")
        else:
            fit_score += 0.2
            fit_reasons.append("Suitable for outdoor completion")
        
        return {
            'workout_name': workout_name,
            'workout_type': workout_type,
            'fit_score': max(0.0, min(1.0, fit_score)),
            'fit_reasons': fit_reasons,
            'indoor_fallback': indoor_fallback,
            'notes': notes,
            'duration_target': {
                'min': min_duration,
                'max': max_duration
            }
        }
    
    def _should_extend_for_workout(self,
                                   constraints: Dict[str, Any],
                                   recommendation: Dict[str, Any]) -> bool:
        """
        Determine if route should be extended to meet workout duration.
        
        Args:
            constraints: Workout constraints
            recommendation: Base commute recommendation
            
        Returns:
            True if route should be extended
        """
        # Only extend for endurance workouts
        if constraints.get('workout_type') != 'Endurance':
            return False
        
        # Don't extend if indoor fallback is preferred
        if constraints.get('indoor_fallback', False):
            return False
        
        # Check if current route is too short
        route = recommendation.get('route', {})
        duration_min = route.get('duration', 0)
        min_duration = constraints.get('min_duration_minutes')
        
        if min_duration and duration_min < min_duration:
            # Route is too short, consider extension
            return True
        
        return False
    
    def _extend_route_for_workout(self,
                                  base_rec: Dict[str, Any],
                                  constraints: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extend route to meet workout duration requirements.
        
        This is a simplified implementation that looks for longer alternative routes.
        A more sophisticated version could generate route extensions or loops.
        
        Args:
            base_rec: Base commute recommendation
            constraints: Workout constraints
            
        Returns:
            Extended recommendation or None if no suitable extension found
        """
        if not self._recommender:
            return None
        
        try:
            direction = base_rec.get('direction')
            min_duration = constraints.get('min_duration_minutes', 0)
            
            # Get all route options for this direction
            all_options = self._recommender.get_all_recommendations(direction)
            
            # Find routes that meet duration requirement
            suitable_routes = [
                rec for rec in all_options
                if rec.duration_minutes >= min_duration
            ]
            
            if not suitable_routes:
                logger.info(f"No routes found meeting {min_duration} min duration requirement")
                return None
            
            # Return the best suitable route
            best_extended = suitable_routes[0]
            extended_rec = self._format_recommendation(best_extended)
            extended_rec['extension_reason'] = f"Extended to meet {constraints.get('workout_name')} duration"
            
            logger.info(f"Extended route from {base_rec['route']['duration']:.0f} to {extended_rec['route']['duration']:.0f} min")
            return extended_rec
            
        except Exception as e:
            logger.error(f"Failed to extend route: {e}", exc_info=True)
            return None


# Made with Bob
