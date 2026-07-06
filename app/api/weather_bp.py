"""Weather API Blueprint — stub (Phase 1).

Routes (to be extracted from launch.py in Phase 4):
  GET /api/weather
  GET /api/weather/commute-windows
  GET /api/weather/hourly
  GET /api/weather/forecast
"""

from flask import Blueprint

bp = Blueprint('weather', __name__, url_prefix='/api')

# Phase 4: route handlers will be moved here from launch.py
