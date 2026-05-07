"""
Unit tests for PlannerService.

Tests long ride planning functionality:
- Ride recommendations with weather scoring
- Location-based ride discovery
- Distance filtering
- Multi-day forecasting
- Ride details retrieval
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date, timedelta

from app.services.planner_service import PlannerService
from src.long_ride_analyzer import LongRide
from src.config import Config
from app import create_app


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app('testing')
    app.config['TESTING'] = True
    return app


@pytest.fixture
def mock_config():
    """Create a mock Config object."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'cache_dir': '/tmp/test_cache',
        'data_dir': '/tmp/test_data'
    }.get(key, default))
    return config


@pytest.fixture
def mock_long_ride():
    """Create a mock LongRide object."""
    ride = Mock(spec=LongRide)
    ride.activity_id = 12345
    ride.name = "Weekend Century"
    ride.distance = 160000  # meters
    ride.distance_km = 160.0
    ride.duration_hours = 5.5
    ride.elevation_gain = 1500
    ride.average_speed = 8.08  # m/s
    ride.start_location = (40.7128, -74.0060)
    ride.end_location = (40.7128, -74.0060)
    ride.is_loop = True
    ride.type = "loop"
    ride.uses = 3
    ride.coordinates = [(40.7128, -74.0060), (40.7580, -73.9855)]
    ride.activity_ids = [12345, 12346, 12347]
    ride.activity_dates = ["2024-01-15", "2024-02-20", "2024-03-10"]
    return ride


@pytest.fixture
def mock_short_ride():
    """Create a mock short ride (30 miles)."""
    ride = Mock(spec=LongRide)
    ride.activity_id = 67890
    ride.name = "Quick Loop"
    ride.distance = 48280  # 30 miles in meters
    ride.distance_km = 48.28
    ride.duration_hours = 2.0
    ride.elevation_gain = 500
    ride.average_speed = 6.71  # m/s
    ride.start_location = (40.7580, -73.9855)
    ride.end_location = (40.7580, -73.9855)
    ride.is_loop = True
    ride.type = "loop"
    ride.uses = 10
    ride.coordinates = [(40.7580, -73.9855), (40.7128, -74.0060)]
    ride.activity_ids = [67890]
    ride.activity_dates = ["2024-03-01"]
    return ride


@pytest.fixture
def planner_service(mock_config):
    """Create a PlannerService instance with mocked weather service."""
    with patch('app.services.planner_service.WeatherService') as mock_weather_class:
        # Create a mock weather service instance
        mock_weather_instance = Mock()
        
        # Mock weather snapshot with proper numeric values
        mock_snapshot = Mock()
        mock_snapshot.temperature_f = 68.0
        mock_snapshot.conditions = 'Clear'
        mock_snapshot.wind_speed_mph = 5.0
        mock_snapshot.wind_direction = 'N'
        mock_snapshot.precipitation_in = 0.0
        mock_snapshot.humidity_percent = 50.0
        mock_snapshot.feels_like_f = 68.0
        mock_snapshot.timestamp = datetime.now()
        
        # Configure get_weather_snapshot to return mock snapshot
        mock_weather_instance.get_weather_snapshot.return_value = mock_snapshot
        
        # Make the WeatherService class return our configured instance
        mock_weather_class.return_value = mock_weather_instance
        
        service = PlannerService(mock_config)
        return service


@pytest.fixture
def initialized_service(planner_service, mock_long_ride, mock_short_ride):
    """Create an initialized PlannerService with test data."""
    planner_service.initialize([mock_long_ride, mock_short_ride])
    return planner_service


class TestPlannerServiceInitialization:
    """Test service initialization."""
    
    def test_init_creates_service(self, mock_config):
        """Test that service can be created."""
        with patch('app.services.planner_service.WeatherService'):
            service = PlannerService(mock_config)
            assert service is not None
            assert service.config == mock_config
            assert service._long_rides is None
    
    def test_initialize_sets_data(self, planner_service, mock_long_ride):
        """Test that initialize sets ride data."""
        planner_service.initialize([mock_long_ride])
        assert planner_service._long_rides == [mock_long_ride]


class TestGetRecommendations:
    """Test get_recommendations functionality."""
    
    def test_get_recommendations_uninitialized(self, planner_service):
        """Test getting recommendations when service not initialized."""
        result = planner_service.get_recommendations()
        assert result['status'] == 'error'
        assert 'not initialized' in result['message']
        assert result['recommendations'] == []
    
    def test_get_recommendations_success(self, initialized_service):
        """Test getting recommendations successfully."""
        result = initialized_service.get_recommendations(forecast_days=3)
        assert result['status'] == 'success'
        assert result['forecast_days'] == 3
        assert 'recommendations' in result
        assert 'best_day' in result
        assert 'total_rides' in result
        # Default distance range (30-100 miles) filters out the short ride
        assert result['total_rides'] >= 1
    
    def test_get_recommendations_with_distance_filter(self, initialized_service):
        """Test filtering recommendations by distance."""
        # Filter for rides 50-200 miles (should include century, exclude short ride)
        result = initialized_service.get_recommendations(
            min_distance=50.0,
            max_distance=200.0
        )
        assert result['status'] == 'success'
        assert result['total_rides'] == 1  # Only the century ride
        assert result['distance_range']['min'] == 50.0
        assert result['distance_range']['max'] == 200.0
    
    def test_get_recommendations_no_rides_in_range(self, initialized_service):
        """Test when no rides match distance criteria."""
        result = initialized_service.get_recommendations(
            min_distance=200.0,
            max_distance=300.0
        )
        assert result['status'] == 'success'
        assert 'No rides found' in result['message']
        assert result['total_rides'] == 0
        assert result['recommendations'] == []
    
    def test_get_recommendations_with_location(self, initialized_service):
        """Test recommendations with location preference."""
        result = initialized_service.get_recommendations(
            location=(40.7128, -74.0060),
            forecast_days=2
        )
        assert result['status'] == 'success'
        assert len(result['recommendations']) <= 2
    
    def test_get_recommendations_multiple_days(self, initialized_service):
        """Test multi-day recommendations."""
        result = initialized_service.get_recommendations(forecast_days=7)
        assert result['status'] == 'success'
        assert len(result['recommendations']) <= 7
        
        # Check each day has required fields
        for day_rec in result['recommendations']:
            assert 'date' in day_rec
            assert 'day_name' in day_rec
            assert 'rides' in day_rec
            assert 'best_ride' in day_rec
            assert 'weather_summary' in day_rec
    
    def test_get_recommendations_best_day_selection(self, initialized_service):
        """Test that best day is correctly identified."""
        result = initialized_service.get_recommendations(forecast_days=3)
        assert result['status'] == 'success'
        
        if result['recommendations']:
            assert result['best_day'] is not None
            # Best day should be one of the recommendation dates
            rec_dates = [r['date'] for r in result['recommendations']]
            assert result['best_day'] in rec_dates
    
    def test_get_recommendations_error_handling(self, initialized_service):
        """Test error handling in recommendations."""
        # Force an error by making _long_rides raise exception
        initialized_service._long_rides = Mock()
        initialized_service._long_rides.__iter__ = Mock(side_effect=Exception("Test error"))
        
        result = initialized_service.get_recommendations()
        assert result['status'] == 'error'
        assert 'Failed to generate recommendations' in result['message']


class TestGetRidesNearLocation:
    """Test get_rides_near_location functionality."""
    
    def test_get_rides_near_location_uninitialized(self, planner_service):
        """Test finding rides when service not initialized."""
        result = planner_service.get_rides_near_location(40.7128, -74.0060)
        assert result['status'] == 'error'
        assert 'not initialized' in result['message']
        assert result['rides'] == []
        assert result['count'] == 0
    
    def test_get_rides_near_location_success(self, initialized_service):
        """Test finding rides near a location."""
        result = initialized_service.get_rides_near_location(
            40.7128, -74.0060,
            radius_miles=10.0
        )
        assert result['status'] == 'success'
        assert result['location'] == [40.7128, -74.0060]
        assert result['radius_miles'] == 10.0
        assert 'rides' in result
        assert 'count' in result
    
    def test_get_rides_near_location_with_limit(self, initialized_service):
        """Test limiting number of results."""
        result = initialized_service.get_rides_near_location(
            40.7128, -74.0060,
            radius_miles=50.0,
            limit=1
        )
        assert result['status'] == 'success'
        assert len(result['rides']) <= 1
    
    def test_get_rides_near_location_sorted_by_distance(self, initialized_service):
        """Test that results are sorted by distance."""
        result = initialized_service.get_rides_near_location(
            40.7128, -74.0060,
            radius_miles=50.0
        )
        
        if len(result['rides']) > 1:
            distances = [r['distance_to_location'] for r in result['rides']]
            assert distances == sorted(distances)
    
    def test_get_rides_near_location_includes_details(self, initialized_service):
        """Test that ride details are included."""
        result = initialized_service.get_rides_near_location(
            40.7128, -74.0060,
            radius_miles=50.0
        )
        
        if result['rides']:
            ride = result['rides'][0]
            assert 'ride_id' in ride
            assert 'name' in ride
            assert 'distance' in ride
            assert 'duration' in ride
            assert 'elevation' in ride
            assert 'distance_to_location' in ride
            assert 'start_location' in ride
            assert 'is_loop' in ride
            assert 'uses' in ride
            assert 'type' in ride
    
    def test_get_rides_near_location_error_handling(self, initialized_service):
        """Test error handling in location search."""
        # Force an error
        initialized_service._long_rides = Mock()
        initialized_service._long_rides.__iter__ = Mock(side_effect=Exception("Test error"))
        
        result = initialized_service.get_rides_near_location(40.7128, -74.0060)
        assert result['status'] == 'error'
        assert 'Failed to find rides' in result['message']


class TestGetRideDetails:
    """Test get_ride_details functionality."""
    
    def test_get_ride_details_uninitialized(self, planner_service):
        """Test getting details when service not initialized."""
        result = planner_service.get_ride_details(12345)
        assert result['status'] == 'error'
        assert 'not initialized' in result['message']
    
    def test_get_ride_details_success(self, initialized_service):
        """Test getting ride details successfully."""
        result = initialized_service.get_ride_details(12345)
        assert result['status'] == 'success'
        assert 'ride' in result
        
        ride = result['ride']
        assert ride['ride_id'] == 12345
        assert ride['name'] == "Weekend Century"
        assert ride['distance'] == 160.0
        assert ride['duration'] == 5.5
        assert ride['elevation'] == 1500
        assert 'average_speed' in ride
        assert 'start_location' in ride
        assert 'end_location' in ride
        assert 'is_loop' in ride
        assert 'type' in ride
        assert 'uses' in ride
        assert 'coordinates' in ride
        assert 'activity_ids' in ride
        assert 'activity_dates' in ride
    
    def test_get_ride_details_not_found(self, initialized_service):
        """Test getting details for non-existent ride."""
        result = initialized_service.get_ride_details(99999)
        assert result['status'] == 'error'
        assert 'not found' in result['message']


class TestRideScoring:
    """Test ride scoring functionality."""
    
    def test_score_rides_for_day(self, initialized_service):
        """Test scoring rides for a specific day."""
        target_date = date.today()
        rides = initialized_service._long_rides
        
        scored_rides = initialized_service._score_rides_for_day(
            rides, target_date, None
        )
        
        assert len(scored_rides) == 2
        
        # Check each ride has required scoring fields
        for ride in scored_rides:
            assert 'score' in ride
            assert 'weather_score' in ride
            assert 'variety_score' in ride
            assert 'location_score' in ride
            assert 0 <= ride['score'] <= 1
            assert 0 <= ride['weather_score'] <= 1
            assert 0 <= ride['variety_score'] <= 1
            assert 0 <= ride['location_score'] <= 1
    
    def test_score_rides_variety_scoring(self, initialized_service):
        """Test that variety score favors less-used routes."""
        target_date = date.today()
        rides = initialized_service._long_rides
        
        scored_rides = initialized_service._score_rides_for_day(
            rides, target_date, None
        )
        
        # Find the rides by their uses count
        century_ride = next(r for r in scored_rides if r['uses'] == 3)
        short_ride = next(r for r in scored_rides if r['uses'] == 10)
        
        # Less-used ride should have higher variety score
        assert century_ride['variety_score'] > short_ride['variety_score']
    
    def test_score_rides_with_location_preference(self, initialized_service):
        """Test location scoring when location specified."""
        target_date = date.today()
        rides = initialized_service._long_rides
        location = (40.7128, -74.0060)
        
        scored_rides = initialized_service._score_rides_for_day(
            rides, target_date, location
        )
        
        # All rides should have location scores
        for ride in scored_rides:
            assert 'location_score' in ride
            assert 0 <= ride['location_score'] <= 1
    
    def test_score_rides_sorted_by_score(self, initialized_service):
        """Test that scored rides are sorted by total score."""
        target_date = date.today()
        rides = initialized_service._long_rides
        
        scored_rides = initialized_service._score_rides_for_day(
            rides, target_date, None
        )
        
        scores = [r['score'] for r in scored_rides]
        assert scores == sorted(scores, reverse=True)


class TestWeatherIntegration:
    """Test weather-related functionality."""
    
    def test_get_weather_for_ride(self, app, initialized_service, mock_long_ride):
        """Test getting weather for a ride."""
        # Need Flask app context for WeatherSnapshot
        with app.app_context():
            target_date = date.today()
            weather = initialized_service._get_weather_for_ride(mock_long_ride, target_date)
            
            assert weather is not None
            assert 'temperature_c' in weather
            assert 'conditions' in weather
            assert 'wind_speed_kph' in weather
            assert 'wind_direction_deg' in weather
            assert 'precipitation_mm' in weather
    
    def test_calculate_weather_score(self, initialized_service):
        """Test weather score calculation."""
        weather = {
            'temperature': 70.0,
            'conditions': 'Clear',
            'wind_speed': 5.0,
            'precipitation': 0.0
        }
        
        score = initialized_service._calculate_weather_score(weather)
        assert 0 <= score <= 1
    
    def test_get_weather_summary(self, initialized_service):
        """Test weather summary generation."""
        weather = {
            'temperature': 72.0,
            'conditions': 'Partly Cloudy',
            'wind_speed': 8.0
        }
        
        summary = initialized_service._get_weather_summary(weather)
        assert '72' in summary
        assert 'Partly Cloudy' in summary
        assert '8' in summary
    
    def test_get_weather_summary_no_data(self, initialized_service):
        """Test weather summary with no data."""
        summary = initialized_service._get_weather_summary(None)
        assert 'unavailable' in summary.lower()


class TestDistanceConversions:
    """Test distance unit conversions."""
    
    def test_miles_to_meters_conversion(self, initialized_service):
        """Test that distance filtering uses correct conversions."""
        # 30 miles = 48,280 meters
        result = initialized_service.get_recommendations(
            min_distance=29.0,
            max_distance=31.0
        )
        
        assert result['status'] == 'success'
        # Should find the 30-mile ride
        assert result['total_rides'] >= 1
    
    def test_distance_range_in_response(self, initialized_service):
        """Test that distance range is included in response."""
        result = initialized_service.get_recommendations(
            min_distance=40.0,
            max_distance=120.0
        )
        
        assert 'distance_range' in result
        assert result['distance_range']['min'] == 40.0
        assert result['distance_range']['max'] == 120.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_rides_list(self, planner_service):
        """Test with no rides."""
        planner_service.initialize([])
        result = planner_service.get_recommendations()
        
        # Empty list returns error because service needs data
        assert result['status'] == 'error'
        assert 'not initialized' in result['message'].lower()
    
    def test_single_day_forecast(self, initialized_service):
        """Test with single day forecast."""
        result = initialized_service.get_recommendations(forecast_days=1)
        assert result['status'] == 'success'
        assert len(result['recommendations']) <= 1
    
    def test_extended_forecast(self, initialized_service):
        """Test with extended forecast period."""
        result = initialized_service.get_recommendations(forecast_days=14)
        assert result['status'] == 'success'
        assert len(result['recommendations']) <= 14
    
    def test_zero_radius_search(self, initialized_service):
        """Test location search with very small radius."""
        result = initialized_service.get_rides_near_location(
            40.7128, -74.0060,
            radius_miles=0.1
        )
        assert result['status'] == 'success'
        # May or may not find rides depending on exact locations


# Made with Bob