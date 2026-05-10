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


@app.route('/api/maps/<page_type>')
def get_map_data(page_type):
    """
    Get map data for client-side rendering.
    
    Supported page types:
    - dashboard: Overview map with all route groups
    - commute: Commute comparison map with route options
    - planner: Long rides map with weather overlay
    - route_detail: Single route detail map
    
    Query params (route_detail only):
    - route_id: Route ID to display
    - route_type: 'commute' or 'long_ride'
    
    Returns:
        JSON with map data:
        {
            'status': 'success' | 'error',
            'center': [lat, lon],
            'zoom': int,
            'routes': [
                {
                    'name': str,
                    'coordinates': [[lat, lon], ...],
                    'color': str,
                    'weight': int,
                    'opacity': float,
                    'popup_html': str,
                    'tooltip': str
                }
            ],
            'markers': [
                {
                    'position': [lat, lon],
                    'icon': {'color': str, 'icon': str, 'prefix': str},
                    'popup_html': str,
                    'tooltip': str
                }
            ],
            'layers': [
                {
                    'name': str,
                    'show': bool,
                    'routes': [...],
                    'markers': [...]
                }
            ]
        }
    """
    initialize_services()
    
    try:
        if page_type == 'dashboard':
            # Get dashboard overview map data
            route_groups = _analysis_service.get_route_groups()
            home, work = _analysis_service.get_locations()
            
            if not route_groups or not home or not work:
                return jsonify({
                    'status': 'error',
                    'message': 'No route data available'
                }), 404
            
            # Calculate center point between home and work
            center_lat = (home['lat'] + work['lat']) / 2
            center_lon = (home['lon'] + work['lon']) / 2
            
            map_data = {
                'status': 'success',
                'center': [center_lat, center_lon],
                'zoom': 12,
                'routes': [],
                'markers': [
                    {
                        'position': [home['lat'], home['lon']],
                        'icon': {'color': 'green', 'icon': 'home', 'prefix': 'fa'},
                        'popup_html': f"<b>Home</b><br>{home.get('name', 'Home Location')}",
                        'tooltip': 'Home'
                    },
                    {
                        'position': [work['lat'], work['lon']],
                        'icon': {'color': 'blue', 'icon': 'briefcase', 'prefix': 'fa'},
                        'popup_html': f"<b>Work</b><br>{work.get('name', 'Work Location')}",
                        'tooltip': 'Work'
                    }
                ],
                'layers': []
            }
            
            # Add route groups as layers
            for group in route_groups[:10]:  # Limit to 10 groups for performance
                group_name = group.get('name', 'Unknown Route')
                frequency = group.get('frequency', 0)
                rep_route = group.get('representative_route', {})
                coordinates = rep_route.get('coordinates', [])
                
                if coordinates:
                    layer_routes = [{
                        'name': group_name,
                        'coordinates': coordinates,
                        'color': '#007bff',
                        'weight': 4,
                        'opacity': 0.8,
                        'popup_html': f"<b>{group_name}</b><br>Uses: {frequency}",
                        'tooltip': f"{group_name} ({frequency} uses)"
                    }]
                    
                    map_data['layers'].append({
                        'name': f"{group_name} ({frequency} uses)",
                        'show': frequency > 5,  # Show frequently used routes by default
                        'routes': layer_routes,
                        'markers': []
                    })
            
            return jsonify(map_data)
        
        elif page_type == 'commute':
            # Get commute comparison map data
            route_groups = _analysis_service.get_route_groups()
            home, work = _analysis_service.get_locations()
            
            if not route_groups or not home or not work:
                return jsonify({
                    'status': 'error',
                    'message': 'No commute data available'
                }), 404
            
            # Initialize commute service
            _commute_service.initialize(route_groups, home, work)
            commute_data = _commute_service.get_workout_aware_commute()
            
            if commute_data.get('status') != 'success':
                return jsonify({
                    'status': 'error',
                    'message': 'No commute recommendation available'
                }), 404
            
            # Get alternative routes
            alternatives = commute_data.get('alternatives', [])
            all_routes = [commute_data.get('route')] + alternatives
            
            center_lat = (home['lat'] + work['lat']) / 2
            center_lon = (home['lon'] + work['lon']) / 2
            
            map_data = {
                'status': 'success',
                'center': [center_lat, center_lon],
                'zoom': 13,
                'routes': [],
                'markers': [
                    {
                        'position': [home['lat'], home['lon']],
                        'icon': {'color': 'green', 'icon': 'home', 'prefix': 'fa'},
                        'popup_html': f"<b>Home</b>",
                        'tooltip': 'Home'
                    },
                    {
                        'position': [work['lat'], work['lon']],
                        'icon': {'color': 'blue', 'icon': 'briefcase', 'prefix': 'fa'},
                        'popup_html': f"<b>Work</b>",
                        'tooltip': 'Work'
                    }
                ],
                'layers': []
            }
            
            # Add each route as a layer
            for idx, route in enumerate(all_routes):
                if not route or not route.get('coordinates'):
                    continue
                
                is_recommended = idx == 0
                route_name = route.get('name', 'Unknown Route')
                score = route.get('score', 0)
                
                layer_routes = [{
                    'name': route_name,
                    'coordinates': route['coordinates'],
                    'color': '#28a745' if is_recommended else '#6c757d',
                    'weight': 5 if is_recommended else 3,
                    'opacity': 0.95 if is_recommended else 0.75,
                    'popup_html': f"<b>{route_name}</b><br>Score: {int(score * 100)}%",
                    'tooltip': f"{route_name} • {int(score * 100)}%"
                }]
                
                map_data['layers'].append({
                    'name': f"{route_name} ({int(score * 100)}%)",
                    'show': True,
                    'routes': layer_routes,
                    'markers': []
                })
            
            return jsonify(map_data)
        
        elif page_type == 'planner':
            # Get long rides map data
            long_rides = _analysis_service.get_long_rides()
            home, _ = _analysis_service.get_locations()
            
            if not long_rides:
                return jsonify({
                    'status': 'error',
                    'message': 'No long rides available'
                }), 404
            
            # Use home as center or calculate from rides
            if home:
                center_lat, center_lon = home['lat'], home['lon']
            else:
                # Calculate center from first ride
                first_ride = long_rides[0]
                coords = first_ride.get('coordinates', [])
                if coords:
                    center_lat = sum(c[0] for c in coords) / len(coords)
                    center_lon = sum(c[1] for c in coords) / len(coords)
                else:
                    center_lat, center_lon = 0, 0
            
            map_data = {
                'status': 'success',
                'center': [center_lat, center_lon],
                'zoom': 11,
                'routes': [],
                'markers': [],
                'layers': []
            }
            
            # Add home marker if available
            if home:
                map_data['markers'].append({
                    'position': [home['lat'], home['lon']],
                    'icon': {'color': 'green', 'icon': 'home', 'prefix': 'fa'},
                    'popup_html': f"<b>Home</b>",
                    'tooltip': 'Home'
                })
            
            # Add each long ride as a layer
            for ride in long_rides[:15]:  # Limit to 15 rides
                ride_name = ride.get('name', 'Long Ride')
                coordinates = ride.get('coordinates', [])
                distance = ride.get('distance', 0) / 1000  # Convert to km
                
                if coordinates:
                    layer_routes = [{
                        'name': ride_name,
                        'coordinates': coordinates,
                        'color': '#007bff',
                        'weight': 4,
                        'opacity': 0.8,
                        'popup_html': f"<b>{ride_name}</b><br>Distance: {distance:.1f} km",
                        'tooltip': ride_name
                    }]
                    
                    # Add start marker
                    start_coord = coordinates[0]
                    layer_markers = [{
                        'position': start_coord,
                        'icon': {'color': 'green', 'icon': 'play', 'prefix': 'fa'},
                        'popup_html': f"<b>Start</b><br>{ride_name}",
                        'tooltip': 'Start'
                    }]
                    
                    # Add end marker if not a loop
                    if not ride.get('is_loop'):
                        end_coord = coordinates[-1]
                        layer_markers.append({
                            'position': end_coord,
                            'icon': {'color': 'red', 'icon': 'stop', 'prefix': 'fa'},
                            'popup_html': f"<b>End</b><br>{ride_name}",
                            'tooltip': 'End'
                        })
                    
                    map_data['layers'].append({
                        'name': f"{ride_name} ({distance:.1f} km)",
                        'show': False,  # Don't show all rides by default
                        'routes': layer_routes,
                        'markers': layer_markers
                    })
            
            return jsonify(map_data)
        
        elif page_type == 'route_detail':
            # Get single route detail map data
            route_id = request.args.get('route_id')
            route_type = request.args.get('route_type', 'commute')
            
            if not route_id:
                return jsonify({
                    'status': 'error',
                    'message': 'route_id parameter required'
                }), 400
            
            # Get route data from route library service
            if route_type == 'commute':
                route_groups = _analysis_service.get_route_groups()
                route = next((g for g in route_groups if g.get('id') == route_id), None)
            else:
                long_rides = _analysis_service.get_long_rides()
                route = next((r for r in long_rides if r.get('id') == route_id), None)
            
            if not route:
                return jsonify({
                    'status': 'error',
                    'message': f'Route {route_id} not found'
                }), 404
            
            coordinates = route.get('coordinates', [])
            if not coordinates:
                return jsonify({
                    'status': 'error',
                    'message': 'Route has no coordinates'
                }), 404
            
            # Calculate center
            center_lat = sum(c[0] for c in coordinates) / len(coordinates)
            center_lon = sum(c[1] for c in coordinates) / len(coordinates)
            
            route_name = route.get('name', 'Unknown Route')
            distance = route.get('distance', 0) / 1000
            
            map_data = {
                'status': 'success',
                'center': [center_lat, center_lon],
                'zoom': 14,
                'routes': [{
                    'name': route_name,
                    'coordinates': coordinates,
                    'color': '#007bff',
                    'weight': 5,
                    'opacity': 0.9,
                    'popup_html': f"<b>{route_name}</b><br>Distance: {distance:.1f} km",
                    'tooltip': route_name
                }],
                'markers': [
                    {
                        'position': coordinates[0],
                        'icon': {'color': 'green', 'icon': 'play', 'prefix': 'fa'},
                        'popup_html': f"<b>Start</b><br>{route_name}",
                        'tooltip': 'Start'
                    },
                    {
                        'position': coordinates[-1],
                        'icon': {'color': 'red', 'icon': 'stop', 'prefix': 'fa'},
                        'popup_html': f"<b>End</b><br>{route_name}",
                        'tooltip': 'End'
                    }
                ],
                'layers': []
            }
            
            return jsonify(map_data)
        
        else:
            return jsonify({
                'status': 'error',
                'message': f'Unknown page type: {page_type}'
            }), 400
        
    except Exception as e:
        logger.error(f"Error getting map data for {page_type}: {e}", exc_info=True)
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


if __name__ == '__main__':
    # Development server
    import os
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
    
    # Open browser in a separate thread after server starts
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    app.run(host='0.0.0.0', port=port, debug=False)


# Made with Bob