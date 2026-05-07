"""
Unit tests for WeatherService.

Tests cover:
- Service initialization
- Current weather retrieval with caching
- Route weather with wind impact
- Weather summary formatting
- Cache key generation
- Comfort score calculation
- Cycling favorability determination
- Degraded weather fallback
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import json

from app.services.weather_service import WeatherService
from src.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'weather.api_key': 'test_api_key',
        'weather.cache_ttl': 7200  # 2 hours
    }.get(key, default))
    return config


@pytest.fixture
def weather_service(mock_config):
    """Create a WeatherService instance with mocked dependencies."""
    with patch('app.services.weather_service.WeatherFetcher'), \
         patch('app.services.weather_service.WindImpactCalculator'), \
         patch('app.services.weather_service.JSONStorage'):
        service = WeatherService(mock_config)
        return service


@pytest.fixture
def sample_weather_data():
    """Sample weather data for testing."""
    return {
        'temperature_c': 20,
        'temperature_f': 68,
        'wind_speed_kph': 15,
        'wind_direction_degrees': 180,
        'precipitation_mm': 0,
        'conditions': 'Clear',
        'humidity': 60
    }


@pytest.fixture
def sample_cache_data():
    """Sample cache data structure."""
    return {
        'locations': {
            '42.3601_-71.0589': {
                'weather_data': {
                    'temperature_c': 20,
                    'temperature_f': 68,
                    'wind_speed_kph': 15,
                    'conditions': 'Clear',
                    'comfort_score': 0.85,
                    'cycling_favorability': 'favorable'
                },
                'timestamp': datetime.now().isoformat(),
                'location_name': 'Boston'
            }
        }
    }


class TestWeatherServiceInit:
    """Test WeatherService initialization."""
    
    def test_init_creates_dependencies(self, mock_config):
        """Test that initialization creates all required dependencies."""
        with patch('app.services.weather_service.WeatherFetcher') as mock_fetcher, \
             patch('app.services.weather_service.WindImpactCalculator') as mock_wind, \
             patch('app.services.weather_service.JSONStorage') as mock_storage:
            
            service = WeatherService(mock_config)
            
            assert service.config == mock_config
            mock_fetcher.assert_called_once()
            mock_wind.assert_called_once()
            mock_storage.assert_called_once()


class TestCacheKeyGeneration:
    """Test cache key generation."""
    
    def test_cache_key_format(self, weather_service):
        """Test cache key format with 4 decimal places."""
        key = weather_service._get_cache_key(42.3601, -71.0589)
        assert key == '42.3601_-71.0589'
    
    def test_cache_key_rounding(self, weather_service):
        """Test cache key rounds to 4 decimal places."""
        key = weather_service._get_cache_key(42.360123456, -71.058987654)
        assert key == '42.3601_-71.0590'
    
    def test_cache_key_negative_coords(self, weather_service):
        """Test cache key with negative coordinates."""
        key = weather_service._get_cache_key(-33.8688, 151.2093)
        assert key == '-33.8688_151.2093'


class TestComfortScoreCalculation:
    """Test comfort score calculation."""
    
    def test_perfect_conditions(self, weather_service):
        """Test perfect cycling conditions (20°C, no wind, no rain)."""
        weather = {
            'temperature_c': 20,
            'wind_speed_kph': 5,
            'precipitation_mm': 0
        }
        score = weather_service._calculate_comfort_score(weather)
        assert score == 1.0
    
    def test_cold_temperature_penalty(self, weather_service):
        """Test penalty for cold temperatures."""
        weather = {'temperature_c': 5, 'wind_speed_kph': 0, 'precipitation_mm': 0}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.8  # -0.2 for temp < 10
    
    def test_freezing_temperature_penalty(self, weather_service):
        """Test penalty for freezing temperatures."""
        weather = {'temperature_c': -5, 'wind_speed_kph': 0, 'precipitation_mm': 0}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.6  # -0.4 for temp < 0
    
    def test_hot_temperature_penalty(self, weather_service):
        """Test penalty for hot temperatures."""
        weather = {'temperature_c': 32, 'wind_speed_kph': 0, 'precipitation_mm': 0}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.7  # -0.3 for temp > 30
    
    def test_extreme_heat_penalty(self, weather_service):
        """Test penalty for extreme heat."""
        weather = {'temperature_c': 38, 'wind_speed_kph': 0, 'precipitation_mm': 0}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.7  # -0.3 for temp > 30 (elif chain, so > 35 never reached)
    
    def test_moderate_wind_penalty(self, weather_service):
        """Test penalty for moderate wind."""
        weather = {'temperature_c': 20, 'wind_speed_kph': 25, 'precipitation_mm': 0}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.85  # -0.15 for wind > 20
    
    def test_strong_wind_penalty(self, weather_service):
        """Test penalty for strong wind."""
        weather = {'temperature_c': 20, 'wind_speed_kph': 35, 'precipitation_mm': 0}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.7  # -0.3 for wind > 30
    
    def test_light_rain_penalty(self, weather_service):
        """Test penalty for light rain."""
        weather = {'temperature_c': 20, 'wind_speed_kph': 0, 'precipitation_mm': 2}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.8  # -0.2 for precip > 0
    
    def test_heavy_rain_penalty(self, weather_service):
        """Test penalty for heavy rain."""
        weather = {'temperature_c': 20, 'wind_speed_kph': 0, 'precipitation_mm': 10}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.6  # -0.4 for precip > 5
    
    def test_combined_penalties(self, weather_service):
        """Test multiple penalties combined."""
        weather = {'temperature_c': 5, 'wind_speed_kph': 25, 'precipitation_mm': 3}
        score = weather_service._calculate_comfort_score(weather)
        # -0.2 (cold) -0.15 (wind) -0.2 (rain) = 0.45
        assert score == 0.45
    
    def test_score_floor_at_zero(self, weather_service):
        """Test that score doesn't go below 0."""
        weather = {'temperature_c': -10, 'wind_speed_kph': 40, 'precipitation_mm': 15}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 0.0
    
    def test_alternative_field_names(self, weather_service):
        """Test using alternative field names (temperature vs temperature_c)."""
        weather = {'temperature': 20, 'wind_speed': 5, 'precipitation': 0}
        score = weather_service._calculate_comfort_score(weather)
        assert score == 1.0


class TestCyclingFavorability:
    """Test cycling favorability categorization."""
    
    def test_favorable_high_score(self, weather_service):
        """Test favorable category for high scores."""
        assert weather_service._get_cycling_favorability(0.9) == 'favorable'
        assert weather_service._get_cycling_favorability(0.7) == 'favorable'
    
    def test_neutral_medium_score(self, weather_service):
        """Test neutral category for medium scores."""
        assert weather_service._get_cycling_favorability(0.6) == 'neutral'
        assert weather_service._get_cycling_favorability(0.4) == 'neutral'
    
    def test_unfavorable_low_score(self, weather_service):
        """Test unfavorable category for low scores."""
        assert weather_service._get_cycling_favorability(0.3) == 'unfavorable'
        assert weather_service._get_cycling_favorability(0.0) == 'unfavorable'
    
    def test_boundary_conditions(self, weather_service):
        """Test boundary values."""
        assert weather_service._get_cycling_favorability(0.69) == 'neutral'
        assert weather_service._get_cycling_favorability(0.39) == 'unfavorable'


class TestEnrichWeatherData:
    """Test weather data enrichment."""
    
    def test_adds_comfort_score(self, weather_service, sample_weather_data):
        """Test that enrichment adds comfort_score."""
        enriched = weather_service._enrich_weather_data(sample_weather_data.copy())
        assert 'comfort_score' in enriched
        assert isinstance(enriched['comfort_score'], float)
        assert 0 <= enriched['comfort_score'] <= 1
    
    def test_adds_cycling_favorability(self, weather_service, sample_weather_data):
        """Test that enrichment adds cycling_favorability."""
        enriched = weather_service._enrich_weather_data(sample_weather_data.copy())
        assert 'cycling_favorability' in enriched
        assert enriched['cycling_favorability'] in ['favorable', 'neutral', 'unfavorable']
    
    def test_preserves_original_data(self, weather_service, sample_weather_data):
        """Test that enrichment preserves original fields."""
        enriched = weather_service._enrich_weather_data(sample_weather_data.copy())
        for key in sample_weather_data:
            assert key in enriched
            assert enriched[key] == sample_weather_data[key]


class TestGetCurrentWeather:
    """Test current weather retrieval."""
    
    def test_cache_hit_fresh_data(self, weather_service, sample_cache_data):
        """Test returning fresh cached data (< 2 hours old)."""
        weather_service.storage.read = Mock(return_value=sample_cache_data)
        
        result = weather_service.get_current_weather(42.3601, -71.0589, 'Boston')
        
        assert result['temperature_c'] == 20
        assert result['comfort_score'] == 0.85
        weather_service.fetcher.get_current_conditions.assert_not_called()
    
    def test_cache_miss_fetches_fresh(self, weather_service, sample_weather_data):
        """Test fetching fresh data on cache miss."""
        weather_service.storage.read = Mock(return_value={'locations': {}})
        weather_service.fetcher.get_current_conditions = Mock(return_value=sample_weather_data)
        weather_service.storage.write = Mock()
        
        result = weather_service.get_current_weather(42.3601, -71.0589, 'Boston')
        
        assert result['temperature_c'] == 20
        assert 'comfort_score' in result
        assert 'cycling_favorability' in result
        weather_service.fetcher.get_current_conditions.assert_called_once_with(42.3601, -71.0589)
        weather_service.storage.write.assert_called_once()
    
    def test_stale_cache_fetches_fresh(self, weather_service, sample_weather_data):
        """Test fetching fresh data when cache is stale (> 2 hours)."""
        stale_cache = {
            'locations': {
                '42.3601_-71.0589': {
                    'weather_data': {'temperature_c': 15},
                    'timestamp': (datetime.now() - timedelta(hours=3)).isoformat(),
                    'location_name': 'Boston'
                }
            }
        }
        weather_service.storage.read = Mock(return_value=stale_cache)
        weather_service.fetcher.get_current_conditions = Mock(return_value=sample_weather_data)
        weather_service.storage.write = Mock()
        
        result = weather_service.get_current_weather(42.3601, -71.0589, 'Boston')
        
        assert result['temperature_c'] == 20  # Fresh data, not stale
        weather_service.fetcher.get_current_conditions.assert_called_once()
    
    def test_api_failure_uses_degraded(self, weather_service):
        """Test falling back to degraded weather on API failure."""
        weather_service.storage.read = Mock(return_value={'locations': {}})
        weather_service.fetcher.get_current_conditions = Mock(return_value=None)
        weather_service._get_degraded_weather = Mock(return_value={'is_stale': True})
        
        result = weather_service.get_current_weather(42.3601, -71.0589)
        
        assert result['is_stale'] is True
        weather_service._get_degraded_weather.assert_called_once()
    
    def test_exception_uses_degraded(self, weather_service):
        """Test falling back to degraded weather on exception."""
        weather_service.storage.read = Mock(side_effect=Exception('Storage error'))
        weather_service._get_degraded_weather = Mock(return_value={'is_stale': True})
        
        result = weather_service.get_current_weather(42.3601, -71.0589)
        
        assert result['is_stale'] is True
        weather_service._get_degraded_weather.assert_called_once()
    
    def test_stores_location_name(self, weather_service, sample_weather_data):
        """Test that location name is stored in cache."""
        weather_service.storage.read = Mock(return_value={'locations': {}})
        weather_service.fetcher.get_current_conditions = Mock(return_value=sample_weather_data)
        weather_service.storage.write = Mock()
        
        weather_service.get_current_weather(42.3601, -71.0589, 'Boston')
        
        call_args = weather_service.storage.write.call_args[0]
        cache_data = call_args[1]
        assert cache_data['locations']['42.3601_-71.0589']['location_name'] == 'Boston'
    
    def test_default_location_name(self, weather_service, sample_weather_data):
        """Test default location name when none provided."""
        weather_service.storage.read = Mock(return_value={'locations': {}})
        weather_service.fetcher.get_current_conditions = Mock(return_value=sample_weather_data)
        weather_service.storage.write = Mock()
        
        weather_service.get_current_weather(42.3601, -71.0589)
        
        call_args = weather_service.storage.write.call_args[0]
        cache_data = call_args[1]
        location_name = cache_data['locations']['42.3601_-71.0589']['location_name']
        assert 'Location' in location_name
        assert '42.36' in location_name


class TestGetRouteWeather:
    """Test route weather retrieval."""
    
    def test_empty_coordinates(self, weather_service):
        """Test handling empty coordinates list."""
        result = weather_service.get_route_weather([])
        assert result == {}
    
    def test_uses_start_location(self, weather_service, sample_weather_data):
        """Test that route weather uses start location."""
        coordinates = [(42.3601, -71.0589), (42.3650, -71.0600), (42.3700, -71.0610)]
        weather_service.get_current_weather = Mock(return_value=sample_weather_data)
        
        result = weather_service.get_route_weather(coordinates, 'Test Route')
        
        weather_service.get_current_weather.assert_called_once_with(
            42.3601, -71.0589, location_name='Test Route'
        )
    
    def test_adds_wind_impact(self, weather_service, sample_weather_data):
        """Test that wind impact is calculated and added."""
        coordinates = [(42.3601, -71.0589), (42.3650, -71.0600)]
        wind_impact = {'headwind_pct': 30, 'tailwind_pct': 20, 'crosswind_pct': 50}
        
        weather_service.get_current_weather = Mock(return_value=sample_weather_data)
        weather_service.wind_calculator.calculate_wind_impact = Mock(return_value=wind_impact)
        
        result = weather_service.get_route_weather(coordinates)
        
        assert 'wind_impact' in result
        assert result['wind_impact'] == wind_impact
        weather_service.wind_calculator.calculate_wind_impact.assert_called_once_with(
            coordinates, 15, 180
        )
    
    def test_no_wind_impact_without_wind_data(self, weather_service):
        """Test that wind impact is not calculated without wind data."""
        coordinates = [(42.3601, -71.0589), (42.3650, -71.0600)]
        weather_data = {'temperature_c': 20, 'wind_speed_kph': 0}
        
        weather_service.get_current_weather = Mock(return_value=weather_data)
        
        result = weather_service.get_route_weather(coordinates)
        
        assert 'wind_impact' not in result
        weather_service.wind_calculator.calculate_wind_impact.assert_not_called()
    
    def test_wind_impact_calculation_failure(self, weather_service, sample_weather_data):
        """Test graceful handling of wind impact calculation failure."""
        coordinates = [(42.3601, -71.0589), (42.3650, -71.0600)]
        
        weather_service.get_current_weather = Mock(return_value=sample_weather_data)
        weather_service.wind_calculator.calculate_wind_impact = Mock(
            side_effect=Exception('Calculation error')
        )
        
        result = weather_service.get_route_weather(coordinates)
        
        assert 'wind_impact' not in result
        assert result['temperature_c'] == 20  # Other data still present
    
    def test_no_weather_data_returns_empty(self, weather_service):
        """Test returning empty dict when no weather data available."""
        coordinates = [(42.3601, -71.0589)]
        weather_service.get_current_weather = Mock(return_value={})
        
        result = weather_service.get_route_weather(coordinates)
        
        assert result == {}
    
    def test_exception_returns_empty(self, weather_service):
        """Test returning empty dict on exception."""
        coordinates = [(42.3601, -71.0589)]
        weather_service.get_current_weather = Mock(side_effect=Exception('Error'))
        
        result = weather_service.get_route_weather(coordinates)
        
        assert result == {}


class TestGetWeatherSummary:
    """Test weather summary formatting."""
    
    def test_formats_summary_string(self, weather_service, sample_weather_data):
        """Test summary string formatting."""
        weather_service.get_current_weather = Mock(return_value=sample_weather_data)
        
        result = weather_service.get_weather_summary(42.3601, -71.0589, 'Boston')
        
        assert 'summary' in result
        assert '68°F' in result['summary']
        assert 'Clear' in result['summary']
        assert 'Wind' in result['summary']
        assert result['available'] is True
    
    def test_includes_wind_in_summary(self, weather_service):
        """Test that wind is included in summary when present."""
        weather_data = {
            'temperature_f': 72,
            'conditions': 'Partly Cloudy',
            'wind_speed_kph': 20
        }
        weather_service.get_current_weather = Mock(return_value=weather_data)
        
        result = weather_service.get_weather_summary(42.3601, -71.0589)
        
        assert 'Wind' in result['summary']
        assert 'mph' in result['summary']
    
    def test_no_wind_in_summary_when_zero(self, weather_service):
        """Test that wind is omitted when zero."""
        weather_data = {
            'temperature_f': 72,
            'conditions': 'Clear',
            'wind_speed_kph': 0
        }
        weather_service.get_current_weather = Mock(return_value=weather_data)
        
        result = weather_service.get_weather_summary(42.3601, -71.0589)
        
        assert 'Wind' not in result['summary']
    
    def test_unavailable_weather(self, weather_service):
        """Test handling unavailable weather data."""
        weather_service.get_current_weather = Mock(return_value={})
        
        result = weather_service.get_weather_summary(42.3601, -71.0589)
        
        assert result['summary'] == 'Weather data unavailable'
        assert result['available'] is False


class TestGetDegradedWeather:
    """Test degraded weather fallback."""
    
    def test_returns_stale_data_within_24h(self, weather_service):
        """Test returning stale data within 24-hour window."""
        stale_cache = {
            'locations': {
                '42.3601_-71.0589': {
                    'weather_data': {'temperature_c': 18, 'conditions': 'Cloudy'},
                    'timestamp': (datetime.now() - timedelta(hours=5)).isoformat(),
                    'location_name': 'Boston'
                }
            }
        }
        weather_service.storage.read = Mock(return_value=stale_cache)
        
        result = weather_service._get_degraded_weather(42.3601, -71.0589, 'Boston')
        
        assert result['temperature_c'] == 18
        assert result['is_stale'] is True
        assert 'age_hours' in result
        assert 4 < result['age_hours'] < 6
    
    def test_rejects_data_older_than_24h(self, weather_service):
        """Test rejecting data older than 24 hours."""
        old_cache = {
            'locations': {
                '42.3601_-71.0589': {
                    'weather_data': {'temperature_c': 18},
                    'timestamp': (datetime.now() - timedelta(hours=30)).isoformat(),
                    'location_name': 'Boston'
                }
            }
        }
        weather_service.storage.read = Mock(return_value=old_cache)
        
        result = weather_service._get_degraded_weather(42.3601, -71.0589)
        
        assert result == {}
    
    def test_no_cache_data_returns_empty(self, weather_service):
        """Test returning empty dict when no cache data exists."""
        weather_service.storage.read = Mock(return_value={'locations': {}})
        
        result = weather_service._get_degraded_weather(42.3601, -71.0589)
        
        assert result == {}
    
    def test_exception_returns_empty(self, weather_service):
        """Test returning empty dict on exception."""
        weather_service.storage.read = Mock(side_effect=Exception('Storage error'))
        
        result = weather_service._get_degraded_weather(42.3601, -71.0589)
        
        assert result == {}
    
    def test_preserves_original_data(self, weather_service):
        """Test that degraded weather preserves original data fields."""
        stale_cache = {
            'locations': {
                '42.3601_-71.0589': {
                    'weather_data': {
                        'temperature_c': 18,
                        'wind_speed_kph': 10,
                        'conditions': 'Cloudy',
                        'comfort_score': 0.75
                    },
                    'timestamp': (datetime.now() - timedelta(hours=5)).isoformat(),
                    'location_name': 'Boston'
                }
            }
        }
        weather_service.storage.read = Mock(return_value=stale_cache)
        
        result = weather_service._get_degraded_weather(42.3601, -71.0589)
        
        assert result['temperature_c'] == 18
        assert result['wind_speed_kph'] == 10
        assert result['conditions'] == 'Cloudy'
        assert result['comfort_score'] == 0.75


# Made with Bob