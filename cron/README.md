# Cron Jobs for Smart Static Architecture

This directory contains standalone cron scripts that replace APScheduler for the Smart Static architecture migration.

## Overview

The Smart Static architecture uses cron for background automation instead of APScheduler, reducing memory usage and complexity. Each job is a standalone Python script that can be run independently.

## 📱 Push Notifications

All cron jobs support **push notifications via ntfy.sh** for proactive monitoring and alerting. See [Notifications Guide](../docs/guides/NOTIFICATIONS_GUIDE.md) for setup instructions.

**Alert Types:**
- 🚨 **Critical**: Disk space >90%, cache corruption, API unresponsive, cron failures
- ⚠️ **Warning**: Disk space >80%, stale data (>36h), security vulnerabilities
- ✅ **Info**: Weekly maintenance summary (opt-in)

**Configuration:** Set `NTFY_ENABLED=true` in `.env` to enable notifications.

## Available Jobs

### 1. Daily Analysis (`daily_analysis.py`)
- **Schedule**: Daily at 2 AM
- **Purpose**: Trigger a full fetch + analysis in the running app via `POST /api/analyze`, then poll `/api/analyze/status` until done
- **How**: Thin HTTP client — does **not** import the analysis stack (the app container does the work inside its own memory limit; see issue #498)
- **Config**: `RIDE_OPTIMIZER_URL` (default `http://127.0.0.1:$APP_PORT`), `ANALYSIS_TIMEOUT` (default 3h), `ANALYSIS_POLL_INTERVAL` (default 30s)
- **Logs**: `logs/cron_daily_analysis.log`
- **Notifications**: Sends critical alert on failure

### 2. Weather Refresh (`weather_refresh.py`)
- **Schedule**: Every 6 hours
- **Purpose**: Refresh home-location weather via `GET /api/weather` (the app caches it server-side)
- **How**: Thin HTTP client — does **not** import the service stack (see issue #498)
- **Config**: `RIDE_OPTIMIZER_URL` (default `http://127.0.0.1:$APP_PORT`)
- **Logs**: `logs/cron_weather_refresh.log`
- **Notifications**: None (non-critical job)

### 3. Cache Cleanup (`cache_cleanup.py`)
- **Schedule**: Daily at 3 AM
- **Purpose**: Remove old cache files based on retention policy
- **Retention**:
  - Activities: 30 days
  - Weather: 7 days
  - Route similarity: 90 days
  - Geocoding: Indefinite
- **Logs**: `logs/cron_cache_cleanup.log`
- **Notifications**: Sends critical alert on failure

### 4. System Health Check (`system_health.py`)
- **Schedule**: Every 15 minutes
- **Purpose**: Monitor system health and record status
- **Checks**:
  - Disk space availability (alerts at 80% and 90%)
  - Cache file accessibility (alerts on corruption)
  - Last analysis age (alerts if >36 hours)
  - API responsiveness (alerts if unresponsive)
- **Output**: Updates `cache/health_status.json`
- **Logs**: `logs/cron_system_health.log`
- **Notifications**:
  - Critical: Disk >90%, cache corruption, API down
  - Warning: Disk >80%, stale data >36h

## Installation

### Automatic Installation

Run the installation script:

```bash
cd /path/to/ride-optimizer
./cron/install_cron.sh
```

This will:
1. Make all cron scripts executable
2. Generate crontab configuration with correct paths
3. Backup existing crontab
4. Install new cron jobs

### Manual Installation

1. Make scripts executable:
```bash
chmod +x cron/*.py
```

2. Edit crontab:
```bash
crontab -e
```

3. Add these lines (replace paths):
```cron
# Ride Optimizer - Smart Static Architecture
0 2 * * * cd /path/to/ride-optimizer && /usr/bin/python3 cron/daily_analysis.py >> logs/cron.log 2>&1
0 */6 * * * cd /path/to/ride-optimizer && /usr/bin/python3 cron/weather_refresh.py >> logs/cron.log 2>&1
0 3 * * * cd /path/to/ride-optimizer && /usr/bin/python3 cron/cache_cleanup.py >> logs/cron.log 2>&1
*/15 * * * * cd /path/to/ride-optimizer && /usr/bin/python3 cron/system_health.py >> logs/cron.log 2>&1
```

## Testing Jobs

Run any job manually to test:

```bash
cd /path/to/ride-optimizer
python3 cron/daily_analysis.py
python3 cron/weather_refresh.py
python3 cron/cache_cleanup.py
python3 cron/system_health.py
```

## Monitoring

### Push Notifications

The recommended monitoring approach is **push notifications via ntfy.sh**:

1. **Setup**: Follow [Notifications Guide](../docs/guides/NOTIFICATIONS_GUIDE.md)
2. **Subscribe**: Use ntfy mobile app or web interface
3. **Receive**: Get instant alerts on your phone/desktop
4. **Act**: Respond to critical issues immediately

**Benefits:**
- Proactive monitoring without checking logs
- Mobile-first alerts on your phone
- Configurable alert types and priorities
- Throttling prevents notification spam

### View Logs

```bash
# All cron output
tail -f logs/cron.log

# Specific job logs
tail -f logs/cron_daily_analysis.log
tail -f logs/cron_weather_refresh.log
tail -f logs/cron_cache_cleanup.log
tail -f logs/cron_system_health.log
```

### Check Job History

Job execution history is stored in `cache/job_history.json`:

```bash
cat cache/job_history.json | jq '.jobs[-5:]'  # Last 5 jobs
```

### Check System Health

Current health status is in `cache/health_status.json`:

```bash
cat cache/health_status.json | jq '.'
```

## Troubleshooting

### Jobs Not Running

1. Check crontab is installed:
```bash
crontab -l | grep "Ride Optimizer"
```

2. Check cron service is running:
```bash
# Linux
sudo systemctl status cron

# macOS
sudo launchctl list | grep cron
```

3. Check logs for errors:
```bash
tail -50 logs/cron.log
```

### Permission Errors

Ensure scripts are executable:
```bash
chmod +x cron/*.py
```

### Path Issues

Cron jobs run with minimal environment. The scripts use absolute paths derived from their location, but ensure:
- Python 3 is in PATH
- Project dependencies are installed
- `.env` file exists with required configuration

## Uninstallation

To remove cron jobs:

```bash
crontab -e
# Delete the "Ride Optimizer" section
```

Or restore from backup:

```bash
crontab cron/crontab.backup.YYYYMMDD_HHMMSS
```

## Architecture Notes

### Why Cron Instead of APScheduler?

1. **Memory Efficiency**: No persistent scheduler process (saves ~50MB)
2. **Simplicity**: Standard Unix tool, no additional dependencies
3. **Reliability**: OS-level scheduling with automatic retries
4. **Monitoring**: Standard syslog integration
5. **Pi-Optimized**: Minimal resource usage for Raspberry Pi

### Job Execution Model

Each job:
1. Runs as standalone process
2. Talks to the running app over HTTP where possible (`daily_analysis.py`, `weather_refresh.py`) so the heavy lifting happens once, inside the app container's memory budget — the jobs themselves import only stdlib + `requests` + light helpers
3. Records execution in `job_history.json`
4. Exits cleanly after completion
5. No shared state between runs

### Degraded Mode Support

Jobs handle failures gracefully:
- Weather refresh: Non-critical, logs warning and continues (no notification)
- Daily analysis: Uses cached data if Strava API fails (sends notification)
- Cache cleanup: Skips if cache directory missing (sends notification on error)
- Health check: Records failures but doesn't crash (sends notifications for issues)

### Notification Throttling

To prevent notification spam, alerts are throttled:
- **Default**: Same alert not sent more than once every 6 hours
- **Configurable**: Adjust `NTFY_THROTTLE_HOURS` in `.env`
- **Per-alert**: Each alert type throttled independently
- **State file**: Throttle state stored in `data/ntfy_throttle.json`

**Example:** If disk space is at 92%, you'll receive one critical alert. If it stays at 92%, you won't receive another alert for 6 hours (unless it increases further).

## Migration from APScheduler

The cron jobs replace these APScheduler jobs:
- `run_daily_analysis()` → `daily_analysis.py`
- `run_weather_refresh()` → `weather_refresh.py`
- `run_cache_cleanup()` → `cache_cleanup.py`
- `check_system_health()` → `system_health.py`
- `run_log_rotation()` → Built into crontab (gzip + delete)

Job history format is compatible, so historical data is preserved.