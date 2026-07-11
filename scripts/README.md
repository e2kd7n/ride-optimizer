# Scripts & Utilities

Utility scripts, test harnesses, and automation tools. Run Python scripts from the project root
(e.g. `python scripts/verify_dependencies.py`); shell scripts are executable (`./scripts/foo.sh`).

## Testing & Validation

- **test_imports.py** — quick syntax check across `app/`, `src/`, and the entry points
  (`launch.py`, `wsgi.py`, `main.py`), useful before installing dependencies.
- **verify_dependencies.py** — confirm required third-party packages are installed.
- **run-tests.sh** / **run_tests.py** — pytest test runner (`./scripts/run-tests.sh [all|unit|integration|coverage|quick|watch]`).
  The `.sh` file is a thin cross-platform-friendly wrapper; `run_tests.py` is the source of truth.
- **run-integration-tests.sh** / **run_integration_tests.py** — integration test runner, same wrapper relationship.

## Data & Migration

- **migrate_cache_to_json_storage.py** — copy geocoded route names from the CLI's
  `cache/route_groups_cache.json` (produced by `main.py --analyze` with geocoding enabled) into the
  web app's `data/route_groups.json`. Needed because the web/cron analysis pipeline runs with
  geocoding disabled (Nominatim rate limits) — see `AnalysisService`.
- **set_rate_limit_block.py** — manually write a geocoding rate-limit block file when Nominatim has
  rate-limited this IP but the app hasn't detected it yet.

## Scheduling

- **setup_windows_tasks.py** — Windows Task Scheduler equivalents of the Unix cron jobs in `cron/`
  (`--install`/`--uninstall`/`--list`). On Unix, use `cron/install_cron.sh` instead.
- **send_maintenance_summary.py** — send a weekly maintenance summary notification via ntfy; called
  by `weekly-maintenance.sh`.

## GitHub Integration

- **close-issue.sh** — close a GitHub issue with a properly formatted comment (handles special characters).
- **align-labels.sh** — align GitHub label sets across the ride-optimizer and mealplanner projects.
- **update-issue-priorities.sh** — regenerate `ISSUE_PRIORITIES.md` from live GitHub issues.
- **verify-issue-closures.sh** — verify issues referenced in recent commits are actually closed.
- **weekly-maintenance.sh** — backs up docs/plans, pushes them to the private backups repo, checks
  git/branch/PR status, kicks off `update-issue-priorities.sh` in the background, and sends a
  maintenance summary.

## Backup & Restore

- **backup-env.sh** — back up `.env` and `*.backup` files to the private backups repository.
- **backup_caches.sh** / **restore-caches.sh** — back up and restore analysis caches
  (`cache/*.json`, `data/route_groups.json`, `data/long_rides.json`, `data/cache/activities.json`).

## Raspberry Pi Deployment

- **pi-auto-update.sh** — pull the latest image from GHCR and redeploy if it changed; runs nightly
  via a systemd timer, or manually with `--force`.
- **pi-update-setup.sh** — install the systemd service + timer for `pi-auto-update.sh` (run once on the Pi).
- **cleanup-pi.sh** — remove unused containers/images/build cache on the Pi without touching volumes.
- **build-pi.sh** — last-resort local ARM build when GHCR/CI is unreachable; normal deploys go
  through CI + `pi-auto-update.sh` instead.

## Archive

`archive/cli-legacy/` holds scripts from the pre-web-platform CLI era (`main.py` + `src/`-only
structure) that no longer apply to the current Flask `app/` architecture. See its README for details.

---

*Last Updated: 2026-07-11*
