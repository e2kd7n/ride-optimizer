"""
Migrate geocoded route names from the CLI cache to the web app data directory.

Reads:   cache/route_groups_cache.json  (updated by geocoding process)
Updates: data/route_groups.json         (read by web app via JSONStorage)

Matches groups by id and copies the name field. All other fields in the web
app data are preserved untouched.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Resolve project root relative to this script's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent

CACHE_FILE = PROJECT_ROOT / 'cache' / 'route_groups_cache.json'
DATA_FILE  = PROJECT_ROOT / 'data'  / 'route_groups.json'


def load_json(path: Path) -> dict:
    with open(path, 'r') as f:
        return json.load(f)


def atomic_write(path: Path, data: dict) -> None:
    """Write data to path atomically using a sibling temp file."""
    tmp = path.with_suffix('.tmp')
    try:
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def main() -> int:
    if not CACHE_FILE.exists():
        print(f"ERROR: Cache file not found: {CACHE_FILE}", file=sys.stderr)
        return 1

    if not DATA_FILE.exists():
        print(f"ERROR: Data file not found: {DATA_FILE}", file=sys.stderr)
        return 1

    cache = load_json(CACHE_FILE)
    web_data = load_json(DATA_FILE)

    # Build id→name map from CLI cache
    cache_groups = cache.get('groups', [])
    name_map = {g['id']: g['name'] for g in cache_groups if 'id' in g and 'name' in g}

    if not name_map:
        print("ERROR: No groups found in cache file.", file=sys.stderr)
        return 1

    # Apply names to web app data
    updated = 0
    for group in web_data.get('route_groups', []):
        gid = group.get('id')
        if gid and gid in name_map:
            group['name'] = name_map[gid]
            updated += 1

    atomic_write(DATA_FILE, web_data)

    print(f"Migration complete: {updated}/{len(web_data.get('route_groups', []))} route names updated in {DATA_FILE}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
