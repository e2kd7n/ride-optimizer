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
# Consecutive status polls allowed to fail (read timeout / connection error)
# before giving up. Under memory pressure the Pi can stall the app process
# for a minute or more mid-analysis; one slow poll used to fail the whole
# run even though the analysis itself went on to finish.
MAX_POLL_ERRORS = int(os.getenv('ANALYSIS_MAX_POLL_ERRORS', '10'))
# Times to re-trigger the analysis when its job state is lost mid-run.
# 'idle' after we started it means the gunicorn worker was replaced (worker
# timeout or OOM kill) and took the in-process analysis thread with it.
MAX_RESTARTS = int(os.getenv('ANALYSIS_MAX_RESTARTS', '1'))
# Upper bound on the nightly multi-source sync (Garmin fetches one GPS track
# per activity, sequentially).
SYNC_TIMEOUT_SECONDS = int(os.getenv('SYNC_TIMEOUT', str(60 * 60)))


def _record_job(storage, status, start_time, result=None, error=None, sync=None):
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
    if sync is not None:
        job_record['sync'] = sync

    try:
        history = storage.read('job_history.json', default={'jobs': []})
        history['jobs'].append(job_record)
        history['jobs'] = history['jobs'][-100:]
        storage.write('job_history.json', history)
    except Exception as save_error:
        logger.error(f"Failed to save job history: {save_error}")
    return job_record


def _csrf_session():
    """A fresh session plus a CSRF token bound to it."""
    session = requests.Session()
    resp = session.get(f"{BASE_URL}/api/csrf-token", timeout=30)
    resp.raise_for_status()
    return session, resp.json()['csrf_token']


def _nightly_sync():
    """Pull new activities from every connected source before analysing (#620).

    Controlled by the Settings toggle "Check for new activities nightly"
    (`nightly_sync`). Never raises: a sync problem is logged and recorded,
    and the analysis still runs on what's cached. Returns a small summary
    dict for job_history, e.g. {'status': 'done', 'new': 3, 'sources': {...}}.
    """
    try:
        session, csrf_token = _csrf_session()
        settings = session.get(f"{BASE_URL}/api/settings", timeout=30)
        settings.raise_for_status()
        if not (settings.json().get('settings') or {}).get('nightly_sync', True):
            logger.info("Nightly sync is turned off in Settings — skipping")
            return {'status': 'disabled'}

        resp = session.post(
            f"{BASE_URL}/api/sync",
            json={'window': 'incremental'},
            headers={'X-CSRFToken': csrf_token},
            timeout=60,
        )
        if resp.status_code == 400 and resp.json().get('status') == 'no_sources':
            logger.info("Nightly sync: no activity source connected — nothing to pull")
            return {'status': 'no_sources'}
        if resp.status_code == 409:
            logger.info("Nightly sync: a fetch is already running — skipping")
            return {'status': 'already_running'}
        resp.raise_for_status()
        logger.info(f"Nightly sync started: {resp.json()}")

        deadline = time.monotonic() + SYNC_TIMEOUT_SECONDS
        poll_errors = 0
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_SECONDS)
            try:
                status = session.get(f"{BASE_URL}/api/sync/status", timeout=30)
                status.raise_for_status()
            except requests.RequestException as poll_error:
                poll_errors += 1
                if poll_errors > MAX_POLL_ERRORS:
                    raise
                logger.warning(f"Sync status poll failed ({poll_errors}), retrying: {poll_error}")
                continue
            poll_errors = 0
            snapshot = status.json()
            if snapshot.get('status') == 'running':
                continue
            result = snapshot.get('result') or {}
            summary = {
                'status': snapshot.get('status'),
                'new': result.get('new', 0),
                'sources': {name: {'status': r.get('status'), 'new': r.get('new'),
                                   'error': r.get('error')}
                            for name, r in (result.get('sources') or {}).items()},
            }
            logger.info(f"Nightly sync finished: {snapshot.get('label')}")
            return summary
        logger.warning("Nightly sync still running at its time limit — continuing")
        return {'status': 'timeout'}
    except Exception as e:
        logger.warning(f"Nightly sync failed: {e}")
        return {'status': 'error', 'error': str(e)[:300]}


def _trigger_analysis():
    """Start an analysis job over HTTP. Returns (session, started).

    started is False when the app answers 409 (already running). Each call
    uses a fresh session so a re-trigger after a worker restart fetches a new
    CSRF token instead of reusing one bound to the old worker's session.
    """
    session, csrf_token = _csrf_session()

    # The nightly sync (#620) already pulled from every connected source,
    # Strava included, so the analysis only reads the cache.
    resp = session.post(
        f"{BASE_URL}/api/analyze",
        json={'fetch_new': False, 'force_refresh': False},
        headers={'X-CSRFToken': csrf_token},
        timeout=60,
    )
    if resp.status_code == 409:
        return session, False
    resp.raise_for_status()
    return session, True


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

    sync_summary = _nightly_sync()

    try:
        session, started = _trigger_analysis()
        if not started:
            logger.warning("Analysis already running — skipping this cron run")
            return 0
        logger.info("Analysis started, polling for completion...")

        # Poll until the job leaves the 'running' state
        deadline = time.monotonic() + TIMEOUT_SECONDS
        poll_errors = 0
        restarts = 0
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Analysis still running after {TIMEOUT_SECONDS}s")
            time.sleep(POLL_INTERVAL_SECONDS)
            try:
                status_resp = session.get(f"{BASE_URL}/api/analyze/status",
                                          timeout=30)
                status_resp.raise_for_status()
            except requests.RequestException as poll_error:
                poll_errors += 1
                if poll_errors > MAX_POLL_ERRORS:
                    raise
                logger.warning(f"Status poll failed ({poll_errors}/"
                               f"{MAX_POLL_ERRORS}), retrying: {poll_error}")
                continue
            poll_errors = 0
            snapshot = status_resp.json()
            state = snapshot.get('status')
            if state == 'running':
                continue
            if state == 'done':
                result = snapshot.get('result') or {}
                break
            if state == 'idle' and restarts < MAX_RESTARTS:
                restarts += 1
                logger.warning("Analysis state lost (gunicorn worker "
                               "restarted?) — re-triggering "
                               f"({restarts}/{MAX_RESTARTS})")
                # A 409 here means something else already started a run;
                # either way there is now a job to poll.
                session, _ = _trigger_analysis()
                continue
            raise RuntimeError(
                f"Analysis ended with status '{state}': "
                f"{snapshot.get('label') or snapshot.get('result')}")

        # The endpoint marks the job 'done' even when run_full_analysis
        # caught an error internally and returned an error payload (e.g.
        # Strava auth failure) — surface that as a real failure instead of
        # logging a bogus "completed successfully" with 0 activities.
        if result.get('status') == 'error':
            raise RuntimeError(
                f"Analysis reported an error: {result.get('message', result)}")

        errors = result.get('errors') or []
        sync_failed = sync_summary.get('status') in ('error', 'timeout')
        job_record = _record_job(
            storage,
            'degraded' if (errors or sync_failed) else 'completed',
            start_time, result=result, sync=sync_summary)

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
        _record_job(storage, 'failed', start_time, error=str(e), sync=sync_summary)
        return 1


if __name__ == '__main__':
    sys.exit(main())
