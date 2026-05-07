#!/usr/bin/env python3
"""
System Health Check Cron Job
Replaces APScheduler job for Smart Static architecture.

Run via cron: */15 * * * * /path/to/cron/system_health.py
"""

import sys
import logging
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.json_storage import JSONStorage

# Configure logging
log_dir = project_root / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'cron_system_health.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_disk_space():
    """Check available disk space."""
    try:
        usage = shutil.disk_usage(project_root)
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        percent_used = (usage.used / usage.total) * 100
        
        return {
            'status': 'healthy' if percent_used < 90 else 'warning',
            'free_gb': round(free_gb, 2),
            'total_gb': round(total_gb, 2),
            'percent_used': round(percent_used, 1)
        }
    except Exception as e:
        logger.error(f"Failed to check disk space: {e}")
        return {'status': 'error', 'error': str(e)}


def check_cache_files():
    """Check cache file accessibility."""
    try:
        cache_dir = project_root / 'cache'
        if not cache_dir.exists():
            return {'status': 'warning', 'message': 'Cache directory not found'}
        
        cache_files = list(cache_dir.glob('*.json'))
        return {
            'status': 'healthy',
            'file_count': len(cache_files),
            'total_size_mb': round(sum(f.stat().st_size for f in cache_files) / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"Failed to check cache files: {e}")
        return {'status': 'error', 'error': str(e)}


def check_last_analysis():
    """Check when last analysis was run."""
    try:
        storage = JSONStorage()
        status = storage.read('status.json', default={})
        last_analysis = status.get('last_analysis')
        
        if not last_analysis:
            return {'status': 'warning', 'message': 'No analysis run yet'}
        
        last_time = datetime.fromisoformat(last_analysis)
        age_hours = (datetime.now() - last_time).total_seconds() / 3600
        
        return {
            'status': 'healthy' if age_hours < 48 else 'warning',
            'last_run': last_analysis,
            'age_hours': round(age_hours, 1)
        }
    except Exception as e:
        logger.error(f"Failed to check last analysis: {e}")
        return {'status': 'error', 'error': str(e)}


def check_api_status():
    """Check if API is accessible."""
    try:
        import requests
        response = requests.get('http://localhost:8083/api/status', timeout=5)
        
        if response.status_code == 200:
            return {'status': 'healthy', 'response_time_ms': response.elapsed.total_seconds() * 1000}
        else:
            return {'status': 'warning', 'http_status': response.status_code}
    except Exception as e:
        # API might not be running, which is OK for cron-based architecture
        return {'status': 'info', 'message': 'API not running (expected for cron mode)'}


def main():
    """Run system health checks."""
    logger.info("=" * 60)
    logger.info("Starting system health check")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    storage = JSONStorage()
    
    try:
        # Run all health checks
        checks = {
            'disk_space': check_disk_space(),
            'cache_files': check_cache_files(),
            'last_analysis': check_last_analysis(),
            'api_status': check_api_status()
        }
        
        # Determine overall status
        statuses = [check['status'] for check in checks.values()]
        if 'error' in statuses:
            overall_status = 'unhealthy'
        elif 'warning' in statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        # Record health check
        health_record = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'checks': checks,
            'duration_seconds': (datetime.now() - start_time).total_seconds()
        }
        
        # Save health status
        storage.write('health_status.json', health_record)
        
        # Record job execution
        job_record = {
            'job_type': 'system_health',
            'status': 'completed',
            'started_at': start_time.isoformat(),
            'completed_at': datetime.now().isoformat(),
            'duration_seconds': health_record['duration_seconds'],
            'result': {
                'overall_status': overall_status,
                'checks_run': len(checks)
            }
        }
        
        # Save job history
        history = storage.read('job_history.json', default={'jobs': []})
        history['jobs'].append(job_record)
        history['jobs'] = history['jobs'][-100:]
        storage.write('job_history.json', history)
        
        logger.info(f"Health check completed: {overall_status}")
        for check_name, check_result in checks.items():
            logger.info(f"  {check_name}: {check_result['status']}")
        
        return 0 if overall_status == 'healthy' else 1
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
