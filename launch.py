"""
Minimal Flask API for Smart Static architecture.

Provides 4 JSON endpoints for static HTML pages to fetch data:
- /api/weather - Current weather data
- /api/recommendation - Next commute recommendation
- /api/routes - All routes for library
- /api/status - System health and freshness

No sessions, CORS, rate limiting - optimized for single-user Pi deployment.
"""

from flask import Flask, jsonify, send_from_directory, request
from pathlib import Path
import logging
from datetime import datetime
import webbrowser
import threading
import time
import json
from typing import List, Dict, Any

from src.config import Config
from src.json_storage import JSONStorage
from src.route_analyzer import Route, RouteGroup
from src.location_finder import Location
from app.services.analysis_service import AnalysisService
from app.services.commute_service import CommuteService
from app.services.weather_service import WeatherService
from app.services.planner_service import PlannerService
from app.services.route_library_service import RouteLibraryService
from app.api import maps_api
from src.secure_logger import SecureLogger
from src.logging_config import setup_logging
from app.schemas import (
    WeatherQuerySchema,
    RecommendationQuerySchema,
    RoutesQuerySchema,
    validate_request_args
)

# Configure logging with rotation (10MB per file, 5 backups)
setup_logging(
    log_dir='logs',
    log_level=logging.INFO,
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5,
    console_output=True  # Enable console output for development
)
logger = SecureLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['JSON_SORT_KEYS'] = False

# Register blueprints
app.register_blueprint(maps_api.bp)

# Initialize configuration and storage
config = Config()
storage = JSONStorage()

# Initialize services (lazy initialization on first request)
_services_initialized = False
_analysis_service = None
_commute_service = None
_weather_service = None
_planner_service = None
_route_library_service = None


def load_route_groups_from_json(json_path: Path) -> List[RouteGroup]:
    """
    Load route groups from JSON file and convert to RouteGroup objects.
    
    Args:
        json_path: Path to route_groups.json file
        
    Returns:
        List of RouteGroup objects
        
    Raises:
        FileNotFoundError: If JSON file doesn't exist
        ValueError: If JSON structure is invalid
    """
    if not json_path.exists():
        raise FileNotFoundError(f"Route groups file not found: {json_path}")
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        route_groups_data = data.get('route_groups', [])
        if not route_groups_data:
            raise ValueError("No route groups found in JSON file")
        
        route_groups = []
        for group_data in route_groups_data:
            # Convert representative route
            rep_route_data = group_data['representative_route']
            representative_route = Route(
                activity_id=rep_route_data['activity_id'],
                direction=rep_route_data['direction'],
                coordinates=[(lat, lon) for lat, lon in rep_route_data['coordinates']],
                distance=rep_route_data['distance'],
                duration=rep_route_data['duration'],
                elevation_gain=rep_route_data['elevation_gain'],
                timestamp=rep_route_data['timestamp'],
                average_speed=rep_route_data['average_speed'],
                is_plus_route=rep_route_data.get('is_plus_route', False)
            )
            
            # Convert all routes in group
            routes = []
            for route_data in group_data.get('routes', []):
                route = Route(
                    activity_id=route_data['activity_id'],
                    direction=route_data['direction'],
                    coordinates=[(lat, lon) for lat, lon in route_data['coordinates']],
                    distance=route_data['distance'],
                    duration=route_data['duration'],
                    elevation_gain=route_data['elevation_gain'],
                    timestamp=route_data['timestamp'],
                    average_speed=route_data['average_speed'],
                    is_plus_route=route_data.get('is_plus_route', False)
                )
                routes.append(route)
            
            # Create RouteGroup
            route_group = RouteGroup(
                id=group_data['id'],
                direction=group_data['direction'],
                routes=routes,
                representative_route=representative_route,
                frequency=group_data['frequency'],
                name=group_data.get('name'),
                is_plus_route=group_data.get('is_plus_route', False),
                difficulty=group_data.get('difficulty', 'easy')
            )
            route_groups.append(route_group)
        
        logger.info(f"Loaded {len(route_groups)} route groups from {json_path}")
        return route_groups
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in route groups file: {e}")
    except KeyError as e:
        raise ValueError(f"Missing required field in route groups JSON: {e}")


def get_locations_from_config(config: Config) -> tuple[Location, Location]:
    """
    Extract home and work locations from config.
    
    Args:
        config: Configuration object
        
    Returns:
        Tuple of (home_location, work_location)
        
    Raises:
        ValueError: If location coordinates are missing or invalid
    """
    try:
        home_lat = config.get('location.home.latitude')
        home_lon = config.get('location.home.longitude')
        work_lat = config.get('location.work.latitude')
        work_lon = config.get('location.work.longitude')
        
        if None in (home_lat, home_lon, work_lat, work_lon):
            raise ValueError("Missing location coordinates in config")
        
        home_location = Location(
            lat=float(home_lat),
            lon=float(home_lon),
            name="Home",
            activity_count=0  # Config-based locations don't have activity counts
        )
        
        work_location = Location(
            lat=float(work_lat),
            lon=float(work_lon),
            name="Work",
            activity_count=0  # Config-based locations don't have activity counts
        )
        
        logger.info(f"Loaded locations - Home: ({home_lat}, {home_lon}), Work: ({work_lat}, {work_lon})")
        return home_location, work_location
        
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid location coordinates in config: {e}")


def initialize_services():
    """Initialize all services (called on first API request)."""
    global _services_initialized, _analysis_service, _commute_service
    global _weather_service, _planner_service, _route_library_service
    
    if _services_initialized:
        return
    
    logger.info("Initializing services...")
    
    try:
        # Initialize core services
        _analysis_service = AnalysisService(config)
        _commute_service = CommuteService(config)
        _weather_service = WeatherService(config)
        _planner_service = PlannerService(config)
        _route_library_service = RouteLibraryService(config)
        
        # Load cached data if available
        status_data = storage.read('status.json', default={})
        if status_data.get('has_data', False):
            logger.info("Loading cached analysis data...")
            
            # Initialize CommuteService with route groups and locations
            try:
                # Load route groups from JSON
                route_groups_path = Path('data/route_groups.json')
                route_groups = load_route_groups_from_json(route_groups_path)
                
                # Extract locations from config
                home_location, work_location = get_locations_from_config(config)
                
                # Initialize commute service
                enable_weather = config.get('weather.enabled', True)
                _commute_service.initialize(
                    route_groups=route_groups,
                    home_location=home_location,
                    work_location=work_location,
                    enable_weather=enable_weather
                )
                logger.info("CommuteService initialized successfully")
                
            except FileNotFoundError as e:
                logger.warning(f"Route groups not found, commute service will not be available: {e}")
            except ValueError as e:
                logger.warning(f"Invalid route data or config, commute service will not be available: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize commute service: {e}", exc_info=True)
        else:
            logger.info("No cached data available - run analysis first to enable commute recommendations")
        
        _services_initialized = True
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise


@app.route('/')
def index():
    """Serve the main application page with Epic #237 redesign."""
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static HTML pages."""
    return send_from_directory('static', path)


@app.route('/api/weather')
@validate_request_args(WeatherQuerySchema)
def get_weather():
    """
    Get current weather data.
    
    Query params:
    - lat: Latitude (optional, defaults to home location)
    - lon: Longitude (optional, defaults to home location)
    - location: Location name (optional)
    
    Returns:
        JSON with weather data including comfort_score and cycling_favorability
    """
    initialize_services()
    
    try:
        # Get location from query params or use home location
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        location_name = request.args.get('location')
        
        if lat is None or lon is None:
            # Use home location from config
            home_lat = config.get('location.home.latitude')
            home_lon = config.get('location.home.longitude')
            
            if home_lat and home_lon:
                lat, lon = home_lat, home_lon
                location_name = location_name or 'Home'
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'No location specified and no home location configured'
                }), 400
        
        weather_data = _weather_service.get_current_weather(lat, lon, location_name)
        
        # Format for frontend expectations (dashboard.js expects 'current' key)
        if weather_data:
            # Convert field names to match frontend expectations
            wind_speed_mph = weather_data.get('wind_speed_kph', 0) * 0.621371
            formatted_weather = {
                'temperature': round(weather_data.get('temperature_f', weather_data.get('temp_c', 0) * 9/5 + 32)),
                'feels_like': round(weather_data.get('feels_like_f', weather_data.get('temperature_f', 0))),
                'conditions': weather_data.get('conditions', 'Unknown'),
                'description': weather_data.get('conditions', 'Unknown'),
                'wind_speed': round(wind_speed_mph),  # Round to nearest mph
                'wind_direction': weather_data.get('wind_direction_cardinal', 'N'),
                'humidity': weather_data.get('humidity', 0),
                'precipitation_probability': weather_data.get('precipitation_mm', 0),
                'comfort_score': int(weather_data.get('comfort_score', 0.5) * 100)  # Convert to 0-100
            }
            
            return jsonify({
                'status': 'success',
                'current': formatted_weather,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Weather data unavailable'
            }), 503
        
    except Exception as e:
        logger.error(f"Error getting weather: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/recommendation')
@validate_request_args(RecommendationQuerySchema)
def get_recommendation():
    """
    Get next commute recommendation.
    
    Query params:
    - direction: 'to_work' or 'to_home' (optional, auto-detected if not specified)
    
    Returns:
        JSON with commute recommendation including route, score, weather, alternatives
    """
    initialize_services()
    
    try:
        direction = request.args.get('direction')
        
        # Get recommendation
        recommendation = _commute_service.get_next_commute(direction)
        
        # Format for frontend while preserving service-level fields for API consumers
        if recommendation.get('status') == 'success' and recommendation.get('route'):
            route = recommendation['route']
            score = recommendation.get('score', 0)
            score_percent = int(score * 100) if isinstance(score, float) and score <= 1 else int(score)
            formatted = {
                'status': 'success',
                'direction': recommendation.get('direction'),
                'time_window': recommendation.get('time_window'),
                'is_today': recommendation.get('is_today'),
                'departure_time': recommendation.get('departure_time'),
                'confidence': recommendation.get('confidence'),
                'route': route,
                'recommended_route': {
                    'id': route.get('id'),
                    'name': route.get('name', 'Unknown Route'),
                    'distance': route.get('distance', 0) / 1000,
                    'duration': route.get('duration', 0),
                    'elevation_gain': route.get('elevation', 0),
                    'coordinates': route.get('coordinates', [])
                },
                'score': score_percent,
                'recommendation': 'Recommended' if score_percent >= 70 else 'Alternative available',
                'breakdown': recommendation.get('breakdown', {}),
                'weather': recommendation.get('weather'),
                'factors': []
            }
            
            for key, value in formatted['breakdown'].items():
                if isinstance(value, (int, float)):
                    factor_value = int(value * 100) if value <= 1 else int(value)
                    formatted['factors'].append(f"{key.title()}: {factor_value}%")
                elif not isinstance(value, dict):
                    formatted['factors'].append(f"{key.title()}: {value}")
            
            # Add timestamp for data freshness
            formatted['timestamp'] = datetime.now().isoformat()
            return jsonify(formatted)
        else:
            # Add timestamp even for error responses
            recommendation['timestamp'] = datetime.now().isoformat()
            return jsonify(recommendation)
        
    except Exception as e:
        logger.error(f"Error getting recommendation: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/commute')
def get_commute():
    """
    Get both commute directions (to_work and to_home) for the commute view.
    
    Returns:
        JSON with both direction recommendations:
        {
            'status': 'success',
            'to_work': {...},
            'to_home': {...},
            'timestamp': str
        }
    """
    initialize_services()
    
    try:
        # Get recommendations for both directions
        to_work = _commute_service.get_next_commute(direction='to_work')
        to_home = _commute_service.get_next_commute(direction='to_home')
        
        return jsonify({
            'status': 'success',
            'to_work': to_work,
            'to_home': to_home,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting commute data: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/commute/map')
def get_commute_map():
    """
    Get interactive map HTML showing both commute routes.
    
    Returns:
        HTML string with Folium map showing both routes
    """
    initialize_services()
    
    try:
        # Get both commute recommendations
        to_work = _commute_service.get_next_commute(direction='to_work')
        to_home = _commute_service.get_next_commute(direction='to_home')
        
        # Collect routes for map with direction metadata
        routes = []
        if to_work.get('status') == 'success':
            # Ensure direction is set for color coding
            to_work['direction'] = 'to_work'
            routes.append(to_work)
        if to_home.get('status') == 'success':
            # Ensure direction is set for color coding
            to_home['direction'] = 'to_home'
            routes.append(to_home)
        
        if not routes:
            return jsonify({
                'status': 'error',
                'message': 'No commute routes available'
            }), 404
        
        # Get locations from config
        home_location, work_location = get_locations_from_config(config)
        
        # Generate comparison map
        map_html = _commute_service.generate_comparison_map(
            routes=routes,
            home_location=home_location,
            work_location=work_location
        )
        
        if map_html:
            return map_html, 200, {'Content-Type': 'text/html'}
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate map'
            }), 500
        
    except Exception as e:
        logger.error(f"Error generating commute map: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/routes')
@validate_request_args(RoutesQuerySchema)
def get_routes():
    """
    Get all routes for library.
    
    Query params:
    - type: 'all', 'commute', or 'long_ride' (default: 'all')
    - sort: 'uses', 'distance', 'recent', 'name' (default: 'uses')
    - limit: Maximum number of routes (optional)
    
    Returns:
        JSON with routes list and metadata
    """
    initialize_services()
    
    try:
        route_type = request.args.get('type', 'all')
        sort_by = request.args.get('sort', 'uses')
        limit = request.args.get('limit', type=int)
        
        routes_data = _route_library_service.get_all_routes(
            route_type=route_type,
            sort_by=sort_by,
            limit=limit
        )
        
        # Format routes for frontend (dashboard.js expects specific fields)
        if routes_data.get('status') == 'success' and routes_data.get('routes'):
            formatted_routes = []
            for route in routes_data['routes']:
                formatted_route = {
                    'id': route.get('id'),
                    'name': route.get('name', 'Unknown Route'),
                    'distance': route.get('distance', 0),  # Already in km
                    'duration': route.get('duration', 0),  # minutes
                    'elevation_gain': route.get('elevation', 0),
                    'sport_type': route.get('type', 'Ride'),
                    'is_favorite': route.get('is_favorite', False),
                    'uses': route.get('uses', 0),
                    'type': route.get('type', 'commute'),
                    'difficulty': route.get('difficulty', 'Easy')
                }
                formatted_routes.append(formatted_route)
            
            return jsonify({
                'status': 'success',
                'routes': formatted_routes,
                'total_count': len(formatted_routes),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify(routes_data)
        
    except Exception as e:
        logger.error(f"Error getting routes: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'routes': [],
            'total_count': 0
        }), 500


@app.route('/api/routes/<route_id>')
def get_route_detail(route_id):
    """Get a single route detail payload by route ID."""
    initialize_services()

    try:
        route_type = request.args.get('type')
        route = _route_library_service.get_route_by_id(route_id, route_type=route_type)

        if not route:
            return jsonify({
                'status': 'error',
                'message': f'Route {route_id} not found'
            }), 404

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
                'sport_type': route.get('sport_type', route.get('ride_type', route.get('type', 'Ride')))
            }
        })

    except Exception as e:
        logger.error(f"Error getting route detail for {route_id}: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/status')
def get_status():
    """
    Get system health and data freshness status.
    
    Returns:
        JSON with system status, data freshness, last analysis time, etc.
    """
    initialize_services()
    
    try:
        # Get analysis status
        analysis_status = _analysis_service.get_analysis_status()
        
        # Format for frontend (dashboard.js expects specific fields)
        status_data = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'storage_ok': True,
            'storage_used_mb': 10,  # TODO: Calculate actual storage
            'storage_total_mb': 1000,
            'uptime_seconds': 3600,  # TODO: Track actual uptime
            'last_update': analysis_status.get('last_analysis'),
            'services': {
                'analysis': 'initialized' if _analysis_service else 'not_initialized',
                'commute': 'initialized' if _commute_service else 'not_initialized',
                'weather': 'initialized' if _weather_service else 'not_initialized',
                'planner': 'initialized' if _planner_service else 'not_initialized',
                'route_library': 'initialized' if _route_library_service else 'not_initialized'
            },
            'data': analysis_status
        }
        
        return jsonify(status_data)
        
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'status': 'error',
        'message': 'Resource not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f'Internal server error: {error}')
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500


def open_browser(port):
    """Open Chrome browser after a short delay to ensure server is ready."""
    time.sleep(1.5)  # Wait for server to start
    url = f'http://localhost:{port}'
    try:
        # Try to open in Chrome specifically
        chrome_path = None
        import platform
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            chrome_path = 'open -a /Applications/Google\\ Chrome.app %s'
        elif system == 'Windows':
            chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
        elif system == 'Linux':
            chrome_path = '/usr/bin/google-chrome %s'
        
        if chrome_path:
            webbrowser.get(chrome_path).open(url)
        else:
            # Fallback to default browser
            webbrowser.open(url)
        
        logger.info(f"Opened browser at {url}")
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")
        logger.info(f"Please open your browser manually to: {url}")


def kill_existing_server(port):
    """Kill any existing server process running on the specified port."""
    import subprocess
    import signal
    
    try:
        # Find process using the port
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    pid_int = int(pid)
                    logger.info(f"Killing existing server process {pid_int} on port {port}")
                    import os
                    os.kill(pid_int, signal.SIGTERM)
                    time.sleep(0.5)  # Give it time to terminate
                except (ValueError, ProcessLookupError) as e:
                    logger.debug(f"Could not kill process {pid}: {e}")
    except FileNotFoundError:
        # lsof not available (Windows)
        logger.debug("lsof command not available, skipping process check")
    except Exception as e:
        logger.warning(f"Error checking for existing server: {e}")


def run_server(port):
    """Run the Flask server (called in subprocess)."""
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    # Development server
    import os
    import sys
    import subprocess
    
    # Check if running as server subprocess
    if len(sys.argv) > 1 and sys.argv[1] == '--serve':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8083
        logger.info(f"Running server on port {port}")
        run_server(port)
        sys.exit(0)
    
    # Main launcher process
    port = int(os.environ.get('PORT', 8083))
    
    # Kill any existing server on this port
    kill_existing_server(port)
    
    logger.info("Starting Ride Optimizer API server...")
    logger.info("API endpoints:")
    logger.info("  GET /api/weather - Current weather data")
    logger.info("  GET /api/recommendation - Next commute recommendation")
    logger.info("  GET /api/routes - All routes for library")
    logger.info("  GET /api/status - System health and freshness")
    logger.info(f"Server will run on port {port}")
    
    # Start server in background subprocess
    with open('/tmp/ride-optimizer-server.log', 'a') as log_file:
        server_process = subprocess.Popen(
            [sys.executable, __file__, '--serve', str(port)],
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )
        
        logger.info(f"Server started with PID {server_process.pid}")
        logger.info(f"Server logs: /tmp/ride-optimizer-server.log")
    
    # Wait for server to start
    time.sleep(2)
    
    # Open browser
    url = f'http://localhost:{port}'
    try:
        import platform
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            os.system(f'open -a "Google Chrome" {url} 2>/dev/null || open {url}')
        elif system == 'Windows':
            os.system(f'start chrome {url} 2>nul || start {url}')
        elif system == 'Linux':
            os.system(f'google-chrome {url} 2>/dev/null || xdg-open {url}')
        else:
            webbrowser.open(url)
        
        logger.info(f"Browser opened at {url}")
    except Exception as e:
        logger.warning(f"Could not open browser: {e}")
        logger.info(f"Please open your browser manually to: {url}")
    
    # Exit cleanly
    logger.info("Launch complete. Server running in background.")
    sys.exit(0)


# Made with Bob