"""
Shared route comparison utilities used by both commute and long-ride analyzers.

Provides coordinate scaling, geometric pre-filters, and shape-distance
calculations. Long rides still use Fréchet + Hausdorff (combined_distance_km,
#615); commutes use metric deviation + coverage (track_deviation_metrics, #613).
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy import sparse
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
# Deviations are stored capped at this, so max_p95_deviation_m must stay below it.
P95_CAP_M = 400.0
# Grid cell for possible_match_pairs' bounds; any size is exact, this one is fast.
SCREEN_CELL_M = 50.0
_CELL_KEY_SPAN = 1 << 32


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


class PreparedTrack:
    """A track projected with a shared lat0 and resampled once, so comparing it
    against many others doesn't redo that work per pair (#614).

    samples: points every SAMPLE_STEP_M, measured against other tracks.
    dense:   points every DENSE_STEP_M, which other tracks are measured against.
    """

    def __init__(self, coords, lat0: float):
        c = np.asarray(coords, dtype=float).reshape(-1, 2)
        if len(c) == 0:
            raise ValueError("empty track")
        xy = project_m(c, lat0)
        self.samples = resample_m(xy, SAMPLE_STEP_M)
        self.dense = resample_m(xy, DENSE_STEP_M)
        self._tree = None

    @property
    def tree(self) -> cKDTree:
        if self._tree is None:
            self._tree = cKDTree(self.dense)
        return self._tree


def prepared_deviation_metrics(t1: PreparedTrack, t2: PreparedTrack) -> tuple:
    """(p95 deviation in metres, mutual coverage) for two PreparedTracks that
    share a lat0.

    Each track's samples are measured against the other's dense points, which
    approximates point-to-segment distance to within DENSE_STEP_M / 2. Both
    values are the worse of the two directions, so the result is symmetric.
    Deviations are capped at P95_CAP_M, which lets the tree search stop early;
    a p95 at the cap means "at least that far".
    """
    def directed(a, b):
        d = b.tree.query(a.samples, distance_upper_bound=P95_CAP_M)[0]
        d = np.minimum(d, P95_CAP_M)
        return float(np.percentile(d, DEVIATION_PERCENTILE)), float(np.mean(d <= COVERAGE_RADIUS_M))

    p95_12, cov_12 = directed(t1, t2)
    p95_21, cov_21 = directed(t2, t1)
    return max(p95_12, p95_21), min(cov_12, cov_21)


def track_deviation_metrics(coords1, coords2) -> tuple:
    """prepared_deviation_metrics for two raw lat/lon tracks, projected about
    their joint mean latitude. Raises ValueError on an empty track."""
    c1 = np.asarray(coords1, dtype=float).reshape(-1, 2)
    c2 = np.asarray(coords2, dtype=float).reshape(-1, 2)
    if len(c1) == 0 or len(c2) == 0:
        raise ValueError("empty track")
    lat0 = float(np.concatenate([c1[:, 0], c2[:, 0]]).mean())
    return prepared_deviation_metrics(PreparedTrack(c1, lat0), PreparedTrack(c2, lat0))


def match_score(p95_m: float, coverage: float, max_p95_m: float, min_coverage: float) -> float:
    """One number for ranking candidate matches: the tighter of the two criteria's
    margins. >= 1.0 exactly when both criteria pass."""
    return min(coverage / min_coverage, max_p95_m / max(p95_m, 1e-9))


def possible_match_pairs(tracks: list, max_p95_m: float, min_coverage: float) -> np.ndarray:
    """(i, j) index pairs, i < j, that *could* pass match_score >= 1.0.

    Every other pair is guaranteed not to match, so only these need the exact
    (and much slower) prepared_deviation_metrics. The bounds come from a grid of
    SCREEN_CELL_M cells: a sample within r metres of a dense point lies within
    ceil(r / SCREEN_CELL_M) cells of it on each axis. So the share of A's samples
    whose cell is within that many cells of one of B's is an upper bound on the
    share of A within r of B -- for r = COVERAGE_RADIUS_M that bounds coverage,
    and for r = max_p95_m it bounds how many samples can be within the p95.
    All tracks' pairs are bounded at once with two sparse matrix products.
    """
    n = len(tracks)
    if n < 2:
        return np.empty((0, 2), dtype=np.int64)
    if max_p95_m >= P95_CAP_M:
        raise ValueError(f"max_p95_m must be below P95_CAP_M ({P95_CAP_M} m)")

    # Cells as single int64 keys (row * _CELL_KEY_SPAN + col): 1-D unique is far
    # faster than unique over rows, and the span leaves room for any
    # projected coordinate on Earth.
    def keys(xy):
        c = np.floor(xy / SCREEN_CELL_M).astype(np.int64)
        return c[:, 0] * _CELL_KEY_SPAN + c[:, 1]

    sample_keys, sample_shares = [], []
    for t in tracks:
        k, counts = np.unique(keys(t.samples), return_counts=True)
        sample_keys.append(k)
        sample_shares.append(counts / len(t.samples))
    dense_keys = [np.unique(keys(t.dense)) for t in tracks]

    def reach(radius_m):
        r = int(math.ceil(radius_m / SCREEN_CELL_M))
        offs = np.array([dx * _CELL_KEY_SPAN + dy
                         for dx in range(-r, r + 1) for dy in range(-r, r + 1)])
        return [np.unique(dk[:, None] + offs[None, :]) for dk in dense_keys]

    def matrix(key_lists, values=None):
        rows = np.repeat(np.arange(n), [len(k) for k in key_lists])
        cols = np.searchsorted(columns, np.concatenate(key_lists))
        vals = np.concatenate(values) if values is not None else np.ones(len(rows))
        return sparse.csr_matrix((vals, (rows, cols)), shape=(n, len(columns)))

    reach_cov, reach_p95 = reach(COVERAGE_RADIUS_M), reach(max_p95_m)
    columns = np.unique(np.concatenate(sample_keys + reach_p95 + reach_cov))
    shares = matrix(sample_keys, sample_shares)  # n x cells, rows sum to 1
    # [a, b]: upper bound on the share of a's samples within reach of b.
    within_p95 = (shares @ matrix(reach_p95).T).toarray()
    within_cov = (shares @ matrix(reach_cov).T).toarray()

    # p95 <= max_p95_m needs more than 0.95 * (n - 1) of n samples within
    # max_p95_m (np.percentile's linear interpolation); 0.95 - 1/n is looser.
    n_samples = np.array([len(t.samples) for t in tracks], dtype=float)
    p95_ok = within_p95 >= (DEVIATION_PERCENTILE / 100.0 - 1.0 / n_samples)[:, None] - 1e-9
    cov_ok = within_cov >= min_coverage - 1e-9
    ok = p95_ok & cov_ok
    ok &= ok.T
    i, j = np.nonzero(np.triu(ok, k=1))
    return np.column_stack([i, j])


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
