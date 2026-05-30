#!/usr/bin/env python3
"""
Unit tests for NtfyNotifier class.

Tests notification formatting, priority mapping, throttling logic,
and configuration validation.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.ntfy_notifier import NtfyNotifier


@pytest.fixture
def temp_throttle_file():
    """Create a temporary throttle file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = Path(f.name)
    yield temp_path
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def notifier_config():
    """Default notifier configuration for testing."""
    return {
        'enabled': 'true',
        'server': 'https://ntfy.sh',
        'topic': 'test-topic',
        'priorities': {
            'critical': 'urgent',
            'warning': 'high',
            'info': 'default'
        },
        'throttle_hours': 6,
        'alert_types': {
            'disk_space_critical': True,
            'disk_space_warning': True,
            'stale_data': True,
            'cache_corruption': True,
            'api_unresponsive': True,
            'cron_failure': True,
            'security_vulnerabilities': True,
            'maintenance_summary': False
        }
    }


@pytest.fixture
def notifier(notifier_config, temp_throttle_file, monkeypatch):
    """Create a NtfyNotifier instance for testing."""
    # Mock the throttle file path
    with patch.object(NtfyNotifier, '__init__', lambda self, config: None):
        notifier = NtfyNotifier(notifier_config)
        notifier.enabled = True
        notifier.server = 'https://ntfy.sh'
        notifier.topic = 'test-topic'
        notifier.priority_critical = 'urgent'
        notifier.priority_warning = 'high'
        notifier.priority_info = 'default'
        notifier.throttle_hours = 6
        notifier.alert_types = notifier_config['alert_types']
        notifier.throttle_file = temp_throttle_file
    return notifier


class TestNtfyNotifierInit:
    """Test NtfyNotifier initialization."""
    
    def test_init_with_config(self, notifier_config):
        """Test initialization with configuration dictionary."""
        notifier = NtfyNotifier(notifier_config)
        assert notifier.enabled is True
        assert notifier.server == 'https://ntfy.sh'
        assert notifier.topic == 'test-topic'
        assert notifier.throttle_hours == 6
    
    def test_init_disabled(self):
        """Test initialization with notifications disabled."""
        config = {'enabled': 'false'}
        notifier = NtfyNotifier(config)
        assert notifier.enabled is False
    
    def test_init_no_topic(self):
        """Test initialization without topic disables notifications."""
        config = {'enabled': 'true', 'topic': None}
        notifier = NtfyNotifier(config)
        assert notifier.enabled is False
    
    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv('NTFY_ENABLED', 'true')
        monkeypatch.setenv('NTFY_SERVER', 'https://custom.ntfy.sh')
        monkeypatch.setenv('NTFY_TOPIC', 'env-topic')
        
        notifier = NtfyNotifier(None)
        assert notifier.enabled is True
        assert notifier.server == 'https://custom.ntfy.sh'
        assert notifier.topic == 'env-topic'


class TestThrottling:
    """Test alert throttling logic."""
    
    def test_should_send_alert_first_time(self, notifier):
        """Test that alert is sent the first time."""
        assert notifier.should_send_alert('test_alert') is True
    
    def test_should_send_alert_throttled(self, notifier):
        """Test that alert is throttled within throttle period."""
        alert_key = 'test_alert'
        
        # First send should succeed
        assert notifier.should_send_alert(alert_key) is True
        notifier._record_alert_sent(alert_key)
        
        # Second send should be throttled
        assert notifier.should_send_alert(alert_key) is False
    
    def test_should_send_alert_after_throttle_period(self, notifier):
        """Test that alert is sent after throttle period expires."""
        alert_key = 'test_alert'
        
        # Record alert as sent 7 hours ago
        state = {alert_key: (datetime.now() - timedelta(hours=7)).isoformat()}
        notifier._save_throttle_state(state)
        
        # Should be allowed now
        assert notifier.should_send_alert(alert_key) is True
    
    def test_should_send_alert_disabled_type(self, notifier):
        """Test that disabled alert types are not sent."""
        notifier.alert_types['maintenance_summary'] = False
        assert notifier.should_send_alert('maintenance_summary') is False
    
    def test_throttle_state_persistence(self, notifier):
        """Test that throttle state persists across instances."""
        alert_key = 'test_alert'
        notifier._record_alert_sent(alert_key)
        
        # Load state in new instance
        state = notifier._load_throttle_state()
        assert alert_key in state
        assert datetime.fromisoformat(state[alert_key]) <= datetime.now()


class TestSendAlert:
    """Test sending alerts."""
    
    @patch('requests.post')
    def test_send_alert_success(self, mock_post, notifier):
        """Test successful alert sending."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_alert(
            title='Test Alert',
            message='Test message',
            priority='urgent',
            tags=['test'],
            alert_key='test_alert'
        )
        
        assert result is True
        mock_post.assert_called_once()
        
        # Verify request parameters
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://ntfy.sh/test-topic'
        assert call_args[1]['headers']['Title'] == 'Test Alert'
        assert call_args[1]['headers']['Priority'] == 'urgent'
        assert call_args[1]['headers']['Tags'] == 'test'
    
    @patch('requests.post')
    def test_send_alert_failure(self, mock_post, notifier):
        """Test alert sending failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        result = notifier.send_alert(
            title='Test Alert',
            message='Test message',
            priority='urgent',
            tags=['test']
        )
        
        assert result is False
    
    @patch('requests.post')
    def test_send_alert_exception(self, mock_post, notifier):
        """Test alert sending with network exception."""
        mock_post.side_effect = Exception('Network error')
        
        result = notifier.send_alert(
            title='Test Alert',
            message='Test message',
            priority='urgent',
            tags=['test']
        )
        
        assert result is False
    
    def test_send_alert_disabled(self, notifier):
        """Test that alerts are not sent when disabled."""
        notifier.enabled = False
        
        result = notifier.send_alert(
            title='Test Alert',
            message='Test message',
            priority='urgent',
            tags=['test']
        )
        
        assert result is False
    
    @patch('requests.post')
    def test_send_alert_throttled(self, mock_post, notifier):
        """Test that throttled alerts are not sent."""
        alert_key = 'test_alert'
        notifier._record_alert_sent(alert_key)
        
        result = notifier.send_alert(
            title='Test Alert',
            message='Test message',
            priority='urgent',
            tags=['test'],
            alert_key=alert_key
        )
        
        assert result is False
        mock_post.assert_not_called()


class TestConvenienceMethods:
    """Test convenience methods for different alert types."""
    
    @patch('requests.post')
    def test_send_critical(self, mock_post, notifier):
        """Test send_critical method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_critical('Critical Alert', 'Critical message')
        
        assert result is True
        call_args = mock_post.call_args
        assert call_args[1]['headers']['Priority'] == 'urgent'
        assert 'critical' in call_args[1]['headers']['Tags']
    
    @patch('requests.post')
    def test_send_warning(self, mock_post, notifier):
        """Test send_warning method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_warning('Warning Alert', 'Warning message')
        
        assert result is True
        call_args = mock_post.call_args
        assert call_args[1]['headers']['Priority'] == 'high'
        assert 'warning' in call_args[1]['headers']['Tags']
    
    @patch('requests.post')
    def test_send_info(self, mock_post, notifier):
        """Test send_info method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_info('Info Alert', 'Info message')
        
        assert result is True
        call_args = mock_post.call_args
        assert call_args[1]['headers']['Priority'] == 'default'
        assert 'info' in call_args[1]['headers']['Tags']


class TestSpecificAlerts:
    """Test specific alert methods."""
    
    @patch('requests.post')
    def test_send_disk_space_critical(self, mock_post, notifier):
        """Test disk space critical alert."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_disk_space_critical(92.5, 8.2)
        
        assert result is True
        call_args = mock_post.call_args
        # Check that the title contains disk space info
        assert 'Disk Space Critical' in call_args[1]['headers']['Title']
        # Check that the message contains the percentage and GB
        message = call_args[1]['data'].decode('utf-8')
        assert '92.5%' in message
        assert '8.2 GB' in message
    
    @patch('requests.post')
    def test_send_stale_data_alert(self, mock_post, notifier):
        """Test stale data alert."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_stale_data_alert(38.5)
        
        assert result is True
        call_args = mock_post.call_args
        message = call_args[1]['data'].decode('utf-8')
        assert '38 hours' in message
    
    @patch('requests.post')
    def test_send_cron_failure_alert(self, mock_post, notifier):
        """Test cron failure alert."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = notifier.send_cron_failure_alert('daily_analysis', 'Connection timeout')
        
        assert result is True
        call_args = mock_post.call_args
        message = call_args[1]['data'].decode('utf-8')
        assert 'daily_analysis' in message
        assert 'Connection timeout' in message
    
    @patch('requests.post')
    def test_send_maintenance_summary(self, mock_post, notifier):
        """Test maintenance summary alert."""
        # Enable maintenance summary alerts
        notifier.alert_types['maintenance_summary'] = True
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        summary = {
            'security_vulnerabilities': 0,
            'issues_closed': 3,
            'cache_size_mb': 245
        }
        
        result = notifier.send_maintenance_summary(summary)
        
        assert result is True
        call_args = mock_post.call_args
        message = call_args[1]['data'].decode('utf-8')
        assert '0 security vulnerabilities' in message
        assert '3 issues closed' in message
        assert '245 MB' in message


@pytest.mark.unit
class TestConfigurationParsing:
    """Test configuration value parsing."""
    
    def test_get_config_value_from_dict(self, notifier):
        """Test getting config value from dictionary."""
        config = {'server': 'https://test.ntfy.sh'}
        value = notifier._get_config_value(config, 'server', 'NTFY_SERVER', 'default')
        assert value == 'https://test.ntfy.sh'
    
    def test_get_config_value_nested(self, notifier):
        """Test getting nested config value."""
        config = {'priorities': {'critical': 'max'}}
        value = notifier._get_config_value(config, 'priorities.critical', 'NTFY_PRIORITY_CRITICAL', 'urgent')
        assert value == 'max'
    
    def test_get_config_value_from_env(self, notifier, monkeypatch):
        """Test getting config value from environment."""
        monkeypatch.setenv('NTFY_SERVER', 'https://env.ntfy.sh')
        value = notifier._get_config_value(None, 'server', 'NTFY_SERVER', 'default')
        assert value == 'https://env.ntfy.sh'
    
    def test_get_config_value_default(self, notifier):
        """Test getting default config value."""
        value = notifier._get_config_value(None, 'missing', 'MISSING_VAR', 'default_value')
        assert value == 'default_value'


