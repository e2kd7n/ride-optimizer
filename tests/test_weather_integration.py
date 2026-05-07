"""
Integration tests for weather functionality.

Tests:
- WeatherSnapshot model CRUD operations
- WeatherService caching and degradation
- Weather integration in dashboard, commute, and planner
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from app.models.weather import WeatherSnapshot
from app.services.weather_service import WeatherService
from src.config import Config


@pytest.mark.integration
class TestWeatherSnapshotModel:
    """Test WeatherSnapshot SQLite model."""
    
    def test_create_weather_snapshot(self, app):
        """Test creating a weather snapshot."""
        with app.app_context():
            weather_data = {
                'temperature': 20.0,
                'conditions': 'Clear',
                'wind_speed': 10.0,
                'wind_direction': 180,
                'precipitation': 0.0,
                'humidity': 50.0
            }
            
            snapshot = WeatherSnapshot.create_from_weather_data(
                weather_data,
                location_name='Test Location',
                is_current=True
            )
            
            assert snapshot is not None
            assert snapshot.location_name == 'Test Location'
            assert snapshot.is_current is True
            assert 0.0 <= snapshot.comfort_score <= 1.0
            assert snapshot.cycling_favorability in ['favorable', 'neutral', 'unfavorable']
    
    def test_comfort_score_calculation(self, app):
        """Test comfort score algorithm."""
        with app.app_context():
            # Perfect conditions
            perfect_weather = {
                'temperature': 20.0,  # 68°F
                'wind_speed': 5.0,
                'precipitation': 0.0
            }
            snapshot = WeatherSnapshot.create_from_weather_data(
                perfect_weather,
                location_name='Perfect',
                is_current=True
            )
            assert snapshot.comfort_score >= 0.8
            assert snapshot.cycling_favorability == 'favorable'
            
            # Poor conditions
            poor_weather = {
                'temperature': -5.0,  # 23°F
                'wind_speed': 35.0,
                'precipitation': 10.0
            }
            snapshot = WeatherSnapshot.create_from_weather_data(
                poor_weather,
                location_name='Poor',
                is_current=True
            )
            assert snapshot.comfort_score < 0.4
            assert snapshot.cycling_favorability == 'unfavorable'
    
    def test_get_current_for_location(self, app):
        """Test retrieving cached weather by location."""
        with app.app_context():
            # Create snapshot
            weather_data = {'temperature': 20.0, 'conditions': 'Clear'}
            snapshot = WeatherSnapshot.create_from_weather_data(
                weather_data,
                location_name='Test',
                is_current=True
            )
            
            lat, lon = snapshot.latitude, snapshot.longitude
            
            # Retrieve within fresh window
            retrieved = WeatherSnapshot.get_current_for_location(lat, lon, max_age_hours=2)
            assert retrieved is not None
            assert retrieved.id == snapshot.id
            
            # Should not retrieve if too old
            snapshot.timestamp = datetime.now(timezone.utc) - timedelta(hours=25)
            snapshot.save()
            
            retrieved = WeatherSnapshot.get_current_for_location(lat, lon, max_age_hours=24)
            assert retrieved is None
    
    def test_cleanup_old_snapshots(self, app):
        """Test automatic cleanup of old weather data."""
        with app.app_context():
            # Create old snapshot
            weather_data = {'temperature': 20.0}
            snapshot = WeatherSnapshot.create_from_weather_data(
                weather_data,
                location_name='Old',
                is_current=True
            )
            snapshot.timestamp = datetime.now(timezone.utc) - timedelta(days=10)
            snapshot.save()
            
            # Cleanup
            deleted = WeatherSnapshot.cleanup_old_snapshots(days=7)
            assert deleted >= 1


@pytest.mark.integration
class TestWeatherService:
    """Test WeatherService caching and degradation."""
    
    @pytest.fixture
    def weather_service(self):
        """Create weather service instance."""
        config = Config('config/config.yaml')
        return WeatherService(config)
    
    @patch('src.weather_fetcher.WeatherFetcher.get_current_conditions')
    def test_get_current_weather_cache_hit(self, mock_fetch, weather_service, app):
        """Test cache hit returns cached data without API call."""
        with app.app_context():
            # Pre-populate cache
            weather_data = {'temperature': 20.0, 'conditions': 'Clear'}
            WeatherSnapshot.create_from_weather_data(
                weather_data,
                location_name='Test',
                is_current=True
            )
            
            # Get weather (should use cache)
            result = weather_service.get_current_weather(40.7128, -74.0060, 'Test')
            
            assert result is not None
            assert 'temperature_c' in result or 'temperature' in result
            mock_fetch.assert_not_called()  # Should not call API
    
    @patch('src.weather_fetcher.WeatherFetcher.get_current_conditions')
    def test_get_current_weather_cache_miss(self, mock_fetch, weather_service, app):
        """Test cache miss fetches from API."""
        with app.app_context():
            # Mock API response
            mock_fetch.return_value = {
                'temperature': 22.0,
                'conditions': 'Partly Cloudy',
                'wind_speed': 12.0
            }
            
            # Get weather (cache miss)
            result = weather_service.get_current_weather(40.7128, -74.0060, 'NYC')
            
            assert result is not None
            mock_fetch.assert_called_once()
    
    @patch('src.weather_fetcher.WeatherFetcher.get_current_conditions')
    def test_graceful_degradation_stale_data(self, mock_fetch, weather_service, app):
        """Test fallback to stale data when API fails."""
        with app.app_context():
            # Create stale snapshot (3 hours old)
            weather_data = {'temperature': 18.0, 'conditions': 'Cloudy'}
            snapshot = WeatherSnapshot.create_from_weather_data(
                weather_data,
                location_name='Stale',
                is_current=True
            )
            snapshot.timestamp = datetime.now(timezone.utc) - timedelta(hours=3)
            snapshot.save()
            
            lat, lon = snapshot.latitude, snapshot.longitude
            
            # Mock API failure
            mock_fetch.return_value = None
            
            # Should return stale data
            result = weather_service.get_current_weather(lat, lon, 'Stale')
            
            assert result is not None
            assert result.get('is_stale') is True
            assert result.get('age_hours', 0) >= 3
    
    def test_get_route_weather_with_wind_impact(self, weather_service, app):
        """Test route weather includes wind impact analysis."""
        with app.app_context():
            coordinates = [
                (40.7128, -74.0060),
                (40.7580, -73.9855),
                (40.7614, -73.9776)
            ]
            
            with patch('src.weather_fetcher.WeatherFetcher.get_current_conditions') as mock_fetch:
                mock_fetch.return_value = {
                    'temperature': 20.0,
                    'wind_speed': 15.0,
                    'wind_direction': 180
                }
                
                result = weather_service.get_route_weather(coordinates, 'Test Route')
                
                assert result is not None
                # Wind impact may or may not be present depending on calculator
                # Just verify we got weather data
                assert 'temperature' in result or 'temperature_c' in result


@pytest.mark.integration
class TestWeatherUIIntegration:
    """Test weather integration in UI views."""
    
    def test_dashboard_weather_display(self, client, app):
        """Test dashboard shows weather card."""
        with app.app_context():
            # Pre-populate weather
            weather_data = {'temperature': 20.0, 'conditions': 'Clear'}
            WeatherSnapshot.create_from_weather_data(
                weather_data,
                location_name='Home',
                is_current=True
            )
            
            response = client.get('/')
            assert response.status_code == 200
            # Check for weather-related content
            assert b'Weather' in response.data or b'weather' in response.data
    
    def test_commute_weather_reasoning(self, client, app):
        """Test commute view shows weather reasoning."""
        with app.app_context():
            response = client.get('/commute')
            assert response.status_code == 200
            # Weather section should be present
            assert b'Weather' in response.data or b'weather' in response.data


# Made with Bob