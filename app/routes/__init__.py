"""
Route blueprints for the Ride Optimizer web platform.

This package contains all Flask blueprints organized by feature area.
"""

# Import blueprints for easy access
from app.routes.dashboard import bp as dashboard_bp
from app.routes.commute import bp as commute_bp
from app.routes.planner import bp as planner_bp
from app.routes.route_library import bp as route_library_bp
from app.routes.settings import bp as settings_bp
from app.routes.api import bp as api_bp

__all__ = [
    'dashboard_bp',
    'commute_bp',
    'planner_bp',
    'route_library_bp',
    'settings_bp',
    'api_bp'
]

# Made with Bob
