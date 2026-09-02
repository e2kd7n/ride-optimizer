#!/bin/bash
# Weekly log rotation.
#
# logs/cron.log and the per-job logs/cron_*.log files are appended to by
# cron jobs running as often as every 2 hours, so their mtime never crosses
# a `find -mtime +7` threshold — that was the old rotation trigger and it
# never fired (#545 / #553). This rotates unconditionally on a fixed
# schedule instead, regardless of mtime.
#
# None of these files are held open by a long-lived process — each cron job
# (and main.py's CLI debug.log) opens its log file fresh per invocation via
# `podman exec ... >> logs/cron.log` or a fresh FileHandler — so a plain
# rename+gzip is safe here; no copytruncate is needed.
#
# Usage: ./scripts/rotate-logs.sh
# Installed weekly via cron/crontab.template (Sunday 4 AM).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
DATE_STAMP="$(date +%Y%m%d)"

[ -d "$LOG_DIR" ] || exit 0

for f in "$LOG_DIR"/*.log; do
    [ -e "$f" ] || continue
    [ -s "$f" ] || continue  # skip empty files — nothing to rotate
    mv "$f" "${f}.${DATE_STAMP}"
    gzip "${f}.${DATE_STAMP}"
done

find "$LOG_DIR" -name "*.log.*.gz" -mtime +30 -delete
