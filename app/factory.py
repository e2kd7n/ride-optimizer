"""Flask application factory.

Phase 1: stub only — create_app() constructs the Flask app and registers
the blueprints that already exist (maps_api).  Stub blueprints are imported
but not yet registered here; they will be wired up in Phase 4.

Usage::

    from app.factory import create_app
    app = create_app()
"""

import logging
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_or_create_secret_key() -> str:
    """Return a stable SECRET_KEY; generate and persist one on first run."""
    if key := os.getenv('FLASK_SECRET_KEY'):
        return key
    key_file = Path('config/secret_key')
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.parent.mkdir(exist_ok=True)
    key_file.write_text(key)
    key_file.chmod(0o600)
    return key


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def create_app(config_overrides: dict | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_overrides: Optional dict of Flask config values to override
            the defaults (useful for testing).

    Returns:
        Configured :class:`~flask.Flask` instance with ``app.container``
        set to a :class:`~app.container.ServiceContainer`.
    """
    app = Flask(__name__, static_folder='../static', static_url_path='')

    # --- core config ---
    app.config['JSON_SORT_KEYS'] = False
    app.config['SECRET_KEY'] = _load_or_create_secret_key()
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
        WTF_CSRF_CHECK_DEFAULT=False,
    )
    if config_overrides:
        app.config.update(config_overrides)

    # --- extensions ---
    csrf = CSRFProtect(app)
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
        strategy="fixed-window",
    )
    app.extensions['csrf'] = csrf
    app.extensions['limiter'] = limiter

    # --- service container ---
    from app.container import ServiceContainer
    app.container = ServiceContainer()  # type: ignore[attr-defined]

    # --- blueprints ---
    _register_blueprints(app)

    return app


def _register_blueprints(app: Flask) -> None:
    """Register all blueprints with the application.

    Phase 1: only maps_api is registered (already a Blueprint).
    Stub blueprints are imported so import errors surface immediately,
    but they are not yet registered — that happens in Phase 4.
    """
    from app.api import maps_api
    app.register_blueprint(maps_api.bp)

    # Phase 4 will uncomment these one at a time:
    # from app.api.weather_bp import bp as weather_bp
    # app.register_blueprint(weather_bp)
    # from app.api.commute_bp import bp as commute_bp
    # app.register_blueprint(commute_bp)
    # from app.api.routes_bp import bp as routes_bp
    # app.register_blueprint(routes_bp)
    # from app.api.planner_bp import bp as planner_bp
    # app.register_blueprint(planner_bp)
    # from app.api.strava_bp import bp as strava_bp
    # app.register_blueprint(strava_bp)
    # from app.api.integrations_bp import bp as integrations_bp
    # app.register_blueprint(integrations_bp)
    # from app.api.data_bp import bp as data_bp
    # app.register_blueprint(data_bp)
    # from app.api.stats_bp import bp as stats_bp
    # app.register_blueprint(stats_bp)
    # from app.api.core_bp import bp as core_bp
    # app.register_blueprint(core_bp)
