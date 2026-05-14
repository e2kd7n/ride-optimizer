"""
Route Formatter Service

Formats route data for API responses and frontend consumption.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RouteFormatter:
    """
    Formats route data for API responses and frontend display.
    
    Responsible only for data transformation and formatting. Does not load,
    filter, or sort routes.
    """
    
    @staticmethod
    def format_single_route(route: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a single route for API response.
        
        Args:
            route: Route dictionary
            
        Returns:
            Formatted route dictionary
        """
        return {
            'id': route.get('id'),
            'name': route.get('name', 'Unnamed Route'),
            'type': route.get('type', 'commute'),
            'direction': route.get('direction', 'unknown'),
            'distance': route.get('distance', 0),  # in meters
            'distance_km': route.get('distance', 0) / 1000,  # converted to km
            'duration': route.get('duration', 0),  # in seconds
            'duration_minutes': route.get('duration', 0) / 60,  # converted to minutes
            'elevation': route.get('elevation_gain', 0),
            'uses': route.get('uses', 0),
            'is_favorite': route.get('is_favorite', False),
            'is_plus_route': route.get('is_plus_route', False),
            'sport_type': route.get('sport_type', 'Ride'),
            'coordinates': route.get('coordinates', []),
            'timestamp': route.get('timestamp', datetime.now().isoformat()),
        }
    
    @staticmethod
    def format_routes_list(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format a list of routes for API response.
        
        Args:
            routes: List of route dictionaries
            
        Returns:
            List of formatted route dictionaries
        """
        return [RouteFormatter.format_single_route(r) for r in routes]
    
    @staticmethod
    def format_api_response(routes: List[Dict[str, Any]], total_count: int = None) -> Dict[str, Any]:
        """
        Format routes as a complete API response.
        
        Args:
            routes: List of route dictionaries
            total_count: Total count of routes (before pagination)
            
        Returns:
            API response dictionary
        """
        if total_count is None:
            total_count = len(routes)
        
        return {
            'status': 'success',
            'routes': RouteFormatter.format_routes_list(routes),
            'total_count': total_count,
            'count': len(routes),
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def format_with_summary(routes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format routes with summary statistics.
        
        Args:
            routes: List of route dictionaries
            
        Returns:
            Dictionary with routes and summary stats
        """
        formatted_routes = RouteFormatter.format_routes_list(routes)
        
        if not formatted_routes:
            return {
                'routes': [],
                'summary': {
                    'total_routes': 0,
                    'total_distance_km': 0,
                    'avg_distance_km': 0,
                    'total_uses': 0
                }
            }
        
        total_distance = sum(r['distance_km'] for r in formatted_routes)
        total_uses = sum(r['uses'] for r in formatted_routes)
        
        return {
            'routes': formatted_routes,
            'summary': {
                'total_routes': len(formatted_routes),
                'total_distance_km': round(total_distance, 2),
                'avg_distance_km': round(total_distance / len(formatted_routes), 2),
                'total_uses': total_uses
            }
        }
    
    @staticmethod
    def format_error_response(message: str, status_code: int = 500) -> Dict[str, Any]:
        """
        Format an error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            
        Returns:
            Error response dictionary
        """
        return {
            'status': 'error',
            'message': message,
            'status_code': status_code,
            'timestamp': datetime.now().isoformat()
        }
