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
from datetime import datetime

from app.scheduler import scheduler, HealthChecker
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
    - Scheduler status
    - Data freshness
    - Background job status
    """
    current_app.logger.info('System status requested')
    
    # Get scheduler status
    scheduler_status = get_scheduler_status()
    
    # Get health status
    health_checker = HealthChecker()
    system_health = health_checker.check_all()
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'scheduler': scheduler_status,
        'health': system_health.to_dict()
    })


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
    
    # TODO: Implement with service layer (Issue #130, #137)
    # - Queue background job for sync
    # - Return job ID for status tracking
    
    return jsonify({
        'status': 'queued',
        'job_id': 'sync-' + datetime.now().strftime('%Y%m%d-%H%M%S'),
        'source': source,
        'queued_at': datetime.now().isoformat()
    }), 202


@bp.route('/scheduler/jobs')
def scheduler_jobs():
    """
    List scheduled jobs.
    
    Returns list of all scheduled jobs with their next run times.
    """
    current_app.logger.info('Scheduled jobs list requested')
    
    scheduler_status = get_scheduler_status()
    
    return jsonify({
        'jobs': scheduler_status.get('jobs', []),
        'count': len(scheduler_status.get('jobs', [])),
        'running': scheduler_status.get('running', False)
    })


@bp.route('/scheduler/jobs/<job_id>')
def scheduler_job_detail(job_id):
    """
    Get details of a specific scheduled job.
    
    Returns detailed job information.
    """
    current_app.logger.info(f'Scheduled job detail requested: job_id={job_id}')
    
    if scheduler is None or not scheduler.running:
        return jsonify({
            'error': 'Scheduler not running'
        }), 503
    
    job = scheduler.get_job(job_id)
    if job is None:
        return jsonify({
            'error': 'Job not found'
        }), 404
    
    return jsonify({
        'id': job.id,
        'name': job.name,
        'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
        'trigger': str(job.trigger)
    })


@bp.route('/scheduler/trigger/<job_id>', methods=['POST'])
def trigger_job(job_id):
    """
    Manually trigger a scheduled job.
    
    Returns trigger status.
    """
    current_app.logger.info(f'Manual job trigger requested: job_id={job_id}')
    
    if scheduler is None or not scheduler.running:
        return jsonify({
            'error': 'Scheduler not running'
        }), 503
    
    job = scheduler.get_job(job_id)
    if job is None:
        return jsonify({
            'error': 'Job not found'
        }), 404
    
    try:
        job.modify(next_run_time=datetime.now())
        return jsonify({
            'status': 'triggered',
            'job_id': job_id,
            'triggered_at': datetime.now().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f'Failed to trigger job {job_id}: {e}')
        return jsonify({
            'error': f'Failed to trigger job: {str(e)}'
        }), 500


@bp.route('/cache/stats')
def cache_stats():
    """
    Get cache statistics.
    
    Returns detailed cache information for all cache types.
    """
    # TODO: Implement with service layer (Issue #130)
    return jsonify({
        'geocoding': {
            'entries': 0,  # TODO: Count entries
            'size_bytes': 0,
            'hit_rate': 0.0,
            'last_updated': None
        },
        'weather': {
            'entries': 0,
            'size_bytes': 0,
            'hit_rate': 0.0,
            'last_updated': None
        },
        'route_groups': {
            'entries': 0,
            'size_bytes': 0,
            'hit_rate': 0.0,
            'last_updated': None
        }
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
    
    # TODO: Implement with service layer (Issue #130)
    return jsonify({
        'status': 'cleared',
        'cache_type': cache_type,
        'cleared_at': datetime.now().isoformat(),
        'entries_removed': 0  # TODO: Return actual count
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
    # TODO: Implement with service layer (Issue #130)
    return jsonify({
        'period': '30d',
        'activities': {
            'total': 0,
            'by_type': {}
        },
        'routes': {
            'total': 0,
            'most_used': []
        },
        'performance': {
            'avg_speed': 0.0,
            'avg_power': 0.0,
            'total_distance': 0.0,
            'total_elevation': 0.0
        }
    })


@bp.route('/metrics')
def metrics():
    """
    Prometheus-style metrics endpoint.
    
    Returns metrics in Prometheus text format for monitoring.
    """
    # TODO: Implement metrics collection (Issue #137)
    metrics_text = """# HELP ride_optimizer_activities_total Total number of activities
# TYPE ride_optimizer_activities_total counter
ride_optimizer_activities_total 0

# HELP ride_optimizer_routes_total Total number of routes
# TYPE ride_optimizer_routes_total gauge
ride_optimizer_routes_total 0

# HELP ride_optimizer_cache_entries Cache entries by type
# TYPE ride_optimizer_cache_entries gauge
ride_optimizer_cache_entries{type="geocoding"} 0
ride_optimizer_cache_entries{type="weather"} 0
ride_optimizer_cache_entries{type="route_groups"} 0
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
