#!/usr/bin/env python3
"""
Weather Refresh Cron Job — thin HTTP client.

Hits the running app's GET /api/weather endpoint (which fetches and caches
weather for the home location server-side) instead of importing the service
stack in-process. The old version also wrote its own incompatible schema
into data/weather_cache.json, clobbering WeatherService's cache format —
going through the API fixes that too (#498).

Run via cron: 0 */6 * * * /path/to/cron/weather_refresh.py
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.json_storage import JSONStorage
from src.logging_config import PIISanitizingFilter
from src.secure_logger import SecureLogger

# Configure logging
log_dir = project_root / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'cron_weather_refresh.log'),
        logging.StreamHandler()
    ]
)
# basicConfig handlers bypass setup_logging(), so sanitize at the handler here
for _handler in logging.getLogger().handlers:
    _handler.addFilter(PIISanitizingFilter())
logger = SecureLogger(__name__)

BASE_URL = os.getenv('RIDE_OPTIMIZER_URL',
                     f"http://127.0.0.1:{os.getenv('APP_PORT', '8083')}")


def _record_job(storage, status, start_time, result=None, error=None):
    """Append a job record to job_history.json (same format as before)."""
    job_record = {
        'job_type': 'weather_refresh',
        'status': status,
        'started_at': start_time.isoformat(),
        'completed_at': datetime.now().isoformat(),
        'duration_seconds': (datetime.now() - start_time).total_seconds(),
    }
    if result is not None:
        job_record['result'] = result
    if error is not None:
        job_record['error'] = error

    try:
        history = storage.read('job_history.json', default={'jobs': []})
        history['jobs'].append(job_record)
        history['jobs'] = history['jobs'][-100:]
        storage.write('job_history.json', history)
    except Exception as save_error:
        logger.error(f"Failed to save job history: {save_error}")
    return job_record


def main():
    """Refresh weather for the home location via the app's API."""
    logger.info("=" * 60)
    logger.info(f"Starting weather refresh cron job (via {BASE_URL})")
    logger.info("=" * 60)

    start_time = datetime.now()
    storage = JSONStorage()

    try:
        # No lat/lon params: the endpoint defaults to the configured home
        # location and populates WeatherService's cache server-side.
        resp = requests.get(f"{BASE_URL}/api/weather", timeout=60)

        if resp.status_code == 400:
            logger.warning("No home location configured, skipping weather refresh")
            return 0
        resp.raise_for_status()

        current = (resp.json() or {}).get('current') or {}
        job_record = _record_job(storage, 'completed', start_time, result={
            'location': 'Home',
            'temperature': current.get('temperature'),
            'comfort_score': current.get('comfort_score'),
        })

        logger.info(f"Weather refresh completed in "
                    f"{job_record['duration_seconds']:.1f}s")
        logger.info(f"Temperature: {job_record['result']['temperature']}°F")
        logger.info(f"Comfort score: {job_record['result']['comfort_score']}/100")
        return 0

    except Exception as e:
        logger.error(f"Weather refresh failed: {e}", exc_info=True)
        _record_job(storage, 'failed', start_time, error=str(e))
        # Don't fail hard - weather refresh is non-critical
        logger.warning("Weather refresh failed but continuing (non-critical)")
        return 0


if __name__ == '__main__':
    sys.exit(main())
