"""
Logging Configuration Module

Provides centralized logging setup with automatic log rotation to prevent
disk space exhaustion in production deployments (especially Raspberry Pi).

Features:
- Automatic log rotation at configurable size limits (default: 10MB)
- Configurable backup retention (default: 5 backups)
- Secure file permissions (0600) for all log files
- Separate security audit logging
- Support for both development (console) and production (file) modes
- Integration with SecureLogger for PII sanitization

Usage:
    from src.logging_config import setup_logging
    
    # Setup with defaults (10MB rotation, 5 backups)
    setup_logging()
    
    # Custom configuration
    setup_logging(
        log_dir='logs',
        log_level=logging.DEBUG,
        max_bytes=5*1024*1024,  # 5MB
        backup_count=3,
        console_output=False  # Production mode
    )
"""

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from typing import Optional

from src.pii_sanitizer import sanitize_log_message


class PIISanitizingFilter(logging.Filter):
    """
    Logging filter that sanitizes PII from every record before it's emitted,
    regardless of which logger produced it.

    ``SecureLogger`` only protects call sites that explicitly opt in to it;
    most of ``app/services/*.py`` and several ``src/*.py`` modules still use
    plain ``logging.getLogger(__name__)`` and can log raw GPS coordinates,
    addresses, or third-party exception strings verbatim. Attaching this
    filter to each handler (rather than to individual loggers) closes that
    gap for every current and future logger in the process, including
    third-party libraries, without requiring every module to be migrated.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize_log_message(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: sanitize_log_message(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
            else:
                # Only sanitize string args in-place; leave numeric/bool args
                # untouched so %d/%f-style third-party log calls don't break.
                record.args = tuple(
                    sanitize_log_message(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True


def setup_logging(
    log_dir: str = 'logs',
    log_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Configure application logging with automatic rotation.
    
    Creates rotating file handlers for main application logs and security audit logs.
    Logs rotate when they reach max_bytes size, keeping backup_count old versions.
    
    Args:
        log_dir: Directory for log files (created if doesn't exist)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of each log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        console_output: Whether to also log to console (default: True for development)
        
    Returns:
        Root logger instance
        
    Example:
        >>> setup_logging(max_bytes=5*1024*1024, backup_count=3)
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
    """
    # Create logs directory with secure permissions
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True, mode=0o700)  # Owner read/write/execute only
    
    # Clear any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Main application log with rotation (falls back to console if not writable)
    main_log_file = log_path / 'ride_optimizer.log'
    try:
        main_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        main_handler.setLevel(log_level)
        main_handler.setFormatter(formatter)
        main_handler.addFilter(PIISanitizingFilter())
        root_logger.addHandler(main_handler)
        _set_secure_permissions(main_log_file)
    except PermissionError:
        console_output = True  # force console so logs are not lost entirely
        logging.warning(f"Cannot write to {main_log_file} — falling back to console logging")

    # Console handler (optional, typically for development)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(PIISanitizingFilter())
        root_logger.addHandler(console_handler)

    # Security audit log (separate file with rotation)
    security_log_file = log_path / 'security_audit.log'
    security_logger = logging.getLogger('security_audit')
    security_logger.handlers.clear()
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False  # Don't send to root logger
    try:
        security_handler = RotatingFileHandler(
            security_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        security_handler.setLevel(logging.INFO)
        security_handler.setFormatter(formatter)
        security_handler.addFilter(PIISanitizingFilter())
        security_logger.addHandler(security_handler)
        _set_secure_permissions(security_log_file)
    except PermissionError:
        logging.warning(f"Cannot write to {security_log_file} — security audit logs will go to console")
    
    # Log startup message
    root_logger.info(
        f"Logging configured: level={logging.getLevelName(log_level)}, "
        f"rotation={max_bytes/1024/1024:.1f}MB, backups={backup_count}"
    )
    
    return root_logger


def _set_secure_permissions(log_file: Path) -> None:
    """
    Set secure file permissions (0600) on log file.
    
    Ensures only the owner can read/write the log file, protecting
    potentially sensitive information from other users on the system.
    
    Args:
        log_file: Path to log file
    """
    if log_file.exists():
        try:
            os.chmod(log_file, 0o600)
        except OSError as e:
            # Log warning but don't fail - permissions may not be changeable
            # on some filesystems (e.g., FAT32, network mounts)
            logging.warning(f"Could not set secure permissions on {log_file}: {e}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Convenience function compatible with SecureLogger usage pattern.
    Returns standard Python logger - wrap with SecureLogger for PII sanitization.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        
    Returns:
        Logger instance
        
    Example:
        >>> from src.logging_config import get_logger
        >>> from src.secure_logger import SecureLogger
        >>> logger = SecureLogger(get_logger(__name__).name)
    """
    return logging.getLogger(name)


def get_security_logger() -> logging.Logger:
    """
    Get the security audit logger.
    
    Returns the dedicated security audit logger for logging authentication,
    authorization, and other security-related events.
    
    Returns:
        Security audit logger instance
        
    Example:
        >>> security_logger = get_security_logger()
        >>> security_logger.info("User authentication successful")
    """
    return logging.getLogger('security_audit')


def reconfigure_logging(
    log_level: Optional[int] = None,
    console_output: Optional[bool] = None
) -> None:
    """
    Reconfigure logging settings without recreating handlers.
    
    Useful for changing log level or console output at runtime
    without disrupting log rotation.
    
    Args:
        log_level: New logging level (None to keep current)
        console_output: Enable/disable console output (None to keep current)
        
    Example:
        >>> reconfigure_logging(log_level=logging.DEBUG)
        >>> reconfigure_logging(console_output=False)  # Disable console in production
    """
    root_logger = logging.getLogger()
    
    if log_level is not None:
        root_logger.setLevel(log_level)
        for handler in root_logger.handlers:
            if not isinstance(handler, logging.StreamHandler) or isinstance(handler, RotatingFileHandler):
                handler.setLevel(log_level)
    
    if console_output is not None:
        # Find console handler
        console_handler = None
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                console_handler = handler
                break
        
        if console_output and not console_handler:
            # Add console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(root_logger.level)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            console_handler.addFilter(PIISanitizingFilter())
            root_logger.addHandler(console_handler)
        elif not console_output and console_handler:
            # Remove console handler
            root_logger.removeHandler(console_handler)


