"""Routes library API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  GET /api/routes
  GET /api/routes/status
  GET /api/routes/search
  GET /api/routes/<route_id>
"""

from flask import Blueprint

bp = Blueprint('routes', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
