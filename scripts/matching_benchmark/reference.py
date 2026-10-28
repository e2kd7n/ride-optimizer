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
