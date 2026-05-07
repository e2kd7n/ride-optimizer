"""
TrainerRoad Service - Workout integration (STUB).

This is a temporary stub to unblock testing.
Will be replaced when Issue #139 (TrainerRoad Integration) is complete.
"""

import logging

logger = logging.getLogger(__name__)


class TrainerRoadService:
    """
    Stub service for TrainerRoad workout integration.
    
    TODO: Implement actual TrainerRoad integration (Issue #139)
    """
    
    def __init__(self):
        """Initialize TrainerRoad service stub."""
        logger.warning("TrainerRoadService is a stub - Issue #139 incomplete")
    
    def get_workout_fit(self, route_distance: float, route_duration: float) -> dict:
        """
        Get workout fit assessment (stub).
        
        Args:
            route_distance: Route distance in meters
            route_duration: Route duration in seconds
            
        Returns:
            Dictionary with workout fit data
        """
        return {
            'status': 'unavailable',
            'message': 'TrainerRoad integration not implemented',
            'fit_score': None
        }
    
    def get_today_workout(self) -> dict:
        """
        Get today's planned workout (stub).
        
        Returns:
            Dictionary with workout data
        """
        return {
            'status': 'unavailable',
            'message': 'TrainerRoad integration not implemented',
            'workout': None
        }


# Made with Bob