"""
Tests for Logging Configuration Module

Verifies that log rotation, file permissions, and logging setup work correctly.
"""

import pytest
import logging
import tempfile
import shutil
from pathlib import Path
import os
import stat

from src.logging_config import (
    setup_logging,
    get_logger,
    get_security_logger,
    reconfigure_logging
)


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for test logs."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    # Clear all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)
    
    # Clear security logger handlers
    security_logger = logging.getLogger('security_audit')
    for handler in security_logger.handlers[:]:
        handler.close()
        security_logger.removeHandler(handler)
    
    yield
    
    # Cleanup after test
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)
    for handler in security_logger.handlers[:]:
        handler.close()
        security_logger.removeHandler(handler)


class TestLoggingSetup:
    """Test basic logging setup functionality."""
    
    def test_setup_creates_log_directory(self, temp_log_dir):
        """Test that setup_logging creates the log directory."""
        log_dir = Path(temp_log_dir) / 'new_logs'
        assert not log_dir.exists()
        
        setup_logging(log_dir=str(log_dir))
        
        assert log_dir.exists()
        assert log_dir.is_dir()
    
    def test_setup_creates_main_log_file(self, temp_log_dir):
        """Test that setup_logging creates the main log file."""
        setup_logging(log_dir=temp_log_dir)
        
        log_file = Path(temp_log_dir) / 'ride_optimizer.log'
        logger = logging.getLogger('test')
        logger.info("Test message")
        
        assert log_file.exists()
        assert log_file.is_file()
    
    def test_setup_creates_security_log_file(self, temp_log_dir):
        """Test that setup_logging creates the security audit log file."""
        setup_logging(log_dir=temp_log_dir)
        
        security_log = Path(temp_log_dir) / 'security_audit.log'
        security_logger = get_security_logger()
        security_logger.info("Security event")
        
        assert security_log.exists()
        assert security_log.is_file()
    
    def test_setup_with_custom_log_level(self, temp_log_dir):
        """Test that custom log level is applied."""
        setup_logging(log_dir=temp_log_dir, log_level=logging.DEBUG)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_setup_with_console_output(self, temp_log_dir):
        """Test that console handler is added when requested."""
        setup_logging(log_dir=temp_log_dir, console_output=True)
        
        root_logger = logging.getLogger()
        console_handlers = [
            h for h in root_logger.handlers 
            if isinstance(h, logging.StreamHandler) and not hasattr(h, 'baseFilename')
        ]
        
        assert len(console_handlers) > 0
    
    def test_setup_without_console_output(self, temp_log_dir):
        """Test that console handler is not added when disabled."""
        setup_logging(log_dir=temp_log_dir, console_output=False)
        
        root_logger = logging.getLogger()
        console_handlers = [
            h for h in root_logger.handlers 
            if isinstance(h, logging.StreamHandler) and not hasattr(h, 'baseFilename')
        ]
        
        assert len(console_handlers) == 0


class TestLogRotation:
    """Test log rotation functionality."""
    
    def test_rotation_at_size_limit(self, temp_log_dir):
        """Test that logs rotate when they reach the size limit."""
        # Setup with very small max_bytes for testing
        max_bytes = 1024  # 1KB
        setup_logging(
            log_dir=temp_log_dir,
            max_bytes=max_bytes,
            backup_count=3
        )
        
        logger = logging.getLogger('test')
        log_file = Path(temp_log_dir) / 'ride_optimizer.log'
        
        # Write enough data to trigger rotation
        for i in range(100):
            logger.info(f"Test message {i} with some padding to increase size" * 5)
        
        # Check that rotation occurred
        backup_file = Path(temp_log_dir) / 'ride_optimizer.log.1'
        assert backup_file.exists(), "Backup file should be created after rotation"
    
    def test_backup_count_limit(self, temp_log_dir):
        """Test that old backups are deleted when backup_count is exceeded."""
        max_bytes = 500  # Very small for quick rotation
        backup_count = 2
        
        setup_logging(
            log_dir=temp_log_dir,
            max_bytes=max_bytes,
            backup_count=backup_count
        )
        
        logger = logging.getLogger('test')
        
        # Write enough to create multiple rotations
        for i in range(300):
            logger.info(f"Test message {i} with padding" * 10)
        
        # Check that we don't exceed backup_count
        log_files = list(Path(temp_log_dir).glob('ride_optimizer.log*'))
        # Should have: ride_optimizer.log + backup_count backups
        assert len(log_files) <= backup_count + 1
    
    def test_security_log_rotation(self, temp_log_dir):
        """Test that security audit logs also rotate."""
        max_bytes = 1024
        setup_logging(
            log_dir=temp_log_dir,
            max_bytes=max_bytes,
            backup_count=3
        )
        
        security_logger = get_security_logger()
        
        # Write enough to trigger rotation
        for i in range(100):
            security_logger.info(f"Security event {i} with padding" * 5)
        
        backup_file = Path(temp_log_dir) / 'security_audit.log.1'
        assert backup_file.exists(), "Security log should rotate"


class TestFilePermissions:
    """Test that log files have secure permissions."""
    
    def test_main_log_permissions(self, temp_log_dir):
        """Test that main log file has 0600 permissions."""
        setup_logging(log_dir=temp_log_dir)
        
        log_file = Path(temp_log_dir) / 'ride_optimizer.log'
        logger = logging.getLogger('test')
        logger.info("Test message")
        
        # Check permissions (owner read/write only)
        file_stat = os.stat(log_file)
        permissions = stat.S_IMODE(file_stat.st_mode)
        
        # 0600 = owner read/write only
        assert permissions == 0o600, f"Expected 0600, got {oct(permissions)}"
    
    def test_security_log_permissions(self, temp_log_dir):
        """Test that security log file has 0600 permissions."""
        setup_logging(log_dir=temp_log_dir)
        
        security_log = Path(temp_log_dir) / 'security_audit.log'
        security_logger = get_security_logger()
        security_logger.info("Security event")
        
        file_stat = os.stat(security_log)
        permissions = stat.S_IMODE(file_stat.st_mode)
        
        assert permissions == 0o600, f"Expected 0600, got {oct(permissions)}"
    
    def test_log_directory_permissions(self, temp_log_dir):
        """Test that log directory has secure permissions."""
        log_dir = Path(temp_log_dir) / 'secure_logs'
        setup_logging(log_dir=str(log_dir))
        
        dir_stat = os.stat(log_dir)
        permissions = stat.S_IMODE(dir_stat.st_mode)
        
        # 0700 = owner read/write/execute only
        assert permissions == 0o700, f"Expected 0700, got {oct(permissions)}"


class TestLoggerRetrieval:
    """Test logger retrieval functions."""
    
    def test_get_logger(self, temp_log_dir):
        """Test that get_logger returns a logger instance."""
        setup_logging(log_dir=temp_log_dir)
        
        logger = get_logger('test_module')
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test_module'
    
    def test_get_security_logger(self, temp_log_dir):
        """Test that get_security_logger returns the security logger."""
        setup_logging(log_dir=temp_log_dir)
        
        security_logger = get_security_logger()
        assert isinstance(security_logger, logging.Logger)
        assert security_logger.name == 'security_audit'
    
    def test_security_logger_does_not_propagate(self, temp_log_dir):
        """Test that security logger doesn't propagate to root logger."""
        setup_logging(log_dir=temp_log_dir)
        
        security_logger = get_security_logger()
        assert security_logger.propagate is False


class TestReconfiguration:
    """Test runtime reconfiguration of logging."""
    
    def test_reconfigure_log_level(self, temp_log_dir):
        """Test changing log level at runtime."""
        setup_logging(log_dir=temp_log_dir, log_level=logging.INFO)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        
        reconfigure_logging(log_level=logging.DEBUG)
        assert root_logger.level == logging.DEBUG
    
    def test_reconfigure_console_output_enable(self, temp_log_dir):
        """Test enabling console output at runtime."""
        setup_logging(log_dir=temp_log_dir, console_output=False)
        
        root_logger = logging.getLogger()
        initial_handler_count = len(root_logger.handlers)
        
        reconfigure_logging(console_output=True)
        
        # Should have one more handler (console)
        assert len(root_logger.handlers) == initial_handler_count + 1
    
    def test_reconfigure_console_output_disable(self, temp_log_dir):
        """Test disabling console output at runtime."""
        setup_logging(log_dir=temp_log_dir, console_output=True)
        
        root_logger = logging.getLogger()
        initial_handler_count = len(root_logger.handlers)
        
        reconfigure_logging(console_output=False)
        
        # Should have one fewer handler
        assert len(root_logger.handlers) == initial_handler_count - 1


class TestLoggingIntegration:
    """Test integration with actual logging."""
    
    def test_log_messages_written_to_file(self, temp_log_dir):
        """Test that log messages are actually written to file."""
        setup_logging(log_dir=temp_log_dir)
        
        logger = logging.getLogger('test')
        test_message = "Integration test message"
        logger.info(test_message)
        
        log_file = Path(temp_log_dir) / 'ride_optimizer.log'
        content = log_file.read_text()
        
        assert test_message in content
    
    def test_security_messages_written_to_separate_file(self, temp_log_dir):
        """Test that security messages go to separate file."""
        setup_logging(log_dir=temp_log_dir)
        
        security_logger = get_security_logger()
        security_message = "Security audit event"
        security_logger.info(security_message)
        
        security_log = Path(temp_log_dir) / 'security_audit.log'
        main_log = Path(temp_log_dir) / 'ride_optimizer.log'
        
        security_content = security_log.read_text()
        main_content = main_log.read_text()
        
        assert security_message in security_content
        assert security_message not in main_content  # Should not propagate
    
    def test_multiple_loggers_write_to_same_file(self, temp_log_dir):
        """Test that multiple loggers write to the same main log file."""
        setup_logging(log_dir=temp_log_dir)
        
        logger1 = logging.getLogger('module1')
        logger2 = logging.getLogger('module2')
        
        message1 = "Message from module1"
        message2 = "Message from module2"
        
        logger1.info(message1)
        logger2.info(message2)
        
        log_file = Path(temp_log_dir) / 'ride_optimizer.log'
        content = log_file.read_text()
        
        assert message1 in content
        assert message2 in content


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_setup_with_existing_directory(self, temp_log_dir):
        """Test that setup works with existing directory."""
        # Create directory first
        log_dir = Path(temp_log_dir) / 'existing'
        log_dir.mkdir()
        
        # Should not raise error
        setup_logging(log_dir=str(log_dir))
        
        log_file = log_dir / 'ride_optimizer.log'
        assert log_file.exists()
    
    def test_setup_called_multiple_times(self, temp_log_dir):
        """Test that calling setup multiple times doesn't create duplicate handlers."""
        setup_logging(log_dir=temp_log_dir)
        initial_handler_count = len(logging.getLogger().handlers)
        
        setup_logging(log_dir=temp_log_dir)
        final_handler_count = len(logging.getLogger().handlers)
        
        # Should clear old handlers, so count should be the same
        assert final_handler_count == initial_handler_count
    
    def test_zero_backup_count(self, temp_log_dir):
        """Test that backup_count=0 means no backups kept."""
        setup_logging(
            log_dir=temp_log_dir,
            max_bytes=500,
            backup_count=0
        )
        
        logger = logging.getLogger('test')
        
        # Write enough to trigger rotation
        for i in range(100):
            logger.info(f"Test message {i}" * 10)
        
        # Should only have main log file, no backups
        log_files = list(Path(temp_log_dir).glob('ride_optimizer.log*'))
        assert len(log_files) == 1


# Made with Bob