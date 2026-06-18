"""
Unit tests for location_finder module.
"""
import pytest
from datetime import time, datetime, timezone
from unittest.mock import Mock

from src.location_finder import LocationFinder, Location


def _make_activity(activity_id, start_date, start_latlng, end_latlng, elapsed_time=1800):
    """Create a mock Activity with the fields LocationFinder uses."""
    a = Mock()
    a.id = activity_id
    a.start_date = start_date
    a.start_latlng = start_latlng
    a.end_latlng = end_latlng
    a.elapsed_time = elapsed_time
    return a


def _make_config(eps=0.002, min_samples=3):
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        'location_detection.clustering.eps': eps,
        'location_detection.clustering.min_samples': min_samples,
        'location_detection.time_windows.morning_start': '06:00',
        'location_detection.time_windows.morning_end': '10:00',
        'location_detection.time_windows.evening_start': '16:00',
        'location_detection.time_windows.evening_end': '20:00',
    }.get(key, default)
    return config


HOME = (40.7128, -74.0060)
WORK = (40.7589, -73.9851)


def _jitter(coord, delta=0.0001, i=0):
    return (coord[0] + delta * i, coord[1] + delta * i)


def _commute_activities(n=10):
    """Generate n morning+evening commute activities between HOME and WORK."""
    activities = []
    for i in range(n):
        activities.append(_make_activity(
            activity_id=i * 2,
            start_date=f"2024-06-{10+i:02d}T07:{30+i%10:02d}:00+00:00",
            start_latlng=_jitter(HOME, i=i),
            end_latlng=_jitter(WORK, i=i),
            elapsed_time=1800,
        ))
        activities.append(_make_activity(
            activity_id=i * 2 + 1,
            start_date=f"2024-06-{10+i:02d}T17:{30+i%10:02d}:00+00:00",
            start_latlng=_jitter(WORK, i=i),
            end_latlng=_jitter(HOME, i=i),
            elapsed_time=1800,
        ))
    return activities


class TestLocation:
    def test_location_dataclass(self):
        loc = Location(lat=40.7, lon=-74.0, name="Home", activity_count=10)
        assert loc.lat == 40.7
        assert loc.avg_departure_time is None
        assert loc.radius == 0.0


class TestExtractEndpoints:
    def test_extracts_start_and_end(self):
        activities = [_make_activity(
            1, "2024-01-01T08:00:00+00:00",
            (40.71, -74.00), (40.75, -73.98), 1800
        )]
        finder = LocationFinder(activities, _make_config())
        endpoints = finder.extract_endpoints()
        assert len(endpoints) == 2
        starts = [e for e in endpoints if e['type'] == 'start']
        ends = [e for e in endpoints if e['type'] == 'end']
        assert len(starts) == 1
        assert len(ends) == 1

    def test_skips_missing_latlng(self):
        a = _make_activity(1, "2024-01-01T08:00:00+00:00", None, None)
        finder = LocationFinder([a], _make_config())
        endpoints = finder.extract_endpoints()
        assert len(endpoints) == 0

    def test_skips_short_latlng(self):
        a = _make_activity(1, "2024-01-01T08:00:00+00:00", (40.0,), (40.0,))
        finder = LocationFinder([a], _make_config())
        assert len(finder.extract_endpoints()) == 0


class TestClusterLocations:
    def test_clusters_nearby_points(self):
        activities = _commute_activities(n=8)
        finder = LocationFinder(activities, _make_config(min_samples=3))
        endpoints = finder.extract_endpoints()
        clusters = finder.cluster_locations(endpoints)
        assert len(clusters) >= 2

    def test_raises_with_too_few_endpoints(self):
        activities = [_make_activity(
            1, "2024-01-01T08:00:00+00:00",
            (40.71, -74.00), (40.75, -73.98)
        )]
        finder = LocationFinder(activities, _make_config(min_samples=5))
        endpoints = finder.extract_endpoints()
        with pytest.raises(ValueError, match="at least"):
            finder.cluster_locations(endpoints)

    def test_cluster_stats_contain_expected_keys(self):
        activities = _commute_activities(n=8)
        finder = LocationFinder(activities, _make_config(min_samples=3))
        endpoints = finder.extract_endpoints()
        clusters = finder.cluster_locations(endpoints)
        for c in clusters:
            assert 'centroid' in c
            assert 'count' in c
            assert 'radius' in c
            assert 'avg_departure' in c
            assert 'avg_arrival' in c


class TestIdentifyHomeWork:
    def test_identifies_two_locations(self):
        activities = _commute_activities(n=10)
        finder = LocationFinder(activities, _make_config(min_samples=3))
        home, work = finder.identify_home_work()
        assert isinstance(home, Location)
        assert isinstance(work, Location)
        assert home.name == "Home"
        assert work.name == "Work"

    def test_raises_with_too_few_endpoints(self):
        activities = _commute_activities(n=2)
        finder = LocationFinder(activities, _make_config(min_samples=3))
        with pytest.raises(ValueError):
            finder.identify_home_work()


class TestClassifyHomeWork:
    def test_morning_departures_score_as_home(self):
        finder = LocationFinder([], _make_config())
        cluster_home = {
            'avg_departure': time(7, 30),
            'avg_arrival': time(18, 0),
        }
        cluster_work = {
            'avg_departure': time(17, 0),
            'avg_arrival': time(8, 30),
        }
        home, work = finder._classify_home_work(cluster_home, cluster_work)
        assert home is cluster_home

    def test_both_equal_scores_returns_second_as_home(self):
        finder = LocationFinder([], _make_config())
        c1 = {'avg_departure': None, 'avg_arrival': None}
        c2 = {'avg_departure': None, 'avg_arrival': None}
        home, work = finder._classify_home_work(c1, c2)
        assert home is c2


class TestParseTime:
    def test_parse_time(self):
        finder = LocationFinder([], _make_config())
        t = finder._parse_time("08:30")
        assert t == time(8, 30)


class TestGetLocationStatistics:
    def test_returns_expected_keys(self):
        loc = Location(lat=40.7, lon=-74.0, name="Home", activity_count=50,
                       avg_departure_time=time(7, 30), radius=150.0)
        finder = LocationFinder([], _make_config())
        stats = finder.get_location_statistics(loc)
        assert stats['name'] == "Home"
        assert stats['coordinates'] == (40.7, -74.0)
        assert stats['radius_meters'] == 150.0
        assert stats['avg_departure_time'] == "07:30:00"

    def test_none_times_returned_as_none(self):
        loc = Location(lat=0, lon=0, name="Work", activity_count=0)
        finder = LocationFinder([], _make_config())
        stats = finder.get_location_statistics(loc)
        assert stats['avg_departure_time'] is None
        assert stats['avg_arrival_time'] is None
