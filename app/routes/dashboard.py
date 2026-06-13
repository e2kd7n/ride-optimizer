"""Dashboard blueprint: main landing page and data summary."""

from flask import Blueprint, g, render_template

from src.config import Config
from app.services.analysis_service import AnalysisService
from app.services.commute_service import CommuteService
from app.services.planner_service import PlannerService
from app.services.weather_service import WeatherService

bp = Blueprint('dashboard', __name__)


def get_services():
    if hasattr(g, 'services'):
        return g.services
    config = Config('config/config.yaml')
    analysis = AnalysisService(config)
    commute = CommuteService(config)
    planner = PlannerService(config)
    weather = WeatherService(config)
    g.services = {
        'analysis': analysis,
        'commute': commute,
        'planner': planner,
        'weather': weather,
    }
    return g.services


def _build_dashboard_context(services):
    ctx = {
        'analysis_status': None,
        'locations': None,
        'weather': None,
        'recommendation': None,
        'error': None,
    }

    try:
        ctx['analysis_status'] = services['analysis'].get_analysis_status()
    except Exception:
        pass

    try:
        home, work = services['analysis'].get_locations()
        ctx['locations'] = {'home': home, 'work': work}
    except Exception:
        home, work = None, None

    try:
        if home:
            ctx['weather'] = services['weather'].get_weather_summary(home['lat'], home['lon'])
    except Exception:
        pass

    try:
        route_groups = services['analysis'].get_route_groups()
        if route_groups and home and work:
            services['commute'].initialize(route_groups, home, work)
            result = services['commute'].get_workout_aware_commute()
            if isinstance(result, dict) and result.get('status') == 'success':
                route = result.get('route', {})
                ctx['recommendation'] = {
                    'direction': result.get('direction'),
                    'route_name': route.get('name') if route else None,
                    'score': result.get('score'),
                }
    except Exception:
        pass

    return ctx


@bp.route('/')
@bp.route('/dashboard')
def dashboard():
    services = get_services()
    ctx = _build_dashboard_context(services)
    return render_template('dashboard.html', **ctx)
