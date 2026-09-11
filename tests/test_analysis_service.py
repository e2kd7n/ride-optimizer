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

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime, timedelta

from app.services.analysis_service import AnalysisService
from src.data_fetcher import Activity
from src.route_analyzer import RouteGroup, Route
from src.long_ride_analyzer import LongRide
from src.location_finder import Location
from src.config_manager import ConfigManager


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=ConfigManager)
    config.get = Mock(side_effect=lambda key, default=None: {
        'analysis.staleness_hours': 24,
        'cache.directory': 'cache/'
    }.get(key, default))
    return config


@pytest.fixture(autouse=True)
def _patch_config_manager(mock_config):
    """Patch ConfigManager.get_instance globally for all tests."""
    with patch('app.services.analysis_service.ConfigManager.get_instance', return_value=mock_config), \
         patch('app.services.weather_service.ConfigManager.get_instance', return_value=mock_config):
        yield


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
def analysis_service():
    """Create an AnalysisService instance."""
    with patch('src.auth_secure.get_authenticated_client') as mock_auth:
        mock_client = Mock()
        mock_auth.return_value = mock_client
        service = AnalysisService()
        service.storage.write = Mock(return_value=True)
        service._cache_loaded = True
        return service


@pytest.mark.unit
class TestAnalysisServiceInitialization:
    """Test AnalysisService initialization."""
    
    def test_init(self, mock_config):
        """Test service initialization."""
        with patch('src.auth_secure.get_authenticated_client') as mock_auth:
            mock_client = Mock()
            mock_auth.return_value = mock_client
            service = AnalysisService()
            
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
        mock_location_finder.identify_home_work = Mock(return_value=(home, work))
        mock_location_finder_class.return_value = mock_location_finder
        
        # Mock route analyzer
        mock_route_analyzer = Mock()
        mock_route_analyzer.group_similar_routes = Mock(return_value=[mock_route_group])
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
        mock_location_finder.identify_home_work = Mock(return_value=(Mock(), Mock()))
        mock_location_finder_class.return_value = mock_location_finder
        
        with patch('app.services.analysis_service.RouteAnalyzer'), \
             patch('app.services.analysis_service.LongRideAnalyzer'):
            
            result = analysis_service.run_full_analysis(force_refresh=True)
            
            mock_data_fetcher.fetch_activities.assert_called_once()
            call_kwargs = mock_data_fetcher.fetch_activities.call_args.kwargs
            assert call_kwargs.get('use_cache') is False
    
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

    @patch('app.services.analysis_service.LocationFinder')
    @patch('app.services.analysis_service.LongRideAnalyzer')
    @patch('app.services.analysis_service.RouteAnalyzer')
    def test_skip_strava_fetch_reads_activities_key(self, mock_route_analyzer_class,
                                                    mock_long_ride_analyzer_class,
                                                    mock_location_finder_class,
                                                    analysis_service, mock_location):
        """Cache file uses {timestamp, count, activities:[...]} wrapper — skip_strava_fetch must read the nested list."""
        home, work = mock_location

        activity_data = {
            'id': 99, 'name': 'Test Ride', 'type': 'Ride',
            'distance': 10000.0, 'moving_time': 1800, 'elapsed_time': 1900,
            'total_elevation_gain': 50.0, 'average_speed': 5.5, 'max_speed': 8.0,
        }
        wrapped_json = json.dumps({
            'timestamp': '2026-06-13T00:00:00',
            'count': 1,
            'activities': [activity_data],
        })

        mock_location_finder_class.return_value.identify_home_work.return_value = (home, work)
        mock_route_analyzer_class.return_value.group_similar_routes.return_value = [Mock(routes=[])]
        mock_long_ride_analyzer_class.return_value.classify_activities.return_value = ([], [])
        mock_long_ride_analyzer_class.return_value.group_similar_rides.return_value = []

        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True

        with patch('app.services.analysis_service.Path', return_value=mock_path_instance), \
             patch('builtins.open', mock_open(read_data=wrapped_json)):
            result = analysis_service.run_full_analysis(skip_strava_fetch=True)

        assert result['status'] == 'success'
        assert result['activities_count'] == 1

    def test_skip_strava_fetch_missing_cache(self, analysis_service):
        """skip_strava_fetch with no cache file returns a clear error."""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False

        with patch('app.services.analysis_service.Path', return_value=mock_path_instance):
            result = analysis_service.run_full_analysis(skip_strava_fetch=True)

        assert result['status'] == 'error'
        assert 'No cached activities' in result['message'] or 'No cached activities' in result['errors'][0]


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
        mock_location_finder.identify_home_work = Mock(return_value=(home, work))
        mock_location_finder_class.return_value = mock_location_finder
        
        mock_route_analyzer = Mock()
        mock_route_analyzer.group_similar_routes = Mock(return_value=[mock_route_group])
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


@pytest.mark.unit
class TestCacheRoundTrip:
    """Test that _save_to_cache → _load_from_cache round-trips correctly."""

    def test_round_trip_preserves_all_data(self, mock_config, tmp_path):
        """Save analysis results to cache, create fresh service, load, verify."""
        route = Route(
            activity_id=111,
            direction='home_to_work',
            coordinates=[(40.7128, -74.0060), (40.7589, -73.9851)],
            distance=8500.0,
            duration=1200,
            elevation_gain=45.0,
            timestamp='2026-06-01T08:00:00',
            average_speed=7.08,
            activity_name='Morning Ride',
            is_plus_route=False,
        )
        group = RouteGroup(
            id='htw_0',
            direction='home_to_work',
            routes=[route],
            representative_route=route,
            frequency=20,
            name='Lakefront Commute',
            is_plus_route=False,
            difficulty='Medium',
        )
        ride = LongRide(
            activity_id=222,
            name='Century Loop',
            coordinates=[(41.0, -87.0), (41.5, -87.5)],
            distance=160000.0,
            duration=21600,
            elevation_gain=800.0,
            timestamp='2026-05-15T07:00:00',
            average_speed=7.4,
            start_location=(41.0, -87.0),
            end_location=(41.0, -87.0),
            is_loop=True,
            type='Ride',
            uses=3,
            activity_ids=[222, 223, 224],
            activity_dates=['2026-05-15', '2026-04-20', '2026-03-10'],
            activity_names=['Century', 'Century v2', 'Century v3'],
        )
        home = Location(name='Home', lat=40.7128, lon=-74.0060, activity_count=50)
        work = Location(name='Office', lat=40.7589, lon=-73.9851, activity_count=50)

        from src.json_storage import JSONStorage
        storage = JSONStorage(str(tmp_path / 'data'))

        # --- Save ---
        svc = AnalysisService()
        svc.storage = storage
        svc._cache_loaded = True
        svc._route_groups = [group]
        svc._long_rides = [ride]
        svc._home_location = home
        svc._work_location = work
        svc._last_analysis_time = datetime(2026, 6, 17, 12, 0, 0)
        svc._activities = []
        svc._save_to_cache()

        # --- Load in fresh service ---
        svc2 = AnalysisService()
        svc2.storage = storage
        svc2._load_from_cache()

        # Route groups
        assert len(svc2._route_groups) == 1
        rg = svc2._route_groups[0]
        assert isinstance(rg, RouteGroup)
        assert rg.id == 'htw_0'
        assert rg.name == 'Lakefront Commute'
        assert rg.direction == 'home_to_work'
        assert rg.frequency == 20
        assert rg.difficulty == 'Medium'
        assert len(rg.routes) == 1
        assert rg.representative_route.activity_id == 111
        assert rg.representative_route.coordinates == [(40.7128, -74.0060), (40.7589, -73.9851)]

        # Long rides
        assert len(svc2._long_rides) == 1
        lr = svc2._long_rides[0]
        assert isinstance(lr, LongRide)
        assert lr.activity_id == 222
        assert lr.name == 'Century Loop'
        assert lr.is_loop is True
        assert lr.uses == 3
        assert lr.activity_ids == [222, 223, 224]
        assert lr.activity_dates == ['2026-05-15', '2026-04-20', '2026-03-10']
        assert lr.activity_names == ['Century', 'Century v2', 'Century v3']
        assert lr.start_location == (41.0, -87.0)

        # Locations
        assert svc2._home_location.name == 'Home'
        assert svc2._home_location.lat == 40.7128
        assert svc2._work_location.name == 'Office'
        assert svc2._work_location.activity_count == 50

        # Analysis time
        assert svc2._last_analysis_time == datetime(2026, 6, 17, 12, 0, 0)


@pytest.mark.unit
class TestCacheLoadEdgeCases:
    """Test _load_from_cache edge cases and fallback paths."""

    def test_load_cache_failure_sets_loaded_flag(self, mock_config):
        """Failed cache load still marks as loaded to avoid retry loops."""
        service = AnalysisService()
        service._cache_loaded = False
        service.storage = Mock()
        service.storage.read = Mock(side_effect=Exception("disk error"))

        service._load_from_cache()
        assert service._cache_loaded is True

    def test_deserialization_fallback_for_route_groups(self, mock_config, tmp_path):
        """If route group deserialization fails, raw dicts are stored."""
        from src.json_storage import JSONStorage
        storage = JSONStorage(str(tmp_path / 'data'))

        bad_route_groups_data = {
            'route_groups': [{'id': 'x', 'bad_key': True}],
            'updated_at': datetime.now().isoformat()
        }
        storage.write('route_groups.json', bad_route_groups_data)
        storage.write('analysis_status.json', {})
        storage.write('long_rides.json', {})

        service = AnalysisService()
        service.storage = storage
        service._load_from_cache()

        assert service._route_groups is not None
        assert isinstance(service._route_groups[0], dict)

    def test_deserialization_fallback_for_long_rides(self, mock_config, tmp_path):
        """If long ride deserialization fails, raw dicts are stored."""
        from src.json_storage import JSONStorage
        storage = JSONStorage(str(tmp_path / 'data'))

        bad_long_rides_data = {
            'long_rides': [{'id': 'x', 'bad_key': True}],
            'updated_at': datetime.now().isoformat()
        }
        storage.write('long_rides.json', bad_long_rides_data)
        storage.write('analysis_status.json', {})
        storage.write('route_groups.json', {})

        service = AnalysisService()
        service.storage = storage
        service._load_from_cache()

        assert service._long_rides is not None
        assert isinstance(service._long_rides[0], dict)


@pytest.mark.unit
class TestRunFullAnalysisProgressCallbacks:
    """Test run_full_analysis progress callbacks and stop_check."""

    @patch('app.services.analysis_service.LocationFinder')
    @patch('app.services.analysis_service.LongRideAnalyzer')
    @patch('app.services.analysis_service.RouteAnalyzer')
    def test_on_progress_is_called(self, mock_route_analyzer_class,
                                    mock_long_ride_analyzer_class,
                                    mock_location_finder_class,
                                    analysis_service, mock_activity,
                                    mock_location):
        """on_progress callback should be invoked during analysis."""
        home, work = mock_location
        mock_data_fetcher = Mock()
        mock_data_fetcher.fetch_activities = Mock(return_value=[mock_activity])
        analysis_service._data_fetcher = mock_data_fetcher

        mock_location_finder_class.return_value.identify_home_work.return_value = (home, work)
        mock_route_analyzer_class.return_value.group_similar_routes.return_value = [Mock(routes=[])]
        mock_long_ride_analyzer_class.return_value.classify_activities.return_value = ([], [])
        mock_long_ride_analyzer_class.return_value.group_similar_rides.return_value = []

        progress_calls = []
        def on_progress(**kwargs):
            progress_calls.append(kwargs)

        result = analysis_service.run_full_analysis(on_progress=on_progress)
        assert result['status'] == 'success'
        assert len(progress_calls) > 0

    @patch('app.services.analysis_service.LocationFinder')
    @patch('app.services.analysis_service.LongRideAnalyzer')
    @patch('app.services.analysis_service.RouteAnalyzer')
    def test_stop_check_halts_analysis(self, mock_route_analyzer_class,
                                        mock_long_ride_analyzer_class,
                                        mock_location_finder_class,
                                        analysis_service, mock_activity,
                                        mock_location):
        """stop_check returning True should produce stopped status."""
        home, work = mock_location
        mock_data_fetcher = Mock()
        mock_data_fetcher.fetch_activities = Mock(return_value=[mock_activity])
        analysis_service._data_fetcher = mock_data_fetcher

        mock_location_finder_class.return_value.identify_home_work.return_value = (home, work)
        mock_route_analyzer_class.return_value.group_similar_routes.return_value = [Mock(routes=[])]

        result = analysis_service.run_full_analysis(stop_check=lambda: True)
        assert result['status'] == 'stopped'

