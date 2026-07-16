"""Flask application factory.

Usage::

    from app.factory import create_app
    app = create_app()
"""

from src.secure_logger import SecureLogger
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, g
from flask_wtf.csrf import CSRFProtect

from app.extensions import limiter

logger = SecureLogger(__name__)


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
    app = Flask(__name__, static_folder='../static', static_url_path='', template_folder='../templates')

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

    @app.before_request
    def _generate_csp_nonce():
        # A fresh per-request nonce, exposed to Jinja as csp_nonce() and
        # matched into the CSP header in _register_after_request. Lets
        # index.html authorize one small nonced inline script (which stashes
        # the nonce for commute.js) without reopening script-src's
        # 'unsafe-inline' — #475 follow-up for the commute-map iframe.
        g.csp_nonce = secrets.token_urlsafe(16)

    app.jinja_env.globals['csp_nonce'] = lambda: g.csp_nonce

    csrf = CSRFProtect(app)
    limiter.init_app(app)
    app.extensions['csrf'] = csrf

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

    # Page routes (Jinja-rendered; nav/bottom-nav/theme-init live in
    # templates/partials/ so they're not duplicated across pages — #470)
    from flask import render_template, send_from_directory

    @app.route('/')
    @app.route('/index.html')
    def index():
        return render_template('index.html', active_page='home')

    @app.route('/routes.html')
    def routes_page():
        return render_template('routes.html', active_page='routes')

    @app.route('/weather.html')
    def weather_page():
        return render_template('weather.html', active_page='weather')

    @app.route('/reports.html')
    def reports_page():
        return render_template('reports.html', active_page='reports')

    @app.route('/settings.html')
    def settings_page():
        return render_template('settings.html', active_page='settings')

    @app.route('/explore.html')
    def explore_page():
        return render_template('explore.html', active_page='explore')

    @app.route('/route-detail.html')
    def route_detail_page():
        return render_template('route-detail.html', active_page='routes')

    @app.route('/compare.html')
    def compare_page():
        return render_template('compare.html', active_page='routes')

    # Everything else (JS/CSS/images, and the remaining standalone static
    # pages: setup.html, commute.html) is served as a plain static file.
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
            # No inline <script>/onclick="" or inline style="" left anywhere
            # in code we author (#470, #475) — script-src and style-src(-elem)
            # both drop 'unsafe-inline'. The remaining data-driven "inline
            # style" cases (chart bars, route/legend colors, comfort scores)
            # were rewritten as either a small fixed set of CSS classes (see
            # the "#475: drop CSP style-src 'unsafe-inline'" section of
            # main.css) or CSSOM property assignment (element.style.x = ...),
            # which CSP does not restrict.
            # code.jquery.com/cdnjs are pulled in by Folium's default map
            # template (rendered server-side, loaded into the commute map
            # iframe below) — not used anywhere else. The 'nonce-...' value
            # is this request's g.csp_nonce (see before_request above):
            # index.html embeds one small nonced <script> that stashes the
            # nonce on window, and commute.js copies it onto every <script>
            # AND <style> tag in the Folium HTML it fetches (plus its own
            # error-page <style> block) before building the blob: iframe —
            # the blob document inherits index.html's CSP (same nonce, same
            # request), so those tags validate without reopening
            # 'unsafe-inline' for the whole app.
            f"script-src 'self' 'nonce-{g.csp_nonce}' https://cdn.jsdelivr.net https://unpkg.com https://code.jquery.com https://cdnjs.cloudflare.com; "
            f"style-src 'self' 'nonce-{g.csp_nonce}' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com https://netdna.bootstrapcdn.com; "
            # style-src-attr overrides style-src for the style="" HTML
            # attribute specifically (CSP3) and is intentionally left at
            # 'unsafe-inline': the commute-map iframe bundles Folium's
            # default jQuery + leaflet.awesome-markers + bootstrap-glyphicons
            # assets, which build style="" attributes at *runtime* (e.g.
            # marker-icon coloring) — code we don't author and can't stamp a
            # nonce onto (nonces/hashes don't apply to style attributes at
            # all per the CSP3 spec). style-src-elem (our own <style> blocks,
            # all 4 of them — 3 in Folium's template, 1 in commute.js's
            # error page — are nonce-stamped) stays on the strict style-src
            # value above, so arbitrary <style> block injection is still
            # blocked; only attribute-level styling is relaxed, and only for
            # this one iframe's third-party bundle.
            "style-src-attr 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "
            # commute.js loads the server-rendered Folium map into an
            # <iframe> via a blob: URL (no frame-src fell back to
            # default-src 'self', which silently broke the map entirely).
            "frame-src 'self' blob:; "
            "font-src 'self' https://cdn.jsdelivr.net https://netdna.bootstrapcdn.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        if _request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
