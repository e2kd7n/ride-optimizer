"""
Shared route comparison utilities used by both commute and long-ride analyzers.

Provides coordinate scaling, geometric pre-filters, and shape-distance
calculations (Fréchet + Hausdorff) behind a single API so both pipelines
converge on the same logic with per-use-case thresholds.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.spatial.distance import directed_hausdorff, cdist

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


def similarity_score(coords1: np.ndarray,
                     coords2: np.ndarray,
                     scale_m: float = 300.0,
                     already_km: bool = False) -> float:
    """
    Return a 0-1 similarity score using combined distance.
    Compatible with the commute analyzer's scoring convention.
    """
    if not already_km:
        coords1 = coords_to_km(coords1)
        coords2 = coords_to_km(coords2)

    dist_km = combined_distance_km(coords1, coords2)
    dist_m = dist_km * 1000
    return 1.0 / (1.0 + dist_m / scale_m)


# ---------------------------------------------------------------------------
# Degree-space variants used by the commute route grouper (RouteAnalyzer).
#
# RouteAnalyzer compares routes that are all within a few km of each other
# (a single commute corridor), so it works directly in raw lat/lon degrees
# with a flat 111km/degree conversion rather than round-tripping through
# coords_to_km's latitude-corrected km scaling used by the long-ride/loop
# comparisons above. It also pre-filters using bbox/centroid/path-length
# values cached once per Route (see Route.compute_geometry) instead of
# recomputing them from full coordinate arrays on every candidate pair --
# that caching matters for the O(n^2) inner loop over hundreds of commute
# activities, so it is kept as a distinct entry point rather than forced
# through passes_prefilter/combined_distance_km above.
# ---------------------------------------------------------------------------

def passes_prefilter_deg(bbox1, centroid1, path_length_deg1,
                         bbox2, centroid2, path_length_deg2,
                         length_ratio_max: float = 2.0,
                         centroid_max_deg: float = 0.02,
                         bbox_overlap_min: float = 0.3) -> bool:
    """
    Fast geometric pre-filter over precomputed degree-space route geometry.
    Returns False if routes are obviously dissimilar. Any missing geometry
    (None) skips the filter entirely -- callers can't reject what they can't
    measure.
    """
    if (bbox1 is None or bbox2 is None
            or path_length_deg1 is None or path_length_deg2 is None):
        return True

    # 1) Path length ratio — reject if one route is far longer than the other
    shorter = min(path_length_deg1, path_length_deg2)
    longer = max(path_length_deg1, path_length_deg2)
    if shorter > 0 and longer / shorter > length_ratio_max:
        return False

    # 2) Centroid distance — reject if centroids are far apart
    cdist_deg = ((centroid1[0] - centroid2[0]) ** 2 + (centroid1[1] - centroid2[1]) ** 2) ** 0.5
    if cdist_deg > centroid_max_deg:
        return False

    # 3) Bounding box overlap ratio — reject if boxes barely intersect
    min_lat1, min_lon1, max_lat1, max_lon1 = bbox1
    min_lat2, min_lon2, max_lat2, max_lon2 = bbox2

    inter_lat = max(0, min(max_lat1, max_lat2) - max(min_lat1, min_lat2))
    inter_lon = max(0, min(max_lon1, max_lon2) - max(min_lon1, min_lon2))
    intersection = inter_lat * inter_lon

    if intersection == 0:
        return False

    area1 = (max_lat1 - min_lat1) * (max_lon1 - min_lon1)
    area2 = (max_lat2 - min_lat2) * (max_lon2 - min_lon2)
    smaller_area = min(area1, area2)
    if smaller_area > 0 and intersection / smaller_area < bbox_overlap_min:
        return False

    return True


def frechet_similarity_deg(coords1: np.ndarray, coords2: np.ndarray,
                           distance_threshold_m: float = 300.0) -> float:
    """
    Fréchet-distance similarity for raw lat/lon-degree coordinates, using a
    flat 111km/degree conversion (adequate over the few-km span of a single
    commute corridor). Raises if similaritymeasures isn't installed --
    callers fall back to hausdorff_percentile_similarity_deg.
    """
    if not FRECHET_AVAILABLE:
        raise RuntimeError("similaritymeasures is not available")
    dist_deg = frechet_dist(coords1, coords2)
    normalized_dist_m = dist_deg * 111000
    return 1 / (1 + normalized_dist_m / distance_threshold_m)


def hausdorff_percentile_similarity_deg(coords1: np.ndarray, coords2: np.ndarray,
                                        percentile: float = 95.0,
                                        distance_threshold_m: float = 200.0) -> float:
    """
    Percentile-based (outlier-tolerant) Hausdorff similarity for raw
    lat/lon-degree coordinates. Using the Nth percentile of nearest-neighbor
    deviations instead of the max tolerates GPS glitches/brief detours while
    still catching real route differences.
    """
    distances_1_to_2 = cdist(coords1, coords2).min(axis=1)
    distances_2_to_1 = cdist(coords2, coords1).min(axis=1)
    percentile_dist = max(
        np.percentile(distances_1_to_2, percentile),
        np.percentile(distances_2_to_1, percentile),
    )
    normalized_dist_m = percentile_dist * 111000
    return 1 / (1 + normalized_dist_m / distance_threshold_m)


def commute_similarity_score(coords1: np.ndarray, coords2: np.ndarray,
                             percentile: float = 95.0,
                             frechet_available: bool = FRECHET_AVAILABLE,
                             disagreement_penalty: float = 0.7,
                             disagreement_floor: float = 0.50) -> float:
    """
    Combined Fréchet+Hausdorff similarity score for commute route grouping.

    Fréchet is the primary metric (order-sensitive, robust to GPS sampling
    differences); percentile Hausdorff is a secondary spatial-disagreement
    check -- if Hausdorff indicates the routes are spatially far apart even
    though Fréchet looks close, the Fréchet score is penalized.
    """
    if frechet_available:
        try:
            frechet_sim = frechet_similarity_deg(coords1, coords2)
            hausdorff_sim = hausdorff_percentile_similarity_deg(coords1, coords2, percentile)
            if hausdorff_sim < disagreement_floor:
                return frechet_sim * disagreement_penalty
            return frechet_sim
        except Exception:
            pass
    return hausdorff_percentile_similarity_deg(coords1, coords2, percentile)
