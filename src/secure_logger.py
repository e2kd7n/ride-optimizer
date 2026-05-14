"""
Secure Logger Module

Provides a logging wrapper that automatically sanitizes PII from all log messages
before writing them to log files or console output.

This ensures that sensitive information like GPS coordinates, addresses, user IDs,
and tokens are never logged in plain text, protecting user privacy while maintaining
debugging utility.

Usage:
    from src.secure_logger import SecureLogger
    
    logger = SecureLogger(__name__)
    logger.info("User at location: 41.8781136, -87.6297982")
    # Logs: "User at location: 41.87xx, -87.62xx"
"""

import logging
from typing import Any, Optional
from src.pii_sanitizer import sanitize_log_message


class SecureLogger:
    """
    Logging wrapper that automatically sanitizes PII from log messages.
    
    Provides the same interface as Python's standard logger but applies
    PII sanitization to all messages before logging.
    
    Attributes:
        logger: Underlying Python logger instance
        name: Logger name (typically __name__ of the module)
    """
    
    def __init__(self, name: str):
        """
        Initialize secure logger.
        
        Args:
            name: Logger name (typically __name__ of the calling module)
        """
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _sanitize_and_log(self, level: str, message: Any, *args, **kwargs):
        """
        Sanitize message and log at specified level.
        
        Args:
            level: Log level method name ('debug', 'info', 'warning', 'error', 'critical')
            message: Log message (will be sanitized)
            *args: Additional positional arguments for logger
            **kwargs: Additional keyword arguments for logger
        """
        # Sanitize the main message
        sanitized_message = sanitize_log_message(message)
        
        # Sanitize any additional arguments
        if args:
            sanitized_args = tuple(sanitize_log_message(arg) for arg in args)
        else:
            sanitized_args = args
        
        # Get the logging method and call it
        log_method = getattr(self.logger, level)
        log_method(sanitized_message, *sanitized_args, **kwargs)
    
    def debug(self, message: Any, *args, **kwargs):
        """
        Log a debug message with PII sanitization.
        
        Args:
            message: Debug message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self._sanitize_and_log('debug', message, *args, **kwargs)
    
    def info(self, message: Any, *args, **kwargs):
        """
        Log an info message with PII sanitization.
        
        Args:
            message: Info message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self._sanitize_and_log('info', message, *args, **kwargs)
    
    def warning(self, message: Any, *args, **kwargs):
        """
        Log a warning message with PII sanitization.
        
        Args:
            message: Warning message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self._sanitize_and_log('warning', message, *args, **kwargs)
    
    def error(self, message: Any, *args, **kwargs):
        """
        Log an error message with PII sanitization.
        
        Args:
            message: Error message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self._sanitize_and_log('error', message, *args, **kwargs)
    
    def critical(self, message: Any, *args, **kwargs):
        """
        Log a critical message with PII sanitization.
        
        Args:
            message: Critical message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self._sanitize_and_log('critical', message, *args, **kwargs)
    
    def exception(self, message: Any, *args, exc_info=True, **kwargs):
        """
        Log an exception with PII sanitization.
        
        Args:
            message: Exception message
            *args: Additional positional arguments
            exc_info: Include exception info (default: True)
            **kwargs: Additional keyword arguments
        """
        sanitized_message = sanitize_log_message(message)
        
        if args:
            sanitized_args = tuple(sanitize_log_message(arg) for arg in args)
        else:
            sanitized_args = args
        
        self.logger.exception(sanitized_message, *sanitized_args, exc_info=exc_info, **kwargs)
    
    def log(self, level: int, message: Any, *args, **kwargs):
        """
        Log a message at specified numeric level with PII sanitization.
        
        Args:
            level: Numeric log level (e.g., logging.INFO)
            message: Log message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        sanitized_message = sanitize_log_message(message)
        
        if args:
            sanitized_args = tuple(sanitize_log_message(arg) for arg in args)
        else:
            sanitized_args = args
        
        self.logger.log(level, sanitized_message, *sanitized_args, **kwargs)
    
    # Delegate property access to underlying logger
    def setLevel(self, level):
        """Set logging level."""
        self.logger.setLevel(level)
    
    def addHandler(self, handler):
        """Add a handler to the logger."""
        self.logger.addHandler(handler)
    
    def removeHandler(self, handler):
        """Remove a handler from the logger."""
        self.logger.removeHandler(handler)
    
    def addFilter(self, filter):
        """Add a filter to the logger."""
        self.logger.addFilter(filter)
    
    def removeFilter(self, filter):
        """Remove a filter from the logger."""
        self.logger.removeFilter(filter)
    
    @property
    def level(self):
        """Get current logging level."""
        return self.logger.level
    
    @property
    def handlers(self):
        """Get list of handlers."""
        return self.logger.handlers
    
    @property
    def filters(self):
        """Get list of filters."""
        return self.logger.filters
    
    def isEnabledFor(self, level: int) -> bool:
        """
        Check if logger is enabled for specified level.
        
        Args:
            level: Numeric log level
            
        Returns:
            True if enabled, False otherwise
        """
        return self.logger.isEnabledFor(level)
    
    def getEffectiveLevel(self) -> int:
        """
        Get effective logging level.
        
        Returns:
            Numeric log level
        """
        return self.logger.getEffectiveLevel()


def get_logger(name: str) -> SecureLogger:
    """
    Get a secure logger instance.
    
    Convenience function that mimics logging.getLogger() but returns
    a SecureLogger instead.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        
    Returns:
        SecureLogger instance
    """
    return SecureLogger(name)

# Made with Bob
