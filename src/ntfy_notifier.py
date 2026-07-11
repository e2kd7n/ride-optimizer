#!/usr/bin/env python3
"""
ntfy.sh Push Notification Module

Sends push notifications via ntfy.sh for system health alerts and maintenance events.
Includes alert throttling to prevent notification spam.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import os
import json
from src.secure_logger import SecureLogger
from src.json_storage import secure_chmod
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = SecureLogger(__name__)


@dataclass
class Alert:
    """Represents a notification alert."""
    title: str
    message: str
    priority: str
    tags: List[str]
    timestamp: str
    alert_key: str


class NtfyNotifier:
    """Send push notifications via ntfy.sh with throttling."""
    
    # Priority levels
    PRIORITY_CRITICAL = "urgent"
    PRIORITY_WARNING = "high"
    PRIORITY_INFO = "default"
    
    # Alert types
    ALERT_DISK_CRITICAL = "disk_space_critical"
    ALERT_DISK_WARNING = "disk_space_warning"
    ALERT_STALE_DATA = "stale_data"
    ALERT_CACHE_CORRUPTION = "cache_corruption"
    ALERT_API_UNRESPONSIVE = "api_unresponsive"
    ALERT_CRON_FAILURE = "cron_failure"
    ALERT_SECURITY_VULN = "security_vulnerabilities"
    ALERT_MAINTENANCE_SUMMARY = "maintenance_summary"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ntfy notifier.
        
        Args:
            config: Configuration dictionary (if None, loads from environment)
        """
        self.session = requests.Session()
        self.enabled = self._get_config_value(config, 'enabled', 'NTFY_ENABLED', 'false').lower() == 'true'
        self.server = self._get_config_value(config, 'server', 'NTFY_SERVER', 'https://ntfy.sh')
        self.topic = self._get_config_value(config, 'topic', 'NTFY_TOPIC', None)
        
        # Priority mappings
        self.priority_critical = self._get_config_value(config, 'priorities.critical', 'NTFY_PRIORITY_CRITICAL', self.PRIORITY_CRITICAL)
        self.priority_warning = self._get_config_value(config, 'priorities.warning', 'NTFY_PRIORITY_WARNING', self.PRIORITY_WARNING)
        self.priority_info = self._get_config_value(config, 'priorities.info', 'NTFY_PRIORITY_INFO', self.PRIORITY_INFO)
        
        # Throttling configuration
        self.throttle_hours = int(self._get_config_value(config, 'throttle_hours', 'NTFY_THROTTLE_HOURS', '6'))
        
        # Alert type configuration
        self.alert_types = self._load_alert_types(config)
        
        # Throttle state file
        project_root = Path(__file__).parent.parent
        self.throttle_file = project_root / 'data' / 'ntfy_throttle.json'
        self.throttle_file.parent.mkdir(exist_ok=True)
        
        if not self.enabled:
            logger.info("ntfy notifications disabled in configuration")
        elif not self.topic:
            logger.warning("ntfy notifications enabled but no topic configured")
            self.enabled = False
    
    def _get_config_value(self, config: Optional[Dict], config_key: str, env_key: str, default: Optional[str]) -> Optional[str]:
        """Get configuration value from config dict or environment variable."""
        if config:
            # Support dot notation for nested keys
            keys = config_key.split('.')
            value = config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if value is not None:
                return str(value)
        
        # Fall back to environment variable
        return os.getenv(env_key, default)
    
    def _load_alert_types(self, config: Optional[Dict]) -> Dict[str, bool]:
        """Load alert type configuration."""
        default_types = {
            self.ALERT_DISK_CRITICAL: True,
            self.ALERT_DISK_WARNING: True,
            self.ALERT_STALE_DATA: True,
            self.ALERT_CACHE_CORRUPTION: True,
            self.ALERT_API_UNRESPONSIVE: True,
            self.ALERT_CRON_FAILURE: True,
            self.ALERT_SECURITY_VULN: True,
            self.ALERT_MAINTENANCE_SUMMARY: False,  # Opt-in
        }
        
        if config and 'alert_types' in config:
            return {**default_types, **config['alert_types']}
        
        return default_types
    
    def _load_throttle_state(self) -> Dict[str, str]:
        """Load throttle state from file."""
        if not self.throttle_file.exists():
            return {}
        
        try:
            with open(self.throttle_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load throttle state: {e}")
            return {}
    
    def _save_throttle_state(self, state: Dict[str, str]):
        """Save throttle state to file."""
        try:
            with open(self.throttle_file, 'w') as f:
                json.dump(state, f, indent=2)
            secure_chmod(self.throttle_file)
        except Exception as e:
            logger.error(f"Failed to save throttle state: {e}")
    
    def should_send_alert(self, alert_key: str) -> bool:
        """
        Check if alert should be sent based on throttling rules.
        
        Args:
            alert_key: Unique key for the alert type
            
        Returns:
            True if alert should be sent, False if throttled
        """
        if not self.enabled:
            return False
        
        # Check if alert type is enabled
        if alert_key in self.alert_types and not self.alert_types[alert_key]:
            logger.debug(f"Alert type {alert_key} is disabled")
            return False
        
        # Load throttle state
        state = self._load_throttle_state()
        
        # Check if alert was recently sent
        if alert_key in state:
            last_sent = datetime.fromisoformat(state[alert_key])
            time_since = datetime.now() - last_sent
            
            if time_since < timedelta(hours=self.throttle_hours):
                logger.debug(f"Alert {alert_key} throttled (last sent {time_since.total_seconds() / 3600:.1f}h ago)")
                return False
        
        return True
    
    def _record_alert_sent(self, alert_key: str):
        """Record that an alert was sent."""
        state = self._load_throttle_state()
        state[alert_key] = datetime.now().isoformat()
        self._save_throttle_state(state)
    
    def send_alert(self, title: str, message: str, priority: str, tags: List[str], alert_key: Optional[str] = None) -> bool:
        """
        Send a notification via ntfy.sh.
        
        Args:
            title: Notification title
            message: Notification message
            priority: Priority level (urgent, high, default, low, min)
            tags: List of tags for categorization
            alert_key: Unique key for throttling (if None, no throttling)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Notifications disabled, skipping alert")
            return False
        
        # Check throttling
        if alert_key and not self.should_send_alert(alert_key):
            return False
        
        try:
            # Prepare notification payload
            url = f"{self.server}/{self.topic}"
            headers = {
                "Title": title,
                "Priority": priority,
                "Tags": ",".join(tags)
            }
            
            # Send notification
            response = self.session.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Notification sent: {title}")
                if alert_key:
                    self._record_alert_sent(alert_key)
                return True
            else:
                logger.error(f"Failed to send notification: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def send_critical(self, title: str, message: str, tags: Optional[List[str]] = None, alert_key: Optional[str] = None) -> bool:
        """
        Send a critical priority notification.
        
        Args:
            title: Notification title
            message: Notification message
            tags: Optional list of tags (default: ['critical'])
            alert_key: Unique key for throttling
            
        Returns:
            True if notification sent successfully
        """
        if tags is None:
            tags = ['critical']
        return self.send_alert(title, message, self.priority_critical, tags, alert_key)
    
    def send_warning(self, title: str, message: str, tags: Optional[List[str]] = None, alert_key: Optional[str] = None) -> bool:
        """
        Send a warning priority notification.
        
        Args:
            title: Notification title
            message: Notification message
            tags: Optional list of tags (default: ['warning'])
            alert_key: Unique key for throttling
            
        Returns:
            True if notification sent successfully
        """
        if tags is None:
            tags = ['warning']
        return self.send_alert(title, message, self.priority_warning, tags, alert_key)
    
    def send_info(self, title: str, message: str, tags: Optional[List[str]] = None, alert_key: Optional[str] = None) -> bool:
        """
        Send an informational priority notification.
        
        Args:
            title: Notification title
            message: Notification message
            tags: Optional list of tags (default: ['info'])
            alert_key: Unique key for throttling
            
        Returns:
            True if notification sent successfully
        """
        if tags is None:
            tags = ['info']
        return self.send_alert(title, message, self.priority_info, tags, alert_key)
    
    def send_disk_space_critical(self, percent_used: float, free_gb: float) -> bool:
        """Send critical disk space alert."""
        title = "🚨 Ride Optimizer: Disk Space Critical"
        message = f"Disk usage: {percent_used:.1f}% ({free_gb:.1f} GB free)\nAction: Run cache cleanup or free disk space"
        return self.send_critical(title, message, tags=['critical', 'disk-space'], alert_key=self.ALERT_DISK_CRITICAL)
    
    def send_disk_space_warning(self, percent_used: float, free_gb: float) -> bool:
        """Send warning disk space alert."""
        title = "⚠️ Ride Optimizer: Disk Space Warning"
        message = f"Disk usage: {percent_used:.1f}% ({free_gb:.1f} GB free)\nAction: Monitor disk space, consider cleanup"
        return self.send_warning(title, message, tags=['warning', 'disk-space'], alert_key=self.ALERT_DISK_WARNING)
    
    def send_stale_data_alert(self, age_hours: float) -> bool:
        """Send stale data alert."""
        title = "⚠️ Ride Optimizer: Data Becoming Stale"
        message = f"Last analysis: {age_hours:.0f} hours ago\nAction: Check cron job status"
        return self.send_warning(title, message, tags=['warning', 'stale-data'], alert_key=self.ALERT_STALE_DATA)
    
    def send_cache_corruption_alert(self, error: str) -> bool:
        """Send cache corruption alert."""
        title = "🚨 Ride Optimizer: Cache Corruption Detected"
        message = f"Error: {error}\nAction: Run cache cleanup or rebuild cache"
        return self.send_critical(title, message, tags=['critical', 'cache'], alert_key=self.ALERT_CACHE_CORRUPTION)
    
    def send_api_unresponsive_alert(self) -> bool:
        """Send API unresponsive alert."""
        title = "🚨 Ride Optimizer: API Unresponsive"
        message = "Application not serving requests\nAction: Check server status and logs"
        return self.send_critical(title, message, tags=['critical', 'api'], alert_key=self.ALERT_API_UNRESPONSIVE)
    
    def send_cron_failure_alert(self, job_name: str, error: str) -> bool:
        """Send cron job failure alert."""
        title = f"🚨 Ride Optimizer: Cron Job Failed"
        message = f"Job: {job_name}\nError: {error}\nAction: Check logs and cron configuration"
        return self.send_critical(title, message, tags=['critical', 'cron'], alert_key=f"{self.ALERT_CRON_FAILURE}_{job_name}")
    
    def send_maintenance_summary(self, summary: Dict[str, Any]) -> bool:
        """Send weekly maintenance summary."""
        title = "✅ Ride Optimizer: Weekly Maintenance Complete"
        
        # Format summary message
        lines = []
        if 'security_vulnerabilities' in summary:
            lines.append(f"- {summary['security_vulnerabilities']} security vulnerabilities")
        if 'issues_closed' in summary:
            lines.append(f"- {summary['issues_closed']} issues closed")
        if 'cache_size_mb' in summary:
            lines.append(f"- Cache: {summary['cache_size_mb']} MB")
        
        message = "\n".join(lines) if lines else "Maintenance completed successfully"
        
        return self.send_info(title, message, tags=['maintenance', 'summary'], alert_key=self.ALERT_MAINTENANCE_SUMMARY)


