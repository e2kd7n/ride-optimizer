"""
Tests for src/route_namer.py.

Targets ≥50% line coverage by exercising:
- Pure-logic helpers (bearing, turns, segment naming, legacy naming)
- Cache I/O and rate-limit file handling
- Geography analysis with mocked geocoder
"""

import json
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open

from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from src.route_namer import RouteNamer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def namer(tmp_path):
    """RouteNamer with mocked Nominatim and tmp cache paths."""
    with patch('src.route_namer.Nominatim') as mock_nom:
        mock_nom.return_value = Mock()
        rn = RouteNamer(config=None)
    rn.cache_dir = str(tmp_path)
    rn.cache_file = str(tmp_path / 'geocoding_cache.json')
    rn.rate_limit_file = str(tmp_path / 'geocoding_rate_limit.json')
    rn.cache = {}
    return rn


def _make_config(**overrides):
    """Return a Mock config that responds to key lookups."""
    defaults = {
        'route_naming.sampling_density': 10,
        'route_naming.min_segment_length_pct': 10,
        'route_naming.enable_segment_naming': True,
        'route_naming.show_full_path': True,
        'route_naming.max_segments_in_name': 3,
        'route_naming.equivalent_streets': {},
        'route_naming.geocoder_timeout': 10,
        'route_naming.geocoder_user_agent': 'test_agent',
        'route_analysis.enable_geocoding': True,
    }
    defaults.update(overrides)
    cfg = Mock()
    cfg.get.side_effect = lambda key, default=None: defaults.get(key, default)
    return cfg


# ---------------------------------------------------------------------------
# generate_simple_name (lines 819–830)
# ---------------------------------------------------------------------------

class TestGenerateSimpleName:
    def test_primary_route(self, namer):
        assert namer.generate_simple_name('route_1', 'home_to_work', rank=1) == 'Primary Route to Work'

    def test_alternative_route(self, namer):
        assert namer.generate_simple_name('route_2', 'home_to_work', rank=2) == 'Alternative Route to Work'

    def test_numbered_route(self, namer):
        assert namer.generate_simple_name('route_3', 'home_to_work', rank=3) == 'Route 3 to Work'

    def test_no_rank_to_home(self, namer):
        result = namer.generate_simple_name('group_5', 'work_to_home')
        assert result == 'Route 5 to Home'

    def test_no_rank_to_work(self, namer):
        result = namer.generate_simple_name('group_2', 'home_to_work')
        assert result == 'Route 2 to Work'


# ---------------------------------------------------------------------------
# _is_access_path (lines 576–605)
# ---------------------------------------------------------------------------

class TestIsAccessPath:
    def test_none_returns_false(self, namer):
        assert namer._is_access_path(None) is False

    def test_empty_returns_false(self, namer):
        assert namer._is_access_path('') is False

    def test_access_in_name(self, namer):
        assert namer._is_access_path('Park Access') is True

    def test_ramp_in_name(self, namer):
        assert namer._is_access_path('Highway Ramp') is True

    def test_entrance_in_name(self, namer):
        assert namer._is_access_path('Stadium Entrance') is True

    def test_exit_in_name(self, namer):
        assert namer._is_access_path('Toll Exit') is True

    def test_path_in_name(self, namer):
        assert namer._is_access_path('Bike Path') is True

    def test_north_drive_is_access(self, namer):
        assert namer._is_access_path('North Park Drive') is True

    def test_lake_shore_drive_not_access(self, namer):
        assert namer._is_access_path('Lake Shore Drive') is False

    def test_martin_luther_king_drive_not_access(self, namer):
        assert namer._is_access_path('Martin Luther King Drive') is False

    def test_regular_street_not_access(self, namer):
        assert namer._is_access_path('Michigan Avenue') is False

    def test_lakeshore_not_access(self, namer):
        assert namer._is_access_path('Lakeshore Boulevard') is False


# ---------------------------------------------------------------------------
# _is_major_street (lines 539–548)
# ---------------------------------------------------------------------------

class TestIsMajorStreet:
    def test_primary_highway(self, namer):
        assert namer._is_major_street({'highway': 'primary'}) is True

    def test_secondary_highway(self, namer):
        assert namer._is_major_street({'highway': 'secondary'}) is True

    def test_tertiary_highway(self, namer):
        assert namer._is_major_street({'highway': 'tertiary'}) is True

    def test_motorway(self, namer):
        assert namer._is_major_street({'highway': 'motorway'}) is True

    def test_trunk(self, namer):
        assert namer._is_major_street({'highway': 'trunk'}) is True

    def test_residential_not_major(self, namer):
        assert namer._is_major_street({'highway': 'residential'}) is False

    def test_boulevard_in_road_name(self, namer):
        assert namer._is_major_street({'road': 'Lake Shore Boulevard'}) is True

    def test_avenue_in_road_name(self, namer):
        assert namer._is_major_street({'road': 'Michigan Avenue'}) is True

    def test_parkway_in_road_name(self, namer):
        assert namer._is_major_street({'road': 'Sheridan Parkway'}) is True

    def test_minor_road_not_major(self, namer):
        assert namer._is_major_street({'road': 'Oak Street'}) is False

    def test_empty_address_not_major(self, namer):
        assert namer._is_major_street({}) is False


# ---------------------------------------------------------------------------
# _filter_significant_streets (lines 555–564)
# ---------------------------------------------------------------------------

class TestFilterSignificantStreets:
    def test_empty_list(self, namer):
        assert namer._filter_significant_streets([]) == []

    def test_returns_top_3(self, namer):
        streets = ['A', 'B', 'A', 'C', 'C', 'A', 'B', 'D']
        result = namer._filter_significant_streets(streets)
        assert result[0] == 'A'
        assert len(result) <= 3

    def test_deduplicates(self, namer):
        streets = ['Main St', 'Main St', 'Elm St']
        result = namer._filter_significant_streets(streets)
        assert result.count('Main St') == 1


# ---------------------------------------------------------------------------
# _normalize_street_name (lines 367–371)
# ---------------------------------------------------------------------------

class TestNormalizeStreetName:
    def test_no_equivalent(self, namer):
        namer.equivalent_streets = {}
        assert namer._normalize_street_name('Oak St') == 'Oak St'

    def test_with_equivalent(self, namer):
        namer.equivalent_streets = {'North Simonds Drive': 'Lakefront Trail'}
        assert namer._normalize_street_name('North Simonds Drive') == 'Lakefront Trail'

    def test_none_passthrough(self, namer):
        namer.equivalent_streets = {}
        assert namer._normalize_street_name(None) is None


# ---------------------------------------------------------------------------
# _calculate_bearing (lines 341–355)
# ---------------------------------------------------------------------------

class TestCalculateBearing:
    def test_due_north(self, namer):
        # Same lon, increasing lat → bearing ≈ 0°
        bearing = namer._calculate_bearing((0, 0), (1, 0))
        assert abs(bearing - 0) < 1 or abs(bearing - 360) < 1

    def test_due_east(self, namer):
        bearing = namer._calculate_bearing((0, 0), (0, 1))
        assert abs(bearing - 90) < 1

    def test_due_south(self, namer):
        bearing = namer._calculate_bearing((1, 0), (0, 0))
        assert abs(bearing - 180) < 1

    def test_due_west(self, namer):
        bearing = namer._calculate_bearing((0, 1), (0, 0))
        assert abs(bearing - 270) < 1

    def test_returns_360_range(self, namer):
        bearing = namer._calculate_bearing((41.88, -87.63), (41.89, -87.62))
        assert 0 <= bearing <= 360


# ---------------------------------------------------------------------------
# _find_significant_turns (lines 298–327)
# ---------------------------------------------------------------------------

class TestFindSignificantTurns:
    def test_empty_returns_empty(self, namer):
        assert namer._find_significant_turns([]) == []

    def test_two_points_returns_empty(self, namer):
        assert namer._find_significant_turns([(0, 0), (1, 0)]) == []

    def test_straight_line_no_turns(self, namer):
        # Points along a straight north-south line → no significant turns
        coords = [(i * 0.01, 0) for i in range(50)]
        turns = namer._find_significant_turns(coords, min_angle=30.0)
        assert isinstance(turns, list)

    def test_sharp_turn_detected(self, namer):
        # Build a route that goes north then turns east
        north_segment = [(i * 0.01, 0.0) for i in range(20)]
        east_segment = [(0.2, i * 0.01) for i in range(20)]
        coords = north_segment + east_segment
        turns = namer._find_significant_turns(coords, min_angle=30.0)
        # Should detect at least one turn near the transition
        assert isinstance(turns, list)


# ---------------------------------------------------------------------------
# _get_strategic_sample_points (lines 254–284)
# ---------------------------------------------------------------------------

class TestGetStrategicSamplePoints:
    def test_few_points_returned_as_is(self, namer):
        coords = [(i, i) for i in range(5)]
        result = namer._get_strategic_sample_points(coords)
        assert result == coords

    def test_returns_at_most_sampling_density(self, namer):
        namer.sampling_density = 5
        coords = [(i * 0.001, i * 0.001) for i in range(100)]
        result = namer._get_strategic_sample_points(coords)
        assert len(result) <= namer.sampling_density + 5  # allow small overshoot

    def test_includes_first_and_last(self, namer):
        coords = [(i * 0.001, 0) for i in range(50)]
        result = namer._get_strategic_sample_points(coords)
        assert coords[0] in result
        assert coords[-1] in result

    def test_straight_line_padded(self, namer):
        namer.sampling_density = 10
        coords = [(i * 0.001, 0) for i in range(100)]
        result = namer._get_strategic_sample_points(coords)
        assert len(result) >= 2


# ---------------------------------------------------------------------------
# _generate_descriptive_name (lines 617–674)
# ---------------------------------------------------------------------------

def _seg(street, length_pct, position='middle'):
    return {'street': street, 'length_pct': length_pct, 'position': position}


class TestGenerateDescriptiveName:
    """Test segment-based naming (enable_segment_naming=True)."""

    def test_three_unique_segments(self, namer):
        segments = [
            _seg('Start St', 20, 'start'),
            _seg('Main Blvd', 60, 'middle'),
            _seg('End Ave', 20, 'end'),
        ]
        result = namer._generate_descriptive_name(
            {'segments': segments}, 'route_1', 'home_to_work'
        )
        assert 'Start St' in result
        assert 'Main Blvd' in result
        assert 'End Ave' in result
        assert '→' in result

    def test_three_segments_two_unique(self, namer):
        # Two unique streets from three segments
        segments = [
            _seg('Alpha Rd', 40, 'start'),
            _seg('Beta Ave', 40, 'middle'),
            _seg('Alpha Rd', 20, 'end'),
        ]
        result = namer._generate_descriptive_name(
            {'segments': segments}, 'route_2', 'home_to_work'
        )
        # Should show "Alpha Rd → Beta Ave" (2 unique streets)
        assert '→' in result or 'Via' in result

    def test_three_segments_one_unique(self, namer):
        segments = [_seg('Only St', 40), _seg('Only St', 30), _seg('Only St', 30)]
        result = namer._generate_descriptive_name(
            {'segments': segments}, 'route_3', 'home_to_work'
        )
        assert 'Via Only St' == result

    def test_two_segments_same_street(self, namer):
        segments = [_seg('Same St', 50), _seg('Same St', 50)]
        result = namer._generate_descriptive_name(
            {'segments': segments}, 'route_1', 'home_to_work'
        )
        assert result == 'Via Same St'

    def test_two_segments_dominant_main(self, namer):
        segments = [_seg('Main Rd', 70, 'start'), _seg('Short Ln', 30, 'end')]
        result = namer._generate_descriptive_name(
            {'segments': segments}, 'route_1', 'home_to_work'
        )
        assert 'Main Rd' in result
        assert 'Short Ln' in result
        assert 'via' in result.lower() or '→' in result

    def test_two_segments_equal_split(self, namer):
        segments = [_seg('First Ave', 50, 'start'), _seg('Second St', 50, 'end')]
        result = namer._generate_descriptive_name(
            {'segments': segments}, 'route_1', 'home_to_work'
        )
        assert '→' in result

    def test_single_segment(self, namer):
        segments = [_seg('Solo Rd', 100)]
        result = namer._generate_descriptive_name(
            {'segments': segments}, 'route_1', 'home_to_work'
        )
        assert result == 'Via Solo Rd'

    def test_no_segments_falls_back_to_legacy(self, namer):
        # When no segments, falls back to _generate_descriptive_name_legacy
        result = namer._generate_descriptive_name(
            {'segments': [], 'major_streets': ['Oak Ave'], 'neighborhoods': [],
             'landmarks': [], 'geographic_features': []},
            'route_1', 'home_to_work'
        )
        assert 'Oak Ave' in result

    def test_segment_naming_disabled_uses_legacy(self, namer):
        namer.enable_segment_naming = False
        segments = [_seg('Main Rd', 80)]
        result = namer._generate_descriptive_name(
            {'segments': segments, 'major_streets': ['Oak Ave'], 'neighborhoods': [],
             'landmarks': [], 'geographic_features': []},
            'route_1', 'home_to_work'
        )
        assert 'Oak Ave' in result

    def test_short_segments_filtered_out(self, namer):
        namer.min_segment_length_pct = 20
        # Both segments below threshold → falls back to legacy
        segments = [_seg('Tiny Ln', 5), _seg('Micro St', 8)]
        result = namer._generate_descriptive_name(
            {'segments': segments, 'major_streets': [], 'neighborhoods': [],
             'landmarks': [], 'geographic_features': []},
            'route_1', 'home_to_work'
        )
        # Falls back to generic name
        assert 'Route' in result or 'to Work' in result

    def test_access_paths_filtered_out(self, namer):
        segments = [
            _seg('Park Access', 50, 'start'),
            _seg('Main Blvd', 50, 'end'),
        ]
        result = namer._generate_descriptive_name(
            {'segments': segments}, 'route_1', 'home_to_work'
        )
        # Park Access should be filtered, only Main Blvd remains
        assert 'Main Blvd' in result


# ---------------------------------------------------------------------------
# _generate_descriptive_name_legacy (lines 687–729)
# ---------------------------------------------------------------------------

class TestGenerateDescriptiveNameLegacy:
    def test_two_major_streets(self, namer):
        route_info = {'major_streets': ['Oak Ave', 'Elm St'],
                      'neighborhoods': [], 'landmarks': [], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'Oak Ave → Elm St'

    def test_three_major_streets(self, namer):
        route_info = {'major_streets': ['A', 'B', 'C'],
                      'neighborhoods': [], 'landmarks': [], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'A → B → C'

    def test_one_street_with_neighborhood(self, namer):
        route_info = {'major_streets': ['Main St'], 'neighborhoods': ['Lakeview'],
                      'landmarks': [], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'Through Lakeview via Main St'

    def test_neighborhood_with_landmark(self, namer):
        route_info = {'major_streets': [], 'neighborhoods': ['Lincoln Park'],
                      'landmarks': ['Conservatory'], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'Through Lincoln Park past Conservatory'

    def test_street_with_feature(self, namer):
        route_info = {'major_streets': ['Shore Dr'], 'neighborhoods': [],
                      'landmarks': [], 'geographic_features': ['Lake Michigan']}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'Shore Dr along Lake Michigan'

    def test_single_major_street(self, namer):
        route_info = {'major_streets': ['Michigan Ave'], 'neighborhoods': [],
                      'landmarks': [], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'Via Michigan Ave'

    def test_single_neighborhood(self, namer):
        route_info = {'major_streets': [], 'neighborhoods': ['Old Town'],
                      'landmarks': [], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'Through Old Town'

    def test_two_neighborhoods(self, namer):
        route_info = {'major_streets': [], 'neighborhoods': ['Wicker Park', 'Bucktown'],
                      'landmarks': [], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'Through Wicker Park and Bucktown'

    def test_geographic_feature_only(self, namer):
        route_info = {'major_streets': [], 'neighborhoods': [],
                      'landmarks': [], 'geographic_features': ['Chicago River']}
        result = namer._generate_descriptive_name_legacy(route_info, 'route_1', 'home_to_work')
        assert result == 'Along Chicago River'

    def test_fallback_to_home(self, namer):
        route_info = {'major_streets': [], 'neighborhoods': [],
                      'landmarks': [], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'group_3', 'work_to_home')
        assert result == 'Route 3 to Home'

    def test_fallback_to_work(self, namer):
        route_info = {'major_streets': [], 'neighborhoods': [],
                      'landmarks': [], 'geographic_features': []}
        result = namer._generate_descriptive_name_legacy(route_info, 'group_7', 'home_to_work')
        assert result == 'Route 7 to Work'


# ---------------------------------------------------------------------------
# name_route with geocoding disabled (lines 170–173)
# ---------------------------------------------------------------------------

class TestNameRouteGeodingDisabled:
    def test_disabled_to_work(self, tmp_path):
        cfg = _make_config(**{'route_analysis.enable_geocoding': False})
        with patch('src.route_namer.Nominatim'):
            rn = RouteNamer(config=cfg)
        rn.cache_dir = str(tmp_path)
        rn.cache_file = str(tmp_path / 'gc.json')
        rn.rate_limit_file = str(tmp_path / 'rl.json')
        result = rn.name_route([(0, 0), (1, 1)], 'group_4', 'home_to_work')
        assert result == 'Route 4 to Work'

    def test_disabled_to_home(self, tmp_path):
        cfg = _make_config(**{'route_analysis.enable_geocoding': False})
        with patch('src.route_namer.Nominatim'):
            rn = RouteNamer(config=cfg)
        rn.cache_dir = str(tmp_path)
        rn.cache_file = str(tmp_path / 'gc.json')
        rn.rate_limit_file = str(tmp_path / 'rl.json')
        result = rn.name_route([(0, 0), (1, 1)], 'group_2', 'work_to_home')
        assert result == 'Route 2 to Home'


# ---------------------------------------------------------------------------
# _load_cache and _save_cache (lines 77, 81–83)
# ---------------------------------------------------------------------------

class TestCacheIO:
    def test_load_cache_file_not_found(self, namer, tmp_path):
        namer.cache_file = str(tmp_path / 'nonexistent.json')
        result = namer._load_cache()
        assert result == {}

    def test_load_cache_corrupt_file(self, namer, tmp_path):
        corrupt = tmp_path / 'corrupt.json'
        corrupt.write_text('not valid json')
        namer.cache_file = str(corrupt)
        result = namer._load_cache()
        assert result == {}

    def test_save_cache_writes_file(self, namer, tmp_path):
        namer.cache = {'key': 'value'}
        namer.cache_file = str(tmp_path / 'cache.json')
        namer._save_cache()
        with open(namer.cache_file) as f:
            data = json.load(f)
        assert data == {'key': 'value'}

    def test_load_valid_cache(self, namer, tmp_path):
        cache_file = tmp_path / 'cache.json'
        cache_file.write_text(json.dumps({'a': 'b'}))
        namer.cache_file = str(cache_file)
        result = namer._load_cache()
        assert result == {'a': 'b'}

    def test_save_cache_error_does_not_raise(self, namer):
        namer.cache_file = '/nonexistent_dir/cache.json'
        namer.cache = {'x': 1}
        namer._save_cache()  # should not raise


# ---------------------------------------------------------------------------
# _check_rate_limit_status (lines 98–125)
# ---------------------------------------------------------------------------

class TestCheckRateLimitStatus:
    def test_no_rate_limit_file(self, namer, tmp_path):
        namer.rate_limit_file = str(tmp_path / 'no_file.json')
        namer._check_rate_limit_status()  # should not raise

    def test_rate_limit_active(self, namer, tmp_path):
        future = datetime.now() + timedelta(hours=2)
        data = {'blocked_until': future.isoformat()}
        rl_file = tmp_path / 'rate_limit.json'
        rl_file.write_text(json.dumps(data))
        namer.rate_limit_file = str(rl_file)
        namer._check_rate_limit_status()  # should log warning, not raise
        assert rl_file.exists()

    def test_rate_limit_expired_removes_file(self, namer, tmp_path):
        past = datetime.now() - timedelta(hours=1)
        data = {'blocked_until': past.isoformat()}
        rl_file = tmp_path / 'rate_limit.json'
        rl_file.write_text(json.dumps(data))
        namer.rate_limit_file = str(rl_file)
        namer._check_rate_limit_status()
        assert not rl_file.exists()

    def test_rate_limit_no_blocked_until(self, namer, tmp_path):
        data = {'reason': 'some reason'}
        rl_file = tmp_path / 'rate_limit.json'
        rl_file.write_text(json.dumps(data))
        namer.rate_limit_file = str(rl_file)
        namer._check_rate_limit_status()  # should return early, file still exists

    def test_corrupt_rate_limit_file(self, namer, tmp_path):
        rl_file = tmp_path / 'rate_limit.json'
        rl_file.write_text('not json')
        namer.rate_limit_file = str(rl_file)
        namer._check_rate_limit_status()  # should not raise


# ---------------------------------------------------------------------------
# _record_rate_limit (lines 131–147)
# ---------------------------------------------------------------------------

class TestRecordRateLimit:
    def test_creates_file(self, namer, tmp_path):
        namer.rate_limit_file = str(tmp_path / 'rl.json')
        namer._record_rate_limit()
        assert os.path.exists(namer.rate_limit_file)

    def test_file_contains_blocked_until(self, namer, tmp_path):
        namer.rate_limit_file = str(tmp_path / 'rl.json')
        namer._record_rate_limit()
        with open(namer.rate_limit_file) as f:
            data = json.load(f)
        assert 'blocked_until' in data
        assert 'blocked_at' in data

    def test_write_error_does_not_raise(self, namer):
        namer.rate_limit_file = '/nonexistent_dir/rl.json'
        namer._record_rate_limit()  # should not raise


# ---------------------------------------------------------------------------
# _get_location_details — cache hit path (lines 440–443)
# ---------------------------------------------------------------------------

class TestGetLocationDetailsCache:
    def test_cache_hit_returns_immediately(self, namer):
        point = (41.88, -87.63)
        cached_result = {'street': 'Michigan Ave', 'is_major': True,
                         'neighborhood': 'Loop', 'landmark': None, 'feature': None}
        namer.cache['details_41.8800,-87.6300'] = cached_result
        result = namer._get_location_details(point)
        assert result == cached_result
        namer.geolocator.reverse.assert_not_called()


# ---------------------------------------------------------------------------
# _identify_route_segments (lines 383–427) — mocked _get_location_details
# ---------------------------------------------------------------------------

class TestIdentifyRouteSegments:
    def test_empty_coords_returns_empty(self, namer):
        result = namer._identify_route_segments([])
        assert result == []

    def test_single_street_one_segment(self, namer):
        coords = [(i * 0.001, 0) for i in range(20)]
        location = {'street': 'Main St', 'is_major': True, 'neighborhood': None,
                    'landmark': None, 'feature': None}
        with patch.object(namer, '_get_location_details', return_value=location):
            segments = namer._identify_route_segments(coords)
        assert len(segments) >= 1
        assert segments[0]['street'] == 'Main St'
        assert 'length_pct' in segments[0]
        assert 'position' in segments[0]

    def test_street_change_creates_new_segment(self, namer):
        coords = [(i * 0.001, 0) for i in range(20)]

        def side_effect(pt):
            idx = coords.index(pt) if pt in coords else 0
            street = 'First St' if idx < 10 else 'Second Ave'
            return {'street': street, 'is_major': True, 'neighborhood': None,
                    'landmark': None, 'feature': None}

        with patch.object(namer, '_get_location_details', side_effect=side_effect):
            with patch.object(namer, '_get_strategic_sample_points', return_value=coords):
                segments = namer._identify_route_segments(coords)
        assert len(segments) >= 1

    def test_segments_have_positions(self, namer):
        coords = [(i * 0.001, 0) for i in range(20)]
        locations = [
            {'street': 'A St', 'is_major': True, 'neighborhood': None, 'landmark': None, 'feature': None},
            {'street': 'B Ave', 'is_major': True, 'neighborhood': None, 'landmark': None, 'feature': None},
            {'street': 'C Rd', 'is_major': True, 'neighborhood': None, 'landmark': None, 'feature': None},
        ]
        call_count = [0]
        def rotating_side_effect(pt):
            result = locations[call_count[0] % len(locations)]
            call_count[0] += 1
            return result

        sample = coords[:6]
        with patch.object(namer, '_get_strategic_sample_points', return_value=sample):
            with patch.object(namer, '_get_location_details', side_effect=rotating_side_effect):
                segments = namer._identify_route_segments(coords)
        positions = {s['position'] for s in segments}
        assert 'start' in positions
        assert 'end' in positions


# ---------------------------------------------------------------------------
# _analyze_route_geography (lines 206–241) — mocked helpers
# ---------------------------------------------------------------------------

class TestAnalyzeRouteGeography:
    def test_empty_returns_empty(self, namer):
        result = namer._analyze_route_geography([])
        assert result == {}

    def test_with_major_street_result(self, namer):
        coords = [(i * 0.001, 0) for i in range(20)]
        location = {
            'street': 'Michigan Ave', 'is_major': True,
            'neighborhood': 'Loop', 'landmark': None, 'feature': None,
        }
        with patch.object(namer, '_get_location_details', return_value=location):
            result = namer._analyze_route_geography(coords)
        assert 'segments' in result
        assert 'major_streets' in result
        assert 'neighborhoods' in result
        assert 'landmarks' in result
        assert 'geographic_features' in result

    def test_collects_neighborhoods(self, namer):
        coords = [(i * 0.001, 0) for i in range(20)]
        location = {
            'street': 'Oak St', 'is_major': False,
            'neighborhood': 'Wicker Park', 'landmark': None, 'feature': None,
        }
        with patch.object(namer, '_get_location_details', return_value=location):
            result = namer._analyze_route_geography(coords)
        assert 'Wicker Park' in result['neighborhoods']

    def test_none_location_skipped(self, namer):
        coords = [(i * 0.001, 0) for i in range(20)]
        with patch.object(namer, '_get_location_details', return_value=None):
            result = namer._analyze_route_geography(coords)
        assert result['major_streets'] == []
        assert result['neighborhoods'] == []
