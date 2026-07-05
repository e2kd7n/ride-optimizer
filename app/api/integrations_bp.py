"""Third-party integrations API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  GET  /api/intervals/status
  POST /api/intervals/connect
  POST /api/intervals/disconnect
  GET  /api/ors/status
  POST /api/ors/connect
  POST /api/ors/disconnect
  GET  /api/garmin/status
  POST /api/garmin/connect
  POST /api/garmin/disconnect
  POST /api/garmin/sync
  GET  /api/trainerroad/status
  POST /api/trainerroad/connect
  POST /api/trainerroad/sync
  POST /api/trainerroad/disconnect
  GET  /api/trainerroad/workouts
  GET  /api/trainerroad/today
"""

from flask import Blueprint

bp = Blueprint('integrations', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
