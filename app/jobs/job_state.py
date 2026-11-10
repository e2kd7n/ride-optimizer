"""Thread-safe job state for background analysis and fetch tasks.

Replaces the bare module-level dict globals in the API blueprints
(_analysis_job, _fetch_job, _analysis_stop_requested, _backfill_job).
Owned by ServiceContainer and accessed from blueprints via
``current_app.container.jobs``.
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class JobState:
    """Thread-safe key/value bag for a single background job."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _data: Dict[str, Any] = field(default_factory=dict)

    def update(self, **kwargs: Any) -> None:
        """Merge *kwargs* into the job state under the lock."""
        with self._lock:
            self._data.update(kwargs)

    def snapshot(self) -> dict:
        """Return a shallow copy of the current state."""
        with self._lock:
            return dict(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if absent."""
        with self._lock:
            return self._data.get(key, default)

    def reset(self, initial: dict) -> None:
        """Replace the entire state with *initial*."""
        with self._lock:
            self._data = dict(initial)

    def try_start(self, initial: dict) -> bool:
        """Atomically claim the job: replace state with *initial* and return
        True, unless the job is already running (return False, no change)."""
        return self.try_claim(initial) is not None

    def try_claim(self, initial: dict) -> Optional[dict]:
        """Like try_start, but return the state it replaced (None if the job
        was already running), so an aborted claim can be put back."""
        with self._lock:
            if self._data.get('status') == 'running':
                return None
            previous = dict(self._data)
            self._data = dict(initial)
            return previous

    def restore_if_running(self, previous: dict) -> None:
        """Put back *previous* if the job is still in a claimed 'running' state."""
        with self._lock:
            if self._data.get('status') == 'running':
                self._data = dict(previous)


# ---------------------------------------------------------------------------
# Request-scoped claims (#664)
#
# An endpoint claims its job (status 'running') before validating input,
# initialising the container or starting its background thread. If anything
# in between raised, the job stayed 'running' and every retry got 409
# "already running" until the process restarted. claim_job() records the
# claim on the request; job_started() marks it as handed to the thread; a
# teardown_request hook (app/factory.py) restores any claim that wasn't.
# ---------------------------------------------------------------------------

def claim_job(job: JobState, initial: dict) -> bool:
    from flask import g
    previous = job.try_claim(initial)
    if previous is None:
        return False
    claims = getattr(g, '_pending_job_claims', None)
    if claims is None:
        claims = g._pending_job_claims = []
    claims.append((job, previous))
    return True


def job_started() -> None:
    """Call right after the job's background thread has started."""
    from flask import g
    g._pending_job_claims = []


def release_unstarted_claims(exc=None) -> None:
    from flask import g
    for job, previous in getattr(g, '_pending_job_claims', None) or []:
        job.restore_if_running(previous)
    g._pending_job_claims = []


class JobRegistry:
    """Holds named job states; accessible from any blueprint via the app container.

    Usage::

        registry = current_app.container.jobs
        registry.analysis.update(status='running')
        registry.analysis_stop.set()   # request stop
    """

    def __init__(self) -> None:
        self.analysis: JobState = JobState()
        self.analysis.reset({'status': 'idle', 'started_at': None, 'result': None})
        self.fetch: JobState = JobState()
        self.fetch.reset({'status': 'idle', 'fetched': 0, 'label': '', 'started_at': None})
        self.backfill: JobState = JobState()
        self.backfill.reset({'status': 'idle'})
        self.history_backfill: JobState = JobState()
        self.history_backfill.reset({'status': 'idle'})
        self.refresh_gear: JobState = JobState()
        self.refresh_gear.reset({'status': 'idle'})
        self.garmin_sync: JobState = JobState()
        self.garmin_sync.reset({'status': 'idle'})
        # threading.Event replaces the bare bool _analysis_stop_requested
        self.analysis_stop: threading.Event = threading.Event()
        self.history_backfill_stop: threading.Event = threading.Event()
