"""Routes library API Blueprint.

Routes:
  GET /api/routes
  GET /api/routes/status
  GET /api/routes/search
  GET /api/routes/<route_id>
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.schemas import RoutesQuerySchema, validate_request_args
from src.config_manager import ConfigManager
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('routes', __name__, url_prefix='/api')


@bp.route('/routes')
@validate_request_args(RoutesQuerySchema)
def get_routes():
    """
    Get all routes for library.

    Query params:
    - type: 'all', 'commute', or 'long_ride' (default: 'all')
    - sort: 'uses', 'distance', 'recent', 'name' (default: 'uses')
    - limit: Maximum number of routes (optional)
    """
    container = current_app.container
    container.initialise()

    route_library_service = container.route_library_service
    if route_library_service is None:
        return jsonify({'status': 'error', 'message': 'Route Library is currently unavailable'}), 503

    try:
        search_query = request.args.get('search', '').strip()
        route_type = request.args.get('type', 'all')
        sort_by = request.args.get('sort', 'uses')
        limit = request.args.get('limit', type=int)

        if search_query:
            routes_data = route_library_service.search_routes(
                query=search_query,
                limit=limit or 50
            )
            raw_routes = routes_data.get('results', [])
        else:
            routes_data = route_library_service.get_all_routes(
                route_type=route_type,
                sort_by=sort_by,
                limit=limit
            )
            raw_routes = routes_data.get('routes', []) if routes_data.get('status') == 'success' else []

        formatted_routes = []
        for route in raw_routes:
            formatted_routes.append({
                'id': route.get('id'),
                'name': route.get('name', 'Unknown Route'),
                'distance': route.get('distance', 0),
                'duration': route.get('duration', 0),
                'elevation_gain': route.get('elevation', 0),
                'sport_type': route.get('type', 'Ride'),
                'is_favorite': route.get('is_favorite', False),
                'uses': route.get('uses', 0),
                'type': route.get('type', 'commute'),
                'difficulty': route.get('difficulty', 'Easy')
            })

        return jsonify({
            'status': 'success',
            'routes': formatted_routes,
            'total_count': len(formatted_routes),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting routes: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Routes temporarily unavailable',
            'routes': [],
            'total_count': 0
        }), 500


@bp.route('/routes/status')
def get_routes_status():
    """
    Get per-route condition summary crossing route data with current weather.
    """
    container = current_app.container
    container.initialise()

    route_library_service = container.route_library_service
    if route_library_service is None:
        return jsonify({'status': 'error', 'message': 'Route Library is currently unavailable'}), 503
    weather_service = container.weather_service
    if weather_service is None:
        return jsonify({'status': 'error', 'message': 'Weather is currently unavailable'}), 503

    try:
        config = ConfigManager.get_instance()
        routes_data = route_library_service.get_all_routes(
            route_type='commute', sort_by='uses', limit=6
        )
        routes = routes_data.get('routes', []) if routes_data.get('status') == 'success' else []

        home_lat = config.get('location.home.latitude')
        home_lon = config.get('location.home.longitude')
        current_weather = None
        if home_lat and home_lon:
            raw = weather_service.get_current_weather(home_lat, home_lon)
            if raw:
                wind_speed_mph = raw.get('wind_speed_kph', 0) * 0.621371
                current_weather = {
                    'conditions': raw.get('conditions', ''),
                    'wind_speed': round(wind_speed_mph),
                    'wind_direction': raw.get('wind_direction_cardinal', ''),
                    'comfort_score': int(raw.get('comfort_score', 0.5) * 100)
                }

        result_routes = []
        for route in routes:
            name = route.get('name', 'Unknown Route')
            condition_score = 75
            condition_note = 'Clear'

            if current_weather:
                wind_speed = current_weather['wind_speed']
                wind_dir = current_weather['wind_direction']
                conditions = current_weather['conditions'].lower()
                comfort = current_weather['comfort_score']
                condition_score = comfort

                if 'thunder' in conditions or 'storm' in conditions:
                    condition_note = 'Storm warning'
                elif 'snow' in conditions:
                    condition_note = 'Snowy'
                elif 'rain' in conditions or 'drizzle' in conditions:
                    condition_note = 'Rainy'
                elif wind_speed >= 20:
                    condition_note = f'{wind_speed} mph crosswind'
                elif wind_speed >= 12:
                    condition_note = f'{wind_speed} mph wind'
                elif wind_speed >= 5:
                    condition_note = f'Light {wind_dir} wind'
                else:
                    condition_note = 'Clear'

            result_routes.append({
                'id': route.get('id'),
                'name': name,
                'condition_score': condition_score,
                'condition_note': condition_note,
                'distance': route.get('distance', 0),
                'type': route.get('type', 'commute')
            })

        return jsonify({
            'status': 'success',
            'routes': result_routes,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting route status: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'routes': []
        }), 500


@bp.route('/routes/search')
def search_routes():
    """
    Search routes by name.

    Query params:
    - q: Search query string (required)
    - limit: Maximum results (default 10, max 100)
    """
    container = current_app.container
    container.initialise()

    route_library_service = container.route_library_service
    if route_library_service is None:
        return jsonify({'status': 'error', 'message': 'Route Library is currently unavailable'}), 503

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({
            'status': 'error',
            'message': 'Query parameter q is required',
            'routes': [],
            'total_count': 0
        }), 400

    limit = min(request.args.get('limit', 10, type=int), 100)

    try:
        result = route_library_service.search_routes(query, limit=limit)
        routes = result.get('results', [])
        return jsonify({
            'status': 'success',
            'query': query,
            'routes': routes,
            'total_count': len(routes)
        })
    except Exception as e:
        logger.error(f"Error searching routes: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Search temporarily unavailable',
            'routes': [],
            'total_count': 0
        }), 500


@bp.route('/routes/<route_id>')
def get_route_detail(route_id):
    """Get a single route detail payload by route ID with validation."""
    container = current_app.container
    container.initialise()

    route_library_service = container.route_library_service
    if route_library_service is None:
        return jsonify({'status': 'error', 'message': 'Route Library is currently unavailable'}), 503

    try:
        if not route_id or not route_id.replace('-', '').replace('_', '').isalnum():
            return jsonify({'status': 'error', 'message': 'Invalid route ID format'}), 400

        if len(route_id) > 100:
            return jsonify({'status': 'error', 'message': 'Route ID too long'}), 400

        route_type = request.args.get('type')
        route = route_library_service.get_route_by_id(route_id, route_type=route_type)

        if not route:
            return jsonify({'status': 'error', 'message': 'Route not found'}), 404

        return jsonify({
            'status': 'success',
            'route': {
                'id': route.get('id'),
                'name': route.get('name', 'Unknown Route'),
                'type': route.get('type'),
                'direction': route.get('direction'),
                'distance': route.get('distance', 0),
                'duration': route.get('duration', 0),
                'elevation': route.get('elevation', 0),
                'uses': route.get('uses', 0),
                'coordinates': route.get('coordinates', []),
                'weather': route.get('weather'),
                'difficulty': route.get('difficulty'),
                'routes': route.get('routes', []),
                'is_favorite': route.get('is_favorite', False),
                'is_plus_route': route.get('is_plus_route', False),
                'sport_type': route.get('sport_type', route.get('ride_type', route.get('type', 'Ride'))),
                'activity_ids': route.get('activity_ids', []),
                'activity_dates': route.get('activity_dates', []),
                'activity_names': route.get('activity_names', [])
            }
        })

    except Exception as e:
        logger.error(f"Error getting route detail for {route_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
