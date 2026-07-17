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

from pathlib import Path

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
    """Write *data* key=value pairs to the runtime overrides file under config/."""
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

    ef.write_text('\n'.join(lines_out) + '\n', encoding='utf-8')
    ef.chmod(0o600)
