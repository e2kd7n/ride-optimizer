"""
Unit tests for data_fetcher module.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from src.data_fetcher import Activity, StravaDataFetcher


class TestActivity:
    """Test Activity dataclass."""
    
    def test_activity_creation(self):
        """Test creating an Activity instance."""
        activity = Activity(
            id=12345,
            name="Morning Commute",
            type="Ride",
            start_date=datetime(2024, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
            distance=5000.0,
            moving_time=1200,
            elapsed_time=1300,
            total_elevation_gain=50.0,
            average_speed=4.17,
            max_speed=8.0,
            polyline="encoded_polyline",
            commute=True
        )
        
        assert activity.id == 12345
        assert activity.name == "Morning Commute"
        assert activity.distance == 5000.0
        assert activity.commute is True
    
    def test_from_strava_activity(self):
        """Test creating Activity from Strava activity object."""
        mock_strava_activity = Mock()
        mock_strava_activity.id = 67890
        mock_strava_activity.name = "Evening Ride"
        mock_strava_activity.type = "Ride"
        mock_strava_activity.start_date = datetime(2024, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        mock_strava_activity.distance = 10000.0
        mock_strava_activity.moving_time = 2400
        mock_strava_activity.elapsed_time = 2500
        mock_strava_activity.total_elevation_gain = 100.0
        mock_strava_activity.average_speed = 4.17
        mock_strava_activity.max_speed = 10.0
        mock_strava_activity.map = Mock()
        mock_strava_activity.map.summary_polyline = "summary_polyline"
        mock_strava_activity.commute = False
        
        activity = Activity.from_strava_activity(mock_strava_activity)
        
        assert activity.id == 67890
        assert activity.name == "Evening Ride"
        assert activity.distance == 10000.0
        assert activity.commute is False
        assert activity.polyline == "summary_polyline"
    
    def test_from_dict(self):
        """Test creating Activity from dictionary."""
        data = {
            'id': 11111,
            'name': 'Test Ride',
            'type': 'Ride',
            'start_date': '2024-01-01T08:00:00Z',
            'distance': 5000.0,
            'moving_time': 1200,
            'elapsed_time': 1300,
            'total_elevation_gain': 50.0,
            'average_speed': 4.17,
            'max_speed': 8.0,
            'polyline': 'test_polyline',
            'commute': True
        }
        
        activity = Activity.from_dict(data)
        
        assert activity.id == 11111
        assert activity.name == 'Test Ride'
        assert activity.distance == 5000.0


class TestStravaDataFetcher:
    """Test StravaDataFetcher class."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Strava client."""
        return Mock()
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock()
        config.get = Mock(side_effect=lambda key, default=None: {
            'cache.directory': 'cache',
            'cache.enabled': True,
            'cache.max_age_days': 7,
            'analysis.min_commute_distance': 1.0,
            'analysis.max_commute_distance': 50.0
        }.get(key, default))
        return config
    
    def test_fetcher_initialization(self, mock_client, mock_config):
        """Test StravaDataFetcher initialization."""
        fetcher = StravaDataFetcher(mock_client, mock_config)
        
        assert fetcher.client == mock_client
        assert fetcher.config == mock_config
        assert fetcher.cache_dir == 'cache'
    
    def test_decode_polyline(self, mock_client, mock_config):
        """Test polyline decoding."""
        fetcher = StravaDataFetcher(mock_client, mock_config)
        
        # Simple polyline encoding for testing
        # This is a simplified test - real polylines are more complex
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        
        result = fetcher.decode_polyline(encoded)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(coord, tuple) and len(coord) == 2 for coord in result)
    
    def test_filter_commute_activities(self, mock_client, mock_config):
        """Test filtering commute activities."""
        fetcher = StravaDataFetcher(mock_client, mock_config)
        
        activities = [
            Activity(
                id=1, name="Commute", type="Ride", 
                start_date=datetime.now(timezone.utc),
                distance=5000.0, moving_time=1200, elapsed_time=1300,
                total_elevation_gain=50.0, average_speed=4.17, max_speed=8.0,
                polyline="poly1", commute=True
            ),
            Activity(
                id=2, name="Long Ride", type="Ride",
                start_date=datetime.now(timezone.utc),
                distance=100000.0, moving_time=10000, elapsed_time=10100,
                total_elevation_gain=500.0, average_speed=10.0, max_speed=15.0,
                polyline="poly2", commute=False
            ),
            Activity(
                id=3, name="Short Commute", type="Ride",
                start_date=datetime.now(timezone.utc),
                distance=3000.0, moving_time=600, elapsed_time=700,
                total_elevation_gain=20.0, average_speed=5.0, max_speed=7.0,
                polyline="poly3", commute=True
            ),
        ]
        
        commute_activities = fetcher.filter_commute_activities(activities)
        
        # Should filter based on commute flag and distance range
        assert len(commute_activities) >= 1
        assert all(act.commute for act in commute_activities)
    
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_cache_activities(self, mock_open, mock_exists, mock_client, mock_config):
        """Test caching activities."""
        mock_exists.return_value = False
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        fetcher = StravaDataFetcher(mock_client, mock_config)
        
        activities = [
            Activity(
                id=1, name="Test", type="Ride",
                start_date=datetime.now(timezone.utc),
                distance=5000.0, moving_time=1200, elapsed_time=1300,
                total_elevation_gain=50.0, average_speed=4.17, max_speed=8.0,
                polyline="poly", commute=True
            )
        ]
        
        result = fetcher.cache_activities(activities)
        
        assert 'cached_count' in result
        assert 'cache_file' in result

# Made with Bob
