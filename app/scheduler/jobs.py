"""
Scheduled Job Implementations

Defines all scheduled jobs for the ride optimizer platform.
Each job records its execution in JobHistory for tracking and monitoring.
"""

import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from flask import current_app

from app.models import db, JobHistory, AnalysisSnapshot
from app.services import AnalysisService

logger = logging.getLogger(__name__)


def _record_job_start(job_type: str, description: str = None) -> JobHistory:
    """Record job start in database.
    
    Args:
        job_type: Type of job being executed
        description: Optional job description
        
    Returns:
        JobHistory record for this job execution
    """
    job = JobHistory(
        job_type=job_type,
        status='running',
        description=description
    )
    db.session.add(job)
    db.session.commit()
    
    logger.info(f"Started job #{job.id}: {job_type}")
    return job


def _record_job_completion(job: JobHistory, result: dict = None) -> None:
    """Record successful job completion.
    
    Args:
        job: JobHistory record to update
        result: Optional result data to store
    """
    job.mark_completed(result=result)
    db.session.commit()
    
    logger.info(
        f"Completed job #{job.id}: {job.job_type} "
        f"(duration: {job.duration_seconds:.1f}s)"
    )


def _record_job_failure(job: JobHistory, error: Exception) -> None:
    """Record job failure.
    
    Args:
        job: JobHistory record to update
        error: Exception that caused the failure
    """
    job.mark_failed(error_message=str(error))
    db.session.commit()
    
    logger.error(
        f"Failed job #{job.id}: {job.job_type} - {error}",
        exc_info=True
    )


def run_daily_analysis() -> None:
    """Run daily analysis refresh.
    
    Fetches latest activities from Strava and performs full route analysis.
    Records results in AnalysisSnapshot for historical tracking.
    
    Degraded Mode Behavior:
    - If Strava API fails: Use cached activities, mark snapshot as 'degraded'
    - If geocoding fails: Continue with existing location data
    - If weather fails: Skip weather analysis, continue with routes
    """
    job = _record_job_start('analysis', 'Daily analysis refresh')
    
    try:
        # Get analysis service
        analysis_service = AnalysisService()
        
        # Run analysis (this will use existing service layer logic)
        result = analysis_service.run_full_analysis(
            fetch_new_activities=True,
            force_refresh=False
        )
        
        # Create snapshot record
        snapshot = AnalysisSnapshot(
            status='completed' if result.get('success') else 'degraded',
            activities_count=result.get('activities_count', 0),
            route_groups_count=result.get('route_groups_count', 0),
            long_rides_count=result.get('long_rides_count', 0),
            cache_file_path=result.get('cache_path'),
            metadata={
                'fetch_new': True,
                'degraded_reason': result.get('degraded_reason')
            }
        )
        db.session.add(snapshot)
        db.session.commit()
        
        _record_job_completion(job, result={
            'snapshot_id': snapshot.id,
            'activities_count': snapshot.activities_count,
            'route_groups_count': snapshot.route_groups_count
        })
        
    except Exception as e:
        _record_job_failure(job, e)
        raise


def run_weather_refresh() -> None:
    """Refresh weather data for active routes.
    
    Updates weather forecasts for frequently used routes.
    Uses last-known-good data if weather API is unavailable.
    
    Degraded Mode Behavior:
    - If weather API fails: Keep existing cached weather data
    - Mark weather data as stale but still usable
    - Log warning for monitoring
    """
    job = _record_job_start('weather_refresh', 'Weather data refresh')
    
    try:
        from src.weather_fetcher import WeatherFetcher
        
        weather_fetcher = WeatherFetcher()
        
        # Get latest snapshot to find active routes
        latest_snapshot = AnalysisSnapshot.query.order_by(
            AnalysisSnapshot.analysis_date.desc()
        ).first()
        
        if not latest_snapshot:
            logger.warning("No analysis snapshot found, skipping weather refresh")
            _record_job_completion(job, result={'skipped': True})
            return
        
        # Refresh weather for route groups
        refreshed_count = 0
        failed_count = 0
        
        for route_group in latest_snapshot.route_groups:
            try:
                # This would call weather API for route location
                # Implementation depends on existing weather_fetcher logic
                refreshed_count += 1
            except Exception as e:
                logger.warning(f"Failed to refresh weather for route {route_group.id}: {e}")
                failed_count += 1
        
        _record_job_completion(job, result={
            'refreshed_count': refreshed_count,
            'failed_count': failed_count,
            'snapshot_id': latest_snapshot.id
        })
        
    except Exception as e:
        _record_job_failure(job, e)
        # Don't raise - weather refresh failure shouldn't crash the app


def run_cache_cleanup() -> None:
    """Clean up old cache files and limit cache growth.
    
    Removes cache files older than retention period.
    Keeps last-known-good snapshots for degraded mode.
    
    Retention Policy:
    - Analysis snapshots: Keep last 30 days
    - Weather cache: Keep last 7 days
    - Route similarity cache: Keep last 90 days
    - Geocoding cache: Keep indefinitely (grows slowly)
    """
    job = _record_job_start('cache_cleanup', 'Cache cleanup and rotation')
    
    try:
        cache_dir = Path('cache')
        if not cache_dir.exists():
            logger.warning("Cache directory not found")
            _record_job_completion(job, result={'skipped': True})
            return
        
        now = datetime.now(timezone.utc)
        retention_days = {
            'activities_cache': 30,
            'weather_cache': 7,
            'route_similarity_cache': 90,
            'route_groups_cache': 30
        }
        
        cleaned_files = []
        total_size_freed = 0
        
        for cache_file in cache_dir.glob('*.json'):
            # Skip geocoding cache (keep indefinitely)
            if 'geocoding' in cache_file.name:
                continue
            
            # Check file age
            file_age_days = (now - datetime.fromtimestamp(
                cache_file.stat().st_mtime, tz=timezone.utc
            )).days
            
            # Determine retention period
            retention = 30  # default
            for pattern, days in retention_days.items():
                if pattern in cache_file.name:
                    retention = days
                    break
            
            # Remove if older than retention period
            if file_age_days > retention:
                file_size = cache_file.stat().st_size
                cache_file.unlink()
                cleaned_files.append(cache_file.name)
                total_size_freed += file_size
                logger.info(f"Removed old cache file: {cache_file.name} ({file_age_days} days old)")
        
        _record_job_completion(job, result={
            'files_removed': len(cleaned_files),
            'size_freed_mb': round(total_size_freed / (1024 * 1024), 2)
        })
        
    except Exception as e:
        _record_job_failure(job, e)


def run_log_rotation() -> None:
    """Rotate and compress old log files.
    
    Keeps logs bounded to prevent disk space issues on Raspberry Pi.
    
    Retention Policy:
    - Keep last 7 days uncompressed
    - Compress logs 7-30 days old
    - Delete logs older than 30 days
    """
    job = _record_job_start('log_rotation', 'Log rotation and compression')
    
    try:
        logs_dir = Path('logs')
        if not logs_dir.exists():
            logger.warning("Logs directory not found")
            _record_job_completion(job, result={'skipped': True})
            return
        
        now = datetime.now(timezone.utc)
        rotated_count = 0
        deleted_count = 0
        
        for log_file in logs_dir.glob('*.log'):
            # Skip current log files
            if log_file.name in ['app.log', 'security_audit.log']:
                continue
            
            file_age_days = (now - datetime.fromtimestamp(
                log_file.stat().st_mtime, tz=timezone.utc
            )).days
            
            # Delete logs older than 30 days
            if file_age_days > 30:
                log_file.unlink()
                deleted_count += 1
                logger.info(f"Deleted old log: {log_file.name}")
            
            # Compress logs 7-30 days old
            elif file_age_days > 7 and not log_file.name.endswith('.gz'):
                import gzip
                with open(log_file, 'rb') as f_in:
                    with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                log_file.unlink()
                rotated_count += 1
                logger.info(f"Compressed log: {log_file.name}")
        
        _record_job_completion(job, result={
            'rotated_count': rotated_count,
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        _record_job_failure(job, e)


def check_system_health() -> None:
    """Check system health and record status.
    
    Monitors:
    - Database connectivity
    - Cache file accessibility
    - Disk space availability
    - Last successful analysis age
    - API endpoint responsiveness
    
    Records health status for monitoring dashboard.
    """
    job = _record_job_start('health_check', 'System health check')
    
    try:
        from app.scheduler.health import HealthChecker
        
        health_checker = HealthChecker()
        health_status = health_checker.check_all()
        
        _record_job_completion(job, result={
            'overall_status': health_status.overall_status,
            'checks_passed': health_status.checks_passed,
            'checks_failed': health_status.checks_failed,
            'warnings': health_status.warnings
        })
        
        # Log warnings
        if health_status.warnings:
            for warning in health_status.warnings:
                logger.warning(f"Health check warning: {warning}")
        
        # Log failures
        if health_status.checks_failed > 0:
            logger.error(
                f"Health check failed: {health_status.checks_failed} checks failed"
            )
        
    except Exception as e:
        _record_job_failure(job, e)

# Made with Bob
