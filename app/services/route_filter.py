"""
Route Filter Service

Filters routes by type, direction, and other criteria.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RouteFilter:
    """
    Filters routes by various criteria.
    
    Responsible only for filtering logic. Does not load or sort routes.
    """
    
    # Valid route types
    VALID_TYPES = {'all', 'commute', 'long_ride'}
    VALID_DIRECTIONS = {'all', 'home_to_work', 'work_to_home'}
    
    @staticmethod
    def by_type(routes: List[Dict[str, Any]], route_type: str) -> List[Dict[str, Any]]:
        """
        Filter routes by type.
        
        Args:
            routes: List of route dictionaries
            route_type: 'all', 'commute', or 'long_ride'
            
        Returns:
            Filtered list of routes
        """
        if route_type not in RouteFilter.VALID_TYPES:
            logger.warning(f"Invalid route type: {route_type}, returning all routes")
            route_type = 'all'
        
        if route_type == 'all':
            return routes
        
        filtered = [r for r in routes if r.get('type', '').lower() == route_type]
        logger.debug(f"Filtered {len(filtered)} routes by type={route_type}")
        return filtered
    
    @staticmethod
    def by_direction(routes: List[Dict[str, Any]], direction: str) -> List[Dict[str, Any]]:
        """
        Filter routes by direction.
        
        Args:
            routes: List of route dictionaries
            direction: 'all', 'home_to_work', or 'work_to_home'
            
        Returns:
            Filtered list of routes
        """
        if direction not in RouteFilter.VALID_DIRECTIONS:
            logger.warning(f"Invalid direction: {direction}, returning all routes")
            direction = 'all'
        
        if direction == 'all':
            return routes
        
        filtered = [r for r in routes if r.get('direction', '') == direction]
        logger.debug(f"Filtered {len(filtered)} routes by direction={direction}")
        return filtered
    
    @staticmethod
    def by_plus_routes(routes: List[Dict[str, Any]], show_plus: bool = True) -> List[Dict[str, Any]]:
        """
        Filter routes by plus route status.
        
        Plus routes are longer commutes (>15% above median distance).
        
        Args:
            routes: List of route dictionaries
            show_plus: If True, show all routes. If False, hide plus routes.
            
        Returns:
            Filtered list of routes
        """
        if show_plus:
            return routes
        
        filtered = [r for r in routes if not r.get('is_plus_route', False)]
        logger.debug(f"Filtered {len(filtered)} routes (excluded plus routes)")
        return filtered
    
    @staticmethod
    def by_min_distance(routes: List[Dict[str, Any]], min_km: float) -> List[Dict[str, Any]]:
        """
        Filter routes by minimum distance.
        
        Args:
            routes: List of route dictionaries
            min_km: Minimum distance in kilometers
            
        Returns:
            Filtered list of routes
        """
        filtered = [r for r in routes if (r.get('distance', 0) / 1000) >= min_km]
        logger.debug(f"Filtered {len(filtered)} routes with distance >= {min_km}km")
        return filtered
    
    @staticmethod
    def by_max_distance(routes: List[Dict[str, Any]], max_km: float) -> List[Dict[str, Any]]:
        """
        Filter routes by maximum distance.
        
        Args:
            routes: List of route dictionaries
            max_km: Maximum distance in kilometers
            
        Returns:
            Filtered list of routes
        """
        filtered = [r for r in routes if (r.get('distance', 0) / 1000) <= max_km]
        logger.debug(f"Filtered {len(filtered)} routes with distance <= {max_km}km")
        return filtered
    
    @staticmethod
    def by_min_uses(routes: List[Dict[str, Any]], min_uses: int) -> List[Dict[str, Any]]:
        """
        Filter routes by minimum number of uses.
        
        Args:
            routes: List of route dictionaries
            min_uses: Minimum number of times route was used
            
        Returns:
            Filtered list of routes
        """
        filtered = [r for r in routes if r.get('uses', 0) >= min_uses]
        logger.debug(f"Filtered {len(filtered)} routes with uses >= {min_uses}")
        return filtered
