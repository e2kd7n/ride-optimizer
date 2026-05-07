"""
APScheduler Configuration and Initialization

Configures APScheduler with SQLAlchemy job store for persistent job scheduling.
Integrates with Flask application context for database access.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from flask import Flask

from app.models import db

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[BackgroundScheduler] = None


def init_scheduler(app: Flask) -> BackgroundScheduler:
    """Initialize APScheduler with Flask app context.
    
    Args:
        app: Flask application instance
        
    Returns:
        Configured BackgroundScheduler instance
        
    Example:
        >>> app = create_app()
        >>> with app.app_context():
        >>>     scheduler = init_scheduler(app)
        >>>     scheduler.start()
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return scheduler
    
    # Must be called within app context to access db.engine
    with app.app_context():
        # Configure job stores
        jobstores = {
            'default': SQLAlchemyJobStore(
                engine=db.engine,
                tablename='apscheduler_jobs'
            )
        }
    
    # Configure executors
    executors = {
        'default': ThreadPoolExecutor(max_workers=4)
    }
    
    # Job defaults
    job_defaults = {
        'coalesce': True,  # Combine missed runs into one
        'max_instances': 1,  # Only one instance of each job at a time
        'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
    }
    
    # Create scheduler
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )
    
    # Add Flask app context to scheduler
    scheduler.app = app
    
    logger.info("Scheduler initialized successfully")
    
    return scheduler


def start_scheduler(app: Flask) -> None:
    """Start the scheduler and register default jobs.
    
    Args:
        app: Flask application instance
    """
    global scheduler
    
    if scheduler is None:
        scheduler = init_scheduler(app)
    
    if scheduler.running:
        logger.warning("Scheduler already running")
        return
    
    # Import jobs here to avoid circular imports
    from app.scheduler.jobs import (
        run_daily_analysis,
        run_weather_refresh,
        run_cache_cleanup,
        run_log_rotation,
        check_system_health
    )
    
    with app.app_context():
        # Register default jobs
        
        # Daily analysis at 2 AM UTC
        scheduler.add_job(
            func=run_daily_analysis,
            trigger='cron',
            hour=2,
            minute=0,
            id='daily_analysis',
            name='Daily Analysis Refresh',
            replace_existing=True
        )
        
        # Weather refresh every 6 hours
        scheduler.add_job(
            func=run_weather_refresh,
            trigger='cron',
            hour='*/6',
            minute=0,
            id='weather_refresh',
            name='Weather Data Refresh',
            replace_existing=True
        )
        
        # Cache cleanup daily at 3 AM UTC
        scheduler.add_job(
            func=run_cache_cleanup,
            trigger='cron',
            hour=3,
            minute=0,
            id='cache_cleanup',
            name='Cache Cleanup',
            replace_existing=True
        )
        
        # Log rotation weekly on Sunday at 4 AM UTC
        scheduler.add_job(
            func=run_log_rotation,
            trigger='cron',
            day_of_week='sun',
            hour=4,
            minute=0,
            id='log_rotation',
            name='Log Rotation',
            replace_existing=True
        )
        
        # System health check every 15 minutes
        scheduler.add_job(
            func=check_system_health,
            trigger='cron',
            minute='*/15',
            id='health_check',
            name='System Health Check',
            replace_existing=True
        )
        
        # Start scheduler
        scheduler.start()
        logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))
        
        # Log scheduled jobs
        for job in scheduler.get_jobs():
            logger.info(
                "Scheduled job: %s (next run: %s)",
                job.name,
                job.next_run_time
            )


def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global scheduler
    
    if scheduler is None or not scheduler.running:
        logger.warning("Scheduler not running")
        return
    
    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=True)
    logger.info("Scheduler shutdown complete")


def get_scheduler_status() -> dict:
    """Get current scheduler status and job information.
    
    Returns:
        Dictionary with scheduler status and job details
    """
    global scheduler
    
    if scheduler is None:
        return {
            'running': False,
            'jobs': [],
            'error': 'Scheduler not initialized'
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })
    
    return {
        'running': scheduler.running,
        'jobs': jobs,
        'job_count': len(jobs)
    }

# Made with Bob
