"""
Route Library Service - Refactored

Orchestrates route loading, filtering, sorting, caching, and formatting.
Uses extracted helper services (RouteLoader, RouteFilter, RouteSorter, etc.)
for clean separation of concerns.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import List, Dict, Any, Optional

from src.config_manager import ConfigManager
from .route_loader import RouteLoader
from .route_filter import RouteFilter
from .route_sorter import RouteSorter
from .route_formatter import RouteFormatter
from .route_cache import RouteCache

logger = logging.getLogger(__name__)


class RouteLibraryService:
    """
    Orchestrates route library operations using extracted helper services.
    
    Responsibilities:
    - Coordinate loading, filtering, sorting, and formatting of routes
    - Manage caching to avoid repeated operations
    - Provide clean API for route library operations
    
    Does NOT do:
    - File I/O (delegated to RouteLoader)
    - Filtering logic (delegated to RouteFilter)
    - Sorting logic (delegated to RouteSorter)
    - Formatting logic (delegated to RouteFormatter)
    - Caching implementation (delegated to RouteCache)
    """
    
    def __init__(self):
        """
        Initialize RouteLibraryService with extracted helper services.
        """
        self.config = ConfigManager.get_instance()
        
        # Initialize helper services
        data_dir = self.config.get('data_dir', 'data')
        self.loader = RouteLoader(data_dir)
        self.filter = RouteFilter()
        self.sorter = RouteSorter()
        self.formatter = RouteFormatter()
        
        # Initialize cache with TTL from config
        cache_ttl = self.config.get('cache.ttl_seconds', 3600)
        self.cache = RouteCache(ttl_seconds=cache_ttl)
        
        logger.info("RouteLibraryService initialized with extracted helper services")
    
    def get_all_routes(
        self,
        route_type: str = 'all',
        sort_by: str = 'uses',
        limit: Optional[int] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get all routes with optional filtering, sorting, and pagination.
        
        This method orchestrates the full pipeline:
        1. Check cache
        2. Load from disk (if not cached)
        3. Filter by type
        4. Sort by specified field
        5. Apply limit (pagination)
        6. Format for API response
        7. Cache for future calls
        
        Args:
            route_type: 'all', 'commute', or 'long_ride'
            sort_by: 'uses', 'distance', 'name', 'duration', 'elevation', 'recent'
            limit: Maximum number of routes to return
            use_cache: Whether to use cached results
            
        Returns:
            API response dictionary with formatted routes
        """
        # Generate cache key
        cache_key = f"routes_{route_type}_{sort_by}_{limit}"
        
        # Check cache
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Returning {len(cached)} routes from cache")
                return self.formatter.format_api_response(cached, len(cached))
        
        try:
            # Load routes from disk
            logger.debug("Loading routes from disk...")
            commute_routes = self.loader.load_commute_routes()
            long_rides = self.loader.load_long_rides()
            all_routes = commute_routes + long_rides
            
            if not all_routes:
                logger.warning("No routes found in data directory")
                return self.formatter.format_error_response("No routes available", 404)
            
            # Filter by type
            logger.debug(f"Filtering {len(all_routes)} routes by type={route_type}...")
            filtered = self.filter.by_type(all_routes, route_type)
            
            if not filtered:
                return self.formatter.format_api_response([], 0)
            
            # Sort
            logger.debug(f"Sorting {len(filtered)} routes by {sort_by}...")
            sorted_routes = self.sorter.sort(filtered, sort_by)
            
            # Apply limit
            total_count = len(sorted_routes)
            if limit:
                sorted_routes = sorted_routes[:limit]
            
            # Cache the result
            self.cache.set(cache_key, sorted_routes)
            
            # Format response
            return self.formatter.format_api_response(sorted_routes, total_count)
            
        except Exception as e:
            logger.error(f"Error getting routes: {e}", exc_info=True)
            return self.formatter.format_error_response(str(e), 500)
    
    def get_route_by_id(self, route_id: str, route_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a single route by ID.
        
        Args:
            route_id: Route ID to retrieve
            route_type: Optional filter by type ('commute' or 'long_ride')
            
        Returns:
            Formatted route dictionary or None if not found
        """
        try:
            # Load all routes
            commute_routes = self.loader.load_commute_routes()
            long_rides = self.loader.load_long_rides()
            all_routes = commute_routes + long_rides
            
            # Filter by type if specified
            if route_type:
                all_routes = self.filter.by_type(all_routes, route_type)
            
            # Find route by ID
            for route in all_routes:
                if route.get('id') == route_id:
                    return self.formatter.format_single_route(route)
            
            logger.warning(f"Route not found: {route_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting route {route_id}: {e}", exc_info=True)
            return None
    
    def get_commute_routes(
        self,
        sort_by: str = 'uses',
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get commute routes (convenience method).
        
        Args:
            sort_by: Field to sort by
            limit: Maximum routes to return
            
        Returns:
            API response with commute routes
        """
        return self.get_all_routes(route_type='commute', sort_by=sort_by, limit=limit)
    
    def get_long_rides(
        self,
        sort_by: str = 'uses',
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get long ride routes (convenience method).
        
        Args:
            sort_by: Field to sort by
            limit: Maximum routes to return
            
        Returns:
            API response with long rides
        """
        return self.get_all_routes(route_type='long_ride', sort_by=sort_by, limit=limit)
    
    def search_routes(self, query: str) -> Dict[str, Any]:
        """
        Search routes by name.
        
        Args:
            query: Search query
            
        Returns:
            API response with matching routes
        """
        try:
            # Load routes
            commute_routes = self.loader.load_commute_routes()
            long_rides = self.loader.load_long_rides()
            all_routes = commute_routes + long_rides
            
            # Search by name (case-insensitive)
            query_lower = query.lower()
            matching = [r for r in all_routes if query_lower in r.get('name', '').lower()]
            
            logger.debug(f"Found {len(matching)} routes matching '{query}'")
            return self.formatter.format_api_response(matching, len(matching))
            
        except Exception as e:
            logger.error(f"Error searching routes: {e}", exc_info=True)
            return self.formatter.format_error_response(str(e), 500)
    
    def clear_cache(self) -> None:
        """
        Clear the route cache.
        
        Useful after updating route data.
        """
        self.cache.clear()
        logger.info("Route cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache.get_cache_info()
