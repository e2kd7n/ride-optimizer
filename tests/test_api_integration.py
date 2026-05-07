"""
Integration tests for Smart Static API endpoints.

Tests the full stack: API → Services → JSON Storage
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from api import app
from src.json_storage import JSONStorage


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_storage(tmp_path):
    """Create mock storage with test data."""
    storage = JSONStorage(base_dir=tmp_path)
    
    # Create test data
    test_routes = {
        'routes': [
            {
                'id': 1,
                'name': 'Test Route 1',
                'distance': 10.5,
                'elevation_gain': 500,
                'sport_type': 'Ride',
                'is_favorite': True,
                'uses': 5
            },
            {
                'id': 2,
                'name': 'Test Route 2',
                'distance': 15.2,
                'elevation_gain': 800,
                'sport_type': 'Ride',
                'is_favorite': False,
                'uses': 3
            }
        ],
        'updated_at': datetime.now().isoformat()
    }
    
    test_weather = {
        'current': {
            'temperature': 72,
            'feels_like': 70,
            'humidity': 60,
            'wind_speed': 5,
            'wind_direction': 'NW',
            'description': 'Partly cloudy',
            'comfort_score': 85
        },
        'forecast': [
            {
                'time': datetime.now().isoformat(),
                'temperature': 73,
                'description': 'Sunny'
            }
        ],
        'updated_at': datetime.now().isoformat()
    }
    
    test_status = {
        'last_analysis': datetime.now().isoformat(),
        'has_data': True,
        'storage_used_mb': 10,
        'storage_total_mb': 1000,
        'storage_ok': True,
        'uptime_seconds': 3600
    }
    
    storage.write('routes.json', test_routes)
    storage.write('weather_cache.json', test_weather)
    storage.write('status.json', test_status)
    
    return storage


class TestAPIIntegration:
    """Integration tests for API endpoints."""
    
    def test_api_status_endpoint(self, client):
        """Test /api/status returns system status."""
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert 'timestamp' in data
        assert 'services' in data
        assert 'data' in data
    
    # NOTE: /api/weather endpoint removed in Smart Static migration
    # Weather data now served via static JSON files
    
    def test_api_routes_endpoint(self, client):
        """Test /api/routes returns route data."""
        with patch('api._route_library_service') as mock_service:
            mock_service.get_all_routes.return_value = {
                'routes': [
                    {'id': 1, 'name': 'Test Route', 'distance': 10.5}
                ],
                'total': 1
            }
            
            response = client.get('/api/routes')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'routes' in data
            assert len(data['routes']) > 0
    
    def test_api_recommendation_endpoint(self, client):
        """Test /api/recommendation returns commute recommendation."""
        with patch('api._commute_service') as mock_service:
            mock_service.get_next_commute.return_value = {
                'recommended_route': {
                    'id': 1,
                    'name': 'Best Route',
                    'distance': 10.5
                },
                'score': 85,
                'recommendation': 'Great conditions!'
            }
            
            response = client.get('/api/recommendation')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'recommended_route' in data
            assert 'score' in data
    
    def test_api_routes_with_filters(self, client):
        """Test /api/routes with query parameters."""
        with patch('api._route_library_service') as mock_service:
            mock_service.get_all_routes.return_value = {
                'routes': [],
                'total': 0
            }
            
            response = client.get('/api/routes?type=commute&sort=distance&limit=10')
            
            assert response.status_code == 200
            mock_service.get_all_routes.assert_called_once()
    
    def test_api_weather_with_location(self, client):
        """Test /api/weather with custom location."""
        with patch('api._weather_service') as mock_service:
            mock_service.get_current_weather.return_value = {
                'current': {'temperature': 68}
            }
            
            response = client.get('/api/weather?lat=40.7128&lon=-74.0060')
            
            assert response.status_code == 200
            mock_service.get_current_weather.assert_called_once()
    
    def test_api_error_handling(self, client):
        """Test API error handling."""
        with patch('api._weather_service') as mock_service:
            mock_service.get_current_weather.side_effect = Exception('Test error')
            
            response = client.get('/api/weather')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['status'] == 'error'
    
    def test_api_404_handling(self, client):
        """Test 404 error handling."""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_static_file_serving(self, client):
        """Test static HTML file serving."""
        # Test index redirect
        response = client.get('/')
        assert response.status_code == 200
    
    def test_api_cors_headers(self, client):
        """Test CORS headers are not set (single-user app)."""
        response = client.get('/api/status')
        assert 'Access-Control-Allow-Origin' not in response.headers


class TestAPIServiceIntegration:
    """Test API integration with actual services."""
    
    @patch('api.Config')
    @patch('api.WeatherService')
    def test_weather_service_integration(self, mock_weather_class, mock_config, client):
        """Test weather service integration."""
        mock_weather = Mock()
        mock_weather.get_current_weather.return_value = {
            'current': {
                'temperature': 72,
                'comfort_score': 85
            }
        }
        mock_weather_class.return_value = mock_weather
        
        response = client.get('/api/weather')
        
        assert response.status_code == 200
    
    @patch('api.Config')
    @patch('api.RouteLibraryService')
    def test_route_library_service_integration(self, mock_route_class, mock_config, client):
        """Test route library service integration."""
        mock_routes = Mock()
        mock_routes.get_all_routes.return_value = {
            'routes': [{'id': 1, 'name': 'Test'}],
            'total': 1
        }
        mock_route_class.return_value = mock_routes
        
        response = client.get('/api/routes')
        
        assert response.status_code == 200


class TestAPIPerformance:
    """Performance tests for API endpoints."""
    
    def test_api_response_time(self, client):
        """Test API response time is acceptable."""
        import time
        
        with patch('api._weather_service') as mock_service:
            mock_service.get_current_weather.return_value = {'current': {}}
            
            start = time.time()
            response = client.get('/api/weather')
            duration = time.time() - start
            
            assert response.status_code == 200
            assert duration < 1.0  # Should respond in < 1 second
    
    def test_api_concurrent_requests(self, client):
        """Test API handles concurrent requests."""
        import concurrent.futures
        
        with patch('api._weather_service') as mock_service:
            mock_service.get_current_weather.return_value = {'current': {}}
            
            def make_request():
                return client.get('/api/weather')
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in futures]
            
            assert all(r.status_code == 200 for r in results)


class TestAPIDataFlow:
    """Test complete data flow through API."""
    
    @patch('api.JSONStorage')
    @patch('api.WeatherService')
    def test_weather_data_flow(self, mock_weather_class, mock_storage_class, client):
        """Test weather data flows from service to API to client."""
        # Setup mocks
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        
        mock_weather = Mock()
        mock_weather.get_current_weather.return_value = {
            'current': {
                'temperature': 72,
                'comfort_score': 85,
                'description': 'Sunny'
            }
        }
        mock_weather_class.return_value = mock_weather
        
        # Make request
        response = client.get('/api/weather')
        
        # Verify data flow
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['weather']['current']['temperature'] == 72


# Made with Bob