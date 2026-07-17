"""Strava OAuth + Setup API Blueprint.

Routes:
  GET  /api/strava/status
  GET  /api/strava/connect
  GET  /api/strava/callback
  POST /api/strava/disconnect
  GET  /api/setup/status
  POST /api/setup/credentials
  POST /api/setup/verify
"""

import os
import time

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for

from app.credentials.env_helpers import read_env, write_env
from app.extensions import limiter
from src.auth_secure import SecureTokenStorage
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)

bp = Blueprint('strava', __name__, url_prefix='/api')


# ---------------------------------------------------------------------------
# Strava OAuth
# ---------------------------------------------------------------------------

@bp.route('/strava/status')
def strava_status():
    import secrets as _secrets
    storage = SecureTokenStorage('config/credentials.json')
    tokens = storage.load_tokens()
    if tokens is None:
        return jsonify({'connected': False, 'reason': 'no_credentials'})

    auth_expires_at = tokens.get('auth_expires_at') or (time.time() + 90 * 86400)

    if auth_expires_at < time.time():
        return jsonify({'connected': False, 'reason': 'auth_expired'})

    if tokens.get('expires_at', 0) < time.time():
        try:
            import requests as http_req
            _env = read_env()
            resp = http_req.post('https://www.strava.com/oauth/token', data={
                'client_id': os.getenv('STRAVA_CLIENT_ID') or _env.get('STRAVA_CLIENT_ID'),
                'client_secret': os.getenv('STRAVA_CLIENT_SECRET') or _env.get('STRAVA_CLIENT_SECRET'),
                'refresh_token': tokens['refresh_token'],
                'grant_type': 'refresh_token',
            }, timeout=15)
            resp.raise_for_status()
            refreshed = resp.json()
            tokens['access_token'] = refreshed['access_token']
            tokens['refresh_token'] = refreshed['refresh_token']
            tokens['expires_at'] = refreshed['expires_at']
            tokens['auth_expires_at'] = auth_expires_at
            storage.save_tokens(tokens)
        except Exception as e:
            logger.warning(f"Strava token refresh failed in status check: {e}")
            return jsonify({'connected': False, 'reason': 'refresh_failed'})

    return jsonify({'connected': True, 'expires_at': tokens['expires_at'], 'auth_expires_at': auth_expires_at})


@bp.route('/strava/connect')
@limiter.limit("10 per minute")
def strava_connect():
    import secrets as _secrets
    state = _secrets.token_hex(16)
    session['strava_oauth_state'] = state
    if request.args.get('setup_redirect') == '1':
        session['setup_redirect'] = True
    client_id = os.getenv('STRAVA_CLIENT_ID')
    redirect_uri = url_for('strava.strava_callback', _external=True)
    auth_url = (
        'https://www.strava.com/oauth/authorize'
        f'?client_id={client_id}'
        f'&redirect_uri={redirect_uri}'
        '&response_type=code'
        '&scope=read,activity:read_all'
        f'&state={state}'
    )
    return redirect(auth_url)


@bp.route('/strava/callback')
@limiter.limit("10 per minute")
def strava_callback():
    error = request.args.get('error')
    if error:
        logger.error(f"Strava OAuth error: {error}")
        return redirect('/settings.html?strava_error=' + error)

    state = request.args.get('state')
    if not state or state != session.pop('strava_oauth_state', None):
        logger.warning("Strava callback: invalid state (possible CSRF)")
        return redirect('/settings.html?strava_error=invalid_state')

    code = request.args.get('code')
    if not code:
        return redirect('/settings.html?strava_error=no_code')

    try:
        import requests as http_req
        _env = read_env()
        resp = http_req.post('https://www.strava.com/oauth/token', data={
            'client_id': os.getenv('STRAVA_CLIENT_ID') or _env.get('STRAVA_CLIENT_ID'),
            'client_secret': os.getenv('STRAVA_CLIENT_SECRET') or _env.get('STRAVA_CLIENT_SECRET'),
            'code': code,
            'grant_type': 'authorization_code',
        }, timeout=15)
        resp.raise_for_status()
        token_data = resp.json()

        storage = SecureTokenStorage('config/credentials.json')
        storage.save_tokens({
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_at': token_data['expires_at'],
            'auth_expires_at': time.time() + 180 * 86400,
        })
        logger.info("Strava OAuth complete — credentials saved")

        # New credentials only change what Strava-backed services can fetch —
        # WeatherService/TrainerRoadService/RouteLibraryService don't depend
        # on Strava auth, so a full container reset is unnecessary (#461).
        current_app.container.refresh_services('analysis', 'commute', 'planner')

        setup_redirect = session.pop('setup_redirect', False)
        if setup_redirect:
            return redirect('/setup.html?connected=1')
        return redirect('/settings.html?strava_connected=1')
    except Exception as e:
        logger.error(f"Strava token exchange failed: {e}", exc_info=True)
        setup_redirect = session.pop('setup_redirect', False)
        if setup_redirect:
            return redirect('/setup.html?strava_error=token_exchange_failed')
        return redirect('/settings.html?strava_error=token_exchange_failed')


@bp.route('/strava/disconnect', methods=['POST'])
@limiter.limit("10 per minute")
def strava_disconnect():
    """Remove saved Strava credentials, severing the connection."""
    try:
        creds_path = current_app.container.credentials_path
        if creds_path.exists():
            creds_path.unlink()
        # See connect handler above — only Strava-backed services need to be
        # rebuilt after a credentials change (#461).
        current_app.container.refresh_services('analysis', 'commute', 'planner')
        logger.info("Strava credentials removed — integration disconnected")
        return jsonify({'success': True})
    except Exception as exc:
        logger.error("Strava disconnect failed: %s", exc)
        return jsonify({'success': False, 'error': 'Could not remove credentials'}), 500


# ---------------------------------------------------------------------------
# Setup / FTUE
# ---------------------------------------------------------------------------

@bp.route('/setup/status')
def setup_status():
    """Return whether Strava credentials are configured."""
    client_id = os.getenv('STRAVA_CLIENT_ID') or read_env().get('STRAVA_CLIENT_ID', '')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET') or read_env().get('STRAVA_CLIENT_SECRET', '')
    configured = bool(client_id and client_secret)
    storage = SecureTokenStorage('config/credentials.json')
    tokens = storage.load_tokens()
    authorized = tokens is not None
    return jsonify({
        'configured': configured,
        'authorized': authorized,
        'setup_complete': configured and authorized,
    })


@bp.route('/setup/credentials', methods=['POST'])
def setup_credentials():
    """Save Strava Client ID and Secret to .env."""
    data = request.get_json(silent=True) or {}
    client_id = str(data.get('client_id', '')).strip()
    client_secret = str(data.get('client_secret', '')).strip()

    if not client_id or not client_secret:
        return jsonify({'success': False, 'error': 'client_id and client_secret are required'}), 400
    if not client_id.isdigit():
        return jsonify({'success': False, 'error': 'client_id must be numeric'}), 400
    if len(client_secret) < 8:
        return jsonify({'success': False, 'error': 'client_secret appears too short'}), 400

    try:
        write_env({'STRAVA_CLIENT_ID': client_id, 'STRAVA_CLIENT_SECRET': client_secret})
        os.environ['STRAVA_CLIENT_ID'] = client_id
        os.environ['STRAVA_CLIENT_SECRET'] = client_secret
        logger.info("Setup: Strava credentials saved via setup wizard")
        return jsonify({'success': True})
    except OSError as exc:
        logger.error("Setup: failed to write .env: %s", exc)
        return jsonify({'success': False, 'error': 'Could not write credentials file'}), 500


@bp.route('/setup/verify', methods=['POST'])
@limiter.limit("10 per minute")
def setup_verify():
    """Test Strava credentials by exchanging a short-lived auth code or hitting /athlete."""
    client_id = os.getenv('STRAVA_CLIENT_ID') or read_env().get('STRAVA_CLIENT_ID', '')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET') or read_env().get('STRAVA_CLIENT_SECRET', '')

    if not client_id or not client_secret:
        return jsonify({'valid': False, 'error': 'Credentials not configured yet'}), 400

    try:
        import requests as http_req
        resp = http_req.post(
            'https://www.strava.com/oauth/token',
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': 'verify_probe',
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        body = resp.json()
        if resp.status_code == 400 and 'AuthorizationCode' in str(body):
            return jsonify({'valid': True, 'message': 'Credentials accepted by Strava'})
        if resp.status_code == 401:
            return jsonify({'valid': False, 'error': 'Strava rejected the credentials — check your Client ID and Secret'})
        return jsonify({'valid': True, 'message': 'Credentials appear valid'})
    except Exception as exc:
        logger.warning("Setup verify error: %s", exc)
        return jsonify({'valid': False, 'error': 'Could not reach Strava to verify'}), 503
