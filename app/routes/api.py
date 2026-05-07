"""
API blueprint - Internal REST API endpoints.

Provides JSON API for:
- Data synchronization
- Background job management
- System status and health
- Cache management
- Analytics and metrics
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from app.models import db, JobHistory, AnalysisSnapshot
from app.scheduler import scheduler
from app.scheduler.health import HealthChecker
from app.scheduler.scheduler import get_scheduler_status

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/health')
def health():
    """
    Health check endpoint.
    
    Returns system health status for monitoring.
    """
    health_checker = HealthChecker()
    system_health = health_checker.check_all()
    
    return jsonify(system_health.to_dict())


@bp.route('/status')
def status():
    """
    Detailed system status.
    
    Returns comprehensive status information including:
    - Data freshness
    - Background job status
    - Cache statistics
    - API rate limits
    """
    current_app.logger.info('System status requested')
    
    # Get latest analysis snapshot for freshness
    latest_snapshot = AnalysisSnapshot.query.order_by(
        AnalysisSnapshot.analysis_date.desc()
    ).first()
    
    # Count jobs by status (last 24 hours)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    active_jobs = JobHistory.query.filter(
        JobHistory.status == 'running',
        JobHistory.started_at >= cutoff
    ).count()
    
    queued_jobs = JobHistory.query.filter(
        JobHistory.status == 'pending',
        JobHistory.created_at >= cutoff
    ).count()
    
    failed_jobs = JobHistory.query.filter(
        JobHistory.status == 'failed',
        JobHistory.started_at >= cutoff
    ).count()
    
    # Get cache statistics
    cache_stats = _get_cache_statistics()
    
    # Get scheduler status
    scheduler_info = get_scheduler_status()
    
    return jsonify({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data_freshness': {
            'activities': latest_snapshot.analysis_date.isoformat() if latest_snapshot else None,
            'snapshot_status': latest_snapshot.status if latest_snapshot else None,
            'activities_count': latest_snapshot.activities_count if latest_snapshot else 0
        },
        'background_jobs': {
            'active': active_jobs,
            'queued': queued_jobs,
            'failed': failed_jobs
        },
        'scheduler': {
            'running': scheduler_info['running'],
            'jobs_count': scheduler_info['jobs_count']
        },
        'cache': cache_stats
    })


def _get_cache_statistics() -> dict:
    """Get statistics for all cache files.
    
    Returns:
        Dictionary with cache statistics by type
    """
    cache_dir = Path('cache')
    stats = {}
    
    if not cache_dir.exists():
        return stats
    
    for cache_file in cache_dir.glob('*.json'):
        try:
            file_size = cache_file.stat().st_size
            
            # Try to count entries
            entry_count = 0
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        entry_count = len(data)
                    elif isinstance(data, list):
                        entry_count = len(data)
            except:
                pass
            
            # Determine cache type from filename
            cache_type = cache_file.stem.replace('_cache', '')
            
            stats[cache_type] = {
                'entries': entry_count,
                'size_bytes': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'last_modified': datetime.fromtimestamp(
                    cache_file.stat().st_mtime, tz=timezone.utc
                ).isoformat()
            }
        except Exception as e:
            current_app.logger.warning(f"Error reading cache file {cache_file}: {e}")
    
    return stats


@bp.route('/sync', methods=['POST'])
def sync():
    """
    Trigger data synchronization.
    
    POST body (JSON):
    {
        "source": "strava",  # or "weather", "all"
        "force": false  # Force sync even if data is fresh
    }
    
    Returns job ID for tracking.
    """
    data = request.get_json() or {}
    source = data.get('source', 'all')
    force = data.get('force', False)
    
    current_app.logger.info(f'Data sync requested: source={source}, force={force}')
    
    # Create job record
    # Use JobHistory.create_job() class method for proper initialization
    job = JobHistory.create_job(
        job_type=f'sync_{source}',
        job_name=f'Manual Sync: {source}',
        parameters={'source': source, 'force': force},
        triggered_by='user'
    )
    db.session.add(job)
    db.session.commit()
    
    # Queue the job with scheduler
    from app.scheduler.jobs import run_daily_analysis
    if scheduler and scheduler.running:
        scheduler.add_job(
            func=run_daily_analysis,
            trigger='date',
            run_date=datetime.now(timezone.utc),
            id=f'manual_sync_{job.id}',
            name=f'Manual Sync #{job.id}',
            replace_existing=True
        )
    
    return jsonify({
        'status': 'queued',
        'job_id': str(job.id),
        'source': source,
        'queued_at': job.created_at.isoformat()
    }), 202


@bp.route('/jobs')
def jobs():
    """
    List background jobs.
    
    Query params:
    - status: Filter by status (active, queued, completed, failed)
    - limit: Maximum results (default: 50)
    
    Returns list of jobs with status.
    """
    status_filter = request.args.get('status', 'all')
    limit = request.args.get('limit', 50, type=int)
    
    current_app.logger.info(f'Jobs list requested: status={status_filter}, limit={limit}')
    
    # Build query
    query = JobHistory.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Get jobs ordered by most recent first
    jobs_list = query.order_by(JobHistory.created_at.desc()).limit(limit).all()
    
    return jsonify({
        'jobs': [
            {
                'id': job.id,
                'job_id': job.job_id,
                'job_type': job.job_type,
                'job_name': job.job_name,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'duration_seconds': job.duration_seconds,
                'error_message': job.error_message
            }
            for job in jobs_list
        ],
        'count': len(jobs_list),
        'filter': status_filter,
        'limit': limit
    })


@bp.route('/jobs/<int:job_id>')
def job_status(job_id):
    """
    Get status of a specific background job.
    
    Returns detailed job information including progress.
    """
    current_app.logger.info(f'Job status requested: job_id={job_id}')
    
    job = JobHistory.query.get_or_404(job_id)
    
    return jsonify({
        'id': job.id,
        'job_id': job.job_id,
        'job_type': job.job_type,
        'job_name': job.job_name,
        'status': job.status,
        'progress': job.progress,
        'created_at': job.created_at.isoformat(),
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'duration_seconds': job.duration_seconds,
        'error_message': job.error_message,
        'result_summary': job.result_summary
    })


@bp.route('/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """
    Cancel a running or queued job.
    
    Returns cancellation status.
    """
    current_app.logger.info(f'Job cancellation requested: job_id={job_id}')
    
    job = JobHistory.query.get_or_404(job_id)
    
    if job.status in ('completed', 'failed', 'cancelled'):
        return jsonify({
            'error': 'Job already finished',
            'status': job.status
        }), 400
    
    # Mark as cancelled
    job.status = 'cancelled'
    job.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    
    # Try to remove from scheduler if it's queued
    if scheduler and scheduler.running:
        try:
            scheduler.remove_job(f'manual_sync_{job_id}')
        except:
            pass  # Job may not be in scheduler
    
    return jsonify({
        'status': 'cancelled',
        'job_id': job_id,
        'cancelled_at': job.completed_at.isoformat()
    })


@bp.route('/cache/stats')
def cache_stats():
    """
    Get cache statistics.
    
    Returns detailed cache information for all cache types.
    """
    stats = _get_cache_statistics()
    
    return jsonify({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'caches': stats,
        'total_size_mb': sum(s.get('size_mb', 0) for s in stats.values()),
        'total_entries': sum(s.get('entries', 0) for s in stats.values())
    })


@bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """
    Clear cache data.
    
    POST body (JSON):
    {
        "cache_type": "geocoding",  # or "weather", "route_groups", "all"
        "confirm": true
    }
    
    Returns cleared cache statistics.
    """
    data = request.get_json() or {}
    cache_type = data.get('cache_type', 'all')
    confirm = data.get('confirm', False)
    
    if not confirm:
        return jsonify({
            'error': 'Confirmation required',
            'message': 'Set "confirm": true to clear cache'
        }), 400
    
    current_app.logger.warning(f'Cache clear requested: type={cache_type}')
    
    cache_dir = Path('cache')
    if not cache_dir.exists():
        return jsonify({
            'error': 'Cache directory not found'
        }), 404
    
    entries_removed = 0
    size_freed = 0
    
    # Determine which files to clear
    if cache_type == 'all':
        pattern = '*.json'
    else:
        pattern = f'{cache_type}_cache.json'
    
    for cache_file in cache_dir.glob(pattern):
        try:
            file_size = cache_file.stat().st_size
            cache_file.unlink()
            entries_removed += 1
            size_freed += file_size
            current_app.logger.info(f"Cleared cache file: {cache_file.name}")
        except Exception as e:
            current_app.logger.error(f"Failed to clear {cache_file}: {e}")
    
    return jsonify({
        'status': 'cleared',
        'cache_type': cache_type,
        'cleared_at': datetime.now(timezone.utc).isoformat(),
        'files_removed': entries_removed,
        'size_freed_mb': round(size_freed / (1024 * 1024), 2)
    })


@bp.route('/analytics/summary')
def analytics_summary():
    """
    Get analytics summary.
    
    Returns high-level analytics including:
    - Total activities
    - Total routes
    - Usage patterns
    - Performance trends
    """
    # Get latest snapshot for analytics
    latest_snapshot = AnalysisSnapshot.query.order_by(
        AnalysisSnapshot.analysis_date.desc()
    ).first()
    
    if not latest_snapshot:
        return jsonify({
            'error': 'No analysis data available',
            'message': 'Run analysis first to generate analytics'
        }), 404
    
    # Get route groups from snapshot
    route_groups = latest_snapshot.route_groups
    
    return jsonify({
        'period': 'latest',
        'snapshot_date': latest_snapshot.analysis_date.isoformat(),
        'activities': {
            'total': latest_snapshot.activities_count,
            'snapshot_status': latest_snapshot.status
        },
        'routes': {
            'total': latest_snapshot.route_groups_count,
            'most_used': [
                {
                    'id': rg.id,
                    'name': rg.name,
                    'uses_count': rg.uses_count
                }
                for rg in sorted(route_groups, key=lambda x: x.uses_count, reverse=True)[:5]
            ]
        },
        'long_rides': {
            'total': latest_snapshot.long_rides_count
        }
    })


@bp.route('/metrics')
def metrics():
    """
    Prometheus-style metrics endpoint.
    
    Returns metrics in Prometheus text format for monitoring.
    """
    # Get latest snapshot
    latest_snapshot = AnalysisSnapshot.query.order_by(
        AnalysisSnapshot.analysis_date.desc()
    ).first()
    
    # Get job statistics
    total_jobs = JobHistory.query.count()
    failed_jobs = JobHistory.query.filter_by(status='failed').count()
    
    # Get cache statistics
    cache_stats = _get_cache_statistics()
    total_cache_mb = sum(s.get('size_mb', 0) for s in cache_stats.values())
    
    metrics_text = f"""# HELP ride_optimizer_activities_total Total number of activities
# TYPE ride_optimizer_activities_total gauge
ride_optimizer_activities_total {latest_snapshot.activities_count if latest_snapshot else 0}

# HELP ride_optimizer_routes_total Total number of routes
# TYPE ride_optimizer_routes_total gauge
ride_optimizer_routes_total {latest_snapshot.route_groups_count if latest_snapshot else 0}

# HELP ride_optimizer_long_rides_total Total number of long rides
# TYPE ride_optimizer_long_rides_total gauge
ride_optimizer_long_rides_total {latest_snapshot.long_rides_count if latest_snapshot else 0}

# HELP ride_optimizer_jobs_total Total number of background jobs
# TYPE ride_optimizer_jobs_total counter
ride_optimizer_jobs_total {total_jobs}

# HELP ride_optimizer_jobs_failed_total Total number of failed jobs
# TYPE ride_optimizer_jobs_failed_total counter
ride_optimizer_jobs_failed_total {failed_jobs}

# HELP ride_optimizer_cache_size_mb Total cache size in megabytes
# TYPE ride_optimizer_cache_size_mb gauge
ride_optimizer_cache_size_mb {total_cache_mb}

# HELP ride_optimizer_scheduler_running Scheduler running status (1=running, 0=stopped)
# TYPE ride_optimizer_scheduler_running gauge
ride_optimizer_scheduler_running {1 if scheduler and scheduler.running else 0}
"""
    
    return metrics_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@bp.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors in API routes."""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested API endpoint does not exist'
    }), 404


@bp.errorhandler(500)
def api_server_error(error):
    """Handle 500 errors in API routes."""
    current_app.logger.error(f'API server error: {error}')
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500

# Made with Bob
