"""Server process management helpers (cross-platform, uses psutil).

Extracted from launch.py. Called by launch.py at startup/shutdown;
not used inside any blueprint.
"""

import json
from src.secure_logger import SecureLogger
import os
import tempfile
import time
import webbrowser
from datetime import datetime
from typing import Optional

logger = SecureLogger(__name__)

# ---------------------------------------------------------------------------
# PID file helpers
# ---------------------------------------------------------------------------

def _pid_file_path() -> str:
    """Return the canonical path for the server PID file."""
    return os.path.join(tempfile.gettempdir(), 'ride-optimizer-server.pid')


def _write_pid_file(pid: int, port: int) -> None:
    """Write PID, port, and start time to the PID file."""
    pid_path = _pid_file_path()
    data = {
        'pid': pid,
        'port': port,
        'started': datetime.now().isoformat(),
    }
    # Atomic temp-file + rename so a concurrent reader never sees a
    # partially written file (issue #459).
    temp_path = pid_path + '.tmp'
    with open(temp_path, 'w') as fh:
        json.dump(data, fh)
    try:
        os.chmod(temp_path, 0o600)
    except OSError:
        pass  # Windows doesn't support chmod; not critical
    os.replace(temp_path, pid_path)


def _read_pid_file() -> dict:
    """Read PID file. Returns {} if missing or corrupt."""
    try:
        with open(_pid_file_path()) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _remove_pid_file() -> None:
    """Remove the PID file if it exists."""
    try:
        os.remove(_pid_file_path())
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Process identity helpers
# ---------------------------------------------------------------------------

def _is_our_server_process(pid: int) -> bool:
    """Return True if *pid* is a live launch.py --serve process owned by us."""
    try:
        import psutil
        proc = psutil.Process(pid)
        if proc.status() == psutil.STATUS_ZOMBIE:
            return False
        cmdline_str = ' '.join(proc.cmdline())
        return 'launch.py' in cmdline_str and '--serve' in cmdline_str
    except Exception:
        return False


def _find_server_on_port(port: int) -> Optional[int]:
    """
    Fallback: scan listening sockets for *port* and return a matching
    launch.py --serve PID, or None.
    """
    try:
        import psutil
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN and conn.pid:
                if _is_our_server_process(conn.pid):
                    return conn.pid
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def kill_existing_server(port: int) -> None:
    """
    Kill any existing ride-optimizer server process.

    Strategy (cross-platform, no lsof/ps):
    1. Read PID file; if the recorded process is our server → SIGTERM it.
    2. Fall back to a port-scan via psutil to catch processes that started
       without writing a PID file (e.g. older launcher versions).
    3. Clean up the PID file afterwards.
    """
    import psutil

    if not isinstance(port, int) or port < 1024 or port > 65535:
        logger.error("Invalid port number: %s", port)
        return

    killed_any = False

    data = _read_pid_file()
    if data:
        pid = data.get('pid')
        if pid and _is_our_server_process(pid):
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=5)
                logger.info(
                    "Stopped existing server (PID %s, port %s, started %s)",
                    pid, data.get('port', '?'), data.get('started', '?'),
                )
                killed_any = True
            except psutil.TimeoutExpired:
                proc.kill()
                logger.warning("Server PID %s did not exit cleanly; force-killed.", pid)
                killed_any = True
            except psutil.NoSuchProcess:
                logger.debug("PID %s from PID file no longer exists.", pid)
        else:
            logger.debug("PID file present but process is gone — cleaning up stale file.")
        _remove_pid_file()

    pid_via_port = _find_server_on_port(port)
    if pid_via_port and not killed_any:
        try:
            proc = psutil.Process(pid_via_port)
            proc.terminate()
            proc.wait(timeout=5)
            logger.info("Stopped stale server found on port %s (PID %s)", port, pid_via_port)
        except psutil.TimeoutExpired:
            proc.kill()
            logger.warning("Stale server PID %s did not exit cleanly; force-killed.", pid_via_port)
        except psutil.NoSuchProcess:
            pass


def server_status() -> dict:
    """
    Return a dict describing the current server state:
      {'running': bool, 'pid': int|None, 'port': int|None,
       'started': str|None, 'uptime_seconds': float|None}
    """
    import psutil

    PORT = 8083
    port = int(os.environ.get('RIDE_OPTIMIZER_PORT', PORT))

    data = _read_pid_file()
    if not data:
        pid = _find_server_on_port(port)
        if pid:
            return {'running': True, 'pid': pid, 'port': port, 'started': None, 'uptime_seconds': None}
        return {'running': False, 'pid': None, 'port': None, 'started': None, 'uptime_seconds': None}

    pid = data.get('pid')
    if pid and _is_our_server_process(pid):
        uptime = None
        try:
            proc = psutil.Process(pid)
            uptime = (datetime.now() - datetime.fromtimestamp(proc.create_time())).total_seconds()
        except Exception:
            pass
        return {
            'running': True,
            'pid': pid,
            'port': data.get('port'),
            'started': data.get('started'),
            'uptime_seconds': uptime,
        }

    _remove_pid_file()
    return {'running': False, 'pid': None, 'port': None, 'started': None, 'uptime_seconds': None}


def stop_server() -> bool:
    """Stop the tracked server. Returns True if a process was stopped."""
    import psutil

    PORT = 8083
    port = int(os.environ.get('RIDE_OPTIMIZER_PORT', PORT))

    data = _read_pid_file()
    pid = data.get('pid') if data else None

    if not pid:
        pid = _find_server_on_port(port)

    if not pid:
        logger.info("No running server found.")
        return False

    if not _is_our_server_process(pid):
        logger.info("PID %s is no longer a ride-optimizer server process.", pid)
        _remove_pid_file()
        return False

    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
        logger.info("Server PID %s stopped.", pid)
    except psutil.TimeoutExpired:
        proc.kill()
        logger.warning("Server PID %s force-killed after timeout.", pid)
    except psutil.NoSuchProcess:
        logger.debug("PID %s was already gone.", pid)

    _remove_pid_file()
    return True


def open_browser(port: int) -> None:
    """Open Chrome (or the default browser) at ``http://127.0.0.1:<port>``."""
    import platform
    from urllib.parse import urlparse

    if not isinstance(port, int) or port < 1024 or port > 65535:
        logger.error("Invalid port for browser: %s", port)
        return

    url = f'http://127.0.0.1:{port}'
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('127.0.0.1', 'localhost'):
        logger.error("Invalid URL for browser: %s", url)
        return

    time.sleep(1.5)

    try:
        system = platform.system()
        if system == 'Darwin':
            chrome_path = 'open -a /Applications/Google\\ Chrome.app %s'
        elif system == 'Windows':
            chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
        elif system == 'Linux':
            chrome_path = '/usr/bin/google-chrome %s'
        else:
            chrome_path = None

        if chrome_path:
            webbrowser.get(chrome_path).open(url)
        else:
            webbrowser.open(url)

        logger.info("Opened browser at %s", url)
    except Exception as exc:
        logger.warning("Could not open browser automatically: %s", exc)
        logger.info("Please open your browser manually to: %s", url)


def run_server(app, port: int) -> None:
    """Write PID file and run the Flask server. Called from launch.py ``--serve`` mode."""
    _write_pid_file(os.getpid(), port)
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    finally:
        _remove_pid_file()
