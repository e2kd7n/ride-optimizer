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

from src.config import Config
from src.json_storage import JSONStorage
from app.services.analysis_service import AnalysisService
from app.services.commute_service import CommuteService
from app.services.weather_service import WeatherService
from app.services.planner_service import PlannerService
from app.services.route_library_service import RouteLibraryService
from app.api import maps_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
            # Services will load from their respective JSON files
        
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
        
        # Format for frontend (dashboard.js expects specific structure)
        if recommendation.get('status') == 'success' and recommendation.get('route'):
            route = recommendation['route']
            formatted = {
                'status': 'success',
                'recommended_route': {
                    'name': route.get('name', 'Unknown Route'),
                    'distance': route.get('distance', 0) / 1000,  # Convert m to km, then to mi
                    'elevation_gain': route.get('elevation', 0)
                },
                'score': int(recommendation.get('score', 50)),
                'recommendation': 'Recommended' if recommendation.get('score', 0) > 70 else 'Alternative available',
                'factors': []
            }
            
            # Add breakdown as factors
            if 'breakdown' in recommendation:
                breakdown = recommendation['breakdown']
                for key, value in breakdown.items():
                    formatted['factors'].append(f"{key.title()}: {int(value * 100)}%")
            
            return jsonify(formatted)
        else:
            return jsonify(recommendation)
        
    except Exception as e:
        logger.error(f"Error getting recommendation: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/routes')
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
                    'elevation_gain': route.get('elevation', 0),
                    'sport_type': route.get('type', 'Ride'),
                    'is_favorite': route.get('is_favorite', False),
                    'uses': route.get('uses', 0),
                    'type': route.get('type', 'commute')
                }
                formatted_routes.append(formatted_route)
            
            return jsonify({
                'status': 'success',
                'routes': formatted_routes,
                'total_count': len(formatted_routes)
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