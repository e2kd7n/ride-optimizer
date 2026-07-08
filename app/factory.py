"""Flask application factory.

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
    )
    if config_overrides:
        app.config.update(config_overrides)

    # --- extensions ---

    @app.before_request
    def _sync_csrf_enabled_with_testing():
        # Test fixtures toggle app.config['TESTING'] on the shared app
        # singleton after creation, so keep CSRF enforcement in sync with it
        # dynamically instead of baking a static value in at app-creation time.
        app.config['WTF_CSRF_ENABLED'] = not app.testing

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

    # --- error handlers ---
    _register_error_handlers(app)

    # --- security headers ---
    _register_after_request(app)

    return app


def _register_blueprints(app: Flask) -> None:
    """Register all blueprints with the application."""
    from app.api import maps_api
    from app.api.weather_bp import bp as weather_bp
    from app.api.commute_bp import bp as commute_bp
    from app.api.routes_bp import bp as routes_bp
    from app.api.planner_bp import bp as planner_bp
    from app.api.strava_bp import bp as strava_bp
    from app.api.integrations_bp import bp as integrations_bp
    from app.api.data_bp import bp as data_bp
    from app.api.stats_bp import bp as stats_bp
    from app.api.core_bp import bp as core_bp

    app.register_blueprint(maps_api.bp)
    # Static file serving
    from flask import send_from_directory
    @app.route('/')
    def index():
        return send_from_directory('../static', 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        return send_from_directory('../static', path)

    app.register_blueprint(weather_bp)
    app.register_blueprint(commute_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(strava_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(core_bp)


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    from flask import jsonify

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'status': 'error', 'message': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error('Internal server error: %s', error)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


def _register_after_request(app: Flask) -> None:
    """Add security headers to all responses."""
    from flask import request as _request

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        if _request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
