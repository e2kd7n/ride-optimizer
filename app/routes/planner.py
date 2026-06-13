"""Planner blueprint: long ride recommendations and calendar view."""

from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, render_template, request

from src.config import Config
from app.services.analysis_service import AnalysisService
from app.services.planner_service import PlannerService
from app.services.weather_service import WeatherService

bp = Blueprint('planner', __name__, url_prefix='/planner')


def get_services():
    if hasattr(g, 'planner_services'):
        return g.planner_services
    config = Config('config/config.yaml')
    g.planner_services = {
        'analysis': AnalysisService(config),
        'planner': PlannerService(config),
        'weather': WeatherService(config),
    }
    return g.planner_services


@bp.route('/')
def index():
    services = get_services()
    days = int(request.args.get('days', 7))
    min_distance = float(request.args.get('min_distance')) if request.args.get('min_distance') else None
    max_distance = float(request.args.get('max_distance')) if request.args.get('max_distance') else None

    long_rides = []
    recommendations = None
    error = None

    try:
        long_rides = services['analysis'].get_long_rides()
        if long_rides:
            services['planner'].initialize(long_rides)
            recommendations = services['planner'].get_recommendations(
                forecast_days=days,
                min_distance=min_distance,
                max_distance=max_distance,
            )
    except Exception:
        pass

    return render_template(
        'planner/index.html',
        long_rides=long_rides,
        recommendations=recommendations,
        forecast_days=days,
        page_title='Long Ride Planner',
    )


@bp.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True) or {}
    days = int(data.get('days', 7))
    min_distance = float(data.get('min_distance')) if data.get('min_distance') is not None else None
    max_distance = float(data.get('max_distance')) if data.get('max_distance') is not None else None

    services = get_services()
    long_rides = services['analysis'].get_long_rides()
    result = {'status': 'success', 'recommendations': []}
    if long_rides:
        services['planner'].initialize(long_rides)
        result = services['planner'].get_recommendations(
            forecast_days=days,
            min_distance=min_distance,
            max_distance=max_distance,
        )

    return jsonify(result)


@bp.route('/route/<route_id>')
def route_detail(route_id):
    services = get_services()
    long_rides = []
    ride = None

    try:
        long_rides = services['analysis'].get_long_rides()
        for r in long_rides:
            if str(getattr(r, 'activity_id', None)) == str(route_id):
                ride = r
                break
    except Exception:
        pass

    return render_template(
        'planner/route.html',
        ride=ride,
        route_id=route_id,
        page_title=f'Route #{route_id}',
    )


@bp.route('/api/recommendations')
def api_recommendations():
    return jsonify({
        'recommendations': [],
        'forecast_days': int(request.args.get('days', 7)),
        'distance_range': {
            'min': request.args.get('min_distance'),
            'max': request.args.get('max_distance'),
        },
        'last_updated': datetime.now(timezone.utc).isoformat(),
    })


@bp.route('/calendar')
def calendar():
    services = get_services()
    long_rides = []

    try:
        long_rides = services['analysis'].get_long_rides()
    except Exception:
        pass

    return render_template(
        'planner/calendar.html',
        long_rides=long_rides,
        page_title='Ride Calendar',
    )
