"""
Unit tests for long_ride_analyzer module.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from src.long_ride_analyzer import LongRide, LongRideAnalyzer
from src.data_fetcher import Activity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_activity(
    activity_id=1,
    name="Weekend Ride",
    type_="Ride",
    sport_type="Ride",
    distance=50000.0,
    moving_time=7200,
    start_latlng=(41.88, -87.63),
    end_latlng=(41.89, -87.62),
    polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@",
    start_date="2026-05-10T08:00:00+00:00",
    elevation_gain=300.0,
):
    return Activity(
        id=activity_id,
        name=name,
        type=type_,
        sport_type=sport_type,
        start_date=start_date,
        distance=distance,
        moving_time=moving_time,
        elapsed_time=moving_time + 600,
        total_elevation_gain=elevation_gain,
        start_latlng=start_latlng,
        end_latlng=end_latlng,
        polyline=polyline,
        average_speed=distance / moving_time,
        max_speed=12.0,
    )


@pytest.fixture(autouse=True)
def _cache_dir(tmp_path, monkeypatch):
    # LongRideAnalyzer's default cache_dir is relative ("cache"): keep tests out of the repo's.
    monkeypatch.chdir(tmp_path)


def _make_analyzer(activities=None, min_distance_km=15):
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        'long_rides.min_distance_km': min_distance_km,
    }.get(key, default)
    return LongRideAnalyzer(activities or [], config)


# ---------------------------------------------------------------------------
# LongRide dataclass tests
# ---------------------------------------------------------------------------

class TestLongRide:
    def test_creation(self):
        ride = LongRide(
            activity_id=1,
            name="Test Loop",
            coordinates=[(41.88, -87.63), (41.89, -87.62), (41.88, -87.63)],
            distance=50000.0,
            duration=7200,
            elevation_gain=300.0,
            timestamp="2026-05-10T08:00:00+00:00",
            average_speed=6.94,
            start_location=(41.88, -87.63),
            end_location=(41.88, -87.63),
            is_loop=True,
            type="Ride",
        )
        assert ride.activity_id == 1
        assert ride.name == "Test Loop"
        assert ride.is_loop is True

    def test_distance_km(self):
        ride = LongRide(
            activity_id=1, name="R", coordinates=[],
            distance=72400.0, duration=10800, elevation_gain=600.0,
            timestamp="2026-05-10T08:00:00+00:00",
            average_speed=6.7, start_location=(0.0, 0.0), end_location=(0.0, 0.0),
            is_loop=False, type="Ride",
        )
        assert abs(ride.distance_km - 72.4) < 0.01

    def test_duration_hours(self):
        ride = LongRide(
            activity_id=1, name="R", coordinates=[],
            distance=50000.0, duration=10800, elevation_gain=300.0,
            timestamp="2026-05-10T08:00:00+00:00",
            average_speed=6.0, start_location=(0.0, 0.0), end_location=(0.0, 0.0),
            is_loop=False, type="Ride",
        )
        assert abs(ride.duration_hours - 3.0) < 0.01

    def test_midpoint_non_empty(self):
        coords = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
        ride = LongRide(
            activity_id=1, name="R", coordinates=coords,
            distance=50000.0, duration=7200, elevation_gain=0.0,
            timestamp="2026-05-10T08:00:00+00:00",
            average_speed=6.0, start_location=(0.0, 0.0), end_location=(2.0, 2.0),
            is_loop=False, type="Ride",
        )
        assert ride.midpoint == (1.0, 1.0)

    def test_midpoint_empty_coords_returns_start(self):
        ride = LongRide(
            activity_id=1, name="R", coordinates=[],
            distance=50000.0, duration=7200, elevation_gain=0.0,
            timestamp="2026-05-10T08:00:00+00:00",
            average_speed=6.0, start_location=(41.88, -87.63), end_location=(41.89, -87.62),
            is_loop=False, type="Ride",
        )
        assert ride.midpoint == (41.88, -87.63)

    def test_default_uses(self):
        ride = LongRide(
            activity_id=1, name="R", coordinates=[],
            distance=50000.0, duration=7200, elevation_gain=0.0,
            timestamp="2026-05-10T08:00:00+00:00",
            average_speed=6.0, start_location=(0.0, 0.0), end_location=(0.0, 0.0),
            is_loop=False, type="Ride",
        )
        assert ride.uses == 1


# ---------------------------------------------------------------------------
# classify_activities tests
# ---------------------------------------------------------------------------

class TestClassifyActivities:
    def test_filters_out_commutes(self):
        commute = _make_activity(1, name="Morning Commute", distance=10000.0)
        long_ride = _make_activity(2, name="Century Ride", distance=60000.0)
        analyzer = _make_analyzer([commute, long_ride])
        _, long_rides = analyzer.classify_activities([commute])
        ids = [r.id for r in long_rides]
        assert 1 not in ids
        assert 2 in ids

    def test_filters_out_virtual_ride_type(self):
        virtual = _make_activity(3, type_="VirtualRide", distance=40000.0)
        analyzer = _make_analyzer([virtual])
        _, long_rides = analyzer.classify_activities([])
        assert not any(r.id == 3 for r in long_rides)

    def test_filters_by_min_distance(self):
        short = _make_activity(4, distance=5000.0)   # 5 km < 15 km minimum
        long = _make_activity(5, distance=50000.0)
        analyzer = _make_analyzer([short, long], min_distance_km=15)
        _, long_rides = analyzer.classify_activities([])
        ids = [r.id for r in long_rides]
        assert 4 not in ids
        assert 5 in ids

    def test_filters_missing_gps(self):
        no_gps = _make_activity(6, polyline=None, start_latlng=None, end_latlng=None,
                                distance=50000.0)
        analyzer = _make_analyzer([no_gps])
        _, long_rides = analyzer.classify_activities([])
        assert not long_rides

    def test_filters_virtual_keywords_in_name(self):
        zwift = _make_activity(7, name="Zwift Race", distance=50000.0)
        analyzer = _make_analyzer([zwift])
        _, long_rides = analyzer.classify_activities([])
        assert not any(r.id == 7 for r in long_rides)

    def test_returns_correct_commutes(self):
        commute = _make_activity(10, distance=12000.0)
        analyzer = _make_analyzer([commute])
        commutes, _ = analyzer.classify_activities([commute])
        assert any(r.id == 10 for r in commutes)


# ---------------------------------------------------------------------------
# group_similar_rides integration test
# ---------------------------------------------------------------------------

class TestGroupSimilarRides:
    def test_empty_input_returns_empty(self):
        analyzer = _make_analyzer()
        result = analyzer.group_similar_rides([])
        assert result == []

    def test_same_named_identical_rides_grouped(self):
        a1 = _make_activity(1, name="Old School", start_date="2026-04-01T08:00:00+00:00")
        a2 = _make_activity(2, name="Old School", start_date="2026-05-01T08:00:00+00:00")
        analyzer = _make_analyzer([a1, a2])
        result = analyzer.group_similar_rides([a1, a2])
        assert len(result) == 1
        assert result[0].name == "Old School"
        assert result[0].uses == 2
        # Most recent first, as the route library expects.
        assert result[0].activity_ids == [2, 1]
        assert result[0].activity_dates == ["2026-05-01", "2026-04-01"]

    def test_distinct_tracks_become_distinct_rides(self):
        a1 = _make_activity(1, name="Route Alpha", polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@")
        a2 = _make_activity(2, name="Route Beta", polyline="egsrHpebn@sA}@gBqAkBoA",
                            start_latlng=(41.88, -87.63), end_latlng=(41.90, -87.61))
        result = _make_analyzer([a1, a2]).group_similar_rides([a1, a2])
        assert {r.activity_id for r in result} == {1, 2}

    def test_generic_named_ride_gets_fallback_name(self):
        generic = _make_activity(1, name="Morning Ride",
                                 start_latlng=(41.88, -87.63),
                                 end_latlng=(41.99, -87.50),
                                 distance=40000.0)
        result = _make_analyzer([generic]).group_similar_rides([generic])
        assert len(result) == 1
        assert result[0].name == "Point to Point (40.0km)"

    def test_loop_flag_from_start_and_end(self):
        loop = _make_activity(1, name="Loop", start_latlng=(41.88, -87.63),
                              end_latlng=(41.88001, -87.63001))  # ~15 m apart
        far = _make_activity(2, name="Out", start_latlng=(41.88, -87.63),
                             end_latlng=(41.99, -87.50), polyline="egsrHpebn@sA}@gBqAkBoA")
        by_id = {r.activity_id: r for r in _make_analyzer().group_similar_rides([loop, far])}
        assert by_id[1].is_loop is True and by_id[2].is_loop is False

    def test_undecodable_polyline_is_skipped(self):
        bad = _make_activity(1, polyline="")  # decodes to no points
        good = _make_activity(2)
        result = _make_analyzer().group_similar_rides([bad, good])
        assert [r.activity_id for r in result] == [2]

    def test_writes_cache_under_cache_dir(self, tmp_path):
        a1, a2 = _make_activity(1), _make_activity(2)
        config = Mock()
        config.get.side_effect = lambda key, default=None: default
        LongRideAnalyzer([], config, cache_dir=str(tmp_path / "c")).group_similar_rides([a1, a2])
        assert (tmp_path / "c" / "long_ride_similarity_cache.json").exists()
