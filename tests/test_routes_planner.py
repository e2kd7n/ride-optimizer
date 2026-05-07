"""
Unit tests for planner routes (app/routes/planner.py).

Tests the long ride planner blueprint endpoints including:
- Main planner view with recommendations
- Route analysis and scoring
- Route detail views
- API endpoints for recommendations
- Calendar view integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
from flask import g

from app import create_app
from src.long_ride_analyzer import LongRide


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_long_ride():
    """Create a mock long ride."""
    ride = Mock(spec=LongRide)
    ride.activity_id = 12345
    ride.name = "Epic Mountain Loop"
    ride.distance = 80467  # 50 miles in meters
    ride.distance_km = 80.467
    ride.duration_hours = 3.5
    ride.elevation_gain = 1200
    ride.average_speed = 6.39  # m/s
    ride.start_location = (40.7128, -74.0060)
    ride.end_location = (40.7128, -74.0060)
    ride.is_loop = True
    ride.type = "loop"
    ride.uses = 5
    ride.coordinates = [(40.7128, -74.0060), (40.7580, -73.9855)]
    ride.activity_ids = [12345, 12346, 12347, 12348, 12349]
    ride.activity_dates = ["2024-01-15", "2024-02-20", "2024-03-10", "2024-04-05", "2024-05-01"]
    return ride


@pytest.fixture
def mock_services():
    """Create mock service instances."""
    with patch('app.routes.planner.AnalysisService') as mock_analysis, \
         patch('app.routes.planner.PlannerService') as mock_planner, \
         patch('app.routes.planner.TrainerRoadService') as mock_trainerroad, \
         patch('app.routes.planner.Config'):
        
        # Configure analysis service
        analysis_instance = Mock()
        mock_analysis.return_value = analysis_instance
        
        # Configure planner service
        planner_instance = Mock()
        mock_planner.return_value = planner_instance
        
        # Configure trainerroad service
        trainerroad_instance = Mock()
        mock_trainerroad.return_value = trainerroad_instance
        
        yield {
            'analysis': analysis_instance,
            'planner': planner_instance,
            'trainerroad': trainerroad_instance
        }


class TestPlannerIndex:
    """Test the main planner index route."""
    
    def test_index_renders_template(self, client, mock_services, mock_long_ride):
        """Test that index route renders the planner template."""
        # Configure mocks
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['planner'].get_recommendations.return_value = {
            'status': 'success',
            'best_day': 'Monday',
            'total_rides': 10,
            'recommendations': []
        }
        mock_services['trainerroad'].get_upcoming_workouts.return_value = []
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Planner</html>') as mock_render:
            response = client.get('/planner/')
        
        assert response.status_code == 200
        mock_render.assert_called_once()
        assert mock_render.call_args[0][0] == 'planner/index.html'
    
    def test_index_with_query_parameters(self, client, mock_services, mock_long_ride):
        """Test index with custom filter parameters."""
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['planner'].get_recommendations.return_value = {
            'status': 'success',
            'best_day': 'Saturday',
            'total_rides': 5,
            'recommendations': []
        }
        mock_services['trainerroad'].get_upcoming_workouts.return_value = []
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Planner</html>'):
            response = client.get('/planner/?days=5&min_distance=40&max_distance=80')
        
        assert response.status_code == 200
        # Verify planner service was called with correct parameters
        mock_services['planner'].get_recommendations.assert_called_once()
        call_kwargs = mock_services['planner'].get_recommendations.call_args[1]
        assert call_kwargs['forecast_days'] == 5
        assert call_kwargs['min_distance'] == 40.0
        assert call_kwargs['max_distance'] == 80.0
    
    def test_index_with_recommendations(self, client, mock_services, mock_long_ride):
        """Test index displays recommendations correctly."""
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['planner'].get_recommendations.return_value = {
            'status': 'success',
            'best_day': 'Saturday',
            'total_rides': 15,
            'recommendations': [
                {
                    'date': '2024-06-01',
                    'day_name': 'Saturday',
                    'rides': [
                        {
                            'ride_id': 12345,
                            'name': 'Epic Mountain Loop',
                            'distance': 80467,
                            'duration': 12600,
                            'elevation': 1200,
                            'score': 0.95,
                            'weather_score': 0.9,
                            'variety_score': 0.8,
                            'is_loop': True,
                            'weather': {'temperature': 72, 'conditions': 'Clear'}
                        }
                    ],
                    'best_ride': {
                        'name': 'Epic Mountain Loop',
                        'distance': 80467,
                        'duration': 12600,
                        'elevation': 1200,
                        'score': 0.95,
                        'weather': {'temperature': 72, 'conditions': 'Clear'}
                    },
                    'weather_summary': 'Perfect riding weather'
                }
            ]
        }
        mock_services['trainerroad'].get_upcoming_workouts.return_value = []
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Recommendations</html>'):
            response = client.get('/planner/')
        
        assert response.status_code == 200
    
    def test_index_no_long_rides(self, client, mock_services):
        """Test index when no long rides are available."""
        mock_services['analysis'].get_long_rides.return_value = []
        mock_services['trainerroad'].get_upcoming_workouts.return_value = []
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>No rides</html>'):
            response = client.get('/planner/')
        
        assert response.status_code == 200
        # Should not call planner service if no rides
        mock_services['planner'].initialize.assert_not_called()
    
    def test_index_with_workout_schedule(self, client, mock_services, mock_long_ride):
        """Test index includes TrainerRoad workout schedule."""
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['planner'].get_recommendations.return_value = {
            'status': 'success',
            'best_day': 'Sunday',
            'total_rides': 8,
            'recommendations': []
        }
        
        # Mock workout data
        mock_workout = Mock()
        mock_workout.date = date(2024, 6, 1)
        mock_workout.name = "Sweet Spot Intervals"
        mock_workout.duration_minutes = 60
        mock_workout.tss = 75
        mock_workout.workout_type = "Intervals"
        
        mock_services['trainerroad'].get_upcoming_workouts.return_value = [mock_workout]
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Workouts</html>'):
            response = client.get('/planner/')
        
        assert response.status_code == 200
        mock_services['trainerroad'].get_upcoming_workouts.assert_called_once_with(days=7)
    
    def test_index_handles_service_errors(self, client, mock_services):
        """Test index handles service errors gracefully."""
        mock_services['analysis'].get_long_rides.side_effect = Exception("Service error")
        mock_services['trainerroad'].get_upcoming_workouts.return_value = []
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Error</html>'):
            response = client.get('/planner/')
        
        # Should still return 200 with empty recommendations
        assert response.status_code == 200
    
    def test_index_handles_trainerroad_errors(self, client, mock_services, mock_long_ride):
        """Test index handles TrainerRoad service errors gracefully."""
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['planner'].get_recommendations.return_value = {
            'status': 'success',
            'best_day': 'Monday',
            'total_rides': 10,
            'recommendations': []
        }
        mock_services['trainerroad'].get_upcoming_workouts.side_effect = Exception("TrainerRoad API error")
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>No workouts</html>'):
            response = client.get('/planner/')
        
        # Should still return 200 without workout schedule
        assert response.status_code == 200


class TestPlannerAnalyze:
    """Test the planner analyze endpoint."""
    
    def test_analyze_requires_post(self, client):
        """Test that analyze endpoint requires POST method."""
        response = client.get('/planner/analyze')
        assert response.status_code == 405  # Method Not Allowed
    
    def test_analyze_with_valid_data(self, client, mock_services, mock_long_ride):
        """Test analyze endpoint with valid request data."""
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['planner'].get_recommendations.return_value = {
            'status': 'success',
            'recommendations': []
        }
        
        response = client.post('/planner/analyze', json={
            'days': 5,
            'min_distance': 40,
            'max_distance': 80
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None


class TestRouteDetail:
    """Test the route detail endpoint."""
    
    def test_route_detail_valid_id(self, client, mock_services, mock_long_ride):
        """Test route detail with valid route ID."""
        # Ensure mock has last_used attribute
        mock_long_ride.last_used = datetime(2024, 6, 15, 10, 0, 0)
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Route Detail</html>'):
            response = client.get('/planner/route/12345')
        
        assert response.status_code == 200
    
    def test_route_detail_invalid_id(self, client, mock_services, mock_long_ride):
        """Test route detail with invalid route ID."""
        mock_long_ride.last_used = datetime(2024, 6, 15, 10, 0, 0)
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Not Found</html>'):
            response = client.get('/planner/route/99999')
            assert response.status_code == 404
        assert response.status_code in [200, 404]


class TestApiRecommendations:
    """Test the API recommendations endpoint."""
    
    def test_api_recommendations_returns_json(self, client, mock_services, mock_long_ride):
        """Test API endpoint returns JSON recommendations."""
        # API endpoint doesn't use services - it returns TODO response
        response = client.get('/planner/api/recommendations')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = response.get_json()
        # API returns recommendations, forecast_days, distance_range, last_updated (no status field)
        assert 'recommendations' in data
        assert 'forecast_days' in data
        assert 'distance_range' in data
        assert 'last_updated' in data
    
    def test_api_recommendations_with_parameters(self, client, mock_services, mock_long_ride):
        """Test API endpoint with query parameters."""
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['planner'].get_recommendations.return_value = {
            'status': 'success',
            'recommendations': []
        }
        
        response = client.get('/planner/api/recommendations?days=3&min_distance=50')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None


class TestCalendar:
    """Test the calendar view endpoint."""
    
    def test_calendar_renders(self, client, mock_services, mock_long_ride):
        """Test calendar view renders successfully."""
        # Ensure mock has last_used attribute
        mock_long_ride.last_used = datetime(2024, 6, 15, 10, 0, 0)
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['trainerroad'].get_upcoming_workouts.return_value = []
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Calendar</html>'):
            response = client.get('/planner/calendar')
        
        assert response.status_code == 200
    
    def test_calendar_with_date_range(self, client, mock_services, mock_long_ride):
        """Test calendar with custom date range."""
        # Set last_used to June 2024
        mock_long_ride.last_used = datetime(2024, 6, 15, 10, 0, 0)
        mock_services['analysis'].get_long_rides.return_value = [mock_long_ride]
        mock_services['trainerroad'].get_upcoming_workouts.return_value = []
        
        with patch('app.routes.planner.get_services', return_value=mock_services), \
             patch('app.routes.planner.render_template', return_value='<html>Calendar June</html>'):
            response = client.get('/planner/calendar?start=2024-06-01&end=2024-06-30')
        
        assert response.status_code == 200


class TestGetServices:
    """Test the get_services helper function."""
    
    def test_get_services_creates_instances(self, app, mock_services):
        """Test that get_services creates service instances."""
        with app.app_context():
            with app.test_request_context():
                from app.routes.planner import get_services
                
                services = get_services()
                
                assert services is not None
                assert 'analysis' in services
                assert 'planner' in services
                assert 'trainerroad' in services
    
    def test_get_services_caches_in_g(self, app, mock_services):
        """Test that get_services caches instances in g."""
        with app.app_context():
            with app.test_request_context():
                from app.routes.planner import get_services
                
                services1 = get_services()
                services2 = get_services()
                
                # Should return same instance
                assert services1 is services2

# Made with Bob
