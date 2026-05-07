"""
# Scheduler Module Documentation

Background job scheduling, execution tracking, and system health monitoring for the ride optimizer platform.

## Overview

The scheduler module provides:
- **Scheduled job execution** using APScheduler
- **Job history tracking** in SQLite database
- **System health monitoring** with freshness windows
- **Degraded mode support** for failed upstream integrations
- **Last-known-good fallback** behavior
- **Resource management** (cache cleanup, log rotation)

## Architecture

```
app/scheduler/
├── __init__.py          # Package exports
├── scheduler.py         # APScheduler configuration
├── jobs.py             # Job implementations
├── health.py           # Health monitoring
└── README.md           # This file
```

## Scheduled Jobs

### Daily Analysis (2 AM UTC)
- Fetches latest activities from Strava
- Performs full route analysis
- Creates AnalysisSnapshot record
- **Degraded mode**: Uses cached activities if Strava API fails

### Weather Refresh (Every 6 hours)
- Updates weather forecasts for active routes
- **Degraded mode**: Keeps existing cached weather data

### Cache Cleanup (3 AM UTC daily)
- Removes old cache files based on retention policy
- Keeps last-known-good snapshots
- **Retention periods**:
  - Analysis snapshots: 30 days
  - Weather cache: 7 days
  - Route similarity cache: 90 days
  - Geocoding cache: Indefinite

### Log Rotation (Sunday 4 AM UTC)
- Compresses logs older than 7 days
- Deletes logs older than 30 days
- Prevents disk space issues on Raspberry Pi

### Health Check (Every 15 minutes)
- Monitors database connectivity
- Checks cache file accessibility
- Monitors disk space
- Validates data freshness
- Tracks recent job failures

## Usage

### Initialize Scheduler

```python
from app import create_app
from app.scheduler import init_scheduler, start_scheduler

app = create_app()

# Initialize and start scheduler
start_scheduler(app)
```

### Get Scheduler Status

```python
from app.scheduler import get_scheduler_status

status = get_scheduler_status()
# Returns:
# {
#     'running': True,
#     'jobs': [
#         {
#             'id': 'daily_analysis',
#             'name': 'Daily Analysis Refresh',
#             'next_run': '2026-05-07T02:00:00+00:00',
#             'trigger': 'cron[hour='2', minute='0']'
#         },
#         ...
#     ],
#     'job_count': 5
# }
```

### Check System Health

```python
from app.scheduler.health import HealthChecker

checker = HealthChecker()
health = checker.check_all()

print(f"Overall status: {health.overall_status}")
print(f"Checks passed: {health.checks_passed}/{len(health.checks)}")

for check in health.checks:
    print(f"{check.name}: {check.status} - {check.message}")
```

### Get Last Known Good Snapshot

```python
from app.scheduler.health import HealthChecker

checker = HealthChecker()
snapshot = checker.get_last_known_good_snapshot()

if snapshot:
    print(f"Last good analysis: {snapshot.analysis_date}")
    print(f"Activities: {snapshot.activities_count}")
    print(f"Route groups: {snapshot.route_groups_count}")
```

## Health Monitoring

### Health Check Types

1. **Database Connectivity**
   - Status: healthy | unhealthy
   - Checks: Simple query execution

2. **Cache Files**
   - Status: healthy | unhealthy
   - Checks: Directory accessibility, file count

3. **Disk Space**
   - Status: healthy | degraded | unhealthy
   - Thresholds:
     - Healthy: >15% free
     - Degraded: 5-15% free
     - Unhealthy: <5% free

4. **Analysis Freshness**
   - Status: healthy | degraded | unhealthy
   - Freshness window: 26 hours (daily + 2h buffer)
   - Thresholds:
     - Healthy: <26 hours old
     - Degraded: 26-52 hours old
     - Unhealthy: >52 hours old

5. **Recent Job Failures**
   - Status: healthy | degraded | unhealthy
   - Window: Last 24 hours
   - Thresholds:
     - Healthy: 0 failures
     - Degraded: 1-2 failures
     - Unhealthy: ≥3 failures for any job type

### Overall Status Determination

- **Healthy**: All checks pass
- **Degraded**: At least one check degraded, none unhealthy
- **Unhealthy**: At least one check unhealthy

## Degraded Mode Behavior

When upstream services fail, the system enters degraded mode:

### Strava API Failure
- Use cached activities
- Mark snapshot as 'degraded'
- Continue with analysis using available data
- Display warning in UI

### Geocoding Failure
- Use existing location data
- Skip geocoding for new routes
- Continue with route analysis
- Background geocoding will retry later

### Weather API Failure
- Keep existing cached weather data
- Mark weather data as stale
- Display "last updated" timestamp
- Continue with route recommendations

### TrainerRoad API Failure
- Skip workout integration
- Continue with route-based recommendations
- Display notice about missing workout data

## Job History Tracking

All jobs record execution history in the `job_history` table:

```python
from app.models import JobHistory

# Query recent jobs
recent_jobs = JobHistory.query.order_by(
    JobHistory.started_at.desc()
).limit(10).all()

for job in recent_jobs:
    print(f"{job.job_type}: {job.status}")
    print(f"  Duration: {job.duration_seconds}s")
    if job.error_message:
        print(f"  Error: {job.error_message}")
```

### Job Status Values

- `pending`: Job queued but not started
- `running`: Job currently executing
- `completed`: Job finished successfully
- `failed`: Job encountered an error

## Configuration

### Scheduler Settings

Configured in `app/scheduler/scheduler.py`:

```python
job_defaults = {
    'coalesce': True,        # Combine missed runs
    'max_instances': 1,      # One instance per job
    'misfire_grace_time': 300  # 5 min grace period
}
```

### Freshness Windows

Configured in `app/scheduler/health.py`:

```python
ANALYSIS_FRESHNESS_WINDOW = 26  # hours
WEATHER_FRESHNESS_WINDOW = 7    # hours
JOB_FAILURE_THRESHOLD = 3       # consecutive failures
```

### Retention Policies

Configured in `app/scheduler/jobs.py`:

```python
retention_days = {
    'activities_cache': 30,
    'weather_cache': 7,
    'route_similarity_cache': 90,
    'route_groups_cache': 30
}
```

## API Endpoints

The scheduler exposes status via API endpoints (defined in `app/routes/api.py`):

### GET /api/scheduler/status
Returns scheduler status and job list.

### GET /api/health
Returns system health status.

### POST /api/scheduler/jobs/{job_id}/run
Manually trigger a job (admin only).

## Testing

### Unit Tests

```bash
pytest tests/test_scheduler.py -v
```

### Integration Tests

```bash
pytest tests/test_scheduler_integration.py -v
```

### Manual Testing

```python
# Test job execution
from app.scheduler.jobs import run_daily_analysis

run_daily_analysis()  # Runs synchronously for testing
```

## Monitoring

### Log Files

- **app.log**: General application logs
- **security_audit.log**: Security-related events
- Job execution logged with INFO level
- Failures logged with ERROR level

### Metrics to Monitor

1. **Job Success Rate**: Track failed vs completed jobs
2. **Job Duration**: Monitor for performance degradation
3. **Disk Space**: Alert when <15% free
4. **Analysis Freshness**: Alert when >26 hours old
5. **Health Check Failures**: Alert on unhealthy status

## Troubleshooting

### Scheduler Not Starting

```python
# Check scheduler status
from app.scheduler import scheduler

if scheduler is None:
    print("Scheduler not initialized")
elif not scheduler.running:
    print("Scheduler initialized but not running")
    scheduler.start()
```

### Jobs Not Running

1. Check scheduler is running: `scheduler.running`
2. Check job is registered: `scheduler.get_jobs()`
3. Check job history for errors: `JobHistory.query.filter_by(status='failed')`
4. Check logs for exceptions

### Degraded Mode Not Working

1. Verify last-known-good snapshot exists
2. Check health status: `HealthChecker().check_all()`
3. Verify cache files are accessible
4. Check error messages in job history

### Disk Space Issues

1. Run cache cleanup manually: `run_cache_cleanup()`
2. Run log rotation manually: `run_log_rotation()`
3. Check retention policies are appropriate
4. Consider increasing disk space

## Dependencies

- **APScheduler**: Background job scheduling
- **Flask-SQLAlchemy**: Database integration
- **SQLAlchemy**: Job store backend

Install with:
```bash
pip install apscheduler flask-sqlalchemy
```

## Best Practices

1. **Always use app context** when accessing database in jobs
2. **Record all job executions** in JobHistory
3. **Handle failures gracefully** - don't crash the app
4. **Log important events** for monitoring
5. **Test degraded mode** behavior regularly
6. **Monitor disk space** on Raspberry Pi
7. **Keep retention policies** appropriate for available storage
8. **Use last-known-good** snapshots for critical features

## Future Enhancements

- [ ] Email/SMS alerts for critical failures
- [ ] Prometheus metrics export
- [ ] Job retry with exponential backoff
- [ ] Dynamic job scheduling based on usage patterns
- [ ] Distributed job execution for scalability
- [ ] Job dependency management
- [ ] Real-time job progress updates via WebSocket
"""