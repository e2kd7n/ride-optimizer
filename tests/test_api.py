"""
Unit tests for launch.py API endpoints.
"""

import pytest
import launch


@pytest.mark.unit
class TestLaunchAPIEndpoints:
    """Test suite for Smart Static API endpoints in launch.py."""

    def test_index_route(self, client):
        """Test index route serves static content."""
        response = client.get('/')
        assert response.status_code in [200, 404]

    def test_weather_endpoint_with_params(self, client, mock_services):
        """Test /api/weather with explicit lat/lon parameters."""
        mock_services['weather'].get_current_weather.return_value = {
            'temperature_f': 72,
            'feels_like_f': 70,
            'conditions': 'Clear',
            'wind_speed_kph': 16,
            'wind_direction_cardinal': 'NW',
            'humidity': 55,
            'precipitation_mm': 0,
            'comfort_score': 0.9
        }

        response = client.get('/api/weather?lat=40.7128&lon=-74.0060&location=NYC')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'current' in data
        assert data['current']['temperature'] == 72
        assert data['current']['comfort_score'] == 90

    def test_weather_endpoint_no_params_uses_home_location(self, client, mock_services):
        """Test /api/weather falls back to configured home location."""
        mock_services['weather'].get_current_weather.return_value = {
            'temperature_f': 68,
            'feels_like_f': 66,
            'conditions': 'Cloudy',
            'wind_speed_kph': 10,
            'wind_direction_cardinal': 'N',
            'humidity': 70,
            'precipitation_mm': 0.2,
            'comfort_score': 0.7
        }

        response = client.get('/api/weather')

        assert response.status_code == 200
        mock_services['weather'].get_current_weather.assert_called_once()
        args = mock_services['weather'].get_current_weather.call_args[0]
        assert args[0] == 40.7128
        assert args[1] == -74.0060

    def test_weather_endpoint_error(self, client, mock_services):
        """Test /api/weather error handling."""
        mock_services['weather'].get_current_weather.side_effect = Exception('API Error')

        response = client.get('/api/weather?lat=40.7128&lon=-74.0060')

        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'API Error' in data['message']

    def test_recommendation_endpoint_formats_success_payload(self, client, mock_services):
        """Test /api/recommendation returns normalized frontend/API payload."""
        mock_services['commute'].get_next_commute.return_value = {
            'status': 'success',
            'direction': 'to_work',
            'time_window': 'morning',
            'is_today': True,
            'departure_time': '8:00 AM',
            'confidence': 'high',
            'route': {
                'id': 'route-1',
                'name': 'Main Route',
                'distance': 5200,
                'duration': 1500,
                'elevation': 45,
                'coordinates': [(40.7128, -74.0060), (40.7589, -73.9851)]
            },
            'score': 0.85,
            'breakdown': {
                'weather': 0.9,
                'time': 0.8
            },
            'weather': {
                'temperature': 72,
                'conditions': 'Clear'
            }
        }

        response = client.get('/api/recommendation')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['direction'] == 'to_work'
        assert data['score'] == 85
        assert data['recommended_route']['id'] == 'route-1'
        assert data['recommended_route']['distance'] == 5.2
        assert data['route']['name'] == 'Main Route'
        assert 'Weather: 90%' in data['factors']
        assert 'Time: 80%' in data['factors']

    def test_recommendation_with_direction(self, client, mock_services):
        """Test /api/recommendation forwards direction parameter."""
        mock_services['commute'].get_next_commute.return_value = {
            'status': 'error',
            'direction': 'to_home',
            'message': 'No routes available',
            'route': None
        }

        response = client.get('/api/recommendation?direction=to_home')

        assert response.status_code == 200
        mock_services['commute'].get_next_commute.assert_called_with('to_home')
        data = response.get_json()
        assert data['direction'] == 'to_home'

    def test_routes_endpoint(self, client, mock_services):
        """Test /api/routes endpoint."""
        mock_services['route_library'].get_all_routes.return_value = {
            'status': 'success',
            'routes': [
                {'id': '1', 'name': 'Route 1', 'distance': 5.0},
                {'id': '2', 'name': 'Route 2', 'distance': 6.5}
            ],
            'total_count': 2
        }

        response = client.get('/api/routes')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['routes']) == 2

    def test_routes_with_filters(self, client, mock_services):
        """Test /api/routes with filter parameters."""
        mock_services['route_library'].get_all_routes.return_value = {
            'status': 'success',
            'routes': []
        }

        response = client.get('/api/routes?type=commute&sort=distance&limit=10')

        assert response.status_code == 200
        mock_services['route_library'].get_all_routes.assert_called_with(
            route_type='commute',
            sort_by='distance',
            limit=10
        )

    def test_status_endpoint(self, client, mock_services):
        """Test /api/status endpoint."""
        mock_services['analysis'].get_analysis_status.return_value = {
            'has_data': True,
            'last_analysis': '2026-05-07T03:00:00',
            'activities_count': 150,
            'route_groups_count': 12,
            'long_rides_count': 8
        }

        response = client.get('/api/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'services' in data
        assert 'data' in data

    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/api/nonexistent')

        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()


@pytest.mark.integration
class TestLaunchInitialization:
    """Light integration coverage for launch service initialization."""

    def test_initialize_services_uses_existing_flag(self, monkeypatch):
        """Test initialize_services returns early when already initialized."""
        monkeypatch.setattr(launch, '_services_initialized', True)
        launch.initialize_services()
        assert launch._services_initialized is True

# Made with Bob
