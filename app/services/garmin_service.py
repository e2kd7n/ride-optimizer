"""
Garmin Connect integration service.

Authenticates via the ``garth`` library and fetches cycling activities
into the same Activity format the rest of the pipeline uses.
"""

from src.secure_logger import SecureLogger
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.data_fetcher import Activity

logger = SecureLogger(__name__)

GARMIN_TOKEN_DIR = Path(__file__).resolve().parent.parent.parent / 'config' / '.garmin_tokens'


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
            import garth
            garth.resume(str(self.token_dir))
            # Just check that both token files loaded — don't touch .username,
            # .profile, or .user_profile; all three hit connectapi over the
            # network and can trigger an SSO refresh.
            assert garth.client.oauth1_token is not None
            self._client = garth
            return True
        except Exception as e:
            logger.debug(f"Garmin resume failed: {e}")
            self._client = None
            return False

    def connect(self, email: str, password: str) -> Dict[str, Any]:
        try:
            import garth
            garth.login(email, password)
            self.token_dir.mkdir(parents=True, exist_ok=True)
            garth.save(str(self.token_dir))
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

        import garth
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
                activities.append(Activity.from_garmin_activity(ga))
            except Exception as e:
                logger.debug(f"Skipping Garmin activity: {e}")
        return activities
