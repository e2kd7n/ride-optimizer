"""Internal REST API endpoints: health, status, sync, jobs, cache, analytics, metrics."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import Blueprint, jsonify, request

from app.models import db, JobHistory, AnalysisSnapshot, RouteGroup
from app.scheduler.scheduler import get_scheduler_status, scheduler
from app.scheduler.health import HealthChecker

bp = Blueprint('routes_api', __name__)


def _get_cache_statistics():
    cache_dir = Path('data/cache')
    if not cache_dir.exists():
        return {}
    stats = {}
    try:
        for cache_file in cache_dir.glob('*.json'):
            try:
                key = cache_file.stem.replace('_cache', '')
                stat = cache_file.stat()
                size_mb = round(stat.st_size / (1024 * 1024), 2)
                with open(cache_file) as f:
                    data = json.load(f)
                entries = len(data) if isinstance(data, (dict, list)) else 0
                stats[key] = {
                    'entries': entries,
                    'size_mb': size_mb,
                    'last_modified': datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            except Exception:
                return {}
    except Exception:
        return {}
    return stats


@bp.route('/api/health')
def health():
    checker = HealthChecker()
    health_data = checker.check_all()
    return jsonify(health_data.to_dict())


@bp.route('/api/status')
def status():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    snapshot = AnalysisSnapshot.query.order_by(AnalysisSnapshot.analysis_date.desc()).first()

    active = JobHistory.query.filter_by(status='running').count()
    queued = JobHistory.query.filter(
        JobHistory.status.in_(['queued', 'pending'])
    ).count()
    failed = JobHistory.query.filter(
        JobHistory.status == 'failed',
        JobHistory.started_at >= cutoff,
    ).count()

    cache_stats = _get_cache_statistics()
    scheduler_status = get_scheduler_status()

    if snapshot:
        data_freshness = {
            'activities': snapshot.activities_count,
            'activities_count': snapshot.activities_count,
            'route_groups': snapshot.route_groups_count,
            'long_rides': snapshot.long_rides_count,
            'last_analysis': snapshot.analysis_date.isoformat() if snapshot.analysis_date else None,
        }
    else:
        data_freshness = {
            'activities': None,
            'activities_count': 0,
            'route_groups': 0,
            'long_rides': 0,
            'last_analysis': None,
        }

    return jsonify({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data_freshness': data_freshness,
        'background_jobs': {
            'active': active,
            'queued': queued,
            'failed': failed,
        },
        'scheduler': scheduler_status,
        'cache': cache_stats,
    })


@bp.route('/api/sync', methods=['POST'])
def sync():
    data = request.get_json(silent=True) or {}
    source = data.get('source', 'all')
    force = data.get('force', False)

    job = JobHistory.create_job(
        job_type=f'sync_{source}',
        job_name=f'Manual Sync: {source}',
        parameters={'source': source, 'force': force},
        triggered_by='user',
    )

    return jsonify({
        'status': 'queued',
        'source': source,
        'job_id': job.job_id,
    }), 202


@bp.route('/api/jobs')
def list_jobs():
    status_filter = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 50))

    query = JobHistory.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    jobs = query.order_by(JobHistory.id.desc()).limit(limit).all()

    return jsonify({
        'jobs': [j.to_dict() for j in jobs],
        'count': len(jobs),
        'filter': status_filter,
        'limit': limit,
    })


@bp.route('/api/jobs/<int:job_id>')
def get_job(job_id):
    job = JobHistory.query.get(job_id)
    if not job:
        return jsonify({'error': 'Not Found'}), 404
    return jsonify(job.to_dict())


@bp.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    job = JobHistory.query.get(job_id)
    if not job:
        return jsonify({'error': 'Not Found'}), 404
    if job.status in ('completed', 'failed', 'cancelled'):
        return jsonify({'error': f'Job already {job.status}', 'status': job.status}), 400
    job.cancel()
    return jsonify({'status': 'cancelled', 'job_id': job.id})


@bp.route('/api/cache/stats')
def cache_stats_endpoint():
    stats = _get_cache_statistics()
    total_size = sum(v.get('size_mb', 0) for v in stats.values())
    total_entries = sum(v.get('entries', 0) for v in stats.values())
    return jsonify({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_size_mb': round(total_size, 2),
        'total_entries': total_entries,
        'caches': stats,
    })


@bp.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    data = request.get_json(silent=True) or {}
    if not data.get('confirm'):
        return jsonify({'error': 'Confirmation required'}), 400

    cache_type = data.get('cache_type', 'all')
    cache_dir = Path('data/cache')

    if not cache_dir.exists():
        return jsonify({'error': 'Cache directory not found'}), 404

    pattern = '*.json' if cache_type == 'all' else f'*{cache_type}*.json'
    files = list(cache_dir.glob(pattern))
    total_bytes = 0
    for f in files:
        total_bytes += f.stat().st_size
        f.unlink()

    return jsonify({
        'status': 'cleared',
        'cache_type': cache_type,
        'files_removed': len(files),
        'size_freed_mb': round(total_bytes / (1024 * 1024), 2),
    })


@bp.route('/api/analytics/summary')
def analytics_summary():
    snapshot = AnalysisSnapshot.query.order_by(AnalysisSnapshot.analysis_date.desc()).first()
    if not snapshot:
        return jsonify({'error': 'No analysis data available'}), 404

    route_groups = (
        RouteGroup.query
        .filter_by(snapshot_id=snapshot.id)
        .order_by(RouteGroup.frequency.desc())
        .all()
    )

    most_used = [
        {
            'id': rg.group_id,
            'name': rg.name,
            'uses_count': rg.frequency,
            'direction': rg.direction,
        }
        for rg in route_groups
    ]

    return jsonify({
        'activities': {'total': snapshot.activities_count},
        'routes': {
            'total': snapshot.route_groups_count,
            'most_used': most_used,
        },
        'long_rides': {'total': snapshot.long_rides_count},
    })


@bp.route('/api/metrics')
def metrics():
    snapshot = AnalysisSnapshot.query.order_by(AnalysisSnapshot.analysis_date.desc()).first()
    cache_stats = _get_cache_statistics()

    activities = snapshot.activities_count if snapshot else 0
    routes = snapshot.route_groups_count if snapshot else 0
    long_rides = snapshot.long_rides_count if snapshot else 0

    total_jobs = JobHistory.query.count()
    failed_jobs = JobHistory.query.filter_by(status='failed').count()
    total_cache_mb = sum(v.get('size_mb', 0) for v in cache_stats.values())
    scheduler_running = 1 if (scheduler and scheduler.running) else 0

    lines = [
        f'ride_optimizer_activities_total {activities}',
        f'ride_optimizer_routes_total {routes}',
        f'ride_optimizer_long_rides_total {long_rides}',
        f'ride_optimizer_jobs_total {total_jobs}',
        f'ride_optimizer_jobs_failed_total {failed_jobs}',
        f'ride_optimizer_cache_size_mb {total_cache_mb}',
        f'ride_optimizer_scheduler_running {scheduler_running}',
    ]

    return '\n'.join(lines), 200, {'Content-Type': 'text/plain; charset=utf-8'}
