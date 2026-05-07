"""
Maps API - Provides page-level map data for dashboard, commute, planner, and route-detail pages.
This is separate from map_api.py which provides route-specific data.

Frontend Integration:
- map-renderer.js calls /api/maps/<page_type>
- Returns map data with center, zoom, routes, markers, and layers
"""

from flask import Blueprint, request, jsonify
from typing import List, Dict, Optional
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

bp = Blueprint('maps_api', __name__, url_prefix='/api/maps')


def load_route_groups() -> Dict:
    """Load route groups from cache."""
    cache_file = Path('cache/route_groups_cache.json')
    if not cache_file.exists():
        return {'groups': []}
    
    with open(cache_file, 'r') as f:
        return json.load(f)


def get_default_center() -> List[float]:
    """Get default map center (Chicago area)."""
    return [41.8781, -87.6298]


@bp.route('/<page_type>')
def get_map_data(page_type: str):
    """
    Get map data for a specific page type.
    
    Page types:
    - dashboard: Overview map with all route groups
    - commute: Commute routes with current recommendation
    - planner: Route planning interface
    - route-detail: Single route detail view
    
    Query params:
    - route_id: For route-detail page
    - route_type: Filter by route type (commute, long_ride, etc.)
    
    Returns:
    {
        "status": "success",
        "center": [lat, lng],
        "zoom": 12,
        "routes": [...],  # Simple routes (no layers)
        "markers": [...],  # Simple markers (no layers)
        "layers": [...]   # Feature layers with routes/markers
    }
    """
    try:
        if page_type == 'dashboard':
            return jsonify(get_dashboard_map_data())
        elif page_type == 'commute':
            return jsonify(get_commute_map_data())
        elif page_type == 'planner':
            return jsonify(get_planner_map_data())
        elif page_type == 'route-detail':
            route_id = request.args.get('route_id')
            if not route_id:
                return jsonify({'error': 'route_id required for route-detail'}), 400
            return jsonify(get_route_detail_map_data(route_id))
        else:
            return jsonify({'error': f'Unknown page type: {page_type}'}), 400
            
    except Exception as e:
        logger.error(f"Error generating map data for {page_type}: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to load map data'
        }), 500


def get_dashboard_map_data() -> Dict:
    """
    Generate map data for dashboard page.
    Shows all route groups with layer control.
    """
    route_groups_data = load_route_groups()
    groups = route_groups_data.get('groups', [])
    
    if not groups:
        return {
            'status': 'success',
            'center': get_default_center(),
            'zoom': 12,
            'routes': [],
            'markers': [],
            'layers': []
        }
    
    # Calculate center from all routes
    all_coords = []
    for group in groups[:10]:  # Limit to first 10 groups for performance
        rep_route = group.get('representative_route', {})
        coords = rep_route.get('coordinates', [])
        if coords:
            all_coords.extend(coords)
    
    if all_coords:
        center_lat = sum(c[0] for c in all_coords) / len(all_coords)
        center_lng = sum(c[1] for c in all_coords) / len(all_coords)
        center = [center_lat, center_lng]
    else:
        center = get_default_center()
    
    # Create layers for route groups (top 10)
    layers = []
    for i, group in enumerate(groups[:10]):
        rep_route = group.get('representative_route', {})
        coords = rep_route.get('coordinates', [])
        
        if not coords:
            continue
        
        # Sample coordinates for performance (every 5th point)
        sampled_coords = coords[::5] if len(coords) > 100 else coords
        
        layer = {
            'name': group.get('name', f'Route Group {i+1}'),
            'show': i < 3,  # Show first 3 layers by default
            'routes': [{
                'coordinates': sampled_coords,
                'color': get_route_color(i),
                'weight': 4,
                'opacity': 0.7,
                'popup_html': f"""
                    <strong>{group.get('name', 'Route')}</strong><br>
                    Distance: {rep_route.get('distance', 0):.1f} mi<br>
                    Elevation: {rep_route.get('elevation_gain', 0):.0f} ft<br>
                    Uses: {group.get('count', 0)}
                """,
                'tooltip': group.get('name', 'Route')
            }],
            'markers': []
        }
        layers.append(layer)
    
    return {
        'status': 'success',
        'center': center,
        'zoom': 12,
        'routes': [],  # Using layers instead
        'markers': [],
        'layers': layers
    }


def get_commute_map_data() -> Dict:
    """
    Generate map data for commute page.
    Shows commute routes with recommended route highlighted.
    """
    route_groups_data = load_route_groups()
    groups = route_groups_data.get('groups', [])
    
    # Filter for commute routes (routes with "commute" in name or type)
    commute_groups = [
        g for g in groups 
        if 'commute' in g.get('name', '').lower() or 
           g.get('route_type') == 'commute'
    ]
    
    if not commute_groups:
        # Fallback to first few groups
        commute_groups = groups[:5]
    
    if not commute_groups:
        return {
            'status': 'success',
            'center': get_default_center(),
            'zoom': 12,
            'routes': [],
            'markers': [],
            'layers': []
        }
    
    # Calculate center
    all_coords = []
    for group in commute_groups:
        rep_route = group.get('representative_route', {})
        coords = rep_route.get('coordinates', [])
        if coords:
            all_coords.extend(coords)
    
    if all_coords:
        center_lat = sum(c[0] for c in all_coords) / len(all_coords)
        center_lng = sum(c[1] for c in all_coords) / len(all_coords)
        center = [center_lat, center_lng]
    else:
        center = get_default_center()
    
    # Create layers for commute routes
    layers = []
    for i, group in enumerate(commute_groups[:5]):  # Limit to 5
        rep_route = group.get('representative_route', {})
        coords = rep_route.get('coordinates', [])
        
        if not coords:
            continue
        
        # Sample coordinates
        sampled_coords = coords[::5] if len(coords) > 100 else coords
        
        # Highlight first route (recommended)
        is_recommended = i == 0
        
        layer = {
            'name': group.get('name', f'Commute Route {i+1}'),
            'show': True,  # Show all commute routes
            'routes': [{
                'coordinates': sampled_coords,
                'color': '#28a745' if is_recommended else get_route_color(i),
                'weight': 5 if is_recommended else 3,
                'opacity': 0.9 if is_recommended else 0.6,
                'popup_html': f"""
                    <strong>{group.get('name', 'Route')}</strong><br>
                    {'<span class="badge bg-success">Recommended</span><br>' if is_recommended else ''}
                    Distance: {rep_route.get('distance', 0):.1f} mi<br>
                    Elevation: {rep_route.get('elevation_gain', 0):.0f} ft<br>
                    Uses: {group.get('count', 0)}
                """,
                'tooltip': group.get('name', 'Route')
            }],
            'markers': []
        }
        layers.append(layer)
    
    return {
        'status': 'success',
        'center': center,
        'zoom': 13,
        'routes': [],
        'markers': [],
        'layers': layers
    }


def get_planner_map_data() -> Dict:
    """
    Generate map data for planner page.
    Shows empty map for route planning.
    """
    return {
        'status': 'success',
        'center': get_default_center(),
        'zoom': 12,
        'routes': [],
        'markers': [],
        'layers': []
    }


def get_route_detail_map_data(route_id: str) -> Dict:
    """
    Generate map data for route detail page.
    Shows single route with full detail.
    """
    route_groups_data = load_route_groups()
    groups = route_groups_data.get('groups', [])
    
    # Find route by ID
    route_group = next((g for g in groups if g['id'] == route_id), None)
    if not route_group:
        return {
            'status': 'error',
            'message': 'Route not found'
        }
    
    rep_route = route_group.get('representative_route', {})
    coords = rep_route.get('coordinates', [])
    
    if not coords:
        return {
            'status': 'error',
            'message': 'Route has no coordinates'
        }
    
    # Calculate center
    center_lat = sum(c[0] for c in coords) / len(coords)
    center_lng = sum(c[1] for c in coords) / len(coords)
    center = [center_lat, center_lng]
    
    # Create single route (no layers needed)
    route = {
        'coordinates': coords,
        'color': '#007bff',
        'weight': 4,
        'opacity': 0.8,
        'popup_html': f"""
            <strong>{route_group.get('name', 'Route')}</strong><br>
            Distance: {rep_route.get('distance', 0):.1f} mi<br>
            Elevation: {rep_route.get('elevation_gain', 0):.0f} ft<br>
            Uses: {route_group.get('count', 0)}
        """,
        'tooltip': route_group.get('name', 'Route')
    }
    
    # Add start/end markers
    markers = [
        {
            'position': coords[0],
            'icon': {'color': 'green'},
            'popup_html': '<strong>Start</strong>',
            'tooltip': 'Start'
        },
        {
            'position': coords[-1],
            'icon': {'color': 'red'},
            'popup_html': '<strong>End</strong>',
            'tooltip': 'End'
        }
    ]
    
    return {
        'status': 'success',
        'center': center,
        'zoom': 14,
        'routes': [route],
        'markers': markers,
        'layers': []
    }


def get_route_color(index: int) -> str:
    """Get color for route by index."""
    colors = [
        '#007bff',  # Blue
        '#28a745',  # Green
        '#dc3545',  # Red
        '#ffc107',  # Yellow
        '#17a2b8',  # Cyan
        '#6f42c1',  # Purple
        '#fd7e14',  # Orange
        '#20c997',  # Teal
    ]
    return colors[index % len(colors)]


# Made with Bob