"""
Weather Service - Production implementation wrapping WeatherFetcher.

Provides weather data integration for the web platform by wrapping
the existing WeatherFetcher from src/weather_fetcher.py.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging

from src.weather_fetcher import WeatherFetcher, WindImpactCalculator
from src.config import Config

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Weather service for web platform.
    
    Wraps WeatherFetcher to provide weather data for routes and locations.
    Implements caching and error handling for production use.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize weather service.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or Config()
        self.enabled = True
        
        try:
            # Initialize WeatherFetcher with caching
            cache_dir = self.config.get('cache_dir', 'cache')
            cache_file = f"{cache_dir}/weather_cache.json"
            
            self.fetcher = WeatherFetcher(
                cache_radius_km=2.0,
                cache_duration_hours=1.5,
                cache_file=cache_file
            )
            self.wind_calculator = WindImpactCalculator()
            logger.info("WeatherService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WeatherService: {e}")
            self.enabled = False
            self.fetcher = None
            self.wind_calculator = None
    
    def get_current_weather(self, location: str = None, lat: float = None, 
                           lon: float = None) -> Optional[Dict[str, Any]]:
        """
        Get current weather conditions for a location.
        
        Args:
            location: Location name (not used, for API compatibility)
            lat: Latitude
            lon: Longitude
            
        Returns:
            Dictionary with current weather or None if unavailable
        """
        if not self.enabled or not self.fetcher:
            logger.warning("WeatherService not available")
            return None
        
        if lat is None or lon is None:
            logger.warning("Latitude and longitude required for weather lookup")
            return None
        
        try:
            conditions = self.fetcher.get_current_conditions(lat, lon)
            if conditions:
                return {
                    'temperature': conditions.get('temp_c'),
                    'wind_speed': conditions.get('wind_speed_kph'),
                    'wind_direction': conditions.get('wind_direction_deg'),
                    'wind_direction_cardinal': conditions.get('wind_direction_cardinal'),
                    'humidity': conditions.get('humidity'),
                    'precipitation': conditions.get('precipitation_mm'),
                    'timestamp': conditions.get('timestamp'),
                    'conditions': self._describe_conditions(conditions)
                }
            return None
            
        except Exception as e:
            logger.error(f"Error fetching current weather: {e}")
            return None
    
    def get_weather_snapshot(self, lat: float, lon: float, 
                            departure_time: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Get weather snapshot for a specific time and location.
        
        Args:
            lat: Latitude
            lon: Longitude
            departure_time: When the ride will start (defaults to now)
            
        Returns:
            Weather snapshot dictionary or None
        """
        if not self.enabled or not self.fetcher:
            return None
        
        if departure_time is None:
            departure_time = datetime.now()
        
        try:
            # If departure is within next hour, use current conditions
            time_until_departure = (departure_time - datetime.now()).total_seconds() / 3600
            
            if time_until_departure <= 1.0:
                conditions = self.fetcher.get_current_conditions(lat, lon)
                if conditions:
                    return {
                        'temperature': conditions.get('temp_c'),
                        'wind_speed': conditions.get('wind_speed_kph'),
                        'wind_direction': conditions.get('wind_direction_deg'),
                        'conditions': self._describe_conditions(conditions),
                        'precipitation_probability': 0 if conditions.get('precipitation_mm', 0) == 0 else 100,
                        'timestamp': departure_time.isoformat()
                    }
            else:
                # Use hourly forecast for future times
                hours_ahead = int(time_until_departure) + 1
                forecast = self.fetcher.get_hourly_forecast(lat, lon, hours=hours_ahead)
                
                if forecast and len(forecast) > 0:
                    # Find closest forecast to departure time
                    target_hour = departure_time.replace(minute=0, second=0, microsecond=0)
                    closest_forecast = min(forecast, 
                                         key=lambda f: abs(datetime.fromisoformat(f['timestamp']) - target_hour))
                    
                    return {
                        'temperature': closest_forecast.get('temp_c'),
                        'wind_speed': closest_forecast.get('wind_speed_kph'),
                        'wind_direction': closest_forecast.get('wind_direction_deg'),
                        'conditions': self._describe_forecast(closest_forecast),
                        'precipitation_probability': closest_forecast.get('precipitation_prob', 0),
                        'timestamp': departure_time.isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting weather snapshot: {e}")
            return None
    
    def get_route_weather(self, coordinates: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
        """
        Get weather conditions along a route.
        
        Args:
            coordinates: List of (lat, lon) tuples
            
        Returns:
            Weather data for the route or None
        """
        if not self.enabled or not self.fetcher:
            return None
        
        if not coordinates or len(coordinates) < 2:
            return None
        
        try:
            weather = self.fetcher.get_route_weather(coordinates)
            if weather:
                return {
                    'temperature': weather.get('temp_c'),
                    'wind_speed': weather.get('wind_speed_kph'),
                    'wind_direction': weather.get('wind_direction_deg'),
                    'wind_direction_cardinal': weather.get('wind_direction_cardinal'),
                    'humidity': weather.get('humidity'),
                    'precipitation': weather.get('precipitation_mm'),
                    'conditions': self._describe_conditions(weather),
                    'samples': weather.get('samples', 0)
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting route weather: {e}")
            return None
    
    def analyze_wind_impact(self, coordinates: List[Tuple[float, float]], 
                           wind_speed: float, wind_direction: float) -> Optional[Dict[str, Any]]:
        """
        Analyze wind impact on a route.
        
        Args:
            coordinates: List of (lat, lon) tuples
            wind_speed: Wind speed in km/h
            wind_direction: Wind direction in degrees
            
        Returns:
            Wind impact analysis or None
        """
        if not self.enabled or not self.wind_calculator:
            return None
        
        if not coordinates or len(coordinates) < 2:
            return None
        
        try:
            return self.wind_calculator.analyze_route_wind_impact(
                coordinates, wind_speed, wind_direction
            )
        except Exception as e:
            logger.error(f"Error analyzing wind impact: {e}")
            return None
    
    def get_daily_forecast(self, lat: float, lon: float, days: int = 7) -> Optional[List[Dict]]:
        """
        Get daily weather forecast.
        
        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days (max 7)
            
        Returns:
            List of daily forecasts or None
        """
        if not self.enabled or not self.fetcher:
            return None
        
        try:
            return self.fetcher.get_daily_forecast(lat, lon, days)
        except Exception as e:
            logger.error(f"Error getting daily forecast: {e}")
            return None
    
    @staticmethod
    def _describe_conditions(weather: Dict) -> str:
        """
        Generate human-readable weather description.
        
        Args:
            weather: Weather data dictionary
            
        Returns:
            Description string
        """
        temp = weather.get('temp_c', 0)
        precip = weather.get('precipitation_mm', 0)
        wind = weather.get('wind_speed_kph', 0)
        
        conditions = []
        
        # Temperature
        if temp < 0:
            conditions.append("Freezing")
        elif temp < 10:
            conditions.append("Cold")
        elif temp < 20:
            conditions.append("Cool")
        elif temp < 25:
            conditions.append("Mild")
        elif temp < 30:
            conditions.append("Warm")
        else:
            conditions.append("Hot")
        
        # Precipitation
        if precip > 5:
            conditions.append("Heavy rain")
        elif precip > 1:
            conditions.append("Rain")
        elif precip > 0:
            conditions.append("Light rain")
        else:
            conditions.append("Clear")
        
        # Wind
        if wind > 30:
            conditions.append("Very windy")
        elif wind > 20:
            conditions.append("Windy")
        
        return ", ".join(conditions)
    
    @staticmethod
    def _describe_forecast(forecast: Dict) -> str:
        """
        Generate description from forecast data.
        
        Args:
            forecast: Forecast data dictionary
            
        Returns:
            Description string
        """
        temp = forecast.get('temp_c', 0)
        precip_prob = forecast.get('precipitation_prob', 0)
        
        conditions = []
        
        if temp < 10:
            conditions.append("Cold")
        elif temp < 20:
            conditions.append("Cool")
        elif temp < 25:
            conditions.append("Mild")
        else:
            conditions.append("Warm")
        
        if precip_prob > 70:
            conditions.append("Likely rain")
        elif precip_prob > 40:
            conditions.append("Possible rain")
        else:
            conditions.append("Clear")
        
        return ", ".join(conditions)


# Made with Bob
