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
from app.services.trainerroad_service import TrainerRoadService
from src.config import Config

bp = Blueprint('planner', __name__, url_prefix='/planner')


def get_services():
    """Get or create service instances for this request."""
    if 'services' not in g:
        config = Config('config/config.yaml')
        g.services = {
            'analysis': AnalysisService(config),
            'planner': PlannerService(config),
            'trainerroad': TrainerRoadService(config)
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
    trainerroad_service = services['trainerroad']
    
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
    
    # Get workout schedule from TrainerRoad
    workout_schedule = None
    try:
        workouts = trainerroad_service.get_upcoming_workouts(days=forecast_days)
        if workouts:
            workout_schedule = [
                {
                    'date': w.date.isoformat(),
                    'name': w.name,
                    'duration': w.duration_minutes,
                    'tss': w.tss,
                    'type': w.workout_type
                }
                for w in workouts
            ]
    except Exception as e:
        current_app.logger.error(f"Error getting workout schedule: {e}")
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
        'workout_schedule': workout_schedule  # TrainerRoad integration
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
    
    try:
        services = get_services()
        analysis_service = services['analysis']
        planner_service = services['planner']
        
        # Get long rides
        long_rides = analysis_service.get_long_rides()
        
        if not long_rides:
            return jsonify({
                'status': 'error',
                'message': 'No long ride data available. Please run analysis first.',
                'analysis_timestamp': datetime.now().isoformat()
            }), 400
        
        # Initialize planner
        planner_service.initialize(long_rides)
        
        # Get recommendations
        rec_data = planner_service.get_recommendations(
            forecast_days=forecast_days,
            min_distance=min_distance,
            max_distance=max_distance
        )
        
        if rec_data.get('status') == 'success':
            return jsonify({
                'status': 'success',
                'message': 'Analysis complete',
                'recommendations': rec_data.get('recommendations', []),
                'best_day': rec_data.get('best_day'),
                'total_rides': rec_data.get('total_rides', 0),
                'analysis_timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': rec_data.get('message', 'Analysis failed'),
                'analysis_timestamp': datetime.now().isoformat()
            }), 500
    
    except Exception as e:
        current_app.logger.error(f"Error analyzing long rides: {e}")
        current_app.logger.debug(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e),
            'analysis_timestamp': datetime.now().isoformat()
        }), 500


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
    
    try:
        services = get_services()
        analysis_service = services['analysis']
        planner_service = services['planner']
        
        # Get long rides
        long_rides = analysis_service.get_long_rides()
        
        # Find the specific route
        route = None
        for ride in long_rides:
            if ride.activity_id == route_id:
                route = {
                    'id': ride.activity_id,
                    'name': ride.name,
                    'distance': ride.distance_km,
                    'duration': ride.duration_hours,
                    'elevation': ride.elevation_gain,
                    'start_location': ride.start_location,
                    'is_loop': ride.is_loop,
                    'uses': ride.uses,
                    'type': ride.type,
                    'last_used': ride.last_used.isoformat() if ride.last_used else None
                }
                break
        
        if not route:
            context = {
                'page_title': f'Route #{route_id}',
                'route': None,
                'error': f'Route {route_id} not found'
            }
            return render_template('planner/route_detail.html', **context), 404
        
        # Get weather forecast for route location
        weather_forecast = None
        try:
            from app.services.weather_service import WeatherService
            weather_service = WeatherService(services['analysis'].config)
            snapshot = weather_service.get_weather_snapshot(
                lat=route['start_location'][0],
                lon=route['start_location'][1],
                target_date=datetime.now().date()
            )
            if snapshot:
                weather_forecast = {
                    'temperature': snapshot.temperature_f,
                    'conditions': snapshot.conditions,
                    'wind_speed': snapshot.wind_speed_mph,
                    'precipitation': snapshot.precipitation_in
                }
        except Exception as e:
            current_app.logger.error(f"Error fetching weather: {e}")
        
        # Find similar routes (same type, similar distance)
        similar_routes = []
        target_distance = route['distance']
        for ride in long_rides[:20]:  # Limit to 20
            if ride.activity_id != route_id:
                distance_diff = abs(ride.distance_km - target_distance)
                if distance_diff < 10:  # Within 10km
                    similar_routes.append({
                        'id': ride.activity_id,
                        'name': ride.name,
                        'distance': ride.distance_km,
                        'elevation': ride.elevation_gain,
                        'similarity_score': 1.0 - (distance_diff / 10)
                    })
        
        similar_routes.sort(key=lambda r: r['similarity_score'], reverse=True)
        
        context = {
            'page_title': route['name'] or f'Route #{route_id}',
            'route': route,
            'weather_forecast': weather_forecast,
            'historical_performance': [],  # Would need activity history from database
            'similar_routes': similar_routes[:5]  # Top 5 similar
        }
        
        return render_template('planner/route_detail.html', **context)
    
    except Exception as e:
        current_app.logger.error(f"Error loading route detail: {e}")
        current_app.logger.debug(traceback.format_exc())
        context = {
            'page_title': f'Route #{route_id}',
            'route': None,
            'error': str(e)
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
    
    try:
        services = get_services()
        analysis_service = services['analysis']
        trainerroad_service = services['trainerroad']
        
        # Get rides for the month
        from datetime import date
        import calendar as cal
        
        month_start = date(year, month, 1)
        _, last_day = cal.monthrange(year, month)
        month_end = date(year, month, last_day)
        
        # Get all long rides
        long_rides = analysis_service.get_long_rides()
        
        # Filter rides by last_used date in the month
        rides_in_month = []
        if long_rides:
            for ride in long_rides:
                if ride.last_used and month_start <= ride.last_used.date() <= month_end:
                    rides_in_month.append({
                        'id': ride.activity_id,
                        'name': ride.name,
                        'date': ride.last_used.date().isoformat(),
                        'distance': ride.distance_km,
                        'duration': ride.duration_hours,
                        'elevation': ride.elevation_gain
                    })
        
        # Get TrainerRoad workouts for the month
        workouts_in_month = []
        try:
            # Get workouts for next 30 days from month start
            days_to_fetch = (month_end - month_start).days + 1
            workouts = trainerroad_service.get_upcoming_workouts(days=days_to_fetch)
            
            if workouts:
                for workout in workouts:
                    if month_start <= workout.date <= month_end:
                        workouts_in_month.append({
                            'date': workout.date.isoformat(),
                            'name': workout.name,
                            'duration': workout.duration_minutes,
                            'tss': workout.tss,
                            'type': workout.workout_type
                        })
        except Exception as e:
            current_app.logger.error(f"Error fetching workouts: {e}")
        
        context = {
            'page_title': 'Ride Calendar',
            'year': year,
            'month': month,
            'month_name': cal.month_name[month],
            'rides': rides_in_month,
            'workouts': workouts_in_month,
            'weather_patterns': {
                'note': 'Historical weather patterns require weather database'
            }
        }
        
        return render_template('planner/calendar.html', **context)
    
    except Exception as e:
        current_app.logger.error(f"Error loading calendar: {e}")
        current_app.logger.debug(traceback.format_exc())
        context = {
            'page_title': 'Ride Calendar',
            'year': year,
            'month': month,
            'rides': [],
            'workouts': [],
            'weather_patterns': {},
            'error': str(e)
        }
        return render_template('planner/calendar.html', **context)

# Made with Bob
