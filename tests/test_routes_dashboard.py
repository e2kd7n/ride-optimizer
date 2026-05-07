"""
Unit tests for Dashboard routes.

Tests the main dashboard endpoint:
- Dashboard rendering
- Service integration
- Error handling
- Data aggregation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from app.routes.dashboard import bp as dashboard_bp


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(dashboard_bp)
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
    planner_service = Mock()
    weather_service = Mock()
    
    return {
        'analysis': analysis_service,
        'commute': commute_service,
        'planner': planner_service,
        'weather': weather_service
    }


class TestDashboardRoute:
    """Test dashboard route functionality."""
    
    @patch('app.routes.dashboard.get_services')
    @patch('app.routes.dashboard.render_template')
    def test_dashboard_success(self, mock_render, mock_get_services, client, mock_services):
        """Test successful dashboard rendering."""
        mock_get_services.return_value = mock_services
        
        # Setup mock responses
        mock_services['analysis'].get_analysis_status.return_value = {
            'status': 'success',
            'last_analysis': '2024-01-01T12:00:00',
            'data_freshness': 'fresh',
            'activities_count': 100,
            'route_groups_count': 5,
            'long_rides_count': 10
        }
        
        mock_services['analysis'].get_locations.return_value = (
            {'lat': 40.7128, 'lon': -74.0060, 'name': 'Home'},
            {'lat': 40.7580, 'lon': -73.9855, 'name': 'Work'}
        )
        
        mock_services['weather'].get_weather_summary.return_value = {
            'favorability': 'good',
            'temperature': 72,
            'conditions': 'Clear'
        }
        
        mock_render.return_value = 'Dashboard HTML'
        
        response = client.get('/')
        
        assert response.status_code == 200
        mock_render.assert_called_once()
    
    @patch('app.routes.dashboard.get_services')
    @patch('app.routes.dashboard.render_template')
    def test_dashboard_analysis_error(self, mock_render, mock_get_services, client, mock_services):
        """Test dashboard when analysis service fails."""
        mock_get_services.return_value = mock_services
        
        # Make analysis service raise exception
        mock_services['analysis'].get_analysis_status.side_effect = Exception("Analysis failed")
        
        mock_render.return_value = 'Dashboard HTML'
        
        response = client.get('/dashboard')
        
        # Should still render with error state
        assert response.status_code == 200
        mock_render.assert_called_once()
    
    @patch('app.routes.dashboard.get_services')
    @patch('app.routes.dashboard.render_template')
    def test_dashboard_weather_error(self, mock_render, mock_get_services, client, mock_services):
        """Test dashboard when weather service fails."""
        mock_get_services.return_value = mock_services
        
        mock_services['analysis'].get_analysis_status.return_value = {
            'status': 'success'
        }
        
        mock_services['analysis'].get_locations.return_value = (
            {'lat': 40.7128, 'lon': -74.0060},
            {'lat': 40.7580, 'lon': -73.9855}
        )
        
        # Make weather service raise exception
        mock_services['weather'].get_weather_summary.side_effect = Exception("Weather failed")
        
        mock_render.return_value = 'Dashboard HTML'
        
        response = client.get('/')
        
        # Should still render without weather
        assert response.status_code == 200
        mock_render.assert_called_once()
    
    @patch('app.routes.dashboard.get_services')
    @patch('app.routes.dashboard.render_template')
    def test_dashboard_no_locations(self, mock_render, mock_get_services, client, mock_services):
        """Test dashboard when locations not available."""
        mock_get_services.return_value = mock_services
        
        mock_services['analysis'].get_analysis_status.return_value = {
            'status': 'success'
        }
        
        # No locations available
        mock_services['analysis'].get_locations.return_value = (None, None)
        
        mock_render.return_value = 'Dashboard HTML'
        
        response = client.get('/')
        
        # Should render without location-dependent features
        assert response.status_code == 200
        mock_render.assert_called_once()
    
    @patch('app.routes.dashboard.get_services')
    @patch('app.routes.dashboard.render_template')
    def test_dashboard_with_commute_recommendation(self, mock_render, mock_get_services, client, mock_services):
        """Test dashboard with commute recommendation."""
        mock_get_services.return_value = mock_services
        
        mock_services['analysis'].get_analysis_status.return_value = {
            'status': 'success'
        }
        
        mock_services['analysis'].get_locations.return_value = (
            {'lat': 40.7128, 'lon': -74.0060},
            {'lat': 40.7580, 'lon': -73.9855}
        )
        
        # Mock route groups
        mock_route_group = Mock()
        mock_services['analysis'].get_route_groups.return_value = [mock_route_group]
        
        # Mock commute recommendation
        mock_services['commute'].get_workout_aware_commute.return_value = {
            'status': 'success',
            'direction': 'to_work',
            'route': {
                'name': 'Main Route',
                'distance': 5000,
                'duration': 1200
            }
        }
        
        mock_render.return_value = 'Dashboard HTML'
        
        response = client.get('/')
        
        assert response.status_code == 200
        mock_services['commute'].initialize.assert_called_once()
        mock_render.assert_called_once()
    
    @patch('app.routes.dashboard.get_services')
    def test_dashboard_both_routes(self, mock_get_services, client, mock_services):
        """Test that both / and /dashboard routes work."""
        mock_get_services.return_value = mock_services
        
        mock_services['analysis'].get_analysis_status.return_value = {
            'status': 'success'
        }
        
        with patch('app.routes.dashboard.render_template', return_value='HTML'):
            response1 = client.get('/')
            response2 = client.get('/dashboard')
            
            assert response1.status_code == 200
            assert response2.status_code == 200


class TestGetServices:
    """Test get_services helper function."""
    
    @patch('app.routes.dashboard.Config')
    @patch('app.routes.dashboard.AnalysisService')
    @patch('app.routes.dashboard.CommuteService')
    @patch('app.routes.dashboard.PlannerService')
    @patch('app.routes.dashboard.WeatherService')
    def test_get_services_creates_services(self, mock_weather, mock_planner,
                                          mock_commute, mock_analysis, mock_config_cls, app):
        """Test that get_services creates service instances."""
        from app.routes.dashboard import get_services
        
        # Properly configure the Config mock
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'cache_dir': 'cache',
            'data_dir': 'data',
            'route_naming.sampling_density': 10,
            'route_naming.geocoder_timeout': 10
        }.get(key, default)
        mock_config_cls.return_value = mock_config
        
        with app.app_context():
            services = get_services()
            
            assert 'analysis' in services
            assert 'commute' in services
            assert 'planner' in services
            assert 'weather' in services
            
            mock_config_cls.assert_called_once_with('config/config.yaml')
            mock_analysis.assert_called_once()
            mock_commute.assert_called_once()
            mock_planner.assert_called_once()
            mock_weather.assert_called_once()
    
    @patch('app.routes.dashboard.Config')
    def test_get_services_caches_in_g(self, mock_config_cls, app):
        """Test that services are cached in Flask g object."""
        from app.routes.dashboard import get_services
        from flask import g
        
        # Properly configure the Config mock
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'cache_dir': 'cache',
            'data_dir': 'data',
            'route_naming.sampling_density': 10,
            'route_naming.geocoder_timeout': 10
        }.get(key, default)
        mock_config_cls.return_value = mock_config
        
        with app.app_context():
            # First call creates services
            services1 = get_services()
            
            # Second call returns cached services
            services2 = get_services()
            
            assert services1 is services2
            assert services1 is g.services


# Made with Bob