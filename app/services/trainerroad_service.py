"""
TrainerRoad Service - ICS feed ingestion and workout normalization.

Provides:
- ICS feed parsing from TrainerRoad calendar
- Workout metadata extraction
- Normalization to internal planning constraints
- Graceful error handling for feed failures
- Secure storage of ICS feed URL
"""

import ipaddress
from src.secure_logger import SecureLogger
import requests
import json
import os
import re
import socket
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from icalendar import Calendar, Event
from urllib.parse import urlparse, urljoin
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from cryptography.fernet import Fernet

from src.config_manager import ConfigManager
from src.json_storage import JSONStorage

logger = SecureLogger(__name__)

WORKOUTS_CACHE = Path('data/cache/trainerroad_workouts.json')

# Only these schemes are ever fetched server-side.
_ALLOWED_FEED_SCHEMES = {'http', 'https'}
# Bound on redirect hops when fetching the feed, to prevent open-ended chains.
_MAX_FEED_REDIRECTS = 5


def _resolve_validated_ips(hostname: Optional[str]) -> Optional[List[str]]:
    """
    Resolve *hostname* and return its IPs **only if every one of them is a
    public, non-internal address**; otherwise return ``None``. Blocks
    loopback/private/link-local/reserved/multicast ranges (including cloud
    metadata endpoints like 169.254.169.254) to prevent SSRF via a
    user-supplied feed URL.

    Returning the concrete IPs (rather than a bool) lets the caller connect to
    the exact address that was validated, closing the DNS-rebinding TOCTOU where
    a hostname resolves to a public IP at check time and a private one at
    connect time.
    """
    if not hostname:
        return None

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return None

    if not addr_infos:
        return None

    ips: List[str] = []
    for info in addr_infos:
        raw_ip = info[4][0].split('%')[0]  # strip IPv6 zone id, if any
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            return None

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return None

        ips.append(raw_ip)

    return ips or None


def _is_safe_feed_host(hostname: Optional[str]) -> bool:
    """Return True only if *hostname* resolves exclusively to public addresses."""
    return _resolve_validated_ips(hostname) is not None


def _is_safe_feed_url(url: str) -> bool:
    """Validate scheme + resolved host safety for a feed URL/redirect target."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in _ALLOWED_FEED_SCHEMES:
        return False

    return _is_safe_feed_host(parsed.hostname)


def _validated_ip_for_url(url: str) -> Optional[str]:
    """
    Validate *url*'s scheme and resolve its host, returning a single validated
    public IP to pin the connection to — or ``None`` if the scheme is disallowed
    or the host resolves to any internal address. This is the fetch-time gate;
    the returned IP is what the connection actually uses (see ``_PinnedIPAdapter``).
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    if parsed.scheme not in _ALLOWED_FEED_SCHEMES:
        return None

    ips = _resolve_validated_ips(parsed.hostname)
    if not ips:
        return None
    return ips[0]


def _pinned_pool_manager(pinned_ip: str, **kwargs):
    """
    Build a urllib3 PoolManager whose connections dial *pinned_ip* at the socket
    layer while keeping the request's real hostname for the ``Host`` header, TLS
    SNI, and certificate verification. The URL/hostname is left untouched (so SNI
    and cert checks stay correct automatically); only the DNS host used for the
    socket connect is overridden — the piece that makes the SSRF check
    TOCTOU-free.
    """
    class _PinnedHTTPConnectionPool(HTTPConnectionPool):
        def _new_conn(self):
            conn = super()._new_conn()
            conn._dns_host = pinned_ip
            return conn

    class _PinnedHTTPSConnectionPool(HTTPSConnectionPool):
        def _new_conn(self):
            conn = super()._new_conn()
            hostname = self.host  # the real hostname the pool was created for
            conn._dns_host = pinned_ip          # socket connects here
            conn.server_hostname = hostname     # SNI stays the hostname
            conn.assert_hostname = hostname     # cert verified against hostname
            return conn

    pm = PoolManager(**kwargs)
    pm.pool_classes_by_scheme = {
        'http': _PinnedHTTPConnectionPool,
        'https': _PinnedHTTPSConnectionPool,
    }
    return pm


class _PinnedIPAdapter(HTTPAdapter):
    """
    Requests adapter that pins every connection to a specific, pre-validated IP.
    The exact IP ``_validated_ip_for_url`` approved is the one the socket
    connects to, so DNS can't be rebound to an internal address between
    validation and connect.
    """

    def __init__(self, pinned_ip: str, **kwargs):
        self._pinned_ip = pinned_ip
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = _pinned_pool_manager(
            self._pinned_ip,
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )


def _pinned_get(url: str, pinned_ip: str, timeout: int):
    """GET *url* with the connection pinned to *pinned_ip* (no redirects)."""
    parsed = urlparse(url)
    session = requests.Session()
    adapter = _PinnedIPAdapter(pinned_ip)
    session.mount(f'{parsed.scheme}://', adapter)
    try:
        return session.get(url, timeout=timeout, allow_redirects=False)
    finally:
        session.close()


class TrainerRoadService:
    """
    Service for TrainerRoad ICS feed integration.

    Features:
    - Parse ICS calendar feeds
    - Extract workout metadata (name, date, duration, type)
    - Normalize to internal planning constraints
    - Store workout data in JSON cache
    - Handle stale/missing/invalid feeds gracefully
    - Secure encrypted storage of ICS feed URL
    """

    def __init__(self):
        self.config = ConfigManager.get_instance()
        self.credentials_path = Path('config/trainerroad_credentials.json')
        self.key_file = Path('config/.trainerroad_encryption_key')
        self.last_sync = None
        self.sync_interval_hours = 6

        self.cipher = self._get_cipher()
        self.feed_url = self._load_feed_url()
        # Locked, atomic JSON storage for the workouts cache (issue #459 —
        # raw open()/json.dump could corrupt the file or lose updates).
        self._cache_storage = JSONStorage(data_dir=str(WORKOUTS_CACHE.parent))

    def _get_cipher(self) -> Fernet:
        env_key = os.getenv('TRAINERROAD_ENCRYPTION_KEY')
        if env_key:
            return Fernet(env_key.encode())

        if self.key_file.exists():
            try:
                key = self.key_file.read_bytes()
                return Fernet(key)
            except Exception as e:
                logger.warning(f"Failed to load encryption key: {e}")

        key = Fernet.generate_key()

        try:
            self.key_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.key_file.write_bytes(key)
            os.chmod(self.key_file, 0o600)
            logger.info(f"Generated new TrainerRoad encryption key: {self.key_file}")
        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")

        return Fernet(key)

    def _load_feed_url(self) -> Optional[str]:
        if not self.credentials_path.exists():
            return None

        try:
            with open(self.credentials_path, 'rb') as f:
                encrypted = f.read()

            decrypted = self.cipher.decrypt(encrypted)
            data = json.loads(decrypted.decode())

            feed_url = data.get('ics_feed_url')
            if feed_url:
                logger.info("Loaded TrainerRoad ICS feed URL from secure storage")
            return feed_url

        except Exception as e:
            logger.error(f"Failed to load TrainerRoad credentials: {e}")
            return None

    def _save_feed_url(self, feed_url: str) -> bool:
        try:
            self.credentials_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

            data = {'ics_feed_url': feed_url}
            data_json = json.dumps(data)
            encrypted = self.cipher.encrypt(data_json.encode())

            with open(self.credentials_path, 'wb') as f:
                f.write(encrypted)

            os.chmod(self.credentials_path, 0o600)
            logger.info(f"Saved TrainerRoad ICS feed URL securely to {self.credentials_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save TrainerRoad credentials: {e}")
            return False

    def set_feed_url(self, feed_url: str) -> bool:
        try:
            parsed = urlparse(feed_url)
            if not all([parsed.scheme, parsed.netloc]):
                # Don't echo the URL — it can embed a secret token in its path.
                logger.error("Invalid feed URL: missing scheme or host")
                return False

            if not _is_safe_feed_url(feed_url):
                logger.error(
                    "Rejected feed URL: scheme must be http/https and host must not "
                    "resolve to a private/internal/loopback address"
                )
                return False

            if not self._save_feed_url(feed_url):
                return False

            self.feed_url = feed_url
            logger.info(f"TrainerRoad feed URL set and saved securely: {parsed.netloc}")
            return True

        except Exception as e:
            logger.error(f"Error validating feed URL: {e}")
            return False

    def get_feed_url(self) -> Optional[str]:
        return self.feed_url

    def remove_credentials(self) -> bool:
        try:
            if self.credentials_path.exists():
                self.credentials_path.unlink()
                logger.info("Removed TrainerRoad credentials")

            self.feed_url = None
            return True

        except Exception as e:
            logger.error(f"Error removing credentials: {e}")
            return False

    def fetch_ics_feed(self, timeout: int = 10) -> Optional[str]:
        if not self.feed_url:
            logger.warning("No feed URL configured")
            return None

        url = self.feed_url
        try:
            for _ in range(_MAX_FEED_REDIRECTS):
                # Validate scheme + resolve host, and pin the connection to the
                # exact IP we validated (TOCTOU-free — see _validated_ip_for_url).
                pinned_ip = _validated_ip_for_url(url)
                if pinned_ip is None:
                    logger.error("ICS feed URL failed safety validation; refusing to fetch")
                    return None

                # Log only the host — the feed URL path can contain a secret token.
                logger.info("Fetching ICS feed from %s", urlparse(url).netloc)
                response = _pinned_get(url, pinned_ip, timeout)

                if response.is_redirect or response.is_permanent_redirect:
                    location = response.headers.get('Location')
                    if not location:
                        logger.error("Redirect response missing Location header")
                        return None

                    # Next hop is re-validated and re-pinned at the top of the loop.
                    url = urljoin(url, location)
                    continue

                response.raise_for_status()
                content = response.text
                logger.info(f"Successfully fetched ICS feed ({len(content)} bytes)")
                return content

            logger.error(f"Too many redirects (>{_MAX_FEED_REDIRECTS}) fetching ICS feed")
            return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching ICS feed after {timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ICS feed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching ICS feed: {e}", exc_info=True)
            return None

    def parse_ics_feed(self, ics_content: str) -> List[Dict[str, Any]]:
        if not ics_content:
            return []

        try:
            cal = Calendar.from_ical(ics_content)
            workouts = []

            for component in cal.walk():
                if component.name != "VEVENT":
                    continue

                try:
                    workout = self._parse_event(component)
                    if workout:
                        workouts.append(workout)
                except Exception as e:
                    logger.warning(f"Error parsing event: {e}")
                    continue

            logger.info(f"Parsed {len(workouts)} workouts from ICS feed")
            return workouts

        except Exception as e:
            logger.error(f"Error parsing ICS feed: {e}", exc_info=True)
            return []

    def _parse_event(self, event: Event) -> Optional[Dict[str, Any]]:
        try:
            summary = str(event.get('summary', ''))
            description = str(event.get('description', ''))
            dtstart = event.get('dtstart')
            dtend = event.get('dtend')
            uid = str(event.get('uid', ''))

            if not summary or not dtstart:
                return None

            if isinstance(dtstart.dt, datetime):
                workout_date = dtstart.dt.date()
            else:
                workout_date = dtstart.dt

            duration_minutes = self._extract_duration_minutes(
                summary,
                dtstart.dt,
                dtend.dt if dtend else None,
            )

            workout_type = self._extract_workout_type(summary, description)
            tss, intensity_factor = self._extract_metrics(description)

            return {
                'workout_id': uid or f"tr_{workout_date.isoformat()}_{hash(summary)}",
                'workout_name': summary,
                'workout_date': workout_date,
                'workout_type': workout_type,
                'duration_minutes': duration_minutes,
                'tss': tss,
                'intensity_factor': intensity_factor,
                'description': description,
                'status': 'scheduled'
            }

        except Exception as e:
            logger.warning(f"Error parsing event: {e}")
            return None

    def _extract_workout_type(self, summary: str, description: str) -> Optional[str]:
        text = f"{summary} {description}".lower()

        type_keywords = [
            ('VO2Max', ['vo2', 'vo2max', 'v02']),
            ('Anaerobic', ['anaerobic', 'over-under']),
            ('Sprint', ['sprint', 'neuromuscular']),
            ('Threshold', ['threshold', 'sweet spot', 'ftp test']),
            ('Tempo', ['tempo']),
            ('Endurance', ['endurance', 'easy', 'recovery', 'base']),
            ('Group Ride', ['group ride', 'group'])
        ]

        for workout_type, keywords in type_keywords:
            if any(keyword in text for keyword in keywords):
                return workout_type

        return None

    def _extract_duration_minutes(self, summary: str, start_value: Any, end_value: Any = None) -> Optional[int]:
        if isinstance(start_value, datetime) and isinstance(end_value, datetime):
            duration = end_value - start_value
            duration_minutes = int(duration.total_seconds() / 60)
            if duration_minutes > 0:
                return duration_minutes

        summary_match = re.match(r'^\s*(\d+):(\d{2})\s+-\s+', summary)
        if summary_match:
            hours = int(summary_match.group(1))
            minutes = int(summary_match.group(2))
            return (hours * 60) + minutes

        return None

    def _normalize_cached_workout(self, workout: Dict[str, Any]) -> Dict[str, Any]:
        if workout.get('duration_minutes') is None:
            workout['duration_minutes'] = self._extract_duration_minutes(
                workout.get('workout_name', ''),
                None,
                None,
            )
        return workout

    def _extract_metrics(self, description: str) -> tuple[Optional[float], Optional[float]]:
        tss = None
        intensity_factor = None

        tss_match = re.search(r'(?:tss[:\s]+)?(\d+)(?:\s+tss)?', description, re.IGNORECASE)
        if tss_match:
            try:
                tss = float(tss_match.group(1))
            except ValueError:
                pass

        if_match = re.search(r'if[:\s]+([0-9.]+)', description, re.IGNORECASE)
        if if_match:
            try:
                intensity_factor = float(if_match.group(1))
            except ValueError:
                pass

        return tss, intensity_factor

    def get_status(self) -> Dict[str, Any]:
        connected = self.feed_url is not None
        cache = self._load_workouts_cache()
        upcoming = [
            w for w in cache.values()
            if w.get('workout_date', '') >= date.today().isoformat()
        ]
        return {
            'connected': connected,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'workout_count': len(upcoming),
        }

    def get_upcoming_workouts(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        cache = self._load_workouts_cache()
        today = date.today()
        end = today + timedelta(days=days_ahead)
        workouts = [
            self._normalize_cached_workout(w)
            for w in cache.values()
            if today.isoformat() <= w.get('workout_date', '') <= end.isoformat()
        ]
        workouts.sort(key=lambda w: w.get('workout_date', ''))
        return workouts

    def get_today_summary(self) -> Dict[str, Any]:
        constraints = self.get_workout_constraints(date.today())
        if not constraints:
            return {'has_workout': False}

        return {
            'has_workout': True,
            'workout': {
                'name': constraints.get('workout_name', 'Workout'),
                'type': constraints.get('workout_type'),
                'duration_minutes': constraints.get('min_duration_minutes'),
                'tss': constraints.get('tss'),
                'indoor_fallback': constraints.get('indoor_fallback', False),
                'notes': constraints.get('notes', []),
            }
        }

    def _load_workouts_cache(self) -> Dict[str, Any]:
        return self._cache_storage.read(WORKOUTS_CACHE.name, default={})

    def sync_workouts(self, days_ahead: int = 14) -> Dict[str, Any]:
        try:
            if self.last_sync:
                time_since_sync = datetime.now() - self.last_sync
                if time_since_sync.total_seconds() < self.sync_interval_hours * 3600:
                    logger.info(f"Skipping sync, last sync was {time_since_sync.total_seconds() / 3600:.1f}h ago")
                    return {
                        'status': 'skipped',
                        'message': f'Last sync was {time_since_sync.total_seconds() / 3600:.1f}h ago',
                        'last_sync': self.last_sync
                    }

            ics_content = self.fetch_ics_feed()
            if not ics_content:
                return {
                    'status': 'error',
                    'message': 'Failed to fetch ICS feed',
                    'workouts_synced': 0
                }

            workouts = self.parse_ics_feed(ics_content)
            if not workouts:
                return {
                    'status': 'error',
                    'message': 'No workouts found in ICS feed',
                    'workouts_synced': 0
                }

            today = date.today()
            end_date = today + timedelta(days=days_ahead)
            upcoming_workouts = [
                w for w in workouts
                if today <= w['workout_date'] <= end_date
            ]

            sync_time = datetime.utcnow().isoformat()
            counts = {'created': 0, 'updated': 0}

            def _merge(cache):
                for workout_data in upcoming_workouts:
                    wid = workout_data['workout_id']
                    entry = {
                        'workout_id': wid,
                        'workout_name': workout_data['workout_name'],
                        'workout_date': workout_data['workout_date'].isoformat(),
                        'workout_type': workout_data.get('workout_type'),
                        'duration_minutes': workout_data.get('duration_minutes'),
                        'tss': workout_data.get('tss'),
                        'intensity_factor': workout_data.get('intensity_factor'),
                        'status': workout_data.get('status', 'scheduled'),
                        'synced_at': sync_time,
                    }
                    if wid in cache:
                        counts['updated'] += 1
                    else:
                        counts['created'] += 1
                    cache[wid] = entry
                return cache

            self._cache_storage.update(WORKOUTS_CACHE.name, _merge, default={})
            created = counts['created']
            updated = counts['updated']
            self.last_sync = datetime.now()

            logger.info(f"Synced {len(upcoming_workouts)} workouts ({created} created, {updated} updated)")

            return {
                'status': 'success',
                'workouts_synced': len(upcoming_workouts),
                'workouts_created': created,
                'workouts_updated': updated,
                'last_sync': self.last_sync,
                'message': f'Successfully synced {len(upcoming_workouts)} workouts'
            }

        except Exception as e:
            logger.error(f"Error syncing workouts: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Sync failed: {str(e)}',
                'workouts_synced': 0
            }

    def get_workout_constraints(self, target_date: date) -> Optional[Dict[str, Any]]:
        cache = self._load_workouts_cache()
        target_str = target_date.isoformat()

        workout = None
        for entry in cache.values():
            if entry.get('workout_date') == target_str:
                workout = self._normalize_cached_workout(entry)
                break

        if not workout:
            return None

        wtype = workout.get('workout_type')
        duration = workout.get('duration_minutes')

        constraints = {
            'has_workout': True,
            'workout_name': workout.get('workout_name'),
            'workout_type': wtype,
            'min_duration_minutes': None,
            'max_duration_minutes': None,
            'preferred_intensity': None,
            'indoor_preferred': False,
            'indoor_fallback': False,
            'notes': []
        }

        if wtype == 'Endurance':
            constraints['min_duration_minutes'] = duration or 60
            constraints['max_duration_minutes'] = (duration or 60) + 30
            constraints['preferred_intensity'] = 'low'
            constraints['indoor_preferred'] = False
            constraints['notes'].append('Can extend commute for endurance work')

        elif wtype in ['Threshold', 'VO2Max']:
            constraints['indoor_preferred'] = True
            constraints['preferred_intensity'] = 'high'
            constraints['notes'].append('High-intensity workout - consider indoor trainer')

        elif wtype == 'Group Ride':
            constraints['min_duration_minutes'] = duration or 60
            constraints['max_duration_minutes'] = (duration or 60) + 60
            constraints['preferred_intensity'] = 'moderate'
            constraints['indoor_preferred'] = False
            constraints['notes'].append('Group ride — match to historical day-of-week pattern')

        elif wtype == 'Recovery':
            constraints['max_duration_minutes'] = 45
            constraints['preferred_intensity'] = 'very_low'
            constraints['notes'].append('Keep it easy for recovery')

        tss = workout.get('tss')
        if tss:
            if tss > 100:
                constraints['notes'].append(f'High training load (TSS: {tss})')
            constraints['tss'] = tss

        return constraints
