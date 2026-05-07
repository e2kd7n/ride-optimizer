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

from src.config import Config
from src.json_storage import JSONStorage
from app.services.analysis_service import AnalysisService
from app.services.commute_service import CommuteService
from app.services.weather_service import WeatherService
from app.services.planner_service import PlannerService
from app.services.route_library_service import RouteLibraryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.config['JSON_SORT_KEYS'] = False

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
    """Serve the main dashboard page."""
    return send_from_directory('static', 'dashboard.html')


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
        
        return jsonify({
            'status': 'success',
            'weather': weather_data,
            'timestamp': datetime.now().isoformat()
        })
        
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
        
        return jsonify(routes_data)
        
    except Exception as e:
        logger.error(f"Error getting routes: {e}", exc_info=True)
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
        
        # Get service initialization status
        status_data = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'analysis': 'initialized' if _analysis_service else 'not_initialized',
                'commute': 'initialized' if _commute_service else 'not_initialized',
                'weather': 'initialized' if _weather_service else 'not_initialized',
                'planner': 'initialized' if _planner_service else 'not_initialized',
                'route_library': 'initialized' if _route_library_service else 'not_initialized'
            },
            'data': analysis_status,
            'memory_usage_mb': 'N/A',  # TODO: Add memory monitoring
            'uptime_seconds': 'N/A'  # TODO: Add uptime tracking
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


if __name__ == '__main__':
    # Development server
    logger.info("Starting Ride Optimizer API server...")
    logger.info("API endpoints:")
    logger.info("  GET /api/weather - Current weather data")
    logger.info("  GET /api/recommendation - Next commute recommendation")
    logger.info("  GET /api/routes - All routes for library")
    logger.info("  GET /api/status - System health and freshness")
    
    app.run(host='0.0.0.0', port=5000, debug=False)


# Made with Bob