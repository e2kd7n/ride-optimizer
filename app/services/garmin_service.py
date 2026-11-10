"""
Garmin Connect integration service.

Authenticates and fetches cycling activities into the same Activity format the
rest of the pipeline uses. All Garmin access goes through the ``GarminClient``
interface (app/services/garmin_client.py, #636), so the underlying library can
be replaced without changing this service.
"""

from src.secure_logger import SecureLogger
import os
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.data_fetcher import Activity

logger = SecureLogger(__name__)

GARMIN_TOKEN_DIR = Path(__file__).resolve().parent.parent.parent / 'config' / '.garmin_tokens'

# Garmin's search endpoint pages; 100 per call keeps responses small.
LIST_PAGE_SIZE = 100


def _secure_token_dir(token_dir: Path) -> None:
    """Restrict Garmin OAuth tokens to the owner (dir 0700, files 0600).

    garth writes its token files with the default umask, unlike every other
    credential store in the app.
    """
    try:
        if not token_dir.exists():
            return
        os.chmod(token_dir, 0o700)
        for path in token_dir.iterdir():
            if path.is_file():
                os.chmod(path, 0o600)
    except OSError as e:
        logger.warning(f"Could not restrict Garmin token permissions: {e}")


def _default_client_factory():
    from app.services.garmin_client import GarthClient
    return GarthClient()


class GarminService:
    """Garmin Connect authentication and activity fetching."""

    def __init__(self, token_dir: Optional[Path] = None,
                 client_factory: Optional[Callable[[], Any]] = None):
        # Overridable so tests can point at a tmp dir instead of the real
        # config/.garmin_tokens directory (disconnect() rmtree's this).
        self.token_dir: Path = token_dir if token_dir is not None else GARMIN_TOKEN_DIR
        self._client_factory = client_factory or _default_client_factory
        self._api = None
        self._connected = False
        self._display_name: Optional[str] = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _client(self):
        if self._api is None:
            self._api = self._client_factory()
        return self._api

    def is_connected(self) -> bool:
        if self._connected:
            return True
        return self._try_resume()

    def _try_resume(self) -> bool:
        if not self.token_dir.exists():
            return False
        try:
            # Only loads the token files; no network call (and so no SSO refresh).
            ok = bool(self._client().resume(self.token_dir))
        except Exception as e:
            logger.debug(f"Garmin resume failed: {e}")
            ok = False
        if ok:
            _secure_token_dir(self.token_dir)
        self._connected = ok
        return ok

    def connect(self, email: str, password: str) -> Dict[str, Any]:
        try:
            username = self._client().login(email, password, self.token_dir)
            _secure_token_dir(self.token_dir)
            self._connected = True
            display_name = username or email.split('@')[0]
            self._display_name = display_name
            return {'success': True, 'display_name': display_name}
        except Exception as e:
            err = str(e)
            logger.error(f"Garmin Connect login failed: {err}")
            if '429' in err or 'Too Many Requests' in err:
                return {
                    'success': False,
                    'error': (
                        'Garmin is rate-limiting login attempts (429 Too Many Requests). '
                        'Wait 15–30 minutes before trying again.'
                    ),
                }
            return {'success': False, 'error': err}

    def disconnect(self):
        if self.token_dir.exists():
            shutil.rmtree(self.token_dir, ignore_errors=True)
        # Drop the client too, so no tokens stay in memory.
        self._api = None
        self._connected = False
        self._display_name = None

    def get_status(self) -> Dict[str, Any]:
        connected = self.is_connected()
        result: Dict[str, Any] = {'connected': connected}
        if connected and self._display_name:
            result['display_name'] = self._display_name
        return result

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------

    def fetch_activities(self, days: Optional[int] = 90, limit: int = 200,
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         progress_callback: Optional[Callable[[int], None]] = None) -> List[Activity]:
        """Fetch activities (with GPS tracks), newest first.

        Either ``days`` back from today, or an explicit ``start_date`` /
        ``end_date`` range (inclusive), which takes precedence. Pages through
        Garmin's list endpoint until ``limit`` activities or the range ends.
        """
        if not self.is_connected():
            raise RuntimeError('Garmin not connected')

        if start_date is None and days is not None:
            start_date = (datetime.now() - timedelta(days=days)).date()

        client = self._client()
        raw: List[Dict[str, Any]] = []
        offset = 0
        while len(raw) < limit:
            page_size = min(LIST_PAGE_SIZE, limit - len(raw))
            page = client.list_activities(start_date, end_date, offset, page_size)
            raw.extend(page)
            if len(page) < page_size:
                break
            offset += len(page)

        activities: List[Activity] = []
        for ga in raw:
            try:
                activity = Activity.from_garmin_activity(ga)
                # The activity list endpoint only returns start/end lat-lng,
                # not a GPS track. Without a track, coverage_tracker has
                # nothing to decode and these rides silently contribute zero
                # tiles to Explore page coverage. Fetch and encode the full
                # polyline per activity so it lands in the same
                # polyline-bearing shape Strava activities use.
                activity.polyline = self._fetch_polyline(activity.id)
                activities.append(activity)
                if progress_callback:
                    progress_callback(len(activities))
            except Exception as e:
                logger.debug(f"Skipping Garmin activity: {e}")
        return activities

    def _fetch_polyline(self, activity_id: int) -> Optional[str]:
        """Fetch an activity's GPS track from Garmin Connect and encode it
        as a Google-encoded polyline (the same format Strava's summary
        polyline uses), so downstream consumers like coverage_tracker don't
        need to know which provider an activity came from.

        Returns None (rather than raising) on any failure — a missing track
        should not block the rest of the sync.
        """
        try:
            details = self._client().activity_details(activity_id)
        except Exception as e:
            logger.debug(f"Failed to fetch GPS track for Garmin activity {activity_id}: {e}")
            return None

        if not isinstance(details, dict):
            return None

        points = (details.get('geoPolylineDTO') or {}).get('polyline') or []
        coords = [
            (p['lat'], p['lon'])
            for p in points
            if isinstance(p, dict) and p.get('lat') is not None and p.get('lon') is not None
        ]
        if not coords:
            return None

        try:
            import polyline as polyline_codec
            return polyline_codec.encode(coords)
        except Exception as e:
            logger.debug(f"Failed to encode GPS track for Garmin activity {activity_id}: {e}")
            return None
