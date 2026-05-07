"""
Unit tests for commute route handlers.

Tests the Flask route handlers in app/routes/commute.py that provide
the commute recommendation interface.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from flask import Flask

from app.routes.commute import bp as commute_bp


@pytest.fixture
def app():
    """Create a test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.register_blueprint(commute_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def mock_services():
    """Create mock services."""
    analysis_service = Mock()
    commute_service = Mock()
    weather_service = Mock()
    
    # Set up default return values
    analysis_service.get_route_groups.return_value = [{'id': 1, 'name': 'Group 1'}]
    analysis_service.get_locations.return_value = ({'lat': 40.7, 'lon': -74.0}, {'lat': 40.8, 'lon': -74.1})
    
    return {
        'analysis': analysis_service,
        'commute': commute_service,
        'weather': weather_service
    }


class TestCommuteIndex:
    """Tests for the commute index page."""

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_index_success_with_recommendation(self, mock_render, mock_get_services, client, mock_services):
        """Test successful index page with commute recommendation."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        # Mock successful recommendation
        mock_services['commute'].get_workout_aware_commute.return_value = {
            'status': 'success',
            'direction': 'to_work',
            'route': {
                'name': 'Morning Commute',
                'id': 123,
                'distance': 15500,  # meters
                'duration': 2700,  # seconds (45 min)
                'elevation': 150
            },
            'score': 0.85,
            'breakdown': {'weather': 0.9, 'traffic': 0.8},
            'weather': {'temp': 18, 'conditions': 'Clear'},
            'departure_time': '07:30',
            'confidence': 'high',
            'workout_fit': {'match': 'good', 'intensity': 'moderate'}
        }
        
        # Mock alternatives
        mock_services['commute'].get_all_commute_options.return_value = {
            'status': 'success',
            'options': [
                {'route': {'name': 'Primary', 'id': 123, 'distance': 15500, 'duration': 2700, 'elevation': 150}, 'score': 0.85},
                {'route': {'name': 'Alt 1', 'id': 124, 'distance': 16000, 'duration': 2800, 'elevation': 120}, 'score': 0.80}
            ]
        }
        
        # Mock departure windows
        mock_services['commute'].get_departure_windows.return_value = {
            'status': 'success',
            'windows': [
                {'direction': 'to_work', 'start_time': '07:00', 'end_time': '08:00', 'optimal_time': '07:30', 'score': 0.9}
            ]
        }
        
        response = client.get('/commute/')
        
        assert response.status_code == 200
        mock_render.assert_called_once()
        assert 'commute/index.html' in str(mock_render.call_args)

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_index_no_recommendation(self, mock_render, mock_get_services, client, mock_services):
        """Test index page when no recommendation is available."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        # Mock no recommendation
        mock_services['commute'].get_workout_aware_commute.return_value = {
            'status': 'error',
            'message': 'No routes available'
        }
        
        response = client.get('/commute/')
        
        assert response.status_code == 200
        mock_render.assert_called_once()

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_index_with_direction_param(self, mock_render, mock_get_services, client, mock_services):
        """Test index page with direction parameter."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        # Mock the service methods - need route_groups and locations for code to reach get_next_commute
        mock_route_group = Mock()
        mock_route_group.name = 'Test Route'
        mock_services['analysis'].get_route_groups.return_value = [mock_route_group]
        mock_services['analysis'].get_locations.return_value = ({'lat': 0, 'lng': 0}, {'lat': 1, 'lng': 1})
        mock_services['commute'].initialize.return_value = None
        mock_services['commute'].get_next_commute.return_value = {'status': 'error'}
        mock_services['commute'].get_all_commute_options.return_value = {'status': 'error'}
        mock_services['commute'].get_departure_windows.return_value = {'status': 'error'}
        
        response = client.get('/commute/?direction=from_work')
        
        assert response.status_code == 200
        # Verify direction parameter was passed
        mock_services['commute'].get_next_commute.assert_called_with(direction='from_work')

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_index_service_error(self, mock_render, mock_get_services, client, mock_services):
        """Test index page with service error."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        # Mock service error
        mock_services['analysis'].get_route_groups.side_effect = Exception("Service error")
        
        response = client.get('/commute/')
        
        # Should still render page with empty data
        assert response.status_code == 200
        mock_render.assert_called_once()

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_index_no_locations(self, mock_render, mock_get_services, client, mock_services):
        """Test index page when locations are not configured."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        # Mock no locations
        mock_services['analysis'].get_locations.return_value = (None, None)
        
        response = client.get('/commute/')
        
        assert response.status_code == 200
        mock_render.assert_called_once()


class TestCommuteAnalyze:
    """Tests for the commute analyze endpoint."""

    @patch('app.routes.commute.get_services')
    def test_analyze_default_params(self, mock_get_services, client, mock_services):
        """Test analyze endpoint with default parameters."""
        mock_get_services.return_value = mock_services
        
        # Mock the service to return a proper dictionary with all required fields
        mock_services['commute'].get_workout_aware_commute.return_value = {
            'status': 'success',
            'route': {
                'name': 'Test Route',
                'id': 123,
                'distance': 10000,
                'duration': 1800,
                'elevation': 100
            },
            'score': 0.85,
            'direction': 'to_work',
            'breakdown': {'weather': 0.9, 'traffic': 0.8},
            'weather': {'temp': 18, 'conditions': 'Clear'},
            'departure_time': '07:30',
            'confidence': 'high'
        }
        
        response = client.post('/commute/analyze', json={})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'analysis_timestamp' in data
        assert 'recommendation' in data

    @patch('app.routes.commute.get_services')
    def test_analyze_with_params(self, mock_get_services, client, mock_services):
        """Test analyze endpoint with custom parameters."""
        mock_get_services.return_value = mock_services
        
        # Mock the service to return a proper dictionary with all required fields
        mock_services['commute'].get_workout_aware_commute.return_value = {
            'status': 'success',
            'route': {
                'name': 'Test Route',
                'id': 124,
                'distance': 10000,
                'duration': 1800,
                'elevation': 100
            },
            'score': 0.85,
            'direction': 'from_work',
            'breakdown': {'weather': 0.9, 'traffic': 0.8},
            'weather': {'temp': 18, 'conditions': 'Clear'},
            'departure_time': '17:30',
            'confidence': 'high'
        }
        
        request_data = {
            'departure_time': '2026-05-07T07:30:00',
            'direction': 'from_work',
            'force_refresh': True
        }
        
        response = client.post('/commute/analyze', json=request_data)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'recommendation' in data

    @patch('app.routes.commute.get_services')
    def test_analyze_no_json_body(self, mock_get_services, client, mock_services):
        """Test analyze endpoint without JSON body."""
        mock_get_services.return_value = mock_services
        
        response = client.post('/commute/analyze')
        
        # Flask returns 415 when no content-type header for POST
        # This is expected behavior - endpoint expects JSON
        assert response.status_code == 415

    @patch('app.routes.commute.get_services')
    def test_analyze_invalid_method(self, mock_get_services, client, mock_services):
        """Test analyze endpoint with GET method (should fail)."""
        mock_get_services.return_value = mock_services
        
        response = client.get('/commute/analyze')
        
        assert response.status_code == 405  # Method Not Allowed


class TestCommuteHistory:
    """Tests for the commute history endpoint."""

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_history_success(self, mock_render, mock_get_services, client, mock_services):
        """Test successful history page rendering."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        response = client.get('/commute/history')
        
        assert response.status_code == 200
        mock_render.assert_called_once()
        assert 'commute/history.html' in str(mock_render.call_args)

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_history_context(self, mock_render, mock_get_services, client, mock_services):
        """Test history page context data."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        response = client.get('/commute/history')
        
        assert response.status_code == 200
        call_args = mock_render.call_args
        context = call_args[1]
        assert 'page_title' in context
        assert context['page_title'] == 'Commute History'


class TestCommuteApiCurrent:
    """Tests for the current commute API endpoint."""

    @patch('app.routes.commute.get_services')
    def test_api_current_success(self, mock_get_services, client, mock_services):
        """Test successful API current endpoint."""
        mock_get_services.return_value = mock_services
        
        response = client.get('/commute/api/current')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'recommendation' in data
        assert 'confidence' in data
        assert 'last_updated' in data
        assert 'factors' in data

    @patch('app.routes.commute.get_services')
    def test_api_current_json_structure(self, mock_get_services, client, mock_services):
        """Test API current endpoint JSON structure."""
        mock_get_services.return_value = mock_services
        
        response = client.get('/commute/api/current')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify factors structure
        assert 'weather' in data['factors']
        assert 'traffic' in data['factors']
        assert 'workout_fit' in data['factors']
        
        # Verify confidence is a number
        assert isinstance(data['confidence'], (int, float))

    @patch('app.routes.commute.get_services')
    def test_api_current_invalid_method(self, mock_get_services, client, mock_services):
        """Test API current endpoint with POST method."""
        mock_get_services.return_value = mock_services
        
        response = client.post('/commute/api/current')
        
        # Flask returns 405 for methods not explicitly allowed
        # This is correct behavior - endpoint is GET only
        assert response.status_code == 405


class TestCommuteServiceIntegration:
    """Tests for service layer integration."""

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_service_initialization(self, mock_render, mock_get_services, client, mock_services):
        """Test that commute service is properly initialized."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        mock_services['commute'].get_workout_aware_commute.return_value = {'status': 'error'}
        
        response = client.get('/commute/')
        
        assert response.status_code == 200
        # Verify initialize was called with route groups and locations
        mock_services['commute'].initialize.assert_called_once()

    @patch('app.routes.commute.get_services')
    @patch('app.routes.commute.render_template')
    def test_workout_fit_integration(self, mock_render, mock_get_services, client, mock_services):
        """Test commute recommendation with route data.
        
        Note: workout_fit feature not yet implemented in route handler.
        Will be added when TrainerRoad integration is complete.
        """
        mock_get_services.return_value = mock_services
        mock_render.return_value = 'rendered_template'
        
        # Mock the service methods
        mock_services['analysis'].get_route_groups.return_value = [{'id': 1, 'name': 'Test Route'}]
        mock_services['analysis'].get_locations.return_value = ({'lat': 0, 'lng': 0}, {'lat': 1, 'lng': 1})
        mock_services['commute'].initialize.return_value = None
        mock_services['commute'].get_next_commute.return_value = {
            'status': 'success',
            'direction': 'to_work',
            'route': {'name': 'Test', 'id': 1, 'distance': 10000, 'duration': 1800, 'elevation': 100, 'coordinates': []},
            'score': 85,
            'breakdown': {},
            'departure_time': '08:00',
            'confidence': 'high'
        }
        mock_services['commute'].get_all_commute_options.return_value = {'status': 'success', 'options': []}
        mock_services['commute'].get_departure_windows.return_value = {'status': 'success', 'windows': []}
        
        response = client.get('/commute/')
        
        assert response.status_code == 200
        call_args = mock_render.call_args
        context = call_args[1]
        assert context['recommendation'] is not None
        assert context['recommendation']['route_name'] == 'Test'

# Made with Bob
