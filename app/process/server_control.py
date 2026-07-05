"""Server process management helpers.

Extracted from launch.py (kill_existing_server, open_browser, run_server).
Called by launch.py at startup/shutdown; not used inside any blueprint.
"""

import logging
import os
import time
import webbrowser
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def kill_existing_server(port: int) -> None:
    """Kill any existing server process running on *port*.

    No-op if no process is found or if *port* is invalid.
    Requires ``lsof`` (Linux / macOS); silently skips on Windows.
    """
    import subprocess
    import signal

    if not isinstance(port, int) or port < 1024 or port > 65535:
        logger.error("Invalid port number: %s", port)
        return

    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if not result.stdout.strip():
            return

        current_user: Optional[str] = os.getenv('USER') or os.getenv('USERNAME')
        for pid_str in result.stdout.strip().split('\n'):
            try:
                pid_int = int(pid_str)
                try:
                    proc_info = subprocess.run(
                        ['ps', '-p', str(pid_int), '-o', 'user='],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    proc_user = proc_info.stdout.strip()
                    if proc_user == current_user:
                        logger.info("Killing server process %s on port %s", pid_int, port)
                        os.kill(pid_int, signal.SIGTERM)
                        time.sleep(0.5)
                    else:
                        logger.warning(
                            "Skipping process %s — owned by %s, not %s",
                            pid_int, proc_user, current_user,
                        )
                except subprocess.TimeoutExpired:
                    logger.warning("Timeout checking ownership of process %s", pid_int)
                except Exception as exc:
                    logger.debug("Could not verify process %s ownership: %s", pid_int, exc)
            except (ValueError, ProcessLookupError, PermissionError) as exc:
                logger.debug("Could not kill process %s: %s", pid_str, exc)

    except subprocess.TimeoutExpired:
        logger.error("Timeout checking for existing server")
    except FileNotFoundError:
        logger.debug("lsof not available; skipping process check")
    except Exception as exc:
        logger.warning("Error checking for existing server: %s", exc)


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

    time.sleep(1.5)  # Wait for server to start

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
