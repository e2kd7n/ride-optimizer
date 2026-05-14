"""
Refactored Route Library Service

Orchestrates route loading, filtering, sorting, and formatting.
This service now acts as an orchestrator using extracted helper classes
instead of handling all concerns itself.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import List, Dict, Any, Optional

from src.config_manager import ConfigManager
from app.services.route_loader import RouteLoader
from app.services.route_filter import RouteFilter
from app.services.route_sorter import RouteSorter
from app.services.route_formatter import RouteFormatter
from app.services.route_cache import RouteCache

logger = logging.getLogger(__name__)


class RouteLibraryService:
    """
    Service for managing route library operations.
    
    This service orchestrates the following extracted components:
    - RouteLoader: Loads routes from JSON files
    - RouteFilter: Filters routes by type, direction, etc.
    - RouteSorter: Sorts routes by various criteria
    - RouteFormatter: Formats routes for API responses
    - RouteCache: Caches route data in memory
    
    BEFORE (monolithic):
        - Single class doing loading, filtering, sorting, formatting, caching
        - 500+ line methods mixing concerns
        - Hard to test individual aspects
        - Hard to reuse components
    
    AFTER (refactored):
        - Each concern is a separate, focused class
        - Service orchestrates the flow
        - Each component is independently testable
        - Components are easily reusable
    """
    
    def __init__(self, data_dir: str = 'data'):
        """
        Initialize RouteLibraryService.
        
        Args:
            data_dir: Directory containing route data files
        """
        self.config_mgr = ConfigManager.get_instance()
        self.loader = RouteLoader(data_dir)
        self.filter = RouteFilter()
        self.sorter = RouteSorter()
        self.formatter = RouteFormatter()
        
        # Cache with TTL from config (default 1 hour)
        cache_ttl = self.config_mgr.get('services.route_library.cache_ttl_seconds', 3600)
        self.cache = RouteCache(ttl_seconds=cache_ttl)
        
        logger.info("RouteLibraryService initialized")
    
    def get_all_routes(self, route_type: str = 'all', sort_by: str = 'uses',
                      limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get all routes with filtering, sorting, and formatting.
        
        This method demonstrates the orchestration pattern:
        1. Load routes from disk
        2. Filter by type
        3. Sort by specified criterion
        4. Format for API response
        5. Apply limit if specified
        
        Args:
            route_type: 'all', 'commute', or 'long_ride'
            sort_by: 'uses', 'distance', 'name', 'duration', 'elevation', 'recent'
            limit: Maximum number of routes to return
            
        Returns:
            API response with routes and metadata
        """
        # Check cache first
        cache_key = f"all_routes_{route_type}_{sort_by}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Returning cached routes for {cache_key}")
            return self.formatter.format_api_response(cached_result, len(cached_result))
        
        # Load from disk
        all_routes = self._load_all_routes()
        
        # Filter
        filtered = self.filter.by_type(all_routes, route_type)
        
        # Sort
        sorted_routes = self.sorter.sort(filtered, sort_by)
        
        # Cache the result
        self.cache.set(cache_key, sorted_routes)
        
        # Apply limit
        if limit:
            sorted_routes = sorted_routes[:limit]
        
        # Format and return
        return self.formatter.format_api_response(sorted_routes, len(filtered))
    
    def get_routes_by_type(self, route_type: str, sort_by: str = 'uses') -> Dict[str, Any]:
        """
        Get routes filtered by type.
        
        Args:
            route_type: 'commute' or 'long_ride'
            sort_by: Sort criterion
            
        Returns:
            API response with filtered and sorted routes
        """
        return self.get_all_routes(route_type=route_type, sort_by=sort_by)
    
    def get_route_by_id(self, route_id: str, route_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a single route by ID.
        
        Args:
            route_id: Route ID
            route_type: Optional filter by route type
            
        Returns:
            Formatted route or None if not found
        """
        all_routes = self._load_all_routes()
        
        for route in all_routes:
            if route.get('id') == route_id:
                if route_type and route.get('type') != route_type:
                    continue
                return self.formatter.format_single_route(route)
        
        logger.warning(f"Route {route_id} not found")
        return None
    
    def search_routes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search routes by name.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching routes
        """
        all_routes = self._load_all_routes()
        query_lower = query.lower()
        
        matches = [
            r for r in all_routes
            if query_lower in r.get('name', '').lower()
        ]
        
        return self.formatter.format_routes_list(matches[:limit])
    
    def get_routes_with_filters(self, route_type: str = 'all', direction: str = 'all',
                               sort_by: str = 'uses', min_distance: Optional[float] = None,
                               max_distance: Optional[float] = None,
                               min_uses: int = 1) -> Dict[str, Any]:
        """
        Get routes with advanced filtering.
        
        Demonstrates chaining multiple filters:
        
        Args:
            route_type: Route type filter
            direction: Route direction filter ('home_to_work', 'work_to_home', 'all')
            sort_by: Sort criterion
            min_distance: Minimum distance in km
            max_distance: Maximum distance in km
            min_uses: Minimum number of uses
            
        Returns:
            API response with filtered routes
        """
        # Load
        all_routes = self._load_all_routes()
        
        # Apply filters in sequence
        filtered = self.filter.by_type(all_routes, route_type)
        filtered = self.filter.by_direction(filtered, direction)
        filtered = self.filter.by_min_uses(filtered, min_uses)
        
        if min_distance is not None:
            filtered = self.filter.by_min_distance(filtered, min_distance)
        if max_distance is not None:
            filtered = self.filter.by_max_distance(filtered, max_distance)
        
        # Sort
        sorted_routes = self.sorter.sort(filtered, sort_by)
        
        # Format
        return self.formatter.format_api_response(sorted_routes, len(filtered))
    
    def invalidate_cache(self, route_type: Optional[str] = None) -> None:
        """
        Invalidate the route cache.
        
        Args:
            route_type: If specified, only invalidate cache for this type
        """
        if route_type:
            cache_key = f"all_routes_{route_type}"
            self.cache.invalidate(cache_key)
            logger.info(f"Invalidated cache for {route_type}")
        else:
            self.cache.clear()
            logger.info("Cleared entire route cache")
    
    def _load_all_routes(self) -> List[Dict[str, Any]]:
        """
        Load all routes (commute and long rides) from disk.
        
        Internal helper method.
        
        Returns:
            Combined list of all routes
        """
        commute_routes = self.loader.load_commute_routes()
        long_rides = self.loader.load_long_rides()
        
        return commute_routes + long_rides
