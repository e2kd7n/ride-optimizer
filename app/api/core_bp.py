"""Core / system API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  GET    /api/csrf-token
  GET    /api/status
  GET    /api/settings
  PUT    /api/settings
  DELETE /api/settings
  DELETE /api/user/data
  GET    /api/plans
  POST   /api/plans
  DELETE /api/plans/<plan_id>
"""

from flask import Blueprint

bp = Blueprint('core', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
