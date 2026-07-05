"""Strava auth/setup API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  GET  /api/strava/status
  GET  /api/strava/connect
  GET  /api/strava/callback
  POST /api/strava/disconnect
  GET  /api/setup/status
  POST /api/setup/credentials
  POST /api/setup/verify
"""

from flask import Blueprint

bp = Blueprint('strava', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
