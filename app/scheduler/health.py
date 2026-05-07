"""
System Health Monitoring

Provides health checks for system components and data freshness monitoring.
Supports degraded mode detection and last-known-good fallback behavior.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from app.models import db, AnalysisSnapshot, JobHistory

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    message: str
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SystemHealth:
    """Overall system health status."""
    overall_status: str  # 'healthy', 'degraded', 'unhealthy'
    checks: List[HealthCheck] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def checks_passed(self) -> int:
        """Count of healthy checks."""
        return sum(1 for c in self.checks if c.status == 'healthy')
    
    @property
    def checks_failed(self) -> int:
        """Count of unhealthy checks."""
        return sum(1 for c in self.checks if c.status == 'unhealthy')
    
    @property
    def checks_degraded(self) -> int:
        """Count of degraded checks."""
        return sum(1 for c in self.checks if c.status == 'degraded')
    
    @property
    def warnings(self) -> List[str]:
        """List of warning messages from degraded/unhealthy checks."""
        return [
            f"{c.name}: {c.message}"
            for c in self.checks
            if c.status in ('degraded', 'unhealthy')
        ]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'overall_status': self.overall_status,
            'checks_passed': self.checks_passed,
            'checks_failed': self.checks_failed,
            'checks_degraded': self.checks_degraded,
            'timestamp': self.timestamp.isoformat(),
            'checks': [
                {
                    'name': c.name,
                    'status': c.status,
                    'message': c.message,
                    'details': c.details,
                    'timestamp': c.timestamp.isoformat()
                }
                for c in self.checks
            ]
        }


class HealthChecker:
    """System health checker with freshness monitoring."""
    
    # Freshness windows (in hours)
    ANALYSIS_FRESHNESS_WINDOW = 26  # Daily + 2 hour buffer
    WEATHER_FRESHNESS_WINDOW = 7  # 6 hours + 1 hour buffer
    JOB_FAILURE_THRESHOLD = 3  # Max consecutive failures before unhealthy
    
    def __init__(self):
        """Initialize health checker."""
        self.checks: List[HealthCheck] = []
    
    def check_all(self) -> SystemHealth:
        """Run all health checks and return overall status.
        
        Returns:
            SystemHealth object with all check results
        """
        self.checks = []
        
        # Run all checks
        self.check_database()
        self.check_cache_files()
        self.check_disk_space()
        self.check_analysis_freshness()
        self.check_recent_job_failures()
        
        # Determine overall status
        if any(c.status == 'unhealthy' for c in self.checks):
            overall_status = 'unhealthy'
        elif any(c.status == 'degraded' for c in self.checks):
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        return SystemHealth(
            overall_status=overall_status,
            checks=self.checks
        )
    
    def check_database(self) -> HealthCheck:
        """Check database connectivity and integrity."""
        try:
            # Try a simple query
            db.session.execute(db.text('SELECT 1'))
            db.session.commit()
            
            check = HealthCheck(
                name='database',
                status='healthy',
                message='Database connection healthy'
            )
        except Exception as e:
            check = HealthCheck(
                name='database',
                status='unhealthy',
                message=f'Database connection failed: {str(e)}'
            )
            logger.error(f"Database health check failed: {e}")
        
        self.checks.append(check)
        return check
    
    def check_cache_files(self) -> HealthCheck:
        """Check cache directory accessibility."""
        try:
            cache_dir = Path('cache')
            
            if not cache_dir.exists():
                check = HealthCheck(
                    name='cache_files',
                    status='unhealthy',
                    message='Cache directory does not exist'
                )
            elif not cache_dir.is_dir():
                check = HealthCheck(
                    name='cache_files',
                    status='unhealthy',
                    message='Cache path is not a directory'
                )
            else:
                # Count cache files
                cache_files = list(cache_dir.glob('*.json'))
                check = HealthCheck(
                    name='cache_files',
                    status='healthy',
                    message='Cache directory accessible',
                    details={'cache_file_count': len(cache_files)}
                )
        except Exception as e:
            check = HealthCheck(
                name='cache_files',
                status='unhealthy',
                message=f'Cache directory check failed: {str(e)}'
            )
            logger.error(f"Cache files health check failed: {e}")
        
        self.checks.append(check)
        return check
    
    def check_disk_space(self) -> HealthCheck:
        """Check available disk space (important for Raspberry Pi)."""
        try:
            import shutil
            
            # Check disk space for current directory
            total, used, free = shutil.disk_usage('.')
            
            # Calculate percentages
            free_percent = (free / total) * 100
            
            # Thresholds
            if free_percent < 5:
                status = 'unhealthy'
                message = f'Critical: Only {free_percent:.1f}% disk space remaining'
            elif free_percent < 15:
                status = 'degraded'
                message = f'Warning: Only {free_percent:.1f}% disk space remaining'
            else:
                status = 'healthy'
                message = f'Disk space healthy ({free_percent:.1f}% free)'
            
            check = HealthCheck(
                name='disk_space',
                status=status,
                message=message,
                details={
                    'total_gb': round(total / (1024**3), 2),
                    'used_gb': round(used / (1024**3), 2),
                    'free_gb': round(free / (1024**3), 2),
                    'free_percent': round(free_percent, 1)
                }
            )
        except Exception as e:
            check = HealthCheck(
                name='disk_space',
                status='degraded',
                message=f'Could not check disk space: {str(e)}'
            )
            logger.error(f"Disk space health check failed: {e}")
        
        self.checks.append(check)
        return check
    
    def check_analysis_freshness(self) -> HealthCheck:
        """Check if analysis data is fresh enough."""
        try:
            # Get most recent analysis snapshot
            latest_snapshot = AnalysisSnapshot.query.order_by(
                AnalysisSnapshot.analysis_date.desc()
            ).first()
            
            if not latest_snapshot:
                check = HealthCheck(
                    name='analysis_freshness',
                    status='unhealthy',
                    message='No analysis snapshots found'
                )
            else:
                now = datetime.now(timezone.utc)
                age_hours = (now - latest_snapshot.analysis_date).total_seconds() / 3600
                
                if age_hours > self.ANALYSIS_FRESHNESS_WINDOW * 2:
                    status = 'unhealthy'
                    message = f'Analysis data very stale ({age_hours:.1f} hours old)'
                elif age_hours > self.ANALYSIS_FRESHNESS_WINDOW:
                    status = 'degraded'
                    message = f'Analysis data stale ({age_hours:.1f} hours old)'
                else:
                    status = 'healthy'
                    message = f'Analysis data fresh ({age_hours:.1f} hours old)'
                
                check = HealthCheck(
                    name='analysis_freshness',
                    status=status,
                    message=message,
                    details={
                        'snapshot_id': latest_snapshot.id,
                        'analysis_date': latest_snapshot.analysis_date.isoformat(),
                        'age_hours': round(age_hours, 1),
                        'snapshot_status': latest_snapshot.status
                    }
                )
        except Exception as e:
            check = HealthCheck(
                name='analysis_freshness',
                status='degraded',
                message=f'Could not check analysis freshness: {str(e)}'
            )
            logger.error(f"Analysis freshness health check failed: {e}")
        
        self.checks.append(check)
        return check
    
    def check_recent_job_failures(self) -> HealthCheck:
        """Check for recent job failures."""
        try:
            # Get recent failed jobs (last 24 hours)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
            failed_jobs = JobHistory.query.filter(
                JobHistory.status == 'failed',
                JobHistory.started_at >= cutoff
            ).all()
            
            if not failed_jobs:
                check = HealthCheck(
                    name='recent_job_failures',
                    status='healthy',
                    message='No recent job failures'
                )
            else:
                # Group by job type
                failures_by_type = {}
                for job in failed_jobs:
                    failures_by_type[job.job_type] = failures_by_type.get(job.job_type, 0) + 1
                
                # Check if any job type has too many failures
                max_failures = max(failures_by_type.values())
                
                if max_failures >= self.JOB_FAILURE_THRESHOLD:
                    status = 'unhealthy'
                    message = f'{len(failed_jobs)} job failures in last 24h (max {max_failures} for one type)'
                else:
                    status = 'degraded'
                    message = f'{len(failed_jobs)} job failures in last 24h'
                
                check = HealthCheck(
                    name='recent_job_failures',
                    status=status,
                    message=message,
                    details={
                        'total_failures': len(failed_jobs),
                        'failures_by_type': failures_by_type
                    }
                )
        except Exception as e:
            check = HealthCheck(
                name='recent_job_failures',
                status='degraded',
                message=f'Could not check job failures: {str(e)}'
            )
            logger.error(f"Job failures health check failed: {e}")
        
        self.checks.append(check)
        return check
    
    def get_last_known_good_snapshot(self) -> Optional[AnalysisSnapshot]:
        """Get the most recent successful analysis snapshot.
        
        Used for degraded mode fallback when current analysis fails.
        
        Returns:
            Most recent completed AnalysisSnapshot, or None if none exist
        """
        return AnalysisSnapshot.query.filter_by(
            status='completed'
        ).order_by(
            AnalysisSnapshot.analysis_date.desc()
        ).first()

# Made with Bob
