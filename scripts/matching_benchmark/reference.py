"""
Independent "ground truth" for route matching (#611).

Deliberately shares no code with src/route_comparison.py or src/route_analyzer.py,
so a bug in the app's matching can't also hide in the yardstick that measures it.

Every track is projected to local metres (equirectangular, cos(lat)-corrected,
one shared origin latitude for the whole corpus) and resampled by arc length.
For a pair of tracks A and B:

    dev_ab      distances from each 20 m sample of A to B (B densified to 5 m)
    cov_min     min over both directions of the share of samples within 50 m
    dev_p95     max over both directions of the 95th-percentile deviation
    label       'same'  if cov_min >= 0.90 and dev_p95 <= 75 m
                'diff'  if cov_min <= 0.50
                'ambig' otherwise

Bump REFERENCE_VERSION whenever any of this changes, so cached reference
results computed under the old definition are discarded.
"""
import math

import numpy as np
from scipy.spatial import cKDTree

REFERENCE_VERSION = 1

SAMPLE_STEP_M = 20.0
DENSE_STEP_M = 5.0
COVERAGE_RADIUS_M = 50.0
SAME_MIN_COVERAGE = 0.90
SAME_MAX_P95_M = 75.0
DIFF_MAX_COVERAGE = 0.50

_M_PER_DEG = 111_320.0


def project(coords, lat0):
    """[[lat, lon], ...] -> (N, 2) array of metres (northing, easting)."""
    c = np.asarray(coords, dtype=float)
    k = math.cos(math.radians(lat0))
    return np.column_stack([c[:, 0] * _M_PER_DEG, c[:, 1] * _M_PER_DEG * k])


def resample(xy, step):
    """Resample a metric polyline at a fixed arc-length step. Returns (points, length_m)."""
    seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    xy = xy[np.concatenate([[True], seg > 0])]
    seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    if s[-1] == 0:
        return xy[:1], 0.0
    t = np.append(np.arange(0.0, s[-1], step), s[-1])
    return np.column_stack([np.interp(t, s, xy[:, 0]), np.interp(t, s, xy[:, 1])]), float(s[-1])


class Track:
    """A route prepared for reference comparisons."""

    __slots__ = ('xy', 'samples', 'length_m', 'tree')

    def __init__(self, coords, lat0):
        self.xy = project(coords, lat0)
        self.samples, self.length_m = resample(self.xy, SAMPLE_STEP_M)
        dense, _ = resample(self.xy, DENSE_STEP_M)
        self.tree = cKDTree(dense)


def compare(a: Track, b: Track) -> dict:
    """Reference metrics for one pair of tracks (symmetric)."""
    dab = b.tree.query(a.samples)[0]
    dba = a.tree.query(b.samples)[0]
    cov_ab = float(np.mean(dab <= COVERAGE_RADIUS_M))
    cov_ba = float(np.mean(dba <= COVERAGE_RADIUS_M))
    m = dict(
        cov_min=min(cov_ab, cov_ba),
        dev_median=float(np.median(np.concatenate([dab, dba]))),
        dev_p95=float(max(np.percentile(dab, 95), np.percentile(dba, 95))),
        len_ratio=max(a.length_m, b.length_m) / max(1e-9, min(a.length_m, b.length_m)),
        start_gap_m=float(np.linalg.norm(a.xy[0] - b.xy[0])),
        end_gap_m=float(np.linalg.norm(a.xy[-1] - b.xy[-1])),
    )
    m['label'] = label(m)
    return m


def label(m: dict) -> str:
    if m['cov_min'] >= SAME_MIN_COVERAGE and m['dev_p95'] <= SAME_MAX_P95_M:
        return 'same'
    if m['cov_min'] <= DIFF_MAX_COVERAGE:
        return 'diff'
    return 'ambig'


# ---------------------------------------------------------------- long rides (#615)
#
# Long rides add a one-way relation: A is "part of" B when A on its own meets the
# 'same' bar against B (>= 90% of A within 50 m of B, A's p95 <= 75 m) but the
# pair isn't 'same' -- a sub-segment, or B is A plus an extension.
#
# Long-ride corpora have millions of pairs, so long_ride_candidates screens them
# first with an exact bound: a sample within 50 m of a dense point of B lies in
# the same or a neighbouring CELL_M cell, so the share of A's samples in cells
# next to B's cells bounds A's coverage by B from above. A pair is only
# compared when that bound exceeds DIFF_MAX_COVERAGE in some direction; every
# other pair is exactly 'diff' and part of nothing.

LONG_REFERENCE_VERSION = 1
CELL_M = 100.0


def compare_long(a: Track, b: Track) -> dict:
    """compare() plus the directed values and the part-of relation."""
    dab = b.tree.query(a.samples)[0]
    dba = a.tree.query(b.samples)[0]
    m = dict(
        cov_ab=float(np.mean(dab <= COVERAGE_RADIUS_M)),
        cov_ba=float(np.mean(dba <= COVERAGE_RADIUS_M)),
        p95_ab=float(np.percentile(dab, 95)),
        p95_ba=float(np.percentile(dba, 95)),
    )
    m['cov_min'] = min(m['cov_ab'], m['cov_ba'])
    m['dev_p95'] = max(m['p95_ab'], m['p95_ba'])
    m['label'] = label(m)
    a_in_b = m['cov_ab'] >= SAME_MIN_COVERAGE and m['p95_ab'] <= SAME_MAX_P95_M
    b_in_a = m['cov_ba'] >= SAME_MIN_COVERAGE and m['p95_ba'] <= SAME_MAX_P95_M
    m['part_of'] = ('' if m['label'] == 'same' else
                    'a_in_b' if a_in_b and not b_in_a else
                    'b_in_a' if b_in_a and not a_in_b else '')
    return m


def long_ride_candidates(coords_list, lat0):
    """(i, j) pairs, i < j, that could be anything but 'diff' (see above)."""
    from scipy import sparse
    n = len(coords_list)
    shift = 1 << 31  # cell (x, y) -> one int64 key
    rows_s, keys_s, vals_s, rows_n, keys_n = [], [], [], [], []
    for t, coords in enumerate(coords_list):
        xy = project(coords, lat0)
        samples, _ = resample(xy, SAMPLE_STEP_M)
        dense, _ = resample(xy, DENSE_STEP_M)
        c = np.floor(samples / CELL_M).astype(np.int64)
        k, counts = np.unique(c[:, 0] * shift + c[:, 1], return_counts=True)
        rows_s.append(np.full(len(k), t)); keys_s.append(k); vals_s.append(counts / len(samples))
        d = np.unique(np.floor(dense / CELL_M).astype(np.int64), axis=0)
        near = np.unique(np.concatenate([(d[:, 0] + dx) * shift + d[:, 1] + dy
                                         for dx in (-1, 0, 1) for dy in (-1, 0, 1)]))
        rows_n.append(np.full(len(near), t)); keys_n.append(near)
    cols, inv = np.unique(np.concatenate(keys_s + keys_n), return_inverse=True)
    n_s = sum(len(k) for k in keys_s)
    shares = sparse.csr_matrix((np.concatenate(vals_s), (np.concatenate(rows_s), inv[:n_s])),
                               shape=(n, len(cols)))
    near = sparse.csr_matrix((np.ones(len(inv) - n_s), (np.concatenate(rows_n), inv[n_s:])),
                             shape=(n, len(cols)))
    bound = (shares @ near.T).tocoo()  # [a, b] bounds the share of a within 50 m of b
    keep = (bound.data > DIFF_MAX_COVERAGE) & (bound.row != bound.col)
    pairs = {(min(a, b), max(a, b)) for a, b in zip(bound.row[keep].tolist(), bound.col[keep].tolist())}
    return sorted(pairs)
