"""Thread-safe job state for background analysis and fetch tasks.

Replaces the bare module-level dict globals in launch.py (_analysis_job,
_fetch_job, _analysis_stop_requested).  Owned by ServiceContainer and
accessed from blueprints via ``current_app.container.jobs``.
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict


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


class JobRegistry:
    """Holds named job states; accessible from any blueprint via the app container.

    Usage::

        registry = current_app.container.jobs
        registry.analysis.update(status='running')
        registry.analysis_stop.set()   # request stop
    """

    def __init__(self) -> None:
        self.analysis: JobState = JobState()
        self.fetch: JobState = JobState()
        # threading.Event replaces the bare bool _analysis_stop_requested
        self.analysis_stop: threading.Event = threading.Event()
