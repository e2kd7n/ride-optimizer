"""
Unit tests for minimal API (api.py).

Tests all 4 endpoints, query parameters, error handling, and service initialization.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the Flask app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import api


@pytest.fixture
def client():
    """Create test client for Flask app."""
    api.app.config['TESTING'] = True
    with api.app.test_client() as client:
        yield client


@pytest.fixture
def mock_services():
    """Mock all services."""
    with patch('api._analysis_service') as mock_analysis, \
         patch('api._commute_service') as mock_commute, \
         patch('api._weather_service') as mock_weather, \
         patch('api._planner_service') as mock_planner, \
         patch('api._route_library_service') as mock_route_library:
        
        # Mark services as initialized
        api._services_initialized = True
        
        yield {
            'analysis': mock_analysis,
            'commute': mock_commute,
            'weather': mock_weather,
            'planner': mock_planner,
            'route_library': mock_route_library
        }


class TestAPIEndpoints:
    """Test suite for API endpoints."""
    
    def test_index_route(self, client):
        """Test index route serves dashboard.html."""
        response = client.get('/')
        # Will return 404 if static file doesn't exist, which is expected in tests
        assert response.status_code in [200, 404]
    
    def test_weather_endpoint_with_params(self, client, mock_services):
        """Test /api/weather with lat/lon parameters."""
        mock_weather = mock_services['weather']
        mock_weather.get_current_weather.return_value = {
            'temperature_f': 72,
            'conditions': 'Clear',
            'comfort_score': 0.9
        }
        
        response = client.get('/api/weather?lat=40.7128&lon=-74.0060&location=NYC')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'weather' in data
        assert data['weather']['temperature_f'] == 72
    
    def test_weather_endpoint_no_params(self, client, mock_services):
        """Test /api/weather without parameters uses home location."""
        with patch('api.config') as mock_config:
            mock_config.get.side_effect = lambda key: {
                'location.home.latitude': 40.7128,
                'location.home.longitude': -74.0060
            }.get(key)
            
            mock_weather = mock_services['weather']
            mock_weather.get_current_weather.return_value = {
                'temperature_f': 72
            }
            
            response = client.get('/api/weather')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
    
    def test_weather_endpoint_error(self, client, mock_services):
        """Test /api/weather error handling."""
        mock_weather = mock_services['weather']
        mock_weather.get_current_weather.side_effect = Exception('API Error')
        
        response = client.get('/api/weather?lat=40.7128&lon=-74.0060')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_recommendation_endpoint(self, client, mock_services):
        """Test /api/recommendation endpoint."""
        mock_commute = mock_services['commute']
        mock_commute.get_next_commute.return_value = {
            'status': 'success',
            'direction': 'to_work',
            'route': {
                'name': 'Main Route',
                'distance': 5.2,
                'duration': 25
            },
            'score': 0.85
        }
        
        response = client.get('/api/recommendation')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['direction'] == 'to_work'
    
    def test_recommendation_with_direction(self, client, mock_services):
        """Test /api/recommendation with direction parameter."""
        mock_commute = mock_services['commute']
        mock_commute.get_next_commute.return_value = {
            'status': 'success',
            'direction': 'to_home'
        }
        
        response = client.get('/api/recommendation?direction=to_home')
        
        assert response.status_code == 200
        mock_commute.get_next_commute.assert_called_with('to_home')
    
    def test_routes_endpoint(self, client, mock_services):
        """Test /api/routes endpoint."""
        mock_route_library = mock_services['route_library']
        mock_route_library.get_all_routes.return_value = {
            'status': 'success',
            'routes': [
                {'id': '1', 'name': 'Route 1', 'distance': 5.0},
                {'id': '2', 'name': 'Route 2', 'distance': 6.5}
            ],
            'total_count': 2
        }
        
        response = client.get('/api/routes')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert len(data['routes']) == 2
    
    def test_routes_with_filters(self, client, mock_services):
        """Test /api/routes with filter parameters."""
        mock_route_library = mock_services['route_library']
        mock_route_library.get_all_routes.return_value = {
            'status': 'success',
            'routes': []
        }
        
        response = client.get('/api/routes?type=commute&sort=distance&limit=10')
        
        assert response.status_code == 200
        mock_route_library.get_all_routes.assert_called_with(
            route_type='commute',
            sort_by='distance',
            limit=10
        )
    
    def test_status_endpoint(self, client, mock_services):
        """Test /api/status endpoint."""
        mock_analysis = mock_services['analysis']
        mock_analysis.get_analysis_status.return_value = {
            'has_data': True,
            'last_analysis': '2026-05-07T03:00:00',
            'activities_count': 150,
            'route_groups_count': 12,
            'long_rides_count': 8
        }
        
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'services' in data
        assert 'data' in data
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API with real services."""
    
    def test_service_initialization(self):
        """Test service initialization on first request."""
        # Reset initialization flag
        api._services_initialized = False
        
        # Call initialize_services
        api.initialize_services()
        
        # Verify services are initialized
        assert api._services_initialized is True
        assert api._analysis_service is not None
        assert api._commute_service is not None
        assert api._weather_service is not None


# Made with Bob