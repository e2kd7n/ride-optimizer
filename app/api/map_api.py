"""
Map API - Provides endpoints for map data, coordinates, and elevation.
Adapts existing CLI services for web API use.
"""

from flask import Blueprint, request, jsonify, current_app
from typing import List, Dict, Optional
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from src.secure_cache import SecureCacheStorage

logger = logging.getLogger(__name__)

bp = Blueprint('map_api', __name__, url_prefix='/api/map')

# Initialize geocoder (reused from LongRidesAPI pattern)
geocoder = Nominatim(user_agent="ride-optimizer")


@bp.route('/routes/<route_id>/coordinates')
def get_route_coordinates(route_id):
    """
    Get route coordinates for map rendering.
    
    Query params:
    - simplify: Boolean to apply simplification
    - sample_rate: Sample every Nth point (1-10)
    
    REUSES: RouteGroup.representative_route.coordinates from src/route_analyzer.py
    """
    try:
        # Load route groups from cache (existing cache file)
        cache = SecureCacheStorage('cache')
        route_groups_data = cache.load('route_groups_cache.json')
        
        if not route_groups_data or 'groups' not in route_groups_data:
            return jsonify({'error': 'No route data available'}), 503
        
        # Find route by ID
        route_group = next((g for g in route_groups_data['groups'] if g['id'] == route_id), None)
        if not route_group:
            return jsonify({'error': 'Route not found'}), 404
        
        # Extract coordinates from representative route
        rep_route = route_group.get('representative_route', {})
        coords = rep_route.get('coordinates', [])
        
        if not coords:
            return jsonify({'error': 'Route has no coordinates'}), 404
        
        # Apply sampling if requested
        sample_rate = int(request.args.get('sample_rate', 1))
        sample_rate = max(1, min(10, sample_rate))  # Clamp 1-10
        
        if sample_rate > 1:
            coords = coords[::sample_rate]
        
        # Calculate bounds
        bounds = _calculate_bounds(coords)
        
        return jsonify({
            'status': 'success',
            'route_id': route_id,
            'coordinates': [{'lat': c[0], 'lng': c[1]} for c in coords],
            'bounds': bounds,
            'metadata': {
                'total_points': len(rep_route.get('coordinates', [])),
                'returned_points': len(coords),
                'sample_rate': sample_rate
            }
        })
        
    except Exception as e:
        logger.error(f'Error fetching coordinates: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@bp.route('/routes/<route_id>/elevation')
def get_route_elevation(route_id):
    """
    Get elevation profile for a route.
    
    Query params:
    - points: Number of elevation points to return (10-200)
    
    REUSES: Route.elevation_gain from src/route_analyzer.py
    """
    try:
        cache = SecureCacheStorage('cache')
        route_groups_data = cache.load('route_groups_cache.json')
        
        if not route_groups_data or 'groups' not in route_groups_data:
            return jsonify({'error': 'No route data available'}), 503
        
        route_group = next((g for g in route_groups_data['groups'] if g['id'] == route_id), None)
        if not route_group:
            return jsonify({'error': 'Route not found'}), 404
        
        # Get representative route
        rep_route = route_group.get('representative_route', {})
        coords = rep_route.get('coordinates', [])
        
        if not coords:
            return jsonify({'error': 'Route has no coordinates'}), 404
        
        # Get requested number of points
        points = int(request.args.get('points', 100))
        points = max(10, min(200, points))  # Clamp 10-200
        
        # Sample coordinates to requested number of points
        step = max(1, len(coords) // points)
        sampled_coords = coords[::step]
        
        # Build elevation data
        elevation_data = []
        total_distance = rep_route.get('distance', 0) / 1000  # Convert to km
        
        for i, coord in enumerate(sampled_coords):
            distance = (i / len(sampled_coords)) * total_distance
            # Note: Actual elevation would come from Strava streams
            # For now, using placeholder
            elevation_data.append({
                'distance': round(distance, 2),
                'elevation': 100,  # Placeholder
                'lat': coord[0],
                'lng': coord[1]
            })
        
        # Calculate statistics
        stats = {
            'elevation_gain': rep_route.get('elevation_gain', 0),
            'total_distance': round(total_distance, 2),
            'max_elevation': 100,  # Placeholder
            'min_elevation': 100,  # Placeholder
            'avg_elevation': 100   # Placeholder
        }
        
        return jsonify({
            'status': 'success',
            'route_id': route_id,
            'elevation_data': elevation_data,
            'statistics': stats,
            'metadata': {
                'total_points': len(coords),
                'sampled_points': len(elevation_data),
                'has_elevation_data': True
            }
        })
        
    except Exception as e:
        logger.error(f'Error fetching elevation: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@bp.route('/routes/<route_id>/analytics/speed')
def get_speed_analytics(route_id):
    """
    Get speed heatmap data for route.
    
    REUSES: Route.average_speed from src/route_analyzer.py
    """
    try:
        cache = SecureCacheStorage('cache')
        route_groups_data = cache.load('route_groups_cache.json')
        
        if not route_groups_data or 'groups' not in route_groups_data:
            return jsonify({'error': 'No route data available'}), 503
        
        route_group = next((g for g in route_groups_data['groups'] if g['id'] == route_id), None)
        if not route_group:
            return jsonify({'error': 'Route not found'}), 404
        
        # Get routes and coordinates
        routes = route_group.get('routes', [])
        coords = route_group.get('representative_route', {}).get('coordinates', [])
        
        if not coords or not routes:
            return jsonify({'error': 'Insufficient data for analytics'}), 404
        
        # Calculate average speed across all routes
        avg_speed = sum(r.get('average_speed', 0) for r in routes) / len(routes)
        
        # Create segments
        segments = []
        num_segments = min(50, len(coords) - 1)
        segment_size = max(1, len(coords) // num_segments)
        
        for i in range(0, len(coords) - segment_size, segment_size):
            start_coord = coords[i]
            end_coord = coords[i + segment_size]
            
            # Color based on speed
            speed_kmh = avg_speed * 3.6  # Convert m/s to km/h
            color = _get_speed_color(avg_speed)
            
            segments.append({
                'start': {'lat': start_coord[0], 'lng': start_coord[1]},
                'end': {'lat': end_coord[0], 'lng': end_coord[1]},
                'speed': round(speed_kmh, 1),
                'color': color,
                'category': _get_speed_category(avg_speed)
            })
        
        return jsonify({
            'status': 'success',
            'route_id': route_id,
            'analytics_type': 'speed',
            'segments': segments,
            'statistics': {
                'avg_speed': round(avg_speed * 3.6, 1),
                'max_speed': round(max(r.get('average_speed', 0) for r in routes) * 3.6, 1),
                'min_speed': round(min(r.get('average_speed', 0) for r in routes) * 3.6, 1)
            }
        })
        
    except Exception as e:
        logger.error(f'Error fetching speed analytics: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@bp.route('/geocode/reverse')
def reverse_geocode():
    """
    Reverse geocode coordinates to address.
    
    Query params:
    - lat: Latitude
    - lng: Longitude
    
    REUSES: Pattern from src/api/long_rides_api.py
    """
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        
        # Check cache first
        cache_key = f"geocode_reverse_{lat:.6f}_{lng:.6f}"
        cache = SecureCacheStorage('cache')
        cached = cache.get(cache_key)
        
        if cached:
            return jsonify({'status': 'success', **cached, 'cached': True})
        
        # Geocode
        location = geocoder.reverse(f"{lat}, {lng}", timeout=10)
        
        if not location:
            return jsonify({'error': 'Location not found'}), 404
        
        result = {
            'location': {'lat': lat, 'lng': lng},
            'address': location.raw.get('address', {}),
            'display_name': location.address
        }
        
        # Cache result (30 days)
        cache.set(cache_key, result, ttl=2592000)
        
        return jsonify({'status': 'success', **result, 'cached': False})
        
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.error(f'Geocoding service error: {e}')
        return jsonify({'error': 'Geocoding service unavailable'}), 503
    except ValueError as e:
        return jsonify({'error': 'Invalid coordinates'}), 400
    except Exception as e:
        logger.error(f'Geocoding error: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/geocode/forward')
def forward_geocode():
    """
    Forward geocode address to coordinates.
    
    Query params:
    - q: Search query/address
    - limit: Maximum results (1-10)
    
    REUSES: Pattern from src/api/long_rides_api.py
    """
    try:
        query = request.args.get('q', '')
        if len(query) < 3:
            return jsonify({'error': 'Query too short (min 3 characters)'}), 400
        
        limit = int(request.args.get('limit', 5))
        limit = max(1, min(10, limit))  # Clamp 1-10
        
        # Geocode
        locations = geocoder.geocode(query, exactly_one=False, limit=limit, timeout=10)
        
        if not locations:
            return jsonify({'status': 'success', 'query': query, 'results': []})
        
        results = []
        for loc in locations:
            results.append({
                'display_name': loc.address,
                'lat': loc.latitude,
                'lng': loc.longitude,
                'type': loc.raw.get('type', 'unknown'),
                'importance': loc.raw.get('importance', 0)
            })
        
        return jsonify({'status': 'success', 'query': query, 'results': results})
        
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.error(f'Geocoding service error: {e}')
        return jsonify({'error': 'Geocoding service unavailable'}), 503
    except Exception as e:
        logger.error(f'Forward geocoding error: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# Utility functions

def _calculate_bounds(coords: List[tuple]) -> Dict:
    """Calculate bounding box (reused from RouteVisualizer logic)"""
    if not coords:
        return {}
    
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    
    return {
        'north': max(lats),
        'south': min(lats),
        'east': max(lngs),
        'west': min(lngs)
    }


def _get_speed_color(speed_ms: float) -> str:
    """Color coding for speed (semantic color system)"""
    speed_kmh = speed_ms * 3.6
    if speed_kmh < 15:
        return '#e74c3c'  # Red - slow
    elif speed_kmh < 20:
        return '#f39c12'  # Orange
    elif speed_kmh < 25:
        return '#f1c40f'  # Yellow
    else:
        return '#27ae60'  # Green - fast


def _get_speed_category(speed_ms: float) -> str:
    """Get speed category label"""
    speed_kmh = speed_ms * 3.6
    if speed_kmh < 15:
        return 'slow'
    elif speed_kmh < 20:
        return 'moderate'
    elif speed_kmh < 25:
        return 'fast'
    else:
        return 'very_fast'

# Made with Bob
