"""
Unit tests for AnalysisService.

Tests cover:
- Service initialization
- Full analysis workflow
- Analysis status tracking
- Data getters (route groups, long rides, activities, locations)
- Cache management
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.analysis_service import AnalysisService
from src.data_fetcher import Activity
from src.route_analyzer import RouteGroup, Route
from src.long_ride_analyzer import LongRide
from src.location_finder import Location
from src.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'analysis.staleness_hours': 24,
        'cache.directory': 'cache/'
    }.get(key, default))
    return config


@pytest.fixture
def mock_activity():
    """Create a mock activity."""
    activity = Mock(spec=Activity)
    activity.id = "12345"
    activity.name = "Morning Commute"
    activity.distance = 10.5
    activity.duration = 1800
    activity.start_date = datetime.now()
    return activity


@pytest.fixture
def mock_route_group():
    """Create a mock route group."""
    route = Mock(spec=Route)
    route.activity_id = "12345"
    route.distance = 10.5
    route.duration = 1800
    
    group = Mock(spec=RouteGroup)
    group.id = "route_1"
    group.name = "Main Commute"
    group.routes = [route]
    group.frequency = 25
    return group


@pytest.fixture
def mock_long_ride():
    """Create a mock long ride."""
    ride = Mock(spec=LongRide)
    ride.id = "long_ride_1"
    ride.name = "Weekend Century"
    ride.distance = 100.0
    ride.duration = 18000
    return ride


@pytest.fixture
def mock_location():
    """Create mock locations."""
    home = Location(name="Home", lat=40.7128, lon=-74.0060, activity_count=10)
    work = Location(name="Work", lat=40.7589, lon=-73.9851, activity_count=10)
    return home, work


@pytest.fixture
def analysis_service(mock_config):
    """Create an AnalysisService instance."""
    # Mock get_authenticated_client to avoid loading real credentials
    with patch('src.auth.get_authenticated_client') as mock_auth:
        mock_client = Mock()
        mock_auth.return_value = mock_client
        service = AnalysisService(mock_config)
        # Mock the _load_from_cache to prevent it from loading cache during tests
        service._cache_loaded = True
        return service


@pytest.mark.unit
class TestAnalysisServiceInitialization:
    """Test AnalysisService initialization."""
    
    def test_init(self, mock_config):
        """Test service initialization."""
        with patch('src.auth.get_authenticated_client') as mock_auth:
            mock_client = Mock()
            mock_auth.return_value = mock_client
            service = AnalysisService(mock_config)
            
            assert service.config == mock_config
            assert service.data_fetcher is not None
            assert service._activities is None
            assert service._route_groups is None
            assert service._long_rides is None
            assert service._home_location is None
            assert service._work_location is None
            assert service._last_analysis_time is None


@pytest.mark.unit
class TestRunFullAnalysis:
    """Test full analysis workflow."""
    
    @patch('app.services.analysis_service.LocationFinder')
    @patch('app.services.analysis_service.LongRideAnalyzer')
    @patch('app.services.analysis_service.RouteAnalyzer')
    def test_run_full_analysis_success(self, mock_route_analyzer_class,
                                       mock_long_ride_analyzer_class,
                                       mock_location_finder_class,
                                       analysis_service, mock_activity,
                                       mock_route_group, mock_long_ride,
                                       mock_location):
        """Test successful full analysis."""
        home, work = mock_location
        
        # Mock data fetcher directly to avoid authentication
        mock_data_fetcher = Mock()
        mock_data_fetcher.fetch_activities = Mock(return_value=[mock_activity])
        analysis_service._data_fetcher = mock_data_fetcher
        
        # Mock location finder
        mock_location_finder = Mock()
        mock_location_finder.find_locations = Mock(return_value=(home, work))
        mock_location_finder_class.return_value = mock_location_finder
        
        # Mock route analyzer
        mock_route_analyzer = Mock()
        mock_route_analyzer.analyze_routes = Mock(return_value=[mock_route_group])
        mock_route_analyzer_class.return_value = mock_route_analyzer
        
        # Mock long ride analyzer
        mock_long_ride_analyzer = Mock()
        mock_long_ride_analyzer.classify_activities = Mock(return_value=([], [mock_activity]))
        mock_long_ride_analyzer.group_similar_rides = Mock(return_value=[mock_long_ride])
        mock_long_ride_analyzer_class.return_value = mock_long_ride_analyzer
        
        # Run analysis
        result = analysis_service.run_full_analysis()
        
        assert result['status'] == 'success'
        assert result['activities_count'] == 1
        assert result['route_groups_count'] == 1
        assert result['long_rides_count'] == 1
        assert result['data_freshness'] == 'fresh'
        assert len(result['errors']) == 0
        assert 'analysis_time' in result
    
    def test_run_full_analysis_no_activities(self, analysis_service):
        """Test analysis with no activities."""
        # Mock data fetcher directly to avoid authentication
        mock_data_fetcher = Mock()
        mock_data_fetcher.fetch_activities = Mock(return_value=[])
        analysis_service._data_fetcher = mock_data_fetcher
        
        result = analysis_service.run_full_analysis()
        
        assert result['status'] == 'error'
        assert result['message'] == 'No activities found'
        assert result['activities_count'] == 0
        assert result['route_groups_count'] == 0
        assert result['long_rides_count'] == 0
        assert 'No activities available' in result['errors'][0]
    
    @patch('app.services.analysis_service.LocationFinder')
    def test_run_full_analysis_with_force_refresh(self, mock_location_finder_class,
                                                  analysis_service, mock_activity):
        """Test analysis with force refresh."""
        # Mock data fetcher directly to avoid authentication
        mock_data_fetcher = Mock()
        mock_data_fetcher.fetch_activities = Mock(return_value=[mock_activity])
        analysis_service._data_fetcher = mock_data_fetcher
        
        # Mock location finder
        mock_location_finder = Mock()
        mock_location_finder.find_locations = Mock(return_value=(Mock(), Mock()))
        mock_location_finder_class.return_value = mock_location_finder
        
        with patch('app.services.analysis_service.RouteAnalyzer'), \
             patch('app.services.analysis_service.LongRideAnalyzer'):
            
            result = analysis_service.run_full_analysis(force_refresh=True)
            
            # Verify force_refresh was passed through
            mock_data_fetcher.fetch_activities.assert_called_once_with(
                force_refresh=True
            )
    
    def test_run_full_analysis_exception_handling(self, analysis_service):
        """Test exception handling during analysis."""
        # Mock data fetcher directly to avoid authentication
        mock_data_fetcher = Mock()
        mock_data_fetcher.fetch_activities = Mock(side_effect=Exception("API Error"))
        analysis_service._data_fetcher = mock_data_fetcher
        
        result = analysis_service.run_full_analysis()
        
        assert result['status'] == 'error'
        assert 'API Error' in result['message']
        assert 'API Error' in result['errors'][0]
        assert result['activities_count'] == 0


@pytest.mark.unit
class TestGetAnalysisStatus:
    """Test analysis status retrieval."""
    
    def test_get_status_no_data(self, analysis_service):
        """Test status when no analysis has been run."""
        status = analysis_service.get_analysis_status()
        
        assert status['has_data'] is False
        assert status['last_analysis'] is None
        assert status['activities_count'] == 0
        assert status['route_groups_count'] == 0
        assert status['long_rides_count'] == 0
        assert status['data_age_hours'] is None
        assert status['is_stale'] is True
    
    def test_get_status_with_fresh_data(self, analysis_service, mock_activity,
                                       mock_route_group, mock_long_ride):
        """Test status with fresh data."""
        # Simulate completed analysis
        analysis_service._activities = [mock_activity]
        analysis_service._route_groups = [mock_route_group]
        analysis_service._long_rides = [mock_long_ride]
        analysis_service._last_analysis_time = datetime.now()
        
        status = analysis_service.get_analysis_status()
        
        assert status['has_data'] is True
        assert status['last_analysis'] is not None
        assert status['activities_count'] == 1
        assert status['route_groups_count'] == 1
        assert status['long_rides_count'] == 1
        assert status['data_age_hours'] is not None
        assert status['data_age_hours'] < 1  # Less than 1 hour old
        assert status['is_stale'] is False
    
    def test_get_status_with_stale_data(self, analysis_service, mock_activity, mock_route_group):
        """Test status with stale data (>24 hours old)."""
        analysis_service._activities = [mock_activity]
        analysis_service._route_groups = [mock_route_group]  # Need non-empty for has_data=True
        analysis_service._long_rides = []
        analysis_service._last_analysis_time = datetime.now() - timedelta(hours=25)
        
        status = analysis_service.get_analysis_status()
        
        assert status['has_data'] is True  # Has route groups
        assert status['data_age_hours'] > 24
        assert status['is_stale'] is True
    
    def test_get_status_partial_data(self, analysis_service, mock_activity):
        """Test status with partial data."""
        # Only activities, no route groups or long rides
        analysis_service._activities = [mock_activity]
        analysis_service._last_analysis_time = datetime.now()
        
        status = analysis_service.get_analysis_status()
        
        assert status['has_data'] is False  # Requires all three
        assert status['activities_count'] == 1
        assert status['route_groups_count'] == 0
        assert status['long_rides_count'] == 0


@pytest.mark.unit
class TestDataGetters:
    """Test data getter methods."""
    
    def test_get_route_groups_empty(self, analysis_service):
        """Test getting route groups when none exist."""
        groups = analysis_service.get_route_groups()
        
        assert groups == []
    
    def test_get_route_groups_with_data(self, analysis_service, mock_route_group):
        """Test getting route groups with data."""
        analysis_service._route_groups = [mock_route_group]
        
        groups = analysis_service.get_route_groups()
        
        assert len(groups) == 1
        assert groups[0] == mock_route_group
    
    def test_get_long_rides_empty(self, analysis_service):
        """Test getting long rides when none exist."""
        rides = analysis_service.get_long_rides()
        
        assert rides == []
    
    def test_get_long_rides_with_data(self, analysis_service, mock_long_ride):
        """Test getting long rides with data."""
        analysis_service._long_rides = [mock_long_ride]
        
        rides = analysis_service.get_long_rides()
        
        assert len(rides) == 1
        assert rides[0] == mock_long_ride
    
    def test_get_activities_empty(self, analysis_service):
        """Test getting activities when none exist."""
        activities = analysis_service.get_activities()
        
        assert activities == []
    
    def test_get_activities_with_data(self, analysis_service, mock_activity):
        """Test getting activities with data."""
        analysis_service._activities = [mock_activity]
        
        activities = analysis_service.get_activities()
        
        assert len(activities) == 1
        assert activities[0] == mock_activity
    
    def test_get_locations_none(self, analysis_service):
        """Test getting locations when none exist."""
        home, work = analysis_service.get_locations()
        
        assert home is None
        assert work is None
    
    def test_get_locations_with_data(self, analysis_service, mock_location):
        """Test getting locations with data."""
        home_loc, work_loc = mock_location
        analysis_service._home_location = home_loc
        analysis_service._work_location = work_loc
        
        home, work = analysis_service.get_locations()
        
        assert home == home_loc
        assert work == work_loc


@pytest.mark.unit
class TestCacheManagement:
    """Test cache management."""
    
    def test_clear_cache(self, analysis_service, mock_activity, mock_route_group,
                        mock_long_ride, mock_location):
        """Test clearing all cached data."""
        home, work = mock_location
        
        # Set up cached data
        analysis_service._activities = [mock_activity]
        analysis_service._route_groups = [mock_route_group]
        analysis_service._long_rides = [mock_long_ride]
        analysis_service._home_location = home
        analysis_service._work_location = work
        analysis_service._last_analysis_time = datetime.now()
        
        # Clear cache
        analysis_service.clear_cache()
        
        # Verify all data is cleared
        assert analysis_service._activities is None
        assert analysis_service._route_groups is None
        assert analysis_service._long_rides is None
        assert analysis_service._home_location is None
        assert analysis_service._work_location is None
        assert analysis_service._last_analysis_time is None


@pytest.mark.unit
class TestAnalysisServiceIntegration:
    """Integration tests for AnalysisService workflows."""
    
    @patch('app.services.analysis_service.LocationFinder')
    @patch('app.services.analysis_service.LongRideAnalyzer')
    @patch('app.services.analysis_service.RouteAnalyzer')
    def test_full_workflow_with_status_check(self, mock_route_analyzer_class,
                                             mock_long_ride_analyzer_class,
                                             mock_location_finder_class,
                                             analysis_service, mock_activity,
                                             mock_route_group, mock_long_ride,
                                             mock_location):
        """Test complete workflow: analyze -> check status -> get data."""
        home, work = mock_location
        
        # Setup mocks - mock data fetcher directly to avoid authentication
        mock_data_fetcher = Mock()
        mock_data_fetcher.fetch_activities = Mock(return_value=[mock_activity])
        analysis_service._data_fetcher = mock_data_fetcher
        
        # Mock location finder
        mock_location_finder = Mock()
        mock_location_finder.find_locations = Mock(return_value=(home, work))
        mock_location_finder_class.return_value = mock_location_finder
        
        mock_route_analyzer = Mock()
        mock_route_analyzer.analyze_routes = Mock(return_value=[mock_route_group])
        mock_route_analyzer_class.return_value = mock_route_analyzer
        
        mock_long_ride_analyzer = Mock()
        mock_long_ride_analyzer.classify_activities = Mock(return_value=([], [mock_activity]))
        mock_long_ride_analyzer.group_similar_rides = Mock(return_value=[mock_long_ride])
        mock_long_ride_analyzer_class.return_value = mock_long_ride_analyzer
        
        # Run analysis
        result = analysis_service.run_full_analysis()
        assert result['status'] == 'success'
        
        # Check status
        status = analysis_service.get_analysis_status()
        assert status['has_data'] is True
        assert status['is_stale'] is False
        
        # Get data
        activities = analysis_service.get_activities()
        assert len(activities) == 1
        
        route_groups = analysis_service.get_route_groups()
        assert len(route_groups) == 1
        
        long_rides = analysis_service.get_long_rides()
        assert len(long_rides) == 1
        
        home_loc, work_loc = analysis_service.get_locations()
        assert home_loc == home
        assert work_loc == work
    
    @patch('app.services.analysis_service.LocationFinder')
    @patch('app.services.analysis_service.LongRideAnalyzer')
    @patch('app.services.analysis_service.RouteAnalyzer')
    def test_workflow_with_cache_clear(self, mock_route_analyzer_class,
                                       mock_long_ride_analyzer_class,
                                       mock_location_finder_class,
                                       analysis_service, mock_activity,
                                       mock_location):
        """Test workflow with cache clearing."""
        home, work = mock_location
        
        # Setup mocks - mock data fetcher directly to avoid authentication
        mock_data_fetcher = Mock()
        mock_data_fetcher.fetch_activities = Mock(return_value=[mock_activity])
        analysis_service._data_fetcher = mock_data_fetcher
        
        # Mock location finder
        mock_location_finder = Mock()
        mock_location_finder.find_locations = Mock(return_value=(home, work))
        mock_location_finder_class.return_value = mock_location_finder
        
        # Create mock route group for non-empty result
        mock_route_group = Mock()
        mock_route_group.routes = []
        
        mock_route_analyzer = Mock()
        mock_route_analyzer.analyze_routes = Mock(return_value=[mock_route_group])
        mock_route_analyzer_class.return_value = mock_route_analyzer
        
        mock_long_ride_analyzer = Mock()
        mock_long_ride_analyzer.classify_activities = Mock(return_value=([], []))
        mock_long_ride_analyzer.group_similar_rides = Mock(return_value=[])
        mock_long_ride_analyzer_class.return_value = mock_long_ride_analyzer
        
        # Run analysis
        result = analysis_service.run_full_analysis()
        assert result['status'] == 'success'
        
        # Verify data exists (has_data checks for non-empty route_groups)
        status = analysis_service.get_analysis_status()
        assert status['has_data'] is True
        
        # Clear cache
        analysis_service.clear_cache()
        
        # Verify data is gone
        status = analysis_service.get_analysis_status()
        assert status['has_data'] is False
        assert len(analysis_service.get_activities()) == 0

# Made with Bob
