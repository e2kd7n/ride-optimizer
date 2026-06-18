"""
Flask application factory for testing and modular imports.

The production app is assembled in launch.py with lazy service initialization.
This factory creates a minimal Flask instance for unit tests that need an app context
but do not require Strava credentials or live data.
"""

from flask import Flask


def create_app(config_name: str = 'default') -> Flask:
    """
    Create a minimal Flask application for testing.

    Services are NOT initialized here — they are lazily initialized in launch.py
    on first request. This factory exists so unit tests can obtain an app context
    without importing launch.py (which requires STRAVA_CLIENT_ID at import time).

    Args:
        config_name: One of 'development', 'production', 'testing', 'default'.

    Returns:
        Configured Flask application instance.
    """
    from pathlib import Path

    project_root = Path(__file__).parent.parent
    app = Flask(
        __name__,
        static_folder=str(project_root / 'static'),
        static_url_path='/static',
    )

    from app.config import config as config_map
    app.config.from_object(config_map[config_name])

    return app
