"""
Dashboard blueprint - Main landing page with overview and recommendations.

Provides the primary entry point for users with today's commute recommendations,
workout fit status, and quick access to other features.
"""

from flask import Blueprint, render_template, current_app
from datetime import datetime

bp = Blueprint('dashboard', __name__)


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
    
    # TODO: Replace with actual service layer calls (Issue #130)
    context = {
        'page_title': 'Dashboard',
        'current_time': datetime.now(),
        'user_name': 'Cyclist',  # TODO: Get from session/config
        'status': {
            'last_analysis': None,  # TODO: Get from database
            'data_freshness': 'unknown',
            'geocoding_status': 'complete'
        },
        'quick_stats': {
            'total_routes': 0,  # TODO: Get from service layer
            'total_activities': 0,
            'favorite_route': None
        },
        'recommendations': {
            'commute': None,  # TODO: Get from commute service
            'workout_fit': None,  # TODO: Get from TrainerRoad integration
            'long_ride': None  # TODO: Get from planner service
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
