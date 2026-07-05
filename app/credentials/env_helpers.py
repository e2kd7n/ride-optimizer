""".env file helpers — read and write key=value pairs.

Extracted verbatim from launch.py (_env_path, _read_env, _write_env).
Used by strava_bp and core_bp to persist credentials without touching
unrelated environment keys.
"""

from pathlib import Path


def env_path() -> Path:
    """Return the canonical path to the project .env file."""
    return Path('.env')


def read_env() -> dict:
    """Parse .env file into a dict.  Returns ``{}`` when the file is absent."""
    ef = env_path()
    if not ef.exists():
        return {}
    result: dict = {}
    for line in ef.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            result[key.strip()] = value.strip()
    return result


def write_env(data: dict) -> None:
    """Write *data* key=value pairs to .env, preserving existing unrelated keys."""
    ef = env_path()
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
