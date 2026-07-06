"""intervals.icu encrypted credential store.

Extracted verbatim from launch.py (_IntervalsCredStore).  Persists
credentials in an encrypted JSON file so an .env-file wipe doesn't
silently destroy the connection.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class IntervalsCredStore:
    """Persist intervals.icu credentials in an encrypted JSON file.

    Survives server restarts; never written to .env so an env-file wipe
    doesn't silently destroy the connection.
    """

    _CREDS_PATH = Path('config/intervals_credentials.json')
    _KEY_PATH = Path('config/.intervals_encryption_key')

    def __init__(self) -> None:
        from cryptography.fernet import Fernet
        self._Fernet = Fernet
        self._cipher = self._load_or_create_key()

    def _load_or_create_key(self):
        from cryptography.fernet import Fernet
        if self._KEY_PATH.exists():
            try:
                return Fernet(self._KEY_PATH.read_bytes())
            except Exception as exc:
                logger.warning("intervals: bad encryption key, regenerating: %s", exc)
        key = Fernet.generate_key()
        self._KEY_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._KEY_PATH.write_bytes(key)
        os.chmod(self._KEY_PATH, 0o600)
        return Fernet(key)

    def load(self) -> dict:
        """Return ``{'athlete_id': ..., 'api_key': ...}`` or ``{}``."""
        if not self._CREDS_PATH.exists():
            return {}
        try:
            encrypted = self._CREDS_PATH.read_bytes()
            data = json.loads(self._cipher.decrypt(encrypted).decode())
            return data if data.get('athlete_id') and data.get('api_key') else {}
        except Exception as exc:
            logger.warning("intervals: failed to load credentials: %s", exc)
            return {}

    def save(self, athlete_id: str, api_key: str) -> None:
        """Encrypt and persist *athlete_id* / *api_key*."""
        self._CREDS_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        encrypted = self._cipher.encrypt(
            json.dumps({'athlete_id': athlete_id, 'api_key': api_key}).encode()
        )
        self._CREDS_PATH.write_bytes(encrypted)
        os.chmod(self._CREDS_PATH, 0o600)

    def delete(self) -> None:
        """Remove the credentials file if it exists."""
        if self._CREDS_PATH.exists():
            self._CREDS_PATH.unlink()
