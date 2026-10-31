"""
Route-matching quality tests on synthetic tracks (#611, epic #616).

Each test drives the real RouteAnalyzer.group_similar_routes end to end with the
production config (config/config.yaml), so it keeps measuring behaviour through
the metric (#613), clustering (#614) and cache (#612) rewrites.

Known defects are marked xfail(strict=True) with the issue that fixes them: when
that fix lands the test XPASSes, strict mode fails the run, and the marker must be
removed in the same change. Real-data numbers live in scripts/matching_benchmark/.

Synthetic geometry sits at an arbitrary latitude of 42.5° (where cos(lat) matters)
far from any real ride; tracks are built in metres and converted to lat/lon.
"""
import itertools
import math
from pathlib import Path

import pytest

from src.config_manager import ConfigManager
from src.location_finder import Location
from src.route_analyzer import Route, RouteAnalyzer

pytestmark = pytest.mark.unit

LAT0, LON0 = 42.5, -100.0
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT0))
REPO = Path(__file__).resolve().parents[1]

# A 9 km staircase commute: alternating 1.5 km east / north legs, (north, east) metres.
STAIRCASE = [(0, 0), (0, 1500), (1500, 1500), (1500, 3000), (3000, 3000),
             (3000, 4500), (4500, 4500), (4500, 6000), (6000, 6000)]


# ---------------------------------------------------------------- helpers

def densify(waypoints, spacing=30.0):
    """Points every `spacing` metres along straight legs between waypoints."""
    pts = [waypoints[0]]
    for (n0, e0), (n1, e1) in zip(waypoints, waypoints[1:]):
        steps = max(1, int(math.hypot(n1 - n0, e1 - e0) // spacing))
        pts += [(n0 + (n1 - n0) * k / steps, e0 + (e1 - e0) * k / steps) for k in range(1, steps + 1)]
    return pts


def shift(points, north=0.0, east=0.0):
    return [(n + north, e + east) for n, e in points]


def mirror(points):
    """Reflect across the north-east diagonal: a north offset becomes an east offset."""
    return [(e, n) for n, e in points]


_next_id = itertools.count(1)


def route(points_m, direction='home_to_work'):
    coords = [(LAT0 + n / M_PER_DEG_LAT, LON0 + e / M_PER_DEG_LON) for n, e in points_m]
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points_m, points_m[1:]))
    r = Route(activity_id=next(_next_id), direction=direction, coordinates=coords,
              distance=length, duration=int(length / 5), elevation_gain=0.0,
              timestamp='2026-01-01T08:00:00+00:00', average_speed=5.0)
    r.compute_geometry()
    return r


class _Config:
    """Production config with optional per-test overrides."""

    _base = None

    def __init__(self, **overrides):
        if _Config._base is None:
            _Config._base = ConfigManager(str(REPO / 'config' / 'config.yaml'))
        self.overrides = overrides

    def get(self, key, default=None):
        if key in self.overrides:
            return self.overrides[key]
        return self._base.get(key, default)


def analyzer(cache_dir, config=None, force=True, stop_check=None):
    home = Location(lat=LAT0, lon=LON0, name='Home', activity_count=0)
    work = Location(lat=LAT0 + 0.05, lon=LON0 + 0.07, name='Work', activity_count=0)
    return RouteAnalyzer([], home, work, config or _Config(), n_workers=1,
                         force_reanalysis=force, cache_dir=cache_dir,
                         enable_geocoding=False, stop_check=stop_check)


def partition(groups):
    """Groups as a set of frozensets of activity IDs (order-free)."""
    return {frozenset(r.activity_id for r in g.routes) for g in groups}


def grouped_together(tmp_path, a, b):
    tmp_path.mkdir(parents=True, exist_ok=True)
    groups = analyzer(tmp_path / 'cache').group_similar_routes([a, b])
    return len(groups) == 1


# ---------------------------------------------------------------- sanity

class TestSanity:
    def test_identical_tracks_group(self, tmp_path):
        base = densify(STAIRCASE)
        assert grouped_together(tmp_path, route(base), route(base))

    def test_small_parallel_offset_groups(self, tmp_path):
        base = densify(STAIRCASE)
        assert grouped_together(tmp_path, route(base), route(shift(base, north=20, east=20)))

    def test_parallel_road_800m_away_is_separate(self, tmp_path):
        base = densify(STAIRCASE)
        assert not grouped_together(tmp_path, route(base), route(shift(base, north=800)))

    def test_different_route_same_endpoints_is_separate(self, tmp_path):
        # Same start and end, but north-then-east instead of the staircase.
        other = densify([(0, 0), (6000, 0), (6000, 6000)])
        assert not grouped_together(tmp_path, route(densify(STAIRCASE)), route(other))


# ---------------------------------------------------------------- metric (#613)

def test_north_and_east_offsets_decided_alike(tmp_path):
    """A ride d metres off must get the same verdict whether the offset is north or east.

    The second pair is the first reflected across the diagonal, so the geometry is
    congruent and any isotropic metric must decide both the same way.
    """
    base = densify(STAIRCASE)
    for d in (30, 60, 90, 110, 130, 160, 250):
        north = grouped_together(tmp_path / f'n{d}', route(base), route(shift(base, north=d)))
        east = grouped_together(tmp_path / f'e{d}', route(mirror(base)),
                                route(shift(mirror(base), east=d)))
        assert north == east, f'{d} m offset: north={north} east={east}'


def test_point_spacing_does_not_matter(tmp_path):
    dense = densify(STAIRCASE, spacing=10)
    sparse = densify(STAIRCASE, spacing=400)  # like a heavily simplified summary_polyline
    assert grouped_together(tmp_path, route(dense), route(sparse))


def test_start_and_end_250m_apart_still_match(tmp_path):
    base = densify(STAIRCASE)
    # Same ride, but starts on a side street 250 m south and parks 250 m further on.
    other = densify([(-250, 0)] + STAIRCASE + [(6250, 6000)])
    assert grouped_together(tmp_path, route(base), route(other))


def test_one_block_detour_still_matches(tmp_path):
    base = densify(STAIRCASE)
    # 140 m-deep, 200 m-long detour around a block on the second east leg.
    detour = (STAIRCASE[:3]
              + [(1500, 2200), (1640, 2200), (1640, 2400), (1500, 2400)]
              + STAIRCASE[3:])
    assert grouped_together(tmp_path, route(base), route(densify(detour)))


def test_single_gps_spike_still_matches(tmp_path):
    base = densify(STAIRCASE)
    spiked = list(base)
    k = len(spiked) // 2
    spiked[k] = (spiked[k][0] + 200, spiked[k][1])
    assert grouped_together(tmp_path, route(base), route(spiked))


# ---------------------------------------------------------------- clustering (#614)

def test_grouping_does_not_depend_on_input_order(tmp_path):
    # Five copies of one ride, each 35 m further north: neighbours match, the
    # outermost pair doesn't — the classic case where a pivot-based greedy pass
    # groups differently depending on which ride it happens to start from.
    base = densify(STAIRCASE)
    rides = [route(shift(base, north=k * 35)) for k in range(5)]
    results = set()
    for i, order in enumerate(itertools.islice(itertools.permutations(rides), 0, None, 17)):
        groups = analyzer(tmp_path / f'run{i}').group_similar_routes(list(order))
        results.add(frozenset(partition(groups)))
    assert len(results) == 1, f'{len(results)} different groupings across input orders'


def test_every_member_matches_its_representative(tmp_path):
    # The same 35 m steps: the outermost rides are 140 m apart, so grouping must
    # not chain them into one group through the rides between them.
    base = densify(STAIRCASE)
    rides = [route(shift(base, north=k * 35)) for k in range(5)]
    an = analyzer(tmp_path / 'cache')
    for g in an.group_similar_routes(rides):
        for r in g.routes:
            assert an._is_match(an.calculate_route_similarity(r, g.representative_route))


def test_group_id_stable_when_unrelated_ride_added(tmp_path):
    commute = route(densify(STAIRCASE))
    unrelated = route(shift(densify(STAIRCASE), north=3000))
    cache = tmp_path / 'cache'

    def id_of(groups, ride):
        return next(g.id for g in groups if ride.activity_id in {r.activity_id for r in g.routes})

    # The unrelated ride sorts first by activity ID, so positional IDs would shift.
    unrelated.activity_id, commute.activity_id = commute.activity_id, unrelated.activity_id
    before = id_of(analyzer(cache, force=False).group_similar_routes([commute]), commute)
    after = id_of(analyzer(cache, force=False).group_similar_routes([unrelated, commute]), commute)
    assert before == after


def test_group_ids_and_names_survive_a_full_recompute(tmp_path):
    base = densify(STAIRCASE)
    rides = [route(base), route(shift(base, north=20)), route(shift(base, north=2000))]
    cache = tmp_path / 'cache'
    first = analyzer(cache, force=False).group_similar_routes(rides)
    an = analyzer(cache, force=False)
    for g in an.groups_cache['groups']:
        g['name'] = f"Named {g['id']}"  # as background geocoding would
    an._save_groups_cache_with_ids([r.activity_id for r in rides], an._deserialize_groups(an.groups_cache['groups']))
    again = analyzer(cache, force=True).group_similar_routes(list(reversed(rides)))
    assert {(g.id, frozenset(r.activity_id for r in g.routes)) for g in again} \
        == {(g.id, frozenset(r.activity_id for r in g.routes)) for g in first}
    assert all(g.name == f'Named {g.id}' for g in again)


def test_incremental_run_matches_full_recompute(tmp_path):
    base = densify(STAIRCASE)
    old = [route(shift(base, north=k * 35)) for k in range(3)] + [route(shift(base, north=2000))]
    new = [route(shift(base, north=k * 35)) for k in (3, 4)] + [route(shift(base, north=2030))]
    cache = tmp_path / 'cache'
    analyzer(cache, force=False).group_similar_routes(old)
    incremental = analyzer(cache, force=False).group_similar_routes(old + new)
    full = analyzer(tmp_path / 'fresh').group_similar_routes(new + old)
    assert partition(incremental) == partition(full)


def test_plus_route_flags_are_recomputed(tmp_path):
    base = densify(STAIRCASE)
    rides = [route(base), route(base)]
    for r in rides:
        r.is_plus_route = True  # left over from an earlier run
    groups = analyzer(tmp_path / 'cache').group_similar_routes(rides)
    assert not any(g.is_plus_route for g in groups)
    assert not any(r.is_plus_route for g in groups for r in g.routes)


def test_cache_hit_keeps_ride_names_and_plus_labels(tmp_path):
    base = densify(STAIRCASE)
    rides = [route(base) for _ in range(3)]
    for r in rides:
        r.activity_name = 'Ride to work'
    rides[2].activity_name = 'Ride to work +'
    cache = tmp_path / 'cache'
    analyzer(cache, force=False).group_similar_routes(rides)
    (group,) = analyzer(cache, force=False).group_similar_routes(rides)
    by_id = {r.activity_id: r for r in group.routes}
    assert by_id[rides[2].activity_id].activity_name == 'Ride to work +'
    assert by_id[rides[2].activity_id].is_plus_route
    assert not by_id[rides[0].activity_id].is_plus_route


# ---------------------------------------------------------------- caches (#612)

def test_threshold_change_regroups(tmp_path):
    base = densify(STAIRCASE)
    a, b = route(base), route(shift(base, north=40))  # p95 deviation ~40 m
    cache = tmp_path / 'cache'
    loose = analyzer(cache, _Config(**{'route_analysis.max_p95_deviation_m': 100}), force=False)
    assert len(loose.group_similar_routes([a, b])) == 1
    # Constructed after the first run so it loads the cache that run wrote.
    strict = analyzer(cache, _Config(**{'route_analysis.max_p95_deviation_m': 30}), force=False)
    assert len(strict.group_similar_routes([a, b])) == 2


def test_stopped_run_does_not_lose_rides(tmp_path):
    base = densify(STAIRCASE)
    rides = [route(shift(base, north=k * 2000)) for k in range(3)]  # three distinct routes
    cache = tmp_path / 'cache'
    analyzer(cache, force=False, stop_check=lambda: True).group_similar_routes(rides)
    groups = analyzer(cache, force=False).group_similar_routes(rides)
    grouped = {r.activity_id for g in groups for r in g.routes}
    assert grouped == {r.activity_id for r in rides}


def test_direction_change_regroups(tmp_path):
    """A home/work change can flip a ride's direction without changing the activity set."""
    base = densify(STAIRCASE)
    a, b = route(base), route(shift(base, north=2000))
    cache = tmp_path / 'cache'
    analyzer(cache, force=False).group_similar_routes([a, b])
    b.direction = 'work_to_home'
    groups = analyzer(cache, force=False).group_similar_routes([a, b])
    assert {g.direction for g in groups if b.activity_id in {r.activity_id for r in g.routes}} \
        == {'work_to_home'}


def test_similarity_cache_from_older_version_is_discarded(tmp_path, monkeypatch):
    import src.route_analyzer as ra
    base = densify(STAIRCASE)
    a, b = route(base), route(shift(base, north=20))
    cache = tmp_path / 'cache'
    analyzer(cache).group_similar_routes([a, b])
    assert analyzer(cache).similarity_cache  # same version: reloaded
    monkeypatch.setattr(ra, 'SIMILARITY_CACHE_VERSION', ra.SIMILARITY_CACHE_VERSION + 1)
    assert analyzer(cache).similarity_cache == {}


def test_legacy_unversioned_similarity_cache_is_discarded(tmp_path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / 'route_similarity_cache.json').write_text('{"aaaa_bbbb": 0.91}')
    assert analyzer(cache).similarity_cache == {}


def test_prefilter_rejections_are_not_cached(tmp_path):
    base = densify(STAIRCASE)
    far = route(shift(base, north=5000))  # centroid far outside the prefilter radius
    an = analyzer(tmp_path / 'cache')
    an.group_similar_routes([route(base), far])
    assert an.similarity_cache == {}


# ---------------------------------------------------------------- long rides (#615)
#
# Driven through the real LongRideAnalyzer.group_similar_rides with the
# production config. Real-data numbers: scripts/matching_benchmark/run_long_ride_benchmark.py.

# A 27 km irregular loop (north, east metres), starting and ending at the origin.
LOOP = [(0, 0), (0, 4000), (3000, 6000), (7000, 6000), (9000, 3000), (8000, 0),
        (5000, -1500), (2000, -1500), (0, 0)]
# A 25 km point-to-point ride.
LINE = [(0, 0), (0, 5000), (4000, 5000), (4000, 12000), (10000, 12000), (10000, 15000)]


def rotate_loop(points, start):
    """The same closed loop, started `start` points further round."""
    ring = points[:-1]
    ring = ring[start:] + ring[:start]
    return ring + [ring[0]]


def cut(points, from_m, to_m):
    """The points of a (densified) track between two distances along it, in metres."""
    out, travelled = [], 0.0
    for k, p in enumerate(points):
        if k:
            travelled += math.hypot(p[0] - points[k - 1][0], p[1] - points[k - 1][1])
        if from_m <= travelled <= to_m:
            out.append(p)
    return out


def long_ride(points_m, name='Morning Ride', ride_id=None):
    import polyline
    from src.data_fetcher import Activity
    coords = [(LAT0 + n / M_PER_DEG_LAT, LON0 + e / M_PER_DEG_LON) for n, e in points_m]
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points_m, points_m[1:]))
    rid = ride_id or next(_next_id)
    return Activity(id=rid, name=name, type='Ride', sport_type='Ride',
                    start_date=f'2026-01-{1 + rid % 28:02d}T08:00:00+00:00',
                    distance=length, moving_time=int(length / 7), elapsed_time=int(length / 6),
                    total_elevation_gain=0.0, start_latlng=coords[0], end_latlng=coords[-1],
                    polyline=polyline.encode(coords), average_speed=7.0, max_speed=12.0)


def long_groups(tmp_path, rides, **overrides):
    from src.long_ride_analyzer import LongRideAnalyzer
    tmp_path.mkdir(parents=True, exist_ok=True)
    return LongRideAnalyzer(rides, _Config(**overrides),
                            cache_dir=str(tmp_path / 'cache')).group_similar_rides(rides)


def long_partition(groups):
    return {frozenset(g.activity_ids) for g in groups}


def same_long_route(tmp_path, a, b):
    return len(long_groups(tmp_path, [a, b])) == 1


class TestLongRideInvariance:
    def test_loop_ridden_in_reverse_matches(self, tmp_path):
        loop = densify(LOOP)
        assert same_long_route(tmp_path, long_ride(loop), long_ride(loop[::-1]))

    def test_loop_started_elsewhere_matches(self, tmp_path):
        # Started at the fourth corner, about 12 km further round.
        assert same_long_route(tmp_path, long_ride(densify(LOOP)),
                               long_ride(densify(rotate_loop(LOOP, 3))))

    def test_loop_reversed_and_started_elsewhere_matches(self, tmp_path):
        other = densify(rotate_loop(LOOP, 5))[::-1]
        assert same_long_route(tmp_path, long_ride(densify(LOOP)), long_ride(other))

    def test_point_spacing_does_not_matter(self, tmp_path):
        assert same_long_route(tmp_path, long_ride(densify(LOOP, spacing=10)),
                               long_ride(densify(LOOP, spacing=500)))


class TestLongRideSeparation:
    def test_parallel_road_400m_away_is_separate(self, tmp_path):
        # The old 1.2 km average merged roads up to 1.2 km apart (L1).
        loop = densify(LOOP)
        assert not same_long_route(tmp_path, long_ride(loop), long_ride(shift(loop, east=400)))

    def test_same_name_on_different_geometry_is_not_merged(self, tmp_path):
        # Same Strava name, but a different loop 3 km away (L4).
        a = long_ride(densify(LOOP), name='Saturday Loop')
        b = long_ride(shift(densify(LOOP), north=3000, east=3000), name='Saturday Loop')
        groups = long_groups(tmp_path, [a, b])
        assert long_partition(groups) == {frozenset({a.id}), frozenset({b.id})}

    def test_unnamed_loops_of_the_same_length_are_separate(self, tmp_path):
        # Two different 27 km loops, both "Morning Ride": the old distance-string
        # fallback bucketed them together (L6).
        a = long_ride(densify(LOOP))
        b = long_ride(shift(densify(LOOP), north=20000))
        assert not same_long_route(tmp_path, a, b)


class TestLongRideNames:
    def test_different_names_on_one_route_merge(self, tmp_path):
        loop = densify(LOOP)
        groups = long_groups(tmp_path, [long_ride(loop, name='Old School'),
                                        long_ride(loop, name='Old School'),
                                        long_ride(shift(loop, north=20), name='Old School w/ friends')])
        assert len(groups) == 1
        assert groups[0].name == 'Old School'  # the most common name

    def test_shared_name_lowers_the_bar_but_needs_geometry(self, tmp_path):
        # The second ride cuts a corner of the loop, so only about 77% of each
        # lies along the other: too different on geometry alone, close enough
        # with a shared name (name_min_coverage).
        loop = densify(LOOP)
        variant = densify(LOOP[:4] + [(8000, 4000)] + LOOP[5:])
        assert not same_long_route(tmp_path / 'unnamed', long_ride(loop), long_ride(variant))
        assert same_long_route(tmp_path / 'named', long_ride(loop, name='Lake Loop'),
                               long_ride(variant, name='lake  loop'))

    def test_unnamed_rides_cluster_with_each_other(self, tmp_path):
        # Generic Strava names used to stay one group per ride unless a named
        # group happened to match them (L5).
        loop = densify(LOOP)
        rides = [long_ride(loop, name=n) for n in
                 ('Morning Ride', 'Night Ride', 'Afternoon Gravel Ride', '')]
        groups = long_groups(tmp_path, rides)
        assert len(groups) == 1 and groups[0].uses == 4
        assert groups[0].name == 'Loop Ride (27.2km)'

    @pytest.mark.parametrize('name,generic', [
        ('Morning Ride', True), ('Night Ride', True), ('Morning Gravel Ride', True),
        ('Evening Mountain Bike Ride', True), ('Lunch E-Bike Ride', True), ('', True),
        ('Gravel Ride', True), ('xXx Team Ride', False), ('Old School', False),
        ('Night Ride to the Lake', False),
    ])
    def test_generic_names(self, name, generic):
        from src.long_ride_analyzer import LongRideAnalyzer
        assert LongRideAnalyzer([], _Config()).is_generic_name(name) is generic

    def test_extra_generic_names_from_config(self):
        from src.long_ride_analyzer import LongRideAnalyzer
        an = LongRideAnalyzer([], _Config(**{'long_rides.generic_names': ['Radfahrt am Morgen']}))
        assert an.is_generic_name('radfahrt am morgen')

    def test_fallback_name_describes_the_shape(self, tmp_path):
        line = densify(LINE)
        out_and_back = line + line[::-1][1:]
        names = {g.name for g in long_groups(tmp_path, [long_ride(line), long_ride(out_and_back)])}
        assert names == {'Point to Point (25.0km)', 'Out & Back (50.0km)'}


class TestLongRideLinks:
    def test_sub_segment_is_linked_not_merged(self, tmp_path):
        # A 15 km piece of a 25 km ride (L3).
        whole = long_ride(densify(LINE))
        part = long_ride(cut(densify(LINE), 5000, 20000))
        by_id = {g.activity_id: g for g in long_groups(tmp_path, [whole, part])}
        assert set(by_id) == {whole.id, part.id}
        assert by_id[part.id].part_of == [whole.id]
        assert by_id[whole.id].contains == [part.id]

    def test_extension_is_linked_not_merged(self, tmp_path):
        # The 25 km ride, and the same ride carrying on for another 15 km.
        base = long_ride(densify(LINE))
        extended = long_ride(densify(LINE + [(10000, 25000), (15000, 25000)]))
        by_id = {g.activity_id: g for g in long_groups(tmp_path, [base, extended])}
        assert by_id[base.id].part_of == [extended.id]
        assert by_id[extended.id].contains == [base.id]


class TestLongRideVariants:
    def test_longer_turnaround_is_the_same_route(self, tmp_path):
        # A 50 km out-and-back vs the same ride turning 2 km further on: the old
        # rule scored it 2.0 km and rejected it while merging parallel roads (L1).
        line = densify(LINE)
        longer = densify(LINE + [(12000, 15000)])
        assert same_long_route(tmp_path, long_ride(line + line[::-1][1:]),
                               long_ride(longer + longer[::-1][1:]))

    def test_short_detour_is_the_same_route(self, tmp_path):
        loop = densify(LOOP)
        # An 800 m-deep detour off the first leg (about 6% of the loop).
        detour = densify(LOOP[:1] + [(0, 1000), (-800, 1000), (-800, 1600), (0, 1600)] + LOOP[1:])
        assert same_long_route(tmp_path, long_ride(loop), long_ride(detour))

    def test_one_way_and_out_and_back_are_separate_but_linked(self, tmp_path):
        # The same road, once vs there and back: coverage alone can't tell them apart.
        line = densify(LINE)
        one_way, there_and_back = long_ride(line), long_ride(line + line[::-1][1:])
        by_id = {g.activity_id: g for g in long_groups(tmp_path, [one_way, there_and_back])}
        assert set(by_id) == {one_way.id, there_and_back.id}
        assert by_id[one_way.id].part_of == [there_and_back.id]

    def test_unrelated_routes_are_not_linked(self, tmp_path):
        groups = long_groups(tmp_path, [long_ride(densify(LOOP)),
                                        long_ride(shift(densify(LOOP), north=20000))])
        assert not any(g.part_of or g.contains for g in groups)


class TestLongRideClustering:
    def test_grouping_does_not_depend_on_input_order(self, tmp_path):
        loop = densify(LOOP)
        rides = ([long_ride(shift(loop, north=k * 35)) for k in range(4)]
                 + [long_ride(densify(LINE), name='Line')])
        results = set()
        for i, order in enumerate(itertools.islice(itertools.permutations(rides), 0, None, 23)):
            groups = long_groups(tmp_path / f'run{i}', list(order))
            results.add(frozenset((g.activity_id, frozenset(g.activity_ids)) for g in groups))
        assert len(results) == 1

    def test_every_member_matches_its_representative(self, tmp_path):
        # 30 m steps: neighbours are within the 50 m coverage radius, the
        # outermost loops (90 m apart) aren't, so they mustn't chain together.
        import polyline
        from src.route_comparison import track_deviation_metrics
        loop = densify(LOOP)
        rides = {r.id: r for r in (long_ride(shift(loop, north=k * 30)) for k in range(4))}
        groups = long_groups(tmp_path, list(rides.values()))
        assert len(groups) > 1
        for g in groups:
            rep = polyline.decode(rides[g.activity_id].polyline)
            for aid in g.activity_ids:
                _, cov = track_deviation_metrics(polyline.decode(rides[aid].polyline), rep)
                assert cov >= 0.85


class TestLongRideCache:
    def test_metrics_are_cached_and_reused(self, tmp_path, monkeypatch):
        import src.long_ride_analyzer as lra
        loop = densify(LOOP)
        rides = [long_ride(loop), long_ride(shift(loop, north=20))]
        long_groups(tmp_path, rides)
        calls = []
        monkeypatch.setattr(lra, 'directed_deviation_metrics',
                            lambda *a: calls.append(1) or (0.0, 1.0, 0.0, 1.0))
        assert len(long_groups(tmp_path, list(reversed(rides)))) == 1
        assert calls == []

    def test_legacy_cache_is_discarded(self, tmp_path):
        from src.long_ride_analyzer import LongRideAnalyzer
        cache = tmp_path / 'cache'
        cache.mkdir()
        (cache / 'long_ride_similarity_cache.json').write_text('{"1:2": Infinity}')
        assert LongRideAnalyzer([], _Config(), cache_dir=str(cache))._similarity_cache == {}

    def test_failed_comparison_is_no_match_and_not_cached(self, tmp_path, monkeypatch):
        import src.long_ride_analyzer as lra

        def boom(*a):
            raise ValueError('bad track')
        monkeypatch.setattr(lra, 'directed_deviation_metrics', boom)
        loop = densify(LOOP)
        an = lra.LongRideAnalyzer([], _Config(), cache_dir=str(tmp_path / 'cache'))
        groups = an.group_similar_rides([long_ride(loop), long_ride(loop)])
        assert len(groups) == 2 and an._similarity_cache == {}
