"""Statistics API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  GET  /api/stats
  GET  /api/stats/gear
  POST /api/stats/refresh-gear
  POST /api/stats/backfill-gear-ids
  GET  /api/stats/backfill-gear-ids/status
"""

from flask import Blueprint

bp = Blueprint('stats', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
