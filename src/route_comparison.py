"""
Shared route comparison utilities used by both commute and long-ride analyzers.

Provides coordinate scaling, geometric pre-filters, and shape-distance
calculations. Long rides still use Fréchet + Hausdorff (combined_distance_km,
#615); commutes use metric deviation + coverage (track_deviation_metrics, #613).
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.distance import directed_hausdorff

try:
    from similaritymeasures import frechet_dist
    FRECHET_AVAILABLE = True
except ImportError:
    FRECHET_AVAILABLE = False


@dataclass
class ComparisonThresholds:
    """Per-use-case thresholds for the geometric filter and distance comparison."""
    centroid_max_km: float = 5.0
    extent_point_max_km: float = 10.0
    length_ratio_max: float = 1.25
    bbox_overlap_min: float = 0.0
    similarity_km: float = 2.0


COMMUTE_THRESHOLDS = ComparisonThresholds(
    centroid_max_km=2.5,
    extent_point_max_km=5.0,
    length_ratio_max=1.5,
    bbox_overlap_min=0.3,
    similarity_km=0.5,
)

LONG_RIDE_THRESHOLDS = ComparisonThresholds(
    centroid_max_km=5.0,
    extent_point_max_km=10.0,
    length_ratio_max=1.25,
    bbox_overlap_min=0.0,
    similarity_km=2.0,
)


def coords_to_km(coords: np.ndarray) -> np.ndarray:
    if len(coords) == 0:
        return coords
    mean_lat = float(np.mean(coords[:, 0]))
    lat_km = 111.32
    lon_km = 111.32 * math.cos(math.radians(mean_lat))
    result = coords.copy().astype(float)
    result[:, 0] *= lat_km
    result[:, 1] *= lon_km
    return result


def extent_point(coords_km: np.ndarray) -> np.ndarray:
    """Return the coordinate farthest from the start point."""
    dists = np.linalg.norm(coords_km - coords_km[0], axis=1)
    return coords_km[int(np.argmax(dists))]


def centroid(coords_km: np.ndarray) -> np.ndarray:
    return coords_km.mean(axis=0)


def path_length_km(coords_km: np.ndarray) -> float:
    if len(coords_km) < 2:
        return 0.0
    return float(np.sum(np.linalg.norm(np.diff(coords_km, axis=0), axis=1)))


def bbox_overlap_ratio(coords1_km: np.ndarray, coords2_km: np.ndarray) -> float:
    """Overlap of bounding boxes as fraction of the smaller box's area."""
    min1 = coords1_km.min(axis=0)
    max1 = coords1_km.max(axis=0)
    min2 = coords2_km.min(axis=0)
    max2 = coords2_km.max(axis=0)

    inter = np.maximum(0, np.minimum(max1, max2) - np.maximum(min1, min2))
    intersection = float(inter[0] * inter[1])
    if intersection == 0:
        return 0.0

    area1 = float((max1[0] - min1[0]) * (max1[1] - min1[1]))
    area2 = float((max2[0] - min2[0]) * (max2[1] - min2[1]))
    smaller = min(area1, area2)
    return intersection / smaller if smaller > 0 else 0.0


def passes_prefilter(coords1_km: np.ndarray,
                     coords2_km: np.ndarray,
                     thresholds: ComparisonThresholds) -> bool:
    """
    Fast geometric pre-filter. Returns False if routes are obviously dissimilar.

    Evaluates (in order of cheapness): path length ratio, centroid distance,
    extent point distance, bounding box overlap.
    """
    len1 = path_length_km(coords1_km)
    len2 = path_length_km(coords2_km)
    if len1 > 0 and len2 > 0:
        ratio = max(len1, len2) / min(len1, len2)
        if ratio > thresholds.length_ratio_max:
            return False

    cdist_km = float(np.linalg.norm(centroid(coords1_km) - centroid(coords2_km)))
    if cdist_km > thresholds.centroid_max_km:
        return False

    if len(coords1_km) >= 2 and len(coords2_km) >= 2:
        ext_dist = float(np.linalg.norm(
            extent_point(coords1_km) - extent_point(coords2_km)))
        if ext_dist > thresholds.extent_point_max_km:
            return False

    if thresholds.bbox_overlap_min > 0:
        if bbox_overlap_ratio(coords1_km, coords2_km) < thresholds.bbox_overlap_min:
            return False

    return True


def combined_distance_km(coords1_km: np.ndarray,
                         coords2_km: np.ndarray) -> float:
    """
    Average of Fréchet and max-directed Hausdorff distances in km-scaled space.
    Falls back to Hausdorff-only when similaritymeasures is unavailable.
    """
    h_dist = max(
        directed_hausdorff(coords1_km, coords2_km)[0],
        directed_hausdorff(coords2_km, coords1_km)[0],
    )
    if FRECHET_AVAILABLE:
        f_dist = frechet_dist(coords1_km, coords2_km)
        return (f_dist + h_dist) / 2
    return h_dist



# ---------------------------------------------------------------------------
# Commute matching (RouteAnalyzer), #613.
#
# Everything is measured in metres in a local equirectangular frame with the
# longitude scaled by cos(lat), so a north and an east offset count the same.
# Tracks are resampled by arc length, so the verdict doesn't depend on how
# densely Strava's summary polyline happens to be sampled.
#
# Two rides match when both of these hold, in both directions:
#   - p95 deviation: 95% of one track's samples lie within max_p95_m of the
#     other track (tolerates GPS spikes, a one-block detour, a different
#     parking spot), and
#   - coverage: at least min_coverage of each track's samples lie within
#     COVERAGE_RADIUS_M of the other (a ride that shares only half the route
#     isn't the same route).
#
# track_deviation_metrics returns the raw (p95_m, coverage) pair, which doesn't
# depend on the configured thresholds, so callers can cache it and still
# re-decide when the thresholds change.
#
# Bump the caller's similarity-cache version when any constant here changes.
# ---------------------------------------------------------------------------

M_PER_DEG_LAT = 111_320.0
SAMPLE_STEP_M = 10.0
DENSE_STEP_M = 5.0
COVERAGE_RADIUS_M = 50.0
DEVIATION_PERCENTILE = 95.0


def project_m(coords, lat0: float) -> np.ndarray:
    """[[lat, lon], ...] -> (N, 2) metres (northing, easting) with longitude
    scaled by cos(lat0). lat0 must be shared by every track being compared."""
    c = np.asarray(coords, dtype=float).reshape(-1, 2)
    return np.column_stack([c[:, 0] * M_PER_DEG_LAT,
                            c[:, 1] * M_PER_DEG_LAT * math.cos(math.radians(lat0))])


def resample_m(xy: np.ndarray, step_m: float) -> np.ndarray:
    """Points every step_m metres along a metric polyline (endpoints kept)."""
    if len(xy) < 2:
        return xy
    seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    if s[-1] == 0:
        return xy[:1]
    t = np.append(np.arange(0.0, s[-1], step_m), s[-1])
    return np.column_stack([np.interp(t, s, xy[:, 0]), np.interp(t, s, xy[:, 1])])


def track_deviation_metrics(coords1, coords2) -> tuple:
    """(p95 deviation in metres, mutual coverage) for two lat/lon tracks.

    Each track's samples (every SAMPLE_STEP_M) are measured against the other
    track densified to DENSE_STEP_M, which approximates point-to-segment
    distance to within DENSE_STEP_M / 2. Both values are the worse of the two
    directions, so the result is symmetric.
    """
    c1 = np.asarray(coords1, dtype=float).reshape(-1, 2)
    c2 = np.asarray(coords2, dtype=float).reshape(-1, 2)
    if len(c1) == 0 or len(c2) == 0:
        raise ValueError("empty track")
    lat0 = float(np.concatenate([c1[:, 0], c2[:, 0]]).mean())
    xy1, xy2 = project_m(c1, lat0), project_m(c2, lat0)

    def directed(a, b):
        d = cKDTree(resample_m(b, DENSE_STEP_M)).query(resample_m(a, SAMPLE_STEP_M))[0]
        return float(np.percentile(d, DEVIATION_PERCENTILE)), float(np.mean(d <= COVERAGE_RADIUS_M))

    p95_12, cov_12 = directed(xy1, xy2)
    p95_21, cov_21 = directed(xy2, xy1)
    return max(p95_12, p95_21), min(cov_12, cov_21)


def match_score(p95_m: float, coverage: float, max_p95_m: float, min_coverage: float) -> float:
    """One number for ranking candidate matches: the tighter of the two criteria's
    margins. >= 1.0 exactly when both criteria pass."""
    return min(coverage / min_coverage, max_p95_m / max(p95_m, 1e-9))


def route_geometry(coords) -> tuple:
    """(bbox, centroid, path_length_m) for the cheap prefilter. bbox and centroid
    are in degrees; path length is in metres."""
    arr = np.asarray(coords, dtype=float).reshape(-1, 2)
    bbox = (float(arr[:, 0].min()), float(arr[:, 1].min()),
            float(arr[:, 0].max()), float(arr[:, 1].max()))
    cen = (float(arr[:, 0].mean()), float(arr[:, 1].mean()))
    xy = project_m(arr, cen[0])
    length = float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum()) if len(arr) > 1 else 0.0
    return bbox, cen, length


def passes_commute_prefilter(bbox1, centroid1, path_length_m1,
                             bbox2, centroid2, path_length_m2,
                             length_ratio_max: float = 2.0,
                             centroid_max_m: float = 2000.0,
                             bbox_overlap_min: float = 0.3) -> bool:
    """
    Cheap rejection of obviously different routes from precomputed geometry
    (see route_geometry). Any missing geometry (None) skips the filter -- callers
    can't reject what they can't measure.

    Distances are in metres. The bbox overlap is a ratio of areas, which per-axis
    scaling cancels out of, so it can stay in degrees and is still isotropic.
    """
    if (bbox1 is None or bbox2 is None or centroid1 is None or centroid2 is None
            or path_length_m1 is None or path_length_m2 is None):
        return True

    shorter = min(path_length_m1, path_length_m2)
    longer = max(path_length_m1, path_length_m2)
    if shorter > 0 and longer / shorter > length_ratio_max:
        return False

    lat0 = (centroid1[0] + centroid2[0]) / 2
    c1, c2 = project_m([centroid1], lat0)[0], project_m([centroid2], lat0)[0]
    if float(np.linalg.norm(c1 - c2)) > centroid_max_m:
        return False

    min_lat1, min_lon1, max_lat1, max_lon1 = bbox1
    min_lat2, min_lon2, max_lat2, max_lon2 = bbox2
    inter_lat = max(0, min(max_lat1, max_lat2) - max(min_lat1, min_lat2))
    inter_lon = max(0, min(max_lon1, max_lon2) - max(min_lon1, min_lon2))
    area1 = (max_lat1 - min_lat1) * (max_lon1 - min_lon1)
    area2 = (max_lat2 - min_lat2) * (max_lon2 - min_lon2)
    smaller_area = min(area1, area2)
    # A dead-straight north-south or east-west track has a zero-area box, which
    # says nothing about overlap; the centroid check above still applies.
    if smaller_area > 0 and inter_lat * inter_lon / smaller_area < bbox_overlap_min:
        return False

    return True
