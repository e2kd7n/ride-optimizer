"""
Weather Service - STUB IMPLEMENTATION
This is a temporary stub to unblock QA testing.
Will be replaced when Issue #138 (Weather Integration) is complete.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class WeatherService:
    """
    Stub weather service for QA testing.
    
    This minimal implementation allows the Flask app to start and QA tests to run.
    Real implementation will be provided by Integration Squad (Issue #138).
    """
    
    def __init__(self, config=None):
        """
        Initialize stub weather service.
        
        Args:
            config: Optional configuration object (ignored in stub)
        """
        self.config = config
        self.enabled = False
    
    def get_current_weather(self, location: str = None) -> Optional[Dict[str, Any]]:
        """
        Get current weather conditions (stub).
        
        Args:
            location: Location to get weather for
            
        Returns:
            None (stub implementation)
        """
        return None
    
    def get_forecast(self, location: str = None, days: int = 7) -> Optional[Dict[str, Any]]:
        """
        Get weather forecast (stub).
        
        Args:
            location: Location to get forecast for
            days: Number of days to forecast
            
        Returns:
            None (stub implementation)
        """
        return None
    
    def is_available(self) -> bool:
        """
        Check if weather service is available.
        
        Returns:
            False (stub always returns False)
        """
        return False
    
    def get_weather_impact(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate weather impact on cycling (stub).
        
        Args:
            conditions: Weather conditions
            
        Returns:
            Empty dict (stub implementation)
        """
        return {}

# Made with Bob
