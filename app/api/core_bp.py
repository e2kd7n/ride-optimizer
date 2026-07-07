"""Core API Blueprint.

Routes:
  GET    /api/status
  GET    /api/settings
  PUT    /api/settings
  DELETE /api/settings
  DELETE /api/user/data
  GET    /api/plans
  POST   /api/plans
  DELETE /api/plans/<plan_id>
  GET    /api/csrf-token
"""

import secrets
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from flask_wtf.csrf import generate_csrf

from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('core', __name__, url_prefix='/api')


@bp.route('/csrf-token')
def get_csrf_token():
    """Return a CSRF token for clients making state-changing requests."""
    return jsonify({'csrf_token': generate_csrf()})


@bp.route('/status')
def get_status():
    """Get system health and data freshness status."""
    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    try:
        analysis_status = analysis_service.get_analysis_status()

        cache_files = {}
        for name in ('analysis_status.json', 'route_groups.json', 'long_rides.json'):
            path = Path('data') / name
            if path.exists():
                cache_files[name] = {'exists': True, 'size_bytes': path.stat().st_size}
            else:
                cache_files[name] = {'exists': False, 'size_bytes': 0}

        status_data = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'last_update': analysis_status.get('last_analysis'),
            'services': {
                'analysis': 'available' if container.analysis_service else 'unavailable',
                'commute': 'available' if container.commute_service else 'unavailable',
                'weather': 'available' if container.weather_service else 'unavailable',
                'planner': 'available' if container.planner_service else 'unavailable',
                'route_library': 'available' if container.route_library_service else 'unavailable',
                'trainerroad': 'available' if container.trainerroad_service else 'unavailable'
            },
            'data': analysis_status,
            'cache': {
                'files': cache_files,
                'total_size_bytes': sum(f['size_bytes'] for f in cache_files.values()),
            }
        }
        return jsonify(status_data)

    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Status temporarily unavailable'}), 500


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@bp.route('/settings', methods=['GET'])
def get_settings():
    """Return current user settings merged with defaults."""
    try:
        settings = current_app.container.settings_service.get_settings()
        return jsonify({'status': 'success', 'settings': settings})
    except Exception as e:
        logger.error(f"Error reading settings: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to read settings'}), 500


@bp.route('/settings', methods=['PUT'])
def update_settings():
    """Partial-update user settings. Only known keys are accepted."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Request body must be a JSON object'}), 400

    try:
        settings = current_app.container.settings_service.update_settings(data)
        return jsonify({'status': 'success', 'settings': settings})
    except Exception as e:
        logger.error(f"Error updating settings: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to update settings'}), 500


@bp.route('/settings', methods=['DELETE'])
def reset_settings():
    """Reset user settings to defaults."""
    try:
        settings = current_app.container.settings_service.reset_settings()
        return jsonify({'status': 'success', 'settings': settings})
    except Exception as e:
        logger.error(f"Error resetting settings: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to reset settings'}), 500


# ---------------------------------------------------------------------------
# User data
# ---------------------------------------------------------------------------

@bp.route('/user/data', methods=['DELETE'])
def delete_user_data():
    """GDPR-compliant endpoint to delete all user data."""
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is not True:
        return jsonify({
            'status': 'error',
            'message': 'Confirmation required. Send {"confirm": true} to delete all data.'
        }), 400

    deleted = []

    storage = current_app.container.storage
    for filename in storage.list_files():
        if storage.delete(filename):
            deleted.append(f'data/{filename}')

    cache_path = Path('data/cache/activities.json')
    if cache_path.exists():
        try:
            cache_path.unlink()
            deleted.append('data/cache/activities.json')
        except Exception as e:
            logger.error(f"Failed to delete activity cache: {e}")

    credentials_path = Path('config/credentials.json')
    if credentials_path.exists():
        try:
            credentials_path.unlink()
            deleted.append('config/credentials.json')
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")

    logger.info(f"GDPR data deletion completed. Deleted: {deleted}")
    return jsonify({'status': 'success', 'deleted': deleted})


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

@bp.route('/plans', methods=['GET'])
def get_plans():
    """List all saved plans."""
    plans = current_app.container.storage.read('saved_plans.json', default=[])
    return jsonify({'status': 'success', 'plans': plans})


@bp.route('/plans', methods=['POST'])
def save_plan():
    """Save a ride plan from an existing route."""
    data = request.get_json(silent=True) or {}
    route_id = data.get('route_id')
    route_name = data.get('route_name', '')
    route_type = data.get('route_type', '')
    note = data.get('note', '')
    distance = data.get('distance', 0)
    duration = data.get('duration', 0)
    elevation = data.get('elevation', 0)

    if not route_id:
        return jsonify({'status': 'error', 'message': 'route_id is required'}), 400
    if len(str(note)) > 500:
        return jsonify({'status': 'error', 'message': 'Note must be 500 characters or less'}), 400

    plans = current_app.container.storage.read('saved_plans.json', default=[])
    plan = {
        'id': secrets.token_hex(8),
        'route_id': str(route_id),
        'route_name': str(route_name)[:200],
        'route_type': str(route_type)[:50],
        'note': str(note)[:500],
        'distance': distance,
        'duration': duration,
        'elevation': elevation,
        'created_at': datetime.now().isoformat(),
    }
    plans.insert(0, plan)
    current_app.container.storage.write('saved_plans.json', plans)
    return jsonify({'status': 'success', 'plan': plan}), 201


@bp.route('/plans/<plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    """Delete a saved plan."""
    if not plan_id or not plan_id.replace('-', '').replace('_', '').isalnum():
        return jsonify({'status': 'error', 'message': 'Invalid plan ID'}), 400

    plans = current_app.container.storage.read('saved_plans.json', default=[])
    original_len = len(plans)
    plans = [p for p in plans if p.get('id') != plan_id]

    if len(plans) == original_len:
        return jsonify({'status': 'error', 'message': 'Plan not found'}), 404

    current_app.container.storage.write('saved_plans.json', plans)
    return jsonify({'status': 'success'})
