"""Planner, Exploration, and Geocode API Blueprint.

Routes:
  GET  /api/planner/recommendations
  GET  /api/planner/rides/nearby
  GET  /api/planner/rides/<ride_id>
  POST /api/planner/analyze
  GET  /api/exploration/tiles
  GET  /api/exploration/roads
  POST /api/exploration/invalidate
  POST /api/exploration/route
  POST /api/exploration/verify-tiles
  GET  /api/geocode
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.extensions import limiter
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('planner', __name__, url_prefix='/api')


# ---------------------------------------------------------------------------
# Planner routes
# ---------------------------------------------------------------------------

@bp.route('/planner/recommendations')
def planner_recommendations():
    """Weather-optimized long ride recommendations for upcoming days."""
    container = current_app.container
    container.initialise()

    planner_service = container.planner_service
    if planner_service is None:
        return jsonify({'status': 'error', 'message': 'Planner is currently unavailable'}), 503

    forecast_days = request.args.get('forecast_days', 7, type=int)
    min_distance = request.args.get('min_distance', 30.0, type=float)
    max_distance = request.args.get('max_distance', 100.0, type=float)

    result = planner_service.get_recommendations(
        forecast_days=forecast_days,
        min_distance=min_distance,
        max_distance=max_distance,
    )
    return jsonify(result)


@bp.route('/planner/rides/nearby')
def planner_rides_nearby():
    """Find rides near a given lat/lon."""
    container = current_app.container
    container.initialise()

    planner_service = container.planner_service
    if planner_service is None:
        return jsonify({'status': 'error', 'message': 'Planner is currently unavailable'}), 503

    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if lat is None or lon is None:
        return jsonify({'status': 'error', 'message': 'lat and lon are required'}), 400

    radius = request.args.get('radius_miles', 10.0, type=float)
    limit = request.args.get('limit', 10, type=int)

    result = planner_service.get_rides_near_location(lat, lon, radius, limit)
    return jsonify(result)


@bp.route('/planner/rides/<int:ride_id>')
def planner_ride_detail(ride_id):
    """Get details for a specific long ride."""
    container = current_app.container
    container.initialise()

    planner_service = container.planner_service
    if planner_service is None:
        return jsonify({'status': 'error', 'message': 'Planner is currently unavailable'}), 503

    result = planner_service.get_ride_details(ride_id)
    if result.get('status') == 'error':
        return jsonify(result), 404
    return jsonify(result)


@bp.route('/planner/analyze', methods=['POST'])
def planner_analyze_ride():
    """Analyze a planned long ride for difficulty and weather suitability."""
    container = current_app.container
    container.initialise()

    planner_service = container.planner_service
    if planner_service is None:
        return jsonify({'status': 'error', 'message': 'Planner is currently unavailable'}), 503

    data = request.get_json(silent=True) or {}
    distance = data.get('distance')
    duration = data.get('duration')
    if distance is None or duration is None:
        return jsonify({'status': 'error', 'message': 'distance and duration are required'}), 400

    date_str = data.get('date')
    ride_date = None
    if date_str:
        try:
            from datetime import date as _date
            ride_date = _date.fromisoformat(date_str)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'date must be YYYY-MM-DD'}), 400

    result = planner_service.analyze_long_ride(distance, duration, ride_date)
    status_code = result.pop('status', 200) if isinstance(result.get('status'), int) else 200
    if status_code >= 400:
        return jsonify(result), status_code
    return jsonify(result)


# ---------------------------------------------------------------------------
# Exploration routes
# ---------------------------------------------------------------------------

@bp.route('/exploration/tiles')
def exploration_tiles():
    """Tile coverage within a bounding box, or all tiles if no bounds given."""
    from src.coverage_tracker import TILE_ZOOM, SQUADRATINHO_ZOOM

    svc = current_app.container.get_exploration_service()

    south = request.args.get('south', type=float)
    west = request.args.get('west', type=float)
    north = request.args.get('north', type=float)
    east = request.args.get('east', type=float)

    zoom = request.args.get('zoom', type=int)
    if zoom is not None and zoom not in (TILE_ZOOM, SQUADRATINHO_ZOOM):
        return jsonify({
            'status': 'error',
            'message': f'zoom must be {TILE_ZOOM} (squadrat) or {SQUADRATINHO_ZOOM} (squadratinho)',
        }), 400

    if all(v is not None for v in (south, west, north, east)):
        result = svc.get_tile_coverage((south, west, north, east), zoom=zoom)
    else:
        result = svc.get_tile_coverage_all(zoom=zoom)

    status_code = 200 if result.get('status') == 'success' else 500
    return jsonify(result), status_code


@bp.route('/exploration/roads')
@limiter.limit("20 per minute")
def exploration_roads():
    """Road coverage within a bounding box (requires osmnx)."""
    svc = current_app.container.get_exploration_service()

    south = request.args.get('south', type=float)
    west = request.args.get('west', type=float)
    north = request.args.get('north', type=float)
    east = request.args.get('east', type=float)

    if any(v is None for v in (south, west, north, east)):
        return jsonify({'status': 'error', 'message': 'south, west, north, east are required'}), 400

    result = svc.get_road_coverage((south, west, north, east))
    status_code = 200 if result.get('status') == 'success' else 500
    return jsonify(result), status_code


@bp.route('/exploration/invalidate', methods=['POST'])
def exploration_invalidate():
    """Clear coverage caches (call after fetching new activities)."""
    svc = current_app.container.get_exploration_service()
    svc.invalidate_caches()
    return jsonify({'status': 'success', 'message': 'Coverage caches invalidated'})


@bp.route('/exploration/route', methods=['POST'])
@limiter.limit("20 per minute")
def exploration_route():
    """Compute a road-following route via ORS for a given waypoint list."""
    svc = current_app.container.get_exploration_service()
    data = request.get_json(silent=True) or {}
    waypoints = data.get('waypoints')
    if not waypoints or not isinstance(waypoints, list) or len(waypoints) < 2:
        return jsonify({'status': 'error', 'message': 'waypoints must be a list of at least 2 [lat, lon] pairs'}), 400
    surface_preference = data.get('surface_preference', 'any')
    if surface_preference not in ('any', 'paved', 'unpaved'):
        return jsonify({'status': 'error', 'message': 'surface_preference must be any, paved, or unpaved'}), 400
    result = svc.compute_route(waypoints, surface_preference=surface_preference)
    status_code = 200 if result.get('status') == 'success' else 500
    return jsonify(result), status_code


@bp.route('/exploration/verify-tiles', methods=['POST'])
@limiter.limit("30 per minute")
def exploration_verify_tiles():
    """Check which planned tiles a route's actual polyline really crosses.

    Planned "new tile" claims are computed before the road route is known
    (see exploration-worker.js); a claim corner can end up snapped to a road
    that never enters the tile. This re-checks claims against the real
    routed coordinates using the same tile-crossing math used to score
    recorded activities (#493).
    """
    from src.coverage_tracker import TILE_ZOOM, SQUADRATINHO_ZOOM

    svc = current_app.container.get_exploration_service()
    data = request.get_json(silent=True) or {}

    coordinates = data.get('coordinates')
    if not isinstance(coordinates, list) or len(coordinates) < 1:
        return jsonify({'status': 'error', 'message': 'coordinates must be a non-empty list of [lat, lon] pairs'}), 400
    if len(coordinates) > 5000:
        return jsonify({'status': 'error', 'message': 'coordinates list too large (max 5000)'}), 400
    try:
        coordinates = [(float(c[0]), float(c[1])) for c in coordinates]
    except (TypeError, ValueError, IndexError):
        return jsonify({'status': 'error', 'message': 'coordinates must be [lat, lon] number pairs'}), 400

    tiles = data.get('tiles')
    if not isinstance(tiles, list) or len(tiles) < 1:
        return jsonify({'status': 'error', 'message': 'tiles must be a non-empty list of {x, y, zoom}'}), 400
    if len(tiles) > 500:
        return jsonify({'status': 'error', 'message': 'tiles list too large (max 500)'}), 400

    allowed_zooms = (TILE_ZOOM, SQUADRATINHO_ZOOM)
    try:
        tiles = [{'x': int(t['x']), 'y': int(t['y']), 'zoom': int(t['zoom'])} for t in tiles]
    except (TypeError, ValueError, KeyError):
        return jsonify({'status': 'error', 'message': 'each tile must have integer x, y, zoom'}), 400
    if any(t['zoom'] not in allowed_zooms for t in tiles):
        return jsonify({'status': 'error', 'message': f'zoom must be one of {allowed_zooms}'}), 400

    result = svc.verify_tile_claims(coordinates, tiles)
    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Geocode route
# ---------------------------------------------------------------------------

@bp.route('/geocode')
@limiter.limit("1 per second")
def geocode_location():
    """Forward-geocode a city/state or postal code to coordinates."""
    query = (request.args.get('query') or '').strip()
    if not query:
        return jsonify({'status': 'error', 'message': 'query is required'}), 400
    if len(query) > 200:
        return jsonify({'status': 'error', 'message': 'query is too long'}), 400

    svc = current_app.container.get_geocoding_service()
    result = svc.geocode(query)
    status_code = 200 if result.get('status') == 'success' else 404
    return jsonify(result), status_code
