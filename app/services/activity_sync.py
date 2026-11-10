"""
Source-agnostic activity sync (#619, #620).

Pulls activities for a date range from every connected source (Strava, Garmin,
later RideWithGPS #589) into data/cache/activities.json, then re-runs analysis
from the cache once if anything new arrived. Used by:

- ``POST /api/sync`` (the Reports calendar's "Backfill this month", and any
  other "get my rides" action), and
- the nightly cron job (``cron/daily_analysis.py``), when the Settings toggle
  "Check for new activities nightly" is on.

One source failing (e.g. Strava API access inactive) never stops the others.
Cross-source duplicates are handled by ``StravaDataFetcher.cache_activities``
(#557). The last result is kept in ``data/sync_status.json`` for Settings.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

SYNC_STATUS_FILE = 'sync_status.json'
SOURCE_LABELS = {'strava': 'Strava', 'garmin': 'Garmin'}
# Incremental nightly window: since the last good sync, with overlap.
NIGHTLY_OVERLAP_DAYS = 2
NIGHTLY_DEFAULT_DAYS = 7
NIGHTLY_MAX_DAYS = 60


def connected_sources(container) -> List[str]:
    """Sources with stored credentials, cheapest checks only (no network)."""
    sources = []
    try:
        if container.credentials_path.exists():
            sources.append('strava')
    except Exception:
        pass
    try:
        if container.get_garmin_service().is_connected():
            sources.append('garmin')
    except Exception as e:
        logger.debug(f"Garmin connection check failed: {e}")
    return sources


def _cache_count() -> int:
    from app.api.activity_cache import load_cached_activities
    return len(load_cached_activities())


def _fetch_strava(container, start: date, end: date, limit: int, progress) -> None:
    analysis = container.analysis_service
    if analysis is None:
        raise RuntimeError('Analysis service unavailable')
    # Local calendar days: stravalib treats naive datetimes as UTC (#494),
    # and `before` is exclusive, so end the window at the next local midnight.
    after = datetime.combine(start, time.min).astimezone()
    before = datetime.combine(end + timedelta(days=1), time.min).astimezone()
    analysis.data_fetcher.fetch_activities(
        limit=limit,
        after=after,
        before=before,
        use_cache=False,
        progress_callback=progress,
        merge_cache=True,
    )


def _fetch_garmin(container, start: date, end: date, limit: int, progress) -> None:
    analysis = container.analysis_service
    if analysis is None:
        raise RuntimeError('Analysis service unavailable')
    garmin = container.get_garmin_service()
    activities = garmin.fetch_activities(
        days=None, start_date=start, end_date=end, limit=limit,
        progress_callback=progress,
    )
    fetcher = analysis.cache_fetcher
    existing_ids = {a.id for a in (fetcher.load_cached_activities() or [])}
    new = [a for a in activities if a.id not in existing_ids]
    if new:
        # cache_activities merges against what's on disk under its lock and
        # drops cross-source duplicates (#557).
        fetcher.cache_activities(new)


FETCHERS = {'strava': _fetch_strava, 'garmin': _fetch_garmin}


def run_sync(container, start: date, end: date, *, limit: int = 1000,
             sources: Optional[List[str]] = None,
             on_progress: Optional[Callable[[str], None]] = None,
             analyse: bool = True) -> Dict[str, Any]:
    """Pull ``start``..``end`` (inclusive) from each source, then analyse once.

    Returns ``{'sources': {name: {'status', 'new', 'fetched', 'error'}},
    'new': int, 'total': int, 'analysed': bool, 'status': 'done'|'error'|'no_sources'}``.
    """
    say = on_progress or (lambda msg: None)
    sources = connected_sources(container) if sources is None else sources
    result: Dict[str, Any] = {
        'start': start.isoformat(), 'end': end.isoformat(),
        'sources': {}, 'new': 0, 'total': 0, 'analysed': False,
        'finished_at': None,
    }
    if not sources:
        result['status'] = 'no_sources'
        result['total'] = _cache_count()
        return result

    before_all = _cache_count()
    for source in sources:
        label = SOURCE_LABELS.get(source, source)
        fetch = FETCHERS.get(source)
        if fetch is None:
            result['sources'][source] = {'status': 'error', 'new': 0, 'fetched': 0,
                                         'error': 'unknown source'}
            continue
        say(f'Fetching from {label}…')
        fetched = {'n': 0}

        def progress(count, _label=label):
            fetched['n'] = count
            say(f'Fetching from {_label}… {count:,} activities')

        before = _cache_count()
        try:
            fetch(container, start, end, limit, progress)
            new = max(0, _cache_count() - before)
            result['sources'][source] = {'status': 'ok', 'new': new,
                                         'fetched': fetched['n'], 'error': None}
        except Exception as e:
            logger.warning(f"{label} sync failed: {e}")
            result['sources'][source] = {'status': 'error', 'new': 0,
                                         'fetched': fetched['n'], 'error': str(e)[:300]}

    total = _cache_count()
    result['total'] = total
    result['new'] = max(0, total - before_all)
    ok = [s for s, r in result['sources'].items() if r['status'] == 'ok']
    result['status'] = 'done' if ok else 'error'

    if analyse and result['new'] > 0:
        say(f"{result['new']:,} new activities — updating analysis…")
        analysis = container.analysis_service
        outcome = analysis.run_full_analysis(force_refresh=False, skip_strava_fetch=True)
        if isinstance(outcome, dict) and outcome.get('status') == 'error':
            result['analysis_error'] = str(outcome.get('message', 'analysis failed'))[:300]
        else:
            result['analysed'] = True
            # Only Commute/Planner derive state from the route groups (#461).
            container.refresh_services('commute', 'planner')
        if container.exploration_service is not None:
            # Soft invalidation: keeps the on-disk tile index (#571); the
            # index adds the new activities incrementally on the next load.
            container.exploration_service.invalidate_caches()

    result['finished_at'] = datetime.now(timezone.utc).isoformat()
    _record(container, result)
    return result


def _record(container, result: Dict[str, Any]) -> None:
    """Keep the latest result per source, for Settings and the nightly window."""
    try:
        def mutate(current):
            status = current if isinstance(current, dict) else {}
            status['last_run'] = {k: result[k] for k in
                                  ('status', 'start', 'end', 'new', 'total', 'analysed', 'finished_at')}
            per = status.setdefault('sources', {})
            for name, r in result['sources'].items():
                entry = per.setdefault(name, {})
                entry['last_attempt'] = result['finished_at']
                entry['last_status'] = r['status']
                entry['last_error'] = r['error']
                entry['last_new'] = r['new']
                if r['status'] == 'ok':
                    entry['last_success'] = result['finished_at']
                    entry['synced_through'] = result['end']
            return status
        container.storage.update(SYNC_STATUS_FILE, mutate, default={})
    except Exception as e:
        logger.warning(f"Could not record sync status: {e}")


def read_status(container) -> Dict[str, Any]:
    try:
        status = container.storage.read(SYNC_STATUS_FILE, default={})
        return status if isinstance(status, dict) else {}
    except Exception:
        return {}


def nightly_window(container, today: Optional[date] = None) -> tuple:
    """(start, end) for the nightly sync: from the oldest per-source
    ``synced_through`` minus an overlap, capped to NIGHTLY_MAX_DAYS."""
    today = today or date.today()
    status = read_status(container)
    through = []
    for entry in (status.get('sources') or {}).values():
        try:
            through.append(date.fromisoformat(entry.get('synced_through')))
        except (TypeError, ValueError):
            continue
    if through:
        start = min(through) - timedelta(days=NIGHTLY_OVERLAP_DAYS)
    else:
        start = today - timedelta(days=NIGHTLY_DEFAULT_DAYS)
    start = max(start, today - timedelta(days=NIGHTLY_MAX_DAYS))
    return min(start, today), today
