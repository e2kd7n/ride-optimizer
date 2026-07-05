"""Planner API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  GET  /api/planner/recommendations
  GET  /api/planner/rides/nearby
  GET  /api/planner/rides/<ride_id>
  POST /api/planner/analyze
  GET  /api/exploration/tiles
  GET  /api/exploration/roads
  POST /api/exploration/invalidate
  POST /api/exploration/route
  GET  /api/geocode
"""

from flask import Blueprint

bp = Blueprint('planner', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
