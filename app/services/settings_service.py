"""
Settings Service - Server-side persistence for user preferences.

Provides:
- JSON file persistence via JSONStorage
- Merge-with-defaults semantics (partial updates)
- Reset to defaults
"""

from src.secure_logger import SecureLogger
from typing import Dict, Any
from copy import deepcopy

from src.json_storage import JSONStorage

logger = SecureLogger(__name__)

SETTINGS_FILENAME = 'user_settings.json'

DEFAULT_SETTINGS: Dict[str, Any] = {
    'unit_system': 'imperial',
    'default_view': 'home',
    'show_weather_details': True,
    'show_elevation': True,
    'auto_save': True,
    'show_secondary_metrics': True,
    'outdoor_min_temp_f': 40,
    'outdoor_allow_rain': False,
}


class SettingsService:
    """
    Service layer for user settings with JSON file persistence.

    Uses JSONStorage to persist to ``user_settings.json`` under the data dir.
    All reads return the stored values merged on top of defaults so that newly
    added keys always have a value.
    """

    def __init__(self):
        self.storage = JSONStorage()

    def get_settings(self) -> Dict[str, Any]:
        """Return current settings merged with defaults."""
        stored = self.storage.read(SETTINGS_FILENAME, default={})
        merged = deepcopy(DEFAULT_SETTINGS)
        if isinstance(stored, dict):
            merged.update(stored)
        return merged

    def update_settings(self, partial: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a partial update and persist.

        Only keys present in *DEFAULT_SETTINGS* are accepted; unknown keys are
        silently dropped to prevent storage of arbitrary data.

        Returns the full settings dict after the update.
        """
        current = self.storage.read(SETTINGS_FILENAME, default={})
        if not isinstance(current, dict):
            current = {}

        # Only accept known keys with basic type validation
        for key, default_val in DEFAULT_SETTINGS.items():
            if key in partial:
                value = partial[key]
                # Type-check: bool before int (bool is subclass of int in Python)
                if isinstance(default_val, bool):
                    if isinstance(value, bool):
                        current[key] = value
                elif isinstance(default_val, int):
                    if isinstance(value, int) and not isinstance(value, bool):
                        current[key] = value
                elif isinstance(default_val, str):
                    if isinstance(value, str) and len(value) <= 50:
                        current[key] = value

        self.storage.write(SETTINGS_FILENAME, current)

        # Return merged with defaults
        merged = deepcopy(DEFAULT_SETTINGS)
        merged.update(current)
        return merged

    def reset_settings(self) -> Dict[str, Any]:
        """Delete persisted settings and return defaults."""
        self.storage.delete(SETTINGS_FILENAME)
        return deepcopy(DEFAULT_SETTINGS)
