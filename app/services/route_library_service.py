"""
Route Library Service - Route browsing and management.

This service provides access to the route library:
- Browse all routes (commute and long rides)
- Search and filter routes
- Get route details and statistics
- Compare routes
- Manage favorites
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.route_analyzer import RouteGroup, Route
from src.long_ride_analyzer import LongRide
from src.config import Config
from src.json_storage import JSONStorage
from src.visualizer import RouteVisualizer
from src.location_finder import Location

logger = logging.getLogger(__name__)


class RouteLibraryService:
    """
    Service for route library access and management.
    
    Provides:
    - Browse all routes (commute + long rides)
    - Search and filter capabilities
    - Route statistics and details
    - Route comparison
    - Favorite management (JSON-based storage)
    """
    
    def __init__(self, config: Config):
        """
        Initialize route library service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.storage = JSONStorage()
        self._route_groups: Optional[List[RouteGroup]] = None
        self._long_rides: Optional[List[LongRide]] = None
        self._favorites: set = set()
        self._cache_loaded = False
        self._load_favorites()
    
    def _load_favorites(self):
        """Load favorites from JSON file into memory cache."""
        try:
            data = self.storage.read('favorite_routes.json', default={'routes': [], 'updated_at': None})
            self._favorites = set(data.get('routes', []))
            logger.info(f"Loaded {len(self._favorites)} favorites from JSON storage")
        except Exception as e:
            logger.error(f"Error loading favorites: {e}")
            self._favorites = set()
    
    def _load_from_cache(self):
        """
        Load route data from JSON cache.
        
        This allows the service to serve cached data without requiring
        fresh analysis. Called automatically on first data access.
        """
        if self._cache_loaded:
            return
        
        logger.info("Loading route data from cache...")
        
        try:
            # Load route groups
            routes_data = self.storage.read('route_groups.json', default={})
            if routes_data.get('route_groups'):
                # Store as dict until we implement proper deserialization
                self._route_groups = routes_data['route_groups']
                logger.info(f"Loaded {len(self._route_groups)} route groups from cache")
            
            # Load long rides
            long_rides_data = self.storage.read('long_rides.json', default={})
            if long_rides_data.get('long_rides'):
                self._long_rides = long_rides_data['long_rides']
                logger.info(f"Loaded {len(self._long_rides)} long rides from cache")
            
            self._cache_loaded = True
            logger.info("Route cache loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading route cache: {e}")
            self._cache_loaded = True  # Mark as loaded to avoid retry loops
    
    def initialize(self, route_groups: List[RouteGroup], long_rides: List[LongRide]):
        """
        Initialize the library with route data.
        
        Must be called before accessing routes.
        
        Args:
            route_groups: List of commute route groups
            long_rides: List of long rides
        """
        logger.info(f"Initializing route library: {len(route_groups)} commute groups, {len(long_rides)} long rides")
        self._route_groups = route_groups
        self._long_rides = long_rides
    
    def get_all_routes(self, 
                      route_type: str = 'all',
                      sort_by: str = 'uses',
                      limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get all routes with optional filtering and sorting.
        
        Args:
            route_type: 'all', 'commute', or 'long_ride'
            sort_by: 'uses', 'distance', 'recent', 'name'
            limit: Maximum number of routes to return
            
        Returns:
            Dictionary with routes:
            {
                'status': 'success' | 'error',
                'routes': List[Dict],
                'total_count': int,
                'filters': {
                    'type': str,
                    'sort_by': str
                }
            }
        """
        # Load cached data if not already loaded
        self._load_from_cache()
        
        if not self._route_groups and not self._long_rides:
            return {
                'status': 'error',
                'message': 'Route library not initialized',
                'routes': [],
                'total_count': 0
            }
        
        try:
            routes = []
            
            # Add commute routes
            if route_type in ['all', 'commute'] and self._route_groups:
                for group in self._route_groups:
                    routes.append(self._format_commute_route(group))
            
            # Add long rides
            if route_type in ['all', 'long_ride'] and self._long_rides:
                for ride in self._long_rides:
                    routes.append(self._format_long_ride(ride))
            
            # Sort routes
            routes = self._sort_routes(routes, sort_by)
            
            # Apply limit
            if limit:
                routes = routes[:limit]
            
            return {
                'status': 'success',
                'routes': routes,
                'total_count': len(routes),
                'filters': {
                    'type': route_type,
                    'sort_by': sort_by
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get routes: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to retrieve routes: {str(e)}',
                'routes': [],
                'total_count': 0
            }
    
    def search_routes(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search routes by name or location.
        
        Args:
            query: Search query string
            limit: Maximum results to return
            
        Returns:
            Dictionary with search results
        """
        if not self._route_groups and not self._long_rides:
            return {
                'status': 'error',
                'message': 'Route library not initialized',
                'results': [],
                'count': 0
            }
        
        try:
            query_lower = query.lower()
            results = []
            
            # Search commute routes
            if self._route_groups:
                for group in self._route_groups:
                    name = (group.name or '').lower()
                    if query_lower in name:
                        results.append(self._format_commute_route(group))
            
            # Search long rides
            if self._long_rides:
                for ride in self._long_rides:
                    name = ride.name.lower()
                    if query_lower in name:
                        results.append(self._format_long_ride(ride))
            
            # Limit results
            results = results[:limit]
            
            return {
                'status': 'success',
                'query': query,
                'results': results,
                'count': len(results)
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Search failed: {str(e)}',
                'results': [],
                'count': 0
            }
    
    def get_route_details(self, route_id: str, route_type: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific route.
        
        Args:
            route_id: Route identifier
            route_type: 'commute' or 'long_ride'
            
        Returns:
            Dictionary with route details
        """
        route = self.get_route_by_id(route_id, route_type=route_type)
        if route:
            return {
                'status': 'success',
                'route': route
            }
        
        return {
            'status': 'error',
            'message': f'Route {route_id} not found'
        }

    def get_route_by_id(self, route_id: str, route_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a single route by ID with full detail payload."""
        self._load_from_cache()

        if route_type in (None, 'all', 'commute') and self._route_groups:
            for group in self._route_groups:
                group_id = group.get('id') if isinstance(group, dict) else group.id
                if group_id == route_id:
                    return self._format_commute_route_detailed(group)

        if route_type in (None, 'all', 'long_ride') and self._long_rides:
            for ride in self._long_rides:
                ride_id = str(ride.get('activity_id') if isinstance(ride, dict) else ride.activity_id)
                if ride_id == route_id:
                    if isinstance(ride, dict):
                        return self._format_long_ride_from_dict_detailed(ride)
                    return self._format_long_ride_detailed(ride)

        return None
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """
        Get overall route library statistics.
        
        Returns:
            Dictionary with statistics:
            {
                'total_routes': int,
                'commute_routes': int,
                'long_rides': int,
                'total_distance': float,
                'total_activities': int,
                'most_used_route': Dict,
                'longest_ride': Dict
            }
        """
        stats = {
            'total_routes': 0,
            'commute_routes': 0,
            'long_rides': 0,
            'total_distance': 0.0,
            'total_activities': 0,
            'most_used_route': None,
            'longest_ride': None
        }
        
        if self._route_groups:
            stats['commute_routes'] = len(self._route_groups)
            stats['total_routes'] += len(self._route_groups)
            
            for group in self._route_groups:
                stats['total_activities'] += group.get('frequency', 0)
                stats['total_distance'] += group.get('representative_route', {}).get('distance', 0) * group.get('frequency', 0)
            
            # Find most used commute route
            if self._route_groups:
                most_used = max(self._route_groups, key=lambda g: g.get('frequency', 0))
                stats['most_used_route'] = {
                    'id': most_used.get('id'),
                    'name': most_used.get('name'),
                    'uses': most_used.get('frequency', 0),
                    'type': 'commute'
                }
        
        if self._long_rides:
            stats['long_rides'] = len(self._long_rides)
            stats['total_routes'] += len(self._long_rides)
            
            for ride in self._long_rides:
                stats['total_activities'] += ride.uses
                stats['total_distance'] += ride.distance * ride.uses
            
            # Find longest ride
            if self._long_rides:
                longest = max(self._long_rides, key=lambda r: r.distance)
                stats['longest_ride'] = {
                    'id': longest.activity_id,
                    'name': longest.name,
                    'distance': longest.distance_km,
                    'type': 'long_ride'
                }
        
        # Convert total distance to km
        stats['total_distance'] = stats['total_distance'] / 1000
        
        return stats
    
    def toggle_favorite(self, route_id: str, is_favorite: bool) -> Dict[str, Any]:
        """
        Toggle favorite status for a route.
        
        Args:
            route_id: Route identifier
            is_favorite: True to add to favorites, False to remove
            
        Returns:
            Dictionary with updated status
        """
        try:
            if is_favorite:
                # Add to favorites
                self._favorites.add(route_id)
                logger.info(f"Added favorite: {route_id}")
            else:
                # Remove from favorites
                self._favorites.discard(route_id)
                logger.info(f"Removed favorite: {route_id}")
            
            # Save to JSON file
            success = self.storage.write('favorites.json', {
                'routes': list(self._favorites),
                'updated_at': datetime.now().isoformat()
            })
            
            if not success:
                raise Exception("Failed to write favorites to JSON storage")
            
            return {
                'status': 'success',
                'route_id': route_id,
                'is_favorite': is_favorite
            }
        
        except Exception as e:
            logger.error(f"Error toggling favorite: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'route_id': route_id,
                'is_favorite': is_favorite
            }
    
    def get_favorites(self) -> Dict[str, Any]:
        """
        Get all favorite routes.
        
        Returns:
            Dictionary with favorite routes
        """
        favorite_routes = []
        
        # Get favorite commute routes
        if self._route_groups:
            for group in self._route_groups:
                if group.id in self._favorites:
                    favorite_routes.append(self._format_commute_route(group))
        
        # Get favorite long rides
        if self._long_rides:
            for ride in self._long_rides:
                if str(ride.activity_id) in self._favorites:
                    favorite_routes.append(self._format_long_ride(ride))
        
        return {
            'status': 'success',
            'favorites': favorite_routes,
            'count': len(favorite_routes)
        }
    
    def _format_commute_route(self, group) -> Dict[str, Any]:
        """
        Format a commute route group for API response.
        
        Args:
            group: RouteGroup object or dict from cache
        """
        # Handle both RouteGroup objects and dict from cache
        if isinstance(group, dict):
            rep_route = group['representative_route']
            # Ensure name is never empty or "Unnamed Activity"
            name = group.get('name') or f"Commute Route {group['id']}"
            if name == "Unnamed Activity":
                name = f"Commute Route {group['id']}"
            
            return {
                'id': group['id'],
                'type': 'commute',
                'name': name,
                'direction': group['direction'],
                'distance': rep_route['distance'] / 1000,  # km
                'duration': rep_route['duration'] / 60,  # minutes
                'elevation': rep_route.get('elevation_gain', 0),
                'uses': group['frequency'],
                'is_plus_route': group.get('is_plus_route', False),
                'is_favorite': group['id'] in self._favorites,
                'difficulty': group.get('difficulty', 'Easy'),
                'sport_type': rep_route.get('sport_type', 'Ride')
            }
        else:
            # RouteGroup object
            rep_route = group.representative_route
            # Ensure name is never empty or "Unnamed Activity"
            name = group.name or f"Commute Route {group.id}"
            if name == "Unnamed Activity":
                name = f"Commute Route {group.id}"
            
            return {
                'id': group.id,
                'type': 'commute',
                'name': name,
                'direction': group.direction,
                'distance': rep_route.distance / 1000,  # km
                'duration': rep_route.duration / 60,  # minutes
                'elevation': rep_route.elevation_gain,
                'uses': group.frequency,
                'is_plus_route': group.is_plus_route,
                'is_favorite': group.id in self._favorites,
                'difficulty': getattr(group, 'difficulty', 'Easy'),
                'sport_type': getattr(rep_route, 'sport_type', 'Ride')
            }
    
    def _get_meaningful_route_name(self, name: str, distance_km: float, timestamp: str, is_loop: bool = False) -> str:
        """
        Generate a meaningful route name with fallback logic.
        
        Priority:
        1. Use provided name if not "Unnamed Activity"
        2. Generate descriptive name based on route characteristics
        
        Args:
            name: Original route name
            distance_km: Distance in kilometers
            timestamp: ISO format timestamp
            is_loop: Whether the route is a loop
            
        Returns:
            Meaningful route name
        """
        # If name exists and is not "Unnamed Activity", use it
        if name and name.strip() and name != "Unnamed Activity":
            return name
        
        # Generate fallback name
        try:
            from datetime import datetime
            date_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            date_str = date_obj.strftime('%b %d, %Y')
        except:
            date_str = timestamp[:10] if timestamp else 'Unknown Date'
        
        route_type = "Loop" if is_loop else "Route"
        return f"{route_type} {distance_km:.1f}km on {date_str}"
    
    def _format_long_ride(self, ride) -> Dict[str, Any]:
        """
        Format a long ride for API response.
        
        Args:
            ride: LongRide object or dict from cache
        """
        # Handle both LongRide objects and dict from cache
        if isinstance(ride, dict):
            # Generate meaningful name with fallback
            meaningful_name = self._get_meaningful_route_name(
                ride['name'],
                ride['distance_km'],
                ride.get('timestamp', ''),
                ride.get('is_loop', False)
            )
            
            return {
                'id': str(ride['activity_id']),
                'type': 'long_ride',
                'name': meaningful_name,
                'distance': ride['distance_km'],
                'duration': ride['duration_hours'] * 60,  # minutes
                'elevation': ride.get('elevation_gain', 0),
                'uses': ride.get('uses', 1),
                'is_loop': ride.get('is_loop', False),
                'is_favorite': str(ride['activity_id']) in self._favorites,
                'difficulty': ride.get('difficulty', 'Easy'),
                'sport_type': ride.get('type', 'Ride')
            }
        else:
            # LongRide object
            # Generate meaningful name with fallback
            meaningful_name = self._get_meaningful_route_name(
                ride.name,
                ride.distance_km,
                ride.timestamp,
                ride.is_loop
            )
            
            return {
                'id': str(ride.activity_id),
                'type': 'long_ride',
                'name': meaningful_name,
                'distance': ride.distance_km,
                'duration': ride.duration_hours * 60,  # minutes
                'elevation': ride.elevation_gain,
                'uses': ride.uses,
                'is_loop': ride.is_loop,
                'is_favorite': str(ride.activity_id) in self._favorites,
                'difficulty': getattr(ride, 'difficulty', 'Easy'),
                'sport_type': ride.type
            }
    
    def _format_commute_route_detailed(self, group) -> Dict[str, Any]:
        """Format detailed commute route information."""
        base = self._format_commute_route(group)
        
        # Handle both dict and RouteGroup objects
        if isinstance(group, dict):
            routes_data = group.get('routes', [])
            rep_route = group.get('representative_route', {})
            coordinates = rep_route.get('coordinates', [])
            
            base.update({
                'routes': [
                    {
                        'activity_id': r.get('activity_id'),
                        'distance': r.get('distance', 0) / 1000,
                        'duration': r.get('duration', 0) / 60,
                        'elevation': r.get('elevation_gain', 0),
                        'timestamp': r.get('timestamp'),
                        'average_speed': r.get('average_speed', 0) * 3.6,  # km/h
                        'activity_name': r.get('activity_name', '')
                    }
                    for r in routes_data
                ],
                'coordinates': coordinates
            })
        else:
            # RouteGroup object
            base.update({
                'routes': [
                    {
                        'activity_id': r.activity_id,
                        'distance': r.distance / 1000,
                        'duration': r.duration / 60,
                        'elevation': r.elevation_gain,
                        'timestamp': r.timestamp,
                        'average_speed': r.average_speed * 3.6,  # km/h
                        'activity_name': r.activity_name
                    }
                    for r in group.routes
                ],
                'coordinates': group.representative_route.coordinates
            })
        
        return base
    
    def _format_long_ride_detailed(self, ride: LongRide) -> Dict[str, Any]:
        """Format detailed long ride information."""
        base = self._format_long_ride(ride)
        base.update({
            'coordinates': ride.coordinates,
            'start_location': list(ride.start_location),
            'end_location': list(ride.end_location),
            'average_speed': ride.average_speed * 3.6,  # km/h
            'activity_ids': ride.activity_ids,
            'activity_dates': ride.activity_dates,
            'ride_type': ride.type
        })
        return base

    def _format_long_ride_from_dict_detailed(self, ride: Dict[str, Any]) -> Dict[str, Any]:
        """Format detailed long ride information from cached dict data."""
        base = self._format_long_ride(ride)
        base.update({
            'coordinates': ride.get('coordinates', []),
            'start_location': ride.get('start_location'),
            'end_location': ride.get('end_location'),
            'average_speed': ride.get('average_speed', 0) * 3.6 if ride.get('average_speed') else 0,
            'activity_ids': ride.get('activity_ids', []),
            'activity_dates': ride.get('activity_dates', []),
            'ride_type': ride.get('type'),
            'weather': ride.get('weather'),
            'difficulty': ride.get('difficulty')
        })
        return base
    
    def _sort_routes(self, routes: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort routes by specified criteria."""
        if sort_by == 'uses':
            return sorted(routes, key=lambda r: r['uses'], reverse=True)
        elif sort_by == 'distance':
            return sorted(routes, key=lambda r: r['distance'], reverse=True)
        elif sort_by == 'name':
            return sorted(routes, key=lambda r: r['name'])
        else:  # 'recent' or default
            return routes
    
    def generate_route_map(self, route_id: str, route_type: str) -> Optional[str]:
        """
        Generate interactive map HTML for a specific route.
        
        Args:
            route_id: Route identifier
            route_type: 'commute' or 'long_ride'
            
        Returns:
            HTML string of the map, or None if route not found or error occurs
        """
        try:
            # Load cached data if not already loaded
            self._load_from_cache()
            
            # Get route data
            route_group = None
            long_ride = None
            
            if route_type == 'commute' and self._route_groups:
                # Find the route group (handle both dict and RouteGroup objects)
                for group in self._route_groups:
                    group_id = group.get('id') if isinstance(group, dict) else group.id
                    if group_id == route_id:
                        route_group = group
                        break
                
                if not route_group:
                    logger.warning(f"Commute route {route_id} not found")
                    return None
                
                # Convert dict to RouteGroup if needed
                if isinstance(route_group, dict):
                    # For now, we'll work with the dict directly
                    # In a full implementation, we'd deserialize to RouteGroup
                    pass
                
            elif route_type == 'long_ride' and self._long_rides:
                # Find the long ride
                for ride in self._long_rides:
                    ride_id = str(ride.get('activity_id') if isinstance(ride, dict) else ride.activity_id)
                    if ride_id == route_id:
                        long_ride = ride
                        break
                
                if not long_ride:
                    logger.warning(f"Long ride {route_id} not found")
                    return None
            
            else:
                logger.warning(f"Invalid route type or no routes available: {route_type}")
                return None
            
            # Create dummy home/work locations for map centering
            # In production, these should come from config or be calculated from route
            if route_type == 'commute' and route_group:
                coords = route_group.get('representative_route', {}).get('coordinates', []) if isinstance(route_group, dict) else route_group.representative_route.coordinates
                if not coords:
                    logger.warning(f"Route {route_id} has no coordinates")
                    return None
                
                # Use first and last coordinates as home/work
                start_coord = coords[0]
                end_coord = coords[-1]
                home = Location(lat=start_coord[0], lon=start_coord[1], name="Start", activity_count=1)
                work = Location(lat=end_coord[0], lon=end_coord[1], name="End", activity_count=1)
                
                # Create visualizer with single route
                visualizer = RouteVisualizer(
                    route_groups=[route_group] if not isinstance(route_group, dict) else [],
                    home=home,
                    work=work,
                    config=self.config
                )
                
                # Create base map
                map_obj = visualizer.create_base_map()
                visualizer.map = map_obj
                
                # Determine route color based on frequency/quality
                frequency = route_group.get('frequency', 0) if isinstance(route_group, dict) else route_group.frequency
                if frequency > 10:
                    color = '#28a745'  # Green for frequently used routes
                elif frequency > 5:
                    color = '#007bff'  # Blue for moderately used
                else:
                    color = '#ffc107'  # Yellow for less used
                
                # Add route layer (handle dict case)
                if isinstance(route_group, dict):
                    # Manually add polyline for dict case
                    import folium
                    rep_route = route_group.get('representative_route', {})
                    route_name = route_group.get('name', f"Route {route_id}")
                    
                    # Create popup HTML
                    popup_html = f"""
                    <div style="font-family: Arial, sans-serif;">
                        <h4 style="margin: 0 0 10px 0;">{route_name}</h4>
                        <table style="width: 100%; font-size: 12px;">
                            <tr>
                                <td><b>Direction:</b></td>
                                <td>{route_group.get('direction', 'N/A').replace('_', ' ').title()}</td>
                            </tr>
                            <tr>
                                <td><b>Uses:</b></td>
                                <td>{frequency} times</td>
                            </tr>
                            <tr>
                                <td><b>Distance:</b></td>
                                <td>{rep_route.get('distance', 0) / 1000:.1f} km</td>
                            </tr>
                            <tr>
                                <td><b>Duration:</b></td>
                                <td>{rep_route.get('duration', 0) / 60:.1f} min</td>
                            </tr>
                            <tr>
                                <td><b>Elevation:</b></td>
                                <td>{rep_route.get('elevation_gain', 0)} m</td>
                            </tr>
                        </table>
                    </div>
                    """
                    
                    folium.PolyLine(
                        coords,
                        color=color,
                        weight=5,
                        opacity=0.8,
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"{route_name} ({frequency} uses)"
                    ).add_to(map_obj)
                else:
                    visualizer.add_route_layer(route_group, color, weight=5, is_optimal=True)
                
                # Add start/end markers
                import folium
                folium.Marker(
                    [start_coord[0], start_coord[1]],
                    popup='<b>Start</b>',
                    tooltip='Start',
                    icon=folium.Icon(color='green', icon='play', prefix='fa')
                ).add_to(map_obj)
                
                folium.Marker(
                    [end_coord[0], end_coord[1]],
                    popup='<b>End</b>',
                    tooltip='End',
                    icon=folium.Icon(color='red', icon='stop', prefix='fa')
                ).add_to(map_obj)
                
                # Fit map to route bounds
                map_obj.fit_bounds(coords)
                
                # Add layer control
                folium.LayerControl().add_to(map_obj)
                
                # Return HTML - use get_root().render() for proper HTML output
                # _repr_html_() returns iframe-based output for Jupyter, which doesn't work in web apps
                return map_obj.get_root().render()
                
            elif route_type == 'long_ride' and long_ride:
                coords = long_ride.get('coordinates', []) if isinstance(long_ride, dict) else long_ride.coordinates
                if not coords:
                    logger.warning(f"Long ride {route_id} has no coordinates")
                    return None
                
                # Use start/end coordinates
                start_coord = coords[0]
                end_coord = coords[-1]
                home = Location(lat=start_coord[0], lon=start_coord[1], name="Start", activity_count=1)
                work = Location(lat=end_coord[0], lon=end_coord[1], name="End", activity_count=1)
                
                # Create visualizer
                visualizer = RouteVisualizer(
                    route_groups=[],
                    home=home,
                    work=work,
                    config=self.config
                )
                
                # Create base map
                map_obj = visualizer.create_base_map()
                
                # Add route polyline
                import folium
                ride_name = long_ride.get('name', 'Long Ride') if isinstance(long_ride, dict) else long_ride.name
                distance_km = long_ride.get('distance_km', 0) if isinstance(long_ride, dict) else long_ride.distance_km
                duration_hours = long_ride.get('duration_hours', 0) if isinstance(long_ride, dict) else long_ride.duration_hours
                elevation = long_ride.get('elevation_gain', 0) if isinstance(long_ride, dict) else long_ride.elevation_gain
                is_loop = long_ride.get('is_loop', False) if isinstance(long_ride, dict) else long_ride.is_loop
                
                popup_html = f"""
                <div style="font-family: Arial, sans-serif;">
                    <h4 style="margin: 0 0 10px 0;">{ride_name}</h4>
                    <table style="width: 100%; font-size: 12px;">
                        <tr>
                            <td><b>Type:</b></td>
                            <td>Long Ride {'(Loop)' if is_loop else ''}</td>
                        </tr>
                        <tr>
                            <td><b>Distance:</b></td>
                            <td>{distance_km:.1f} km</td>
                        </tr>
                        <tr>
                            <td><b>Duration:</b></td>
                            <td>{duration_hours:.1f} hrs</td>
                        </tr>
                        <tr>
                            <td><b>Elevation:</b></td>
                            <td>{elevation} m</td>
                        </tr>
                    </table>
                </div>
                """
                
                folium.PolyLine(
                    coords,
                    color='#8B008B',  # Purple for long rides
                    weight=5,
                    opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=ride_name
                ).add_to(map_obj)
                
                # Add start marker
                folium.Marker(
                    [start_coord[0], start_coord[1]],
                    popup='<b>Start</b>',
                    tooltip='Start',
                    icon=folium.Icon(color='green', icon='play', prefix='fa')
                ).add_to(map_obj)
                
                # Add end marker (only if not a loop)
                if not is_loop:
                    folium.Marker(
                        [end_coord[0], end_coord[1]],
                        popup='<b>End</b>',
                        tooltip='End',
                        icon=folium.Icon(color='red', icon='stop', prefix='fa')
                    ).add_to(map_obj)
                
                # Fit map to route bounds
                map_obj.fit_bounds(coords)
                
                # Add layer control
                folium.LayerControl().add_to(map_obj)
                
                # Return HTML - use get_root().render() for proper HTML output
                # _repr_html_() returns iframe-based output for Jupyter, which doesn't work in web apps
                return map_obj.get_root().render()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate map for route {route_id}: {e}", exc_info=True)
            return None
    
    def get_routes(self,
                   route_type: str = 'all',
                   sort_by: str = 'uses',
                   limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get routes with optional filtering and sorting.
        
        This is the primary method for retrieving routes from the library.
        It's an alias for get_all_routes() to provide a cleaner API interface.
        
        Args:
            route_type: Filter by type - 'all', 'commute', or 'long_ride'
            sort_by: Sort criteria - 'uses', 'distance', 'recent', or 'name'
            limit: Maximum number of routes to return (None for all)
            
        Returns:
            Dictionary with routes and metadata:
            {
                'status': 'success' | 'error',
                'routes': List[Dict],  # List of route objects
                'total_count': int,    # Total number of routes returned
                'filters': {
                    'type': str,       # Applied route type filter
                    'sort_by': str     # Applied sort criteria
                }
            }
            
        Example:
            >>> service.get_routes(route_type='commute', sort_by='distance', limit=10)
            {
                'status': 'success',
                'routes': [...],
                'total_count': 10,
                'filters': {'type': 'commute', 'sort_by': 'distance'}
            }
        """
        return self.get_all_routes(route_type=route_type, sort_by=sort_by, limit=limit)
    
    def get_route_history(self, route_id: str) -> Dict[str, Any]:
        """
        Get usage history for a specific route.
        
        Returns all instances when this route was used, including dates,
        times, and performance metrics for each use.
        
        Args:
            route_id: Route identifier (group ID for commutes, activity ID for long rides)
            
        Returns:
            Dictionary with route history:
            {
                'status': 'success' | 'error',
                'route_id': str,
                'route_name': str,
                'route_type': 'commute' | 'long_ride',
                'total_uses': int,
                'first_used': str,  # ISO timestamp
                'last_used': str,   # ISO timestamp
                'history': [
                    {
                        'activity_id': int,
                        'date': str,        # ISO timestamp
                        'distance': float,  # km
                        'duration': float,  # minutes
                        'elevation': float, # meters
                        'average_speed': float  # km/h
                    },
                    ...
                ]
            }
            
        Example:
            >>> service.get_route_history('route_123')
            {
                'status': 'success',
                'route_id': 'route_123',
                'route_name': 'Main Commute',
                'total_uses': 45,
                'history': [...]
            }
        """
        try:
            # Load cached data if not already loaded
            self._load_from_cache()
            
            # Search in commute routes
            if self._route_groups:
                for group in self._route_groups:
                    group_id = group.get('id') if isinstance(group, dict) else group.id
                    if group_id == route_id:
                        # Found commute route
                        routes_data = group.get('routes', []) if isinstance(group, dict) else group.routes
                        name = group.get('name') if isinstance(group, dict) else group.name
                        
                        history = []
                        for route in routes_data:
                            if isinstance(route, dict):
                                history.append({
                                    'activity_id': route.get('activity_id'),
                                    'date': route.get('timestamp'),
                                    'distance': route.get('distance', 0) / 1000,  # km
                                    'duration': route.get('duration', 0) / 60,  # minutes
                                    'elevation': route.get('elevation_gain', 0),
                                    'average_speed': route.get('average_speed', 0) * 3.6  # km/h
                                })
                            else:
                                history.append({
                                    'activity_id': route.activity_id,
                                    'date': route.timestamp,
                                    'distance': route.distance / 1000,
                                    'duration': route.duration / 60,
                                    'elevation': route.elevation_gain,
                                    'average_speed': route.average_speed * 3.6
                                })
                        
                        # Sort by date (most recent first)
                        history.sort(key=lambda x: x['date'], reverse=True)
                        
                        return {
                            'status': 'success',
                            'route_id': route_id,
                            'route_name': name or f"Route {route_id}",
                            'route_type': 'commute',
                            'total_uses': len(history),
                            'first_used': history[-1]['date'] if history else None,
                            'last_used': history[0]['date'] if history else None,
                            'history': history
                        }
            
            # Search in long rides
            if self._long_rides:
                for ride in self._long_rides:
                    ride_id = str(ride.get('activity_id') if isinstance(ride, dict) else ride.activity_id)
                    if ride_id == route_id:
                        # Found long ride
                        if isinstance(ride, dict):
                            activity_ids = ride.get('activity_ids', [ride.get('activity_id')])
                            activity_dates = ride.get('activity_dates', [ride.get('timestamp')])
                            name = ride.get('name')
                            distance = ride.get('distance_km')
                            duration = ride.get('duration_hours') * 60
                            elevation = ride.get('elevation_gain', 0)
                            avg_speed = (ride.get('distance', 0) / ride.get('duration', 1)) * 3.6 if ride.get('duration') else 0
                        else:
                            activity_ids = ride.activity_ids or [ride.activity_id]
                            activity_dates = ride.activity_dates or [ride.timestamp]
                            name = ride.name
                            distance = ride.distance_km
                            duration = ride.duration_hours * 60
                            elevation = ride.elevation_gain
                            avg_speed = ride.average_speed * 3.6
                        
                        history = []
                        for act_id, act_date in zip(activity_ids, activity_dates):
                            history.append({
                                'activity_id': act_id,
                                'date': act_date,
                                'distance': distance,
                                'duration': duration,
                                'elevation': elevation,
                                'average_speed': avg_speed
                            })
                        
                        # Sort by date (most recent first)
                        history.sort(key=lambda x: x['date'], reverse=True)
                        
                        return {
                            'status': 'success',
                            'route_id': route_id,
                            'route_name': name,
                            'route_type': 'long_ride',
                            'total_uses': len(history),
                            'first_used': history[-1]['date'] if history else None,
                            'last_used': history[0]['date'] if history else None,
                            'history': history
                        }
            
            # Route not found
            return {
                'status': 'error',
                'message': f'Route {route_id} not found',
                'route_id': route_id,
                'total_uses': 0,
                'history': []
            }
            
        except Exception as e:
            logger.error(f"Failed to get route history for {route_id}: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to retrieve route history: {str(e)}',
                'route_id': route_id,
                'total_uses': 0,
                'history': []
            }
    
    def compare_routes(self, route_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple routes side-by-side.
        
        Provides detailed comparison of route metrics including relative
        differences (e.g., "20% longer", "15% more elevation").
        
        Args:
            route_ids: List of route IDs to compare (max 5)
            
        Returns:
            Dictionary with comparison data:
            {
                'status': 'success' | 'error',
                'routes': [
                    {
                        'id': str,
                        'name': str,
                        'type': str,
                        'distance': float,      # km
                        'duration': float,      # minutes
                        'elevation': float,     # meters
                        'average_speed': float, # km/h
                        'uses': int,
                        'last_used': str,       # ISO timestamp
                        'relative_distance': str,    # e.g., "+20%"
                        'relative_duration': str,    # e.g., "-5%"
                        'relative_elevation': str    # e.g., "+15%"
                    },
                    ...
                ],
                'summary': {
                    'shortest_route': str,  # route name
                    'fastest_route': str,
                    'flattest_route': str,
                    'most_used_route': str
                }
            }
            
        Example:
            >>> service.compare_routes(['route_1', 'route_2', 'route_3'])
            {
                'status': 'success',
                'routes': [...],
                'summary': {
                    'shortest_route': 'Main Commute',
                    'fastest_route': 'Highway Route',
                    ...
                }
            }
        """
        try:
            # Validate input
            if not route_ids:
                return {
                    'status': 'error',
                    'message': 'No route IDs provided',
                    'routes': []
                }
            
            if len(route_ids) > 5:
                return {
                    'status': 'error',
                    'message': 'Maximum 5 routes can be compared at once',
                    'routes': []
                }
            
            # Load cached data if not already loaded
            self._load_from_cache()
            
            # Collect route data
            routes_data = []
            for route_id in route_ids:
                route_info = None
                
                # Search in commute routes
                if self._route_groups:
                    for group in self._route_groups:
                        group_id = group.get('id') if isinstance(group, dict) else group.id
                        if group_id == route_id:
                            route_info = self._format_commute_route(group)
                            # Get last used date from routes
                            routes = group.get('routes', []) if isinstance(group, dict) else group.routes
                            if routes:
                                last_route = max(routes, key=lambda r: r.get('timestamp') if isinstance(r, dict) else r.timestamp)
                                route_info['last_used'] = last_route.get('timestamp') if isinstance(last_route, dict) else last_route.timestamp
                            else:
                                route_info['last_used'] = None
                            break
                
                # Search in long rides if not found
                if not route_info and self._long_rides:
                    for ride in self._long_rides:
                        ride_id = str(ride.get('activity_id') if isinstance(ride, dict) else ride.activity_id)
                        if ride_id == route_id:
                            route_info = self._format_long_ride(ride)
                            route_info['last_used'] = ride.get('timestamp') if isinstance(ride, dict) else ride.timestamp
                            break
                
                if route_info:
                    routes_data.append(route_info)
                else:
                    logger.warning(f"Route {route_id} not found for comparison")
            
            if not routes_data:
                return {
                    'status': 'error',
                    'message': 'None of the specified routes were found',
                    'routes': []
                }
            
            # Calculate relative metrics (compare to first route as baseline)
            baseline = routes_data[0]
            baseline_distance = baseline['distance']
            baseline_duration = baseline['duration']
            baseline_elevation = baseline['elevation']
            
            for route in routes_data:
                # Calculate relative differences
                if baseline_distance > 0:
                    dist_diff = ((route['distance'] - baseline_distance) / baseline_distance) * 100
                    route['relative_distance'] = f"{dist_diff:+.1f}%" if dist_diff != 0 else "baseline"
                else:
                    route['relative_distance'] = "N/A"
                
                if baseline_duration > 0:
                    dur_diff = ((route['duration'] - baseline_duration) / baseline_duration) * 100
                    route['relative_duration'] = f"{dur_diff:+.1f}%" if dur_diff != 0 else "baseline"
                else:
                    route['relative_duration'] = "N/A"
                
                if baseline_elevation > 0:
                    elev_diff = ((route['elevation'] - baseline_elevation) / baseline_elevation) * 100
                    route['relative_elevation'] = f"{elev_diff:+.1f}%" if elev_diff != 0 else "baseline"
                else:
                    route['relative_elevation'] = "N/A"
                
                # Add average speed if not present
                if 'average_speed' not in route and route['duration'] > 0:
                    route['average_speed'] = (route['distance'] / (route['duration'] / 60))  # km/h
            
            # Generate summary
            summary = {
                'shortest_route': min(routes_data, key=lambda r: r['distance'])['name'],
                'fastest_route': min(routes_data, key=lambda r: r['duration'])['name'],
                'flattest_route': min(routes_data, key=lambda r: r['elevation'])['name'],
                'most_used_route': max(routes_data, key=lambda r: r['uses'])['name']
            }
            
            return {
                'status': 'success',
                'routes': routes_data,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Failed to compare routes: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to compare routes: {str(e)}',
                'routes': []
            }
    
    def export_routes(self, format: str = 'json', route_type: str = 'all') -> Dict[str, Any]:
        """
        Export routes in various formats.
        
        Supports JSON, CSV, and GPX formats for route data export.
        
        Args:
            format: Export format - 'json', 'csv', or 'gpx'
            route_type: Filter routes - 'all', 'commute', or 'long_ride'
            
        Returns:
            Dictionary with export data:
            {
                'status': 'success' | 'error',
                'format': str,
                'data': str | dict,  # Exported data in requested format
                'route_count': int
            }
            
        Formats:
            - JSON: Structured route data with all fields
            - CSV: Tabular format with key metrics (distance, duration, etc.)
            - GPX: GPS Exchange Format with coordinates and metadata
            
        Example:
            >>> service.export_routes(format='csv', route_type='commute')
            {
                'status': 'success',
                'format': 'csv',
                'data': 'id,name,type,distance,...',
                'route_count': 15
            }
        """
        try:
            # Validate format
            if format not in ['json', 'csv', 'gpx']:
                return {
                    'status': 'error',
                    'message': f"Unsupported format: {format}. Use 'json', 'csv', or 'gpx'",
                    'format': format,
                    'data': None
                }
            
            # Get routes
            routes_result = self.get_all_routes(route_type=route_type)
            if routes_result['status'] != 'success':
                return {
                    'status': 'error',
                    'message': 'Failed to retrieve routes for export',
                    'format': format,
                    'data': None
                }
            
            routes = routes_result['routes']
            
            if format == 'json':
                # JSON export - return structured data
                export_data = {
                    'exported_at': datetime.now().isoformat(),
                    'route_type': route_type,
                    'route_count': len(routes),
                    'routes': routes
                }
                
                return {
                    'status': 'success',
                    'format': 'json',
                    'data': export_data,
                    'route_count': len(routes)
                }
            
            elif format == 'csv':
                # CSV export - tabular format
                csv_lines = []
                csv_lines.append('id,name,type,distance_km,duration_min,elevation_m,uses,average_speed_kmh')
                
                for route in routes:
                    avg_speed = (route['distance'] / (route['duration'] / 60)) if route['duration'] > 0 else 0
                    csv_lines.append(
                        f"{route['id']},"
                        f"\"{route['name']}\","
                        f"{route['type']},"
                        f"{route['distance']:.2f},"
                        f"{route['duration']:.1f},"
                        f"{route['elevation']:.1f},"
                        f"{route['uses']},"
                        f"{avg_speed:.2f}"
                    )
                
                csv_data = '\n'.join(csv_lines)
                
                return {
                    'status': 'success',
                    'format': 'csv',
                    'data': csv_data,
                    'route_count': len(routes)
                }
            
            elif format == 'gpx':
                # GPX export - GPS Exchange Format
                gpx_lines = []
                gpx_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
                gpx_lines.append('<gpx version="1.1" creator="Ride Optimizer">')
                gpx_lines.append(f'  <metadata>')
                gpx_lines.append(f'    <time>{datetime.now().isoformat()}</time>')
                gpx_lines.append(f'  </metadata>')
                
                # Get detailed route data with coordinates
                for route in routes:
                    route_details = self.get_route_details(route['id'], route['type'])
                    if route_details['status'] == 'success':
                        route_data = route_details['route']
                        coords = route_data.get('coordinates', [])
                        
                        if coords:
                            gpx_lines.append(f'  <trk>')
                            gpx_lines.append(f'    <name>{route["name"]}</name>')
                            gpx_lines.append(f'    <type>{route["type"]}</type>')
                            gpx_lines.append(f'    <trkseg>')
                            
                            for lat, lon in coords:
                                gpx_lines.append(f'      <trkpt lat="{lat}" lon="{lon}"/>')
                            
                            gpx_lines.append(f'    </trkseg>')
                            gpx_lines.append(f'  </trk>')
                
                gpx_lines.append('</gpx>')
                gpx_data = '\n'.join(gpx_lines)
                
                return {
                    'status': 'success',
                    'format': 'gpx',
                    'data': gpx_data,
                    'route_count': len(routes)
                }
            
        except Exception as e:
            logger.error(f"Failed to export routes: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Failed to export routes: {str(e)}',
                'format': format,
                'data': None
            }

# Made with Bob
