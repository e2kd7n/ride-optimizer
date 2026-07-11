"""Integrations API Blueprint.

Routes:
  GET  /api/intervals/status
  POST /api/intervals/connect
  POST /api/intervals/disconnect
  GET  /api/ors/status
  POST /api/ors/connect
  POST /api/ors/disconnect
  GET  /api/location/status
  POST /api/location/save
  GET  /api/garmin/status
  POST /api/garmin/connect
  POST /api/garmin/disconnect
  POST /api/garmin/sync
  GET  /api/trainerroad/status
  POST /api/trainerroad/connect
  POST /api/trainerroad/sync
  POST /api/trainerroad/disconnect
  GET  /api/trainerroad/workouts
  GET  /api/trainerroad/today
"""

import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.credentials.env_helpers import read_env, write_env
from app.extensions import limiter
from src.config_manager import ConfigManager
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('integrations', __name__, url_prefix='/api')


# ---------------------------------------------------------------------------
# intervals.icu
# ---------------------------------------------------------------------------

@bp.route('/intervals/status')
def intervals_status():
    """Return whether intervals.icu credentials are configured and valid."""
    creds = current_app.container.intervals_creds.load()
    if not creds:
        return jsonify({'connected': False})
    return jsonify({'connected': True, 'athlete_id': creds['athlete_id']})


@bp.route('/intervals/connect', methods=['POST'])
@limiter.limit("10 per minute")
def intervals_connect():
    """Save intervals.icu credentials and verify them against the API."""
    data = request.get_json(silent=True) or {}
    athlete_id = str(data.get('athlete_id', '')).strip()
    api_key = str(data.get('api_key', '')).strip()

    if not athlete_id or not api_key:
        return jsonify({'success': False, 'error': 'Athlete ID and API Key are required'}), 400

    if not athlete_id.startswith('i'):
        athlete_id = 'i' + athlete_id

    try:
        import requests as http_req
        from requests.auth import HTTPBasicAuth
        resp = http_req.get(
            f'https://intervals.icu/api/v1/athlete/{athlete_id}',
            auth=HTTPBasicAuth('API_KEY', api_key),
            timeout=10,
        )
        if resp.status_code == 401:
            return jsonify({'success': False, 'error': 'Invalid API key — check your intervals.icu API settings'}), 400
        if resp.status_code == 404:
            return jsonify({'success': False, 'error': f'Athlete {athlete_id} not found — check your Athlete ID'}), 400
        if not resp.ok:
            return jsonify({'success': False, 'error': f'intervals.icu returned {resp.status_code}'}), 400

        athlete_data = resp.json()
        athlete_name = athlete_data.get('name') or athlete_data.get('username') or athlete_id
    except Exception as exc:
        logger.warning("intervals.icu connect error: %s", exc)
        return jsonify({'success': False, 'error': 'Could not reach intervals.icu'}), 503

    try:
        current_app.container.intervals_creds.save(athlete_id, api_key)
        logger.info("intervals.icu credentials saved for athlete %s (%s)", athlete_id, athlete_name)
        return jsonify({'success': True, 'athlete_id': athlete_id, 'athlete_name': athlete_name})
    except Exception as exc:
        logger.error("intervals.icu: failed to save credentials: %s", exc)
        return jsonify({'success': False, 'error': 'Could not save credentials'}), 500


@bp.route('/intervals/disconnect', methods=['POST'])
def intervals_disconnect():
    """Remove saved intervals.icu credentials."""
    try:
        current_app.container.intervals_creds.delete()
        logger.info("intervals.icu credentials removed")
        return jsonify({'success': True})
    except Exception as exc:
        logger.error("intervals.icu: failed to delete credentials: %s", exc)
        return jsonify({'success': False, 'error': 'Could not remove credentials'}), 500


# ---------------------------------------------------------------------------
# ORS (OpenRouteService)
# ---------------------------------------------------------------------------

@bp.route('/ors/status')
def ors_status():
    """Return whether ORS API key is configured."""
    env = read_env()
    api_key = os.getenv('ORS_API_KEY') or env.get('ORS_API_KEY', '')
    return jsonify({'configured': bool(api_key and api_key != 'your_ors_api_key')})


@bp.route('/ors/connect', methods=['POST'])
def ors_connect():
    """Save ORS API key to .env."""
    data = request.get_json(silent=True) or {}
    api_key = str(data.get('api_key', '')).strip()

    if not api_key:
        return jsonify({'success': False, 'error': 'API key is required'}), 400

    try:
        write_env({'ORS_API_KEY': api_key})
        os.environ['ORS_API_KEY'] = api_key
        ConfigManager.get_instance().reload()
        logger.info("ORS API key saved")
        return jsonify({'success': True})
    except OSError as exc:
        logger.error("ORS: failed to write .env: %s", exc)
        return jsonify({'success': False, 'error': 'Could not save API key'}), 500


@bp.route('/ors/disconnect', methods=['POST'])
def ors_disconnect():
    """Remove ORS API key from .env and unset it in the running process."""
    try:
        write_env({'ORS_API_KEY': ''})
        os.environ.pop('ORS_API_KEY', None)
        ConfigManager.get_instance().reload()
        logger.info("ORS API key removed")
        return jsonify({'success': True})
    except OSError as exc:
        logger.error("ORS: failed to clear .env: %s", exc)
        return jsonify({'success': False, 'error': 'Could not remove API key'}), 500


# ---------------------------------------------------------------------------
# Home & Work Location (#472)
# ---------------------------------------------------------------------------

def _read_location_coord(env: dict, key: str):
    val = os.getenv(key)
    if val is None:
        val = env.get(key)
    if val is None or val == '':
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _validate_location_payload(payload, label: str):
    """Validate a {"lat": ..., "lon": ...} payload. Returns ((lat, lon), None) or (None, error)."""
    if not isinstance(payload, dict):
        return None, f'{label} location is required'
    try:
        lat = float(payload.get('lat'))
        lon = float(payload.get('lon'))
    except (TypeError, ValueError):
        return None, f'{label} latitude/longitude must be numbers'
    if not (-90 <= lat <= 90):
        return None, f'{label} latitude must be between -90 and 90'
    if not (-180 <= lon <= 180):
        return None, f'{label} longitude must be between -180 and 180'
    return (lat, lon), None


@bp.route('/location/status')
def location_status():
    """Return currently configured home/work coordinates, read from .env."""
    env = read_env()
    home_lat = _read_location_coord(env, 'HOME_LATITUDE')
    home_lon = _read_location_coord(env, 'HOME_LONGITUDE')
    work_lat = _read_location_coord(env, 'WORK_LATITUDE')
    work_lon = _read_location_coord(env, 'WORK_LONGITUDE')

    home = {'lat': home_lat, 'lon': home_lon} if home_lat is not None and home_lon is not None else None
    work = {'lat': work_lat, 'lon': work_lon} if work_lat is not None and work_lon is not None else None

    return jsonify({'configured': home is not None and work is not None, 'home': home, 'work': work})


@bp.route('/location/save', methods=['POST'])
@limiter.limit("10 per minute")
def location_save():
    """Validate and persist home/work coordinates to .env, then reload config."""
    data = request.get_json(silent=True) or {}

    home, home_err = _validate_location_payload(data.get('home'), 'Home')
    if home_err:
        return jsonify({'success': False, 'error': home_err}), 400
    work, work_err = _validate_location_payload(data.get('work'), 'Work')
    if work_err:
        return jsonify({'success': False, 'error': work_err}), 400

    env_updates = {
        'HOME_LATITUDE': home[0],
        'HOME_LONGITUDE': home[1],
        'WORK_LATITUDE': work[0],
        'WORK_LONGITUDE': work[1],
    }
    try:
        write_env({k: str(v) for k, v in env_updates.items()})
        for k, v in env_updates.items():
            os.environ[k] = str(v)
    except OSError as exc:
        logger.error("Location: failed to write .env: %s", exc)
        return jsonify({'success': False, 'error': 'Could not write location to .env — check file permissions'}), 500

    logger.info("Home/work location saved via settings")

    # .env is the source of truth and is now correct — a failure past this point (e.g. a
    # concurrent edit leaving config.yaml briefly invalid) shouldn't be reported as a lost save.
    try:
        ConfigManager.get_instance().reload()
        current_app.container.reset_initialisation()
    except Exception as exc:
        logger.error("Location saved but config reload failed: %s", exc, exc_info=True)
        return jsonify({'success': True, 'warning': 'Saved, but the app may need a restart to pick up the change.'})

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# Garmin Connect
# ---------------------------------------------------------------------------

@bp.route('/garmin/status')
def garmin_status():
    """Return Garmin Connect connection status."""
    svc = current_app.container.get_garmin_service()
    return jsonify(svc.get_status())


@bp.route('/garmin/connect', methods=['POST'])
@limiter.limit("10 per minute")
def garmin_connect():
    """Authenticate with Garmin Connect via email + password."""
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', '')).strip()

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password are required'}), 400

    svc = current_app.container.get_garmin_service()
    result = svc.connect(email, password)
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@bp.route('/garmin/disconnect', methods=['POST'])
def garmin_disconnect():
    """Remove Garmin Connect credentials."""
    svc = current_app.container.get_garmin_service()
    svc.disconnect()
    return jsonify({'success': True})


@bp.route('/garmin/sync', methods=['POST'])
@limiter.limit("10 per minute")
def garmin_sync():
    """Fetch activities from Garmin Connect and merge into local cache."""
    container = current_app.container
    container.initialise()

    svc = container.get_garmin_service()
    if not svc.is_connected():
        return jsonify({'success': False, 'error': 'Garmin not connected'}), 400

    data = request.get_json(silent=True) or {}
    days = min(int(data.get('days', 90)), 365)

    try:
        activities = svc.fetch_activities(days=days)
        if container.analysis_service and container.analysis_service.data_fetcher:
            existing = container.analysis_service.data_fetcher.load_cached_activities() or []
            existing_ids = {a.id for a in existing}
            new_acts = [a for a in activities if a.id not in existing_ids]
            if new_acts:
                merged = existing + new_acts
                container.analysis_service.data_fetcher.cache_activities(merged)
            return jsonify({
                'success': True,
                'fetched': len(activities),
                'new': len(new_acts),
                'total': len(existing) + len(new_acts),
            })
        return jsonify({'success': True, 'fetched': len(activities), 'new': len(activities)})
    except Exception as e:
        logger.error(f"Garmin sync failed: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# TrainerRoad
# ---------------------------------------------------------------------------

@bp.route('/trainerroad/status')
def trainerroad_status():
    """Return TrainerRoad connection status."""
    container = current_app.container
    container.initialise()

    trainerroad_service = container.trainerroad_service
    if trainerroad_service is None:
        return jsonify({'status': 'error', 'message': 'TrainerRoad is currently unavailable'}), 503

    status = trainerroad_service.get_status()
    return jsonify(status)


@bp.route('/trainerroad/connect', methods=['POST'])
@limiter.limit("10 per minute")
def trainerroad_connect():
    """Set ICS feed URL, validate, and trigger initial sync."""
    container = current_app.container
    container.initialise()

    trainerroad_service = container.trainerroad_service
    if trainerroad_service is None:
        return jsonify({'status': 'error', 'message': 'TrainerRoad is currently unavailable'}), 503

    data = request.get_json(silent=True) or {}
    feed_url = (data.get('feed_url') or '').strip()

    if not feed_url:
        return jsonify({'success': False, 'error': 'Feed URL is required'}), 400

    if not trainerroad_service.set_feed_url(feed_url):
        return jsonify({'success': False, 'error': 'Invalid feed URL'}), 400

    result = trainerroad_service.sync_workouts()
    return jsonify({
        'success': result.get('status') == 'success',
        'workouts_synced': result.get('workouts_synced', 0),
        'error': result.get('message') if result.get('status') != 'success' else None,
    })


@bp.route('/trainerroad/sync', methods=['POST'])
@limiter.limit("10 per minute")
def trainerroad_sync():
    """Force a workout sync."""
    container = current_app.container
    container.initialise()

    trainerroad_service = container.trainerroad_service
    if trainerroad_service is None:
        return jsonify({'status': 'error', 'message': 'TrainerRoad is currently unavailable'}), 503

    trainerroad_service.last_sync = None
    result = trainerroad_service.sync_workouts()
    return jsonify({
        'success': result.get('status') == 'success',
        'workouts_synced': result.get('workouts_synced', 0),
        'created': result.get('workouts_created', 0),
        'updated': result.get('workouts_updated', 0),
    })


@bp.route('/trainerroad/disconnect', methods=['POST'])
def trainerroad_disconnect():
    """Remove TrainerRoad credentials and clear cached workouts."""
    container = current_app.container
    container.initialise()

    trainerroad_service = container.trainerroad_service
    if trainerroad_service is None:
        return jsonify({'status': 'error', 'message': 'TrainerRoad is currently unavailable'}), 503

    trainerroad_service.remove_credentials()
    return jsonify({'success': True})


@bp.route('/trainerroad/workouts')
def trainerroad_workouts():
    """Return upcoming workouts for settings table."""
    container = current_app.container
    container.initialise()

    trainerroad_service = container.trainerroad_service
    if trainerroad_service is None:
        return jsonify({'status': 'error', 'message': 'TrainerRoad is currently unavailable'}), 503

    workouts = trainerroad_service.get_upcoming_workouts(days_ahead=7)
    return jsonify({'workouts': workouts})


@bp.route('/trainerroad/today')
def trainerroad_today():
    """Return today's workout summary with weather-aware indoor/outdoor decision."""
    container = current_app.container
    container.initialise()

    trainerroad_service = container.trainerroad_service
    if trainerroad_service is None:
        return jsonify({'status': 'error', 'message': 'TrainerRoad is currently unavailable'}), 503

    summary = trainerroad_service.get_today_summary()

    if summary.get('has_workout') and container.commute_service:
        from datetime import date as _date
        constraints = trainerroad_service.get_workout_constraints(_date.today())
        if constraints:
            container.commute_service._apply_weather_indoor_decision(constraints)
            summary['workout']['indoor_fallback'] = constraints.get('indoor_fallback', False)
            summary['workout']['indoor_reason'] = constraints.get('indoor_reason')
            summary['workout']['notes'] = constraints.get('notes', [])

    return jsonify(summary)
