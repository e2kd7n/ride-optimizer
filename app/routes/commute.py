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
    
    # Get direction from query param or auto-detect
    direction = request.args.get('direction')
    
    # Initialize commute service
    recommendation = None
    alternatives = []
    departure_windows = []
    
    try:
        route_groups = analysis_service.get_route_groups()
        home, work = analysis_service.get_locations()
        
        if route_groups and home and work:
            commute_service.initialize(route_groups, home, work)
            
            # Get primary recommendation (workout-aware)
            rec_data = commute_service.get_workout_aware_commute(direction=direction)
            
            if rec_data.get('status') == 'success':
                route = rec_data.get('route', {})
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
                    'weather': rec_data.get('weather', {}),
                    'departure_time': rec_data.get('departure_time'),
                    'confidence': rec_data.get('confidence', 'medium'),
                    'workout_fit': rec_data.get('workout_fit')  # TrainerRoad integration
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
        'workout_fit': recommendation.get('workout_fit') if recommendation else None
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
    
    try:
        services = get_services()
        analysis_service = services['analysis']
        commute_service = services['commute']
        
        # Initialize services
        route_groups = analysis_service.get_route_groups()
        home, work = analysis_service.get_locations()
        
        if not route_groups or not home or not work:
            return jsonify({
                'status': 'error',
                'message': 'Route data not available. Please run analysis first.',
                'analysis_timestamp': datetime.now().isoformat()
            }), 400
        
        commute_service.initialize(route_groups, home, work)
        
        # Get workout-aware recommendation
        rec_data = commute_service.get_workout_aware_commute(
            direction=direction,
            departure_time=departure_time
        )
        
        if rec_data.get('status') == 'success':
            return jsonify({
                'status': 'success',
                'message': 'Analysis complete',
                'recommendation': rec_data,
                'analysis_timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': rec_data.get('message', 'No recommendation available'),
                'analysis_timestamp': datetime.now().isoformat()
            }), 404
    
    except Exception as e:
        current_app.logger.error(f"Error analyzing commute: {e}")
        current_app.logger.debug(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e),
            'analysis_timestamp': datetime.now().isoformat()
        }), 500


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
    
    try:
        services = get_services()
        analysis_service = services['analysis']
        
        # Get route groups for commute routes
        route_groups = analysis_service.get_route_groups()
        
        # Filter for commute routes (typically shorter distances)
        commute_routes = []
        if route_groups:
            for group in route_groups:
                # Commute routes are typically 5-25 miles
                distance_miles = group.avg_distance / 1609.34
                if 5 <= distance_miles <= 25:
                    commute_routes.append({
                        'group_id': group.group_id,
                        'name': group.name,
                        'distance': distance_miles,
                        'elevation': group.avg_elevation,
                        'uses': group.uses,
                        'last_used': group.last_used.isoformat() if group.last_used else None,
                        'avg_speed': group.avg_speed if hasattr(group, 'avg_speed') else None
                    })
        
        # Sort by most recently used
        commute_routes.sort(key=lambda r: r['last_used'] or '', reverse=True)
        
        # Calculate basic trends
        total_commutes = sum(r['uses'] for r in commute_routes)
        avg_distance = sum(r['distance'] * r['uses'] for r in commute_routes) / total_commutes if total_commutes > 0 else 0
        
        context = {
            'page_title': 'Commute History',
            'recent_commutes': commute_routes[:20],  # Top 20 most recent
            'performance_trends': {
                'total_commutes': total_commutes,
                'avg_distance': round(avg_distance, 1),
                'unique_routes': len(commute_routes)
            },
            'weather_correlations': {
                'note': 'Weather correlation analysis requires historical weather data'
            }
        }
        
        return render_template('commute/history.html', **context)
    
    except Exception as e:
        current_app.logger.error(f"Error loading commute history: {e}")
        current_app.logger.debug(traceback.format_exc())
        context = {
            'page_title': 'Commute History',
            'recent_commutes': [],
            'performance_trends': {},
            'weather_correlations': {},
            'error': str(e)
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
