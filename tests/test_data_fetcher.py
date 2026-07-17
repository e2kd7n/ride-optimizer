"""
Unit tests for data_fetcher module.
"""
import json
import pytest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from src.data_fetcher import Activity, StravaDataFetcher


class TestActivity:
    """Test Activity dataclass."""
    
    def test_activity_creation(self):
        """Test creating an Activity instance."""
        activity = Activity(
            id=12345,
            name="Morning Commute",
            type="Ride",
            start_date="2024-01-01T08:00:00+00:00",
            distance=5000.0,
            moving_time=1200,
            elapsed_time=1300,
            total_elevation_gain=50.0,
            average_speed=4.17,
            max_speed=8.0,
            start_latlng=(41.8781, -87.6298),
            end_latlng=(41.8819, -87.6278),
            polyline="encoded_polyline"
        )
        
        assert activity.id == 12345
        assert activity.name == "Morning Commute"
        assert activity.distance == 5000.0
    
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
        mock_strava_activity.start_latlng = [41.8781, -87.6298]
        mock_strava_activity.end_latlng = [41.8819, -87.6278]
        mock_strava_activity.map = Mock()
        mock_strava_activity.map.summary_polyline = "summary_polyline"
        
        activity = Activity.from_strava_activity(mock_strava_activity)
        
        assert activity.id == 67890
        assert activity.name == "Evening Ride"
        assert activity.distance == 10000.0
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
            'start_latlng': [41.8781, -87.6298],
            'end_latlng': [41.8819, -87.6278],
            'polyline': 'test_polyline'
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
        fetcher = StravaDataFetcher(mock_client, mock_config, use_test_cache=True)
        
        assert fetcher.client == mock_client
        assert fetcher.config == mock_config
        assert hasattr(fetcher, 'cache_path')
    
    def test_decode_polyline(self, mock_client, mock_config):
        """Test polyline decoding."""
        fetcher = StravaDataFetcher(mock_client, mock_config, use_test_cache=True)
        
        # Simple polyline encoding for testing
        # This is a simplified test - real polylines are more complex
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        
        result = fetcher.decode_polyline(encoded)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(coord, tuple) and len(coord) == 2 for coord in result)
    
    def test_filter_commute_activities(self, mock_client, mock_config):
        """Test filtering commute activities."""
        fetcher = StravaDataFetcher(mock_client, mock_config, use_test_cache=True)
        
        activities = [
            Activity(
                id=1, name="Morning Commute", type="Ride",
                start_date=datetime.now(timezone.utc).isoformat(),
                distance=5000.0, moving_time=1200, elapsed_time=1300,
                total_elevation_gain=50.0, average_speed=4.17, max_speed=8.0,
                start_latlng=(41.8781, -87.6298),
                end_latlng=(41.8819, -87.6278),
                polyline="poly1"
            ),
            Activity(
                id=2, name="Long Ride", type="Ride",
                start_date=datetime.now(timezone.utc).isoformat(),
                distance=100000.0, moving_time=10000, elapsed_time=10100,
                total_elevation_gain=500.0, average_speed=10.0, max_speed=15.0,
                start_latlng=(41.8781, -87.6298),
                end_latlng=(41.9819, -87.7278),
                polyline="poly2"
            ),
            Activity(
                id=3, name="Evening Commute", type="Ride",
                start_date=datetime.now(timezone.utc).isoformat(),
                distance=3000.0, moving_time=600, elapsed_time=700,
                total_elevation_gain=20.0, average_speed=5.0, max_speed=7.0,
                start_latlng=(41.8819, -87.6278),
                end_latlng=(41.8781, -87.6298),
                polyline="poly3"
            ),
        ]
        
        commute_activities = fetcher.filter_commute_activities(activities)
        
        # Should filter based on commute keywords in name and distance range
        assert len(commute_activities) >= 1
        assert all('commute' in act.name.lower() or 'work' in act.name.lower() for act in commute_activities)
    
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_cache_activities(self, mock_open, mock_exists, mock_client, mock_config):
        """Test caching activities."""
        mock_exists.return_value = False
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        fetcher = StravaDataFetcher(mock_client, mock_config, use_test_cache=True)
        
        activities = [
            Activity(
                id=1, name="Test Commute", type="Ride",
                start_date=datetime.now(timezone.utc).isoformat(),
                distance=5000.0, moving_time=1200, elapsed_time=1300,
                total_elevation_gain=50.0, average_speed=4.17, max_speed=8.0,
                start_latlng=(41.8781, -87.6298),
                end_latlng=(41.8819, -87.6278),
                polyline="poly"
            )
        ]
        
        result = fetcher.cache_activities(activities)

        # Check for the actual keys returned by cache_activities
        assert 'new' in result
        assert 'total' in result
        assert result['total'] == 1


class TestActivityToDict:
    """Test Activity.to_dict() and round-trip serialization."""

    def test_to_dict_basic(self):
        activity = Activity(
            id=1, name="Test", type="Ride",
            start_date="2026-01-01T08:00:00+00:00",
            distance=5000.0, moving_time=1200, elapsed_time=1300,
            total_elevation_gain=50.0, average_speed=4.17, max_speed=8.0
        )
        d = activity.to_dict()
        assert d['id'] == 1
        assert d['name'] == "Test"
        assert d['distance'] == 5000.0

    def test_to_dict_and_from_dict_roundtrip(self):
        activity = Activity(
            id=99, name="Round Trip", type="Ride",
            start_date="2026-03-15T09:00:00+00:00",
            distance=12000.0, moving_time=2100, elapsed_time=2200,
            total_elevation_gain=110.0, average_speed=5.7, max_speed=9.0,
            start_latlng=(41.88, -87.63), end_latlng=(41.89, -87.62),
            polyline="test_poly", sport_type="GravelRide"
        )
        d = activity.to_dict()
        restored = Activity.from_dict(d)
        assert restored.id == activity.id
        assert restored.name == activity.name
        assert restored.sport_type == activity.sport_type
        assert restored.distance == activity.distance


class TestActivityFromStravaEdgeCases:
    """Edge cases for Activity.from_strava_activity()."""

    def _base_mock(self):
        m = Mock()
        m.id = 1
        m.name = "Ride"
        m.type = "Ride"
        m.sport_type = None
        m.start_date = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        m.distance = 5000.0
        m.moving_time = 1200
        m.elapsed_time = 1300
        m.total_elevation_gain = 50.0
        m.average_speed = 4.17
        m.max_speed = 8.0
        m.start_latlng = None
        m.end_latlng = None
        m.map = None
        return m

    def test_from_strava_with_sport_type(self):
        m = self._base_mock()
        sport = Mock()
        sport.root = "GravelRide"
        m.sport_type = sport
        act = Activity.from_strava_activity(m)
        assert act.sport_type == "GravelRide"

    def test_from_strava_no_map(self):
        m = self._base_mock()
        m.map = None
        act = Activity.from_strava_activity(m)
        assert act.polyline is None

    def test_from_strava_summary_polyline(self):
        m = self._base_mock()
        m.map = Mock()
        m.map.summary_polyline = "abc123"
        act = Activity.from_strava_activity(m)
        assert act.polyline == "abc123"

    def test_from_strava_detailed_polyline(self):
        m = self._base_mock()
        m.map = Mock()
        m.map.polyline = "detailed_poly"
        m.map.summary_polyline = "summary_poly"
        act = Activity.from_strava_activity(m, use_detailed_polyline=True)
        assert act.polyline == "detailed_poly"

    def test_from_strava_timedelta_moving_time(self):
        m = self._base_mock()
        m.moving_time = timedelta(seconds=2100)
        m.elapsed_time = timedelta(seconds=2200)
        act = Activity.from_strava_activity(m)
        assert act.moving_time == 2100
        assert act.elapsed_time == 2200

    def test_from_strava_missing_distance(self):
        m = self._base_mock()
        m.distance = None
        act = Activity.from_strava_activity(m)
        assert act.distance == 0.0

    def test_from_strava_missing_elevation(self):
        m = self._base_mock()
        m.total_elevation_gain = None
        act = Activity.from_strava_activity(m)
        assert act.total_elevation_gain == 0.0

    def test_from_strava_latlng_list(self):
        m = self._base_mock()
        m.start_latlng = [41.88, -87.63]
        m.end_latlng = [41.89, -87.62]
        act = Activity.from_strava_activity(m)
        assert act.start_latlng == (41.88, -87.63)
        assert act.end_latlng == (41.89, -87.62)


class TestActivityFromDictEdgeCases:
    """Edge cases for Activity.from_dict()."""

    def _base_dict(self):
        return {
            'id': 1, 'name': 'Test', 'type': 'Ride',
            'distance': 5000.0, 'moving_time': 1200, 'elapsed_time': 1300,
            'total_elevation_gain': 50.0, 'average_speed': 4.0, 'max_speed': 8.0
        }

    def test_from_dict_no_latlng(self):
        d = self._base_dict()
        d['start_latlng'] = None
        d['end_latlng'] = None
        act = Activity.from_dict(d)
        assert act.start_latlng is None

    def test_from_dict_simple_latlng(self):
        d = self._base_dict()
        d['start_latlng'] = [41.88, -87.63]
        act = Activity.from_dict(d)
        assert act.start_latlng == (41.88, -87.63)

    def test_from_dict_with_sport_type(self):
        d = self._base_dict()
        d['sport_type'] = "MountainBikeRide"
        act = Activity.from_dict(d)
        assert act.sport_type == "MountainBikeRide"

    def test_from_dict_missing_optional_fields(self):
        d = self._base_dict()
        # Missing all optional fields
        act = Activity.from_dict(d)
        assert act.polyline is None
        assert act.sport_type is None


class TestCacheManagement:
    """Test cache validity and persistence."""

    @pytest.fixture
    def fetcher(self, tmp_path):
        client = Mock()
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'data_fetching.cache_duration_days': 7,
            'data_fetching.max_activities': 500,
        }.get(key, default)
        f = StravaDataFetcher(client, config, use_test_cache=False)
        f.cache_path = tmp_path / "activities.json"
        return f

    def _write_cache(self, path, age_days=0, activities=None):
        ts = (datetime.now() - timedelta(days=age_days)).isoformat()
        acts = activities or [
            {'id': 1, 'name': 'A', 'type': 'Ride', 'distance': 5000.0,
             'moving_time': 1200, 'elapsed_time': 1300,
             'total_elevation_gain': 50.0, 'average_speed': 4.0, 'max_speed': 8.0}
        ]
        data = {'timestamp': ts, 'count': len(acts), 'activities': acts}
        path.write_text(json.dumps(data))

    def test_is_cache_valid_fresh(self, fetcher):
        self._write_cache(fetcher.cache_path, age_days=1)
        assert fetcher.is_cache_valid() is True

    def test_is_cache_valid_expired(self, fetcher):
        self._write_cache(fetcher.cache_path, age_days=10)
        assert fetcher.is_cache_valid() is False

    def test_is_cache_valid_missing(self, fetcher):
        assert fetcher.cache_path.exists() is False
        assert fetcher.is_cache_valid() is False

    def test_load_cached_activities(self, fetcher):
        self._write_cache(fetcher.cache_path, age_days=1)
        activities = fetcher.load_cached_activities()
        assert len(activities) == 1
        assert activities[0].id == 1

    def test_load_cached_activities_missing(self, fetcher):
        result = fetcher.load_cached_activities()
        assert result == []

    def test_cache_activities_new(self, fetcher):
        acts = [Activity(id=10, name="R", type="Ride", distance=1000.0,
                         moving_time=300, elapsed_time=310, total_elevation_gain=10.0,
                         average_speed=3.0, max_speed=5.0)]
        stats = fetcher.cache_activities(acts, merge=False)
        assert stats['new'] == 1
        assert stats['total'] == 1
        assert fetcher.cache_path.exists()

    def test_cache_activities_merge(self, fetcher):
        self._write_cache(fetcher.cache_path, age_days=0, activities=[
            {'id': 1, 'name': 'Old', 'type': 'Ride', 'distance': 1000.0,
             'moving_time': 300, 'elapsed_time': 310,
             'total_elevation_gain': 10.0, 'average_speed': 3.0, 'max_speed': 5.0}
        ])
        new_acts = [Activity(id=2, name="New", type="Ride", distance=2000.0,
                             moving_time=600, elapsed_time=620, total_elevation_gain=20.0,
                             average_speed=3.0, max_speed=5.0)]
        stats = fetcher.cache_activities(new_acts, merge=True)
        assert stats['new'] == 1
        assert stats['total'] == 2

    def test_cache_activities_update_existing(self, fetcher):
        self._write_cache(fetcher.cache_path, age_days=0, activities=[
            {'id': 5, 'name': 'Orig', 'type': 'Ride', 'distance': 1000.0,
             'moving_time': 300, 'elapsed_time': 310,
             'total_elevation_gain': 10.0, 'average_speed': 3.0, 'max_speed': 5.0}
        ])
        updated = [Activity(id=5, name="Updated", type="Ride", distance=1100.0,
                            moving_time=300, elapsed_time=310, total_elevation_gain=10.0,
                            average_speed=3.0, max_speed=5.0)]
        stats = fetcher.cache_activities(updated, merge=True)
        assert stats['updated'] == 1
        assert stats['total'] == 1

    def test_get_cache_age_days(self, fetcher):
        self._write_cache(fetcher.cache_path, age_days=3)
        age = fetcher._get_cache_age_days()
        assert 2.9 < age < 3.1

    def test_get_cache_age_days_missing(self, fetcher):
        assert fetcher._get_cache_age_days() == 0.0


class TestFetchActivities:
    """Test fetch_activities() with various scenarios."""

    @pytest.fixture
    def fetcher(self, tmp_path):
        client = Mock()
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'data_fetching.cache_duration_days': 7,
            'data_fetching.max_activities': 500,
            'route_filtering.min_distance_km': 1.0,
            'route_filtering.max_distance_km': 50.0,
            'route_filtering.activity_types': ['Ride'],
            'route_filtering.exclude_virtual': True,
        }.get(key, default)
        f = StravaDataFetcher(client, config, use_test_cache=False)
        f.cache_path = tmp_path / "activities.json"
        return f

    def _make_strava_activity(self, activity_id=1, distance=5000.0):
        m = Mock()
        m.id = activity_id
        m.name = f"Ride {activity_id}"
        m.type = "Ride"
        m.sport_type = None
        m.start_date = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
        m.start_date_local = None
        m.distance = distance
        m.moving_time = 1200
        m.elapsed_time = 1300
        m.total_elevation_gain = 50.0
        m.average_speed = 4.17
        m.max_speed = 8.0
        m.start_latlng = None
        m.end_latlng = None
        m.map = None
        return m

    def test_fetch_uses_cache_when_valid(self, fetcher, tmp_path):
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'count': 1,
            'activities': [
                {'id': 99, 'name': 'Cached', 'type': 'Ride', 'distance': 5000.0,
                 'moving_time': 1200, 'elapsed_time': 1300,
                 'total_elevation_gain': 50.0, 'average_speed': 4.0, 'max_speed': 8.0}
            ]
        }
        fetcher.cache_path.write_text(json.dumps(cache_data))
        result = fetcher.fetch_activities(use_cache=True)
        fetcher.client.get_activities.assert_not_called()
        assert len(result) == 1
        assert result[0].id == 99

    def test_fetch_bypasses_cache_when_use_cache_false(self, fetcher):
        fetcher.client.get_activities.return_value = [self._make_strava_activity(42)]
        result = fetcher.fetch_activities(use_cache=False)
        fetcher.client.get_activities.assert_called_once()
        assert len(result) == 1

    def test_fetch_calls_progress_callback(self, fetcher):
        fetcher.client.get_activities.return_value = [
            self._make_strava_activity(1), self._make_strava_activity(2)
        ]
        calls = []
        fetcher.fetch_activities(use_cache=False, progress_callback=lambda n: calls.append(n))
        assert calls == [1, 2]

    def test_fetch_with_limit(self, fetcher):
        fetcher.client.get_activities.return_value = [self._make_strava_activity(1)]
        fetcher.fetch_activities(use_cache=False, limit=10)
        fetcher.client.get_activities.assert_called_once()
        kwargs = fetcher.client.get_activities.call_args
        assert kwargs[1]['limit'] == 10 or kwargs[0][0] == 10

    def test_fetch_api_error_raises(self, fetcher):
        fetcher.client.get_activities.side_effect = RuntimeError("API down")
        with pytest.raises(RuntimeError, match="API down"):
            fetcher.fetch_activities(use_cache=False)

    def test_get_activity_details_success(self, fetcher):
        strava_act = self._make_strava_activity(77)
        strava_act.map = Mock()
        strava_act.map.polyline = "detailed"
        strava_act.map.summary_polyline = "summary"
        fetcher.client.get_activity.return_value = strava_act
        result = fetcher.get_activity_details(77)
        assert result is not None
        assert result.id == 77

    def test_get_activity_details_error_returns_none(self, fetcher):
        fetcher.client.get_activity.side_effect = RuntimeError("Not found")
        result = fetcher.get_activity_details(999)
        assert result is None

    def test_fetch_with_before_date_filters(self, fetcher):
        strava_act = self._make_strava_activity(1)
        strava_act.start_date = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
        fetcher.client.get_activities.return_value = [strava_act]
        before_date = datetime(2026, 5, 1, 0, 0)
        result = fetcher.fetch_activities(use_cache=False, before=before_date)
        assert len(result) == 0

    def test_fetch_with_before_date_includes(self, fetcher):
        strava_act = self._make_strava_activity(1)
        strava_act.start_date = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
        fetcher.client.get_activities.return_value = [strava_act]
        before_date = datetime(2026, 5, 1, 0, 0)
        result = fetcher.fetch_activities(use_cache=False, before=before_date)
        assert len(result) == 1

    def test_fetch_with_after_date(self, fetcher):
        strava_act = self._make_strava_activity(1)
        fetcher.client.get_activities.return_value = [strava_act]
        after_date = datetime(2026, 1, 1, 0, 0)
        result = fetcher.fetch_activities(use_cache=False, after=after_date)
        assert len(result) == 1

    def test_fetch_with_date_range(self, fetcher):
        strava_act = self._make_strava_activity(1)
        fetcher.client.get_activities.return_value = [strava_act]
        result = fetcher.fetch_activities(
            use_cache=False,
            after=datetime(2026, 1, 1),
            before=datetime(2026, 12, 31),
        )
        assert len(result) == 1

    def test_fetch_expired_cache_fetches_from_api(self, fetcher, tmp_path):
        cache_data = {
            'timestamp': (datetime.now() - timedelta(days=30)).isoformat(),
            'count': 1,
            'activities': [
                {'id': 99, 'name': 'Old', 'type': 'Ride', 'distance': 5000.0,
                 'moving_time': 1200, 'elapsed_time': 1300,
                 'total_elevation_gain': 50.0, 'average_speed': 4.0, 'max_speed': 8.0}
            ]
        }
        fetcher.cache_path.write_text(json.dumps(cache_data))
        strava_act = self._make_strava_activity(42)
        fetcher.client.get_activities.return_value = [strava_act]
        result = fetcher.fetch_activities(use_cache=True)
        fetcher.client.get_activities.assert_called_once()
        assert len(result) == 1


class TestFromStravaToSecondsEdgeCases:
    """Cover to_seconds branches: None, .seconds attribute, plain int."""

    def _base_mock(self):
        m = Mock()
        m.id = 1
        m.name = "Ride"
        m.type = "Ride"
        m.sport_type = None
        m.start_date = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        m.distance = 5000.0
        m.total_elevation_gain = 50.0
        m.average_speed = 4.0
        m.max_speed = 8.0
        m.start_latlng = None
        m.end_latlng = None
        m.map = None
        return m

    def test_moving_time_none(self):
        m = self._base_mock()
        m.moving_time = None
        m.elapsed_time = 1300
        act = Activity.from_strava_activity(m)
        assert act.moving_time == 0

    def test_time_with_seconds_attribute(self):
        m = self._base_mock()
        duration = Mock(spec=[])
        duration.seconds = 2500
        m.moving_time = duration
        m.elapsed_time = 2600
        act = Activity.from_strava_activity(m)
        assert act.moving_time == 2500

    def test_time_plain_int(self):
        m = self._base_mock()
        m.moving_time = 1800
        m.elapsed_time = 1900
        act = Activity.from_strava_activity(m)
        assert act.moving_time == 1800


class TestFromDictNestedLatlng:
    """Cover nested latlng extraction: [['root', [lat, lon]]]."""

    def _base_dict(self):
        return {
            'id': 1, 'name': 'Test', 'type': 'Ride',
            'distance': 5000.0, 'moving_time': 1200, 'elapsed_time': 1300,
            'total_elevation_gain': 50.0, 'average_speed': 4.0, 'max_speed': 8.0
        }

    def test_nested_latlng_structure(self):
        d = self._base_dict()
        d['start_latlng'] = [['root', [41.88, -87.63]]]
        d['end_latlng'] = [['root', [41.89, -87.62]]]
        act = Activity.from_dict(d)
        assert act.start_latlng == (41.88, -87.63)
        assert act.end_latlng == (41.89, -87.62)

    def test_nested_latlng_invalid_inner(self):
        d = self._base_dict()
        d['start_latlng'] = [['root', 'invalid']]
        act = Activity.from_dict(d)
        assert act.start_latlng is None

    def test_empty_list_latlng(self):
        d = self._base_dict()
        d['start_latlng'] = []
        act = Activity.from_dict(d)
        assert act.start_latlng == []


class TestEnrichActivities:
    """Test enrich_activities_with_detailed_polylines."""

    @pytest.fixture
    def fetcher(self, tmp_path):
        client = Mock()
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'data_fetching.cache_duration_days': 7,
            'data_fetching.max_activities': 500,
        }.get(key, default)
        f = StravaDataFetcher(client, config, use_test_cache=False)
        f.cache_path = tmp_path / "activities.json"
        return f

    def _make_strava_act(self, aid=1):
        m = Mock()
        m.id = aid
        m.name = "Ride"
        m.type = "Ride"
        m.sport_type = None
        m.start_date = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        m.distance = 5000.0
        m.moving_time = 1200
        m.elapsed_time = 1300
        m.total_elevation_gain = 50.0
        m.average_speed = 4.0
        m.max_speed = 8.0
        m.start_latlng = None
        m.end_latlng = None
        m.map = Mock()
        m.map.polyline = "detailed_poly"
        m.map.summary_polyline = "summary_poly"
        return m

    def test_enriches_polylines(self, fetcher):
        activity = Activity(
            id=1, name="Test", type="Ride",
            start_date="2026-01-01T08:00:00+00:00",
            distance=5000.0, moving_time=1200, elapsed_time=1300,
            total_elevation_gain=50.0, average_speed=4.0, max_speed=8.0,
            polyline="summary_only",
        )
        fetcher.client.get_activity.return_value = self._make_strava_act(1)
        result = fetcher.enrich_activities_with_detailed_polylines([activity])
        assert len(result) == 1
        assert result[0].polyline == "detailed_poly"

    def test_enrichment_failure_keeps_original(self, fetcher):
        activity = Activity(
            id=2, name="Test", type="Ride",
            start_date="2026-01-01T08:00:00+00:00",
            distance=5000.0, moving_time=1200, elapsed_time=1300,
            total_elevation_gain=50.0, average_speed=4.0, max_speed=8.0,
            polyline="original_poly",
        )
        fetcher.client.get_activity.side_effect = RuntimeError("API error")
        result = fetcher.enrich_activities_with_detailed_polylines([activity])
        assert len(result) == 1
        assert result[0].polyline == "original_poly"


class TestFilterCommuteEdgeCases:
    """Cover filter_commute_activities edge cases."""

    @pytest.fixture
    def fetcher(self, tmp_path):
        client = Mock()
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'data_fetching.cache_duration_days': 7,
            'data_fetching.max_activities': 500,
            'route_filtering.min_distance_km': 1.0,
            'route_filtering.max_distance_km': 50.0,
            'route_filtering.activity_types': ['Ride'],
            'route_filtering.exclude_virtual': True,
        }.get(key, default)
        f = StravaDataFetcher(client, config, use_test_cache=False)
        f.cache_path = tmp_path / "activities.json"
        return f

    def _make_act(self, **kwargs):
        defaults = dict(
            id=1, name="Commute", type="Ride",
            start_date=datetime.now(timezone.utc).isoformat(),
            distance=5000.0, moving_time=1200, elapsed_time=1300,
            total_elevation_gain=50.0, average_speed=4.0, max_speed=8.0,
            start_latlng=(41.88, -87.63), end_latlng=(41.89, -87.62),
            polyline="poly",
        )
        defaults.update(kwargs)
        return Activity(**defaults)

    def test_excludes_non_ride_type(self, fetcher):
        act = self._make_act(type="Run", name="Morning Commute")
        result = fetcher.filter_commute_activities([act])
        assert len(result) == 0

    def test_excludes_too_short(self, fetcher):
        act = self._make_act(distance=500.0, name="Morning Commute")
        result = fetcher.filter_commute_activities([act])
        assert len(result) == 0

    def test_excludes_too_long(self, fetcher):
        act = self._make_act(distance=60000.0, name="Morning Commute")
        result = fetcher.filter_commute_activities([act])
        assert len(result) == 0

    def test_excludes_no_gps(self, fetcher):
        act = self._make_act(start_latlng=None, end_latlng=None, name="Morning Commute")
        result = fetcher.filter_commute_activities([act])
        assert len(result) == 0

    def test_excludes_no_polyline(self, fetcher):
        act = self._make_act(polyline=None, name="Morning Commute")
        result = fetcher.filter_commute_activities([act])
        assert len(result) == 0

    def test_excludes_virtual(self, fetcher):
        act = self._make_act(name="Virtual Commute")
        result = fetcher.filter_commute_activities([act])
        assert len(result) == 0

    def test_includes_valid_commute(self, fetcher):
        act = self._make_act(name="Morning Commute")
        result = fetcher.filter_commute_activities([act])
        assert len(result) == 1


class TestGearMethods:
    """Test gear fetching, caching, and backfill."""

    @pytest.fixture
    def fetcher(self, tmp_path):
        client = Mock()
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'data_fetching.cache_duration_days': 7,
            'data_fetching.max_activities': 500,
        }.get(key, default)
        f = StravaDataFetcher(client, config, use_test_cache=False)
        f.cache_path = tmp_path / "activities.json"
        return f

    def test_fetch_athlete_gear(self, fetcher):
        bike = Mock()
        bike.id = "b123"
        bike.name = "Tarmac"
        bike.brand_name = "Specialized"
        bike.model_name = "SL7"
        bike.primary = True
        bike.distance = 5000.0
        shoe = Mock()
        shoe.id = "s456"
        shoe.name = "Pegasus"
        shoe.brand_name = "Nike"
        shoe.model_name = "40"
        shoe.primary = False
        shoe.distance = 1000.0
        athlete = Mock()
        athlete.bikes = [bike]
        athlete.shoes = [shoe]
        fetcher.client.get_athlete.return_value = athlete
        result = fetcher.fetch_athlete_gear()
        assert len(result['bikes']) == 1
        assert result['bikes'][0]['id'] == 'b123'
        assert result['bikes'][0]['name'] == 'Tarmac'
        assert result['bikes'][0]['primary'] is True
        assert len(result['shoes']) == 1
        assert result['shoes'][0]['id'] == 's456'

    def test_fetch_athlete_gear_error(self, fetcher):
        fetcher.client.get_athlete.side_effect = RuntimeError("Auth failed")
        with pytest.raises(RuntimeError):
            fetcher.fetch_athlete_gear()

    def test_load_cached_gear_missing(self, fetcher):
        result = fetcher.load_cached_gear()
        assert result is None

    def test_load_cached_gear_exists(self, fetcher):
        gear_data = {'timestamp': '2026-01-01', 'bikes': [], 'shoes': []}
        fetcher._gear_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(fetcher._gear_cache_path, 'w') as f:
            json.dump(gear_data, f)
        result = fetcher.load_cached_gear()
        assert result == gear_data

    def test_load_cached_gear_corrupt(self, fetcher):
        fetcher._gear_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(fetcher._gear_cache_path, 'w') as f:
            f.write("not json")
        result = fetcher.load_cached_gear()
        assert result is None

    def test_backfill_gear_ids_no_cache(self, fetcher):
        result = fetcher.backfill_gear_ids()
        assert result == {'updated': 0, 'skipped': 0, 'total_cached': 0}

    def test_backfill_gear_ids_all_have_gear(self, fetcher):
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'count': 1,
            'activities': [
                {'id': 1, 'name': 'R', 'type': 'Ride', 'distance': 5000.0,
                 'moving_time': 1200, 'elapsed_time': 1300,
                 'total_elevation_gain': 50.0, 'average_speed': 4.0,
                 'max_speed': 8.0, 'gear_id': 'b123'}
            ]
        }
        fetcher.cache_path.write_text(json.dumps(cache_data))
        result = fetcher.backfill_gear_ids()
        assert result['updated'] == 0
        assert result['skipped'] == 1

    def test_backfill_gear_ids_updates_missing(self, fetcher):
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'count': 1,
            'activities': [
                {'id': 1, 'name': 'R', 'type': 'Ride', 'distance': 5000.0,
                 'moving_time': 1200, 'elapsed_time': 1300,
                 'total_elevation_gain': 50.0, 'average_speed': 4.0,
                 'max_speed': 8.0}
            ]
        }
        fetcher.cache_path.write_text(json.dumps(cache_data))
        strava_act = Mock()
        strava_act.id = 1
        strava_act.gear_id = "b456"
        fetcher.client.get_activities.return_value = [strava_act]
        result = fetcher.backfill_gear_ids()
        assert result['updated'] == 1
        assert result['total_cached'] == 1

    def test_backfill_gear_ids_api_error(self, fetcher):
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'count': 1,
            'activities': [
                {'id': 1, 'name': 'R', 'type': 'Ride', 'distance': 5000.0,
                 'moving_time': 1200, 'elapsed_time': 1300,
                 'total_elevation_gain': 50.0, 'average_speed': 4.0,
                 'max_speed': 8.0}
            ]
        }
        fetcher.cache_path.write_text(json.dumps(cache_data))
        fetcher.client.get_activities.side_effect = RuntimeError("API error")
        with pytest.raises(RuntimeError):
            fetcher.backfill_gear_ids()

    def test_backfill_progress_callback(self, fetcher):
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'count': 1,
            'activities': [
                {'id': 1, 'name': 'R', 'type': 'Ride', 'distance': 5000.0,
                 'moving_time': 1200, 'elapsed_time': 1300,
                 'total_elevation_gain': 50.0, 'average_speed': 4.0,
                 'max_speed': 8.0}
            ]
        }
        fetcher.cache_path.write_text(json.dumps(cache_data))
        strava_act = Mock()
        strava_act.id = 1
        strava_act.gear_id = "b789"
        fetcher.client.get_activities.return_value = [strava_act]
        calls = []
        fetcher.backfill_gear_ids(progress_callback=lambda fetched, updated: calls.append((fetched, updated)))
        assert len(calls) >= 1


class TestBackfillFullHistory:
    """Test backfill_full_history() — issue #486 pagination-backward fix."""

    @pytest.fixture
    def fetcher(self, tmp_path):
        client = Mock()
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'data_fetching.cache_duration_days': 7,
            'data_fetching.max_activities': 500,
            'data_fetching.backfill_page_size': 200,
        }.get(key, default)
        f = StravaDataFetcher(client, config, use_test_cache=False)
        f.cache_path = tmp_path / "activities.json"
        return f

    def _make_strava_activity(self, activity_id, day):
        m = Mock()
        m.id = activity_id
        m.name = f"Ride {activity_id}"
        m.type = "Ride"
        m.sport_type = None
        m.start_date = datetime(2026, 1, day, 8, 0, tzinfo=timezone.utc)
        m.start_date_local = None
        m.distance = 5000.0
        m.moving_time = 1200
        m.elapsed_time = 1300
        m.total_elevation_gain = 50.0
        m.average_speed = 4.17
        m.max_speed = 8.0
        m.start_latlng = None
        m.end_latlng = None
        m.map = None
        return m

    @patch('src.data_fetcher.time.sleep')
    def test_stops_on_empty_page(self, mock_sleep, fetcher):
        # Two pages of activities, then Strava returns nothing further back.
        page1 = [self._make_strava_activity(i, day=20 - i) for i in range(5)]
        page2 = [self._make_strava_activity(i, day=10 - i) for i in range(5, 10)]
        fetcher.client.get_activities.side_effect = [page1, page2, []]

        result = fetcher.backfill_full_history()

        assert result['new_total'] == 10
        assert result['pages'] == 2
        assert fetcher.client.get_activities.call_count == 3
        cached = fetcher.load_cached_activities()
        assert len(cached) == 10

    @patch('src.data_fetcher.time.sleep')
    def test_stops_when_page_fully_cached(self, mock_sleep, fetcher):
        # Pre-seed the cache with an activity that the second page will re-fetch.
        page1 = [self._make_strava_activity(1, day=20)]
        page2 = [self._make_strava_activity(2, day=10)]  # already cached below
        fetcher.client.get_activities.side_effect = [page1, page2]

        from src.data_fetcher import Activity
        seeded = Activity(id=2, name="Cached", type="Ride", distance=5000.0,
                           moving_time=1200, elapsed_time=1300, total_elevation_gain=50.0,
                           average_speed=4.0, max_speed=8.0,
                           start_date=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc).isoformat())
        fetcher.cache_activities([seeded], merge=False)

        result = fetcher.backfill_full_history()

        # Page 1 (new activity id=1) merges; page 2 re-fetches the already-cached
        # id=2 with nothing new, so the loop stops after 2 pages without a 3rd call.
        assert result['pages'] == 2
        assert fetcher.client.get_activities.call_count == 2
        cached_ids = {a.id for a in fetcher.load_cached_activities()}
        assert cached_ids == {1, 2}

    @patch('src.data_fetcher.time.sleep')
    def test_merges_across_pages_no_duplicates(self, mock_sleep, fetcher):
        page1 = [self._make_strava_activity(1, day=20)]
        page2 = [self._make_strava_activity(2, day=10)]
        fetcher.client.get_activities.side_effect = [page1, page2, []]

        fetcher.backfill_full_history()

        cached = fetcher.load_cached_activities()
        assert sorted(a.id for a in cached) == [1, 2]

    @patch('src.data_fetcher.time.sleep')
    def test_respects_stop_check(self, mock_sleep, fetcher):
        result = fetcher.backfill_full_history(stop_check=lambda: True)

        assert result == {'new_total': 0, 'pages': 0}
        fetcher.client.get_activities.assert_not_called()

    @patch('src.data_fetcher.time.sleep')
    def test_api_error_propagates(self, mock_sleep, fetcher):
        fetcher.client.get_activities.side_effect = RuntimeError("API down")
        with pytest.raises(RuntimeError, match="API down"):
            fetcher.backfill_full_history()

    @patch('src.data_fetcher.time.sleep')
    def test_progress_callback_invoked(self, mock_sleep, fetcher):
        page1 = [self._make_strava_activity(1, day=20)]
        fetcher.client.get_activities.side_effect = [page1, []]
        calls = []
        fetcher.backfill_full_history(progress_callback=lambda new_total, pages, oldest: calls.append((new_total, pages)))
        assert calls == [(1, 1)]

