"""
Route Sorter Service

Sorts routes by various criteria (uses, distance, name, etc.).

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import List, Dict, Any, Literal

logger = logging.getLogger(__name__)

SortField = Literal['uses', 'distance', 'name', 'duration', 'elevation']


class RouteSorter:
    """
    Sorts routes by various criteria.
    
    Responsible only for sorting logic. Does not load or filter routes.
    """
    
    VALID_SORT_FIELDS = {'uses', 'distance', 'name', 'duration', 'elevation', 'recent'}
    
    @staticmethod
    def sort(routes: List[Dict[str, Any]], sort_by: str = 'uses', reverse: bool = True) -> List[Dict[str, Any]]:
        """
        Sort routes by the specified field.
        
        Args:
            routes: List of route dictionaries
            sort_by: Field to sort by ('uses', 'distance', 'name', 'duration', 'elevation', 'recent')
            reverse: If True, sort in descending order
            
        Returns:
            Sorted list of routes
        """
        if sort_by not in RouteSorter.VALID_SORT_FIELDS:
            logger.warning(f"Invalid sort field: {sort_by}, defaulting to 'uses'")
            sort_by = 'uses'
        
        # Make a copy to avoid modifying the original list
        sorted_routes = routes.copy()
        
        if sort_by == 'uses':
            sorted_routes.sort(key=lambda r: r.get('uses', 0), reverse=reverse)
        elif sort_by == 'distance':
            sorted_routes.sort(key=lambda r: r.get('distance', 0), reverse=reverse)
        elif sort_by == 'name':
            sorted_routes.sort(key=lambda r: r.get('name', ''), reverse=reverse)
        elif sort_by == 'duration':
            sorted_routes.sort(key=lambda r: r.get('duration', 0), reverse=reverse)
        elif sort_by == 'elevation':
            sorted_routes.sort(key=lambda r: r.get('elevation', 0), reverse=reverse)
        elif sort_by == 'recent':
            sorted_routes.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
        
        logger.debug(f"Sorted {len(sorted_routes)} routes by {sort_by} (reverse={reverse})")
        return sorted_routes
    
    @staticmethod
    def sort_uses_descending(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort routes by usage count (most used first).
        
        Args:
            routes: List of route dictionaries
            
        Returns:
            Sorted list of routes
        """
        return RouteSorter.sort(routes, 'uses', reverse=True)
    
    @staticmethod
    def sort_distance_descending(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort routes by distance (longest first).
        
        Args:
            routes: List of route dictionaries
            
        Returns:
            Sorted list of routes
        """
        return RouteSorter.sort(routes, 'distance', reverse=True)
    
    @staticmethod
    def sort_name_ascending(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort routes by name (alphabetically).
        
        Args:
            routes: List of route dictionaries
            
        Returns:
            Sorted list of routes
        """
        return RouteSorter.sort(routes, 'name', reverse=False)
    
    @staticmethod
    def sort_recent_first(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort routes by recency (most recent first).
        
        Args:
            routes: List of route dictionaries
            
        Returns:
            Sorted list of routes
        """
        return RouteSorter.sort(routes, 'recent', reverse=True)
