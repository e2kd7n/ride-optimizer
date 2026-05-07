#!/usr/bin/env python3
"""
Cache Cleanup Cron Job
Replaces APScheduler job for Smart Static architecture.

Run via cron: 0 3 * * * /path/to/cron/cache_cleanup.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

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
        logging.FileHandler(log_dir / 'cron_cache_cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Clean up old cache files and limit cache growth."""
    logger.info("=" * 60)
    logger.info("Starting cache cleanup cron job")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    storage = JSONStorage()
    
    try:
        cache_dir = project_root / 'cache'
        if not cache_dir.exists():
            logger.warning("Cache directory not found")
            return 0
        
        now = datetime.now(timezone.utc)
        retention_days = {
            'activities_cache': 30,
            'weather_cache': 7,
            'route_similarity_cache': 90,
            'route_groups_cache': 30,
            'job_history': 90
        }
        
        cleaned_files = []
        total_size_freed = 0
        
        for cache_file in cache_dir.glob('*.json'):
            # Skip geocoding cache (keep indefinitely)
            if 'geocoding' in cache_file.name:
                logger.info(f"Skipping geocoding cache: {cache_file.name}")
                continue
            
            # Check file age
            file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime, tz=timezone.utc)
            file_age_days = (now - file_mtime).days
            
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
        
        # Record job execution
        job_record = {
            'job_type': 'cache_cleanup',
            'status': 'completed',
            'started_at': start_time.isoformat(),
            'completed_at': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'result': {
                'files_removed': len(cleaned_files),
                'size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
                'files': cleaned_files
            }
        }
        
        # Save job history
        history = storage.read('job_history.json', default={'jobs': []})
        history['jobs'].append(job_record)
        history['jobs'] = history['jobs'][-100:]
        storage.write('job_history.json', history)
        
        logger.info(f"Cache cleanup completed in {job_record['duration_seconds']:.1f}s")
        logger.info(f"Files removed: {len(cleaned_files)}")
        logger.info(f"Space freed: {job_record['result']['size_freed_mb']} MB")
        
        return 0
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}", exc_info=True)
        
        # Record failure
        job_record = {
            'job_type': 'cache_cleanup',
            'status': 'failed',
            'started_at': start_time.isoformat(),
            'completed_at': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'error': str(e)
        }
        
        try:
            history = storage.read('job_history.json', default={'jobs': []})
            history['jobs'].append(job_record)
            history['jobs'] = history['jobs'][-100:]
            storage.write('job_history.json', history)
        except Exception as save_error:
            logger.error(f"Failed to save job history: {save_error}")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
