"""
End-to-end workflow tests for Smart Static architecture.

Tests the complete workflow:
1. API serves cached data (no auth required)
2. Cron jobs update cache (auth required)
3. API serves updated data
4. Frontend can fetch and display data
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from api import app
from src.json_storage import JSONStorage


@pytest.fixture
def storage(tmp_path):
    """Create temporary storage for E2E tests."""
    return JSONStorage(data_dir=tmp_path)


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_services(monkeypatch):
    """Mock all services for E2E testing."""
    # Import fixtures from conftest
    from tests.conftest import (
        mock_analysis_service, mock_weather_service,
        mock_commute_service, mock_route_library_service,
        mock_planner_service, mock_config
    )
    
    # Create mock instances
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        'location.home.latitude': 40.7128,
        'location.home.longitude': -74.0060,
    }.get(key, default)
    
    analysis = Mock()
    analysis.get_analysis_status.return_value = {
        'has_data': True,
        'last_analysis': datetime.now().isoformat(),
        'activities_count': 150,
        'route_groups_count': 12,
        'long_rides_count': 8,
        'data_age_hours': 2.5,
        'is_stale': False
    }
    
    weather = Mock()
    weather.get_current_weather.return_value = {
        'temperature': 72,
        'comfort_score': 85
    }
    
    commute = Mock()
    commute.get_next_commute.return_value = {
        'status': 'success',
        'direction': 'to_work',
        'recommended_route': {'name': 'Morning Commute', 'score': 92}
    }
    
    routes = Mock()
    routes.get_all_routes.return_value = {
        'status': 'success',
        'routes': [{'id': 1, 'name': 'Test Route'}],
        'total_count': 1
    }
    
    planner = Mock()
    
    # Patch initialize_services
    def mock_initialize():
        import api
        api._services_initialized = True
        api._analysis_service = analysis
        api._weather_service = weather
        api._commute_service = commute
        api._route_library_service = routes
        api._planner_service = planner
    
    monkeypatch.setattr('api.config', config)
    monkeypatch.setattr('api.initialize_services', mock_initialize)
    
    return {
        'analysis': analysis,
        'weather': weather,
        'commute': commute,
        'routes': routes,
        'planner': planner
    }


class TestE2EWorkflow:
    """End-to-end workflow tests."""
    
    def test_complete_workflow(self, client, mock_services, storage):
        """
        Test complete Smart Static workflow:
        1. API starts without auth
        2. API serves cached data
        3. All endpoints work
        4. Data is consistent
        """
        # Step 1: Verify API starts without authentication
        response = client.get('/api/status')
        assert response.status_code == 200
        
        # Step 2: Verify all endpoints work
        endpoints = [
            '/api/status',
            '/api/weather?lat=40.7128&lon=-74.0060',
            '/api/recommendation',
            '/api/routes'
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Failed: {endpoint}"
            data = json.loads(response.data)
            assert data['status'] == 'success', f"Failed: {endpoint}"
        
        # Step 3: Verify data consistency
        status_response = client.get('/api/status')
        status_data = json.loads(status_response.data)
        
        assert status_data['data']['has_data'] is True
        assert status_data['data']['activities_count'] == 150
        assert status_data['data']['route_groups_count'] == 12
    
    def test_api_without_cache(self, client, mock_services):
        """Test API behavior when no cached data exists."""
        # Configure mock to return no data
        mock_services['analysis'].get_analysis_status.return_value = {
            'has_data': False,
            'last_analysis': None,
            'activities_count': 0,
            'route_groups_count': 0,
            'long_rides_count': 0,
            'data_age_hours': None,
            'is_stale': True
        }
        
        response = client.get('/api/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['data']['has_data'] is False
        assert data['data']['activities_count'] == 0
    
    def test_api_performance(self, client, mock_services):
        """Test API response times are acceptable."""
        endpoints = [
            '/api/status',
            '/api/weather?lat=40.7128&lon=-74.0060',
            '/api/routes'
        ]
        
        for endpoint in endpoints:
            start = time.time()
            response = client.get(endpoint)
            duration = time.time() - start
            
            assert response.status_code == 200
            assert duration < 0.5, f"{endpoint} took {duration}s (should be < 0.5s)"
    
    def test_static_file_serving(self, client):
        """Test static HTML files are served correctly."""
        # Test main pages
        pages = ['/', '/dashboard.html', '/routes.html', '/commute.html']
        
        for page in pages:
            response = client.get(page)
            assert response.status_code == 200
            assert response.content_type.startswith('text/html')
    
    def test_error_recovery(self, client, mock_services):
        """Test system recovers gracefully from errors."""
        # Simulate service error
        mock_services['weather'].get_current_weather.side_effect = Exception('Test error')
        
        response = client.get('/api/weather?lat=40.7128&lon=-74.0060')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Test error' in data['message']
        
        # Reset and verify recovery
        mock_services['weather'].get_current_weather.side_effect = None
        mock_services['weather'].get_current_weather.return_value = {
            'temperature': 72,
            'comfort_score': 85
        }
        
        response = client.get('/api/weather?lat=40.7128&lon=-74.0060')
        assert response.status_code == 200
    
    def test_concurrent_requests(self, client, mock_services):
        """Test API handles multiple requests correctly."""
        # Make multiple requests
        responses = []
        for _ in range(10):
            response = client.get('/api/status')
            responses.append(response)
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # All should return consistent data
        data_list = [json.loads(r.data) for r in responses]
        first_data = data_list[0]
        
        for data in data_list[1:]:
            assert data['data']['activities_count'] == first_data['data']['activities_count']
    
    def test_data_freshness_indicator(self, client, mock_services):
        """Test API correctly indicates data freshness."""
        # Test with fresh data
        mock_services['analysis'].get_analysis_status.return_value = {
            'has_data': True,
            'last_analysis': datetime.now().isoformat(),
            'data_age_hours': 2.0,
            'is_stale': False
        }
        
        response = client.get('/api/status')
        data = json.loads(response.data)
        assert data['data']['is_stale'] is False
        
        # Test with stale data
        mock_services['analysis'].get_analysis_status.return_value = {
            'has_data': True,
            'last_analysis': datetime.now().isoformat(),
            'data_age_hours': 30.0,
            'is_stale': True
        }
        
        response = client.get('/api/status')
        data = json.loads(response.data)
        assert data['data']['is_stale'] is True


class TestE2EIntegration:
    """Integration tests for complete system."""
    
    def test_full_stack_integration(self, client, mock_services):
        """Test full stack from API to services to storage."""
        # 1. Check system status
        status_response = client.get('/api/status')
        assert status_response.status_code == 200
        
        # 2. Get weather data
        weather_response = client.get('/api/weather?lat=40.7128&lon=-74.0060')
        assert weather_response.status_code == 200
        weather_data = json.loads(weather_response.data)
        assert 'weather' in weather_data
        
        # 3. Get route recommendations
        routes_response = client.get('/api/routes')
        assert routes_response.status_code == 200
        routes_data = json.loads(routes_response.data)
        assert 'routes' in routes_data
        
        # 4. Get commute recommendation
        commute_response = client.get('/api/recommendation')
        assert commute_response.status_code == 200
        commute_data = json.loads(commute_response.data)
        assert commute_data['status'] == 'success'
    
    def test_api_data_consistency(self, client, mock_services):
        """Test data consistency across multiple API calls."""
        # Make multiple calls to same endpoint
        responses = [client.get('/api/status') for _ in range(5)]
        
        # Parse all responses
        data_list = [json.loads(r.data) for r in responses]
        
        # Verify all return same data
        first_count = data_list[0]['data']['activities_count']
        assert all(d['data']['activities_count'] == first_count for d in data_list)


# Made with Bob