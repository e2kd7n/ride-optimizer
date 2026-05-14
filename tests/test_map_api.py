"""
Tests for Map API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from app.api import map_api
from src.secure_cache import SecureCacheStorage


@pytest.fixture
def app():
    """Create minimal test app with map blueprint only."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(map_api.bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.mark.unit
class TestGeocodingEndpoints:
    """Test geocoding endpoints."""

    def test_reverse_geocode_success(self, client):
        """Test successful reverse geocoding."""
        mock_location = MagicMock()
        mock_location.address = "123 Main St, New York, NY"
        mock_location.raw = {'address': {'city': 'New York'}}

        with patch('app.api.map_api.geocoder.reverse', return_value=mock_location):
            with patch.object(SecureCacheStorage, 'get', return_value=None):
                with patch.object(SecureCacheStorage, 'set') as mock_set:
                    response = client.get('/api/map/geocode/reverse?lat=40.7128&lng=-74.0060')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['cached'] is False
        assert data['display_name'] == "123 Main St, New York, NY"
        mock_set.assert_called_once()

    def test_reverse_geocode_cached(self, client):
        """Test cached reverse geocoding."""
        cached_data = {
            'location': {'lat': 40.7128, 'lng': -74.0060},
            'display_name': 'Cached Location',
            'address': {'city': 'New York'}
        }

        with patch.object(SecureCacheStorage, 'get', return_value=cached_data):
            response = client.get('/api/map/geocode/reverse?lat=40.7128&lng=-74.0060')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['cached'] is True
        assert data['display_name'] == 'Cached Location'

    def test_reverse_geocode_invalid_coordinates(self, client):
        """Test reverse geocoding with invalid coordinates."""
        response = client.get('/api/map/geocode/reverse?lat=invalid&lng=-74.0060')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_forward_geocode_success(self, client):
        """Test successful forward geocoding."""
        mock_location = MagicMock()
        mock_location.address = "Central Park, New York"
        mock_location.latitude = 40.7829
        mock_location.longitude = -73.9654
        mock_location.raw = {'type': 'park', 'importance': 0.95}

        with patch('app.api.map_api.geocoder.geocode', return_value=[mock_location]):
            response = client.get('/api/map/geocode/forward?q=Central Park')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['query'] == 'Central Park'
        assert len(data['results']) == 1
        assert data['results'][0]['lat'] == 40.7829

    def test_forward_geocode_query_too_short(self, client):
        """Test forward geocoding with short query."""
        response = client.get('/api/map/geocode/forward?q=ab')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


@pytest.mark.unit
class TestUtilityFunctions:
    """Test utility functions."""

    def test_calculate_bounds(self):
        """Test bounds calculation."""
        from app.api.map_api import _calculate_bounds

        coords = [(40.7128, -74.0060), (40.7138, -74.0070), (40.7148, -74.0080)]
        bounds = _calculate_bounds(coords)

        assert bounds['north'] == 40.7148
        assert bounds['south'] == 40.7128
        assert bounds['east'] == -74.0060
        assert bounds['west'] == -74.0080

    def test_get_speed_color(self):
        """Test speed color coding."""
        from app.api.map_api import _get_speed_color

        assert _get_speed_color(4.0) == '#e74c3c'
        assert _get_speed_color(7.0) == '#27ae60'

# Made with Bob
