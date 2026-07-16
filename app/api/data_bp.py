"""Data API Blueprint (analyze, fetch, cache, activities).

Routes:
  POST /api/analyze
  GET  /api/analyze/status
  POST /api/analyze/stop
  POST /api/fetch
  GET  /api/fetch/status
  POST /api/fetch/backfill-history
  GET  /api/fetch/backfill-history/status
  POST /api/fetch/backfill-history/stop
  GET  /api/cache-info
  GET  /api/activities
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from flask import Blueprint, current_app, jsonify, request

from app.extensions import limiter
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('data', __name__, url_prefix='/api')


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


def _parse_date_range(data: dict):
    """
    Parse after_date/before_date from a request body into datetimes suitable
    for stravalib's get_activities(after=, before=).

    Two corrections vs a bare `datetime.fromisoformat()`:
    - A naive datetime is treated by stravalib as already being UTC. Our
      callers (the calendar view, the Settings custom-range picker) send
      bare "YYYY-MM-DD" values that represent a *local* calendar date, so
      the naive datetime is localized to the server's local timezone before
      being handed off — otherwise the query window is shifted by the
      server's UTC offset (issue #494).
    - `before_date` is documented/used as an inclusive end date ("through
      this day"), but Strava's `before` filter is a strict less-than. A
      bare date (no time component) is bumped forward one day so the whole
      selected day is included (issue #495).
    """
    after_date = None
    before_date = None
    for key, target in (('after_date', 'after'), ('before_date', 'before')):
        raw = data.get(key)
        if not raw:
            continue
        try:
            parsed = datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            continue
        is_bare_date = 'T' not in raw
        if target == 'before' and is_bare_date:
            parsed = parsed + timedelta(days=1)
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()  # attach server-local tzinfo, same wall-clock time
        if target == 'after':
            after_date = parsed
        else:
            before_date = parsed
    return after_date, before_date


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@bp.route('/analyze', methods=['POST'])
@limiter.limit("10 per minute")
def trigger_analysis():
    jobs = current_app.container.jobs
    if not jobs.analysis.try_start({
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
    }):
        return jsonify({'status': 'already_running', 'message': 'Analysis is already in progress'}), 409

    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        jobs.analysis.reset({'status': 'idle', 'started_at': None, 'result': None})
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    data = request.get_json(silent=True) or {}
    fetch_new = bool(data.get('fetch_new', False))
    force_refresh = bool(data.get('force_refresh', False))

    after_date, before_date = _parse_date_range(data) if fetch_new else (None, None)

    jobs.analysis_stop.clear()

    def _run():
        try:
            result = analysis_service.run_full_analysis(
                force_refresh=force_refresh,
                skip_strava_fetch=not fetch_new,
                after=after_date,
                before=before_date,
                on_progress=jobs.analysis.update,
                stop_check=jobs.analysis_stop.is_set,
            )
            if jobs.analysis_stop.is_set():
                jobs.analysis.update(status='stopped', phase='stopped',
                                     label='Analysis stopped by user')
            else:
                jobs.analysis.update(status='done', phase='done', result=result,
                                     label=f"Done — {result.get('activities_count', 0):,} activities")
            container.reset_initialisation()
        except Exception as e:
            logger.error(f"Background analysis failed: {e}", exc_info=True)
            jobs.analysis.update(status='error', phase='error',
                                 result={'status': 'error', 'message': str(e)},
                                 label=f'Error: {e}')
        finally:
            jobs.analysis_stop.clear()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started', 'fetch_new': fetch_new})


@bp.route('/analyze/status')
def get_analyze_status():
    return jsonify(current_app.container.jobs.analysis.snapshot())


@bp.route('/analyze/stop', methods=['POST'])
def stop_analysis():
    jobs = current_app.container.jobs
    if jobs.analysis.get('status') != 'running':
        return jsonify({'status': 'not_running'}), 400
    jobs.analysis_stop.set()
    jobs.analysis.update(label='Stopping…')
    return jsonify({'status': 'stopping'})


@bp.route('/fetch', methods=['POST'])
@limiter.limit("10 per minute")
def trigger_fetch():
    jobs = current_app.container.jobs
    if not jobs.fetch.try_start({
        'status': 'running',
        'fetched': 0,
        'label': 'Connecting to Strava…',
        'started_at': datetime.now().isoformat(),
        'total_in_cache': 0,
    }):
        return jsonify({'status': 'already_running'}), 409

    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        jobs.fetch.reset({'status': 'idle', 'fetched': 0, 'label': '', 'started_at': None})
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    data = request.get_json(silent=True) or {}

    after_date, before_date = _parse_date_range(data)

    limit = int(data.get('limit', 1000))

    def _run():
        try:
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
                jobs.fetch.update(fetched=count,
                                  label=f'Fetching from Strava… {count:,} activities')

            analysis_service.data_fetcher.fetch_activities(
                limit=limit,
                after=after_date,
                before=before_date,
                use_cache=False,
                progress_callback=_progress,
                merge_cache=True,
            )

            total = jobs.fetch.get('fetched', 0)
            if cache_path.exists():
                with open(cache_path) as f:
                    raw = _json.load(f)
                total = raw.get('count', len(raw.get('activities', [])))

            new_count = total - pre_fetch_count
            if new_count > 0:
                jobs.fetch.update(
                    label=f'Fetch done — {new_count:,} new activities. Running incremental analysis…',
                    total_in_cache=total,
                )
                logger.info(f"Fetch added {new_count} new activities, triggering incremental analysis")
                analysis_service.run_full_analysis(
                    force_refresh=False,
                    skip_strava_fetch=True,
                )
                container.reset_initialisation()
                jobs.fetch.update(
                    status='done',
                    label=f'Done — {total:,} activities, {new_count:,} new (analysis updated)',
                    total_in_cache=total,
                )
            else:
                jobs.fetch.update(
                    status='done',
                    label=f'Done — {total:,} activities in cache (no new activities)',
                    total_in_cache=total,
                )
        except Exception as e:
            logger.error(f"Background fetch failed: {e}", exc_info=True)
            jobs.fetch.update(status='error', label=f'Error: {e}')

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started'})


@bp.route('/fetch/status')
def get_fetch_status():
    return jsonify(current_app.container.jobs.fetch.snapshot())


@bp.route('/fetch/backfill-history', methods=['POST'])
@limiter.limit("2 per minute")
def trigger_history_backfill():
    """
    Page backward through the account's full Strava history (issue #486).

    A normal fetch only ever returns the most recent `max_activities`
    activities. This walks backward with `before=` until it reaches the
    start of history or catches up to what's already cached. Explicit,
    user-triggered action — not run as part of the normal fetch/analyze flow.
    """
    jobs = current_app.container.jobs
    if not jobs.history_backfill.try_start({
        'status': 'running',
        'new_total': 0,
        'pages': 0,
        'label': 'Starting full history backfill…',
        'started_at': datetime.now().isoformat(),
    }):
        return jsonify({'status': 'already_running'}), 409

    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        jobs.history_backfill.reset({'status': 'idle'})
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    jobs.history_backfill_stop.clear()

    def _progress(new_total, pages, oldest_seen):
        label = f'Paging back through history… {new_total:,} new activities found ({pages} pages)'
        if oldest_seen:
            label += f', now at {oldest_seen.date()}'
        jobs.history_backfill.update(new_total=new_total, pages=pages, label=label)

    def _run():
        try:
            result = analysis_service.data_fetcher.backfill_full_history(
                progress_callback=_progress,
                stop_check=jobs.history_backfill_stop.is_set,
            )
            new_total = result['new_total']
            if new_total > 0:
                jobs.history_backfill.update(
                    label=f'Backfill done — {new_total:,} new activities. Running incremental analysis…',
                    new_total=new_total,
                    pages=result['pages'],
                )
                analysis_service.run_full_analysis(force_refresh=False, skip_strava_fetch=True)
                container.reset_initialisation()
                jobs.history_backfill.update(
                    status='done',
                    label=f'Done — {new_total:,} new activities backfilled (analysis updated)',
                )
            else:
                jobs.history_backfill.update(
                    status='done',
                    label='Done — cache already had full history, nothing new found',
                )
        except Exception as e:
            logger.error(f"Background history backfill failed: {e}", exc_info=True)
            jobs.history_backfill.update(status='error', label=f'Error: {e}')
        finally:
            jobs.history_backfill_stop.clear()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started'})


@bp.route('/fetch/backfill-history/status')
def get_history_backfill_status():
    return jsonify(current_app.container.jobs.history_backfill.snapshot())


@bp.route('/fetch/backfill-history/stop', methods=['POST'])
def stop_history_backfill():
    jobs = current_app.container.jobs
    if jobs.history_backfill.get('status') != 'running':
        return jsonify({'status': 'not_running'}), 400
    jobs.history_backfill_stop.set()
    jobs.history_backfill.update(label='Stopping…')
    return jsonify({'status': 'stopping'})


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
        activities = [a for a in all_activities if a.start_date and _activity_local_start(a) >= start]
    elif period == 'this_month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        activities = [a for a in all_activities if a.start_date and _activity_local_start(a) >= start]
    elif period == 'this_year':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        activities = [a for a in all_activities if a.start_date and _activity_local_start(a) >= start]
    elif period == 'last_30d':
        start = now - timedelta(days=30)
        activities = [a for a in all_activities if a.start_date and _activity_local_start(a) >= start]
    elif period == 'last_year':
        start = now.replace(year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=now.year - 1, month=12, day=31, hour=23, minute=59, second=59, microsecond=0)
        activities = [a for a in all_activities if a.start_date and start <= _activity_local_start(a) <= end]
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


def _activity_local_start(a) -> datetime:
    """
    Return an activity's start as a naive datetime in the *ride's own*
    local time, so period filters bucket by the calendar day/month/year the
    ride actually started in rather than the server's timezone or UTC
    (issue #496). See app/api/stats_bp.py for the fuller rationale — this
    mirrors that helper for the /activities list endpoint.
    """
    local = getattr(a, 'start_date_local', None)
    if local:
        try:
            return datetime.fromisoformat(local.replace('Z', '+00:00')).replace(tzinfo=None)
        except (ValueError, AttributeError):
            pass
    if not a.start_date:
        return datetime.min
    try:
        return datetime.fromisoformat(a.start_date.replace('Z', '+00:00')).astimezone().replace(tzinfo=None)
    except (ValueError, AttributeError):
        return datetime.min
