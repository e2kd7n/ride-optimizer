"""
Shared route comparison utilities used by both commute and long-ride analyzers.

Both compare tracks in metres on arc-length-resampled tracks: p95 deviation and
50 m coverage (track_deviation_metrics, #613), grouped by centre clustering
(cluster_by_centres, #614). Long rides add directed coverage, so a ride lying
along part of another can be linked to it without being merged into it (#615).
"""

import math

import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree


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
# Commute corridor (#618): grid cell size, and how many rides must pass through
# a cell for it to be part of the corridor.
CORRIDOR_CELL_M = 25.0
CORRIDOR_MIN_SUPPORT = 2


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

    samples: points every sample_step_m, measured against other tracks.
    dense:   points every dense_step_m, which other tracks are measured against.

    Long rides use coarser steps (LONG_RIDE_SAMPLE_STEP_M / LONG_RIDE_DENSE_STEP_M)
    to keep memory and time per pair bounded on 100+ km tracks.
    """

    def __init__(self, coords, lat0: float,
                 sample_step_m: float = SAMPLE_STEP_M, dense_step_m: float = DENSE_STEP_M):
        c = np.asarray(coords, dtype=float).reshape(-1, 2)
        if len(c) == 0:
            raise ValueError("empty track")
        xy = project_m(c, lat0)
        self.samples = resample_m(xy, sample_step_m)
        self.dense = resample_m(xy, dense_step_m)
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
    p95_12, cov_12, p95_21, cov_21 = directed_deviation_metrics(t1, t2)
    return max(p95_12, p95_21), min(cov_12, cov_21)


def directed_deviation_metrics(t1: PreparedTrack, t2: PreparedTrack) -> tuple:
    """(p95_12, cov_12, p95_21, cov_21): the p95 deviation of t1's samples from
    t2 and the share of them within COVERAGE_RADIUS_M of t2, then the same for
    t2 against t1. Coverage of A by B is "how much of A lies along B", so it
    tells a sub-segment (A inside B) from an extension (B inside A) (#615)."""
    def directed(a, b):
        d = b.tree.query(a.samples, distance_upper_bound=P95_CAP_M)[0]
        d = np.minimum(d, P95_CAP_M)
        return float(np.percentile(d, DEVIATION_PERCENTILE)), float(np.mean(d <= COVERAGE_RADIUS_M))

    return directed(t1, t2) + directed(t2, t1)


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


def _grid_keys(xy: np.ndarray, cell_m: float) -> np.ndarray:
    """Grid cells of metric points as single int64 keys (row * _CELL_KEY_SPAN +
    col): 1-D unique is far faster than unique over rows, and the span leaves
    room for any projected coordinate on Earth."""
    c = np.floor(xy / cell_m).astype(np.int64)
    return c[:, 0] * _CELL_KEY_SPAN + c[:, 1]


def corridor_cells(tracks_coords: list, lat0: float,
                   min_support: int = CORRIDOR_MIN_SUPPORT) -> np.ndarray:
    """Sorted grid keys of the corridor a set of rides follows (#618): the
    CORRIDOR_CELL_M cells that at least min_support of them pass through,
    widened by one cell so a ride a lane or a GPS wobble away still counts.
    Requiring support keeps one ride's one-off detour out of the corridor."""
    per_track = [np.unique(_grid_keys(resample_m(project_m(c, lat0), SAMPLE_STEP_M),
                                      CORRIDOR_CELL_M))
                 for c in tracks_coords if len(c) >= 2]
    if not per_track:
        return np.empty(0, dtype=np.int64)
    cells, support = np.unique(np.concatenate(per_track), return_counts=True)
    core = cells[support >= min_support]
    offs = np.array([dx * _CELL_KEY_SPAN + dy for dx in (-1, 0, 1) for dy in (-1, 0, 1)])
    return np.unique(core[:, None] + offs[None, :])


def corridor_share(coords, lat0: float, cells: np.ndarray) -> float:
    """Share of a ride's length (samples every SAMPLE_STEP_M) inside corridor_cells."""
    if len(cells) == 0 or len(coords) < 2:
        return 0.0
    keys = _grid_keys(resample_m(project_m(coords, lat0), SAMPLE_STEP_M), CORRIDOR_CELL_M)
    return float(np.isin(keys, cells).mean())


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

    def keys(xy):
        return _grid_keys(xy, SCREEN_CELL_M)

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


def cluster_by_centres(n: int, edges) -> list:
    """Group indices 0..n-1 into [(centre, members)], given the match edges
    (i, j, score); only edges with score >= 1.0 count as matches.

    Repeatedly takes the ungrouped item that matches the most other ungrouped
    items as a centre, and groups it with every ungrouped item that matches it
    (Butina clustering). Ties go to the higher total match score, then the
    lower index, so with items in a fixed order (activity ID) the result
    doesn't depend on input order (#614). Every member matches its group's
    centre, so a group can't chain into a different route, and the centre is
    the group's representative. Members are listed in index order.
    """
    neighbours = [dict() for _ in range(n)]
    for i, j, score in edges:
        if score >= 1.0 and i != j:
            neighbours[i][j] = neighbours[j][i] = float(score)
    # An ungrouped item's degree counts itself plus its ungrouped matches.
    degree = np.array([len(nb) + 1 for nb in neighbours], dtype=np.int64)
    ungrouped = np.ones(n, dtype=bool)
    result = []
    while ungrouped.any():
        live = np.flatnonzero(ungrouped)
        top = live[degree[live] == degree[live].max()]
        centre = int(top[0])
        if len(top) > 1:
            best = None
            for c in top:
                row = np.zeros(n)
                for v, score in neighbours[c].items():
                    if ungrouped[v]:
                        row[v] = score
                total = row.sum()
                if best is None or total > best:
                    best, centre = total, int(c)
        members = sorted([centre] + [v for v in neighbours[centre] if ungrouped[v]])
        ungrouped[members] = False
        for m in members:
            for v in neighbours[m]:
                degree[v] -= 1
        result.append((centre, members))
    return result


# ---------------------------------------------------------------------------
# Long rides (LongRideAnalyzer), #615.
#
# Same metric as commutes, but a long-ride corpus is thousands of 15-300 km
# tracks: all of them resampled every 10 m would not fit in the Pi's memory,
# and all pairs (millions) would take hours. So long rides are resampled more
# coarsely, and coverage_bound_pairs screens out, exactly and from compact
# per-track cell lists, the pairs whose coverage can't reach a threshold.
# ---------------------------------------------------------------------------

LONG_RIDE_SAMPLE_STEP_M = 25.0
LONG_RIDE_DENSE_STEP_M = 10.0
LONG_SCREEN_CELL_M = 100.0
# Cells are hashed into this many columns. A collision can only make a bound
# looser, never tighter, so it stays a valid upper bound.
_SCREEN_COLUMNS = 1 << 26
_BOUND_SLACK = 1e-5


def _hash_cells(cells: np.ndarray) -> np.ndarray:
    h = ((cells[:, 0] * 73856093) ^ (cells[:, 1] * 19349663)) & (_SCREEN_COLUMNS - 1)
    return h.astype(np.int32)


def coverage_cells(track: PreparedTrack) -> tuple:
    """Compact screening summary of a track for coverage_bound_pairs:
    (sample_columns, sample_shares, near_columns). A sample within
    COVERAGE_RADIUS_M of a dense point lies within r cells of it on each axis,
    so it falls in one of the dense points' "near" cells."""
    r = int(math.ceil(COVERAGE_RADIUS_M / LONG_SCREEN_CELL_M))
    cols, counts = np.unique(
        _hash_cells(np.floor(track.samples / LONG_SCREEN_CELL_M).astype(np.int64)),
        return_counts=True)
    dense = np.unique(np.floor(track.dense / LONG_SCREEN_CELL_M).astype(np.int64), axis=0)
    offsets = np.array([(dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)])
    near = np.unique((dense[:, None, :] + offsets[None, :, :]).reshape(-1, 2), axis=0)
    return cols, (counts / len(track.samples)).astype(np.float32), np.unique(_hash_cells(near))


def coverage_bound_pairs(cells: list, min_mutual: float, min_either: float,
                         block_rows: int = 64) -> tuple:
    """Pairs that could reach a coverage threshold, with their upper bounds.

    cells: coverage_cells() of each track. Returns arrays (i, j, bound_ij,
    bound_ji) over i < j, where bound_ij is an upper bound on the share of
    track i within COVERAGE_RADIUS_M of track j, keeping pairs where
    min(bounds) >= min_mutual or max(bounds) >= min_either. Every other pair
    is guaranteed to have coverage below both.

    Memory matters here (a real corpus has millions of near-cells): matrices
    are float32/int32 and built straight from the per-track lists, only the
    small shares matrix is ever transposed, and the products are taken in
    blocks of rows. Bounds are rounded up by _BOUND_SLACK to absorb float32
    error, so they stay upper bounds.
    """
    n = len(cells)
    empty = (np.empty(0, dtype=np.int64),) * 2 + (np.empty(0),) * 2
    if n < 2:
        return empty

    # Renumber the hashed columns actually used to 0..m-1, so a transpose
    # indexes m columns rather than all _SCREEN_COLUMNS.
    used = np.unique(np.concatenate([c[0] for c in cells] + [c[2] for c in cells]))

    def matrix(column_lists, value_lists=None):
        # Each list is sorted and unique, and so stays after renumbering.
        indptr = np.zeros(n + 1, dtype=np.int64)
        indptr[1:] = np.cumsum([len(c) for c in column_lists])
        indices = np.concatenate([np.searchsorted(used, c).astype(np.int32) for c in column_lists])
        data = (np.concatenate(value_lists).astype(np.float32) if value_lists is not None
                else np.ones(len(indices), dtype=np.float32))
        return sparse.csr_matrix((data, indices, indptr), shape=(n, len(used)))

    shares = matrix([c[0] for c in cells], [c[1] for c in cells])
    near = matrix([c[2] for c in cells])
    shares_t = shares.T.tocsr()
    out = [[], [], [], []]
    for start in range(0, n, block_rows):
        stop = min(n, start + block_rows)
        # [a, b]: bound on a within reach of b, then on b within reach of a.
        ab = (near @ shares[start:stop].T).T.toarray().astype(np.float64) + _BOUND_SLACK
        ba = (near[start:stop] @ shares_t).toarray().astype(np.float64) + _BOUND_SLACK
        rows = np.arange(start, stop)[:, None]
        keep = ((np.arange(n)[None, :] > rows)
                & ((np.minimum(ab, ba) >= min_mutual) | (np.maximum(ab, ba) >= min_either)))
        a, b = np.nonzero(keep)
        out[0].append(a + start)
        out[1].append(b)
        out[2].append(ab[a, b])
        out[3].append(ba[a, b])
    return tuple(np.concatenate(o) for o in out)


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
