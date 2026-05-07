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
        # Load cached data if not already loaded
        self._load_from_cache()
        
        if route_type == 'commute' and self._route_groups:
            # Handle both dict and RouteGroup objects
            group = None
            for g in self._route_groups:
                g_id = g.get('id') if isinstance(g, dict) else g.id
                if g_id == route_id:
                    group = g
                    break
            
            if group:
                return {
                    'status': 'success',
                    'route': self._format_commute_route_detailed(group)
                }
        
        elif route_type == 'long_ride' and self._long_rides:
            # Handle both dict and LongRide objects
            ride = None
            for r in self._long_rides:
                r_id = str(r.get('activity_id') if isinstance(r, dict) else r.activity_id)
                if r_id == route_id:
                    ride = r
                    break
            
            if ride:
                return {
                    'status': 'success',
                    'route': self._format_long_ride_detailed(ride)
                }
        
        return {
            'status': 'error',
            'message': f'Route {route_id} not found'
        }
    
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
            return {
                'id': group['id'],
                'type': 'commute',
                'name': group.get('name') or f"Route {group['id']}",
                'direction': group['direction'],
                'distance': rep_route['distance'] / 1000,  # km
                'duration': rep_route['duration'] / 60,  # minutes
                'elevation': rep_route.get('elevation_gain', 0),
                'uses': group['frequency'],
                'is_plus_route': group.get('is_plus_route', False),
                'is_favorite': group['id'] in self._favorites
            }
        else:
            # RouteGroup object
            rep_route = group.representative_route
            return {
                'id': group.id,
                'type': 'commute',
                'name': group.name or f"Route {group.id}",
                'direction': group.direction,
                'distance': rep_route.distance / 1000,  # km
                'duration': rep_route.duration / 60,  # minutes
                'elevation': rep_route.elevation_gain,
                'uses': group.frequency,
                'is_plus_route': group.is_plus_route,
                'is_favorite': group.id in self._favorites
            }
    
    def _format_long_ride(self, ride) -> Dict[str, Any]:
        """
        Format a long ride for API response.
        
        Args:
            ride: LongRide object or dict from cache
        """
        # Handle both LongRide objects and dict from cache
        if isinstance(ride, dict):
            return {
                'id': str(ride['activity_id']),
                'type': 'long_ride',
                'name': ride['name'],
                'distance': ride['distance_km'],
                'duration': ride['duration_hours'] * 60,  # minutes
                'elevation': ride.get('elevation_gain', 0),
                'uses': ride.get('uses', 1),
                'is_loop': ride.get('is_loop', False),
                'is_favorite': str(ride['activity_id']) in self._favorites
            }
        else:
            # LongRide object
            return {
                'id': str(ride.activity_id),
                'type': 'long_ride',
                'name': ride.name,
                'distance': ride.distance_km,
                'duration': ride.duration_hours * 60,  # minutes
                'elevation': ride.elevation_gain,
                'uses': ride.uses,
                'is_loop': ride.is_loop,
                'is_favorite': str(ride.activity_id) in self._favorites
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
                
                # Return HTML
                return map_obj._repr_html_()
                
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
                
                # Return HTML
                return map_obj._repr_html_()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate map for route {route_id}: {e}", exc_info=True)
            return None

# Made with Bob
