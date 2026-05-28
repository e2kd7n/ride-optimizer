# ntfy.sh Push Notifications Guide

This guide explains how to set up and use push notifications for Ride Optimizer maintenance alerts and system health monitoring.

## 📱 What is ntfy.sh?

[ntfy.sh](https://ntfy.sh) is a simple, free push notification service that works on web, iOS, and Android. It requires no account or registration - just subscribe to a topic and start receiving notifications.

## 🎯 Benefits

- **Proactive Monitoring**: Get alerted immediately when issues occur
- **Reduced Downtime**: Fix problems before they become critical
- **Peace of Mind**: Know your system is healthy without checking logs
- **Mobile-First**: Receive notifications on your phone, tablet, or desktop
- **Privacy-Focused**: Self-hosted option available for complete control

## 🚀 Quick Start

### 1. Generate a Unique Topic

Your topic name should be unique and unguessable to prevent others from subscribing to your notifications:

```bash
# Generate a unique topic ID
python3 -c "import uuid; print(f'ride-optimizer-{uuid.uuid4().hex[:8]}')"
# Example output: ride-optimizer-a3f7b2c1
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# ntfy.sh Push Notifications
NTFY_ENABLED=true
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=ride-optimizer-a3f7b2c1  # Use your unique topic
NTFY_PRIORITY_CRITICAL=urgent
NTFY_PRIORITY_WARNING=high
NTFY_PRIORITY_INFO=default
NTFY_THROTTLE_HOURS=6
```

### 3. Subscribe to Notifications

#### Web Browser
1. Visit [ntfy.sh](https://ntfy.sh)
2. Enter your topic name (e.g., `ride-optimizer-a3f7b2c1`)
3. Click "Subscribe"
4. Bookmark the page for easy access

#### iOS App
1. Download [ntfy](https://apps.apple.com/us/app/ntfy/id1625396347) from the App Store
2. Open the app and tap "+"
3. Enter your topic name
4. Tap "Subscribe"
5. Enable notifications in iOS Settings

#### Android App
1. Download [ntfy](https://play.google.com/store/apps/details?id=io.heckel.ntfy) from Google Play
2. Open the app and tap "+"
3. Enter your topic name
4. Tap "Subscribe"
5. Grant notification permissions

### 4. Test Your Setup

Send a test notification:

```python
from src.config import Config
from src.ntfy_notifier import NtfyNotifier

config = Config()
notifier = NtfyNotifier(config.get('notifications.ntfy'))
notifier.send_info('Test Notification', 'Ride Optimizer notifications are working!')
```

## 📊 Alert Types

### Critical Alerts (🚨 Urgent Priority)

**Immediate action required** - these indicate serious problems:

- **Disk Space Critical** (>90% full)
  - Risk of application failure
  - Action: Run cache cleanup or free disk space
  
- **Cache Corruption Detected**
  - Data integrity issues
  - Action: Run cache cleanup or rebuild cache
  
- **API Unresponsive**
  - Application not serving requests
  - Action: Check server status and logs
  
- **Cron Job Failures**
  - Background tasks not executing
  - Action: Check logs and cron configuration

### Warning Alerts (⚠️ High Priority)

**Action needed soon** - these indicate developing problems:

- **Disk Space Warning** (>80% full)
  - Approaching critical threshold
  - Action: Monitor disk space, consider cleanup
  
- **Stale Data** (>36 hours since last analysis)
  - Data becoming outdated
  - Action: Check cron job status
  
- **Security Vulnerabilities** (from weekly maintenance)
  - Dependencies need updating
  - Action: Review and update dependencies

### Informational Alerts (✅ Default Priority)

**Optional** - these provide status updates:

- **Weekly Maintenance Completed**
  - Summary of health check results
  - Opt-in: Set `maintenance_summary: true` in config
  
- **Cache Cleanup Completed**
  - Disk space recovered
  - Informational only

## ⚙️ Configuration

### Alert Type Configuration

Enable or disable specific alert types in `config/config.yaml`:

```yaml
notifications:
  ntfy:
    enabled: ${NTFY_ENABLED}
    server: ${NTFY_SERVER}
    topic: ${NTFY_TOPIC}
    throttle_hours: 6
    alert_types:
      disk_space_critical: true      # Critical disk space alerts
      disk_space_warning: true       # Warning disk space alerts
      stale_data: true               # Stale data alerts
      cache_corruption: true         # Cache corruption alerts
      api_unresponsive: true         # API health alerts
      cron_failure: true             # Cron job failure alerts
      security_vulnerabilities: true # Security alerts
      maintenance_summary: false     # Weekly summary (opt-in)
```

### Throttling

Alerts are throttled to prevent notification spam. By default, the same alert will not be sent more than once every 6 hours.

Adjust throttling in `.env`:

```bash
NTFY_THROTTLE_HOURS=6  # Minimum hours between duplicate alerts
```

### Priority Levels

Customize notification priorities:

```bash
NTFY_PRIORITY_CRITICAL=urgent  # Options: max, urgent, high, default, low, min
NTFY_PRIORITY_WARNING=high
NTFY_PRIORITY_INFO=default
```

## 🔒 Security & Privacy

### Topic Privacy

- **Use unique, unguessable topic names** - anyone who knows your topic can subscribe
- **Never share your topic publicly** - treat it like a password
- **Rotate topics periodically** - generate a new topic every few months

### Data Privacy

- **No sensitive data in notifications** - credentials, tokens, and PII are never included
- **Minimal information** - only essential details for troubleshooting
- **Self-hosted option** - run your own ntfy server for complete control

### Self-Hosted ntfy Server

For maximum privacy, run your own ntfy server:

1. Follow the [ntfy server installation guide](https://docs.ntfy.sh/install/)
2. Update your `.env`:
   ```bash
   NTFY_SERVER=https://your-ntfy-server.com
   ```

## 📱 Notification Examples

### Critical Alert
```
🚨 Ride Optimizer: Disk Space Critical
Disk usage: 92% (8.2 GB free)
Action: Run cache cleanup or free disk space
Priority: urgent
Tags: critical, disk-space
```

### Warning Alert
```
⚠️ Ride Optimizer: Data Becoming Stale
Last analysis: 38 hours ago
Action: Check cron job status
Priority: high
Tags: warning, stale-data
```

### Info Alert
```
✅ Ride Optimizer: Weekly Maintenance Complete
- 0 security vulnerabilities
- 3 issues closed
- Cache: 245 MB
Priority: default
Tags: maintenance, summary
```

## 🛠️ Troubleshooting

### Not Receiving Notifications

1. **Check configuration**:
   ```bash
   # Verify NTFY_ENABLED is true
   grep NTFY_ENABLED .env
   
   # Verify topic is set
   grep NTFY_TOPIC .env
   ```

2. **Test connectivity**:
   ```bash
   curl -d "Test message" https://ntfy.sh/your-topic-name
   ```

3. **Check logs**:
   ```bash
   tail -f logs/cron_system_health.log
   ```

4. **Verify subscription**:
   - Open ntfy app/web
   - Confirm you're subscribed to the correct topic
   - Check notification permissions

### Alerts Being Throttled

If you're not receiving expected alerts, they may be throttled:

1. **Check throttle state**:
   ```bash
   cat data/ntfy_throttle.json
   ```

2. **Clear throttle state** (for testing):
   ```bash
   rm data/ntfy_throttle.json
   ```

3. **Adjust throttle period** in `.env`:
   ```bash
   NTFY_THROTTLE_HOURS=1  # More frequent alerts (not recommended for production)
   ```

### Too Many Notifications

If you're receiving too many notifications:

1. **Increase throttle period**:
   ```bash
   NTFY_THROTTLE_HOURS=12  # Less frequent alerts
   ```

2. **Disable specific alert types** in `config/config.yaml`:
   ```yaml
   alert_types:
     disk_space_warning: false  # Disable warning-level disk alerts
   ```

3. **Fix underlying issues** - notifications indicate real problems that should be addressed

## 📚 Integration Points

Notifications are integrated into:

- **System Health Check** (`cron/system_health.py`) - Runs every 15 minutes
  - Disk space monitoring
  - Stale data detection
  - Cache health checks
  - API responsiveness

- **Daily Analysis** (`cron/daily_analysis.py`) - Runs daily at 2 AM
  - Analysis failures
  - Data processing errors

- **Cache Cleanup** (`cron/cache_cleanup.py`) - Runs daily at 3 AM
  - Cleanup failures
  - Disk space issues

- **Weekly Maintenance** (`scripts/weekly-maintenance.sh`) - Runs weekly
  - Security vulnerabilities
  - Maintenance summary (opt-in)

## 🎨 Customization

### Custom Alert Messages

Create custom alerts in your code:

```python
from src.config import Config
from src.ntfy_notifier import NtfyNotifier

config = Config()
notifier = NtfyNotifier(config.get('notifications.ntfy'))

# Send custom critical alert
notifier.send_critical(
    title='Custom Critical Alert',
    message='Something important happened',
    tags=['custom', 'critical'],
    alert_key='custom_alert'  # For throttling
)

# Send custom warning
notifier.send_warning(
    title='Custom Warning',
    message='Something to watch',
    tags=['custom', 'warning']
)

# Send custom info
notifier.send_info(
    title='Custom Info',
    message='FYI: Something happened',
    tags=['custom', 'info']
)
```

### Custom Alert Types

Add new alert types to `config/config.yaml`:

```yaml
alert_types:
  custom_alert_type: true
```

Then use in code:

```python
if notifier.should_send_alert('custom_alert_type'):
    notifier.send_alert(
        title='Custom Alert',
        message='Custom message',
        priority='high',
        tags=['custom'],
        alert_key='custom_alert_type'
    )
```

## 📖 Additional Resources

- [ntfy.sh Documentation](https://docs.ntfy.sh/)
- [ntfy.sh GitHub](https://github.com/binwiederhier/ntfy)
- [System Health Monitoring](../cron/README.md)
- [Maintenance Checklist](../releases/maintenance/MAINTENANCE_CHECKLIST.md)

## 💡 Best Practices

1. **Use unique topic names** - prevent unauthorized subscriptions
2. **Enable critical alerts only** - avoid notification fatigue
3. **Act on alerts promptly** - they indicate real problems
4. **Review throttle settings** - balance awareness with spam prevention
5. **Test regularly** - ensure notifications are working
6. **Monitor alert frequency** - high frequency indicates systemic issues
7. **Document custom alerts** - help future maintainers understand notifications

## 🤝 Support

For issues or questions:
- Check logs in `logs/` directory
- Review [Technical Specification](../TECHNICAL_SPEC.md)
- Open an issue on GitHub

---

**Made with Bob** 🤖