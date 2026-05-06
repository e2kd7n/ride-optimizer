"""
Planner blueprint - Long ride planning and recommendations.

Provides intelligent long ride recommendations based on:
- Weather forecasts (7-day window)
- Workout fit and training load
- Route variety and exploration
- Seasonal patterns
- Historical performance
"""

from flask import Blueprint, render_template, request, jsonify, current_app, g
from datetime import datetime, timedelta
import traceback

from app.services import AnalysisService, PlannerService
from src.config import Config

bp = Blueprint('planner', __name__, url_prefix='/planner')


def get_services():
    """Get or create service instances for this request."""
    if 'services' not in g:
        config = Config('config/config.yaml')
        g.services = {
            'analysis': AnalysisService(config),
            'planner': PlannerService(config)
        }
    return g.services


@bp.route('/')
def index():
    """
    Main long ride planner view.
    
    Shows:
    - Best long ride options for next 7 days
    - Weather forecast comparison
    - Workout fit recommendations
    - Route suggestions with variety scoring
    """
    current_app.logger.info('Long ride planner accessed')
    
    services = get_services()
    analysis_service = services['analysis']
    planner_service = services['planner']
    
    # Get filter parameters
    forecast_days = int(request.args.get('days', 7))
    min_distance = float(request.args.get('min_distance', 30))
    max_distance = float(request.args.get('max_distance', 100))
    
    recommendations = []
    best_day = None
    total_rides = 0
    
    try:
        long_rides = analysis_service.get_long_rides()
        
        if long_rides:
            planner_service.initialize(long_rides)
            
            # Get recommendations
            rec_data = planner_service.get_recommendations(
                forecast_days=forecast_days,
                min_distance=min_distance,
                max_distance=max_distance
            )
            
            if rec_data.get('status') == 'success':
                best_day = rec_data.get('best_day')
                total_rides = rec_data.get('total_rides', 0)
                
                for day_rec in rec_data.get('recommendations', []):
                    rides = []
                    for ride in day_rec.get('rides', [])[:5]:  # Top 5 per day
                        rides.append({
                            'ride_id': ride.get('ride_id'),
                            'name': ride.get('name', 'Unknown Ride'),
                            'distance': ride.get('distance', 0) / 1000,  # km
                            'duration': ride.get('duration', 0) / 60,  # minutes
                            'elevation': ride.get('elevation', 0),  # meters
                            'score': ride.get('score', 0),
                            'weather_score': ride.get('weather_score', 0),
                            'variety_score': ride.get('variety_score', 0),
                            'is_loop': ride.get('is_loop', False),
                            'weather': ride.get('weather', {})
                        })
                    
                    best_ride = day_rec.get('best_ride', {})
                    recommendations.append({
                        'date': day_rec.get('date'),
                        'day_name': day_rec.get('day_name'),
                        'rides': rides,
                        'best_ride': {
                            'name': best_ride.get('name', 'Unknown'),
                            'distance': best_ride.get('distance', 0) / 1000,
                            'duration': best_ride.get('duration', 0) / 60,
                            'elevation': best_ride.get('elevation', 0),
                            'score': best_ride.get('score', 0),
                            'weather': best_ride.get('weather', {})
                        } if best_ride else None,
                        'weather_summary': day_rec.get('weather_summary', '')
                    })
                    
    except Exception as e:
        current_app.logger.error(f"Error getting planner recommendations: {e}")
        current_app.logger.debug(traceback.format_exc())
    
    context = {
        'page_title': 'Long Ride Planner',
        'current_time': datetime.now(),
        'forecast_days': forecast_days,
        'min_distance': min_distance,
        'max_distance': max_distance,
        'recommendations': recommendations,
        'best_day': best_day,
        'total_rides': total_rides,
        'workout_schedule': None  # TODO: TrainerRoad integration (Issue #139)
    }
    
    return render_template('planner/index.html', **context)


@bp.route('/analyze', methods=['POST'])
def analyze():
    """
    Trigger fresh long ride analysis.
    
    POST body (JSON):
    {
        "forecast_days": 7,  # Number of days to analyze (1-14)
        "min_distance": 30,  # Minimum ride distance in miles
        "max_distance": 100,  # Maximum ride distance in miles
        "force_refresh": false  # Force re-analysis
    }
    
    Returns:
    {
        "status": "success",
        "recommendations": [...],
        "analysis_timestamp": "2026-05-07T06:00:00"
    }
    """
    data = request.get_json() or {}
    
    forecast_days = data.get('forecast_days', 7)
    min_distance = data.get('min_distance', 30)
    max_distance = data.get('max_distance', 100)
    force_refresh = data.get('force_refresh', False)
    
    current_app.logger.info(
        f'Long ride analysis requested: days={forecast_days}, '
        f'distance={min_distance}-{max_distance}mi, force_refresh={force_refresh}'
    )
    
    # TODO: Implement with service layer (Issue #130)
    # - Call long_ride_analyzer.get_recommendations()
    # - Include weather, workout fit, route variety analysis
    # - Cache results with appropriate TTL
    
    return jsonify({
        'status': 'success',
        'message': 'Analysis complete',
        'recommendations': [],  # TODO: Return actual recommendations
        'analysis_timestamp': datetime.now().isoformat()
    })


@bp.route('/route/<int:route_id>')
def route_detail(route_id):
    """
    Detailed view of a specific route for planning.
    
    Shows:
    - Route map and elevation profile
    - Historical performance data
    - Weather forecast for route area
    - Optimal departure times
    - Similar route alternatives
    """
    current_app.logger.info(f'Route detail accessed: route_id={route_id}')
    
    # TODO: Replace with actual service layer calls (Issue #130)
    context = {
        'page_title': f'Route #{route_id}',
        'route': None,  # TODO: Get from database
        'weather_forecast': None,  # TODO: Get localized weather
        'historical_performance': [],  # TODO: Get past activities on this route
        'similar_routes': []  # TODO: Find similar alternatives
    }
    
    return render_template('planner/route_detail.html', **context)


@bp.route('/api/recommendations')
def api_recommendations():
    """
    API endpoint for long ride recommendations.
    
    Query params:
    - days: Number of forecast days (default: 7)
    - min_distance: Minimum distance in miles (default: 30)
    - max_distance: Maximum distance in miles (default: 100)
    
    Returns JSON with ranked recommendations.
    """
    days = request.args.get('days', 7, type=int)
    min_distance = request.args.get('min_distance', 30, type=float)
    max_distance = request.args.get('max_distance', 100, type=float)
    
    # TODO: Implement with service layer (Issue #130)
    return jsonify({
        'recommendations': [],
        'forecast_days': days,
        'distance_range': {
            'min': min_distance,
            'max': max_distance
        },
        'last_updated': datetime.now().isoformat()
    })


@bp.route('/calendar')
def calendar():
    """
    Calendar view of planned and completed rides.
    
    Shows:
    - Monthly calendar with rides
    - Workout schedule integration
    - Weather patterns
    - Training load visualization
    """
    current_app.logger.info('Ride calendar accessed')
    
    # Get month from query params or use current month
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # TODO: Replace with actual service layer calls (Issue #130)
    context = {
        'page_title': 'Ride Calendar',
        'year': year,
        'month': month,
        'rides': [],  # TODO: Get rides for month
        'workouts': [],  # TODO: Get TrainerRoad workouts
        'weather_patterns': {}  # TODO: Get historical weather
    }
    
    return render_template('planner/calendar.html', **context)

# Made with Bob
