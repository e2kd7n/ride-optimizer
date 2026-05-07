"""
Shared pytest fixtures for integration tests.

Provides mocked services and test data for API integration testing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


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

@pytest.fixture
def client():
    """Flask test client fixture for UAT tests."""
    from launch import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_weather_data():
    """Mock current weather data for testing."""
    return {
        "location": "Test City",
        "temperature": 22.0,
        "temperature_f": 72.0,
        "temperature_c": 22.0,
        "conditions": "Sunny",
        "wind_speed": 10.0,
        "wind_speed_kph": 16.0,
        "wind_speed_mph": 10.0,
        "wind_direction": "NW",
        "wind_direction_degrees": 315,
        "precipitation_chance": 0.0,
        "precipitation_mm": 0.0,
        "humidity": 60,
        "feels_like": 70.0,
        "feels_like_f": 70.0,
        "ride_score": 9.2,
        "comfort_score": 0.92,
        "cycling_favorability": "favorable",
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def mock_route_data():
    """Mock route information for testing."""
    return {
        "id": "test-route-123",
        "name": "Test Route",
        "distance": 50.0,
        "distance_miles": 31.0,
        "distance_km": 50.0,
        "elevation_gain": 500.0,
        "elevation_gain_meters": 500.0,
        "elevation_gain_feet": 1640.0,
        "coordinates": [(40.7128, -74.0060), (40.7580, -73.9855)],
        "sport_type": "Ride",
        "type": "Ride",
        "uses": 15,
        "is_favorite": False,
        "is_loop": False,
        "created_at": datetime.now().isoformat()
    }


@pytest.fixture
def mock_long_routes():
    """Mock long ride route data for testing."""
    return [
        {
            "id": "route-1",
            "name": "Long Route 1",
            "distance": 100.0,
            "distance_miles": 62.0,
            "distance_km": 100.0,
            "elevation_gain": 800.0,
            "elevation_gain_meters": 800.0,
            "sport_type": "Ride",
            "uses": 8,
            "is_loop": True
        },
        {
            "id": "route-2",
            "name": "Long Route 2",
            "distance": 98.0,
            "distance_miles": 61.0,
            "distance_km": 98.0,
            "elevation_gain": 600.0,
            "elevation_gain_meters": 600.0,
            "sport_type": "Ride",
            "uses": 6,
            "is_loop": True
        },
        {
            "id": "route-3",
            "name": "Long Route 3",
            "distance": 105.0,
            "distance_miles": 65.0,
            "distance_km": 105.0,
            "elevation_gain": 1000.0,
            "elevation_gain_meters": 1000.0,
            "sport_type": "Ride",
            "uses": 10,
            "is_loop": False
        }
    ]


@pytest.fixture
def mock_7day_forecast():
    """Mock 7-day weather forecast for testing."""
    base_date = datetime.now()
    return {
        "location": "Test City",
        "forecast": [
            {
                "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "day_name": (base_date + timedelta(days=i)).strftime("%A"),
                "temp_high": 24.0 + i,
                "temp_high_f": 75.0 + i * 1.8,
                "temp_high_c": 24.0 + i,
                "temp_low": 15.0 + i,
                "temp_low_f": 59.0 + i * 1.8,
                "temp_low_c": 15.0 + i,
                "conditions": "Sunny" if i % 2 == 0 else "Partly Cloudy",
                "precipitation_chance": 0.0 if i % 3 != 0 else 20.0,
                "precipitation_mm": 0.0,
                "wind_speed": 12.0 + i,
                "wind_speed_kph": 19.0 + i * 1.6,
                "wind_speed_mph": 12.0 + i,
                "wind_direction": "NW",
                "wind_direction_degrees": 315,
                "ride_score": 9.5 - (i * 0.2),
                "comfort_score": 0.95 - (i * 0.02),
                "cycling_favorability": "favorable" if i < 3 else "neutral"
            }
            for i in range(7)
        ]
    }


@pytest.fixture
def mock_long_ride_analysis():
    """Mock long ride analysis results for testing."""
    return {
        "distance": 100.0,
        "distance_miles": 62.0,
        "distance_km": 100.0,
        "duration": 300,
        "duration_minutes": 300,
        "duration_hours": 5.0,
        "date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
        "recommendations": [
            {
                "route_id": "route-1",
                "route_name": "Long Route 1",
                "score": 92.5,
                "weather_score": 95.0,
                "variety_score": 88.0,
                "workout_fit_score": 90.0,
                "distance": 100.0,
                "elevation_gain": 800.0,
                "estimated_duration": 300
            },
            {
                "route_id": "route-2",
                "route_name": "Long Route 2",
                "score": 88.0,
                "weather_score": 90.0,
                "variety_score": 85.0,
                "workout_fit_score": 88.0,
                "distance": 98.0,
                "elevation_gain": 600.0,
                "estimated_duration": 290
            }
        ],
        "weather_forecast": {
            "temperature": 22.0,
            "conditions": "Sunny",
            "wind_speed": 10.0,
            "precipitation_chance": 0.0,
            "ride_score": 9.5
        },
        "workout_fit": {
            "training_load": "moderate",
            "recovery_status": "good",
            "recommended_intensity": "endurance",
            "fit_score": 90.0
        },
        "route_variety": {
            "new_routes": 2,
            "repeated_routes": 1,
            "variety_score": 88.0,
            "exploration_opportunities": ["New scenic loop", "Alternative descent"]
        }
    }


# Made with Bob
