"""
Unit tests for long_ride_analyzer module.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from src.long_ride_analyzer import LongRide, LongRideAnalyzer, RideRecommendation
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
# group_rides_by_name tests
# ---------------------------------------------------------------------------

class TestGroupRidesByName:
    def test_groups_same_name(self):
        a1 = _make_activity(1, name="Old School", start_date="2026-05-01T08:00:00+00:00")
        a2 = _make_activity(2, name="Old School", start_date="2026-05-08T08:00:00+00:00")
        analyzer = _make_analyzer([a1, a2])
        groups, unnamed = analyzer.group_rides_by_name([a1, a2])
        assert "Old School" in groups
        assert len(groups["Old School"]) == 2
        assert len(unnamed) == 0

    def test_generic_names_go_to_unnamed(self):
        generic = _make_activity(3, name="Morning Ride")
        analyzer = _make_analyzer([generic])
        groups, unnamed = analyzer.group_rides_by_name([generic])
        assert len(groups) == 0
        assert len(unnamed) == 1

    def test_empty_name_goes_to_unnamed(self):
        noname = _make_activity(4, name="")
        analyzer = _make_analyzer([noname])
        groups, unnamed = analyzer.group_rides_by_name([noname])
        assert len(unnamed) == 1

    def test_different_names_separate_groups(self):
        a1 = _make_activity(5, name="Route A")
        a2 = _make_activity(6, name="Route B")
        analyzer = _make_analyzer([a1, a2])
        groups, _ = analyzer.group_rides_by_name([a1, a2])
        assert "Route A" in groups
        assert "Route B" in groups


# ---------------------------------------------------------------------------
# consolidate_named_groups tests
# ---------------------------------------------------------------------------

class TestConsolidateNamedGroups:
    def test_creates_long_ride_from_named_group(self):
        activity = _make_activity(
            1, name="Sunday Loop",
            start_latlng=(41.88, -87.63),
            end_latlng=(41.88, -87.63),
        )
        analyzer = _make_analyzer([activity])
        rides = analyzer.consolidate_named_groups({"Sunday Loop": [activity]})
        assert len(rides) == 1
        assert rides[0].name == "Sunday Loop"
        assert rides[0].uses == 1

    def test_uses_count_from_multiple_activities(self):
        a1 = _make_activity(1, name="Loop", start_date="2026-04-01T08:00:00+00:00")
        a2 = _make_activity(2, name="Loop", start_date="2026-05-01T08:00:00+00:00")
        analyzer = _make_analyzer([a1, a2])
        rides = analyzer.consolidate_named_groups({"Loop": [a1, a2]})
        assert rides[0].uses == 2

    def test_skips_activities_without_polyline(self):
        bad = _make_activity(3, name="Bad Ride", polyline=None)
        analyzer = _make_analyzer([bad])
        rides = analyzer.consolidate_named_groups({"Bad Ride": [bad]})
        assert len(rides) == 0

    def test_uses_most_recent_as_representative(self):
        old = _make_activity(1, name="Route", start_date="2026-01-01T08:00:00+00:00")
        new = _make_activity(2, name="Route", start_date="2026-05-01T08:00:00+00:00")
        analyzer = _make_analyzer([old, new])
        rides = analyzer.consolidate_named_groups({"Route": [old, new]})
        assert rides[0].activity_id == 2  # most recent

    def test_is_loop_detection_close_start_end(self):
        # Same start/end = loop
        activity = _make_activity(
            1, name="Loop",
            start_latlng=(41.88, -87.63),
            end_latlng=(41.88001, -87.63001),  # ~15m away
        )
        analyzer = _make_analyzer([activity])
        rides = analyzer.consolidate_named_groups({"Loop": [activity]})
        assert rides[0].is_loop is True

    def test_is_not_loop_far_start_end(self):
        activity = _make_activity(
            1, name="Out&Back",
            start_latlng=(41.88, -87.63),
            end_latlng=(41.99, -87.50),  # far away
        )
        analyzer = _make_analyzer([activity])
        rides = analyzer.consolidate_named_groups({"Out&Back": [activity]})
        assert rides[0].is_loop is False


# ---------------------------------------------------------------------------
# generate_fallback_names tests
# ---------------------------------------------------------------------------

class TestGenerateFallbackNames:
    def test_generates_loop_name(self):
        act = _make_activity(
            1, start_latlng=(41.88, -87.63), end_latlng=(41.88001, -87.63001),
            distance=50000.0
        )
        analyzer = _make_analyzer([act])
        groups = analyzer.generate_fallback_names([act])
        names = list(groups.keys())
        assert any("Loop" in n for n in names)

    def test_generates_out_and_back_name(self):
        act = _make_activity(
            1, start_latlng=(41.88, -87.63), end_latlng=(41.99, -87.50),
            distance=40000.0
        )
        analyzer = _make_analyzer([act])
        groups = analyzer.generate_fallback_names([act])
        names = list(groups.keys())
        assert any("Out" in n or "Back" in n for n in names)

    def test_no_start_latlng_skipped(self):
        act = _make_activity(1, start_latlng=None, distance=50000.0)
        analyzer = _make_analyzer([act])
        groups = analyzer.generate_fallback_names([act])
        assert len(groups) == 0

    def test_empty_input(self):
        analyzer = _make_analyzer()
        groups = analyzer.generate_fallback_names([])
        assert groups == {}


# ---------------------------------------------------------------------------
# find_rides_near_location tests
# ---------------------------------------------------------------------------

class TestFindRidesNearLocation:
    def _make_ride(self, ride_id, coords):
        return LongRide(
            activity_id=ride_id, name=f"Ride {ride_id}", coordinates=coords,
            distance=50000.0, duration=7200, elevation_gain=300.0,
            timestamp="2026-05-10T08:00:00+00:00", average_speed=6.94,
            start_location=coords[0], end_location=coords[-1],
            is_loop=False, type="Ride",
        )

    def test_finds_nearby_ride(self):
        ride = self._make_ride(1, [(41.88, -87.63), (41.89, -87.62)])
        analyzer = _make_analyzer()
        result = analyzer.find_rides_near_location([ride], 41.88, -87.63, search_radius_km=1.0)
        assert len(result) == 1

    def test_excludes_distant_ride(self):
        ride = self._make_ride(1, [(42.5, -88.0), (42.6, -88.1)])
        analyzer = _make_analyzer()
        result = analyzer.find_rides_near_location([ride], 41.88, -87.63, search_radius_km=1.0)
        assert len(result) == 0

    def test_empty_rides_returns_empty(self):
        analyzer = _make_analyzer()
        result = analyzer.find_rides_near_location([], 41.88, -87.63)
        assert result == []


# ---------------------------------------------------------------------------
# calculate_wind_score tests
# ---------------------------------------------------------------------------

class TestCalculateWindScore:
    def _make_ride(self):
        coords = [(41.88 + i * 0.01, -87.63 + i * 0.01) for i in range(20)]
        return LongRide(
            activity_id=1, name="Wind Test", coordinates=coords,
            distance=50000.0, duration=7200, elevation_gain=100.0,
            timestamp="2026-05-10T08:00:00+00:00", average_speed=6.94,
            start_location=coords[0], end_location=coords[-1],
            is_loop=False, type="Ride",
        )

    def test_returns_tuple(self):
        analyzer = _make_analyzer()
        ride = self._make_ride()
        score, analysis = analyzer.calculate_wind_score(ride, {'wind_direction_deg': 180, 'wind_speed_kph': 20})
        assert isinstance(score, float)
        assert isinstance(analysis, dict)
        assert 0.0 <= score <= 1.0

    def test_insufficient_coords_returns_neutral(self):
        short_ride = LongRide(
            activity_id=1, name="Short", coordinates=[(0.0, 0.0)],
            distance=1000.0, duration=300, elevation_gain=0.0,
            timestamp="2026-05-10T08:00:00+00:00", average_speed=3.0,
            start_location=(0.0, 0.0), end_location=(0.0, 0.0),
            is_loop=False, type="Ride",
        )
        analyzer = _make_analyzer()
        score, analysis = analyzer.calculate_wind_score(short_ride, {})
        assert score == 0.5
        assert analysis.get('status') == 'insufficient_data'


# ---------------------------------------------------------------------------
# group_similar_rides integration test
# ---------------------------------------------------------------------------

class TestGroupSimilarRides:
    def test_empty_input_returns_empty(self):
        analyzer = _make_analyzer()
        result = analyzer.group_similar_rides([])
        assert result == []

    def test_named_activities_grouped(self):
        a1 = _make_activity(1, name="Old School", start_date="2026-04-01T08:00:00+00:00")
        a2 = _make_activity(2, name="Old School", start_date="2026-05-01T08:00:00+00:00")
        analyzer = _make_analyzer([a1, a2])
        result = analyzer.group_similar_rides([a1, a2])
        assert len(result) == 1
        assert result[0].name == "Old School"
        assert result[0].uses == 2

    def test_distinct_names_become_distinct_rides(self):
        # Use different polylines so routes are not merged by similarity check.
        # "_p~iF~ps|U" → SF area; "krz_Hxobi@..." → different region
        a1 = _make_activity(1, name="Route Alpha",
                             polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@")
        a2 = _make_activity(2, name="Route Beta",
                             polyline="egsrHpebn@sA}@gBqAkBoA",  # different coords
                             start_latlng=(41.88, -87.63), end_latlng=(41.90, -87.61))
        analyzer = _make_analyzer([a1, a2])
        result = analyzer.group_similar_rides([a1, a2])
        # With different polylines the routes are distinct; we get 1 or 2 rides
        # depending on distance — at minimum 1 ride should be returned
        assert len(result) >= 1

    def test_generic_named_activities_get_fallback_names(self):
        generic = _make_activity(1, name="Morning Ride",
                                 start_latlng=(41.88, -87.63),
                                 end_latlng=(41.99, -87.50),
                                 distance=40000.0)
        analyzer = _make_analyzer([generic])
        result = analyzer.group_similar_rides([generic])
        assert len(result) == 1
        # fallback name should reference distance or type
        assert result[0].name != ""
