"""
Shared pytest fixtures for integration tests.

Provides mocked services and test data for API integration testing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_config():
    """Mock Config with test data."""
    config = Mock()
    
    # Mock location config
    config.get.side_effect = lambda key, default=None: {
        'location.home.latitude': 40.7128,
        'location.home.longitude': -74.0060,
        'location.work.latitude': 40.7589,
        'location.work.longitude': -73.9851,
    }.get(key, default)
    
    return config


@pytest.fixture
def mock_analysis_service():
    """Mock AnalysisService with test data."""
    service = Mock()
    
    # Mock get_analysis_status
    service.get_analysis_status.return_value = {
        'has_data': True,
        'last_analysis': datetime.now().isoformat(),
        'activities_count': 150,
        'route_groups_count': 12,
        'long_rides_count': 8,
        'data_age_hours': 2.5,
        'is_stale': False
    }
    
    # Mock get_route_groups
    service.get_route_groups.return_value = [
        {
            'name': 'Morning Commute',
            'routes_count': 45,
            'distance': 10.5,
            'uses': 45
        },
        {
            'name': 'Evening Commute',
            'routes_count': 42,
            'distance': 10.8,
            'uses': 42
        }
    ]
    
    # Mock get_long_rides
    service.get_long_rides.return_value = [
        {
            'name': 'Weekend Loop',
            'distance': 50.2,
            'elevation_gain': 1200,
            'uses': 8
        }
    ]
    
    return service


@pytest.fixture
def mock_weather_service():
    """Mock WeatherService with test data."""
    service = Mock()
    
    # Mock get_current_weather
    service.get_current_weather.return_value = {
        'temperature': 72,
        'feels_like': 70,
        'humidity': 60,
        'wind_speed': 5,
        'wind_direction': 'NW',
        'description': 'Partly cloudy',
        'comfort_score': 85,
        'cycling_favorability': 'excellent'
    }
    
    # Mock get_forecast
    service.get_forecast.return_value = [
        {
            'time': datetime.now().isoformat(),
            'temperature': 73,
            'description': 'Sunny',
            'comfort_score': 90
        }
    ]
    
    return service


@pytest.fixture
def mock_commute_service():
    """Mock CommuteService with test data."""
    service = Mock()
    
    # Mock get_next_commute
    service.get_next_commute.return_value = {
        'status': 'success',
        'direction': 'to_work',
        'recommended_route': {
            'name': 'Morning Commute',
            'distance': 10.5,
            'score': 92
        },
        'weather': {
            'temperature': 72,
            'comfort_score': 85
        },
        'alternatives': [
            {
                'name': 'Scenic Route',
                'distance': 12.3,
                'score': 88
            }
        ]
    }
    
    return service


@pytest.fixture
def mock_route_library_service():
    """Mock RouteLibraryService with test data."""
    service = Mock()
    
    # Mock get_all_routes
    service.get_all_routes.return_value = {
        'status': 'success',
        'routes': [
            {
                'id': 1,
                'name': 'Morning Commute',
                'distance': 10.5,
                'elevation_gain': 500,
                'sport_type': 'Ride',
                'is_favorite': True,
                'uses': 45
            },
            {
                'id': 2,
                'name': 'Evening Commute',
                'distance': 10.8,
                'elevation_gain': 520,
                'sport_type': 'Ride',
                'is_favorite': True,
                'uses': 42
            }
        ],
        'total_count': 2,
        'updated_at': datetime.now().isoformat()
    }
    
    return service


@pytest.fixture
def mock_planner_service():
    """Mock PlannerService with test data."""
    service = Mock()
    
    # Mock get_plan
    service.get_plan.return_value = {
        'status': 'success',
        'plan': {
            'week': 'Week 1',
            'workouts': []
        }
    }
    
    return service


@pytest.fixture
def mock_services(monkeypatch, mock_config, mock_analysis_service, mock_weather_service,
                  mock_commute_service, mock_route_library_service, mock_planner_service):
    """
    Patch all services in launch.py with mocked versions.
    
    This fixture ensures the API can initialize without requiring Strava authentication.
    """
    # Patch the config
    monkeypatch.setattr('launch.config', mock_config)
    
    # Patch the initialize_services function to use mocked services
    def mock_initialize_services():
        import launch
        launch._services_initialized = True
        launch._analysis_service = mock_analysis_service
        launch._weather_service = mock_weather_service
        launch._commute_service = mock_commute_service
        launch._route_library_service = mock_route_library_service
        launch._planner_service = mock_planner_service
    
    # Apply the patch
    monkeypatch.setattr('launch.initialize_services', mock_initialize_services)
    
    return {
        'analysis': mock_analysis_service,
        'weather': mock_weather_service,
        'commute': mock_commute_service,
        'route_library': mock_route_library_service,
        'planner': mock_planner_service
    }

# Made with Bob
