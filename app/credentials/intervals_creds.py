"""intervals.icu encrypted credential store.

Extracted verbatim from launch.py (_IntervalsCredStore).  Persists
credentials in an encrypted JSON file so an .env-file wipe doesn't
silently destroy the connection.
"""

import json
from src.secure_logger import SecureLogger
import os
from pathlib import Path

logger = SecureLogger(__name__)


class IntervalsCredStore:
    """Persist intervals.icu credentials in an encrypted JSON file.

    Survives server restarts; never written to .env so an env-file wipe
    doesn't silently destroy the connection.
    """

    def __init__(self, creds_path: Path = None, key_path: Path = None) -> None:
        # Overridable so tests can point at a tmp dir instead of the real
        # config/intervals_credentials.json (delete() unlinks this).
        self._creds_path: Path = creds_path if creds_path is not None else Path('config/intervals_credentials.json')
        self._key_path: Path = key_path if key_path is not None else Path('config/.intervals_encryption_key')
        from cryptography.fernet import Fernet
        self._Fernet = Fernet
        self._cipher = self._load_or_create_key()

    def _load_or_create_key(self):
        from cryptography.fernet import Fernet
        if self._key_path.exists():
            try:
                return Fernet(self._key_path.read_bytes())
            except Exception as exc:
                logger.warning("intervals: bad encryption key, regenerating: %s", exc)
        key = Fernet.generate_key()
        self._key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._key_path.write_bytes(key)
        os.chmod(self._key_path, 0o600)
        return Fernet(key)

    def load(self) -> dict:
        """Return ``{'athlete_id': ..., 'api_key': ...}`` or ``{}``."""
        if not self._creds_path.exists():
            return {}
        try:
            encrypted = self._creds_path.read_bytes()
            data = json.loads(self._cipher.decrypt(encrypted).decode())
            return data if data.get('athlete_id') and data.get('api_key') else {}
        except Exception as exc:
            logger.warning("intervals: failed to load credentials: %s", exc)
            return {}

    def save(self, athlete_id: str, api_key: str) -> None:
        """Encrypt and persist *athlete_id* / *api_key*."""
        self._creds_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        encrypted = self._cipher.encrypt(
            json.dumps({'athlete_id': athlete_id, 'api_key': api_key}).encode()
        )
        self._creds_path.write_bytes(encrypted)
        os.chmod(self._creds_path, 0o600)

    def delete(self) -> None:
        """Remove the credentials file if it exists."""
        if self._creds_path.exists():
            self._creds_path.unlink()
