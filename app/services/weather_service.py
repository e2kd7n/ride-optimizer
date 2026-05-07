"""
Weather Service - Wrapper around WeatherFetcher with caching and degradation.

Provides:
- Smart caching with SQLite persistence
- Graceful degradation (stale data fallback)
- Wind impact analysis for routes
- Weather summary formatting for UI
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from src.weather_fetcher import WeatherFetcher, WindImpactCalculator
from src.config import Config
from app.models.weather import WeatherSnapshot

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service layer for weather data with caching and graceful degradation.
    
    Features:
    - 2-hour fresh data window
    - 24-hour stale data fallback
    - SQLite persistence via WeatherSnapshot
    - Wind impact analysis for routes
    """
    
    def __init__(self, config: Config):
        """
        Initialize weather service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.fetcher = WeatherFetcher()
        self.wind_calculator = WindImpactCalculator()
    
    def get_current_weather(self, 
                           lat: float, 
                           lon: float,
                           location_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current weather with smart caching.
        
        Strategy:
        1. Check SQLite for fresh data (< 2 hours old)
        2. If cache miss, fetch from API
        3. If API fails, use stale data (up to 24 hours old)
        4. Store successful fetches in SQLite
        
        Args:
            lat: Latitude
            lon: Longitude
            location_name: Optional location name for display
            
        Returns:
            Dictionary with weather data including comfort_score and cycling_favorability
        """
        try:
            # Check cache first (2-hour fresh window)
            snapshot = WeatherSnapshot.get_current_for_location(lat, lon, max_age_hours=2)
            
            if snapshot:
                logger.info(f"Using cached weather for ({lat}, {lon}), age: {snapshot.age_hours:.1f}h")
                return snapshot.to_dict()
            
            # Cache miss - fetch fresh data
            logger.info(f"Fetching fresh weather for ({lat}, {lon})")
            weather_data = self.fetcher.get_current_conditions(lat, lon)
            
            if not weather_data:
                logger.warning(f"API returned no data for ({lat}, {lon}), trying degraded fallback")
                return self._get_degraded_weather(lat, lon, location_name)
            
            # Store in SQLite
            snapshot = WeatherSnapshot.create_from_weather_data(
                weather_data,
                location_name=location_name or f"Location ({lat:.2f}, {lon:.2f})",
                is_current=True
            )
            
            if snapshot:
                logger.info(f"Stored fresh weather snapshot for {location_name or 'location'}")
                return snapshot.to_dict()
            else:
                logger.warning("Failed to create weather snapshot, returning raw data")
                return weather_data
                
        except Exception as e:
            logger.error(f"Error getting current weather: {e}", exc_info=True)
            return self._get_degraded_weather(lat, lon, location_name)
    
    def get_route_weather(self,
                         coordinates: List[Tuple[float, float]],
                         route_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get weather for a route with wind impact analysis.
        
        Args:
            coordinates: List of (lat, lon) tuples along the route
            route_name: Optional route name for display
            
        Returns:
            Dictionary with weather data plus wind_impact analysis
        """
        if not coordinates:
            logger.warning("No coordinates provided for route weather")
            return {}
        
        try:
            # Use route start location for weather
            start_lat, start_lon = coordinates[0]
            
            # Get current weather
            weather = self.get_current_weather(start_lat, start_lon, location_name=route_name)
            
            if not weather:
                return {}
            
            # Add wind impact analysis if we have wind data
            wind_speed = weather.get('wind_speed_kph', 0)
            wind_direction = weather.get('wind_direction_degrees', 0)
            
            if wind_speed > 0 and wind_direction is not None:
                try:
                    wind_impact = self.wind_calculator.calculate_wind_impact(
                        coordinates,
                        wind_speed,
                        wind_direction
                    )
                    weather['wind_impact'] = wind_impact
                    logger.info(f"Added wind impact analysis for {route_name or 'route'}")
                except Exception as e:
                    logger.warning(f"Failed to calculate wind impact: {e}")
            
            return weather
            
        except Exception as e:
            logger.error(f"Error getting route weather: {e}", exc_info=True)
            return {}
    
    def get_weather_summary(self,
                           lat: float,
                           lon: float,
                           location_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get weather with formatted summary for UI display.
        
        Args:
            lat: Latitude
            lon: Longitude
            location_name: Optional location name
            
        Returns:
            Dictionary with weather data and formatted summary string
        """
        weather = self.get_current_weather(lat, lon, location_name)
        
        if not weather:
            return {
                'summary': 'Weather data unavailable',
                'available': False
            }
        
        # Format summary
        temp_f = weather.get('temperature_f', 0)
        conditions = weather.get('conditions', 'Unknown')
        wind_kph = weather.get('wind_speed_kph', 0)
        wind_mph = wind_kph * 0.621371
        
        summary = f"{temp_f:.0f}°F, {conditions}"
        if wind_kph > 0:
            summary += f", Wind {wind_mph:.0f} mph"
        
        weather['summary'] = summary
        weather['available'] = True
        
        return weather
    
    def _get_degraded_weather(self,
                             lat: float,
                             lon: float,
                             location_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get stale weather data as fallback (up to 24 hours old).
        
        Args:
            lat: Latitude
            lon: Longitude
            location_name: Optional location name
            
        Returns:
            Dictionary with stale weather data or empty dict if none available
        """
        try:
            # Try to get stale data (up to 24 hours old)
            snapshot = WeatherSnapshot.get_current_for_location(lat, lon, max_age_hours=24)
            
            if snapshot:
                logger.warning(
                    f"Using stale weather data for ({lat}, {lon}), "
                    f"age: {snapshot.age_hours:.1f}h"
                )
                data = snapshot.to_dict()
                data['is_stale'] = True
                data['age_hours'] = snapshot.age_hours
                return data
            
            logger.error(f"No weather data available for ({lat}, {lon}), even stale")
            return {}
            
        except Exception as e:
            logger.error(f"Error getting degraded weather: {e}", exc_info=True)
            return {}


# Made with Bob