"""
Ride Optimizer — server launcher (CLI entry point).

Starts the Flask application created by app.factory.create_app().
All route handlers live in app/api/ blueprints.
All service initialisation lives in app/container.py.
All infrastructure helpers live in app/process/ and app/credentials/.

Usage:
  python launch.py               — kill any existing server and launch in background
  python launch.py --serve [PORT] — run server in foreground (called internally)
  python launch.py --status      — print server status and exit
  python launch.py --stop        — stop any running server and exit
"""

import logging
import os
import sys
import time

from src.logging_config import setup_logging

# Configure logging with rotation (10MB per file, 5 backups)
setup_logging(
    log_dir='logs',
    log_level=logging.INFO,
    max_bytes=10 * 1024 * 1024,
    backup_count=5,
    console_output=True,
)
logger = logging.getLogger(__name__)

PORT = 8083


def _get_port() -> int:
    return int(os.environ.get('RIDE_OPTIMIZER_PORT', PORT))


def _build_app():
    """Create and return the configured Flask application."""
    from app.factory import create_app
    return create_app()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import subprocess
    import tempfile

    from app.process.server_control import (
        kill_existing_server,
        run_server,
        server_status,
        stop_server,
        open_browser,
    )

    port = _get_port()

    # ---- --serve (foreground subprocess mode) ----
    if len(sys.argv) > 1 and sys.argv[1] == '--serve':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else port
        logger.info(f"Running server on port {port}")
        app = _build_app()
        run_server(app, port)
        sys.exit(0)

    # ---- --status ----
    if len(sys.argv) > 1 and sys.argv[1] == '--status':
        st = server_status()
        if st['running']:
            uptime = f"{int(st['uptime_seconds'])}s" if st['uptime_seconds'] is not None else 'unknown'
            print(
                f"Server is RUNNING  pid={st['pid']}  port={st['port']}  "
                f"started={st['started']}  uptime={uptime}"
            )
        else:
            print("Server is NOT running.")
        sys.exit(0 if st['running'] else 1)

    # ---- --stop ----
    if len(sys.argv) > 1 and sys.argv[1] == '--stop':
        stopped = stop_server()
        sys.exit(0 if stopped else 1)

    # ---- normal launch ----
    kill_existing_server(port)

    logger.info("Starting Ride Optimizer API server...")
    logger.info(f"Server will run on port {port}")

    log_path = os.path.join(tempfile.gettempdir(), 'ride-optimizer-server.log')
    with open(log_path, 'a') as log_file:
        server_process = subprocess.Popen(
            [sys.executable, __file__, '--serve', str(port)],
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )

    logger.info(f"Server started with PID {server_process.pid}")
    logger.info(f"Server logs: {log_path}")

    time.sleep(2)

    url = f'http://localhost:{port}'
    try:
        import platform
        system = platform.system()
        if system == 'Darwin':
            os.system(f'open -a "Google Chrome" {url} 2>/dev/null || open {url}')
        elif system == 'Windows':
            os.system(f'start chrome {url} 2>nul || start {url}')
        elif system == 'Linux':
            os.system(f'google-chrome {url} 2>/dev/null || xdg-open {url}')
        else:
            import webbrowser
            webbrowser.open(url)
        logger.info(f"Browser opened at {url}")
    except Exception as e:
        logger.warning(f"Could not open browser: {e}")
        logger.info(f"Please open your browser manually to: {url}")

    logger.info("Launch complete. Server running in background.")
    sys.exit(0)


# When imported (e.g. by WSGI or testing), expose the app object.
app = _build_app()

# Re-export process management helpers for backward compatibility with tests
# that do ``monkeypatch.setattr(launch, '_pid_file_path', ...)`` etc.
# Removed in Phase 6 once tests are updated to import from app.process.server_control.
from app.process.server_control import (  # noqa: E402
    _pid_file_path,
    _write_pid_file,
    _read_pid_file,
    _remove_pid_file,
    _is_our_server_process,
    _find_server_on_port,
    kill_existing_server,
    server_status,
    stop_server,
    run_server,
    open_browser,
)

# Route handlers that called ``from launch import something`` during
# Phase 1 can now be updated to use app.container directly, but for
# backward-compat we leave ``get_locations_from_config`` importable
# here during the transition window (removed fully in Phase 6).

def get_locations_from_config(config):
    """Compatibility shim — use app.container._load_commute_data() instead."""
    from src.location_finder import Location
    try:
        home_lat = config.get('location.home.latitude')
        home_lon = config.get('location.home.longitude')
        work_lat = config.get('location.work.latitude')
        work_lon = config.get('location.work.longitude')
        if None in (home_lat, home_lon, work_lat, work_lon):
            raise ValueError("Missing location coordinates in config")
        home_location = Location(lat=float(home_lat), lon=float(home_lon), name="Home", activity_count=0)
        work_location = Location(lat=float(work_lat), lon=float(work_lon), name="Work", activity_count=0)
        return home_location, work_location
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid location coordinates in config: {e}")
