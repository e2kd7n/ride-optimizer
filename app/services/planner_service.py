"""
Planner Service - Long ride planning and recommendations.

This service provides intelligent long ride recommendations based on:
- Weather forecasts (7-day window)
- Route variety and exploration
- Workout fit (TrainerRoad integration)
- Historical performance
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from src.long_ride_analyzer import LongRideAnalyzer, LongRide, RideRecommendation
from src.weather_fetcher import WeatherFetcher
from src.config import Config

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
        """Get weather forecast for a ride on a specific date."""
        # TODO: Implement actual weather fetching
        # For now, return placeholder
        return {
            'temperature': 70.0,
            'conditions': 'Clear',
            'wind_speed': 5.0,
            'wind_direction': 'N',
            'precipitation': 0.0
        }
    
    def _calculate_weather_score(self, weather: Dict[str, Any]) -> float:
        """Calculate weather suitability score (0-1)."""
        # TODO: Implement actual weather scoring
        # For now, return placeholder
        return 0.8
    
    def _get_weather_summary(self, weather: Optional[Dict[str, Any]]) -> str:
        """Generate human-readable weather summary."""
        if not weather:
            return "Weather data unavailable"
        
        temp = weather.get('temperature', 0)
        conditions = weather.get('conditions', 'Unknown')
        wind = weather.get('wind_speed', 0)
        
        return f"{temp}°F, {conditions}, Wind {wind} mph"

# Made with Bob
