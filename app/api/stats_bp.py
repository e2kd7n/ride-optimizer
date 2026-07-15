"""Statistics API Blueprint.

Routes:
  GET  /api/stats
  GET  /api/stats/gear
  POST /api/stats/refresh-gear
  POST /api/stats/backfill-gear-ids
  GET  /api/stats/backfill-gear-ids/status
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from flask import Blueprint, current_app, jsonify, request

from app.extensions import limiter
from src.logging_config import setup_logging
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('stats', __name__, url_prefix='/api')


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_activities_for_stats():
    """Load raw activities from cache for stats computation."""
    from src.data_fetcher import Activity as _Activity
    cache_path = Path('data/cache/activities.json')
    if not cache_path.exists():
        return []
    try:
        with open(cache_path, 'r') as f:
            raw = json.load(f)
        return [_Activity.from_dict(a) for a in raw.get('activities', [])]
    except Exception as e:
        logger.warning(f"Could not load activities for stats: {e}")
        return []


def _meters_to_miles(m):
    return m * 0.000621371


def _meters_to_feet(m):
    return m * 3.28084


def _ms_to_mph(ms):
    return ms * 2.23694


def _seconds_to_hours(s):
    return s / 3600.0


def _parse_activity_start_local(start_date):
    """
    Parse a Strava activity's start_date (UTC, e.g. "...Z") into a naive
    datetime in the server's local time.

    A bare `.replace(tzinfo=None)` on the parsed UTC value keeps the UTC
    wall-clock numbers, so a ride that starts late at night locally but
    crosses into the next UTC day gets bucketed/compared against
    `datetime.now()` (local) as if it happened a day later than it did
    (issue #496). Converting via `.astimezone()` first shifts the
    wall-clock to local time before the tzinfo is dropped.
    """
    return datetime.fromisoformat(start_date.replace('Z', '+00:00')).astimezone().replace(tzinfo=None)


def _filter_activities_by_period(activities, period):
    """Return activities within the requested period."""
    now = datetime.now()
    if period == 'this_week':
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'this_month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'this_year':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'last_30d':
        start = now - timedelta(days=30)
    elif period == 'last_year':
        start = now.replace(year=now.year - 1, month=1, day=1,
                            hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(year=now.year - 1, month=12, day=31,
                          hour=23, minute=59, second=59, microsecond=0)
        result = []
        for a in activities:
            if not a.start_date:
                continue
            try:
                d = _parse_activity_start_local(a.start_date)
                if start <= d <= end:
                    result.append(a)
            except (ValueError, AttributeError):
                pass
        return result
    else:
        # all_time
        return activities

    result = []
    for a in activities:
        if not a.start_date:
            continue
        try:
            d = _parse_activity_start_local(a.start_date)
            if d >= start:
                result.append(a)
        except (ValueError, AttributeError):
            pass
    return result


def _compute_speed_distribution(activities):
    """Histogram of average speeds (mph) in 2 mph bins."""
    speeds = [round(_ms_to_mph(a.average_speed), 1)
              for a in activities if a.average_speed and a.average_speed > 0]
    if not speeds:
        return []
    bin_width = 2
    min_bin = int(min(speeds) // bin_width) * bin_width
    max_bin = int(max(speeds) // bin_width) * bin_width + bin_width
    bins = list(range(min_bin, max_bin + bin_width, bin_width))
    counts = [0] * (len(bins) - 1)
    for s in speeds:
        idx = min(int((s - min_bin) // bin_width), len(counts) - 1)
        counts[idx] += 1
    return [{'label': f'{bins[i]}-{bins[i+1]}', 'min': bins[i], 'max': bins[i+1], 'count': counts[i]}
            for i in range(len(counts))]


def _compute_elevation_distribution(activities):
    """Histogram of elevation gain per ride (ft) in 250 ft bins."""
    elevations = [round(_meters_to_feet(a.total_elevation_gain))
                  for a in activities if a.total_elevation_gain and a.total_elevation_gain > 0]
    if not elevations:
        return []
    bin_width = 250
    min_bin = int(min(elevations) // bin_width) * bin_width
    max_bin = int(max(elevations) // bin_width) * bin_width + bin_width
    bins = list(range(min_bin, max_bin + bin_width, bin_width))
    counts = [0] * (len(bins) - 1)
    for e in elevations:
        idx = min(int((e - min_bin) // bin_width), len(counts) - 1)
        counts[idx] += 1
    return [{'label': f'{bins[i]}-{bins[i+1]}', 'min': bins[i], 'max': bins[i+1], 'count': counts[i]}
            for i in range(len(counts))]


def _compute_summary(activities):
    """Compute aggregate summary stats for a list of activities."""
    if not activities:
        return {
            'total_rides': 0, 'total_distance_mi': 0, 'total_time_h': 0,
            'total_elevation_ft': 0, 'avg_distance_mi': 0, 'avg_speed_mph': 0,
            'avg_elevation_ft': 0, 'avg_heartrate': None, 'total_kudos': 0,
            'total_kilojoules': 0,
        }
    total_dist = sum(a.distance for a in activities)
    total_time = sum(a.moving_time for a in activities)
    total_elev = sum(a.total_elevation_gain for a in activities)
    n = len(activities)
    hr_vals = [a.average_heartrate for a in activities if a.average_heartrate]
    kj_vals = [a.kilojoules for a in activities if a.kilojoules]
    speed_vals = [a.average_speed for a in activities if a.average_speed]
    return {
        'total_rides': n,
        'total_distance_mi': round(_meters_to_miles(total_dist), 1),
        'total_time_h': round(_seconds_to_hours(total_time), 1),
        'total_elevation_ft': round(_meters_to_feet(total_elev)),
        'avg_distance_mi': round(_meters_to_miles(total_dist / n), 1),
        'avg_speed_mph': round(_ms_to_mph(sum(speed_vals) / len(speed_vals)), 1) if speed_vals else 0,
        'avg_elevation_ft': round(_meters_to_feet(total_elev / n)),
        'avg_heartrate': round(sum(hr_vals) / len(hr_vals), 1) if hr_vals else None,
        'total_kudos': sum(a.kudos_count for a in activities),
        'total_kilojoules': round(sum(kj_vals), 1) if kj_vals else 0,
    }


def _compute_records(activities):
    """Personal records across activities."""
    if not activities:
        return {}

    def _fmt(a):
        return {
            'id': a.id, 'name': a.name,
            'date': (a.start_date or '')[:10],
            'distance_mi': round(_meters_to_miles(a.distance), 1),
            'speed_mph': round(_ms_to_mph(a.average_speed), 1),
            'elevation_ft': round(_meters_to_feet(a.total_elevation_gain)),
            'time_h': round(_seconds_to_hours(a.moving_time), 1),
        }

    longest = max(activities, key=lambda a: a.distance)
    highest_elev = max(activities, key=lambda a: a.total_elevation_gain)
    fastest = max(activities, key=lambda a: a.average_speed)
    most_kj = max((a for a in activities if a.kilojoules), key=lambda a: a.kilojoules, default=None)
    records = {
        'longest_ride': _fmt(longest),
        'most_elevation': _fmt(highest_elev),
        'fastest_speed': _fmt(fastest),
    }
    if most_kj:
        records['most_kilojoules'] = {**_fmt(most_kj), 'kilojoules': round(most_kj.kilojoules)}
    return records


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@bp.route('/stats')
@limiter.limit("30 per minute")
def get_stats():
    """
    Aggregate ride statistics.

    Query params:
    - period: all_time | this_year | last_year | this_month | this_week | last_30d (default: all_time)
    """
    period = request.args.get('period', 'all_time')
    valid_periods = {'all_time', 'this_year', 'last_year', 'this_month', 'this_week', 'last_30d'}
    if period not in valid_periods:
        period = 'all_time'

    all_activities = _load_activities_for_stats()
    if not all_activities:
        return jsonify({'status': 'no_data',
                        'message': 'No activities cached. Fetch activities from Strava first.'})

    activities = _filter_activities_by_period(all_activities, period)

    # By-type breakdown
    type_map: Dict[str, list] = {}
    for a in activities:
        t = a.sport_type or a.type or 'Unknown'
        type_map.setdefault(t, []).append(a)
    by_type = []
    for t, acts in sorted(type_map.items(), key=lambda x: -len(x[1])):
        s = _compute_summary(acts)
        by_type.append({'sport_type': t, **s})

    # Weekly trend — last 52 weeks
    week_buckets: Dict[str, list] = {}
    for a in all_activities:
        if not a.start_date:
            continue
        try:
            d = _parse_activity_start_local(a.start_date)
            label = d.strftime('%G-W%V')
            week_buckets.setdefault(label, []).append(a)
        except (ValueError, AttributeError):
            pass
    sorted_weeks = sorted(week_buckets.keys())[-52:]
    by_week = [{'week': wk, **_compute_summary(week_buckets[wk])} for wk in sorted_weeks]

    # Monthly trend — last 24 months
    month_buckets: Dict[str, list] = {}
    for a in all_activities:
        if not a.start_date:
            continue
        try:
            d = _parse_activity_start_local(a.start_date)
            label = d.strftime('%Y-%m')
            month_buckets.setdefault(label, []).append(a)
        except (ValueError, AttributeError):
            pass
    sorted_months = sorted(month_buckets.keys())[-24:]
    by_month = [{'month': mo, **_compute_summary(month_buckets[mo])} for mo in sorted_months]

    return jsonify({
        'status': 'success',
        'data': {
            'period': period,
            'total_activities_in_cache': len(all_activities),
            'summary': _compute_summary(activities),
            'records': _compute_records(activities),
            'by_type': by_type,
            'by_week': by_week,
            'by_month': by_month,
            'speed_distribution': _compute_speed_distribution(activities),
            'elevation_distribution': _compute_elevation_distribution(activities),
        },
        'timestamp': datetime.now().isoformat(),
    })


@bp.route('/stats/gear')
def get_gear_stats():
    """Per-gear (bike/shoe) statistics computed from cached activities."""
    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    all_activities = _load_activities_for_stats()

    gear_cache = analysis_service.data_fetcher.load_cached_gear() if analysis_service else None
    gear_meta: Dict[str, dict] = {}
    if gear_cache:
        for g in gear_cache.get('bikes', []) + gear_cache.get('shoes', []):
            gear_meta[g['id']] = g

    gear_buckets: Dict[str, list] = {}
    unassigned = []
    for a in all_activities:
        if a.gear_id:
            gear_buckets.setdefault(a.gear_id, []).append(a)
        else:
            unassigned.append(a)

    gear_list = []
    for gear_id, acts in gear_buckets.items():
        meta = gear_meta.get(gear_id, {'id': gear_id, 'name': gear_id, 'type': 'unknown'})
        s = _compute_summary(acts)
        last_used = max((a.start_date or '' for a in acts), default='')[:10]
        gear_list.append({**meta, **s, 'last_used': last_used})

    gear_list.sort(key=lambda g: (0 if g.get('type') == 'bike' else 1, -g.get('total_distance_mi', 0)))

    return jsonify({
        'status': 'success',
        'data': {
            'gear': gear_list,
            'unassigned': _compute_summary(unassigned),
            'gear_cache_available': gear_cache is not None,
        },
        'timestamp': datetime.now().isoformat(),
    })


@bp.route('/stats/refresh-gear', methods=['POST'])
def refresh_gear():
    """Fetch athlete's bikes and shoes from Strava and update the gear cache."""
    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    try:
        data = analysis_service.data_fetcher.fetch_athlete_gear()
        bikes = len(data.get('bikes', []))
        shoes = len(data.get('shoes', []))
        return jsonify({
            'status': 'success',
            'message': f'Refreshed {bikes} bikes and {shoes} shoes',
            'bikes': bikes,
            'shoes': shoes,
        })
    except Exception as e:
        logger.error(f"Failed to refresh gear: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/stats/backfill-gear-ids', methods=['POST'])
def backfill_gear_ids():
    """
    Patch gear_id on cached activities that are missing it.
    Runs as a background job; poll /api/stats/backfill-gear-ids/status for progress.
    """
    jobs = current_app.container.jobs
    if not jobs.backfill.try_start({'status': 'running', 'fetched': 0, 'updated': 0,
                                    'label': 'Connecting to Strava…'}):
        return jsonify({'status': 'already_running'}), 409

    container = current_app.container
    container.initialise()

    analysis_service = container.analysis_service
    if analysis_service is None:
        jobs.backfill.reset({'status': 'idle'})
        return jsonify({'status': 'error', 'message': 'Analysis is currently unavailable'}), 503

    def _run():
        try:
            def _progress(fetched, updated):
                jobs.backfill.update(
                    fetched=fetched, updated=updated,
                    label=f'Scanned {fetched:,} activities, patched {updated:,} gear IDs…')

            result = analysis_service.data_fetcher.backfill_gear_ids(progress_callback=_progress)
            jobs.backfill.update(
                status='done',
                label=f"Done — {result['updated']} activities updated, {result['skipped']} already had gear ID",
                **result,
            )
        except Exception as e:
            logger.error(f"Gear backfill failed: {e}", exc_info=True)
            jobs.backfill.update(status='error', label=f'Error: {e}')

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'status': 'started'})


@bp.route('/stats/backfill-gear-ids/status')
def backfill_gear_ids_status():
    return jsonify(current_app.container.jobs.backfill.snapshot())
