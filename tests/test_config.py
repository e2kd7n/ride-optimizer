"""
Unit tests for config module.
"""
import pytest
import tempfile
import os
from pathlib import Path
from src.config import Config, load_config


class TestConfig:
    """Test configuration loading and management."""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        config_content = """
strava:
  client_id: "test_client_id"
  client_secret: "test_secret"

locations:
  home:
    lat: 41.8781
    lon: -87.6298
  work:
    lat: 41.8819
    lon: -87.6278

analysis:
  similarity_threshold: 0.85
  min_commute_distance: 1.0
  max_commute_distance: 50.0
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        config = Config(str(config_file))
        
        assert config.get('strava.client_id') == "test_client_id"
        assert config.get('locations.home.lat') == 41.8781
        assert config.get('analysis.similarity_threshold') == 0.85
    
    def test_get_with_default(self, tmp_path):
        """Test getting config value with default."""
        config_content = """
strava:
  client_id: "test_id"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        config = Config(str(config_file))
        
        assert config.get('nonexistent.key', 'default_value') == 'default_value'
        assert config.get('strava.client_id', 'default') == 'test_id'
    
    def test_env_var_replacement(self, tmp_path, monkeypatch):
        """Test environment variable replacement in config."""
        monkeypatch.setenv('TEST_CLIENT_ID', 'env_client_id')
        monkeypatch.setenv('TEST_SECRET', 'env_secret')
        
        config_content = """
strava:
  client_id: "${TEST_CLIENT_ID}"
  client_secret: "${TEST_SECRET}"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        config = Config(str(config_file))
        
        assert config.get('strava.client_id') == 'env_client_id'
        assert config.get('strava.client_secret') == 'env_secret'
    
    def test_nested_key_access(self, tmp_path):
        """Test accessing nested configuration keys."""
        config_content = """
level1:
  level2:
    level3:
      value: "deep_value"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        config = Config(str(config_file))
        
        assert config.get('level1.level2.level3.value') == 'deep_value'
        assert config.get('level1.level2.level3.nonexistent', 'default') == 'default'
    
    def test_load_config_function(self, tmp_path):
        """Test the load_config convenience function."""
        config_content = """
test:
  value: 123
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        config = load_config(str(config_file))
        
        assert isinstance(config, Config)
        assert config.get('test.value') == 123
    
    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        with pytest.raises(FileNotFoundError):
            Config("/nonexistent/path/config.yaml")
    
    def test_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML syntax."""
        config_content = """
invalid: yaml: syntax:
  - broken
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        with pytest.raises(Exception):  # YAML parsing error
            Config(str(config_file))
    
    def test_empty_config(self, tmp_path):
        """Test handling of empty configuration file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        
        config = Config(str(config_file))
        assert config.get('any.key', 'default') == 'default'

# Made with Bob
