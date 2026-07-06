"""Data API Blueprint (analyze, fetch, cache, activities).

Routes:
  POST /api/analyze
  GET  /api/analyze/status
  POST /api/analyze/stop
  POST /api/fetch
  GET  /api/fetch/status
  GET  /api/cache-info
  GET  /api/activities
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from flask import Blueprint, current_app, jsonify, request

from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('data', __name__, url_prefix='/api')

# Module-level job state — mirrors launch.py module globals
_analysis_job: Dict[str, Any] = {'status': 'idle', 'started_at': None, 'result': None}
_analysis_stop_requested: bool = False
_fetch_job: Dict[str, Any] = {'status': 'idle', 'fetched': 0, 'label': '', 'started_at': None}


# ---------------------------------------------------------------------------
# Unit conversion helpers (shared with stats_bp — kept local here to avoid
# creating a coupling; they're trivial one-liners)
# ---------------------------------------------------------------------------

def _meters_to_miles(m):
    return m * 0.000621371


def _meters_to_feet(m):
    return m * 3.28084


def _ms_to_mph(ms):
    return ms * 2.23694


def _seconds_to_hours(s):
    return s / 3600.0


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@bp.route('/analyze', methods=['POST'])
def trigger_analysis():
    global _analysis_job
    if _analysis_job.get('status') == 'running':
        return jsonify({'status': 'already_running', 'message': 'Analysis is already in progress'}), 409

    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    data = request.get_json(silent=True) or {}
    fetch_new = bool(data.get('fetch_new', False))
    force_refresh = bool(data.get('force_refresh', True))

    after_date = None
    before_date = None
    if fetch_new:
        for key, target in [('after_date', 'after_date'), ('before_date', 'before_date')]:
            raw = data.get(key)
            if raw:
                try:
                    parsed = datetime.fromisoformat(raw)
                    if key == 'after_date':
                        after_date = parsed
                    else:
                        before_date = parsed
                except (ValueError, TypeError):
                    pass

    _analysis_job = {
        'status': 'running',
        'phase': 'starting',
        'fetched': 0,
        'preview_ready': False,
        'preview_count': 0,
        'label': 'Starting…',
        'started_at': datetime.now().isoformat(),
        'result': None,
        'routes_done': 0,
        'routes_total': 0,
        'eta_secs': None,
    }

    def _update_job(**kwargs):
        global _analysis_job
        for k, v in kwargs.items():
            _analysis_job[k] = v

    global _analysis_stop_requested
    _analysis_stop_requested = False

    def _stop_check():
        return _analysis_stop_requested

    def _run():
        global _analysis_job, _analysis_stop_requested
        try:
            result = analysis_service.run_full_analysis(
                force_refresh=force_refresh,
                skip_strava_fetch=not fetch_new,
                after=after_date,
                before=before_date,
                on_progress=_update_job,
                stop_check=_stop_check,
            )
            if _analysis_stop_requested:
                _update_job(status='stopped', phase='stopped',
                            label='Analysis stopped by user')
            else:
                _update_job(status='done', phase='done', result=result,
                            label=f"Done — {result.get('activities_count', 0):,} activities")
            container.reset_initialisation()
        except Exception as e:
            logger.error(f"Background analysis failed: {e}", exc_info=True)
            _update_job(status='error', phase='error',
                        result={'status': 'error', 'message': str(e)},
                        label=f'Error: {e}')
        finally:
            _analysis_stop_requested = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'fetch_new': fetch_new})


@bp.route('/analyze/status')
def get_analyze_status():
    return jsonify(_analysis_job)


@bp.route('/analyze/stop', methods=['POST'])
def stop_analysis():
    global _analysis_stop_requested, _analysis_job
    if _analysis_job.get('status') != 'running':
        return jsonify({'status': 'not_running'}), 400
    _analysis_stop_requested = True
    _analysis_job['label'] = 'Stopping…'
    return jsonify({'status': 'stopping'})


@bp.route('/fetch', methods=['POST'])
def trigger_fetch():
    global _fetch_job
    if _fetch_job.get('status') == 'running':
        return jsonify({'status': 'already_running'}), 409

    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    data = request.get_json(silent=True) or {}

    after_date = None
    before_date = None
    for key in ('after_date', 'before_date'):
        raw = data.get(key)
        if raw:
            try:
                val = datetime.fromisoformat(raw)
                if key == 'after_date':
                    after_date = val
                else:
                    before_date = val
            except (ValueError, TypeError):
                pass

    limit = int(data.get('limit', 1000))

    _fetch_job = {
        'status': 'running',
        'fetched': 0,
        'label': 'Connecting to Strava…',
        'started_at': datetime.now().isoformat(),
        'total_in_cache': 0,
    }

    def _run():
        global _fetch_job
        try:
            import time as _time
            import json as _json
            from pathlib import Path as _Path

            cache_path = _Path('data/cache/activities.json')
            pre_fetch_count = 0
            if cache_path.exists():
                try:
                    with open(cache_path) as f:
                        raw = _json.load(f)
                    pre_fetch_count = raw.get('count', len(raw.get('activities', [])))
                except Exception:
                    pass

            def _progress(count):
                if count % 30 == 0 and count > 0:
                    _time.sleep(2)
                _fetch_job['fetched'] = count
                _fetch_job['label'] = f'Fetching from Strava… {count:,} activities'

            analysis_service.data_fetcher.fetch_activities(
                limit=limit,
                after=after_date,
                before=before_date,
                use_cache=False,
                progress_callback=_progress,
                merge_cache=True,
            )

            total = _fetch_job['fetched']
            if cache_path.exists():
                with open(cache_path) as f:
                    raw = _json.load(f)
                total = raw.get('count', len(raw.get('activities', [])))

            new_count = total - pre_fetch_count
            if new_count > 0:
                _fetch_job.update({
                    'label': f'Fetch done — {new_count:,} new activities. Running incremental analysis…',
                    'total_in_cache': total,
                })
                logger.info(f"Fetch added {new_count} new activities, triggering incremental analysis")
                analysis_service.run_full_analysis(
                    force_refresh=False,
                    skip_strava_fetch=True,
                )
                container.reset_initialisation()
                _fetch_job.update({
                    'status': 'done',
                    'label': f'Done — {total:,} activities, {new_count:,} new (analysis updated)',
                    'total_in_cache': total,
                })
            else:
                _fetch_job.update({
                    'status': 'done',
                    'label': f'Done — {total:,} activities in cache (no new activities)',
                    'total_in_cache': total,
                })
        except Exception as e:
            logger.error(f"Background fetch failed: {e}", exc_info=True)
            _fetch_job.update({'status': 'error', 'label': f'Error: {e}'})

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started'})


@bp.route('/fetch/status')
def get_fetch_status():
    return jsonify(_fetch_job)


@bp.route('/cache-info')
def get_cache_info():
    cache_path = Path('data/cache/activities.json')
    if not cache_path.exists():
        return jsonify({'status': 'no_cache', 'activity_count': 0})
    try:
        with open(cache_path) as f:
            cache_data = json.load(f)
        activities = cache_data.get('activities', cache_data) if isinstance(cache_data, dict) else cache_data
        if not isinstance(activities, list):
            return jsonify({'status': 'error', 'message': 'Cache format unrecognized'}), 500
        dates = sorted(a['start_date'] for a in activities if isinstance(a, dict) and a.get('start_date'))
        stat = cache_path.stat()
        return jsonify({
            'status': 'ok',
            'activity_count': len(activities),
            'date_earliest': dates[0] if dates else None,
            'date_latest': dates[-1] if dates else None,
            'cache_size_mb': round(stat.st_size / (1024 * 1024), 1),
            'cache_age_hours': round((datetime.now().timestamp() - stat.st_mtime) / 3600, 1),
        })
    except Exception as e:
        logger.error(f"Error reading cache info: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/activities')
def get_activities():
    """
    Filterable list of raw activities from cache.

    Query params:
    - gear_id: filter by gear ID
    - sport_type: filter by sport type
    - period: all_time | this_year | last_year | this_month | this_week | last_30d
    - sort: date_desc | date_asc | distance_desc | speed_desc | elevation_desc
    - limit: max results (default 200)
    - offset: pagination offset (default 0)
    """
    from src.data_fetcher import Activity as _Activity
    from datetime import timedelta

    gear_id = request.args.get('gear_id', '').strip() or None
    sport_type = request.args.get('sport_type', '').strip() or None
    period = request.args.get('period', 'all_time')
    sort = request.args.get('sort', 'date_desc')
    try:
        limit = min(int(request.args.get('limit', 200)), 1000)
        offset = max(int(request.args.get('offset', 0)), 0)
    except (ValueError, TypeError):
        limit, offset = 200, 0

    # Load activities
    cache_path = Path('data/cache/activities.json')
    all_activities = []
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                raw = json.load(f)
            all_activities = [_Activity.from_dict(a) for a in raw.get('activities', [])]
        except Exception as e:
            logger.warning(f"Could not load activities: {e}")

    # Filter by period
    now = datetime.now()
    if period == 'this_week':
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        activities = [a for a in all_activities if a.start_date and _parse_date(a.start_date) >= start]
    elif period == 'this_month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        activities = [a for a in all_activities if a.start_date and _parse_date(a.start_date) >= start]
    elif period == 'this_year':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        activities = [a for a in all_activities if a.start_date and _parse_date(a.start_date) >= start]
    elif period == 'last_30d':
        start = now - timedelta(days=30)
        activities = [a for a in all_activities if a.start_date and _parse_date(a.start_date) >= start]
    elif period == 'last_year':
        start = now.replace(year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=now.year - 1, month=12, day=31, hour=23, minute=59, second=59, microsecond=0)
        activities = [a for a in all_activities if a.start_date and start <= _parse_date(a.start_date) <= end]
    else:
        activities = all_activities

    # Load gear metadata
    analysis_service = current_app.container.analysis_service
    gear_cache = analysis_service.data_fetcher.load_cached_gear() if analysis_service else None
    gear_names: Dict[str, str] = {}
    gear_types: Dict[str, str] = {}
    if gear_cache:
        for g in gear_cache.get('bikes', []) + gear_cache.get('shoes', []):
            gear_names[g['id']] = g.get('name', g['id'])
            gear_types[g['id']] = g.get('type', 'unknown')

    if gear_id:
        activities = [a for a in activities if a.gear_id == gear_id]
    if sport_type:
        activities = [a for a in activities if (a.sport_type or a.type) == sport_type]

    sort_key_map = {
        'date_desc': (lambda a: a.start_date or '', True),
        'date_asc': (lambda a: a.start_date or '', False),
        'distance_desc': (lambda a: a.distance, True),
        'speed_desc': (lambda a: a.average_speed, True),
        'elevation_desc': (lambda a: a.total_elevation_gain, True),
    }
    key_fn, reverse = sort_key_map.get(sort, sort_key_map['date_desc'])
    activities.sort(key=key_fn, reverse=reverse)

    total = len(activities)
    page = activities[offset:offset + limit]

    def _serialize(a):
        return {
            'id': a.id,
            'name': a.name,
            'sport_type': a.sport_type or a.type,
            'date': (a.start_date or '')[:10],
            'distance_mi': round(_meters_to_miles(a.distance), 1),
            'time_h': round(_seconds_to_hours(a.moving_time), 1),
            'elevation_ft': round(_meters_to_feet(a.total_elevation_gain)),
            'speed_mph': round(_ms_to_mph(a.average_speed), 1),
            'gear_id': a.gear_id,
            'gear_name': gear_names.get(a.gear_id, '') if a.gear_id else '',
            'gear_type': gear_types.get(a.gear_id, '') if a.gear_id else '',
            'average_heartrate': a.average_heartrate,
            'average_watts': a.average_watts,
            'suffer_score': a.suffer_score,
            'kudos_count': a.kudos_count,
            'achievement_count': a.achievement_count,
            'pr_count': a.pr_count,
        }

    return jsonify({
        'status': 'success',
        'data': {
            'activities': [_serialize(a) for a in page],
            'total': total,
            'offset': offset,
            'limit': limit,
        },
        'timestamp': datetime.now().isoformat(),
    })


def _parse_date(s: str) -> datetime:
    """Parse an ISO date string, stripping timezone for naive comparison."""
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00')).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return datetime.min
