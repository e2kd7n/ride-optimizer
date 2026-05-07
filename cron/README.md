# Cron Jobs for Smart Static Architecture

This directory contains standalone cron scripts that replace APScheduler for the Smart Static architecture migration.

## Overview

The Smart Static architecture uses cron for background automation instead of APScheduler, reducing memory usage and complexity. Each job is a standalone Python script that can be run independently.

## Available Jobs

### 1. Daily Analysis (`daily_analysis.py`)
- **Schedule**: Daily at 2 AM
- **Purpose**: Fetch latest activities from Strava and perform full route analysis
- **Output**: Updates `cache/activities_cache.json`, `cache/route_groups_cache.json`
- **Logs**: `logs/cron_daily_analysis.log`

### 2. Weather Refresh (`weather_refresh.py`)
- **Schedule**: Every 6 hours
- **Purpose**: Update weather data for home location
- **Output**: Updates `cache/weather_cache.json`
- **Logs**: `logs/cron_weather_refresh.log`

### 3. Cache Cleanup (`cache_cleanup.py`)
- **Schedule**: Daily at 3 AM
- **Purpose**: Remove old cache files based on retention policy
- **Retention**: 
  - Activities: 30 days
  - Weather: 7 days
  - Route similarity: 90 days
  - Geocoding: Indefinite
- **Logs**: `logs/cron_cache_cleanup.log`

### 4. System Health Check (`system_health.py`)
- **Schedule**: Every 15 minutes
- **Purpose**: Monitor system health and record status
- **Checks**:
  - Disk space availability
  - Cache file accessibility
  - Last analysis age
  - API responsiveness
- **Output**: Updates `cache/health_status.json`
- **Logs**: `logs/cron_system_health.log`

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
2. Loads only required services
3. Records execution in `job_history.json`
4. Exits cleanly after completion
5. No shared state between runs

### Degraded Mode Support

Jobs handle failures gracefully:
- Weather refresh: Non-critical, logs warning and continues
- Daily analysis: Uses cached data if Strava API fails
- Cache cleanup: Skips if cache directory missing
- Health check: Records failures but doesn't crash

## Migration from APScheduler

The cron jobs replace these APScheduler jobs:
- `run_daily_analysis()` → `daily_analysis.py`
- `run_weather_refresh()` → `weather_refresh.py`
- `run_cache_cleanup()` → `cache_cleanup.py`
- `check_system_health()` → `system_health.py`
- `run_log_rotation()` → Built into crontab (gzip + delete)

Job history format is compatible, so historical data is preserved.