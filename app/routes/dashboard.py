"""
Dashboard blueprint - Main landing page with overview and recommendations.

Provides the primary entry point for users with today's commute recommendations,
workout fit status, and quick access to other features.
"""

from flask import Blueprint, render_template, current_app, g
from datetime import datetime, timedelta
import traceback

from app.services import AnalysisService, CommuteService, PlannerService
from app.services.weather_service import WeatherService
from src.config import Config

bp = Blueprint('dashboard', __name__)


def get_services():
    """Get or create service instances for this request."""
    if 'services' not in g:
        config = Config('config/config.yaml')
        g.services = {
            'analysis': AnalysisService(config),
            'commute': CommuteService(config),
            'planner': PlannerService(config),
            'weather': WeatherService()
        }
    return g.services


@bp.route('/')
@bp.route('/dashboard')
def index():
    """
    Main dashboard view.
    
    Shows:
    - Today's best commute recommendation
    - Workout fit summary (if TrainerRoad data available)
    - Departure timing guidance
    - Best long ride option today
    - Freshness/status summary
    - Quick stats
    """
    current_app.logger.info('Dashboard accessed')
    
    services = get_services()
    analysis_service = services['analysis']
    commute_service = services['commute']
    planner_service = services['planner']
    weather_service = services['weather']
    
    # Get analysis status
    try:
        status_data = analysis_service.get_analysis_status()
        current_app.logger.info(f"Analysis status: {status_data.get('status')}")
    except Exception as e:
        current_app.logger.error(f"Error getting analysis status: {e}")
        status_data = {
            'status': 'error',
            'last_analysis': None,
            'data_freshness': 'unknown',
            'activities_count': 0,
            'route_groups_count': 0,
            'long_rides_count': 0
        }
    
    # Get current weather for home location
    current_weather = None
    try:
        home, work = analysis_service.get_locations()
        if home:
            current_weather = weather_service.get_weather_summary(
                home['lat'],
                home['lon'],
                location_name='Home'
            )
            current_app.logger.info(f"Weather: {current_weather.get('favorability', 'unknown')}")
    except Exception as e:
        current_app.logger.error(f"Error getting weather: {e}")
        current_app.logger.debug(traceback.format_exc())
    
    # Get commute recommendation
    commute_recommendation = None
    try:
        # Initialize commute service if we have route groups
        route_groups = analysis_service.get_route_groups()
        home, work = analysis_service.get_locations()
        
        if route_groups and home and work:
            commute_service.initialize(route_groups, home, work)
            commute_data = commute_service.get_workout_aware_commute()
            
            if commute_data.get('status') == 'success':
                route = commute_data.get('route', {})
                commute_recommendation = {
                    'direction': commute_data.get('direction'),
                    'route_name': route.get('name', 'Unknown Route'),
                    'distance': route.get('distance', 0) / 1000,  # Convert to km
                    'duration': route.get('duration', 0) / 60,  # Convert to minutes
                    'score': commute_data.get('score', 0),
                    'departure_time': commute_data.get('departure_time'),
                    'weather': commute_data.get('weather', {}),
                    'workout_fit': commute_data.get('workout_fit')  # TrainerRoad integration
                }
    except Exception as e:
        current_app.logger.error(f"Error getting commute recommendation: {e}")
        current_app.logger.debug(traceback.format_exc())
    
    # Get long ride recommendation
    long_ride_recommendation = None
    try:
        long_rides = analysis_service.get_long_rides()
        if long_rides:
            planner_service.initialize(long_rides)
            planner_data = planner_service.get_recommendations(forecast_days=7)
            
            if planner_data.get('status') == 'success':
                recommendations = planner_data.get('recommendations', [])
                if recommendations:
                    # Get today's or next best recommendation
                    best_rec = recommendations[0]
                    best_ride = best_rec.get('best_ride', {})
                    long_ride_recommendation = {
                        'day': best_rec.get('day_name'),
                        'ride_name': best_ride.get('name', 'Unknown Ride'),
                        'distance': best_ride.get('distance', 0) / 1000,  # Convert to km
                        'duration': best_ride.get('duration', 0) / 60,  # Convert to minutes
                        'score': best_ride.get('score', 0),
                        'weather': best_rec.get('weather', {})
                    }
    except Exception as e:
        current_app.logger.error(f"Error getting long ride recommendation: {e}")
        current_app.logger.debug(traceback.format_exc())
    
    # Determine data freshness
    data_freshness = 'unknown'
    if status_data.get('last_analysis'):
        try:
            last_analysis = datetime.fromisoformat(status_data['last_analysis'])
            hours_old = (datetime.now() - last_analysis).total_seconds() / 3600
            if hours_old < 24:
                data_freshness = 'fresh'
            elif hours_old < 72:
                data_freshness = 'stale'
            else:
                data_freshness = 'very_stale'
        except:
            pass
    
    context = {
        'page_title': 'Dashboard',
        'current_time': datetime.now(),
        'user_name': 'Cyclist',
        'status': {
            'last_analysis': status_data.get('last_analysis'),
            'data_freshness': data_freshness,
            'geocoding_status': 'complete' if status_data.get('geocoding_complete') else 'pending'
        },
        'quick_stats': {
            'total_routes': status_data.get('route_groups_count', 0),
            'total_activities': status_data.get('activities_count', 0),
            'total_long_rides': status_data.get('long_rides_count', 0)
        },
        'weather': current_weather,
        'recommendations': {
            'commute': commute_recommendation,
            'workout_fit': None,  # TODO: TrainerRoad integration (Issue #139)
            'long_ride': long_ride_recommendation
        }
    }
    
    return render_template('dashboard/index.html', **context)


@bp.route('/health')
def health():
    """
    Health check endpoint for monitoring.
    
    Returns JSON with system status.
    """
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '3.0.0-dev'
    }

# Made with Bob
