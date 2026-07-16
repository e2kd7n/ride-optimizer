#!/usr/bin/env python3
"""
Daily Analysis Cron Job — thin HTTP client.

Triggers the running app's /api/analyze endpoint and polls for completion
instead of importing the analysis stack in-process. The old version loaded
a second full copy of numpy/sklearn/folium plus the entire activity history
on the host, outside the container's memory limit — the main cause of the
Pi's swap spikes (#498).

Run via cron: 0 2 * * * /path/to/cron/daily_analysis.py
"""

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.json_storage import JSONStorage
from src.config_manager import ConfigManager
from src.logging_config import PIISanitizingFilter
from src.ntfy_notifier import NtfyNotifier
from src.secure_logger import SecureLogger

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
# basicConfig handlers bypass setup_logging(), so sanitize at the handler here
for _handler in logging.getLogger().handlers:
    _handler.addFilter(PIISanitizingFilter())
logger = SecureLogger(__name__)

BASE_URL = os.getenv('RIDE_OPTIMIZER_URL',
                     f"http://127.0.0.1:{os.getenv('APP_PORT', '8083')}")
POLL_INTERVAL_SECONDS = int(os.getenv('ANALYSIS_POLL_INTERVAL', '30'))
TIMEOUT_SECONDS = int(os.getenv('ANALYSIS_TIMEOUT', str(3 * 60 * 60)))


def _record_job(storage, status, start_time, result=None, error=None):
    """Append a job record to job_history.json (same format as before)."""
    job_record = {
        'job_type': 'daily_analysis',
        'status': status,
        'started_at': start_time.isoformat(),
        'completed_at': datetime.now().isoformat(),
        'duration_seconds': (datetime.now() - start_time).total_seconds(),
    }
    if result is not None:
        job_record['result'] = {
            'activities_count': result.get('activities_count', 0),
            'route_groups_count': result.get('route_groups_count', 0),
            'long_rides_count': result.get('long_rides_count', 0),
            'degraded_reason': result.get('degraded_reason'),
        }
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
    """Trigger analysis over HTTP and wait for it to finish."""
    logger.info("=" * 60)
    logger.info(f"Starting daily analysis cron job (via {BASE_URL})")
    logger.info("=" * 60)

    start_time = datetime.now()
    storage = JSONStorage()

    try:
        config = ConfigManager.get_instance()
        notifier = NtfyNotifier(config.get('notifications.ntfy'))
    except Exception as e:
        logger.warning(f"Failed to initialize notifier: {e}")
        notifier = None

    try:
        session = requests.Session()

        # CSRF: fetch a token (sets the session cookie the token is bound to)
        resp = session.get(f"{BASE_URL}/api/csrf-token", timeout=30)
        resp.raise_for_status()
        csrf_token = resp.json()['csrf_token']

        # Trigger the analysis job. fetch_new=True matches the old in-process
        # behavior (run_full_analysis with skip_strava_fetch=False).
        resp = session.post(
            f"{BASE_URL}/api/analyze",
            json={'fetch_new': True, 'force_refresh': False},
            headers={'X-CSRFToken': csrf_token},
            timeout=60,
        )
        if resp.status_code == 409:
            logger.warning("Analysis already running — skipping this cron run")
            return 0
        resp.raise_for_status()
        logger.info("Analysis started, polling for completion...")

        # Poll until the job leaves the 'running' state
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Analysis still running after {TIMEOUT_SECONDS}s")
            time.sleep(POLL_INTERVAL_SECONDS)
            status_resp = session.get(f"{BASE_URL}/api/analyze/status",
                                      timeout=30)
            status_resp.raise_for_status()
            snapshot = status_resp.json()
            state = snapshot.get('status')
            if state == 'running':
                continue
            if state == 'done':
                result = snapshot.get('result') or {}
                break
            raise RuntimeError(
                f"Analysis ended with status '{state}': "
                f"{snapshot.get('label') or snapshot.get('result')}")

        job_record = _record_job(
            storage,
            'completed' if result.get('success', True) else 'degraded',
            start_time, result=result)

        status = storage.read('status.json', default={})
        status['last_analysis'] = datetime.now().isoformat()
        status['has_data'] = True
        storage.write('status.json', status)

        logger.info(f"Analysis completed successfully in "
                    f"{job_record['duration_seconds']:.1f}s")
        logger.info(f"Activities: {job_record['result']['activities_count']}")
        logger.info(f"Route groups: {job_record['result']['route_groups_count']}")
        return 0

    except Exception as e:
        logger.error(f"Daily analysis failed: {e}", exc_info=True)
        if notifier:
            notifier.send_cron_failure_alert('daily_analysis', str(e))
        _record_job(storage, 'failed', start_time, error=str(e))
        return 1


if __name__ == '__main__':
    sys.exit(main())
