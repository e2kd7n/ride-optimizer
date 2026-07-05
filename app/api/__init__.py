"""API package — Blueprint stubs and the existing maps_api Blueprint.

Stub blueprints (Phase 1) are importable but contain no route handlers yet.
Route handlers will be extracted from launch.py into each blueprint in Phase 4.
"""

from app.api import maps_api

__all__ = [
    'maps_api',
    # Phase 4 additions (uncomment as each blueprint is filled):
    # 'weather_bp',
    # 'commute_bp',
    # 'routes_bp',
    # 'planner_bp',
    # 'strava_bp',
    # 'integrations_bp',
    # 'data_bp',
    # 'stats_bp',
    # 'core_bp',
]
