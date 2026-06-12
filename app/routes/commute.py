"""Commute blueprint: recommendation views and API endpoints."""

from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, render_template, request

from src.config import Config
from app.services.analysis_service import AnalysisService
from app.services.commute_service import CommuteService
from app.services.weather_service import WeatherService

bp = Blueprint('commute', __name__, url_prefix='/commute')


def get_services():
    if hasattr(g, 'commute_services'):
        return g.commute_services
    config = Config('config/config.yaml')
    g.commute_services = {
        'analysis': AnalysisService(config),
        'commute': CommuteService(config),
        'weather': WeatherService(config),
    }
    return g.commute_services


def _build_recommendation(result):
    if not (isinstance(result, dict) and result.get('status') == 'success'):
        return None
    route = result.get('route') or {}
    return {
        'route_name': route.get('name'),
        'route_id': route.get('id'),
        'distance_km': round((route.get('distance') or 0) / 1000, 1),
        'duration_min': round((route.get('duration') or 0) / 60),
        'elevation': route.get('elevation'),
        'score': result.get('score'),
        'direction': result.get('direction'),
        'departure_time': result.get('departure_time'),
        'confidence': result.get('confidence'),
    }


@bp.route('/')
def index():
    services = get_services()
    direction = request.args.get('direction')
    recommendation = None
    alternatives = []
    windows = []

    try:
        route_groups = services['analysis'].get_route_groups()
        home, work = services['analysis'].get_locations()
        if route_groups and home and work:
            services['commute'].initialize(route_groups, home, work)

        if direction:
            result = services['commute'].get_next_commute(direction=direction)
        else:
            result = services['commute'].get_workout_aware_commute()
            if not (isinstance(result, dict) and result.get('status') == 'success'):
                result = services['commute'].get_next_commute()

        recommendation = _build_recommendation(result)

        alt_result = services['commute'].get_all_commute_options()
        if isinstance(alt_result, dict) and alt_result.get('status') == 'success':
            alternatives = alt_result.get('options', [])

        win_result = services['commute'].get_departure_windows()
        if isinstance(win_result, dict) and win_result.get('status') == 'success':
            windows = win_result.get('windows', [])

    except Exception:
        pass

    return render_template(
        'commute/index.html',
        recommendation=recommendation,
        alternatives=alternatives,
        departure_windows=windows,
        direction=direction,
        page_title='Commute Planner',
    )


@bp.route('/analyze', methods=['POST'])
def analyze():
    data = request.json or {}
    services = get_services()
    direction = data.get('direction')
    departure_time = data.get('departure_time')

    result = services['commute'].get_workout_aware_commute(
        direction=direction,
        departure_time=departure_time,
    )

    recommendation = _build_recommendation(result) if isinstance(result, dict) else None

    return jsonify({
        'status': result.get('status', 'error') if isinstance(result, dict) else 'error',
        'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
        'recommendation': recommendation,
    })


@bp.route('/history')
def history():
    services = get_services()
    return render_template(
        'commute/history.html',
        page_title='Commute History',
    )


@bp.route('/api/current')
def api_current():
    services = get_services()
    return jsonify({
        'recommendation': None,
        'confidence': 0,
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'factors': {
            'weather': None,
            'traffic': None,
            'workout_fit': None,
        },
    })
