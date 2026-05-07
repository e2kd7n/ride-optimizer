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
from datetime import datetime, time, date

from src.next_commute_recommender import NextCommuteRecommender, CommuteRecommendation
from src.route_analyzer import RouteGroup
from src.location_finder import Location
from src.config import Config
from app.services.trainerroad_service import TrainerRoadService
from app.models.workouts import WorkoutMetadata

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
        self.trainerroad_service = TrainerRoadService(config)
    
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
