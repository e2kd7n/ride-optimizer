"""
Centralized Configuration Manager

This module provides a singleton ConfigManager that handles all configuration
management for the ride-optimizer application. Instead of passing config objects
through function parameters, all code imports ConfigManager and accesses the
global singleton instance.

Benefits:
- Eliminates config parameter threading throughout the codebase
- Single source of truth for configuration
- Easier to test (can mock the singleton)
- Simpler function signatures
- Consistent access pattern across the entire app

Usage:
    from src.config_manager import ConfigManager
    
    config_mgr = ConfigManager.get_instance()
    threshold = config_mgr.get('route_analysis.similarity_threshold', 0.85)

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
import json
from pathlib import Path
from typing import Any, Optional, Dict
import yaml

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Singleton class for centralized configuration management.
    
    This class loads configuration from YAML files and provides a clean interface
    for accessing configuration values throughout the application.
    """
    
    _instance: Optional['ConfigManager'] = None
    _lock = None  # For thread-safe singleton pattern if needed
    
    def __init__(self, config_file: str = 'config/config.yaml'):
        """
        Initialize ConfigManager with a configuration file.
        
        Args:
            config_file: Path to the YAML configuration file
        """
        self.config_file = Path(config_file)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    @classmethod
    def get_instance(cls, config_file: str = 'config/config.yaml') -> 'ConfigManager':
        """
        Get the singleton instance of ConfigManager.
        
        Creates the instance on first call, returns existing instance on subsequent calls.
        The config_file parameter is only used on first initialization.
        
        Args:
            config_file: Path to the YAML configuration file (ignored after first call)
            
        Returns:
            ConfigManager singleton instance
        """
        if cls._instance is None:
            cls._instance = ConfigManager(config_file)
            logger.info(f"ConfigManager initialized with {config_file}")
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """
        Reset the singleton instance. Useful for testing.
        
        After calling this, the next call to get_instance() will create a new instance.
        """
        cls._instance = None
        logger.debug("ConfigManager instance reset")
    
    def _load_config(self) -> None:
        """
        Load configuration from YAML file.
        
        Raises:
            FileNotFoundError: If config file does not exist
            yaml.YAMLError: If config file has invalid YAML syntax
        """
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        try:
            with open(self.config_file, 'r') as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"Configuration loaded from {self.config_file}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in {self.config_file}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Supports nested access via dot notation. For example:
        - 'strava.client_id' accesses config['strava']['client_id']
        - 'route_analysis.similarity_threshold' accesses config['route_analysis']['similarity_threshold']
        
        Args:
            key: Configuration key using dot notation
            default: Default value if key is not found
            
        Returns:
            Configuration value or default if not found
            
        Example:
            >>> config_mgr = ConfigManager.get_instance()
            >>> threshold = config_mgr.get('route_analysis.similarity_threshold', 0.85)
            >>> client_id = config_mgr.get('strava.client_id')
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Creates intermediate dictionaries if needed. Useful for overriding config
        values at runtime (e.g., in tests or when reading from environment variables).
        
        Args:
            key: Configuration key using dot notation
            value: Value to set
            
        Example:
            >>> config_mgr = ConfigManager.get_instance()
            >>> config_mgr.set('route_analysis.similarity_threshold', 0.90)
        """
        keys = key.split('.')
        current = self._config
        
        # Navigate/create nested structure
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the final value
        current[keys[-1]] = value
        logger.debug(f"Configuration set: {key} = {value}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section as a dictionary.
        
        Args:
            section: Section name (e.g., 'strava', 'route_analysis')
            
        Returns:
            Dictionary of configuration values for the section, or empty dict if not found
            
        Example:
            >>> config_mgr = ConfigManager.get_instance()
            >>> strava_config = config_mgr.get_section('strava')
            >>> client_id = strava_config.get('client_id')
        """
        return self._config.get(section, {})
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration dictionary.
        
        Use with caution - prefer get() or get_section() for specific values.
        
        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()
    
    def reload(self) -> None:
        """
        Reload configuration from file.
        
        Useful if configuration file has changed at runtime.
        """
        self._load_config()
        logger.info(f"Configuration reloaded from {self.config_file}")
    
    def validate_required_keys(self, required_keys: list) -> bool:
        """
        Validate that required configuration keys exist.
        
        Args:
            required_keys: List of required keys using dot notation
            
        Returns:
            True if all keys exist, False otherwise
            
        Raises:
            ValueError: If any required keys are missing
            
        Example:
            >>> config_mgr = ConfigManager.get_instance()
            >>> config_mgr.validate_required_keys([
            ...     'strava.client_id',
            ...     'strava.client_secret',
            ...     'location.home.latitude'
            ... ])
        """
        missing_keys = []
        
        for key in required_keys:
            if self.get(key) is None:
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")
        
        return True


# Convenience function for backward compatibility with old code that used load_config()
def load_config(config_file: str = 'config/config.yaml') -> ConfigManager:
    """
    Load configuration and return the ConfigManager singleton.
    
    This function provides backward compatibility with code that previously
    used a load_config() function. New code should use ConfigManager.get_instance()
    directly.
    
    Args:
        config_file: Path to the YAML configuration file
        
    Returns:
        ConfigManager singleton instance
        
    Example:
        >>> config = load_config('config/config.yaml')
        >>> threshold = config.get('route_analysis.similarity_threshold')
    """
    return ConfigManager.get_instance(config_file)
