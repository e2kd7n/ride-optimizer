"""Route library blueprint: browse, search, favorite routes."""

import math
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, render_template, request

from src.config import Config
from app.services.analysis_service import AnalysisService
from app.services.route_library_service import RouteLibraryService

bp = Blueprint('route_library', __name__, url_prefix='/routes')

_PAGE_SIZE = 20


def get_services():
    if hasattr(g, 'route_library_services'):
        return g.route_library_services

    config = Config('config/config.yaml')
    analysis = AnalysisService(config)
    library = RouteLibraryService(config)

    route_groups = []
    long_rides = []
    try:
        route_groups = analysis.get_route_groups()
    except Exception:
        pass
    try:
        long_rides = analysis.get_long_rides()
    except Exception:
        pass

    try:
        library.initialize(route_groups, long_rides)
    except Exception:
        pass

    g.route_library_services = {'library': library, 'analysis': analysis}
    return g.route_library_services


@bp.route('/')
def index():
    services = get_services()
    sort_by = request.args.get('sort', 'uses')
    filter_by = request.args.get('filter', 'all')
    search_term = request.args.get('search', '')
    page = int(request.args.get('page', 1))

    routes = []
    total_routes = 0
    total_pages = 1
    error = None

    try:
        if search_term:
            result = services['library'].search_routes(search_term, limit=100)
            routes = result.get('results', []) if isinstance(result, dict) else []
        elif filter_by == 'favorite':
            result = services['library'].get_favorites()
            routes = result.get('favorites', []) if isinstance(result, dict) else []
        else:
            result = services['library'].get_all_routes(route_type=filter_by, sort_by=sort_by)
            routes = result.get('routes', []) if isinstance(result, dict) else []

        total_routes = len(routes)
        total_pages = max(1, math.ceil(total_routes / _PAGE_SIZE))
        start = (page - 1) * _PAGE_SIZE
        routes = routes[start:start + _PAGE_SIZE]

    except Exception as exc:
        error = str(exc)
        routes = []
        total_routes = 0
        total_pages = 1

    return render_template(
        'routes/index.html',
        routes=routes,
        total_routes=total_routes,
        total_pages=total_pages,
        page=page,
        sort_by=sort_by,
        filter_by=filter_by,
        search_term=search_term,
        page_title='Route Library',
        error=error,
    )


@bp.route('/<route_type>/<route_id>')
def detail(route_type, route_id):
    services = get_services()
    error = None
    route = None

    try:
        result = services['library'].get_route_details(route_id, route_type)
        if isinstance(result, dict) and result.get('status') == 'success':
            route = result.get('route')
        else:
            error = result.get('message', 'Route not found') if isinstance(result, dict) else 'Route not found'
    except Exception:
        error = 'Failed to load route details'

    if error:
        return render_template(
            'routes/detail.html',
            route=None,
            route_type=route_type,
            error=error,
            page_title='Route Not Found',
        )

    return render_template(
        'routes/detail.html',
        route=route,
        route_type=route_type,
        page_title=route.get('name', 'Route Detail') if route else 'Route Detail',
    )


@bp.route('/api/search')
def api_search():
    services = get_services()
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))
    type_filter = request.args.get('type')

    try:
        result = services['library'].search_routes(query, limit=limit)
        results = result.get('results', []) if isinstance(result, dict) else []
        if type_filter:
            results = [r for r in results if r.get('type') == type_filter]
        return jsonify({
            'status': 'success',
            'query': query,
            'results': results,
            'count': len(results),
            'limit': limit,
        })
    except Exception as exc:
        return jsonify({
            'status': 'error',
            'message': str(exc),
            'results': [],
            'count': 0,
        }), 500


@bp.route('/api/<route_id>/favorite', methods=['POST'])
def api_toggle_favorite(route_id):
    services = get_services()
    data = request.get_json(silent=True) or {}
    is_favorite = data.get('favorite', False)

    try:
        result = services['library'].toggle_favorite(route_id, is_favorite)
        return jsonify(result)
    except Exception as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 500


@bp.route('/api/stats')
def api_stats():
    services = get_services()
    try:
        stats = services['library'].get_route_statistics()
        return jsonify({
            'status': 'success',
            'statistics': stats,
            'last_updated': datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 500
