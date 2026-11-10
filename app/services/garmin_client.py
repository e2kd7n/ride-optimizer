"""
Garmin Connect client interface (#636).

``GarminService`` talks to Garmin only through the small ``GarminClient``
protocol below, so the library behind it can be swapped without touching the
service, the sync jobs or the Data Cleanup work (#628) built on top.

``GarthClient`` is the current implementation. ``garth`` was deprecated by its
author in Nov 2026 and is pinned to 0.8.0 (requirements.txt). The recorded
migration target is ``python-garminconnect`` (>= 0.3.x, which no longer
depends on garth); see #636 for the decision and the follow-up issue.

Unlike the old code, ``GarthClient`` owns a private ``garth.Client`` instance
instead of the process-global ``garth.client``, so a connect can't swap tokens
under a running sync, and every call has a timeout.
"""

from __future__ import annotations

import threading
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

# Seconds per Garmin HTTP call. Without a bound, an expired-token refresh was
# seen hanging forever, taking one of gunicorn's four threads out of service.
GARMIN_TIMEOUT_SECONDS = 30

ACTIVITY_LIST_PATH = '/activitylist-service/activities/search/activities'
ACTIVITY_DETAILS_PATH = '/activity-service/activity/{activity_id}/details'


class GarminClient(Protocol):
    """The Garmin Connect operations the app needs."""

    def resume(self, token_dir: Path) -> bool:
        """Load saved tokens from ``token_dir``; True if usable tokens were found.
        Must not make a network call."""

    def login(self, email: str, password: str, token_dir: Path) -> Optional[str]:
        """Log in, save tokens to ``token_dir``, return the display name if known."""

    def list_activities(self, start_date: Optional[date], end_date: Optional[date],
                        start: int, limit: int) -> List[Dict[str, Any]]:
        """One page of the activity list (Garmin's search endpoint), newest first."""

    def activity_details(self, activity_id: int) -> Optional[Dict[str, Any]]:
        """Activity details including ``geoPolylineDTO`` (the GPS track)."""


class GarthClient:
    """``GarminClient`` backed by a private ``garth.Client`` instance."""

    def __init__(self, timeout: int = GARMIN_TIMEOUT_SECONDS):
        from garth.http import Client

        self._client = Client()
        try:
            self._client.configure(timeout=timeout, telemetry_enabled=False)
        except TypeError:  # garth without telemetry support
            self._client.configure(timeout=timeout)
        # garth refreshes OAuth2 tokens inside requests; serialise calls so two
        # threads never refresh (or log in) at the same time on one client.
        self._lock = threading.RLock()

    def resume(self, token_dir: Path) -> bool:
        with self._lock:
            self._client.load(str(token_dir))
            return self._client.oauth1_token is not None

    def login(self, email: str, password: str, token_dir: Path) -> Optional[str]:
        with self._lock:
            self._client.login(email, password)
            token_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            self._client.dump(str(token_dir))
            try:
                return self._client.username
            except Exception:
                return None

    def list_activities(self, start_date: Optional[date], end_date: Optional[date],
                        start: int, limit: int) -> List[Dict[str, Any]]:
        params = {'start': str(start), 'limit': str(limit)}
        if start_date is not None:
            params['startDate'] = start_date.isoformat()
        if end_date is not None:
            params['endDate'] = end_date.isoformat()
        with self._lock:
            raw = self._client.connectapi(ACTIVITY_LIST_PATH, params=params)
        return raw if isinstance(raw, list) else []

    def activity_details(self, activity_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            details = self._client.connectapi(
                ACTIVITY_DETAILS_PATH.format(activity_id=int(activity_id)),
                params={'maxPolylineSize': 4000},
            )
        return details if isinstance(details, dict) else None
