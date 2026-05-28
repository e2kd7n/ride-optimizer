# GitHub Issue: Incorporate ntfy.sh Push Notifications for Maintenance Alerts

## Issue Metadata
- **Title:** Add ntfy.sh push notifications for maintenance and system health alerts
- **Labels:** `P2-medium,enhancement,backend,infrastructure,notifications,raspberry-pi`
- **Milestone:** `v0.15.0`
- **Assignees:** (to be assigned)

---

## 📋 Summary

Integrate [ntfy.sh](https://ntfy.sh) push notifications to proactively alert users when maintenance actions are needed to keep the Ride Optimizer application healthy and operational. This addresses the gap between automated health monitoring and user awareness, particularly for Raspberry Pi deployments where users may not regularly check logs.

## 🎯 Problem Statement

Currently, the application has robust health monitoring via [`cron/system_health.py`](../cron/system_health.py) that runs every 15 minutes and checks:
- Disk space availability
- Cache file accessibility  
- Last analysis age (warns if >48 hours)
- API responsiveness

However, **users are not proactively notified** when issues are detected. Problems can persist unnoticed until:
- The application stops working entirely
- Data becomes stale (>48 hours since last analysis)
- Disk space fills up
- Cache corruption occurs

For Raspberry Pi deployments, users may not regularly SSH in to check logs, leading to degraded service or complete failures going undetected.

## 💡 Proposed Solution

Integrate ntfy.sh push notifications to send alerts when:

### Critical Alerts (Immediate Action Required)
- **Disk space >90% full** - Risk of application failure
- **Last analysis >48 hours old** - Stale data affecting recommendations
- **Cache file corruption detected** - Data integrity issues
- **API unresponsive** - Application not serving requests
- **Cron job failures** - Background tasks not executing

### Warning Alerts (Action Needed Soon)
- **Disk space >80% full** - Approaching critical threshold
- **Last analysis >36 hours old** - Data becoming stale
- **Dependency security vulnerabilities** - From weekly maintenance checks
- **Rate limit approaching** - Strava API usage >80% of limit

### Informational Alerts (Optional)
- **Weekly maintenance completed** - Summary of health check
- **Cache cleanup completed** - Disk space recovered
- **Dependency updates available** - Non-security updates

## 🏗️ Technical Architecture

### Integration Points

1. **System Health Check** ([`cron/system_health.py`](../cron/system_health.py))
   - Add ntfy notification on status changes (healthy → degraded → unhealthy)
   - Send alerts when specific thresholds exceeded
   - Implement alert throttling (max 1 alert per issue per 6 hours)

2. **Cron Jobs** (all scripts in [`cron/`](../cron/))
   - Send failure notifications on exceptions
   - Report completion status for critical jobs
   - Include error details and suggested remediation

3. **Weekly Maintenance** ([`scripts/weekly-maintenance.sh`](../scripts/weekly-maintenance.sh))
   - Send summary notification with key metrics
   - Alert on security vulnerabilities found
   - Report on open P0/P1 issues

### Configuration

Add to `.env`:
```bash
# ntfy.sh Configuration
NTFY_ENABLED=true
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=ride-optimizer-alerts-{unique-id}
NTFY_PRIORITY_CRITICAL=urgent
NTFY_PRIORITY_WARNING=high
NTFY_PRIORITY_INFO=default
```

Add to [`config/config.yaml`](../config/config.yaml):
```yaml
notifications:
  ntfy:
    enabled: ${NTFY_ENABLED}
    server: ${NTFY_SERVER}
    topic: ${NTFY_TOPIC}
    priorities:
      critical: ${NTFY_PRIORITY_CRITICAL}
      warning: ${NTFY_PRIORITY_WARNING}
      info: ${NTFY_PRIORITY_INFO}
    throttle_hours: 6  # Minimum hours between duplicate alerts
    alert_types:
      disk_space_critical: true
      disk_space_warning: true
      stale_data: true
      cache_corruption: true
      api_unresponsive: true
      cron_failure: true
      security_vulnerabilities: true
      maintenance_summary: false  # Opt-in
```

### Implementation Files

Create new module: `src/ntfy_notifier.py`
```python
class NtfyNotifier:
    """Send push notifications via ntfy.sh"""
    
    def send_alert(self, title: str, message: str, priority: str, tags: List[str])
    def send_critical(self, title: str, message: str)
    def send_warning(self, title: str, message: str)
    def send_info(self, title: str, message: str)
    def should_send_alert(self, alert_key: str) -> bool  # Throttling logic
```

Update existing files:
- [`cron/system_health.py`](../cron/system_health.py) - Add notification calls
- [`cron/daily_analysis.py`](../cron/daily_analysis.py) - Notify on failures
- [`cron/cache_cleanup.py`](../cron/cache_cleanup.py) - Notify on errors
- [`cron/weather_refresh.py`](../cron/weather_refresh.py) - Notify on failures
- [`scripts/weekly-maintenance.sh`](../scripts/weekly-maintenance.sh) - Send summary

## 📝 Acceptance Criteria

- [ ] `src/ntfy_notifier.py` module created with full notification API
- [ ] Configuration added to `.env.example` and `config/config.yaml`
- [ ] System health check sends alerts on status degradation
- [ ] All cron jobs send failure notifications with error details
- [ ] Alert throttling prevents notification spam (max 1 per 6 hours per issue)
- [ ] Weekly maintenance sends optional summary notification
- [ ] Documentation added to [`cron/README.md`](../cron/README.md)
- [ ] User guide created in [`docs/guides/NOTIFICATIONS_GUIDE.md`](../docs/guides/)
- [ ] Unit tests for `NtfyNotifier` class (>80% coverage)
- [ ] Integration test for end-to-end notification flow
- [ ] Notifications work on Raspberry Pi deployment
- [ ] Mobile app setup instructions included (iOS/Android)

## 🧪 Testing Strategy

### Unit Tests (`tests/test_ntfy_notifier.py`)
- Test notification formatting
- Test priority mapping
- Test throttling logic
- Test configuration validation
- Mock HTTP requests to ntfy.sh

### Integration Tests (`tests/test_ntfy_integration.py`)
- Test actual notification delivery (to test topic)
- Test error handling for network failures
- Test retry logic
- Test alert deduplication

### Manual Testing
- Trigger disk space warning (fill disk to 85%)
- Stop daily analysis cron job (wait 48+ hours)
- Corrupt cache file and verify alert
- Run weekly maintenance and verify summary

## 📚 Documentation Requirements

### User Guide (`docs/guides/NOTIFICATIONS_GUIDE.md`)
- ntfy.sh overview and benefits
- Setup instructions (web, iOS, Android apps)
- Topic subscription process
- Alert types and meanings
- Troubleshooting common issues
- Privacy considerations (self-hosted ntfy option)

### Technical Documentation
- Update [`cron/README.md`](../cron/README.md) with notification behavior
- Add notification architecture to [`docs/TECHNICAL_SPEC.md`](../docs/TECHNICAL_SPEC.md)
- Document alert throttling algorithm
- Include example notification payloads

## 🔒 Security Considerations

- **Topic Privacy**: Use unique, unguessable topic names (e.g., `ride-optimizer-{uuid}`)
- **No Sensitive Data**: Never include credentials, tokens, or PII in notifications
- **Self-Hosted Option**: Support self-hosted ntfy servers for privacy-conscious users
- **Rate Limiting**: Respect ntfy.sh rate limits (no more than 1 req/sec)
- **Opt-Out**: Allow users to disable notifications entirely

## 🎨 User Experience

### Notification Examples

**Critical Alert:**
```
🚨 Ride Optimizer: Disk Space Critical
Disk usage: 92% (8.2 GB free)
Action: Run cache cleanup or free disk space
Priority: urgent
Tags: critical, disk-space
```

**Warning Alert:**
```
⚠️ Ride Optimizer: Data Becoming Stale
Last analysis: 38 hours ago
Action: Check cron job status
Priority: high
Tags: warning, stale-data
```

**Info Alert:**
```
✅ Ride Optimizer: Weekly Maintenance Complete
- 0 security vulnerabilities
- 3 issues closed
- Cache: 245 MB
Priority: default
Tags: maintenance, summary
```

## 🔗 Related Issues

- #152 - Architecture Simplification (Smart Static architecture)
- Maintenance checklist: [`docs/releases/maintenance/MAINTENANCE_CHECKLIST.md`](../docs/releases/maintenance/MAINTENANCE_CHECKLIST.md)
- System health monitoring: [`cron/system_health.py`](../cron/system_health.py)

## 📊 Success Metrics

- **Alert Accuracy**: >95% of alerts require actual user action
- **False Positive Rate**: <5% of alerts are false alarms
- **Response Time**: Users respond to critical alerts within 4 hours
- **User Satisfaction**: Positive feedback on notification usefulness
- **System Uptime**: Improved uptime due to proactive issue detection

## 🚀 Implementation Phases

### Phase 1: Core Infrastructure (v0.15.0)
- Implement `NtfyNotifier` class
- Add configuration support
- Integrate with system health check
- Basic documentation

### Phase 2: Cron Integration (v0.15.0)
- Add notifications to all cron jobs
- Implement alert throttling
- Add weekly maintenance summary

### Phase 3: Polish & Documentation (v0.15.0)
- Comprehensive user guide
- Mobile app setup instructions
- Integration tests
- Self-hosted ntfy support

## 💭 Future Enhancements (Post-v0.15.0)

- **Custom Alert Rules**: User-defined thresholds and alert types
- **Alert History**: Web UI to view past notifications
- **Multi-Channel**: Support email, Slack, Discord in addition to ntfy
- **Smart Throttling**: ML-based alert prioritization
- **Actionable Notifications**: Deep links to fix issues directly from notification

## 🏷️ Issue Creation Command

```bash
gh issue create \
  --title "Add ntfy.sh push notifications for maintenance and system health alerts" \
  --label "P2-medium,enhancement,backend,infrastructure,notifications,raspberry-pi" \
  --milestone "v0.15.0" \
  --body-file .bob/github_issue_ntfy_notifications.md
```

---

**Estimated Effort:** 8-12 hours
**Priority Justification:** P2-medium - Valuable for proactive maintenance but not blocking current functionality
**Target Release:** v0.15.0 - Aligns with advanced features and long-term enhancements