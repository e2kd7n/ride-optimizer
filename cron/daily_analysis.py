#!/usr/bin/env python3
"""
Daily Analysis Cron Job
Replaces APScheduler job for Smart Static architecture.

Run via cron: 0 2 * * * /path/to/cron/daily_analysis.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.json_storage import JSONStorage
from app.services.analysis_service import AnalysisService

# Configure logging
log_dir = project_root / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'cron_daily_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Run daily analysis refresh."""
    logger.info("=" * 60)
    logger.info("Starting daily analysis cron job")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    storage = JSONStorage()
    
    try:
        # Initialize services
        config = Config()
        analysis_service = AnalysisService(config)
        
        # Run full analysis
        logger.info("Running full analysis...")
        result = analysis_service.run_full_analysis(
            fetch_new_activities=True,
            force_refresh=False
        )
        
        # Record job execution
        job_record = {
            'job_type': 'daily_analysis',
            'status': 'completed' if result.get('success') else 'degraded',
            'started_at': start_time.isoformat(),
            'completed_at': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'result': {
                'activities_count': result.get('activities_count', 0),
                'route_groups_count': result.get('route_groups_count', 0),
                'long_rides_count': result.get('long_rides_count', 0),
                'degraded_reason': result.get('degraded_reason')
            }
        }
        
        # Save job history
        history = storage.read('job_history.json', default={'jobs': []})
        history['jobs'].append(job_record)
        
        # Keep only last 100 job records
        history['jobs'] = history['jobs'][-100:]
        storage.write('job_history.json', history)
        
        # Update status
        status = storage.read('status.json', default={})
        status['last_analysis'] = datetime.now().isoformat()
        status['has_data'] = True
        storage.write('status.json', status)
        
        logger.info(f"Analysis completed successfully in {job_record['duration_seconds']:.1f}s")
        logger.info(f"Activities: {job_record['result']['activities_count']}")
        logger.info(f"Route groups: {job_record['result']['route_groups_count']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Daily analysis failed: {e}", exc_info=True)
        
        # Record failure
        job_record = {
            'job_type': 'daily_analysis',
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
