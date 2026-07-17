"""
Tests for src/route_comparison.py — the shared route-similarity math used by
both RouteAnalyzer (commute grouping) and LongRideAnalyzer (recreational ride
grouping). See issue #463: this module exists so the two analyzers don't
reimplement Fréchet/Hausdorff comparison independently.
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
    similarity_score,
    passes_prefilter_deg,
    frechet_similarity_deg,
    hausdorff_percentile_similarity_deg,
    commute_similarity_score,
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

    def test_similarity_score_high_for_identical(self):
        coords = _line()
        assert similarity_score(coords, coords) > 0.99

    def test_similarity_score_low_for_distant(self):
        assert similarity_score(_line(), _line(offset_lat=1.0)) < 0.1

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


class TestDegreeScaledHelpers:
    """Covers the RouteAnalyzer (commute grouper) variants: raw lat/lon degrees,
    flat 111km/degree conversion, and precomputed-geometry prefiltering."""

    def test_frechet_similarity_deg_high_for_identical(self):
        coords = _line()
        assert frechet_similarity_deg(coords, coords) > 0.9

    def test_frechet_similarity_deg_low_for_distant(self):
        assert frechet_similarity_deg(_line(), _line(offset_lat=1.0)) < 0.5

    def test_hausdorff_percentile_similarity_deg_high_for_identical(self):
        coords = _line()
        assert hausdorff_percentile_similarity_deg(coords, coords) > 0.9

    def test_hausdorff_percentile_similarity_deg_bounded(self):
        sim = hausdorff_percentile_similarity_deg(_line(), _line(offset_lat=0.5))
        assert 0.0 <= sim <= 1.0

    def test_commute_similarity_score_matches_frechet_when_agreeing(self):
        coords = _line()
        assert commute_similarity_score(coords, coords) > 0.99

    def test_commute_similarity_score_falls_back_without_frechet(self):
        coords = _line()
        score_with = commute_similarity_score(coords, coords, frechet_available=True)
        score_without = commute_similarity_score(coords, coords, frechet_available=False)
        # Both should agree closely for identical routes even via different paths
        assert score_with == pytest.approx(score_without, abs=0.05)

    def test_passes_prefilter_deg_none_geometry_passes(self):
        assert passes_prefilter_deg(None, None, None, None, None, None) is True

    def test_passes_prefilter_deg_rejects_distant_centroid(self):
        bbox1 = (41.87, -87.64, 41.89, -87.62)
        bbox2 = (43.87, -89.64, 43.89, -89.62)
        assert passes_prefilter_deg(
            bbox1, (41.88, -87.63), 0.01,
            bbox2, (43.88, -89.63), 0.01,
        ) is False

    def test_passes_prefilter_deg_rejects_length_ratio(self):
        bbox = (41.87, -87.64, 41.89, -87.62)
        assert passes_prefilter_deg(
            bbox, (41.88, -87.63), 0.001,
            bbox, (41.88, -87.63), 1.0,
            length_ratio_max=2.0,
        ) is False


class TestComparisonThresholds:
    def test_commute_and_long_ride_thresholds_are_distinct_instances(self):
        assert isinstance(COMMUTE_THRESHOLDS, ComparisonThresholds)
        assert isinstance(LONG_RIDE_THRESHOLDS, ComparisonThresholds)
        assert COMMUTE_THRESHOLDS is not LONG_RIDE_THRESHOLDS
