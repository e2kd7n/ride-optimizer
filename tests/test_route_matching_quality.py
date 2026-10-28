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

@pytest.mark.xfail(strict=True, reason='#614: greedy pivot clustering depends on input order')
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


@pytest.mark.xfail(strict=True, reason='#614: group IDs are positional, so favourites drift')
def test_group_id_stable_when_unrelated_ride_added(tmp_path):
    commute = route(densify(STAIRCASE))
    unrelated = route(shift(densify(STAIRCASE), north=3000))

    def id_of(groups, ride):
        return next(g.id for g in groups if ride.activity_id in {r.activity_id for r in g.routes})

    before = id_of(analyzer(tmp_path / 'a').group_similar_routes([commute]), commute)
    after = id_of(analyzer(tmp_path / 'b').group_similar_routes([unrelated, commute]), commute)
    assert before == after


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
