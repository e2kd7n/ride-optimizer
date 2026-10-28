"""
Tests for src/route_comparison.py — the shared route-similarity math used by
both RouteAnalyzer (commute grouping) and LongRideAnalyzer (recreational ride
grouping). See issue #463: this module exists so the two analyzers don't
reimplement comparison math independently.
"""
import numpy as np
import pytest

from src.route_comparison import (
    ComparisonThresholds,
    COMMUTE_THRESHOLDS,
    LONG_RIDE_THRESHOLDS,
    coords_to_km,
    extent_point,
    centroid,
    path_length_km,
    bbox_overlap_ratio,
    passes_prefilter,
    combined_distance_km,
    M_PER_DEG_LAT,
    project_m,
    resample_m,
    track_deviation_metrics,
    match_score,
    route_geometry,
    passes_commute_prefilter,
)


def _line(offset_lat=0.0, offset_lon=0.0, n=6):
    return np.array([
        [41.8800 + offset_lat + i * 0.001, -87.6300 + offset_lon]
        for i in range(n)
    ])


class TestKmScaledHelpers:
    def test_coords_to_km_identity_on_empty(self):
        assert len(coords_to_km(np.empty((0, 2)))) == 0

    def test_combined_distance_km_zero_for_identical_routes(self):
        coords_km = coords_to_km(_line())
        assert combined_distance_km(coords_km, coords_km) == pytest.approx(0.0, abs=1e-6)

    def test_combined_distance_km_grows_with_offset(self):
        c1 = coords_to_km(_line())
        c2 = coords_to_km(_line(offset_lat=0.5))  # ~55km away
        assert combined_distance_km(c1, c2) > 10

    def test_passes_prefilter_rejects_distant_centroids(self):
        c1 = coords_to_km(_line())
        c2 = coords_to_km(_line(offset_lat=1.0))
        assert passes_prefilter(c1, c2, COMMUTE_THRESHOLDS) is False

    def test_passes_prefilter_accepts_nearby_routes(self):
        c1 = coords_to_km(_line())
        c2 = coords_to_km(_line(offset_lon=0.0005))
        assert passes_prefilter(c1, c2, LONG_RIDE_THRESHOLDS) is True

    def test_bbox_overlap_ratio_full_overlap_is_one(self):
        # A pure north-south line has zero-width bbox in one axis, so use a
        # route with variation on both axes to get a non-degenerate box.
        square = np.array([[41.88, -87.63], [41.89, -87.63], [41.89, -87.62], [41.88, -87.62]])
        c1 = coords_to_km(square)
        assert bbox_overlap_ratio(c1, c1) == pytest.approx(1.0)

    def test_path_length_km_zero_for_single_point(self):
        assert path_length_km(np.array([[41.88, -87.63]])) == 0.0


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


class TestComparisonThresholds:
    def test_commute_and_long_ride_thresholds_are_distinct_instances(self):
        assert isinstance(COMMUTE_THRESHOLDS, ComparisonThresholds)
        assert isinstance(LONG_RIDE_THRESHOLDS, ComparisonThresholds)
        assert COMMUTE_THRESHOLDS is not LONG_RIDE_THRESHOLDS
