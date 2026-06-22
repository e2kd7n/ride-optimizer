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
from datetime import datetime, time, date, timezone

from app.services.commute_service import CommuteService
from src.next_commute_recommender import CommuteRecommendation
from src.route_analyzer import RouteGroup, Route
from src.location_finder import Location
from src.config_manager import ConfigManager


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=ConfigManager)
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
    route.activity_id = "12345"
    route.distance = 10.5
    route.duration = 1800  # 30 minutes
    route.elevation_gain = 150.0
    route.coordinates = [
        (40.7128, -74.0060),
        (40.7300, -74.0000),
        (40.7589, -73.9851)
    ]
    return route


@pytest.fixture
def mock_route_group(mock_route):
    """Create a mock route group."""
    group = Mock(spec=RouteGroup)
    group.id = "route_123"
    group.name = "Main Commute Route"
    group.representative_route = mock_route
    group.frequency = 25
    group.direction = "home_to_work"
    group.is_plus_route = False
    group.routes = [mock_route]
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
    with patch('app.services.commute_service.ConfigManager.get_instance', return_value=mock_config), \
         patch('app.services.weather_service.ConfigManager.get_instance', return_value=mock_config), \
         patch('app.services.trainerroad_service.ConfigManager.get_instance', return_value=mock_config):
        return CommuteService()


@pytest.mark.unit
class TestCommuteServiceInitialization:
    """Test CommuteService initialization."""
    
    def test_init(self, mock_config, commute_service):
        """Test service initialization."""
        assert commute_service.config == mock_config
        assert commute_service._recommender is None
    
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
        commute_service._recommender.get_next_commute_recommendations.return_value = {'to_work': mock_rec}

        result = commute_service.get_next_commute(direction='to_work')

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
        commute_service._recommender.get_next_commute_recommendations.return_value = {'to_home': mock_rec}

        result = commute_service.get_next_commute(direction='to_home')

        commute_service._recommender.get_next_commute_recommendations.assert_called_once()
        assert result['direction'] == 'to_home'
    
    def test_get_next_commute_no_suitable_route(self, commute_service):
        """Test when no suitable route is found."""
        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendations.return_value = {}

        result = commute_service.get_next_commute()

        assert result['status'] == 'error'
        assert 'no suitable' in result['message'].lower()
        assert result['route'] is None

    def test_get_next_commute_exception_handling(self, commute_service):
        """Test exception handling during recommendation."""
        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendations.side_effect = \
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
        
        mock_recommender.get_next_commute_recommendations.return_value = {'to_work': mock_rec}
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

@pytest.mark.unit
class TestCommuteMapWeatherOverlay:
    """Test commute comparison map weather overlays."""
    
    def test_generate_comparison_map_includes_weather_layer(self, commute_service, mock_route_group, mock_location):
        """Map should include toggleable weather overlay and weather summary widget."""
        home, work = mock_location
        mock_route_group.representative_route.coordinates = [
            (40.7128, -74.0060),
            (40.7300, -74.0000),
            (40.7589, -73.9851)
        ]
        
        commute_service._recommender = Mock()
        commute_service._recommender.route_groups = [mock_route_group]
        commute_service.weather_service.get_current_weather = Mock(return_value={
            'conditions': 'Clear',
            'temperature_c': 20,
            'wind_speed_kph': 10,
            'wind_direction_cardinal': 'NW',
            'precipitation_mm': 0,
            'cycling_favorability': 'favorable',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        routes = [{
            'route': {
                'id': 'route_123',
                'name': 'Main Commute Route',
                'coordinates': mock_route_group.representative_route.coordinates,
                'distance': 10500,
                'duration': 1800,
                'elevation': 150
            },
            'score': 0.9,
            'weather': {'conditions': 'Clear'}
        }]
        
        html = commute_service.generate_comparison_map(routes, home, work)
        
        assert html is not None
        assert 'Weather Overlay' in html
        assert 'Main Commute Route' in html
    
    def test_generate_comparison_map_gracefully_handles_weather_failures(self, commute_service, mock_route_group, mock_location):
        """Map should still render if weather fetch fails."""
        home, work = mock_location
        mock_route_group.representative_route.coordinates = [
            (40.7128, -74.0060),
            (40.7589, -73.9851)
        ]
        
        commute_service._recommender = Mock()
        commute_service._recommender.route_groups = [mock_route_group]
        commute_service.weather_service.get_current_weather = Mock(side_effect=Exception("weather down"))
        
        routes = [{
            'route': {
                'id': 'route_123',
                'name': 'Main Commute Route',
                'coordinates': mock_route_group.representative_route.coordinates,
                'distance': 10500,
                'duration': 1800,
                'elevation': 150
            },
            'score': 0.9
        }]
        
        html = commute_service.generate_comparison_map(routes, home, work)

        assert html is not None
        assert 'Main Commute Route' in html


@pytest.mark.unit
class TestGetNextCommuteTimeBasedDirection:
    """Test time-based direction logic in get_next_commute."""

    def _setup_recommender(self, commute_service, mock_route_group, directions):
        """Helper to set up recommender with recommendations for given directions."""
        recs = {}
        for d in directions:
            rec = Mock(spec=CommuteRecommendation)
            rec.direction = d
            rec.time_window = 'morning' if d == 'to_work' else 'evening'
            rec.route_group = mock_route_group
            rec.score = 0.8
            rec.breakdown = {}
            rec.is_today = True
            rec.window_start = time(7, 0)
            rec.window_end = time(9, 0)
            rec.forecast_weather = None
            recs[d] = rec
        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendations.return_value = recs
        return recs

    @patch('app.services.commute_service.datetime')
    def test_morning_prefers_to_work(self, mock_dt, commute_service, mock_route_group):
        """Before 10 AM, preferred direction should be to_work."""
        mock_dt.now.return_value = datetime(2026, 6, 17, 8, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        self._setup_recommender(commute_service, mock_route_group, ['to_work', 'to_home'])

        result = commute_service.get_next_commute()
        assert result['direction'] == 'to_work'

    @patch('app.services.commute_service.datetime')
    def test_midday_prefers_to_home(self, mock_dt, commute_service, mock_route_group):
        """Between 10 AM and 6 PM, preferred direction should be to_home."""
        mock_dt.now.return_value = datetime(2026, 6, 17, 14, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        self._setup_recommender(commute_service, mock_route_group, ['to_work', 'to_home'])

        result = commute_service.get_next_commute()
        assert result['direction'] == 'to_home'

    @patch('app.services.commute_service.datetime')
    def test_evening_prefers_to_work(self, mock_dt, commute_service, mock_route_group):
        """After 6 PM, preferred direction should be to_work (for tomorrow)."""
        mock_dt.now.return_value = datetime(2026, 6, 17, 20, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        self._setup_recommender(commute_service, mock_route_group, ['to_work', 'to_home'])

        result = commute_service.get_next_commute()
        assert result['direction'] == 'to_work'

    @patch('app.services.commute_service.datetime')
    def test_fallback_when_preferred_missing(self, mock_dt, commute_service, mock_route_group):
        """When preferred direction is not available, return first available."""
        mock_dt.now.return_value = datetime(2026, 6, 17, 14, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        # Only to_work available, but midday prefers to_home
        self._setup_recommender(commute_service, mock_route_group, ['to_work'])

        result = commute_service.get_next_commute()
        assert result['status'] == 'success'
        assert result['direction'] == 'to_work'


@pytest.mark.unit
class TestGetAllCommuteOptionsDefaultDirection:
    """Test default direction logic in get_all_commute_options."""

    def test_default_direction_uses_time(self, commute_service):
        """Default direction should be based on current time of day."""
        commute_service._recommender = Mock()
        commute_service._recommender.get_all_recommendations.return_value = []

        from datetime import datetime as _dt
        current_hour = _dt.now().hour
        expected = 'to_work' if current_hour < 12 else 'to_home'

        result = commute_service.get_all_commute_options()
        assert result['direction'] == expected


@pytest.mark.unit
class TestRouteColorAndConfidence:
    """Test _get_route_color and _get_confidence_label."""

    def test_route_color_high_score(self, commute_service):
        assert commute_service._get_route_color(0.90) == '#28a745'

    def test_route_color_medium_score(self, commute_service):
        assert commute_service._get_route_color(0.75) == '#007bff'

    def test_route_color_low_score(self, commute_service):
        assert commute_service._get_route_color(0.55) == '#ffc107'

    def test_route_color_very_low_score(self, commute_service):
        assert commute_service._get_route_color(0.30) == '#dc3545'

    def test_confidence_high(self, commute_service):
        assert commute_service._get_confidence_label(0.90) == 'high'

    def test_confidence_medium(self, commute_service):
        assert commute_service._get_confidence_label(0.70) == 'medium'

    def test_confidence_low(self, commute_service):
        assert commute_service._get_confidence_label(0.50) == 'low'


@pytest.mark.unit
class TestComparisonPopup:
    """Test _create_comparison_popup HTML generation."""

    def test_popup_includes_route_details(self, commute_service):
        route_option = {
            'route': {
                'name': 'Test Route',
                'distance': 10500,
                'duration': 1800,
                'elevation': 150
            },
            'score': 0.85,
            'weather': {
                'conditions': 'Clear',
                'temperature': 72,
                'wind_speed': 5,
                'precipitation': 0,
                'cycling_favorability': 'favorable'
            }
        }
        html = commute_service._create_comparison_popup(route_option)
        assert 'Test Route' in html
        assert '85%' in html
        assert 'Clear' in html
        assert '72' in html
        assert 'Favorable' in html

    def test_popup_without_weather(self, commute_service):
        route_option = {
            'route': {
                'name': 'No Weather Route',
                'distance': 5000,
                'duration': 900,
                'elevation': 50
            },
            'score': 0.6,
            'weather': None
        }
        html = commute_service._create_comparison_popup(route_option)
        assert 'No Weather Route' in html
        assert 'Unavailable' in html


@pytest.mark.unit
class TestWeatherMarkerStyle:
    """Test _get_weather_marker_style."""

    def test_rainy_conditions(self, commute_service):
        weather = {'conditions': 'Light Rain', 'precipitation': 1.0}
        icon, prefix, color = commute_service._get_weather_marker_style(weather)
        assert icon == 'cloud-rain'
        assert color == 'red'

    def test_windy_conditions(self, commute_service):
        weather = {'conditions': 'Clear', 'wind_speed_kph': 30}
        icon, prefix, color = commute_service._get_weather_marker_style(weather)
        assert icon == 'flag'
        assert color == 'orange'

    def test_cloudy_conditions(self, commute_service):
        weather = {'conditions': 'Overcast', 'wind_speed_kph': 5}
        icon, prefix, color = commute_service._get_weather_marker_style(weather)
        assert icon == 'cloud'
        assert color == 'blue'

    def test_favorable_conditions(self, commute_service):
        weather = {'conditions': 'Clear', 'wind_speed_kph': 5, 'cycling_favorability': 'favorable'}
        icon, prefix, color = commute_service._get_weather_marker_style(weather)
        assert icon == 'sun'
        assert color == 'green'

    def test_default_conditions(self, commute_service):
        weather = {'conditions': 'Haze', 'wind_speed_kph': 10}
        icon, prefix, color = commute_service._get_weather_marker_style(weather)
        assert icon == 'cloud-sun'
        assert color == 'lightgray'


@pytest.mark.unit
class TestWeatherPopup:
    """Test _create_weather_popup HTML generation."""

    def test_popup_with_all_fields(self, commute_service):
        weather = {
            'conditions': 'Clear',
            'temperature': 72,
            'wind_speed': 10,
            'wind_direction_cardinal': 'NW',
            'precipitation_probability': 20
        }
        html = commute_service._create_weather_popup('Home', weather)
        assert 'Home' in html
        assert 'Clear' in html
        assert '72' in html
        assert '10' in html
        assert 'NW' in html
        assert '20%' in html

    def test_popup_with_celsius_conversion(self, commute_service):
        weather = {
            'conditions': 'Cloudy',
            'temperature_c': 20,
            'wind_speed_kph': 15,
            'wind_direction': 'S',
            'precipitation_mm': 2.5
        }
        html = commute_service._create_weather_popup('Work', weather)
        assert 'Work' in html
        assert '68' in html  # 20°C = 68°F
        assert '2.5' in html

    def test_popup_with_stale_data(self, commute_service):
        weather = {
            'conditions': 'Clear',
            'temperature': 70,
            'is_stale': True
        }
        html = commute_service._create_weather_popup('Test', weather)
        assert 'stale' in html.lower()


@pytest.mark.unit
class TestWorkoutAwareCommute:
    """Test get_workout_aware_commute."""

    def test_no_workout_scheduled(self, commute_service, mock_route_group):
        """When no workout, return base recommendation with workout_fit=None."""
        commute_service.trainerroad_service.get_workout_constraints = Mock(return_value=None)
        mock_rec = Mock(spec=CommuteRecommendation)
        mock_rec.direction = 'to_work'
        mock_rec.time_window = 'morning'
        mock_rec.route_group = mock_route_group
        mock_rec.score = 0.85
        mock_rec.breakdown = {}
        mock_rec.is_today = True
        mock_rec.window_start = time(7, 0)
        mock_rec.window_end = time(9, 0)
        mock_rec.forecast_weather = None

        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendations.return_value = {'to_work': mock_rec}

        result = commute_service.get_workout_aware_commute('to_work')
        assert result['status'] == 'success'
        assert result['workout_fit'] is None
        assert result['is_workout_extended'] is False

    def test_base_rec_error_returned(self, commute_service):
        """When base recommendation is an error, return it directly."""
        commute_service.trainerroad_service.get_workout_constraints = Mock(return_value={'workout_name': 'Test'})
        commute_service._recommender = None

        result = commute_service.get_workout_aware_commute()
        assert result['status'] == 'error'

    def test_with_workout_no_extension(self, commute_service, mock_route_group):
        """Workout scheduled but no extension needed (non-endurance)."""
        commute_service.trainerroad_service.get_workout_constraints = Mock(return_value={
            'workout_name': 'Intervals',
            'workout_type': 'VO2Max',
            'min_duration_minutes': 30,
            'max_duration_minutes': 60,
            'indoor_fallback': True,
            'notes': []
        })
        mock_rec = Mock(spec=CommuteRecommendation)
        mock_rec.direction = 'to_work'
        mock_rec.time_window = 'morning'
        mock_rec.route_group = mock_route_group
        mock_rec.score = 0.85
        mock_rec.breakdown = {}
        mock_rec.is_today = True
        mock_rec.window_start = time(7, 0)
        mock_rec.window_end = time(9, 0)
        mock_rec.forecast_weather = None

        commute_service._recommender = Mock()
        commute_service._recommender.get_next_commute_recommendations.return_value = {'to_work': mock_rec}

        result = commute_service.get_workout_aware_commute('to_work')
        assert result['status'] == 'success'
        assert result['workout_fit'] is not None
        assert result['workout_fit']['workout_name'] == 'Intervals'
        assert result['is_workout_extended'] is False


@pytest.mark.unit
class TestAnalyzeWorkoutFit:
    """Test _analyze_workout_fit."""

    def test_duration_matches(self, commute_service):
        recommendation = {'route': {'duration': 45}}  # 45 "minutes" (code reads raw value)
        constraints = {
            'workout_name': 'Endurance',
            'workout_type': 'Endurance',
            'min_duration_minutes': 30,
            'max_duration_minutes': 60,
            'indoor_fallback': False,
            'notes': ['Easy spin']
        }
        result = commute_service._analyze_workout_fit(recommendation, constraints)
        assert result['fit_score'] == 1.0
        assert 'Duration matches' in result['fit_reasons'][0]
        assert result['indoor_fallback'] is False

    def test_duration_too_short(self, commute_service):
        recommendation = {'route': {'duration': 10}}
        constraints = {
            'workout_name': 'Long Ride',
            'workout_type': 'Endurance',
            'min_duration_minutes': 60,
            'max_duration_minutes': None,
            'indoor_fallback': False,
            'notes': []
        }
        result = commute_service._analyze_workout_fit(recommendation, constraints)
        assert result['fit_score'] < 0.5

    def test_duration_too_long(self, commute_service):
        recommendation = {'route': {'duration': 7200}}  # 120 min
        constraints = {
            'workout_name': 'Recovery',
            'workout_type': 'Recovery',
            'min_duration_minutes': None,
            'max_duration_minutes': 30,
            'indoor_fallback': False,
            'notes': []
        }
        result = commute_service._analyze_workout_fit(recommendation, constraints)
        assert 'longer than recommended' in result['fit_reasons'][0]

    def test_indoor_fallback_penalty(self, commute_service):
        recommendation = {'route': {'duration': 2400}}
        constraints = {
            'workout_name': 'Sprint Intervals',
            'workout_type': 'VO2Max',
            'min_duration_minutes': 30,
            'max_duration_minutes': 50,
            'indoor_fallback': True,
            'notes': []
        }
        result = commute_service._analyze_workout_fit(recommendation, constraints)
        assert result['indoor_fallback'] is True
        assert any('indoor' in r.lower() for r in result['fit_reasons'])


@pytest.mark.unit
class TestShouldExtendForWorkout:
    """Test _should_extend_for_workout."""

    def test_extends_for_short_endurance_route(self, commute_service):
        constraints = {
            'workout_type': 'Endurance',
            'indoor_fallback': False,
            'min_duration_minutes': 60
        }
        recommendation = {'route': {'duration': 30}}  # 30 < 60
        assert commute_service._should_extend_for_workout(constraints, recommendation) is True

    def test_no_extend_for_non_endurance(self, commute_service):
        constraints = {
            'workout_type': 'VO2Max',
            'indoor_fallback': False,
            'min_duration_minutes': 60
        }
        recommendation = {'route': {'duration': 1800}}
        assert commute_service._should_extend_for_workout(constraints, recommendation) is False

    def test_no_extend_for_indoor_fallback(self, commute_service):
        constraints = {
            'workout_type': 'Endurance',
            'indoor_fallback': True,
            'min_duration_minutes': 60
        }
        recommendation = {'route': {'duration': 1800}}
        assert commute_service._should_extend_for_workout(constraints, recommendation) is False

    def test_no_extend_when_duration_sufficient(self, commute_service):
        constraints = {
            'workout_type': 'Endurance',
            'indoor_fallback': False,
            'min_duration_minutes': 30
        }
        recommendation = {'route': {'duration': 2400}}  # 40 min > 30 min
        assert commute_service._should_extend_for_workout(constraints, recommendation) is False


@pytest.mark.unit
class TestExtendRouteForWorkout:
    """Test _extend_route_for_workout."""

    def test_no_recommender_returns_none(self, commute_service):
        commute_service._recommender = None
        result = commute_service._extend_route_for_workout(
            {'direction': 'to_work'},
            {'min_duration_minutes': 60}
        )
        assert result is None

    def test_no_suitable_routes_returns_none(self, commute_service):
        commute_service._recommender = Mock()
        commute_service._recommender.get_all_recommendations.return_value = []

        result = commute_service._extend_route_for_workout(
            {'direction': 'to_work', 'route': {'duration': 1800}},
            {'min_duration_minutes': 120, 'workout_name': 'Long Endurance'}
        )
        assert result is None

    def test_extends_to_suitable_route(self, commute_service, mock_route_group):
        extended_rec = Mock(spec=CommuteRecommendation)
        extended_rec.direction = 'to_work'
        extended_rec.time_window = 'morning'
        extended_rec.route_group = mock_route_group
        extended_rec.score = 0.75
        extended_rec.breakdown = {}
        extended_rec.is_today = True
        extended_rec.window_start = time(7, 0)
        extended_rec.window_end = time(9, 0)
        extended_rec.forecast_weather = None
        extended_rec.duration_minutes = 65

        commute_service._recommender = Mock()
        commute_service._recommender.get_all_recommendations.return_value = [extended_rec]

        result = commute_service._extend_route_for_workout(
            {'direction': 'to_work', 'route': {'duration': 1800}},
            {'min_duration_minutes': 60, 'workout_name': 'Endurance Ride'}
        )
        assert result is not None
        assert result['extension_reason'] is not None

    def test_exception_returns_none(self, commute_service):
        commute_service._recommender = Mock()
        commute_service._recommender.get_all_recommendations.side_effect = Exception("Boom")

        result = commute_service._extend_route_for_workout(
            {'direction': 'to_work', 'route': {'duration': 1800}},
            {'min_duration_minutes': 60, 'workout_name': 'Test'}
        )
        assert result is None


@pytest.mark.unit
class TestGenerateComparisonMapEmpty:
    """Test generate_comparison_map edge cases."""

    def test_empty_routes_returns_none(self, commute_service, mock_location):
        home, work = mock_location
        result = commute_service.generate_comparison_map([], home, work)
        assert result is None

    def test_map_with_direction_colors(self, commute_service, mock_route_group, mock_location):
        """Routes should get direction-based colors."""
        home, work = mock_location
        mock_route_group.representative_route.coordinates = [
            (40.7128, -74.0060),
            (40.7589, -73.9851)
        ]
        commute_service._recommender = Mock()
        commute_service._recommender.route_groups = [mock_route_group]
        commute_service.weather_service.get_current_weather = Mock(return_value=None)

        routes = [{
            'route': {
                'id': 'route_123',
                'name': 'Test',
                'coordinates': mock_route_group.representative_route.coordinates,
                'distance': 10500,
                'duration': 1800,
                'elevation': 150
            },
            'direction': 'to_work',
            'score': 0.9,
            'weather': {}
        }]

        html = commute_service.generate_comparison_map(routes, home, work)
        assert html is not None
        assert '#28a745' in html  # Green for to_work

