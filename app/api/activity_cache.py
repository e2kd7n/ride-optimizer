"""
Shared, mtime-invalidated accessor for the raw Strava activity cache.

stats_bp and data_bp each re-read and re-parsed data/cache/activities.json
(and rebuilt every Activity object) on every request (#461). This module
parses and converts once, then serves the same list until the file changes
on disk.

The returned list is SHARED across callers and threads — treat it as
read-only. Copy (``list(...)``) before sorting or mutating.

AnalysisService is not a substitute here: it only holds ``_activities``
in memory after an in-process analysis run, not after loading from cache
(see AnalysisService._load_from_cache — "we don't cache full activity
objects").
"""

import threading
from pathlib import Path
from typing import List

from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

_CACHE_PATH = Path('data/cache/activities.json')
_guard = threading.Lock()
_memo = {'stamp': None, 'activities': []}


def load_cached_activities() -> List:
    """Activity objects from data/cache/activities.json, cached by file mtime.

    Returns [] if the cache file is missing or unreadable.
    """
    import json

    from src.data_fetcher import Activity

    try:
        st = _CACHE_PATH.stat()
    except OSError:
        with _guard:
            _memo['stamp'] = None
            _memo['activities'] = []
        return []
    stamp = (st.st_mtime_ns, st.st_size)

    with _guard:
        if _memo['stamp'] == stamp:
            return _memo['activities']

    try:
        with open(_CACHE_PATH, 'r') as f:
            raw = json.load(f)
        activities = [Activity.from_dict(a) for a in raw.get('activities', [])]
    except Exception as e:
        logger.warning(f"Could not load activities cache: {e}")
        return []

    with _guard:
        _memo['stamp'] = stamp
        _memo['activities'] = activities
    return activities
