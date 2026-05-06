"""
Job Scheduler Module

Provides background job scheduling, execution tracking, and reliability features.
Uses APScheduler for job scheduling with SQLAlchemy job store.

Key Features:
- Scheduled refresh execution (daily analysis updates)
- Stage-level job history and outcome tracking
- Freshness windows and stale-data indicators
- Last-known-good snapshot serving
- Degraded mode behavior for failed upstream integrations
- Log and cache growth management

Usage:
    from app.scheduler import scheduler, init_scheduler
    
    # Initialize scheduler with Flask app
    init_scheduler(app)
    
    # Start scheduler
    scheduler.start()
    
    # Add a job
    scheduler.add_job(
        func=my_function,
        trigger='cron',
        hour=2,
        minute=0,
        id='daily_analysis'
    )
"""

from .scheduler import scheduler, init_scheduler
from .jobs import (
    run_daily_analysis,
    run_weather_refresh,
    run_cache_cleanup,
    run_log_rotation,
    check_system_health
)
from .health import HealthChecker, SystemHealth

__all__ = [
    'scheduler',
    'init_scheduler',
    'run_daily_analysis',
    'run_weather_refresh',
    'run_cache_cleanup',
    'run_log_rotation',
    'check_system_health',
    'HealthChecker',
    'SystemHealth'
]

# Made with Bob
