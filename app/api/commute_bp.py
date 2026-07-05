"""Commute API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  GET /api/recommendation
  GET /api/commute
  GET /api/commute/map
  GET /api/workout-options
"""

from flask import Blueprint

bp = Blueprint('commute', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
