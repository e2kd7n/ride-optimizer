#!/usr/bin/env python3
"""
Weekly Error-Log Triage

Scans the per-job cron logs (logs/cron_*.log — NOT the aggregate logs/cron.log,
which would double-count every line since each job's own StreamHandler output
is *also* captured into cron.log by the crontab redirect) for ERROR/WARNING/
CRITICAL lines from the last 7 days, clusters them by (logger, normalized
message), and emits one JSON line per recurring cluster to stdout.

scripts/log-triage.sh consumes this output, dedupes against existing
`auto-log-triage`-labeled GitHub issues via a fingerprint marker, and files
`gh issue create` for genuinely new/recurring clusters only — see #550.
Additive to cron/system_health.py's existing checks, not a replacement.

Run via cron (weekly, before rotate-logs.sh, so it sees the full week):
    podman exec CONTAINER python cron/log_triage.py
"""

import sys
import json
import re
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pii_sanitizer import sanitize_log_message

LOG_DIR = project_root / 'logs'
LOOKBACK_DAYS = 7

# Matches the standard format used across cron/*.py and src/logging_config.py:
# '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LINE_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - '
    r'(?P<logger>\S+) - (?P<level>WARNING|ERROR|CRITICAL) - (?P<message>.*)$'
)

# A single flaky-API warning isn't worth an issue; a handful of the same
# error over a week is. CRITICAL is rare enough by convention to flag on
# first sight.
MIN_OCCURRENCES = {'CRITICAL': 1, 'ERROR': 3, 'WARNING': 5}

# Strip volatile tokens (durations, sizes, ids) so two occurrences of the
# same underlying problem with different embedded values still cluster as
# one recurring issue instead of one-off never-repeating fingerprints.
_UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
_FLOAT_PATTERN = re.compile(r'-?\d+\.\d+')
_INT_PATTERN = re.compile(r'\b\d+\b')


def normalize_message(message: str) -> str:
    text = message.lower()
    text = _UUID_PATTERN.sub('<id>', text)
    text = _FLOAT_PATTERN.sub('<n>', text)
    text = _INT_PATTERN.sub('<n>', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:200]


def compute_fingerprint(logger_name: str, normalized: str) -> str:
    return hashlib.sha256(f'{logger_name}:{normalized}'.encode('utf-8')).hexdigest()[:12]


def iter_log_files():
    if not LOG_DIR.exists():
        return
    # cron_*.log only — excludes the aggregate cron.log (see module docstring)
    # and non-Python-logging logs like cron_weekly_maintenance.log (those
    # just won't match LOG_LINE_PATTERN and yield zero entries).
    for path in sorted(LOG_DIR.glob('cron_*.log')):
        yield path


def parse_entries(cutoff: datetime):
    entries = []
    for path in iter_log_files():
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for line in text.splitlines():
            match = LOG_LINE_PATTERN.match(line)
            if not match:
                continue
            try:
                timestamp = datetime.strptime(match.group('timestamp'), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
            if timestamp < cutoff:
                continue
            entries.append({
                'timestamp': timestamp,
                'logger': match.group('logger'),
                'level': match.group('level'),
                # Defense in depth: PIISanitizingFilter already sanitizes at
                # write time on every handler that has it attached, but
                # re-sanitizing here means a candidate is never one write
                # site away from leaking raw GPS/tokens into a public issue.
                'message': sanitize_log_message(match.group('message')),
                'source_file': path.name,
            })
    return entries


def cluster(entries):
    groups = defaultdict(list)
    for entry in entries:
        key = (entry['logger'], entry['level'], normalize_message(entry['message']))
        groups[key].append(entry)

    candidates = []
    for (logger_name, level, normalized), rows in groups.items():
        if len(rows) < MIN_OCCURRENCES.get(level, 3):
            continue
        rows.sort(key=lambda r: r['timestamp'])
        first, last = rows[0], rows[-1]
        candidates.append({
            'fingerprint': compute_fingerprint(logger_name, normalized),
            'level': level,
            'logger': logger_name,
            'occurrences': len(rows),
            'first_seen': first['timestamp'].isoformat(),
            'last_seen': last['timestamp'].isoformat(),
            'excerpt': first['message'][:300],
            'source_file': first['source_file'],
        })
    candidates.sort(key=lambda c: (-c['occurrences'], c['logger']))
    return candidates


def severity_for(candidate) -> str:
    if candidate['level'] in ('ERROR', 'CRITICAL'):
        return 'P1-high' if candidate['occurrences'] >= 10 else 'P2-medium'
    return 'P3-low'


def render_title(candidate) -> str:
    title = f"Recurring {candidate['level'].title()} in {candidate['logger']}: {candidate['excerpt']}"
    return title[:250]


def render_body(candidate, severity) -> str:
    lines = [
        f"**Severity:** {severity}",
        f"**Level:** {candidate['level']}",
        f"**Occurrences (last {LOOKBACK_DAYS} days):** {candidate['occurrences']}",
        f"**Logger:** {candidate['logger']}",
        f"**Source:** logs/{candidate['source_file']}",
        f"**First seen:** {candidate['first_seen']}",
        f"**Last seen:** {candidate['last_seen']}",
        '',
        '**Sample message:**',
        '```',
        candidate['excerpt'],
        '```',
        '',
        '_Auto-filed by `scripts/log-triage.sh` from a weekly scan of `logs/cron_*.log`. '
        'Additive to `cron/system_health.py`\'s existing checks — see #550._',
        '',
        f"<!-- auto-log-triage:fingerprint={candidate['fingerprint']} -->",
    ]
    return '\n'.join(lines)


def build_output(candidate):
    severity = severity_for(candidate)
    return {
        'fingerprint': candidate['fingerprint'],
        'title': render_title(candidate),
        'body': render_body(candidate, severity),
        'labels': ['bug', severity, 'auto-log-triage'],
        'occurrences': candidate['occurrences'],
    }


def main():
    try:
        cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
        entries = parse_entries(cutoff)
        candidates = cluster(entries)
        for candidate in candidates:
            print(json.dumps(build_output(candidate)))
        return 0
    except Exception as e:
        print(f"log_triage failed: {e}", file=sys.stderr)
        try:
            from src.config_manager import ConfigManager
            from src.ntfy_notifier import NtfyNotifier
            config = ConfigManager.get_instance()
            NtfyNotifier(config.get('notifications.ntfy')).send_cron_failure_alert('log_triage', str(e))
        except Exception:
            pass  # Notification is best-effort — never mask the real failure below.
        return 1


if __name__ == '__main__':
    sys.exit(main())
