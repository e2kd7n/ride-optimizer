"""
Commute blueprint - Next commute recommendations and analysis.

Provides intelligent commute route recommendations based on:
- Current weather conditions
- Traffic patterns
- Workout fit (TrainerRoad integration)
- Historical route performance
- Departure timing optimization
"""

from flask import Blueprint, render_template, request, jsonify, current_app, g
from datetime import datetime, timedelta
import traceback

from app.services import AnalysisService, CommuteService
from src.config import Config

bp = Blueprint('commute', __name__, url_prefix='/commute')


def get_services():
    """Get or create service instances for this request."""
    if 'services' not in g:
        config = Config('config/config.yaml')
        g.services = {
            'analysis': AnalysisService(config),
            'commute': CommuteService(config)
        }
    return g.services


@bp.route('/')
def index():
    """
    Main commute recommendations view.
    
    Shows:
    - Best route for next commute
    - Alternative routes with pros/cons
    - Optimal departure time window
    - Weather forecast impact
    - Workout fit analysis
    """
    current_app.logger.info('Commute recommendations accessed')
    
    services = get_services()
    analysis_service = services['analysis']
    commute_service = services['commute']
    weather_service = services['weather']
    
    # Get direction from query param or auto-detect
    direction = request.args.get('direction')
    
    # Initialize commute service
    recommendation = None
    alternatives = []
    departure_windows = []
    route_weather = None
    
    try:
        route_groups = analysis_service.get_route_groups()
        home, work = analysis_service.get_locations()
        
        if route_groups and home and work:
            commute_service.initialize(route_groups, home, work)
            
            # Get primary recommendation
            rec_data = commute_service.get_next_commute(direction=direction)
            
            if rec_data.get('status') == 'success':
                route = rec_data.get('route', {})
                
                # Get detailed weather for the route
                route_coords = route.get('coordinates', [])
                if route_coords:
                    try:
                        route_weather = weather_service.get_route_weather(
                            route_coords,
                            route_name=route.get('name', 'Route')
                        )
                        current_app.logger.info(f"Route weather: {route_weather.get('cycling_favorability') if route_weather else 'unavailable'}")
                    except Exception as e:
                        current_app.logger.error(f"Error getting route weather: {e}")
                
                recommendation = {
                    'direction': rec_data.get('direction'),
                    'direction_display': rec_data.get('direction', '').replace('_', ' ').title(),
                    'route_name': route.get('name', 'Unknown Route'),
                    'route_id': route.get('id'),
                    'distance': route.get('distance', 0) / 1000,  # km
                    'duration': route.get('duration', 0) / 60,  # minutes
                    'elevation': route.get('elevation', 0),  # meters
                    'score': rec_data.get('score', 0),
                    'breakdown': rec_data.get('breakdown', {}),
                    'weather': route_weather,  # Enhanced weather with wind impact
                    'departure_time': rec_data.get('departure_time'),
                    'confidence': rec_data.get('confidence', 'medium')
                }
                
                # Get alternatives
                alt_direction = rec_data.get('direction')
                if alt_direction:
                    alt_data = commute_service.get_all_commute_options(alt_direction)
                    if alt_data.get('status') == 'success':
                        options = alt_data.get('options', [])
                        # Skip the first one (it's the primary recommendation)
                        for opt in options[1:4]:  # Get up to 3 alternatives
                            route = opt.get('route', {})
                            alternatives.append({
                                'route_name': route.get('name', 'Unknown'),
                                'route_id': route.get('id'),
                                'distance': route.get('distance', 0) / 1000,
                                'duration': route.get('duration', 0) / 60,
                                'elevation': route.get('elevation', 0),
                                'score': opt.get('score', 0),
                                'breakdown': opt.get('breakdown', {})
                            })
            
            # Get departure windows
            windows_data = commute_service.get_departure_windows()
            if windows_data.get('status') == 'success':
                for window in windows_data.get('windows', []):
                    departure_windows.append({
                        'direction': window.get('direction'),
                        'direction_display': window.get('direction', '').replace('_', ' ').title(),
                        'start_time': window.get('start_time'),
                        'end_time': window.get('end_time'),
                        'optimal_time': window.get('optimal_time'),
                        'score': window.get('score', 0)
                    })
                    
    except Exception as e:
        current_app.logger.error(f"Error getting commute recommendations: {e}")
        current_app.logger.debug(traceback.format_exc())
    
    context = {
        'page_title': 'Next Commute',
        'current_time': datetime.now(),
        'recommendation': recommendation,
        'alternatives': alternatives,
        'departure_windows': departure_windows,
        'route_weather': route_weather,
        'workout_fit': None  # TODO: TrainerRoad integration (Issue #139)
    }
    
    return render_template('commute/index.html', **context)


@bp.route('/analyze', methods=['POST'])
def analyze():
    """
    Trigger fresh commute analysis.
    
    POST body (JSON):
    {
        "departure_time": "2026-05-07T07:30:00",  # Optional, defaults to next typical commute time
        "direction": "to_work",  # or "from_work"
        "force_refresh": false  # Force re-analysis even if recent data exists
    }
    
    Returns:
    {
        "status": "success",
        "recommendation": {...},
        "analysis_timestamp": "2026-05-07T06:00:00"
    }
    """
    data = request.get_json() or {}
    
    departure_time = data.get('departure_time')
    direction = data.get('direction', 'to_work')
    force_refresh = data.get('force_refresh', False)
    
    current_app.logger.info(f'Commute analysis requested: direction={direction}, force_refresh={force_refresh}')
    
    # TODO: Implement with service layer (Issue #130)
    # - Call next_commute_recommender.get_recommendation()
    # - Include weather, traffic, workout fit analysis
    # - Cache results with appropriate TTL
    
    return jsonify({
        'status': 'success',
        'message': 'Analysis complete',
        'recommendation': None,  # TODO: Return actual recommendation
        'analysis_timestamp': datetime.now().isoformat()
    })


@bp.route('/history')
def history():
    """
    Historical commute performance and trends.
    
    Shows:
    - Route performance over time
    - Weather impact analysis
    - Seasonal patterns
    - Best/worst commute days
    """
    current_app.logger.info('Commute history accessed')
    
    # TODO: Replace with actual service layer calls (Issue #130)
    context = {
        'page_title': 'Commute History',
        'recent_commutes': [],  # TODO: Get from database
        'performance_trends': {},  # TODO: Calculate trends
        'weather_correlations': {}  # TODO: Analyze weather impact
    }
    
    return render_template('commute/history.html', **context)


@bp.route('/api/current')
def api_current():
    """
    API endpoint for current commute recommendation.
    
    Returns JSON with current best commute option.
    Used by dashboard and mobile apps.
    """
    # TODO: Implement with service layer (Issue #130)
    return jsonify({
        'recommendation': None,
        'confidence': 0.0,
        'last_updated': datetime.now().isoformat(),
        'factors': {
            'weather': 'unknown',
            'traffic': 'unknown',
            'workout_fit': 'unknown'
        }
    })

# Made with Bob
