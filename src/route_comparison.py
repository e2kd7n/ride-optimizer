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
