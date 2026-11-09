""".env file helpers — read and write key=value pairs.

Extracted verbatim from launch.py (_env_path, _read_env, _write_env).
Used by strava_bp and core_bp to persist credentials without touching
unrelated environment keys.

Runtime writes (Strava reconnect, ORS key, home/work location — anything set
through the web UI after the container is already running) go to
``config/runtime_overrides.env`` instead of the project's ``.env``. ``.env``
is only injected into the container at creation time via docker-compose's
``env_file:`` and is never bind-mounted, so writes to it from inside a
running container are lost on the next redeploy. ``config/`` *is*
bind-mounted and already carries the correct container-writable ownership
(it holds ``credentials.json``), so runtime overrides persist there instead.
``read_env()`` merges both files, with the runtime overrides taking
precedence, so callers don't need to know which file a given key lives in.
"""

import os
import tempfile
import threading
from pathlib import Path

# Serialises read-modify-write of the runtime overrides file across request
# threads (ORS connect, location save and Strava setup can race).
_write_lock = threading.Lock()

RUNTIME_OVERRIDES_FILENAME = 'runtime_overrides.env'


def env_path() -> Path:
    """Return the canonical path to the project .env file (read-only at runtime)."""
    return Path('.env')


def runtime_env_path() -> Path:
    """Return the path to the container-writable runtime overrides file."""
    return Path('config') / RUNTIME_OVERRIDES_FILENAME


def _parse_env_file(path: Path) -> dict:
    """Parse a key=value env file into a dict.  Returns ``{}`` when absent."""
    if not path.exists():
        return {}
    result: dict = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            result[key.strip()] = value.strip()
    return result


def read_env() -> dict:
    """Return .env merged with runtime overrides (overrides take precedence)."""
    merged = _parse_env_file(env_path())
    merged.update(_parse_env_file(runtime_env_path()))
    return merged


def write_env(data: dict) -> None:
    """Write *data* key=value pairs to the runtime overrides file under config/.

    Locked and atomic: two concurrent writers used to lose one write, and a
    truncating write_text() could be read half-written or left truncated by a
    crash, dropping keys such as HOME_LATITUDE/HOME_LONGITUDE.
    """
    with _write_lock:
        _write_env_locked(data)


def _write_env_locked(data: dict) -> None:
    ef = runtime_env_path()
    existing: dict = {}
    lines_out: list = []

    if ef.exists():
        for line in ef.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key, _, _ = stripped.partition('=')
                existing[key.strip()] = len(lines_out)
                lines_out.append(line)
            else:
                lines_out.append(line)

    for key, value in data.items():
        safe_value = str(value).replace('\n', '').replace('\r', '')
        if key in existing:
            lines_out[existing[key]] = f'{key}={safe_value}'
        else:
            lines_out.append(f'{key}={safe_value}')

    ef.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ef.parent, prefix='.runtime_overrides.', suffix='.tmp')
    try:
        # mkstemp creates the file 0600, so the secrets are never world-readable.
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(lines_out) + '\n')
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, ef)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
