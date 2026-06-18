"""
Unit tests for config_manager module.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from src.config_manager import ConfigManager, load_config


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset ConfigManager singleton between tests."""
    ConfigManager.reset_instance()
    yield
    ConfigManager.reset_instance()


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config YAML file."""
    config_data = {
        'strava': {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
        },
        'route_analysis': {
            'similarity_threshold': 0.85,
            'min_routes': 3,
        },
        'units': {
            'system': 'imperial',
        },
        'location': {
            'home': {
                'latitude': 40.7128,
                'longitude': -74.0060,
            }
        }
    }
    config_path = tmp_path / 'config.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)
    return str(config_path)


class TestConfigManagerSingleton:
    def test_get_instance_creates_singleton(self, config_file):
        instance1 = ConfigManager.get_instance(config_file)
        instance2 = ConfigManager.get_instance(config_file)
        assert instance1 is instance2

    def test_reset_instance_clears_singleton(self, config_file):
        instance1 = ConfigManager.get_instance(config_file)
        ConfigManager.reset_instance()
        instance2 = ConfigManager.get_instance(config_file)
        assert instance1 is not instance2


class TestConfigManagerGet:
    def test_get_top_level_key(self, config_file):
        cm = ConfigManager(config_file)
        assert isinstance(cm.get('strava'), dict)

    def test_get_nested_key(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get('strava.client_id') == 'test_id'

    def test_get_deeply_nested_key(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get('location.home.latitude') == 40.7128

    def test_get_missing_key_returns_default(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get('nonexistent.key', 'fallback') == 'fallback'

    def test_get_missing_key_returns_none_by_default(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get('nonexistent') is None

    def test_get_traversal_through_non_dict(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get('strava.client_id.deeper', 'default') == 'default'


class TestConfigManagerSet:
    def test_set_existing_key(self, config_file):
        cm = ConfigManager(config_file)
        cm.set('units.system', 'metric')
        assert cm.get('units.system') == 'metric'

    def test_set_creates_intermediate_dicts(self, config_file):
        cm = ConfigManager(config_file)
        cm.set('new.nested.key', 42)
        assert cm.get('new.nested.key') == 42

    def test_set_single_key(self, config_file):
        cm = ConfigManager(config_file)
        cm.set('debug', True)
        assert cm.get('debug') is True


class TestConfigManagerSections:
    def test_get_section(self, config_file):
        cm = ConfigManager(config_file)
        section = cm.get_section('strava')
        assert section['client_id'] == 'test_id'
        assert section['client_secret'] == 'test_secret'

    def test_get_missing_section_returns_empty_dict(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get_section('nonexistent') == {}

    def test_get_all_returns_copy(self, config_file):
        cm = ConfigManager(config_file)
        all_config = cm.get_all()
        all_config['strava'] = 'modified'
        assert cm.get('strava') != 'modified'


class TestConfigManagerReload:
    def test_reload_picks_up_file_changes(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.get('units.system') == 'imperial'

        new_data = {'units': {'system': 'metric'}}
        with open(config_file, 'w') as f:
            yaml.dump(new_data, f)

        cm.reload()
        assert cm.get('units.system') == 'metric'


class TestConfigManagerValidation:
    def test_validate_required_keys_success(self, config_file):
        cm = ConfigManager(config_file)
        assert cm.validate_required_keys(['strava.client_id', 'units.system']) is True

    def test_validate_required_keys_raises_on_missing(self, config_file):
        cm = ConfigManager(config_file)
        with pytest.raises(ValueError, match="Missing required"):
            cm.validate_required_keys(['strava.client_id', 'nonexistent.key'])


class TestConfigManagerLoadErrors:
    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            ConfigManager('/nonexistent/path/config.yaml')

    def test_invalid_yaml_raises(self, tmp_path):
        bad_yaml = tmp_path / 'bad.yaml'
        bad_yaml.write_text(': : :\n  - :\n    invalid: [')
        with pytest.raises(yaml.YAMLError):
            ConfigManager(str(bad_yaml))

    def test_empty_yaml_loads_as_empty_dict(self, tmp_path):
        empty = tmp_path / 'empty.yaml'
        empty.write_text('')
        cm = ConfigManager(str(empty))
        assert cm.get_all() == {}


class TestLoadConfigCompat:
    def test_load_config_returns_singleton(self, config_file):
        cm = load_config(config_file)
        assert isinstance(cm, ConfigManager)
        assert cm is ConfigManager.get_instance()
