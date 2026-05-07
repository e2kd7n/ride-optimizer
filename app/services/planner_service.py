"""
Planner Service - Long ride planning and recommendations.

This service provides intelligent long ride recommendations based on:
- Weather forecasts (7-day window)
- Route variety and exploration
- Workout fit (TrainerRoad integration)
- Historical performance
"""

import logging
from html import escape
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import folium

from src.long_ride_analyzer import LongRideAnalyzer, LongRide, RideRecommendation
from src.weather_fetcher import WeatherFetcher
from src.config import Config
from src.location_finder import Location
from app.services.weather_service import WeatherService
from app.models.weather import WeatherSnapshot

logger = logging.getLogger(__name__)


class PlannerService:
    """
    Service for long ride planning and recommendations.
    
    Provides:
    - Multi-day weather-optimized ride recommendations
    - Route variety scoring
    - Workout fit integration
    - Interactive map-based ride discovery
    """
    
    def __init__(self, config: Config):
        """
        Initialize planner service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.weather_fetcher = WeatherFetcher()
        self.weather_service = WeatherService(config)
        self._long_rides: Optional[List[LongRide]] = None
    
    def initialize(self, long_rides: List[LongRide]):
        """
        Initialize the planner with long ride data.
        
        Must be called before getting recommendations.
        
        Args:
            long_rides: List of analyzed long rides
        """
        logger.info(f"Initializing planner with {len(long_rides)} long rides")
        self._long_rides = long_rides
    
    def get_recommendations(self, 
                          forecast_days: int = 7,
                          min_distance: float = 30.0,
                          max_distance: float = 100.0,
                          location: Optional[Tuple[float, float]] = None) -> Dict[str, Any]:
        """
        Get long ride recommendations for upcoming days.
        
        Args:
            forecast_days: Number of days to analyze (1-14)
            min_distance: Minimum ride distance in miles
            max_distance: Maximum ride distance in miles
            location: Optional (lat, lon) to find rides near a specific location
            
        Returns:
            Dictionary with recommendations:
            {
                'status': 'success' | 'error',
                'forecast_days': int,
                'recommendations': [
                    {
                        'date': str (YYYY-MM-DD),
                        'day_name': str,
                        'rides': [
                            {
                                'ride_id': int,
                                'name': str,
                                'distance': float,
                                'duration': float,
                                'elevation': float,
                                'score': float,
                                'weather_score': float,
                                'variety_score': float,
                                'weather': {...},
                                'start_location': [lat, lon],
                                'is_loop': bool
                            }
                        ],
                        'best_ride': {...},
                        'weather_summary': str
                    }
                ],
                'best_day': str,
                'total_rides': int
            }
        """
        if not self._long_rides:
            return {
                'status': 'error',
                'message': 'Planner service not initialized. Run analysis first.',
                'recommendations': []
            }
        
        try:
            # Filter rides by distance
            min_meters = min_distance * 1609.34  # miles to meters
            max_meters = max_distance * 1609.34
            
            filtered_rides = [
                ride for ride in self._long_rides
                if min_meters <= ride.distance <= max_meters
            ]
            
            logger.info(f"Filtered to {len(filtered_rides)} rides in distance range")
            
            if not filtered_rides:
                return {
                    'status': 'success',
                    'message': 'No rides found in specified distance range',
                    'forecast_days': forecast_days,
                    'recommendations': [],
                    'total_rides': 0
                }
            
            # Get weather forecasts for each day
            recommendations = []
            today = datetime.now().date()
            
            for day_offset in range(forecast_days):
                target_date = today + timedelta(days=day_offset)
                day_name = target_date.strftime('%A')
                
                # Score rides for this day
                day_rides = self._score_rides_for_day(
                    filtered_rides, 
                    target_date,
                    location
                )
                
                if day_rides:
                    best_ride = max(day_rides, key=lambda r: r['score'])
                    
                    recommendations.append({
                        'date': target_date.isoformat(),
                        'day_name': day_name,
                        'rides': day_rides[:5],  # Top 5 rides
                        'best_ride': best_ride,
                        'weather_summary': self._get_weather_summary(best_ride.get('weather')),
                        'ride_count': len(day_rides)
                    })
            
            # Find best day overall
            best_day = None
            if recommendations:
                best_day_rec = max(
                    recommendations,
                    key=lambda d: d['best_ride']['score'] if d.get('best_ride') else 0
                )
                best_day = best_day_rec['date']
            
            return {
                'status': 'success',
                'forecast_days': forecast_days,
                'recommendations': recommendations,
                'best_day': best_day,
                'total_rides': len(filtered_rides),
                'distance_range': {
                    'min': min_distance,
                    'max': max_distance
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get ride recommendations: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to generate recommendations: {str(e)}',
                'recommendations': []
            }
    
    def get_rides_near_location(self, 
                               lat: float, 
                               lon: float,
                               radius_miles: float = 10.0,
                               limit: int = 10) -> Dict[str, Any]:
        """
        Find rides near a specific location (for map-based discovery).
        
        Args:
            lat: Latitude
            lon: Longitude
            radius_miles: Search radius in miles
            limit: Maximum number of rides to return
            
        Returns:
            Dictionary with nearby rides:
            {
                'status': 'success' | 'error',
                'location': [lat, lon],
                'radius_miles': float,
                'rides': List[Dict],
                'count': int
            }
        """
        if not self._long_rides:
            return {
                'status': 'error',
                'message': 'Planner service not initialized',
                'rides': [],
                'count': 0
            }
        
        try:
            from geopy.distance import geodesic
            
            location = (lat, lon)
            radius_meters = radius_miles * 1609.34
            
            # Find rides within radius
            nearby_rides = []
            for ride in self._long_rides:
                # Check distance to ride start
                distance = geodesic(location, ride.start_location).meters
                
                if distance <= radius_meters:
                    nearby_rides.append({
                        'ride_id': ride.activity_id,
                        'name': ride.name,
                        'distance': ride.distance_km,
                        'duration': ride.duration_hours,
                        'elevation': ride.elevation_gain,
                        'distance_to_location': distance / 1609.34,  # miles
                        'start_location': list(ride.start_location),
                        'is_loop': ride.is_loop,
                        'uses': ride.uses,
                        'type': ride.type
                    })
            
            # Sort by distance to location
            nearby_rides.sort(key=lambda r: r['distance_to_location'])
            
            return {
                'status': 'success',
                'location': [lat, lon],
                'radius_miles': radius_miles,
                'rides': nearby_rides[:limit],
                'count': len(nearby_rides)
            }
            
        except Exception as e:
            logger.error(f"Failed to find nearby rides: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to find rides: {str(e)}',
                'rides': [],
                'count': 0
            }
    
    def get_ride_details(self, ride_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific ride.
        
        Args:
            ride_id: Activity ID of the ride
            
        Returns:
            Dictionary with ride details
        """
        if not self._long_rides:
            return {
                'status': 'error',
                'message': 'Planner service not initialized'
            }
        
        # Find the ride
        ride = next((r for r in self._long_rides if r.activity_id == ride_id), None)
        
        if not ride:
            return {
                'status': 'error',
                'message': f'Ride {ride_id} not found'
            }
        
        return {
            'status': 'success',
            'ride': {
                'ride_id': ride.activity_id,
                'name': ride.name,
                'distance': ride.distance_km,
                'duration': ride.duration_hours,
                'elevation': ride.elevation_gain,
                'average_speed': ride.average_speed * 3.6,  # m/s to km/h
                'start_location': list(ride.start_location),
                'end_location': list(ride.end_location),
                'is_loop': ride.is_loop,
                'type': ride.type,
                'uses': ride.uses,
                'coordinates': ride.coordinates,
                'activity_ids': ride.activity_ids,
                'activity_dates': ride.activity_dates
            }
        }
    
    def _score_rides_for_day(self, 
                            rides: List[LongRide],
                            target_date: datetime.date,
                            location: Optional[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """
        Score rides for a specific day based on weather and other factors.
        
        Args:
            rides: List of rides to score
            target_date: Date to score for
            location: Optional location preference
            
        Returns:
            List of scored rides
        """
        scored_rides = []
        
        for ride in rides:
            # Get weather forecast for ride location
            weather = self._get_weather_for_ride(ride, target_date)
            
            # Calculate scores
            weather_score = self._calculate_weather_score(weather)
            variety_score = 1.0 / (ride.uses + 1)  # Prefer less-used routes
            
            # Location proximity score (if location specified)
            location_score = 1.0
            if location:
                from geopy.distance import geodesic
                distance = geodesic(location, ride.start_location).meters
                # Prefer rides within 10 miles
                location_score = max(0, 1.0 - (distance / 16093.4))
            
            # Combined score
            score = (
                weather_score * 0.5 +
                variety_score * 0.3 +
                location_score * 0.2
            )
            
            scored_rides.append({
                'ride_id': ride.activity_id,
                'name': ride.name,
                'distance': ride.distance_km,
                'duration': ride.duration_hours,
                'elevation': ride.elevation_gain,
                'score': score,
                'weather_score': weather_score,
                'variety_score': variety_score,
                'location_score': location_score,
                'weather': weather,
                'start_location': list(ride.start_location),
                'is_loop': ride.is_loop,
                'uses': ride.uses
            })
        
        # Sort by score
        scored_rides.sort(key=lambda r: r['score'], reverse=True)
        return scored_rides
    
    def _get_weather_for_ride(self, ride: LongRide, target_date: datetime.date) -> Dict[str, Any]:
        """
        Get weather forecast for a ride on a specific date.
        
        Args:
            ride: LongRide object with coordinates
            target_date: Date to get forecast for
            
        Returns:
            Dictionary with weather data including comfort_score and cycling_favorability
        """
        try:
            # Calculate days ahead for forecast
            days_ahead = (target_date - datetime.now().date()).days
            
            if days_ahead < 0:
                logger.warning(f"Cannot get forecast for past date: {target_date}")
                return {}
            
            # Get forecast for ride start location
            lat, lon = ride.start_location
            
            # Get forecast from WeatherFetcher (uses get_daily_forecast, not get_forecast)
            forecast_data = self.weather_fetcher.get_daily_forecast(lat, lon, days=min(days_ahead + 1, 7))
            
            if not forecast_data:
                logger.warning(f"No forecast data available for {target_date}")
                return {}
            
            # Find the forecast for target date (forecast_data is a list of daily forecasts)
            if days_ahead < len(forecast_data):
                day_forecast = forecast_data[days_ahead]
                
                # Create WeatherSnapshot to calculate comfort metrics
                snapshot = WeatherSnapshot.create_from_weather_data(
                    day_forecast,
                    location_name=ride.name,
                    is_current=False,
                    forecast_time=datetime.combine(target_date, datetime.min.time())
                )
                
                if snapshot:
                    return snapshot.to_dict()
            
            logger.warning(f"Forecast not available for day {days_ahead}")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get weather for ride {ride.activity_id}: {e}", exc_info=True)
            return {}
    
    def _calculate_weather_score(self, weather: Dict[str, Any]) -> float:
        """
        Calculate weather suitability score (0-1) for cycling.
        
        Uses the comfort_score from WeatherSnapshot if available,
        otherwise calculates based on temperature, wind, and precipitation.
        
        Args:
            weather: Weather data dictionary
            
        Returns:
            Score from 0.0 (terrible) to 1.0 (perfect)
        """
        if not weather:
            return 0.5  # Neutral score if no weather data
        
        # Use pre-calculated comfort_score if available
        if 'comfort_score' in weather:
            return weather['comfort_score']
        
        # Fallback: calculate score manually
        score = 1.0
        
        # Temperature scoring (optimal: 15-25°C / 59-77°F)
        temp_c = weather.get('temperature_c', weather.get('temperature', 20))
        if isinstance(temp_c, (int, float)):
            if temp_c < 0:
                score -= 0.4
            elif temp_c < 10:
                score -= 0.2
            elif temp_c > 30:
                score -= 0.3
            elif temp_c > 35:
                score -= 0.5
        
        # Wind scoring (unfavorable above 20 kph / 12 mph)
        wind_kph = weather.get('wind_speed_kph', weather.get('wind_speed', 0))
        if isinstance(wind_kph, (int, float)):
            if wind_kph > 30:
                score -= 0.3
            elif wind_kph > 20:
                score -= 0.15
        
        # Precipitation scoring
        precip_mm = weather.get('precipitation_mm', weather.get('precipitation', 0))
        if isinstance(precip_mm, (int, float)) and precip_mm > 0:
            if precip_mm > 5:
                score -= 0.4
            else:
                score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _get_weather_summary(self, weather: Optional[Dict[str, Any]]) -> str:
        """Generate human-readable weather summary."""
        if not weather:
            return "Weather data unavailable"
        
        temp = weather.get('temperature', 0)
        conditions = weather.get('conditions', 'Unknown')
        wind = weather.get('wind_speed', 0)
        
        return f"{temp}°F, {conditions}, Wind {wind} mph"
    
    def generate_long_rides_map(self,
                                long_rides: List[Dict[str, Any]],
                                home_location: Optional[Tuple[float, float]] = None) -> Optional[str]:
        """
        Generate an interactive map showing all recommended long rides.
        
        Args:
            long_rides: List of long ride recommendations (from get_recommendations)
            home_location: Optional (lat, lon) tuple for home marker
            
        Returns:
            Folium HTML string or None if generation fails
        """
        if not long_rides:
            logger.warning("No long rides provided for map generation")
            return None
        
        try:
            # Collect all rides from all days
            all_rides = []
            for day_rec in long_rides:
                for ride in day_rec.get('rides', []):
                    # Avoid duplicates
                    if not any(r['ride_id'] == ride['ride_id'] for r in all_rides):
                        all_rides.append(ride)
            
            if not all_rides:
                logger.warning("No rides found in recommendations")
                return None
            
            # Calculate map center from all ride locations
            all_lats = []
            all_lons = []
            for ride in all_rides:
                start_loc = ride.get('start_location', [])
                if len(start_loc) == 2:
                    all_lats.append(start_loc[0])
                    all_lons.append(start_loc[1])
            
            if home_location:
                all_lats.append(home_location[0])
                all_lons.append(home_location[1])
            
            center_lat = sum(all_lats) / len(all_lats) if all_lats else 0
            center_lon = sum(all_lons) / len(all_lons) if all_lons else 0
            
            # Create base map
            map_obj = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=12,
                tiles=None,
                control_scale=True
            )
            
            # Add tile layers
            folium.TileLayer(
                tiles='OpenStreetMap',
                name='OpenStreetMap',
                overlay=False,
                control=True
            ).add_to(map_obj)
            
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satellite',
                overlay=False,
                control=True
            ).add_to(map_obj)
            
            folium.TileLayer(
                tiles='CartoDB positron',
                name='Light',
                overlay=False,
                control=True
            ).add_to(map_obj)
            
            # Add home marker if provided
            if home_location:
                folium.Marker(
                    home_location,
                    popup="<b>Home</b>",
                    tooltip="Home",
                    icon=folium.Icon(color='green', icon='home', prefix='fa')
                ).add_to(map_obj)
            
            # Track all coordinates for bounds
            all_bounds = []
            if home_location:
                all_bounds.append(list(home_location))
            
            # Add each long ride as a layer
            weather_overlay = folium.FeatureGroup(name='Weather Overlay', show=False)
            
            for idx, ride in enumerate(all_rides):
                ride_obj = None
                if self._long_rides:
                    ride_obj = next((r for r in self._long_rides if r.activity_id == ride['ride_id']), None)
                
                if not ride_obj or not ride_obj.coordinates:
                    logger.warning(f"Skipping ride {ride['ride_id']}: no coordinates")
                    continue
                
                weather = ride.get('weather', {}) or {}
                weather_score = ride.get('weather_score', 0.5)
                route_status = self._get_weather_status(weather_score)
                route_color = self._get_weather_color(weather_score)
                
                popup_html = f"""
                <div style="font-family: Arial, sans-serif; min-width: 250px;">
                    <h4 style="margin: 0 0 10px 0; color: #2c3e50;">{escape(ride.get('name', 'Unknown Ride'))}</h4>
                    <div style="margin-bottom: 8px;">
                        <strong>📏 Distance:</strong> {ride.get('distance', 0):.1f} km<br>
                        <strong>⏱️ Duration:</strong> {ride.get('duration', 0):.1f} hr<br>
                        <strong>⛰️ Elevation:</strong> {ride.get('elevation', 0):.0f} m<br>
                        <strong>⭐ Score:</strong> {ride.get('score', 0) * 100:.0f}%
                    </div>
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd;">
                        <strong>Weather Status:</strong> <span style="color: {route_color}; font-weight: bold;">{route_status}</span><br>
                        <strong>Weather Score:</strong> {weather_score * 100:.0f}%<br>
                        <strong>Variety Score:</strong> {ride.get('variety_score', 0) * 100:.0f}%<br>
                        <strong>Forecast:</strong> {escape(self._get_weather_summary(weather))}
                    </div>
                    {'<div style="margin-top: 8px;"><span style="background: #6f42c1; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.85em;">🔄 Loop</span></div>' if ride.get('is_loop') else ''}
                </div>
                """
                
                feature_group = folium.FeatureGroup(
                    name=f"{ride.get('name', 'Unknown')} ({route_status})",
                    show=True
                )
                
                self._add_weather_segmented_route(
                    feature_group=feature_group,
                    coordinates=ride_obj.coordinates,
                    weather_score=weather_score,
                    popup_html=popup_html,
                    ride_name=ride.get('name', 'Unknown'),
                    ride_distance=ride.get('distance', 0)
                )
                
                folium.CircleMarker(
                    ride_obj.start_location,
                    radius=6,
                    color=route_color,
                    fill=True,
                    fillColor='white',
                    fillOpacity=1,
                    weight=2,
                    popup=f"<b>Start:</b> {escape(ride.get('name', 'Unknown'))}",
                    tooltip="Start"
                ).add_to(feature_group)
                
                if not ride.get('is_loop'):
                    folium.CircleMarker(
                        ride_obj.end_location,
                        radius=6,
                        color=route_color,
                        fill=True,
                        fillColor='black',
                        fillOpacity=1,
                        weight=2,
                        popup=f"<b>End:</b> {escape(ride.get('name', 'Unknown'))}",
                        tooltip="End"
                    ).add_to(feature_group)
                
                self._add_weather_forecast_markers(weather_overlay, ride_obj, ride)
                feature_group.add_to(map_obj)
                all_bounds.extend([[lat, lon] for lat, lon in ride_obj.coordinates])
            
            # Fit map to show all rides
            if all_bounds:
                map_obj.fit_bounds(all_bounds, padding=(30, 30))
            
            if weather_overlay._children:
                weather_overlay.add_to(map_obj)
            
            # Add layer control
            folium.LayerControl(collapsed=False).add_to(map_obj)
            
            return map_obj._repr_html_()
            
        except Exception as e:
            logger.error(f"Failed to generate long rides map: {e}", exc_info=True)
            return None

    def _get_weather_status(self, weather_score: float) -> str:
        """Return friendly weather status for a route."""
        if weather_score >= 0.7:
            return 'Favorable'
        if weather_score >= 0.5:
            return 'Acceptable'
        return 'Unfavorable'
    
    def _get_weather_color(self, weather_score: float) -> str:
        """Semantic weather color for route display."""
        if weather_score >= 0.7:
            return '#28a745'
        if weather_score >= 0.5:
            return '#ffc107'
        return '#dc3545'
    
    def _add_weather_segmented_route(self,
                                     feature_group: folium.FeatureGroup,
                                     coordinates: List[Tuple[float, float]],
                                     weather_score: float,
                                     popup_html: str,
                                     ride_name: str,
                                     ride_distance: float) -> None:
        """Draw route segments with semantic weather coloring."""
        if len(coordinates) < 2:
            return
        
        segment_count = min(6, max(3, len(coordinates) // 20))
        chunk_size = max(2, len(coordinates) // segment_count)
        
        for start_idx in range(0, len(coordinates) - 1, chunk_size):
            segment = coordinates[start_idx:start_idx + chunk_size + 1]
            if len(segment) < 2:
                continue
            
            adjusted_score = weather_score
            if start_idx > len(coordinates) * 0.66:
                adjusted_score = max(0.0, weather_score - 0.15)
            elif start_idx > len(coordinates) * 0.33:
                adjusted_score = max(0.0, weather_score - 0.05)
            
            color = self._get_weather_color(adjusted_score)
            folium.PolyLine(
                segment,
                color=color,
                weight=6,
                opacity=0.9,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"{ride_name} • {ride_distance:.1f} km • {self._get_weather_status(adjusted_score)}"
            ).add_to(feature_group)
    
    def _add_weather_forecast_markers(self,
                                      weather_overlay: folium.FeatureGroup,
                                      ride_obj: LongRide,
                                      ride: Dict[str, Any]) -> None:
        """Add forecast markers at start, midpoint, and end for long ride routes."""
        points = [
            ('Start', ride_obj.coordinates[0]),
            ('Midpoint', ride_obj.coordinates[len(ride_obj.coordinates) // 2]),
            ('End', ride_obj.coordinates[-1]),
        ]
        weather = ride.get('weather', {}) or {}
        route_color = self._get_weather_color(ride.get('weather_score', 0.5))
        
        for label, point in points:
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; min-width: 220px;">
                <h4 style="margin: 0 0 10px 0;">{escape(ride.get('name', 'Unknown Ride'))} {label}</h4>
                <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                    <tr><td><b>Forecast</b></td><td>{escape(self._get_weather_summary(weather))}</td></tr>
                    <tr><td><b>Weather Score</b></td><td>{ride.get('weather_score', 0) * 100:.0f}%</td></tr>
                    <tr><td><b>Status</b></td><td>{self._get_weather_status(ride.get('weather_score', 0.5))}</td></tr>
                </table>
            </div>
            """
            folium.CircleMarker(
                point,
                radius=7,
                color=route_color,
                fill=True,
                fillColor=route_color,
                fillOpacity=0.65,
                weight=2,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{label} forecast"
            ).add_to(weather_overlay)

# Made with Bob
