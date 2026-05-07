"""
Route Library blueprint - Browse, search, and manage routes.

Provides comprehensive route management:
- Browse all discovered routes
- Search and filter by criteria
- View route details and statistics
- Compare routes
- Manage favorites and preferences
"""

from flask import Blueprint, render_template, request, jsonify, current_app, g
from datetime import datetime

from app.services.route_library_service import RouteLibraryService
from app.services.analysis_service import AnalysisService
from src.config import Config

bp = Blueprint('route_library', __name__, url_prefix='/routes')


def get_services():
    """Get or create request-scoped services."""
    if 'route_library_services' not in g:
        config = Config('config/config.yaml')
        analysis_service = AnalysisService(config)
        route_library_service = RouteLibraryService(config)
        
        # Initialize with data from analysis if available
        # Otherwise, service will load from cache automatically
        try:
            route_groups = analysis_service.get_route_groups()
            long_rides = analysis_service.get_long_rides()
            
            # Only initialize if we have fresh data, otherwise let cache be used
            if route_groups or long_rides:
                route_library_service.initialize(route_groups, long_rides)
                current_app.logger.info(f"Initialized route library with {len(route_groups)} groups, {len(long_rides)} long rides")
            else:
                current_app.logger.info("No fresh analysis data, route library will use cache")
        except Exception as e:
            current_app.logger.error(f"Failed to initialize route library: {e}")
        
        g.route_library_services = {
            'library': route_library_service,
            'analysis': analysis_service
        }
    
    return g.route_library_services


@bp.route('/')
def index():
    """
    Main route library view with browsing and filtering.
    
    Query params:
    - sort: Sort order (distance, uses, recent, name)
    - filter: Filter criteria (commute, long_ride, favorite, all)
    - search: Search term for route names/locations
    - page: Pagination page number
    """
    sort_by = request.args.get('sort', 'uses')
    filter_by = request.args.get('filter', 'all')
    search_term = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    current_app.logger.info(
        f'Route library accessed: sort={sort_by}, filter={filter_by}, '
        f'search={search_term}, page={page}'
    )
    
    try:
        services = get_services()
        library_service = services['library']
        
        # Get routes based on filter
        if filter_by == 'favorite':
            result = library_service.get_favorites()
            routes = result.get('favorites', [])
        elif search_term:
            result = library_service.search_routes(search_term, limit=100)
            routes = result.get('results', [])
        else:
            result = library_service.get_all_routes(
                route_type=filter_by,
                sort_by=sort_by
            )
            routes = result.get('routes', [])
        
        # Get statistics for filter counts
        stats = library_service.get_route_statistics()
        
        # Pagination
        total_routes = len(routes)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_routes = routes[start_idx:end_idx]
        
        context = {
            'page_title': 'Route Library',
            'routes': paginated_routes,
            'total_routes': total_routes,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_routes + per_page - 1) // per_page,
            'sort_by': sort_by,
            'filter_by': filter_by,
            'search_term': search_term,
            'stats': stats,
            'filters': {
                'commute': stats.get('commute_routes', 0),
                'long_ride': stats.get('long_rides', 0),
                'favorite': len(library_service._favorites)
            }
        }
        
    except Exception as e:
        current_app.logger.error(f"Route library error: {e}", exc_info=True)
        context = {
            'page_title': 'Route Library',
            'routes': [],
            'total_routes': 0,
            'page': 1,
            'per_page': per_page,
            'total_pages': 0,
            'sort_by': sort_by,
            'filter_by': filter_by,
            'search_term': search_term,
            'error': 'Failed to load routes. Please ensure analysis has been run.',
            'stats': {},
            'filters': {'commute': 0, 'long_ride': 0, 'favorite': 0}
        }
    
    return render_template('routes/index.html', **context)


@bp.route('/<route_type>/<route_id>')
def detail(route_type, route_id):
    """
    Detailed view of a specific route.
    
    Shows:
    - Route map with elevation profile
    - Complete statistics (distance, elevation, uses)
    - Historical activities on this route
    - Similar route suggestions
    
    Args:
        route_type: 'commute' or 'long_ride'
        route_id: Route identifier
    """
    current_app.logger.info(f'Route detail accessed: type={route_type}, id={route_id}')
    
    try:
        services = get_services()
        library_service = services['library']
        
        result = library_service.get_route_details(route_id, route_type)
        
        if result.get('status') == 'error':
            context = {
                'page_title': 'Route Not Found',
                'error': result.get('message', 'Route not found')
            }
        else:
            route = result.get('route', {})
            
            # Generate map HTML for the route
            map_html = None
            try:
                map_html = library_service.generate_route_map(route_id, route_type)
                if map_html:
                    current_app.logger.info(f"Generated map for route {route_id}")
                else:
                    current_app.logger.warning(f"Failed to generate map for route {route_id}")
            except Exception as map_error:
                current_app.logger.error(f"Map generation error: {map_error}", exc_info=True)
            
            context = {
                'page_title': f"Route: {route.get('name', 'Unknown')}",
                'route': route,
                'route_type': route_type,
                'map_html': map_html
            }
            
    except Exception as e:
        current_app.logger.error(f"Route detail error: {e}", exc_info=True)
        context = {
            'page_title': 'Route Details',
            'error': 'Failed to load route details'
        }
    
    return render_template('routes/detail.html', **context)


@bp.route('/api/search')
def api_search():
    """
    API endpoint for route search.
    
    Query params:
    - q: Search query
    - limit: Maximum results (default: 10)
    - type: Route type filter (commute, long_ride, all)
    
    Returns JSON with matching routes.
    """
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    route_type = request.args.get('type', 'all')
    
    try:
        services = get_services()
        library_service = services['library']
        
        result = library_service.search_routes(query, limit=limit)
        
        # Filter by type if specified
        if route_type != 'all':
            results = [r for r in result.get('results', []) if r.get('type') == route_type]
        else:
            results = result.get('results', [])
        
        # Ensure proper JSON structure with all required fields
        formatted_results = []
        for route in results:
            formatted_results.append({
                'id': route.get('id', ''),
                'name': route.get('name', ''),
                'type': route.get('type', 'commute'),
                'distance': route.get('distance', 0),
                'uses': route.get('uses', 0)
            })
        
        return jsonify({
            'status': 'success',
            'routes': formatted_results,  # Changed from 'results' to 'routes' for QA test
            'results': formatted_results,  # Keep both for backward compatibility
            'query': query,
            'count': len(formatted_results),
            'limit': limit
        })
        
    except Exception as e:
        current_app.logger.error(f"Search API error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'results': [],
            'count': 0
        }), 500


@bp.route('/api/<route_id>/favorite', methods=['POST'])
def api_toggle_favorite(route_id):
    """
    Toggle favorite status for a route.
    
    POST body (JSON):
    {
        "favorite": true  # or false
    }
    
    Returns updated route status.
    """
    data = request.get_json() or {}
    is_favorite = data.get('favorite', False)
    
    current_app.logger.info(f'Toggle favorite: route_id={route_id}, favorite={is_favorite}')
    
    try:
        services = get_services()
        library_service = services['library']
        
        result = library_service.toggle_favorite(route_id, is_favorite)
        
        return jsonify({
            'status': 'success',
            'route_id': route_id,
            'is_favorite': is_favorite
        })
        
    except Exception as e:
        current_app.logger.error(f"Toggle favorite error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/api/stats')
def api_library_stats():
    """
    API endpoint for route library statistics.
    
    Returns overall library statistics.
    """
    try:
        services = get_services()
        library_service = services['library']
        
        stats = library_service.get_route_statistics()
        
        return jsonify({
            'status': 'success',
            'statistics': stats,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Stats API error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Made with Bob
