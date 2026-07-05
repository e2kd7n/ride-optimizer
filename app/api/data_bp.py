"""Activity data API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  POST /api/analyze
  GET  /api/analyze/status
  POST /api/analyze/stop
  POST /api/fetch
  GET  /api/fetch/status
  GET  /api/cache-info
  GET  /api/activities
"""

from flask import Blueprint

bp = Blueprint('data', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
