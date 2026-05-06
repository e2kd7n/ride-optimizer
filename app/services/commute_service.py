"""
Commute Service - Next commute recommendations.

This service provides intelligent commute route recommendations based on:
- Time of day (morning/evening commute windows)
- Weather forecasts
- Historical route performance
- Workout fit (TrainerRoad integration)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, time

from src.next_commute_recommender import NextCommuteRecommender, CommuteRecommendation
from src.route_analyzer import RouteGroup
from src.location_finder import Location
from src.config import Config

logger = logging.getLogger(__name__)


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
            # Get recommendation
            recommendation = self._recommender.get_next_commute_recommendation(
                direction=direction
            )
            
            if not recommendation:
                return {
                    'status': 'error',
                    'message': 'No suitable commute route found',
                    'direction': direction,
                    'route': None
                }
            
            # Convert to web-friendly format
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
                'is_plus_route': route_group.is_plus_route
            },
            'score': rec.score,
            'breakdown': rec.breakdown,
            'is_today': rec.is_today,
            'window_start': rec.window_start.strftime('%H:%M'),
            'window_end': rec.window_end.strftime('%H:%M')
        }
        
        # Add weather if available
        if rec.forecast_weather:
            result['weather'] = rec.forecast_weather
        
        return result

# Made with Bob
