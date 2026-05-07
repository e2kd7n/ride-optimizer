"""
Weather Service - Wrapper around WeatherFetcher with caching and degradation.

Provides:
- Smart caching with JSON file persistence
- Graceful degradation (stale data fallback)
- Wind impact analysis for routes
- Weather summary formatting for UI
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from src.weather_fetcher import WeatherFetcher, WindImpactCalculator
from src.config import Config
from src.json_storage import JSONStorage

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service layer for weather data with caching and graceful degradation.
    
    Features:
    - 2-hour fresh data window
    - 24-hour stale data fallback
    - JSON file persistence
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
        self.storage = JSONStorage()
    
    def _get_cache_key(self, lat: float, lon: float) -> str:
        """Generate cache key for location."""
        return f"{lat:.4f}_{lon:.4f}"
    
    def _calculate_comfort_score(self, weather_data: Dict[str, Any]) -> float:
        """
        Calculate cycling comfort score (0-1) based on weather conditions.
        
        Args:
            weather_data: Weather data dictionary
            
        Returns:
            Comfort score from 0.0 (terrible) to 1.0 (perfect)
        """
        score = 1.0
        
        # Temperature scoring (optimal: 15-25°C / 59-77°F)
        temp_c = weather_data.get('temperature_c', weather_data.get('temperature', 20))
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
        wind_kph = weather_data.get('wind_speed_kph', weather_data.get('wind_speed', 0))
        if isinstance(wind_kph, (int, float)):
            if wind_kph > 30:
                score -= 0.3
            elif wind_kph > 20:
                score -= 0.15
        
        # Precipitation scoring
        precip_mm = weather_data.get('precipitation_mm', weather_data.get('precipitation', 0))
        if isinstance(precip_mm, (int, float)) and precip_mm > 0:
            if precip_mm > 5:
                score -= 0.4
            else:
                score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _get_cycling_favorability(self, comfort_score: float) -> str:
        """
        Convert comfort score to favorability category.
        
        Args:
            comfort_score: Comfort score (0-1)
            
        Returns:
            'favorable', 'neutral', or 'unfavorable'
        """
        if comfort_score >= 0.7:
            return 'favorable'
        elif comfort_score >= 0.4:
            return 'neutral'
        else:
            return 'unfavorable'
    
    def _enrich_weather_data(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add comfort score and favorability to weather data.
        
        Args:
            weather_data: Raw weather data
            
        Returns:
            Enriched weather data with comfort metrics
        """
        comfort_score = self._calculate_comfort_score(weather_data)
        weather_data['comfort_score'] = comfort_score
        weather_data['cycling_favorability'] = self._get_cycling_favorability(comfort_score)
        return weather_data
    
    def get_current_weather(self, 
                           lat: float, 
                           lon: float,
                           location_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current weather with smart caching.
        
        Strategy:
        1. Check JSON cache for fresh data (< 2 hours old)
        2. If cache miss, fetch from API
        3. If API fails, use stale data (up to 24 hours old)
        4. Store successful fetches in JSON cache
        
        Args:
            lat: Latitude
            lon: Longitude
            location_name: Optional location name for display
            
        Returns:
            Dictionary with weather data including comfort_score and cycling_favorability
        """
        try:
            cache_key = self._get_cache_key(lat, lon)
            
            # Check cache first (2-hour fresh window)
            cache = self.storage.read('weather_cache.json', default={'locations': {}})
            
            if cache_key in cache['locations']:
                cached = cache['locations'][cache_key]
                timestamp = datetime.fromisoformat(cached['timestamp'])
                age_hours = (datetime.now() - timestamp).total_seconds() / 3600
                
                if age_hours < 2:
                    logger.info(f"Using cached weather for ({lat}, {lon}), age: {age_hours:.1f}h")
                    return cached['weather_data']
            
            # Cache miss - fetch fresh data
            logger.info(f"Fetching fresh weather for ({lat}, {lon})")
            weather_data = self.fetcher.get_current_conditions(lat, lon)
            
            if not weather_data:
                logger.warning(f"API returned no data for ({lat}, {lon}), trying degraded fallback")
                return self._get_degraded_weather(lat, lon, location_name)
            
            # Enrich with comfort metrics
            weather_data = self._enrich_weather_data(weather_data)
            
            # Store in JSON cache
            cache['locations'][cache_key] = {
                'weather_data': weather_data,
                'timestamp': datetime.now().isoformat(),
                'location_name': location_name or f"Location ({lat:.2f}, {lon:.2f})"
            }
            
            self.storage.write('weather_cache.json', cache)
            logger.info(f"Stored fresh weather snapshot for {location_name or 'location'}")
            
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
            cache_key = self._get_cache_key(lat, lon)
            cache = self.storage.read('weather_cache.json', default={'locations': {}})
            
            if cache_key in cache['locations']:
                cached = cache['locations'][cache_key]
                timestamp = datetime.fromisoformat(cached['timestamp'])
                age_hours = (datetime.now() - timestamp).total_seconds() / 3600
                
                # Accept stale data up to 24 hours old
                if age_hours < 24:
                    logger.warning(
                        f"Using stale weather data for ({lat}, {lon}), "
                        f"age: {age_hours:.1f}h"
                    )
                    data = cached['weather_data'].copy()
                    data['is_stale'] = True
                    data['age_hours'] = age_hours
                    return data
            
            logger.error(f"No weather data available for ({lat}, {lon}), even stale")
            return {}
            
        except Exception as e:
            logger.error(f"Error getting degraded weather: {e}", exc_info=True)
            return {}


# Made with Bob