"""
Tests for Map API endpoints.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app
from src.secure_cache import SecureCacheStorage


@pytest.fixture
def app():
    """Create test app."""
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_route_data():
    """Mock route groups data."""
    return {
        'groups': [
            {
                'id': 'route_test_123',
                'direction': 'home_to_work',
                'frequency': 10,
                'representative_route': {
                    'coordinates': [
                        [40.7128, -74.0060],
                        [40.7138, -74.0070],
                        [40.7148, -74.0080]
                    ],
                    'distance': 5000,
                    'elevation_gain': 50,
                    'average_speed': 5.5
                },
                'routes': [
                    {'average_speed': 5.5},
                    {'average_speed': 6.0}
                ]
            }
        ]
    }


class TestRouteCoordinatesEndpoint:
    """Test /api/map/routes/<id>/coordinates endpoint."""
    
    def test_get_coordinates_success(self, client, mock_route_data):
        """Test successful coordinate fetch."""
        with patch.object(SecureCacheStorage, 'load', return_value=mock_route_data):
            response = client.get('/api/map/routes/route_test_123/coordinates')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
            assert 'coordinates' in data
            assert len(data['coordinates']) == 3
            assert data['coordinates'][0]['lat'] == 40.7128
            assert 'bounds' in data
    
    def test_get_coordinates_with_sampling(self, client, mock_route_data):
        """Test coordinate sampling."""
        with patch.object(SecureCacheStorage, 'load', return_value=mock_route_data):
            response = client.get('/api/map/routes/route_test_123/coordinates?sample_rate=2')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['metadata']['sample_rate'] == 2
            assert len(data['coordinates']) < 3
    
    def test_get_coordinates_not_found(self, client, mock_route_data):
        """Test 404 for non-existent route."""
        with patch.object(SecureCacheStorage, 'load', return_value=mock_route_data):
            response = client.get('/api/map/routes/invalid_route/coordinates')
            
            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data


class TestElevationEndpoint:
    """Test /api/map/routes/<id>/elevation endpoint."""
    
    def test_get_elevation_success(self, client, mock_route_data):
        """Test successful elevation fetch."""
        with patch.object(SecureCacheStorage, 'load', return_value=mock_route_data):
            response = client.get('/api/map/routes/route_test_123/elevation')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
            assert 'elevation_data' in data
            assert 'statistics' in data
            assert data['statistics']['elevation_gain'] == 50
    
    def test_get_elevation_with_points(self, client, mock_route_data):
        """Test elevation with custom point count."""
        with patch.object(SecureCacheStorage, 'load', return_value=mock_route_data):
            response = client.get('/api/map/routes/route_test_123/elevation?points=50')
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data['elevation_data']) <= 50


class TestSpeedAnalyticsEndpoint:
    """Test /api/map/routes/<id>/analytics/speed endpoint."""
    
    def test_get_speed_analytics_success(self, client, mock_route_data):
        """Test successful speed analytics fetch."""
        with patch.object(SecureCacheStorage, 'load', return_value=mock_route_data):
            response = client.get('/api/map/routes/route_test_123/analytics/speed')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
            assert data['analytics_type'] == 'speed'
            assert 'segments' in data
            assert len(data['segments']) > 0
            assert 'color' in data['segments'][0]
            assert 'speed' in data['segments'][0]


class TestGeocodingEndpoints:
    """Test geocoding endpoints."""
    
    def test_reverse_geocode_success(self, client):
        """Test successful reverse geocoding."""
        mock_location = MagicMock()
        mock_location.address = "123 Main St, New York, NY"
        mock_location.raw = {'address': {'city': 'New York'}}
        
        with patch('app.api.map_api.geocoder.reverse', return_value=mock_location):
            with patch.object(SecureCacheStorage, 'get', return_value=None):
                with patch.object(SecureCacheStorage, 'set'):
                    response = client.get('/api/map/geocode/reverse?lat=40.7128&lng=-74.0060')
                    
                    assert response.status_code == 200
                    data = response.get_json()
                    assert data['status'] == 'success'
                    assert 'display_name' in data
    
    def test_reverse_geocode_cached(self, client):
        """Test cached reverse geocoding."""
        cached_data = {
            'location': {'lat': 40.7128, 'lng': -74.0060},
            'display_name': 'Cached Location'
        }
        
        with patch.object(SecureCacheStorage, 'get', return_value=cached_data):
            response = client.get('/api/map/geocode/reverse?lat=40.7128&lng=-74.0060')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['cached'] == True
    
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
            assert len(data['results']) == 1
            assert data['results'][0]['lat'] == 40.7829
    
    def test_forward_geocode_query_too_short(self, client):
        """Test forward geocoding with short query."""
        response = client.get('/api/map/geocode/forward?q=ab')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


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
        
        # Slow speed (< 15 km/h = 4.17 m/s)
        assert _get_speed_color(4.0) == '#e74c3c'  # Red
        
        # Fast speed (> 25 km/h = 6.94 m/s)
        assert _get_speed_color(7.0) == '#27ae60'  # Green

# Made with Bob
