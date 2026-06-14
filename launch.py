"""
Minimal Flask API for Smart Static architecture.

Provides 4 JSON endpoints for static HTML pages to fetch data:
- /api/weather - Current weather data
- /api/recommendation - Next commute recommendation
- /api/routes - All routes for library
- /api/status - System health and freshness

No sessions, CORS, rate limiting - optimized for single-user Pi deployment.
"""

from flask import Flask, jsonify, send_from_directory, request, redirect, url_for, session
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pathlib import Path
import logging
from datetime import datetime, timedelta
import webbrowser
import threading
import time
import json
import secrets
import os
from typing import List, Dict, Any

from src.config import Config
from src.json_storage import JSONStorage
from src.route_analyzer import Route, RouteGroup
from src.location_finder import Location
from app.services.analysis_service import AnalysisService
from app.services.commute_service import CommuteService
from app.services.weather_service import WeatherService
from src.weather_fetcher import WindImpactCalculator
from app.services.planner_service import PlannerService
from app.services.route_library_service import RouteLibraryService
from app.api import maps_api
from src.secure_logger import SecureLogger
from src.auth_secure import SecureTokenStorage
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

def _load_or_create_secret_key() -> str:
    """Load SECRET_KEY from env var, then persisted file, or generate and persist a new one."""
    if key := os.getenv('FLASK_SECRET_KEY'):
        return key
    key_file = Path('config/secret_key')
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.parent.mkdir(exist_ok=True)
    key_file.write_text(key)
    key_file.chmod(0o600)
    return key


# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['JSON_SORT_KEYS'] = False
app.config['SECRET_KEY'] = _load_or_create_secret_key()

# Configure session security
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Set to True when using HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    WTF_CSRF_CHECK_DEFAULT=False,  # Explicit opt-in per route via @csrf.protect; JSON API uses SameSite+Content-Type
)

# Initialize CSRF protection (infrastructure ready; token served at /api/csrf-token for future mutations)
csrf = CSRFProtect(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Register blueprints
app.register_blueprint(maps_api.bp)


@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
        "img-src 'self' data: https: blob:; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    
    # Add HSTS if using HTTPS
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response


@app.route('/api/csrf-token')
@csrf.exempt
def get_csrf_token():
    """Return a CSRF token for clients making state-changing requests."""
    return jsonify({'csrf_token': generate_csrf()})

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
_analysis_job = {'status': 'idle', 'started_at': None, 'result': None}
_analysis_stop_requested = False
_fetch_job = {'status': 'idle', 'fetched': 0, 'label': '', 'started_at': None}


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
@limiter.limit("30 per minute")
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
            temp_c = weather_data.get('temp_c', 0) or 0
            feels_like_c = weather_data.get('feels_like_c', temp_c) or temp_c
            formatted_weather = {
                'temperature': round(weather_data.get('temperature_f', temp_c * 9/5 + 32)),
                'feels_like': round(weather_data.get('feels_like_f', feels_like_c * 9/5 + 32)),
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
        # Hide internal error details in production
        error_msg = str(e) if app.debug else 'Weather data temporarily unavailable'
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500


def _degrees_to_cardinal(deg: float) -> str:
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return dirs[round(deg / 22.5) % 16]


@app.route('/api/weather/commute-windows')
@limiter.limit("20 per minute")
def get_commute_windows():
    """
    Get hourly weather forecast sliced into morning and evening commute windows.

    Returns morning (7–9 AM) and evening (3–6 PM) conditions plus an optimal
    departure suggestion for each window — covering issues #110, #111, #115.
    """
    initialize_services()

    try:
        lat = config.get('location.home.latitude')
        lon = config.get('location.home.longitude')
        if not lat or not lon:
            return jsonify({'status': 'error', 'message': 'Home location not configured'}), 400

        lat, lon = float(lat), float(lon)
        hourly = _weather_service.fetcher.get_hourly_forecast(lat, lon, hours=24)
        if not hourly:
            return jsonify({'status': 'error', 'message': 'Forecast unavailable'}), 503

        def _format_hour(h: dict) -> dict:
            temp_f = round(h['temp_c'] * 9 / 5 + 32)
            wind_mph = round(h['wind_speed_kph'] * 0.621371)
            gust_mph = round(h.get('wind_gust_kph', h['wind_speed_kph']) * 0.621371)
            wind_deg = h.get('wind_direction_deg', 0)
            return {
                'hour': h['timestamp'][11:16],   # "HH:MM"
                'temp_f': temp_f,
                'wind_mph': wind_mph,
                'wind_gust_mph': gust_mph,
                'wind_direction': _degrees_to_cardinal(wind_deg),
                'precip_prob': h.get('precipitation_prob', 0),
            }

        def _window_summary(hours: list) -> dict:
            if not hours:
                return {}
            avg_temp = round(sum(h['temp_f'] for h in hours) / len(hours))
            avg_wind = round(sum(h['wind_mph'] for h in hours) / len(hours))
            max_precip = max(h['precip_prob'] for h in hours)
            # Optimal = least discomfort: weight precip 2x, wind equally
            best = min(hours, key=lambda h: h['precip_prob'] * 2 + h['wind_mph'])
            dirs = [h['wind_direction'] for h in hours]
            dominant_dir = max(set(dirs), key=dirs.count)
            return {
                'avg_temp_f': avg_temp,
                'avg_wind_mph': avg_wind,
                'max_precip_prob': max_precip,
                'dominant_wind_direction': dominant_dir,
                'optimal_departure': best['hour'],
                'hours': hours,
            }

        morning_raw, evening_raw = [], []
        for h in hourly:
            ts = h.get('timestamp', '')
            try:
                hour_int = int(ts[11:13])
            except (ValueError, IndexError):
                continue
            if 7 <= hour_int <= 8:   # 7:00–8:59
                morning_raw.append(_format_hour(h))
            elif 15 <= hour_int <= 17:  # 15:00–17:59
                evening_raw.append(_format_hour(h))

        return jsonify({
            'status': 'success',
            'morning': _window_summary(morning_raw),
            'evening': _window_summary(evening_raw),
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error getting commute windows: {e}", exc_info=True)
        error_msg = str(e) if app.debug else 'Forecast data temporarily unavailable'
        return jsonify({'status': 'error', 'message': error_msg}), 500


@app.route('/api/weather/forecast')
@limiter.limit("20 per minute")
def get_weather_forecast():
    """
    Get 7-day daily weather forecast.

    Returns daily forecasts with comfort scores and cycling favorability,
    covering issues #109 and #54 (7-day forecast card data).
    """
    initialize_services()

    try:
        lat = config.get('location.home.latitude')
        lon = config.get('location.home.longitude')
        if not lat or not lon:
            return jsonify({'status': 'error', 'message': 'Home location not configured'}), 400

        lat, lon = float(lat), float(lon)
        raw = _weather_service.fetcher.get_daily_forecast(lat, lon, days=7)
        if not raw:
            return jsonify({'status': 'error', 'message': 'Forecast unavailable'}), 503

        def _comfort(day: dict) -> float:
            temp_c = (day.get('temp_max_c', 20) + day.get('temp_min_c', 15)) / 2
            score = 1.0
            if temp_c < 0:
                score -= 0.4
            elif temp_c < 10:
                score -= 0.2
            elif temp_c > 35:
                score -= 0.5
            elif temp_c > 30:
                score -= 0.3
            wind = day.get('wind_speed_max_kph', 0) or 0
            if wind > 30:
                score -= 0.3
            elif wind > 20:
                score -= 0.15
            precip = day.get('precipitation_sum_mm', 0) or 0
            if precip > 5:
                score -= 0.4
            elif precip > 0:
                score -= 0.2
            return round(max(0.0, min(1.0, score)), 2)

        def _favorability(score: float) -> str:
            if score >= 0.7:
                return 'favorable'
            elif score >= 0.4:
                return 'neutral'
            return 'unfavorable'

        days = []
        for day in raw:
            comfort = _comfort(day)
            temp_max_f = round(day.get('temp_max_c', 20) * 9 / 5 + 32)
            temp_min_f = round(day.get('temp_min_c', 15) * 9 / 5 + 32)
            wind_mph = round((day.get('wind_speed_max_kph', 0) or 0) * 0.621371)
            wind_dir = _degrees_to_cardinal(day.get('wind_direction_dominant_deg', 0) or 0)
            precip_prob = day.get('precipitation_prob_max', 0) or 0
            precip_in = round((day.get('precipitation_sum_mm', 0) or 0) * 0.0393701, 2)
            days.append({
                'date': day.get('date'),
                'temp_max_f': temp_max_f,
                'temp_min_f': temp_min_f,
                'wind_mph': wind_mph,
                'wind_direction': wind_dir,
                'precip_prob': precip_prob,
                'precip_in': precip_in,
                'comfort_score': int(comfort * 100),
                'cycling_favorability': _favorability(comfort),
            })

        return jsonify({
            'status': 'success',
            'forecast': days,
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error getting weather forecast: {e}", exc_info=True)
        error_msg = str(e) if app.debug else 'Forecast data temporarily unavailable'
        return jsonify({'status': 'error', 'message': error_msg}), 500


@app.route('/api/recommendation')
@limiter.limit("20 per minute")
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
        error_msg = str(e) if app.debug else 'Recommendation temporarily unavailable'
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500


def _enrich_commute_recommendation(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Add reasons, weather_summary, and time_impact to a recommendation dict."""
    if not rec or rec.get('status') != 'success':
        return rec

    enriched = dict(rec)
    weather = rec.get('weather') or {}
    breakdown = rec.get('breakdown') or {}
    route = rec.get('route') or {}

    # weather_summary — natural language sentence
    temp = weather.get('temperature', 0)
    wind_speed = weather.get('wind_speed', 0)
    wind_dir = weather.get('wind_direction', '')
    conditions = (weather.get('conditions') or '').lower()

    sky_part = 'Clear skies'
    if 'thunder' in conditions or 'storm' in conditions:
        sky_part = 'Stormy'
    elif 'rain' in conditions or 'drizzle' in conditions:
        sky_part = 'Rainy'
    elif 'snow' in conditions:
        sky_part = 'Snowy'
    elif 'cloud' in conditions or 'overcast' in conditions:
        sky_part = 'Cloudy'
    elif 'fog' in conditions or 'mist' in conditions:
        sky_part = 'Foggy'
    elif conditions:
        sky_part = conditions.capitalize()

    wind_part = ''
    if wind_speed >= 15:
        wind_part = f'strong {wind_dir} wind ({round(wind_speed)} mph)'
    elif wind_speed >= 8:
        wind_part = f'light {wind_dir} wind'
    elif wind_speed >= 3:
        wind_part = 'gentle breeze'

    enriched['weather_summary'] = f"{sky_part}{', ' + wind_part if wind_part else ''}"

    # wind_impact — headwind/tailwind analysis for this route (#113)
    wind_impact = None
    coords = route.get('coordinates') or []
    wind_deg = weather.get('wind_direction_deg')
    wind_kph = weather.get('wind_speed_kph')
    if len(coords) >= 2 and wind_deg is not None and wind_kph is not None:
        try:
            start = tuple(coords[0])[:2]
            end = tuple(coords[-1])[:2]
            bearing = WindImpactCalculator.calculate_bearing(start, end)
            components = WindImpactCalculator.calculate_wind_component(
                float(wind_kph), float(wind_deg), bearing
            )
            hw_mph = round(components['headwind_kph'] * 0.621371)
            abs_mph = abs(hw_mph)
            if hw_mph > 3:
                label = f'Headwind ~{abs_mph} mph'
                icon = 'bi-wind text-warning'
            elif hw_mph < -3:
                label = f'Tailwind ~{abs_mph} mph'
                icon = 'bi-wind text-success'
            else:
                label = 'Crosswind'
                icon = 'bi-wind text-info'
            wind_impact = {'label': label, 'mph': abs_mph, 'icon': icon,
                           'is_tailwind': hw_mph < -3, 'is_headwind': hw_mph > 3}
        except Exception:
            pass
    enriched['wind_impact'] = wind_impact

    # reasons — 2–4 decision bullets
    reasons = []
    weather_score = breakdown.get('weather', 0)
    if isinstance(weather_score, (int, float)) and weather_score > 0.75:
        reasons.append('Favorable weather for cycling today')
    elif wind_impact and wind_impact.get('is_tailwind') and wind_speed >= 8:
        reasons.append(f"Tailwind advantage — ~{wind_impact['mph']} mph boost")
    elif wind_impact and wind_impact.get('is_headwind') and wind_speed >= 15:
        reasons.append(f"Strong headwind (~{wind_impact['mph']} mph) — expect slower pace")
    elif wind_speed >= 15:
        reasons.append('Strong wind — check if it works as a tailwind')

    frequency = route.get('frequency', 0)
    if frequency >= 10:
        reasons.append('Your most-ridden route — reliable timing')
    elif frequency >= 3:
        reasons.append('A familiar route for you')

    time_score = breakdown.get('time', 0)
    if isinstance(time_score, (int, float)) and time_score > 0.8:
        reasons.append('Optimal timing for your usual commute window')

    safety_score = breakdown.get('safety', 0)
    if isinstance(safety_score, (int, float)) and safety_score > 0.75:
        reasons.append('No known obstacles or hazards')

    if not reasons:
        score = rec.get('score', 0)
        score_val = int(score * 100) if isinstance(score, float) and score <= 1 else int(score)
        if score_val >= 70:
            reasons.append('Best available option given current conditions')
        else:
            reasons.append('Consider checking alternative routes today')

    enriched['reasons'] = reasons[:4]

    # time_impact — estimated duration; route.duration is in seconds, convert to minutes
    duration_secs = route.get('duration', 0)
    duration_mins = round(duration_secs / 60) if duration_secs else None
    enriched['time_impact'] = {
        'estimated_minutes': duration_mins,
        'vs_average_minutes': None,
        'label': f'~{duration_mins} minutes estimated' if duration_mins else None
    }

    # transit_recommendation — suggest transit when conditions are unfavorable (#114)
    enriched['transit_recommendation'] = _get_transit_recommendation(weather)

    return enriched


def _get_transit_recommendation(weather: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a transit suggestion when cycling conditions are too poor.

    Triggers on:
    - comfort_score < 0.4 (service-level 'unfavorable')
    - Thunderstorms / severe storms regardless of score

    Returns dict with:
      suggested (bool), severity ('severe'|'poor'|None), reason (str), transit_url (str)
    """
    if not weather:
        return {'suggested': False}

    conditions = (weather.get('conditions') or '').lower()
    comfort_score = weather.get('comfort_score')
    favorability = (weather.get('cycling_favorability') or '').lower()

    # Severe: thunderstorm / electrical storm — always suggest transit
    is_severe = 'thunder' in conditions or 'storm' in conditions
    is_heavy_precip = 'heavy rain' in conditions or 'heavy snow' in conditions or 'blizzard' in conditions

    if is_severe or is_heavy_precip:
        reason = 'Dangerous conditions — thunderstorm or severe weather' if is_severe else 'Heavy precipitation — cycling not advised'
        return {
            'suggested': True,
            'severity': 'severe',
            'reason': reason,
            'transit_url': 'https://www.google.com/maps?travelmode=transit',
        }

    # Poor: backend says 'unfavorable' (comfort_score < 0.4)
    if favorability == 'unfavorable' or (isinstance(comfort_score, (int, float)) and comfort_score < 0.4):
        # Build a human-readable reason from the dominant factor
        temp = weather.get('temperature', weather.get('temp_f'))
        wind_speed = weather.get('wind_speed', weather.get('wind_speed_kph', 0))
        precip_mm = weather.get('precipitation_mm', weather.get('precipitation', 0))

        if 'rain' in conditions or 'drizzle' in conditions or (isinstance(precip_mm, (int, float)) and precip_mm > 2):
            reason = 'Rainy conditions — consider public transit or waiting for a dry window'
        elif 'snow' in conditions:
            reason = 'Snowy conditions — transit may be safer'
        elif isinstance(temp, (int, float)) and temp <= 25:
            reason = f'Very cold ({round(temp)}°F) — transit recommended'
        elif isinstance(temp, (int, float)) and temp >= 95:
            reason = f'Extreme heat ({round(temp)}°F) — consider transit'
        elif isinstance(wind_speed, (int, float)) and wind_speed >= 25:
            reason = f'Very strong winds ({round(wind_speed)} mph) — transit recommended'
        else:
            reason = 'Poor cycling conditions today — transit is a good alternative'

        return {
            'suggested': True,
            'severity': 'poor',
            'reason': reason,
            'transit_url': 'https://www.google.com/maps?travelmode=transit',
        }

    return {'suggested': False}


@app.route('/api/commute')
@limiter.limit("30 per minute")
def get_commute():
    """
    Get both commute directions (to_work and to_home) for the commute view.

    Returns:
        JSON with both direction recommendations including reasons, weather_summary,
        and time_impact fields for the Hero Decision Card (#286).
    """
    initialize_services()

    try:
        # Get recommendations for both directions
        to_work = _enrich_commute_recommendation(
            _commute_service.get_next_commute(direction='to_work')
        )
        to_home = _enrich_commute_recommendation(
            _commute_service.get_next_commute(direction='to_home')
        )

        return jsonify({
            'status': 'success',
            'to_work': to_work,
            'to_home': to_home,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting commute data: {e}", exc_info=True)
        error_msg = str(e) if app.debug else 'Commute data temporarily unavailable'
        return jsonify({
            'status': 'error',
            'message': error_msg
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
@limiter.limit("30 per minute")
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
        search_query = request.args.get('search', '').strip()
        route_type = request.args.get('type', 'all')
        sort_by = request.args.get('sort', 'uses')
        limit = request.args.get('limit', type=int)

        if search_query:
            routes_data = _route_library_service.search_routes(
                query=search_query,
                limit=limit or 50
            )
            raw_routes = routes_data.get('results', [])
        else:
            routes_data = _route_library_service.get_all_routes(
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
        error_msg = str(e) if app.debug else 'Routes temporarily unavailable'
        return jsonify({
            'status': 'error',
            'message': error_msg,
            'routes': [],
            'total_count': 0
        }), 500


@app.route('/api/routes/status')
def get_routes_status():
    """
    Get per-route condition summary crossing route data with current weather (#289).

    Returns:
        JSON with commute routes list, each with condition_score and condition_note.
    """
    initialize_services()

    try:
        routes_data = _route_library_service.get_all_routes(
            route_type='commute', sort_by='uses', limit=6
        )
        routes = routes_data.get('routes', []) if routes_data.get('status') == 'success' else []

        # Get current weather at home location
        home_lat = config.get('location.home.latitude')
        home_lon = config.get('location.home.longitude')
        current_weather = None
        if home_lat and home_lon:
            raw = _weather_service.get_current_weather(home_lat, home_lon)
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


@app.route('/api/routes/search')
@limiter.limit("30 per minute")
def search_routes():
    """
    Search routes by name.

    Query params:
    - q: Search query string (required)
    - limit: Maximum results (default 10, max 100)

    Returns:
        JSON with routes list matching the query
    """
    initialize_services()

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
        result = _route_library_service.search_routes(query, limit=limit)
        routes = result.get('results', [])
        return jsonify({
            'status': 'success',
            'query': query,
            'routes': routes,
            'total_count': len(routes)
        })
    except Exception as e:
        logger.error(f"Error searching routes: {e}", exc_info=True)
        error_msg = str(e) if app.debug else 'Search temporarily unavailable'
        return jsonify({
            'status': 'error',
            'message': error_msg,
            'routes': [],
            'total_count': 0
        }), 500


@app.route('/api/routes/<route_id>')
@limiter.limit("60 per minute")
def get_route_detail(route_id):
    """Get a single route detail payload by route ID with validation."""
    initialize_services()

    try:
        # Validate route_id format to prevent injection
        if not route_id or not route_id.replace('-', '').replace('_', '').isalnum():
            return jsonify({
                'status': 'error',
                'message': 'Invalid route ID format'
            }), 400
        
        if len(route_id) > 100:
            return jsonify({
                'status': 'error',
                'message': 'Route ID too long'
            }), 400
        
        route_type = request.args.get('type')
        route = _route_library_service.get_route_by_id(route_id, route_type=route_type)

        if not route:
            return jsonify({
                'status': 'error',
                'message': 'Route not found'
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
@limiter.exempt
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
        error_msg = str(e) if app.debug else 'Status temporarily unavailable'
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500


@app.route('/api/strava/status')
def strava_status():
    storage = SecureTokenStorage('config/credentials.json')
    tokens = storage.load_tokens()
    if tokens is None:
        return jsonify({'connected': False, 'reason': 'no_credentials'})

    # Migration: grant existing tokens without auth_expires_at a 90-day window from now
    auth_expires_at = tokens.get('auth_expires_at') or (time.time() + 90 * 86400)

    if auth_expires_at < time.time():
        return jsonify({'connected': False, 'reason': 'auth_expired'})

    # Auto-refresh the short-lived access token when it has expired
    if tokens.get('expires_at', 0) < time.time():
        try:
            import requests as http_req
            resp = http_req.post('https://www.strava.com/oauth/token', data={
                'client_id': os.getenv('STRAVA_CLIENT_ID'),
                'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
                'refresh_token': tokens['refresh_token'],
                'grant_type': 'refresh_token',
            }, timeout=15)
            resp.raise_for_status()
            refreshed = resp.json()
            tokens['access_token'] = refreshed['access_token']
            tokens['refresh_token'] = refreshed['refresh_token']
            tokens['expires_at'] = refreshed['expires_at']
            tokens['auth_expires_at'] = auth_expires_at
            storage.save_tokens(tokens)
        except Exception as e:
            logger.warning(f"Strava token refresh failed in status check: {e}")
            return jsonify({'connected': False, 'reason': 'refresh_failed'})

    return jsonify({'connected': True, 'expires_at': tokens['expires_at'], 'auth_expires_at': auth_expires_at})


@app.route('/api/strava/connect')
def strava_connect():
    state = secrets.token_hex(16)
    session['strava_oauth_state'] = state
    # Remember if the user came from the setup wizard
    if request.args.get('setup_redirect') == '1':
        session['setup_redirect'] = True
    client_id = os.getenv('STRAVA_CLIENT_ID')
    redirect_uri = url_for('strava_callback', _external=True)
    auth_url = (
        'https://www.strava.com/oauth/authorize'
        f'?client_id={client_id}'
        f'&redirect_uri={redirect_uri}'
        '&response_type=code'
        '&scope=read,activity:read_all'
        f'&state={state}'
    )
    return redirect(auth_url)


@app.route('/api/strava/callback')
@csrf.exempt
def strava_callback():
    error = request.args.get('error')
    if error:
        logger.error(f"Strava OAuth error: {error}")
        return redirect('/settings.html?strava_error=' + error)

    state = request.args.get('state')
    if not state or state != session.pop('strava_oauth_state', None):
        logger.warning("Strava callback: invalid state (possible CSRF)")
        return redirect('/settings.html?strava_error=invalid_state')

    code = request.args.get('code')
    if not code:
        return redirect('/settings.html?strava_error=no_code')

    try:
        import requests as http_req
        resp = http_req.post('https://www.strava.com/oauth/token', data={
            'client_id': os.getenv('STRAVA_CLIENT_ID'),
            'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
            'code': code,
            'grant_type': 'authorization_code',
        }, timeout=15)
        resp.raise_for_status()
        token_data = resp.json()

        storage = SecureTokenStorage('config/credentials.json')
        storage.save_tokens({
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_at': token_data['expires_at'],
            'auth_expires_at': time.time() + 180 * 86400,
        })
        logger.info("Strava OAuth complete — credentials saved")

        global _services_initialized
        _services_initialized = False

        # Redirect back to setup wizard when coming from FTUE flow
        setup_redirect = session.pop('setup_redirect', False)
        if setup_redirect:
            return redirect('/setup.html?connected=1')
        return redirect('/settings.html?strava_connected=1')
    except Exception as e:
        logger.error(f"Strava token exchange failed: {e}", exc_info=True)
        setup_redirect = session.pop('setup_redirect', False)
        if setup_redirect:
            return redirect('/setup.html?strava_error=token_exchange_failed')
        return redirect('/settings.html?strava_error=token_exchange_failed')


# ---------------------------------------------------------------------------
# Setup / FTUE endpoints (Issue #260)
# ---------------------------------------------------------------------------

def _env_path() -> Path:
    return Path('.env')


def _read_env() -> dict:
    """Parse .env file into a dict. Returns {} when file is absent."""
    env_file = _env_path()
    if not env_file.exists():
        return {}
    result = {}
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            result[key.strip()] = value.strip()
    return result


def _write_env(data: dict) -> None:
    """Write *data* key=value pairs to .env, preserving existing unrelated keys."""
    env_file = _env_path()
    existing = {}
    lines_out = []

    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key, _, value = stripped.partition('=')
                existing[key.strip()] = len(lines_out)
                lines_out.append(line)
            else:
                lines_out.append(line)

    for key, value in data.items():
        safe_value = str(value).replace('\n', '').replace('\r', '')
        if key in existing:
            lines_out[existing[key]] = f'{key}={safe_value}'
        else:
            lines_out.append(f'{key}={safe_value}')

    env_file.write_text('\n'.join(lines_out) + '\n', encoding='utf-8')
    env_file.chmod(0o600)


@app.route('/api/setup/status')
def setup_status():
    """Return whether Strava credentials are configured."""
    client_id = os.getenv('STRAVA_CLIENT_ID') or _read_env().get('STRAVA_CLIENT_ID', '')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET') or _read_env().get('STRAVA_CLIENT_SECRET', '')
    configured = bool(client_id and client_secret)
    storage = SecureTokenStorage('config/credentials.json')
    tokens = storage.load_tokens()
    authorized = tokens is not None
    return jsonify({
        'configured': configured,
        'authorized': authorized,
        'setup_complete': configured and authorized,
    })


@app.route('/api/setup/credentials', methods=['POST'])
@csrf.exempt
def setup_credentials():
    """Save Strava Client ID and Secret to .env."""
    data = request.get_json(silent=True) or {}
    client_id = str(data.get('client_id', '')).strip()
    client_secret = str(data.get('client_secret', '')).strip()

    if not client_id or not client_secret:
        return jsonify({'success': False, 'error': 'client_id and client_secret are required'}), 400
    if not client_id.isdigit():
        return jsonify({'success': False, 'error': 'client_id must be numeric'}), 400
    if len(client_secret) < 8:
        return jsonify({'success': False, 'error': 'client_secret appears too short'}), 400

    try:
        _write_env({'STRAVA_CLIENT_ID': client_id, 'STRAVA_CLIENT_SECRET': client_secret})
        os.environ['STRAVA_CLIENT_ID'] = client_id
        os.environ['STRAVA_CLIENT_SECRET'] = client_secret
        logger.info("Setup: Strava credentials saved via setup wizard")
        return jsonify({'success': True})
    except OSError as exc:
        logger.error("Setup: failed to write .env: %s", exc)
        return jsonify({'success': False, 'error': 'Could not write credentials file'}), 500


@app.route('/api/setup/verify', methods=['POST'])
@csrf.exempt
def setup_verify():
    """Test Strava credentials by exchanging a short-lived auth code or hitting /athlete."""
    client_id = os.getenv('STRAVA_CLIENT_ID') or _read_env().get('STRAVA_CLIENT_ID', '')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET') or _read_env().get('STRAVA_CLIENT_SECRET', '')

    if not client_id or not client_secret:
        return jsonify({'valid': False, 'error': 'Credentials not configured yet'}), 400

    # We can't fully verify without a token, but we can confirm the credentials
    # exist and look structurally valid.  A lightweight check posts to the Strava
    # token endpoint with an obviously-bad code — Strava returns 400 with
    # {"message":"Bad Request","errors":[{"resource":"AuthorizationCode",...}]}
    # which tells us the app_id/secret were accepted (not a 401 Unauthorized).
    try:
        import requests as http_req
        resp = http_req.post(
            'https://www.strava.com/oauth/token',
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': 'verify_probe',
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        body = resp.json()
        if resp.status_code == 400 and 'AuthorizationCode' in str(body):
            return jsonify({'valid': True, 'message': 'Credentials accepted by Strava'})
        if resp.status_code == 401:
            return jsonify({'valid': False, 'error': 'Strava rejected the credentials — check your Client ID and Secret'})
        return jsonify({'valid': True, 'message': 'Credentials appear valid'})
    except Exception as exc:
        logger.warning("Setup verify error: %s", exc)
        return jsonify({'valid': False, 'error': 'Could not reach Strava to verify'}), 503


@app.route('/api/cache-info')
def get_cache_info():
    cache_path = Path('data/cache/activities.json')
    if not cache_path.exists():
        return jsonify({'status': 'no_cache', 'activity_count': 0})
    try:
        with open(cache_path) as f:
            cache_data = json.load(f)
        activities = cache_data.get('activities', cache_data) if isinstance(cache_data, dict) else cache_data
        if not isinstance(activities, list):
            return jsonify({'status': 'error', 'message': 'Cache format unrecognized'}), 500
        dates = sorted(a['start_date'] for a in activities if isinstance(a, dict) and a.get('start_date'))
        stat = cache_path.stat()
        return jsonify({
            'status': 'ok',
            'activity_count': len(activities),
            'date_earliest': dates[0] if dates else None,
            'date_latest': dates[-1] if dates else None,
            'cache_size_mb': round(stat.st_size / (1024 * 1024), 1),
            'cache_age_hours': round((datetime.now().timestamp() - stat.st_mtime) / 3600, 1),
        })
    except Exception as e:
        logger.error(f"Error reading cache info: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def trigger_analysis():
    global _analysis_job
    if _analysis_job.get('status') == 'running':
        return jsonify({'status': 'already_running', 'message': 'Analysis is already in progress'}), 409

    initialize_services()
    data = request.get_json(silent=True) or {}
    fetch_new = bool(data.get('fetch_new', False))

    after_date = None
    before_date = None
    if fetch_new:
        for key, target in [('after_date', 'after_date'), ('before_date', 'before_date')]:
            raw = data.get(key)
            if raw:
                try:
                    parsed = datetime.fromisoformat(raw)
                    if key == 'after_date':
                        after_date = parsed
                    else:
                        before_date = parsed
                except (ValueError, TypeError):
                    pass

    _analysis_job = {
        'status': 'running',
        'phase': 'starting',
        'fetched': 0,
        'preview_ready': False,
        'preview_count': 0,
        'label': 'Starting…',
        'started_at': datetime.now().isoformat(),
        'result': None,
        'routes_done': 0,
        'routes_total': 0,
        'eta_secs': None,
    }

    def _update_job(**kwargs):
        global _analysis_job
        for k, v in kwargs.items():
            _analysis_job[k] = v

    global _analysis_stop_requested
    _analysis_stop_requested = False

    def _stop_check():
        return _analysis_stop_requested

    def _run():
        global _analysis_job, _services_initialized, _analysis_stop_requested
        try:
            result = _analysis_service.run_full_analysis(
                force_refresh=True,
                skip_strava_fetch=not fetch_new,
                after=after_date,
                before=before_date,
                on_progress=_update_job,
                stop_check=_stop_check,
            )
            if _analysis_stop_requested:
                _update_job(status='stopped', phase='stopped',
                            label='Analysis stopped by user')
            else:
                _update_job(status='done', phase='done', result=result,
                            label=f"Done — {result.get('activities_count', 0):,} activities")
            _services_initialized = False
        except Exception as e:
            logger.error(f"Background analysis failed: {e}", exc_info=True)
            _update_job(status='error', phase='error',
                        result={'status': 'error', 'message': str(e)},
                        label=f'Error: {e}')
        finally:
            _analysis_stop_requested = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'fetch_new': fetch_new})


@app.route('/api/analyze/status')
@limiter.exempt
def get_analyze_status():
    return jsonify(_analysis_job)


@app.route('/api/analyze/stop', methods=['POST'])
@limiter.exempt
def stop_analysis():
    global _analysis_stop_requested, _analysis_job
    if _analysis_job.get('status') != 'running':
        return jsonify({'status': 'not_running'}), 400
    _analysis_stop_requested = True
    _analysis_job['label'] = 'Stopping…'
    return jsonify({'status': 'stopping'})


@app.route('/api/fetch', methods=['POST'])
@limiter.limit("5 per minute")
def trigger_fetch():
    global _fetch_job
    if _fetch_job.get('status') == 'running':
        return jsonify({'status': 'already_running'}), 409

    initialize_services()
    data = request.get_json(silent=True) or {}

    after_date = None
    before_date = None
    for key in ('after_date', 'before_date'):
        raw = data.get(key)
        if raw:
            try:
                val = datetime.fromisoformat(raw)
                if key == 'after_date':
                    after_date = val
                else:
                    before_date = val
            except (ValueError, TypeError):
                pass

    limit = int(data.get('limit', 1000))

    _fetch_job = {
        'status': 'running',
        'fetched': 0,
        'label': 'Connecting to Strava…',
        'started_at': datetime.now().isoformat(),
        'total_in_cache': 0,
    }

    def _run():
        global _fetch_job
        try:
            import time as _time
            import json as _json
            from pathlib import Path as _Path

            def _progress(count):
                # Sleep 2s every 30 activities (one Strava page) to stay gentle on the Pi
                if count % 30 == 0 and count > 0:
                    _time.sleep(2)
                _fetch_job['fetched'] = count
                _fetch_job['label'] = f'Fetching from Strava… {count:,} activities'

            _analysis_service.data_fetcher.fetch_activities(
                limit=limit,
                after=after_date,
                before=before_date,
                use_cache=False,
                progress_callback=_progress,
                merge_cache=True,
            )

            cache_path = _Path('data/cache/activities.json')
            total = _fetch_job['fetched']
            if cache_path.exists():
                with open(cache_path) as f:
                    raw = _json.load(f)
                total = raw.get('count', len(raw.get('activities', [])))

            _fetch_job.update({
                'status': 'done',
                'label': f'Done — {total:,} activities in cache',
                'total_in_cache': total,
            })
        except Exception as e:
            logger.error(f"Background fetch failed: {e}", exc_info=True)
            _fetch_job.update({
                'status': 'error',
                'label': f'Error: {e}',
            })

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started'})


@app.route('/api/fetch/status')
@limiter.exempt
def get_fetch_status():
    return jsonify(_fetch_job)


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
    
    # Validate port
    if not isinstance(port, int) or port < 1024 or port > 65535:
        logger.error(f"Invalid port for browser: {port}")
        return
    
    # Use 127.0.0.1 instead of localhost for security
    url = f'http://127.0.0.1:{port}'
    
    # Validate URL before opening
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https'] or parsed.hostname not in ['127.0.0.1', 'localhost']:
        logger.error(f"Invalid URL for browser: {url}")
        return
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
    
    # Validate port is an integer in valid range
    if not isinstance(port, int) or port < 1024 or port > 65535:
        logger.error(f"Invalid port number: {port}")
        return
    
    try:
        # Find process using the port
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5  # Add timeout for security
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            current_user = os.getenv('USER') or os.getenv('USERNAME')
            
            for pid in pids:
                try:
                    pid_int = int(pid)
                    
                    # Verify process belongs to current user before killing
                    try:
                        proc_info = subprocess.run(
                            ['ps', '-p', str(pid_int), '-o', 'user='],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        proc_user = proc_info.stdout.strip()
                        
                        if proc_user == current_user:
                            logger.info(f"Killing server process {pid_int} on port {port}")
                            os.kill(pid_int, signal.SIGTERM)
                            time.sleep(0.5)  # Give it time to terminate
                        else:
                            logger.warning(f"Skipping process {pid_int} - owned by {proc_user}, not {current_user}")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Timeout checking ownership of process {pid_int}")
                    except Exception as e:
                        logger.debug(f"Could not verify process {pid_int} ownership: {e}")
                        
                except (ValueError, ProcessLookupError, PermissionError) as e:
                    logger.debug(f"Could not kill process {pid}: {e}")
                    
    except subprocess.TimeoutExpired:
        logger.error("Timeout checking for existing server")
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


