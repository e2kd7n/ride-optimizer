"""
Garmin Connect integration service.

Authenticates via the ``garth`` library and fetches cycling activities
into the same Activity format the rest of the pipeline uses.
"""

from src.secure_logger import SecureLogger
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.data_fetcher import Activity

logger = SecureLogger(__name__)

GARMIN_TOKEN_DIR = Path(__file__).resolve().parent.parent.parent / 'config' / '.garmin_tokens'

# Seconds per Garmin HTTP call. garth's default has no overall bound, and an
# expired-token refresh was seen hanging forever, permanently taking one of
# gunicorn's four threads out of service.
GARTH_TIMEOUT_SECONDS = 30

# garth keeps one process-global client. Serialise the calls that swap its
# credentials (login/resume) so a connect can't change tokens under another
# thread mid-call. Full per-instance client isolation is tracked in #636.
_garth_lock = threading.RLock()
_garth_configured = False


def _garth():
    """Import garth, applying our timeout and telemetry settings once."""
    global _garth_configured
    import garth
    configure = getattr(garth, 'configure', None)
    if not _garth_configured and configure is not None:
        with _garth_lock:
            if not _garth_configured:
                try:
                    configure(timeout=GARTH_TIMEOUT_SECONDS, telemetry_enabled=False)
                except TypeError:
                    # Older garth without telemetry support.
                    configure(timeout=GARTH_TIMEOUT_SECONDS)
                _garth_configured = True
    return garth


def _secure_token_dir(token_dir: Path) -> None:
    """Restrict Garmin OAuth tokens to the owner (dir 0700, files 0600).

    garth.save() writes with the default umask, unlike every other credential
    store in the app.
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


class GarminService:
    """Thin wrapper around garth for Garmin Connect authentication and activity fetching."""

    def __init__(self, token_dir: Optional[Path] = None):
        self._client = None
        self._display_name: Optional[str] = None
        # Overridable so tests can point at a tmp dir instead of the real
        # config/.garmin_tokens directory (disconnect() rmtree's this).
        self.token_dir: Path = token_dir if token_dir is not None else GARMIN_TOKEN_DIR

    def is_connected(self) -> bool:
        if self._client is not None:
            return True
        return self._try_resume()

    def _try_resume(self) -> bool:
        if not self.token_dir.exists():
            return False
        try:
            garth = _garth()
            with _garth_lock:
                garth.resume(str(self.token_dir))
                # Just check that both token files loaded — don't touch .username,
                # .profile, or .user_profile; all three hit connectapi over the
                # network and can trigger an SSO refresh.
                assert garth.client.oauth1_token is not None
            _secure_token_dir(self.token_dir)
            self._client = garth
            return True
        except Exception as e:
            logger.debug(f"Garmin resume failed: {e}")
            self._client = None
            return False

    def connect(self, email: str, password: str) -> Dict[str, Any]:
        try:
            garth = _garth()
            with _garth_lock:
                garth.login(email, password)
                self.token_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                garth.save(str(self.token_dir))
            _secure_token_dir(self.token_dir)
            self._client = garth
            try:
                display_name = garth.client.username or email.split('@')[0]
            except Exception:
                display_name = email.split('@')[0]
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
        import shutil
        if self.token_dir.exists():
            shutil.rmtree(self.token_dir, ignore_errors=True)
        self._client = None

    def get_status(self) -> Dict[str, Any]:
        connected = self.is_connected()
        result: Dict[str, Any] = {'connected': connected}
        if connected and self._display_name:
            result['display_name'] = self._display_name
        return result

    def fetch_activities(self, days: int = 90, limit: int = 200) -> List[Activity]:
        if not self.is_connected():
            raise RuntimeError('Garmin not connected')

        garth = _garth()
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        raw = garth.connectapi(
            f'/activitylist-service/activities/search/activities',
            params={'startDate': start, 'limit': str(limit), 'start': '0'},
        )
        if not isinstance(raw, list):
            raw = []

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
            garth = _garth()
            details = garth.connectapi(
                f'/activity-service/activity/{activity_id}/details',
                params={'maxPolylineSize': 4000},
            )
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
