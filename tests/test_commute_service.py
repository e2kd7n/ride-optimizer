"""
Unit tests for CommuteService.

Tests cover:
- Service initialization
- Next commute recommendations
- All commute options retrieval
- Departure window calculations
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, time, timezone

from app.services.commute_service import CommuteService
from src.next_commute_recommender import CommuteRecommendation
from src.route_analyzer import RouteGroup, Route
from src.location_finder import Location
from src.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'commute.morning_window_start': '07:00',
        'commute.morning_window_end': '09:00',
        'commute.evening_window_start': '15:00',
        'commute.evening_window_end': '18:00'
    }.get(key, default))
    return config


@pytest.fixture
def mock_route():
    """Create a mock route."""
    route = Mock(spec=Route)
    route.distance = 10.5
    route.duration = 1800  # 30 minutes
    route.elevation_gain = 150.0
    return route


@pytest.fixture
def mock_route_group(mock_route):
    """Create a mock route group."""
    group = Mock(spec=RouteGroup)
    group.id = "route_123"
    group.name = "Main Commute Route"
    group.representative_route = mock_route
    group.frequency = 25
    group.is_plus_route = False
    return group


@pytest.fixture
def mock_location():
    """Create mock locations."""
    home = Location(name="Home", lat=40.7128, lon=-74.0060, activity_count=10)
    work = Location(name="Work", lat=40.7589, lon=-73.9851, activity_count=10)
    return home, work


@pytest.fixture
def commute_service(mock_config):
    """Create a CommuteService instance."""
    return CommuteService(mock_config)


@pytest.mark.unit
class TestCommuteServiceInitialization:
    """Test CommuteService initialization."""
    
    def test_init(self, mock_config):
        """Test service initialization."""
        service = CommuteService(mock_config)
        
        assert service.config == mock_config
        assert service._recommender is None
    
    @patch('app.services.commute_service.NextCommuteRecommender')
    def test_initialize_with_route_data(self, mock_recommender_class, 
                                       commute_service, mock_route_group, 
                                       mock_location):
        """Test initializing recommender with route data."""
        home, work = mock_location
        route_groups = [mock_route_group]
        
        commute_service.initialize(
            route_groups=route_groups,
            home_location=home,
            work_location=work,
            enable_weather=True
        )
        
        # Verify NextCommuteRecommender was created
        mock_recommender_class.assert_called_once_with(
            route_groups=route_groups,
            config=commute_service.config,
            home_location=(home.lat, home.lon),
            work_location=(work.lat, work.lon),
            enable_weather=True
        )
        
        assert commute_service._recommender is not None
    
    @patch('app.services.commute_service.NextCommuteRecommender')
    def test_initialize_without_weather(self, mock_recommender_class,
                                       commute_service, mock_route_group,
                                       mock_location):
        """Test initializing without weather integration."""
        home, work = mock_location
        route_groups = [mock_route_group]
        
        commute_service.initialize(
            route_groups=route_groups,
            home_location=home,
            work_location=work,
            enable_weather=False
        )
        
        # Verify weather was disabled
        call_kwargs = mock_recommender_class.call_args[1]
        assert call_kwargs['enable_weather'] is False


@pytest.mark.unit
class TestGetNextCommute:
    """Test getting next commute recommendations."""
    
    def test_get_next_commute_not_initialized(self, commute_service):
        """Test getting recommendation when service not initialized."""
        result = commute_service.get_next_commute()
        
        assert result['status'] == 'error'
        assert 'not initialized' in result['message'].lower()
        assert result['direction'] is None
        assert result['route'] is None
    
    def test_get_next_commute_success(self, commute_service, mock_route_group):
        """Test successful commute recommendation."""
        # Setup mock recommender
        mock_rec = Mock(spec=CommuteRecommendation)
        mock_rec.direction = 'to_work'
        mock_rec.time_window = 'morning'
        mock_rec.route_group = mock_route_group
        mock_rec.score = 0.85
        mock_rec.breakdown = {
            'time': 0.9,
            'distance': 0.8,
            'safety': 0.85,
            'weather': 0.9
        }
        mock_rec.is_today = True
        mock_rec.window_start = time(7, 0)
        mock_rec.window_end = time(9, 0)
        mock_rec.forecast_weather = {
            'temperature': 72.0,
            'conditions': 'Clear',
            'wind_speed': 5.0
        }
        
        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendation.return_value = mock_rec
        
        result = commute_service.get_next_commute()
        
        assert result['status'] == 'success'
        assert result['direction'] == 'to_work'
        assert result['time_window'] == 'morning'
        assert result['route']['id'] == 'route_123'
        assert result['route']['name'] == 'Main Commute Route'
        assert result['score'] == 0.85
        assert result['is_today'] is True
        assert 'weather' in result
        assert result['weather']['temperature'] == 72.0
    
    def test_get_next_commute_with_direction_override(self, commute_service, 
                                                      mock_route_group):
        """Test getting recommendation with direction override."""
        mock_rec = Mock(spec=CommuteRecommendation)
        mock_rec.direction = 'to_home'
        mock_rec.time_window = 'evening'
        mock_rec.route_group = mock_route_group
        mock_rec.score = 0.75
        mock_rec.breakdown = {}
        mock_rec.is_today = True
        mock_rec.window_start = time(15, 0)
        mock_rec.window_end = time(18, 0)
        mock_rec.forecast_weather = None
        
        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendation.return_value = mock_rec
        
        result = commute_service.get_next_commute(direction='to_home')
        
        commute_service._recommender.get_next_commute_recommendation.assert_called_once_with(
            direction='to_home'
        )
        assert result['direction'] == 'to_home'
    
    def test_get_next_commute_no_suitable_route(self, commute_service):
        """Test when no suitable route is found."""
        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendation.return_value = None
        
        result = commute_service.get_next_commute()
        
        assert result['status'] == 'error'
        assert 'no suitable' in result['message'].lower()
        assert result['route'] is None
    
    def test_get_next_commute_exception_handling(self, commute_service):
        """Test exception handling during recommendation."""
        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendation.side_effect = \
            Exception("Weather API unavailable")
        
        result = commute_service.get_next_commute()
        
        assert result['status'] == 'error'
        assert 'failed to generate' in result['message'].lower()
        assert 'weather api unavailable' in result['message'].lower()


@pytest.mark.unit
class TestGetAllCommuteOptions:
    """Test getting all commute options."""
    
    def test_get_all_options_not_initialized(self, commute_service):
        """Test getting options when service not initialized."""
        result = commute_service.get_all_commute_options('to_work')
        
        assert result['status'] == 'error'
        assert 'not initialized' in result['message'].lower()
        assert result['direction'] == 'to_work'
        assert result['options'] == []
        assert result['count'] == 0
    
    def test_get_all_options_success(self, commute_service, mock_route_group):
        """Test successfully getting all options."""
        # Create multiple mock recommendations
        mock_recs = []
        for i in range(3):
            rec = Mock(spec=CommuteRecommendation)
            rec.direction = 'to_work'
            rec.time_window = 'morning'
            rec.route_group = mock_route_group
            rec.score = 0.9 - (i * 0.1)
            rec.breakdown = {}
            rec.is_today = True
            rec.window_start = time(7, 0)
            rec.window_end = time(9, 0)
            rec.forecast_weather = None
            mock_recs.append(rec)
        
        commute_service._recommender = Mock()
        commute_service._recommender.get_all_recommendations.return_value = mock_recs
        
        result = commute_service.get_all_commute_options('to_work')
        
        assert result['status'] == 'success'
        assert result['direction'] == 'to_work'
        assert result['count'] == 3
        assert len(result['options']) == 3
        # Verify scores are in order
        assert result['options'][0]['score'] == 0.9
        assert result['options'][1]['score'] == 0.8
        assert result['options'][2]['score'] == 0.7
    
    def test_get_all_options_empty_list(self, commute_service):
        """Test when no options are available."""
        commute_service._recommender = Mock()
        commute_service._recommender.get_all_recommendations.return_value = []
        
        result = commute_service.get_all_commute_options('to_home')
        
        assert result['status'] == 'success'
        assert result['count'] == 0
        assert result['options'] == []
    
    def test_get_all_options_exception_handling(self, commute_service):
        """Test exception handling when getting options."""
        commute_service._recommender = Mock()
        commute_service._recommender.get_all_recommendations.side_effect = \
            Exception("Database error")
        
        result = commute_service.get_all_commute_options('to_work')
        
        assert result['status'] == 'error'
        assert 'failed to get options' in result['message'].lower()
        assert result['count'] == 0


@pytest.mark.unit
class TestGetDepartureWindows:
    """Test departure window calculations."""
    
    def test_get_windows_not_initialized(self, commute_service):
        """Test getting windows when service not initialized."""
        result = commute_service.get_departure_windows()
        
        # Should return default windows
        assert 'morning' in result
        assert 'evening' in result
        assert result['morning']['start'] == '07:00'
        assert result['morning']['end'] == '09:00'
        assert result['evening']['start'] == '15:00'
        assert result['evening']['end'] == '18:00'
    
    def test_get_windows_from_recommender(self, commute_service):
        """Test getting windows from initialized recommender."""
        commute_service._recommender = Mock()
        commute_service._recommender.morning_window_start = time(6, 30)
        commute_service._recommender.morning_window_end = time(9, 30)
        commute_service._recommender.evening_window_start = time(16, 0)
        commute_service._recommender.evening_window_end = time(19, 0)
        
        result = commute_service.get_departure_windows()
        
        assert result['morning']['start'] == '06:30'
        assert result['morning']['end'] == '09:30'
        assert result['evening']['start'] == '16:00'
        assert result['evening']['end'] == '19:00'
        # Optimal times are placeholders for now
        assert 'optimal' in result['morning']
        assert 'optimal' in result['evening']


@pytest.mark.unit
class TestFormatRecommendation:
    """Test recommendation formatting."""
    
    def test_format_basic_recommendation(self, commute_service, mock_route_group):
        """Test formatting a basic recommendation."""
        rec = Mock(spec=CommuteRecommendation)
        rec.direction = 'to_work'
        rec.time_window = 'morning'
        rec.route_group = mock_route_group
        rec.score = 0.88
        rec.breakdown = {'time': 0.9, 'distance': 0.85}
        rec.is_today = True
        rec.window_start = time(7, 15)
        rec.window_end = time(8, 45)
        rec.forecast_weather = None
        
        result = commute_service._format_recommendation(rec)
        
        assert result['status'] == 'success'
        assert result['direction'] == 'to_work'
        assert result['time_window'] == 'morning'
        assert result['route']['id'] == 'route_123'
        assert result['route']['name'] == 'Main Commute Route'
        assert result['route']['distance'] == 10.5
        assert result['route']['duration'] == 1800
        assert result['route']['elevation'] == 150.0
        assert result['route']['frequency'] == 25
        assert result['route']['is_plus_route'] is False
        assert result['score'] == 0.88
        assert result['breakdown'] == {'time': 0.9, 'distance': 0.85}
        assert result['is_today'] is True
        assert result['window_start'] == '07:15'
        assert result['window_end'] == '08:45'
        assert 'weather' not in result
    
    def test_format_recommendation_with_weather(self, commute_service, 
                                               mock_route_group):
        """Test formatting recommendation with weather data."""
        rec = Mock(spec=CommuteRecommendation)
        rec.direction = 'to_home'
        rec.time_window = 'evening'
        rec.route_group = mock_route_group
        rec.score = 0.75
        rec.breakdown = {}
        rec.is_today = False
        rec.window_start = time(16, 0)
        rec.window_end = time(17, 30)
        rec.forecast_weather = {
            'temperature': 68.0,
            'conditions': 'Partly Cloudy',
            'wind_speed': 8.0,
            'wind_direction': 'NW',
            'precipitation': 0.0
        }
        
        result = commute_service._format_recommendation(rec)
        
        assert 'weather' in result
        assert result['weather']['temperature'] == 68.0
        assert result['weather']['conditions'] == 'Partly Cloudy'
        assert result['weather']['wind_speed'] == 8.0
        assert result['is_today'] is False
    
    def test_format_recommendation_unnamed_route(self, commute_service, 
                                                 mock_route_group):
        """Test formatting recommendation with unnamed route."""
        mock_route_group.name = None
        
        rec = Mock(spec=CommuteRecommendation)
        rec.direction = 'to_work'
        rec.time_window = 'morning'
        rec.route_group = mock_route_group
        rec.score = 0.8
        rec.breakdown = {}
        rec.is_today = True
        rec.window_start = time(7, 0)
        rec.window_end = time(9, 0)
        rec.forecast_weather = None
        
        result = commute_service._format_recommendation(rec)
        
        # Should use fallback name
        assert result['route']['name'] == 'Route route_123'


@pytest.mark.unit
class TestCommuteServiceIntegration:
    """Integration tests for CommuteService workflows."""
    
    @patch('app.services.commute_service.NextCommuteRecommender')
    def test_full_workflow(self, mock_recommender_class, commute_service,
                          mock_route_group, mock_location):
        """Test complete workflow from initialization to recommendation."""
        home, work = mock_location
        
        # Setup mock recommender
        mock_recommender = Mock()
        mock_recommender_class.return_value = mock_recommender
        
        mock_rec = Mock(spec=CommuteRecommendation)
        mock_rec.direction = 'to_work'
        mock_rec.time_window = 'morning'
        mock_rec.route_group = mock_route_group
        mock_rec.score = 0.9
        mock_rec.breakdown = {}
        mock_rec.is_today = True
        mock_rec.window_start = time(7, 0)
        mock_rec.window_end = time(9, 0)
        mock_rec.forecast_weather = None
        
        mock_recommender.get_next_commute_recommendation.return_value = mock_rec
        mock_recommender.morning_window_start = time(7, 0)
        mock_recommender.morning_window_end = time(9, 0)
        mock_recommender.evening_window_start = time(15, 0)
        mock_recommender.evening_window_end = time(18, 0)
        
        # Initialize service
        commute_service.initialize(
            route_groups=[mock_route_group],
            home_location=home,
            work_location=work
        )
        
        # Get recommendation
        result = commute_service.get_next_commute()
        assert result['status'] == 'success'
        
        # Get departure windows
        windows = commute_service.get_departure_windows()
        assert windows['morning']['start'] == '07:00'
        
        # Get all options
        mock_recommender.get_all_recommendations.return_value = [mock_rec]
        options = commute_service.get_all_commute_options('to_work')
        assert options['count'] == 1

# Made with Bob
