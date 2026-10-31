"""
Tests for src/route_comparison.py — the shared route-similarity math used by
both RouteAnalyzer (commute grouping) and LongRideAnalyzer (recreational ride
grouping). See issue #463: this module exists so the two analyzers don't
reimplement comparison math independently.
"""
import numpy as np
import pytest

from src.route_comparison import (
    M_PER_DEG_LAT,
    LONG_RIDE_DENSE_STEP_M,
    LONG_RIDE_SAMPLE_STEP_M,
    cluster_by_centres,
    coverage_bound_pairs,
    coverage_cells,
    directed_deviation_metrics,
    project_m,
    resample_m,
    track_deviation_metrics,
    match_score,
    route_geometry,
    passes_commute_prefilter,
    PreparedTrack,
    prepared_deviation_metrics,
    possible_match_pairs,
    P95_CAP_M,
)


def _line(offset_lat=0.0, offset_lon=0.0, n=6):
    return np.array([
        [41.8800 + offset_lat + i * 0.001, -87.6300 + offset_lon]
        for i in range(n)
    ])


class TestCommuteMetric:
    """Covers the RouteAnalyzer (commute grouper) metric: metres with cos(lat),
    arc-length resampling, p95 deviation + coverage (#613)."""

    def test_project_m_scales_longitude_by_cos_lat(self):
        xy = project_m([[60.0, 0.0], [60.0, 1.0]], lat0=60.0)
        assert xy[1, 1] - xy[0, 1] == pytest.approx(M_PER_DEG_LAT * 0.5)

    def test_resample_m_spacing_and_endpoints(self):
        pts = resample_m(np.array([[0.0, 0.0], [0.0, 95.0]]), 10.0)
        assert len(pts) == 11
        assert pts[-1, 1] == pytest.approx(95.0)
        assert np.diff(pts[:-1, 1]) == pytest.approx(np.full(9, 10.0))

    def test_identical_tracks_have_zero_deviation_full_coverage(self):
        p95, cov = track_deviation_metrics(_line(), _line())
        assert p95 == pytest.approx(0.0, abs=1e-6)
        assert cov == 1.0

    def test_metrics_are_symmetric(self):
        a, b = _line(), np.vstack([_line(), [[41.886, -87.628]]])
        assert track_deviation_metrics(a, b) == pytest.approx(track_deviation_metrics(b, a))

    def test_parallel_offset_measured_in_metres(self):
        # 0.0005° of longitude at 41.88° is ~41 m east.
        p95, cov = track_deviation_metrics(_line(), _line(offset_lon=0.0005))
        assert p95 == pytest.approx(0.0005 * M_PER_DEG_LAT * np.cos(np.radians(41.88)), rel=0.02)
        assert cov == 1.0

    def test_distant_track_has_no_coverage(self):
        assert track_deviation_metrics(_line(), _line(offset_lat=0.01))[1] == 0.0

    def test_empty_track_raises(self):
        with pytest.raises(ValueError):
            track_deviation_metrics(np.empty((0, 2)), _line())

    def test_match_score_is_one_at_the_thresholds(self):
        assert match_score(100.0, 0.85, max_p95_m=100.0, min_coverage=0.85) == pytest.approx(1.0)
        assert match_score(101.0, 0.99, max_p95_m=100.0, min_coverage=0.85) < 1.0
        assert match_score(10.0, 0.80, max_p95_m=100.0, min_coverage=0.85) < 1.0

    def test_route_geometry_length_in_metres(self):
        _, _, length = route_geometry(_line())  # 5 steps of 0.001° latitude
        assert length == pytest.approx(5 * 0.001 * M_PER_DEG_LAT)

    def test_prefilter_none_geometry_passes(self):
        assert passes_commute_prefilter(None, None, None, None, None, None) is True

    def test_prefilter_rejects_distant_centroid(self):
        bbox1 = (41.87, -87.64, 41.89, -87.62)
        bbox2 = (43.87, -89.64, 43.89, -89.62)
        assert passes_commute_prefilter(
            bbox1, (41.88, -87.63), 5000.0,
            bbox2, (43.88, -89.63), 5000.0,
        ) is False

    def test_prefilter_centroid_distance_is_isotropic(self):
        # 1.8 km north and 1.8 km east must get the same verdict.
        bbox = (41.87, -87.64, 41.89, -87.62)
        lat_off = 1800 / M_PER_DEG_LAT
        lon_off = 1800 / (M_PER_DEG_LAT * np.cos(np.radians(41.88)))
        north = passes_commute_prefilter(bbox, (41.88, -87.63), 5000.0,
                                         bbox, (41.88 + lat_off, -87.63), 5000.0,
                                         bbox_overlap_min=0)
        east = passes_commute_prefilter(bbox, (41.88, -87.63), 5000.0,
                                        bbox, (41.88, -87.63 + lon_off), 5000.0,
                                        bbox_overlap_min=0)
        assert north is east is True

    def test_prefilter_rejects_length_ratio(self):
        bbox = (41.87, -87.64, 41.89, -87.62)
        assert passes_commute_prefilter(
            bbox, (41.88, -87.63), 1000.0,
            bbox, (41.88, -87.63), 5000.0,
            length_ratio_max=2.0,
        ) is False

    def test_prefilter_straight_track_not_rejected_by_bbox(self):
        bbox = (41.87, -87.63, 41.89, -87.63)  # zero width
        assert passes_commute_prefilter(bbox, (41.88, -87.63), 2000.0,
                                        bbox, (41.88, -87.63), 2000.0) is True


class TestPossibleMatchPairs:
    """The grid screen in front of the exact metric (#614): it may keep pairs
    that don't match, but must never drop one that does."""

    @staticmethod
    def _tracks(offsets_m, lat0=41.88):
        deg = 1 / M_PER_DEG_LAT
        # A 2 km L-shaped track, offset north by each amount.
        base = [(41.88, -87.63), (41.89, -87.63), (41.89, -87.6165)]
        return [PreparedTrack([(lat + off * deg, lon) for lat, lon in base], lat0)
                for off in offsets_m]

    def test_never_drops_a_matching_pair(self):
        tracks = self._tracks([0, 20, 45, 70, 95, 99, 104, 130, 400, 2000])
        kept = {tuple(p) for p in possible_match_pairs(tracks, 100.0, 0.85)}
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                score = match_score(*prepared_deviation_metrics(tracks[i], tracks[j]), 100.0, 0.85)
                if score >= 1.0:
                    assert (i, j) in kept, (i, j, score)

    def test_drops_distant_pairs(self):
        assert len(possible_match_pairs(self._tracks([0, 2000]), 100.0, 0.85)) == 0

    def test_single_track_has_no_pairs(self):
        assert possible_match_pairs(self._tracks([0]), 100.0, 0.85).shape == (0, 2)

    def test_threshold_must_be_below_cap(self):
        with pytest.raises(ValueError):
            possible_match_pairs(self._tracks([0, 10]), P95_CAP_M, 0.85)

    def test_prepared_metrics_match_raw_metrics(self):
        a, b = _line(), _line(offset_lon=0.0005)
        lat0 = float(np.vstack([a, b])[:, 0].mean())
        assert prepared_deviation_metrics(PreparedTrack(a, lat0), PreparedTrack(b, lat0)) \
            == pytest.approx(track_deviation_metrics(a, b))


class TestDirectedMetrics:
    def test_sub_segment_is_covered_one_way(self):
        whole = _line(n=21)
        part = whole[5:11]
        lat0 = 41.89
        p95_pw, cov_pw, _, cov_wp = directed_deviation_metrics(PreparedTrack(part, lat0),
                                                               PreparedTrack(whole, lat0))
        assert cov_pw == 1.0 and p95_pw < 5.0  # within the 5 m dense spacing
        assert cov_wp < 0.4

    def test_symmetric_metrics_are_the_worse_direction(self):
        a, b = PreparedTrack(_line(n=21), 41.89), PreparedTrack(_line(n=21)[5:11], 41.89)
        p95_ab, cov_ab, p95_ba, cov_ba = directed_deviation_metrics(a, b)
        assert prepared_deviation_metrics(a, b) == (max(p95_ab, p95_ba), min(cov_ab, cov_ba))

    def test_coarse_long_ride_steps(self):
        t = PreparedTrack(_line(n=21), 41.89, LONG_RIDE_SAMPLE_STEP_M, LONG_RIDE_DENSE_STEP_M)
        assert np.diff(t.samples[:-1, 0]) == pytest.approx(np.full(len(t.samples) - 2,
                                                                   LONG_RIDE_SAMPLE_STEP_M))


class TestCoverageBoundPairs:
    """The long-ride screen (#615): bounds must never be below the exact coverage."""

    @staticmethod
    def _tracks():
        deg = 1 / M_PER_DEG_LAT
        base = [(41.88 + i * 0.002, -87.63 + (i % 3) * 0.003) for i in range(15)]
        variants = [base, base[3:9], base[::-1], [(la + 40 * deg, lo) for la, lo in base],
                    [(la + 120 * deg, lo) for la, lo in base], base[:8] + [(41.95, -87.60)],
                    [(la + 0.05, lo) for la, lo in base]]
        return [PreparedTrack(v, 41.89, LONG_RIDE_SAMPLE_STEP_M, LONG_RIDE_DENSE_STEP_M)
                for v in variants]

    def test_bounds_are_upper_bounds(self):
        tracks = self._tracks()
        i, j, b_ij, b_ji = coverage_bound_pairs([coverage_cells(t) for t in tracks], 0.0, 0.0)
        bounds = {(a, b): (u, v) for a, b, u, v in zip(i, j, b_ij, b_ji)}
        for a in range(len(tracks)):
            for b in range(a + 1, len(tracks)):
                _, cov_ab, _, cov_ba = directed_deviation_metrics(tracks[a], tracks[b])
                u, v = bounds.get((a, b), (0.0, 0.0))
                assert cov_ab <= u + 1e-9 and cov_ba <= v + 1e-9, (a, b)

    def test_never_drops_a_pair_that_reaches_the_threshold(self):
        tracks = self._tracks()
        i, j, _, _ = coverage_bound_pairs([coverage_cells(t) for t in tracks], 0.85, 0.9)
        kept = set(zip(i.tolist(), j.tolist()))
        for a in range(len(tracks)):
            for b in range(a + 1, len(tracks)):
                _, cov_ab, _, cov_ba = directed_deviation_metrics(tracks[a], tracks[b])
                if min(cov_ab, cov_ba) >= 0.85 or max(cov_ab, cov_ba) >= 0.9:
                    assert (a, b) in kept, (a, b)

    def test_drops_distant_pairs_and_blocks_agree(self):
        tracks = self._tracks()
        cells = [coverage_cells(t) for t in tracks]
        whole = coverage_bound_pairs(cells, 0.5, 0.5)
        blocked = coverage_bound_pairs(cells, 0.5, 0.5, block_rows=2)
        assert all(np.array_equal(x, y) for x, y in zip(whole, blocked))
        assert 6 not in set(whole[0].tolist()) | set(whole[1].tolist())  # 5.5 km away

    def test_single_track_has_no_pairs(self):
        assert len(coverage_bound_pairs([coverage_cells(self._tracks()[0])], 0.5, 0.5)[0]) == 0


class TestClusterByCentres:
    @staticmethod
    def _dense_reference(scores):
        """The pre-#615 dense implementation, kept here as the specification."""
        n = len(scores)
        match = scores >= 1.0
        np.fill_diagonal(match, True)
        ungrouped = np.ones(n, dtype=bool)
        result = []
        while ungrouped.any():
            live = match & ungrouped[None, :]
            degree = live.sum(axis=1)
            total = np.where(live, scores, 0.0).sum(axis=1)
            cand = np.flatnonzero(ungrouped)
            centre = int(cand[np.lexsort((cand, -total[cand], -degree[cand]))[0]])
            members = np.flatnonzero(match[centre] & ungrouped)
            ungrouped[members] = False
            result.append((centre, [int(m) for m in members]))
        return result

    def test_matches_dense_reference_on_random_graphs(self):
        rng = np.random.default_rng(615)
        for _ in range(200):
            n = int(rng.integers(1, 25))
            s = np.triu(rng.uniform(0.5, 1.3, (n, n)) * (rng.random((n, n)) < 0.3), 1)
            s = np.round(s, 2)  # rounding creates ties
            s = s + s.T
            edges = [(i, j, s[i, j]) for i in range(n) for j in range(i + 1, n) if s[i, j]]
            assert cluster_by_centres(n, edges) == self._dense_reference(s)

    def test_scores_below_one_are_not_matches(self):
        assert cluster_by_centres(2, [(0, 1, 0.99)]) == [(0, [0]), (1, [1])]
