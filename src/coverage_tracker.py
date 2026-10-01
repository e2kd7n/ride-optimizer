"""
Coverage tracking for exploration route generation.

Computes which map tiles have been ridden based on cached Strava activity
GPS tracks. (An earlier osmnx-based road-segment coverage feature was
removed in #581 — it required osmnx/shapely, which were never added to
requirements.txt, so it could only ever 500 in production; superseded by
the tile-coverage/squadrat approach below.)
"""

import json
import hashlib
import os
from src.secure_logger import SecureLogger
import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import polyline as polyline_codec
import requests

from src.json_storage import secure_chmod

logger = SecureLogger(__name__)

TILE_ZOOM = 14              # "squadrat" granularity (squadrat.at / squadrat.com default)
SQUADRATINHO_ZOOM = 17      # "squadratinho" granularity — each squadrat = 8x8 squadratinhos
MAX_WATER_POLYGON_CACHES = 32  # cap on retained water_<hash>.json files
# Parsed water polygons kept in memory (LRU), as compact numpy ring arrays.
# Each water_*.json can be several MB on disk, so only the most recently
# explored areas stay resident -- sized for one loop/out-and-back area grid
# (up to 3x3 boxes, each with its own snapped fetch, #604) so a reload of
# the same area stops re-reading and re-parsing every file.
_WATER_POLYGON_MEMO_SIZE = 9
# On-disk format of water_<key>.json / coast_<key>.json (#603). Version 2
# water files hold stitched multipolygon groups (inner rings included); a
# pre-#603 water file is a bare list of rings and is still read as-is, so a
# deploy doesn't throw away every warm water cache and force the slow cold
# fetches. Coastline lives in its own, much smaller coast_<key>.json, so
# adding it to an area with a warm water cache costs only a coastline query.
_WATER_CACHE_VERSION = 2
# Wall-clock budget for the Overpass fetches behind one multi-box roadless
# request (#604). Each Overpass call's own timeout is capped at whatever is
# left of it, and boxes whose fetch would start after it runs out are
# reported as failed, so one request can't hold a worker thread for
# N x _OVERPASS_REQUEST_TIMEOUT_S. explore.js's 60 s timeout sits above it.
_ROADLESS_FETCH_BUDGET_S = 50
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Overpass's own internal query budget ([out:json][timeout:N]) and the
# client-side requests.post timeout. #562 lowered these from 25/30 s to
# 10/12 s, but a cold water fetch for a dense metro cell legitimately takes
# longer — measured from the Pi on 2026-09-30: 14.7 s and 28 MB for the
# 1x1 degree Chicago cell — so 12 s made it fail on every attempt. Raised
# back now that the cost of a slow endpoint is bounded elsewhere: the
# negative cache (#562), the concurrency cap (#598), the per-request budget
# above, and explore.js no longer retrying (#604). The client timeout stays
# a few seconds above the query timeout so we don't abort a query Overpass
# would've legitimately finished.
_OVERPASS_QUERY_TIMEOUT_S = 25
_OVERPASS_REQUEST_TIMEOUT_S = 30
# Short-lived "this endpoint just failed" marker (#562), keyed by endpoint
# rather than by bbox: an outage is global to the endpoint, but the query
# bbox changes on nearly every pin placement, so a bbox-keyed marker would
# almost always miss and every request would still pay the full timeout.
_OVERPASS_NEGATIVE_CACHE_TTL_S = 60
# Caps how many threads can be blocked inside an Overpass call at once
# (#598). The app runs a single gunicorn worker with only 4 threads total
# (gunicorn.conf.py), shared across every endpoint — page loads included.
# Without a cap, a handful of concurrent water-polygon cache misses (a
# user panning across several new areas, or Overpass itself running slow)
# can occupy every thread for up to _OVERPASS_REQUEST_TIMEOUT_S each,
# leaving nothing to serve unrelated requests — confirmed live: two test
# requests against a cold bbox queued 13.5 minutes before being serviced
# at all. Kept well under the thread count so fast, local-only endpoints
# (tile coverage from the warm index, page loads) always have headroom.
_MAX_CONCURRENT_OVERPASS_CALLS = 2
# How long a request waits for a free Overpass slot before giving up.
# Bounds the worst case to roughly this plus one request's own timeout,
# instead of queueing behind however many callers are already waiting.
_OVERPASS_SEMAPHORE_WAIT_S = 5


#: Placeholder value for a visited tile in a TileCoverage response (#579).
#: Every consumer (exploration-worker.js, explore.js's drawTileGrid) only
#: ever reads Object.keys(coverageData.visited) — the per-tile
#: {"first_ridden": ..., "activity_ids": [...]} detail the tile index keeps
#: internally was being shipped over the wire and silently discarded on
#: every request. At full-history scale (65k+ tiles observed in
#: production) that's several MB of wasted payload over cellular. The full
#: detail still lives in the on-disk/in-memory tile index (see
#: _build_or_update_tile_index) for incremental-update bookkeeping — only
#: the response-building path (get_tile_coverage/get_tile_coverage_all)
#: drops it before handing tiles to a caller.
_TRIMMED_TILE_VALUE = 1


@dataclass
class TileCoverage:
    """Result of tile coverage computation.

    `visited` maps tile key ("x,y") to a trimmed placeholder value (#579),
    not the tile index's full per-tile detail — see _TRIMMED_TILE_VALUE.
    """
    visited: Dict[str, int] = field(default_factory=dict)
    total_in_bounds: int = 0
    bounds: Optional[Tuple[float, float, float, float]] = None
    computed_at: str = ""
    zoom: int = TILE_ZOOM
    # True when this snapshot was served from the last-published tile index
    # instead of waiting on an in-progress rebuild for this zoom (#563) — a
    # cold rebuild (or a #560 startup pre-warm) can take multiple seconds,
    # and a caller on a short client-side timeout would rather get an
    # immediate, possibly-slightly-stale answer than block for the full
    # rebuild. False for every normal (fresh-or-freshly-built) response.
    stale: bool = False

    @property
    def visited_count(self) -> int:
        return len(self.visited)

    @property
    def coverage_pct(self) -> float:
        if self.total_in_bounds == 0:
            return 0.0
        # get_tile_coverage_all() (#556) trims outlier tiles out of `bounds`/
        # `total_in_bounds` while keeping the full ridden-tile set in `visited`
        # (so a genuinely-ridden far-away tile still shows up on the map) — so
        # visited_count can, in principle, include a handful of tiles outside
        # the reported bounds. Cap at 100% rather than surface a nonsensical
        # >100% "coverage" figure; the trimmed denominator is deliberately a
        # "core riding area" estimate, not a strict superset guarantee.
        return round(min(100.0, self.visited_count / self.total_in_bounds * 100), 1)

    def to_dict(self) -> dict:
        return {
            "visited": self.visited,
            "total_in_bounds": self.total_in_bounds,
            "visited_count": self.visited_count,
            "coverage_pct": self.coverage_pct,
            "bounds": self.bounds,
            "computed_at": self.computed_at,
            "zoom": self.zoom,
            "stale": self.stale,
        }


def _bbox_cache_key(bounds: Tuple[float, float, float, float]) -> str:
    """Stable short hash for a (rounded) bbox, used to key per-bbox caches."""
    rounded = tuple(round(v, 5) for v in bounds)
    raw = ",".join(str(v) for v in rounded)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# Grid size (degrees) that a water-polygon fetch's bounds get snapped to
# before keying/querying its on-disk cache (see _snap_bbox_to_grid). #562
# and #574 sped up what happens on a water-polygon cache miss (tighter
# Overpass timeouts, a bbox-prefilter ahead of the ray-cast) but neither
# touched _get_or_fetch_water_polygons's cache key itself, which is still
# the exact, pixel-precise viewport bbox explore.js sends on every
# pan/zoom — the same almost-always-miss pattern get_tile_coverage()'s
# docstring describes, just in the one cache that pattern wasn't fixed in.
# 0.5 is a bit larger than explore.js's COVERAGE_MAX_BBOX_DEGREES (0.45)
# so a typical single-viewport request lands inside one grid cell.
_WATER_POLYGON_GRID_DEGREES = 0.5


def _snap_bbox_to_grid(
    bounds: Tuple[float, float, float, float], grid_degrees: float
) -> Tuple[float, float, float, float]:
    """Expand `bounds` outward to the nearest enclosing multiple of
    `grid_degrees`, so nearby requests (a pan/zoom that only shifts the
    viewport slightly) resolve to the same snapped bbox and reuse the same
    cache entry instead of each keying its own."""
    south, west, north, east = bounds
    return (
        math.floor(south / grid_degrees) * grid_degrees,
        math.floor(west / grid_degrees) * grid_degrees,
        math.ceil(north / grid_degrees) * grid_degrees,
        math.ceil(east / grid_degrees) * grid_degrees,
    )


# Tukey's-fences trimming for _robust_tile_range (#556): a single activity
# geographically far from a rider's normal riding area (a trip, or a
# corrupted/erroneous GPS point) otherwise balloons get_tile_coverage_all()'s
# reported bounds to span the outlier, driving total_in_bounds into the tens
# of millions and coverage_pct to a permanent ~0% — verified on production
# data (5,849 visited tiles, but a bbox spanning nearly the whole globe).
_OUTLIER_IQR_MULTIPLIER = 3
# Below this many points, percentile statistics are too noisy to trust —
# just use the raw range (matches pre-fix behavior for small datasets).
_OUTLIER_MIN_SAMPLES = 20


def _robust_tile_range(coords: List[int]) -> Tuple[int, int]:
    """(min, max) of `coords`, excluding extreme outliers via Tukey's fences.

    Applied independently per axis (x, then y) since the bounding box this
    feeds is inherently an axis-aligned rectangle — an outlier tile's x and y
    don't need to be jointly extreme to distort that rectangle on one side.
    Falls back to the raw min/max when there are too few points to trust
    percentile statistics, or when the interquartile range is zero (a tight,
    degenerate cluster with no meaningful spread to trim).
    """
    if len(coords) < _OUTLIER_MIN_SAMPLES:
        return min(coords), max(coords)

    arr = np.asarray(coords)
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    if iqr == 0:
        return int(arr.min()), int(arr.max())

    lower = q1 - _OUTLIER_IQR_MULTIPLIER * iqr
    upper = q3 + _OUTLIER_IQR_MULTIPLIER * iqr
    filtered = arr[(arr >= lower) & (arr <= upper)]
    if filtered.size == 0:
        return int(arr.min()), int(arr.max())
    return int(filtered.min()), int(filtered.max())


def lat_lon_to_tile(lat: float, lon: float, zoom: int = TILE_ZOOM) -> Tuple[int, int]:
    """Convert latitude/longitude to slippy-map tile indices."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_bounds(x: int, y: int, zoom: int = TILE_ZOOM) -> Tuple[float, float, float, float]:
    """Convert tile indices to (south, west, north, east) bounds in degrees."""
    n = 2 ** zoom
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    south_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    north = math.degrees(north_rad)
    south = math.degrees(south_rad)
    return south, west, north, east


def _segment_tiles(lat1: float, lon1: float, lat2: float, lon2: float, zoom: int) -> List[Tuple[int, int]]:
    """
    Exact set of tiles a GPS segment passes through, via grid traversal
    (2D DDA / "supercover line", per Amanatides & Woo) in continuous
    tile-space rather than sampling points at a fixed interval.

    This replaces distance-based interpolation for tile coverage: instead
    of guessing how finely to resample a segment so no tile gets skipped
    (and re-tuning that guess per zoom level), it walks the exact set of
    grid cells the line crosses — O(tiles crossed) instead of O(samples),
    and correct at any zoom without a tunable interval. This is what makes
    squadratinho (zoom 17) coverage tractable: a sparse, simplified summary
    polyline with long segments no longer needs thousands of interpolated
    samples per segment, just the handful of tiles it actually crosses.
    """
    n = 2 ** zoom
    fx1 = (lon1 + 180.0) / 360.0 * n
    fx2 = (lon2 + 180.0) / 360.0 * n
    fy1 = (1.0 - math.asinh(math.tan(math.radians(lat1))) / math.pi) / 2.0 * n
    fy2 = (1.0 - math.asinh(math.tan(math.radians(lat2))) / math.pi) / 2.0 * n

    x0, y0 = int(fx1), int(fy1)
    x1, y1 = int(fx2), int(fy2)

    if x0 == x1 and y0 == y1:
        return [(x0, y0)]

    dx, dy = fx2 - fx1, fy2 - fy1
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1

    if dx != 0:
        t_delta_x = abs(1.0 / dx)
        t_max_x = ((x0 + (1 if step_x > 0 else 0)) - fx1) / dx
    else:
        t_delta_x = t_max_x = float("inf")

    if dy != 0:
        t_delta_y = abs(1.0 / dy)
        t_max_y = ((y0 + (1 if step_y > 0 else 0)) - fy1) / dy
    else:
        t_delta_y = t_max_y = float("inf")

    x, y = x0, y0
    tiles = [(x, y)]
    # Safety cap: a single segment shouldn't legitimately cross more tiles
    # than this even at squadratinho zoom; guards against pathological
    # data (e.g. a corrupted point pair spanning half the globe).
    for _ in range(20_000):
        if (x, y) == (x1, y1):
            break
        if t_max_x < t_max_y:
            x += step_x
            t_max_x += t_delta_x
        else:
            y += step_y
            t_max_y += t_delta_y
        tiles.append((x, y))

    return tiles


def _activity_tiles(coords: List[Tuple[float, float]], zoom: int) -> Set[Tuple[int, int]]:
    """All tiles an activity's decoded GPS track passes through, exactly."""
    if not coords:
        return set()
    if len(coords) == 1:
        lat, lon = coords[0]
        return {lat_lon_to_tile(lat, lon, zoom)}

    tiles: Set[Tuple[int, int]] = set()
    for i in range(1, len(coords)):
        lat1, lon1 = coords[i - 1]
        lat2, lon2 = coords[i]
        tiles.update(_segment_tiles(lat1, lon1, lat2, lon2, zoom))
    return tiles


# ── Water geometry (#525, #603, #604) ─────────────────────────────
#
# Pure-Python/numpy helpers that turn an Overpass water/coastline response
# into "water groups" — lists of rings combined under the even-odd rule —
# and rasterize those groups onto a slippy-map tile grid.


def _normalize_boxes(bounds) -> List[Tuple[float, float, float, float]]:
    """Accept one (south, west, north, east) box or a list of them."""
    if not bounds:
        return []
    if isinstance(bounds[0], (int, float)):
        return [tuple(bounds)]
    return [tuple(b) for b in bounds]


def _pt_key(pt) -> Tuple[float, float]:
    """Endpoint identity for stitching ways — OSM coordinates are stored at
    1e-7 degree precision, so two ways sharing a node round to the same key."""
    return (round(pt[0], 7), round(pt[1], 7))


def _join_ways(lines: List[list], directed: bool) -> List[list]:
    """Stitch ways that share endpoints into longer chains/rings.

    `directed` keeps every way's own direction (coastline ways, whose
    direction encodes which side is water); otherwise a way may be reversed
    to fit (multipolygon member ways, which OSM doesn't orient consistently).
    """
    chains = {i: list(line) for i, line in enumerate(lines) if len(line) >= 2}
    starts: Dict[Tuple[float, float], Set[int]] = {}
    ends: Dict[Tuple[float, float], Set[int]] = {}
    for i, c in chains.items():
        starts.setdefault(_pt_key(c[0]), set()).add(i)
        ends.setdefault(_pt_key(c[-1]), set()).add(i)

    def detach(i: int) -> list:
        c = chains.pop(i)
        starts[_pt_key(c[0])].discard(i)
        ends[_pt_key(c[-1])].discard(i)
        return c

    out = []
    while chains:
        chain = detach(next(iter(chains)))
        # Extend the tail, then the head, until closed or nothing fits.
        while _pt_key(chain[0]) != _pt_key(chain[-1]):
            k = _pt_key(chain[-1])
            if starts.get(k):
                chain.extend(detach(next(iter(starts[k])))[1:])
            elif not directed and ends.get(k):
                chain.extend(detach(next(iter(ends[k])))[::-1][1:])
            else:
                break
        while _pt_key(chain[0]) != _pt_key(chain[-1]):
            k = _pt_key(chain[0])
            if ends.get(k):
                chain[:0] = detach(next(iter(ends[k])))[:-1]
            elif not directed and starts.get(k):
                chain[:0] = detach(next(iter(starts[k])))[::-1][:-1]
            else:
                break
        out.append(chain)
    return out


def _parse_overpass_water(elements: list) -> Tuple[List[list], List[list]]:
    """Overpass `out geom` elements -> (water groups, coastline chains).

    A water group is a list of [lat, lon] rings (one for a `natural=water`
    way; a multipolygon relation's stitched outer and inner rings); a
    coastline chain is a directed polyline with land on the left and water
    on the right. Coordinates are rounded to 1e-6 degrees (~10 cm) to keep
    the cache files small.
    """
    def pts_of(geometry):
        return [[round(pt["lat"], 6), round(pt["lon"], 6)] for pt in geometry]

    water: List[list] = []
    coastline: List[list] = []
    for element in elements:
        etype = element.get("type")
        tags = element.get("tags") or {}
        if etype == "way" and element.get("geometry"):
            pts = pts_of(element["geometry"])
            if tags.get("natural") == "coastline":
                if len(pts) >= 2:
                    coastline.append(pts)
            elif len(pts) >= 3:
                water.append([pts])
        elif etype == "relation":
            members = [
                pts_of(m["geometry"])
                for m in element.get("members", [])
                if m.get("role") in ("outer", "inner") and m.get("geometry")
            ]
            rings = [r for r in _join_ways(members, directed=False) if len(r) >= 3]
            if rings:
                water.append(rings)
    return water, _join_ways(coastline, directed=True)


def _water_groups_from_cache(raw) -> Optional[List[list]]:
    """Water groups from a water_<key>.json body: the current versioned
    format, or a pre-#603 bare list of rings (each its own group, exactly as
    it was rasterized before). None for anything unreadable."""
    if isinstance(raw, list):
        return [[ring] for ring in raw]
    if isinstance(raw, dict) and raw.get("version") == _WATER_CACHE_VERSION:
        return raw.get("water", [])
    return None


def _coastline_from_cache(raw) -> Optional[List[list]]:
    if isinstance(raw, dict) and raw.get("version") == _WATER_CACHE_VERSION:
        return raw.get("coastline", [])
    return None


def _ring_bbox(rings: List[np.ndarray]) -> Tuple[float, float, float, float]:
    """(south, west, north, east) of a group of rings."""
    lats = np.concatenate([r[:, 0] for r in rings])
    lons = np.concatenate([r[:, 1] for r in rings])
    return float(lats.min()), float(lons.min()), float(lats.max()), float(lons.max())


def _build_water_groups(
    water: List[list], coastline: List[list], rect: Tuple[float, float, float, float],
) -> list:
    """Water groups + coastline chains -> [(bbox, [ring arrays]), ...] ready
    to rasterize. Coastline chains become one extra group, clipped to `rect`
    (the snapped fetch rectangle)."""
    groups = []
    for group in water:
        rings = [np.asarray(r, dtype=float) for r in group if len(r) >= 3]
        if rings:
            groups.append((_ring_bbox(rings), rings))
    coast_rings = _coastline_water_rings(coastline, rect)
    if coast_rings:
        rings = [np.asarray(r, dtype=float) for r in coast_rings]
        groups.append((_ring_bbox(rings), rings))
    return groups


def _signed_area(ring: list) -> float:
    """Shoelace area in (lon, lat) space: > 0 counter-clockwise."""
    area = 0.0
    n = len(ring)
    for i in range(n):
        y1, x1 = ring[i]
        y2, x2 = ring[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def _clip_segment(p, q, rect) -> Optional[Tuple[float, float]]:
    """Liang-Barsky: the [t0, t1] parameter range of segment p->q inside
    `rect`, or None if it misses entirely."""
    south, west, north, east = rect
    y0, x0 = p
    y1, x1 = q
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for pk, qk in ((-dx, x0 - west), (dx, east - x0), (-dy, y0 - south), (dy, north - y0)):
        if pk == 0:
            if qk < 0:
                return None
            continue
        r = qk / pk
        if pk < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return None
    return t0, t1


def _clip_polyline(points: list, rect) -> List[list]:
    """Split a polyline into its pieces inside `rect`."""
    pieces: List[list] = []
    cur: Optional[list] = None
    for p, q in zip(points, points[1:]):
        res = _clip_segment(p, q, rect)
        if res is None:
            if cur is not None:
                pieces.append(cur)
                cur = None
            continue
        t0, t1 = res
        a = (p[0] + (q[0] - p[0]) * t0, p[1] + (q[1] - p[1]) * t0)
        b = (p[0] + (q[0] - p[0]) * t1, p[1] + (q[1] - p[1]) * t1)
        if cur is None:
            cur = [a]
        cur.append(b)
        if t1 < 1.0:
            pieces.append(cur)
            cur = None
    if cur is not None:
        pieces.append(cur)
    return pieces


def _coastline_water_rings(chains: List[list], rect) -> List[list]:
    """Close directed coastline chains (water on the right) into water-side
    rings within `rect` (#603).

    Chains are clipped to the rectangle; each clipped piece enters and exits
    through the rectangle boundary. Starting from a piece's exit, walking
    the boundary clockwise keeps the water on the right, so the ring runs
    along the boundary (picking up any corners on the way) to the next
    piece's entry, follows that piece, and so on until it closes. Chains
    that close inside the rectangle are kept as-is: clockwise is enclosed
    water, counter-clockwise an island. With no chain crossing the boundary
    the rectangle is all water if its outermost closed ring is an island,
    and otherwise has no coastline water beyond those closed rings.

    Pieces that start or end inside the rectangle are broken data (a
    coastline gap) and are dropped; all returned rings form one even-odd
    group. A rectangle with no coastline at all — say, a snapped cell
    entirely in the middle of Lake Michigan — can't be told apart from
    inland and yields nothing.
    """
    south, west, north, east = rect
    width, height = east - west, north - south
    perimeter = 2 * (width + height)
    eps = 1e-9 * max(1.0, width, height)

    def on_boundary(pt) -> bool:
        lat, lon = pt
        return min(abs(lat - north), abs(lat - south), abs(lon - east), abs(lon - west)) <= eps

    def inside(pt) -> bool:
        return south <= pt[0] <= north and west <= pt[1] <= east

    def perimeter_pos(pt) -> float:
        # Clockwise from the NW corner: top edge east, right edge south,
        # bottom edge west, left edge north.
        lat, lon = pt
        d = [abs(lat - north), abs(lon - east), abs(lat - south), abs(lon - west)]
        edge = d.index(min(d))
        if edge == 0:
            return lon - west
        if edge == 1:
            return width + (north - lat)
        if edge == 2:
            return width + height + (east - lon)
        return 2 * width + height + (lat - south)

    corners = [
        (0.0, (north, west)),
        (width, (north, east)),
        (width + height, (south, east)),
        (2 * width + height, (south, west)),
    ]

    closed_rings: List[list] = []
    pieces: List[list] = []
    for chain in chains:
        if len(chain) < 2:
            continue
        pts = [tuple(p) for p in chain]
        if _pt_key(pts[0]) == _pt_key(pts[-1]) and len(pts) >= 4:
            ring = pts[:-1]
            outside_idx = next((i for i, p in enumerate(ring) if not inside(p)), None)
            if outside_idx is None:
                closed_rings.append(ring)
                continue
            # Rotate so the ring starts (and ends) outside the rectangle —
            # then every clipped piece enters and exits via the boundary.
            pts = ring[outside_idx:] + ring[:outside_idx] + [ring[outside_idx]]
        for piece in _clip_polyline(pts, rect):
            if len(piece) < 2 or all(_pt_key(p) == _pt_key(piece[0]) for p in piece):
                continue
            if not (on_boundary(piece[0]) and on_boundary(piece[-1])):
                logger.debug("Dropping coastline piece with an end inside the clip rectangle")
                continue
            pieces.append(piece)

    rings: List[list] = []
    if pieces:
        t_in = [perimeter_pos(p[0]) for p in pieces]
        t_out = [perimeter_pos(p[-1]) for p in pieces]
        used = [False] * len(pieces)
        for start in range(len(pieces)):
            if used[start]:
                continue
            ring: List[tuple] = []
            cur = start
            for _ in range(len(pieces) + 1):
                used[cur] = True
                ring.extend(pieces[cur])
                best, best_d = start, (t_in[start] - t_out[cur]) % perimeter
                for j in range(len(pieces)):
                    if used[j]:
                        continue
                    d = (t_in[j] - t_out[cur]) % perimeter
                    if d < best_d:
                        best, best_d = j, d
                for d_corner, corner in sorted(
                    ((ct - t_out[cur]) % perimeter, cpt) for ct, cpt in corners
                ):
                    if 0 < d_corner < best_d:
                        ring.append(corner)
                if best == start:
                    break
                cur = best
            if len(ring) >= 3:
                rings.append(ring)
        rings.extend(closed_rings)
    elif closed_rings:
        rings.extend(closed_rings)
        outermost = max(closed_rings, key=lambda r: abs(_signed_area(r)))
        if _signed_area(outermost) > 0:  # an island: the sea surrounds it
            rings.append([(north, west), (north, east), (south, east), (south, west)])
    return rings


def _rasterize_water_groups(
    groups: List[List[np.ndarray]], zoom: int,
    min_tx: int, max_tx: int, min_ty: int, max_ty: int,
) -> np.ndarray:
    """Boolean [ty, tx] mask of tiles whose center falls inside water.

    Each group is a list of rings combined under the even-odd rule (so an
    island ring punches a hole); groups are unioned. Same half-open
    crossing rule as a classic ray-cast point-in-polygon test, but done as
    a numpy scanline — every ring edge is intersected with each tile row it
    spans once, instead of every tile being tested against every edge
    (#604). Each row's crossings, sorted by longitude and paired up, give
    the water intervals; a per-row difference array unions them.
    """
    n_rows, n_cols = max_ty - min_ty + 1, max_tx - min_tx + 1
    mask = np.zeros((max(n_rows, 0), max(n_cols, 0)), dtype=bool)
    if n_rows <= 0 or n_cols <= 0 or not groups:
        return mask

    row_lats = np.array([
        (b[0] + b[2]) / 2 for b in (tile_to_bounds(min_tx, ty, zoom) for ty in range(min_ty, max_ty + 1))
    ])
    col_lons = np.array([
        (b[1] + b[3]) / 2 for b in (tile_to_bounds(tx, min_ty, zoom) for tx in range(min_tx, max_tx + 1))
    ])
    asc_lats = row_lats[::-1]  # rows run north -> south; searchsorted needs ascending

    a_parts, b_parts, g_parts = [], [], []
    for gid, rings in enumerate(groups):
        for ring in rings:
            if len(ring) < 3:
                continue
            a_parts.append(ring)
            b_parts.append(np.roll(ring, -1, axis=0))
            g_parts.append(np.full(len(ring), gid))
    if not a_parts:
        return mask
    a = np.concatenate(a_parts)
    b = np.concatenate(b_parts)
    gid = np.concatenate(g_parts)
    ya, xa, yb, xb = a[:, 0], a[:, 1], b[:, 0], b[:, 1]

    # An edge crosses a row's center latitude when min(ya, yb) <= lat < max(ya, yb).
    i0 = np.searchsorted(asc_lats, np.minimum(ya, yb), side="left")
    i1 = np.searchsorted(asc_lats, np.maximum(ya, yb), side="left")
    counts = i1 - i0
    total = int(counts.sum())
    if total == 0:
        return mask
    edge = np.repeat(np.arange(len(counts)), counts)
    asc_idx = np.repeat(i0, counts) + (np.arange(total) - np.repeat(np.cumsum(counts) - counts, counts))
    lat = asc_lats[asc_idx]
    x = xa[edge] + (xb[edge] - xa[edge]) * (lat - ya[edge]) / (yb[edge] - ya[edge])
    row = n_rows - 1 - asc_idx

    # Every (group, row) has an even number of crossings, so after sorting
    # consecutive pairs never straddle two groups or rows.
    order = np.lexsort((x, row, gid[edge]))
    x, row = x[order], row[order]
    x0, x1, r = x[0::2], x[1::2], row[0::2]
    # Tile centers c with x0 <= c < x1 are inside.
    c0 = np.searchsorted(col_lons, x0, side="left")
    c1 = np.searchsorted(col_lons, x1, side="left")
    keep = c1 > c0
    diff = np.zeros((n_rows, n_cols + 1), dtype=np.int32)
    np.add.at(diff, (r[keep], c0[keep]), 1)
    np.add.at(diff, (r[keep], c1[keep]), -1)
    return np.cumsum(diff, axis=1)[:, :n_cols] > 0


def _mask_to_runs(mask: np.ndarray, min_tx: int, min_ty: int) -> List[List[int]]:
    """[[y, x_start, x_end], ...] (x inclusive) for each horizontal run of
    True cells in a [ty, tx] mask."""
    if mask.size == 0 or not mask.any():
        return []
    padded = np.zeros((mask.shape[0], mask.shape[1] + 2), dtype=np.int8)
    padded[:, 1:-1] = mask
    d = np.diff(padded, axis=1)
    run_starts = np.argwhere(d == 1)
    run_ends = np.argwhere(d == -1)
    return [
        [int(min_ty + r), int(min_tx + c0), int(min_tx + c1 - 1)]
        for (r, c0), (_, c1) in zip(run_starts, run_ends)
    ]


class CoverageTracker:
    """Compute tile coverage from Strava activity GPS data."""

    def __init__(self, config):
        self.config = config
        self.zoom = config.get("exploration.tile_zoom_level", TILE_ZOOM)
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        removed = self._sweep_legacy_coverage_tile_files()
        if removed:
            logger.info("Removed %d legacy coverage_tiles_*.json cache file(s) (#555)", removed)
        self._activities_cache: Optional[List[dict]] = None
        # In-memory copy of each zoom's tile index (see _build_or_update_tile_index),
        # keyed by zoom. Avoids re-reading/re-parsing the on-disk index on every
        # request once a worker thread has built it once.
        self._tile_index_cache: Dict[int, dict] = {}
        # Per-zoom locks (#558) rather than one lock shared across every
        # zoom — a cold rebuild at one zoom (e.g. squadratinho, zoom 17)
        # would otherwise serialize reads/writes at an already-warm zoom
        # (squadrat, zoom 14) behind it. Lazily created per zoom by
        # _get_zoom_lock(); _tile_index_locks_lock guards only that
        # lazy-creation step, never held across a build/read.
        self._tile_index_locks: Dict[int, threading.Lock] = {}
        self._tile_index_locks_lock = threading.Lock()
        # Negative cache for Overpass failures (#562): endpoint -> wall-clock
        # timestamp until which fresh requests fail fast instead of retrying.
        self._overpass_failure_until: Dict[str, float] = {}
        self._overpass_failure_lock = threading.Lock()
        # Per-(snapped-bbox) locks so concurrent requests for the same water-
        # polygon cache key (e.g. explore.js "both" mode's zoom=14 and
        # zoom=17 roadless-tile calls, which share identical bounds) share
        # one Overpass fetch instead of each firing its own redundant query
        # and racing to write the same cache file. Same lazy-creation
        # pattern as _get_zoom_lock/_tile_index_locks_lock above.
        self._water_polygon_locks: Dict[str, threading.Lock] = {}
        self._water_polygon_locks_lock = threading.Lock()
        # key -> ((mtime_ns, size), water groups); see _WATER_POLYGON_MEMO_SIZE.
        self._water_polygon_memo: "OrderedDict[str, Tuple[Tuple[int, int], list]]" = OrderedDict()
        self._water_polygon_memo_lock = threading.Lock()
        # Caps concurrent Overpass calls across *all* bboxes (#598) — the
        # per-key lock above only de-dups requests for the *same* bbox;
        # this bounds how many different-bbox calls can block a thread at
        # once, so the app's small shared thread pool always keeps headroom
        # for fast, local-only endpoints even when several new areas are
        # queried in quick succession or Overpass itself is slow.
        self._overpass_semaphore = threading.BoundedSemaphore(_MAX_CONCURRENT_OVERPASS_CALLS)

    # ------------------------------------------------------------------
    # Activity loading
    # ------------------------------------------------------------------

    def _load_activities(self) -> List[dict]:
        """Load cached Strava activities (lazy, cached in memory per process)."""
        if self._activities_cache is not None:
            return self._activities_cache

        path = Path("data/cache/activities.json")
        if not path.exists():
            logger.warning("No activities cache found at %s", path)
            self._activities_cache = []
            return self._activities_cache

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            activities = data if isinstance(data, list) else data.get("activities", [])
            ride_types = {"Ride", "EBikeRide", "GravelRide", "MountainBikeRide"}
            activities = [
                a for a in activities
                if a.get("type") in ride_types or a.get("sport_type") in ride_types
            ]
            logger.info("Loaded %d ride activities for coverage analysis", len(activities))
            self._activities_cache = activities
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load activities: %s", exc)
            self._activities_cache = []

        return self._activities_cache

    def _decode_activity_coords(self, activity: dict) -> List[Tuple[float, float]]:
        """Decode an activity's polyline to a list of (lat, lon) tuples."""
        encoded = activity.get("polyline")
        if not encoded:
            return []
        try:
            return polyline_codec.decode(encoded)
        except Exception:
            return []

    def tiles_crossed_by_path(
        self, coords: List[Tuple[float, float]], zoom: int
    ) -> Set[Tuple[int, int]]:
        """All tiles an arbitrary lat/lon path crosses, exactly.

        Same exact grid-traversal ground truth used for scoring recorded
        activities (`_activity_tiles`), exposed so a *planned* route (e.g. an
        ORS road-route polyline that hasn't been ridden yet) can be checked
        against it before claiming tile coverage in the UI.
        """
        return _activity_tiles(coords, zoom)

    # ------------------------------------------------------------------
    # Tile coverage
    # ------------------------------------------------------------------

    def _tile_index_path(self, zoom: int) -> Path:
        return self.cache_dir / f"tile_index_{zoom}.json"

    def _load_tile_index_from_disk(self, zoom: int) -> Optional[dict]:
        path = self._tile_index_path(zoom)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "indexed_activity_ids": set(data["indexed_activity_ids"]),
                "tiles": data["tiles"],
            }
        except (json.JSONDecodeError, OSError, KeyError):
            logger.warning("Tile index cache at %s is missing/corrupt — will rebuild", path)
            return None

    def _write_tile_index_atomic(self, zoom: int, index: dict) -> None:
        """Atomic write (temp file + os.replace) so a mid-write crash or a
        concurrent reader never observes a torn/partial JSON file."""
        path = self._tile_index_path(zoom)
        payload = {
            "indexed_activity_ids": sorted(index["indexed_activity_ids"]),
            "tiles": index["tiles"],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp_path = path.with_name(f"{path.name}.tmp{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            secure_chmod(tmp_path)
            os.replace(tmp_path, path)
            secure_chmod(path)
        except OSError as exc:
            logger.warning("Failed to write tile index cache: %s", exc)
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def _get_zoom_lock(self, zoom: int) -> threading.Lock:
        """Return the lock guarding zoom `zoom`'s tile index, creating it on
        first use (#558). Per-zoom rather than one global lock so a cold
        rebuild at one zoom doesn't block reads/writes at an already-warm
        zoom. The outer unlocked check avoids taking
        _tile_index_locks_lock on every call once a zoom's lock exists.
        """
        lock = self._tile_index_locks.get(zoom)
        if lock is not None:
            return lock
        with self._tile_index_locks_lock:
            lock = self._tile_index_locks.get(zoom)
            if lock is None:
                lock = threading.Lock()
                self._tile_index_locks[zoom] = lock
            return lock

    def _get_water_polygon_lock(self, key: str) -> threading.Lock:
        """Return the lock guarding water-polygon cache key `key` (a snapped
        bbox's cache key), creating it on first use. Per-key rather than one
        global lock so concurrent requests for different areas stay
        independent; only requests for the same snapped bbox serialize
        behind one Overpass fetch."""
        lock = self._water_polygon_locks.get(key)
        if lock is not None:
            return lock
        with self._water_polygon_locks_lock:
            lock = self._water_polygon_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._water_polygon_locks[key] = lock
            return lock

    def _build_or_update_tile_index(self, zoom: int) -> dict:
        """Return {"indexed_activity_ids": set, "tiles": dict} for `zoom`,
        the full set of tiles ever ridden at that zoom level, keyed "x,y".

        Replaces the old per-bbox rescan-from-scratch cache: every activity's
        polyline is decoded and folded into this index at most once (tracked
        by activity id, not a "last id" watermark — data_fetcher.py rewrites
        activities.json as a merged-and-resorted whole on every fetch, so a
        watermark would miss activities inserted anywhere but the tail).
        Bbox queries (get_tile_coverage) then just filter this flat dict by
        tile range — no polyline decoding on the request path at all once the
        index is warm.

        invalidate_caches() now runs automatically after every activity
        fetch/analyze/backfill (see the three call sites in
        app/api/data_bp.py) and clears the in-memory index/activities cache
        so this call reloads from disk and diffs against fresh data (#571).
        This also self-heals independent of that, on *every* call, by
        diffing the currently-loaded activity ids against what's indexed
        rather than assuming the index is fresh just because it exists on
        disk — that still matters for e.g. a long-running dev process, or
        any other path that touches activities.json without going through
        invalidate_caches().

        Guarded by a per-zoom lock (#558), not one lock shared across every
        zoom, so a cold rebuild at one zoom doesn't serialize reads/writes
        at an already-warm zoom behind it. Updates are copy-on-write: when
        new activities need folding in, this builds a *new* tiles dict (and
        a new entry dict for any tile a new activity touches) instead of
        mutating the previously-published one in place, then publishes the
        result with a single `self._tile_index_cache[zoom] = index`
        assignment — atomic under the GIL. A caller that grabbed a
        reference to the old `index` before this ran (e.g. get_tile_coverage(),
        which iterates index["tiles"] *after* this lock is released) keeps
        iterating a snapshot that's never mutated out from under it, no
        matter what runs next. This is what fixes the dict-mutated-during-
        iteration race from #559 (merged into #558): under the old design,
        a concurrent rebuild mutated the exact same dict object a reader
        elsewhere was iterating.
        """
        with self._get_zoom_lock(zoom):
            return self._build_or_update_tile_index_locked(zoom)

    def _build_or_update_tile_index_locked(self, zoom: int) -> dict:
        """Body of _build_or_update_tile_index(), assuming the caller
        already holds self._get_zoom_lock(zoom). Split out so
        _get_tile_index_or_stale() (#563) can do its own non-blocking
        `acquire` and then run the exact same build logic, instead of
        duplicating it."""
        index = self._tile_index_cache.get(zoom)
        if index is None:
            index = self._load_tile_index_from_disk(zoom)
        if index is None:
            index = {"indexed_activity_ids": set(), "tiles": {}}

        activities = self._load_activities()
        current_ids = {a.get("id") for a in activities if a.get("id") is not None}
        new_ids = current_ids - index["indexed_activity_ids"]

        if new_ids:
            start = time.monotonic()
            decoded_count = 0
            # Shallow copies: existing tile entries are shared objects
            # with the previously-published index until this loop
            # touches them, at which point a *new* entry dict/list is
            # substituted in new_tiles rather than the shared one being
            # mutated in place (see docstring above).
            new_tiles = dict(index["tiles"])
            new_indexed_ids = set(index["indexed_activity_ids"])
            for act in activities:
                act_id = act.get("id")
                if act_id not in new_ids:
                    continue
                coords = self._decode_activity_coords(act)
                decoded_count += 1
                if coords:
                    act_date = act.get("start_date", "")
                    for tx, ty in _activity_tiles(coords, zoom):
                        key = f"{tx},{ty}"
                        entry = new_tiles.get(key)
                        if entry is None:
                            new_tiles[key] = {"first_ridden": act_date, "activity_ids": [act_id]}
                        elif act_id not in entry["activity_ids"]:
                            new_tiles[key] = {
                                "first_ridden": entry["first_ridden"],
                                "activity_ids": entry["activity_ids"] + [act_id],
                            }
                new_indexed_ids.add(act_id)

            index = {"indexed_activity_ids": new_indexed_ids, "tiles": new_tiles}

            logger.info(
                "Tile index (zoom=%d) updated: %d new activities decoded in %.2fs (total indexed=%d, tiles=%d)",
                zoom, decoded_count, time.monotonic() - start,
                len(index["indexed_activity_ids"]), len(index["tiles"]),
            )
            self._write_tile_index_atomic(zoom, index)

        self._tile_index_cache[zoom] = index
        return index

    def _get_tile_index_or_stale(self, zoom: int) -> Tuple[dict, bool]:
        """Non-blocking tile-index fetch for the request path (#563).

        Returns (index, stale). If zoom's lock is free, this acquires it
        and runs the normal build/update in-line (stale=False) — identical
        to calling _build_or_update_tile_index(zoom) directly. If the lock
        is already held (a rebuild — cold start, #560 pre-warm, or another
        request — is in progress for this zoom), this does NOT block:
        it immediately returns the last-published in-memory snapshot
        (stale=True) so the caller can respond right away instead of
        waiting out the full rebuild. The rebuild already in progress
        continues in the background under the lock as before and will
        publish a fresh snapshot for the next request.

        Falls back to the normal blocking build only when there is no
        snapshot at all yet to serve as "stale" — a genuinely cold zoom
        with two first-requests racing each other, where returning nothing
        would be worse than a brief wait.
        """
        lock = self._get_zoom_lock(zoom)
        if lock.acquire(blocking=False):
            try:
                return self._build_or_update_tile_index_locked(zoom), False
            finally:
                lock.release()

        cached = self._tile_index_cache.get(zoom)
        if cached is not None:
            logger.info(
                "get_tile_coverage(zoom=%d): rebuild already in progress — serving stale snapshot (%d tiles)",
                zoom, len(cached["tiles"]),
            )
            return cached, True

        logger.info(
            "get_tile_coverage(zoom=%d): rebuild in progress and no snapshot published yet — blocking",
            zoom,
        )
        return self._build_or_update_tile_index(zoom), False

    def get_tile_coverage(
        self,
        bounds: Optional[Tuple[float, float, float, float]],
        zoom: Optional[int] = None,
    ) -> TileCoverage:
        """
        Compute tile coverage within a bounding box.

        Filters the persisted, incrementally-updated per-zoom tile index
        (`_build_or_update_tile_index`) down to `bounds`, instead of
        rescanning every activity per viewport. The viewport bbox changes on
        nearly every request (pan/zoom/new start point), so caching per-bbox
        on disk was an almost-always-miss cache that forced a full
        recompute — decoding every activity's polyline and walking its
        tiles — on effectively every Explore page load.

        Args:
            bounds: (south, west, north, east) in degrees, or None for the
                full-history view (delegates to get_tile_coverage_all).
            zoom: tile zoom level — TILE_ZOOM (squadrat) or SQUADRATINHO_ZOOM
                (squadratinho). Defaults to the configured zoom.

        Returns:
            TileCoverage with visited tile data and stats
        """
        zoom = zoom or self.zoom
        if bounds is None:
            return self.get_tile_coverage_all(zoom=zoom)

        start = time.monotonic()
        index, stale = self._get_tile_index_or_stale(zoom)

        south, west, north, east = bounds
        min_tx, min_ty = lat_lon_to_tile(north, west, zoom)
        max_tx, max_ty = lat_lon_to_tile(south, east, zoom)

        visited: Dict[str, int] = {}
        for key in index["tiles"]:
            tx_str, ty_str = key.split(",")
            tx, ty = int(tx_str), int(ty_str)
            if min_tx <= tx <= max_tx and min_ty <= ty <= max_ty:
                visited[key] = _TRIMMED_TILE_VALUE

        total_tiles = (max_tx - min_tx + 1) * (max_ty - min_ty + 1)

        logger.info(
            "get_tile_coverage(zoom=%d) served from index in %.3fs "
            "(%d visited-in-bbox / %d total tiles indexed, stale=%s)",
            zoom, time.monotonic() - start, len(visited), len(index["tiles"]), stale,
        )

        return TileCoverage(
            visited=visited,
            total_in_bounds=max(total_tiles, 1),
            bounds=bounds,
            computed_at=datetime.now(timezone.utc).isoformat(),
            zoom=zoom,
            stale=stale,
        )

    def get_tile_coverage_all(self, zoom: Optional[int] = None) -> TileCoverage:
        """
        Compute tile coverage across ALL activities (no bounds filter).

        Useful for getting overall stats and the full visited tile set.
        """
        zoom = zoom or self.zoom
        index = self._build_or_update_tile_index(zoom)
        visited = {key: _TRIMMED_TILE_VALUE for key in index["tiles"]}

        bounds = None
        total_in_bounds = len(visited)
        if visited:
            xs = [int(k.split(",")[0]) for k in visited]
            ys = [int(k.split(",")[1]) for k in visited]
            # Robust to outlier tiles (#556) — see _robust_tile_range.
            min_tx, max_tx = _robust_tile_range(xs)
            min_ty, max_ty = _robust_tile_range(ys)
            south, west, _, _ = tile_to_bounds(min_tx, max_ty, zoom)
            _, _, north, east = tile_to_bounds(max_tx, min_ty, zoom)
            bounds = (south, west, north, east)
            total_in_bounds = max((max_tx - min_tx + 1) * (max_ty - min_ty + 1), 1)

        return TileCoverage(
            visited=visited,
            total_in_bounds=total_in_bounds,
            bounds=bounds,
            computed_at=datetime.now(timezone.utc).isoformat(),
            zoom=zoom,
        )

    # ------------------------------------------------------------------
    # Water polygons (open-water tile exclusion, #525)
    # ------------------------------------------------------------------

    def _get_or_fetch_water_features(
        self,
        bounds: Tuple[float, float, float, float],
        deadline: Optional[float] = None,
    ) -> List[Tuple[Tuple[float, float, float, float], List[np.ndarray]]]:
        """Load cached open-water geometry for `bounds`, querying Overpass
        for whatever isn't cached yet.

        Returns a list of "water groups", each a (bbox, rings) pair where
        `rings` is a list of (N, 2) [lat, lon] arrays combined under the
        even-odd rule (see _rasterize_water_groups). Three sources feed it:

        * a `natural=water` way — one group, one ring;
        * a `natural=water` relation — one group holding its outer AND
          inner rings, with member ways stitched into real rings first
          (_join_ways), so an island inside a lake stays land and a lake
          whose outline is split across several member ways is one ring
          instead of each piece being closed with its own straight chord;
        * `natural=coastline` ways (#603) — the Great Lakes and every
          sea/ocean coast are mapped as open coastline lines (water on the
          right), never as a water polygon. They're turned into one group of
          water-side rings clipped to the snapped fetch rectangle, see
          _coastline_water_rings.

        Water and coastline are cached in separate files (water_<key>.json,
        coast_<key>.json): a dense metro cell's water is tens of MB from
        Overpass while its coastline is small, so an area whose water is
        already cached only pays for the cheap coastline query. When both
        are missing they're fetched in one query.

        Pure-Python/numpy + `requests` only — no osmnx/shapely.

        `bounds` is snapped outward to a fixed grid (_snap_bbox_to_grid)
        before it's used as a cache key or an Overpass query bbox, so a
        pan/zoom within the same area reuses one cached fetch instead of
        each exact viewport paying out its own Overpass round-trip. The
        snapped rectangle is also the coastline clip rectangle: every
        coastline way with a node inside it was fetched, so a chain can only
        leave it by crossing its boundary.

        `deadline` (time.monotonic()) caps the Overpass call's timeout to
        the caller's remaining budget.

        The whole cache-check/fetch/write sequence runs under a per-key
        lock (_get_water_polygon_lock) so two concurrent requests for the
        same snapped bbox — e.g. explore.js "both" mode's zoom=14 and
        zoom=17 roadless-tile calls, which share identical bounds — share
        one Overpass round-trip and one outcome, instead of each firing its
        own redundant query, doubling load on an already-slow endpoint, and
        potentially racing to write the same cache file.
        """
        bounds = _snap_bbox_to_grid(bounds, _WATER_POLYGON_GRID_DEGREES)
        key = _bbox_cache_key(bounds)
        water_file = self.cache_dir / f"water_{key}.json"
        coast_file = self.cache_dir / f"coast_{key}.json"

        with self._get_water_polygon_lock(key):
            water_stamp = self._fresh_cache_stamp(water_file)
            coast_stamp = self._fresh_cache_stamp(coast_file)
            if water_stamp and coast_stamp:
                with self._water_polygon_memo_lock:
                    memo = self._water_polygon_memo.get(key)
                    if memo is not None and memo[0] == (water_stamp, coast_stamp):
                        self._water_polygon_memo.move_to_end(key)
                        return memo[1]

            water = _water_groups_from_cache(self._read_cache_json(water_file)) if water_stamp else None
            coastline = _coastline_from_cache(self._read_cache_json(coast_file)) if coast_stamp else None

            if water is None or coastline is None:
                south, west, north, east = bounds
                bbox = f"({south},{west},{north},{east})"
                parts = []
                if water is None:
                    parts += [f'way["natural"="water"]{bbox};', f'relation["natural"="water"]{bbox};']
                if coastline is None:
                    parts.append(f'way["natural"="coastline"]{bbox};')
                elements = self._overpass_query("(" + "".join(parts) + ");out geom;", deadline)
                fetched_water, fetched_coast = _parse_overpass_water(elements)
                if water is None:
                    water = fetched_water
                    self._write_cache_json(water_file, {"version": _WATER_CACHE_VERSION, "water": water})
                if coastline is None:
                    coastline = fetched_coast
                    self._write_cache_json(coast_file, {"version": _WATER_CACHE_VERSION, "coastline": coastline})
                self._evict_old_water_polygon_caches()

            groups = _build_water_groups(water, coastline, bounds)
            water_stamp = self._fresh_cache_stamp(water_file)
            coast_stamp = self._fresh_cache_stamp(coast_file)
            if water_stamp and coast_stamp:
                self._remember_water_polygons(key, (water_stamp, coast_stamp), groups)
            return groups

    def _fresh_cache_stamp(self, path: Path) -> Optional[Tuple[int, int]]:
        """(mtime_ns, size) of a water/coast cache file, or None if it's
        missing or older than exploration.water_polygon_cache_ttl_seconds
        (0 = never expires)."""
        try:
            st = path.stat()
        except OSError:
            return None
        ttl = int(self.config.get("exploration.water_polygon_cache_ttl_seconds", 0))
        age_s = time.time() - st.st_mtime
        if ttl > 0 and age_s > ttl:
            logger.info("Water polygon cache %s is %.0fs old (TTL %ds) — refetching", path, age_s, ttl)
            return None
        return (st.st_mtime_ns, st.st_size)

    @staticmethod
    def _read_cache_json(path: Path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _write_cache_json(path: Path, data) -> None:
        """Atomic write (temp file + os.replace, #562) — like the tile index
        and route cache already do — so a concurrent reader can never
        observe a truncated/partial JSON file mid-write."""
        tmp_path = path.with_name(f"{path.name}.tmp{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(",", ":"))
            secure_chmod(tmp_path)
            os.replace(tmp_path, path)
            secure_chmod(path)
        except OSError as exc:
            logger.warning("Failed to write water polygon cache: %s", exc)
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def _overpass_query(self, body: str, deadline: Optional[float] = None) -> list:
        """POST one Overpass query and return its elements, behind the
        negative cache (#562) and the concurrency cap (#598)."""
        # Negative cache (#562): skip straight to failure if Overpass
        # failed recently rather than paying out another full timeout for a
        # query that's very likely to fail again during an outage.
        with self._overpass_failure_lock:
            failure_until = self._overpass_failure_until.get(_OVERPASS_URL)
        if failure_until is not None and time.time() < failure_until:
            remaining = failure_until - time.time()
            logger.warning(
                "Overpass endpoint recently failed — skipping retry for %.0fs more", remaining,
            )
            raise RuntimeError(
                f"Overpass water-polygon lookup temporarily unavailable ({remaining:.0f}s)"
            )

        timeout = _OVERPASS_REQUEST_TIMEOUT_S
        if deadline is not None:
            timeout = min(timeout, deadline - time.monotonic())
            if timeout < 1:
                raise RuntimeError("water lookup time budget exhausted")

        # Concurrency cap (#598): bound how many threads can be blocked
        # inside the actual Overpass call at once, across all bboxes — see
        # _MAX_CONCURRENT_OVERPASS_CALLS. Fail fast rather than queue if no
        # slot frees up within the wait budget, instead of silently tying up
        # a thread for however long callers ahead of us take.
        if not self._overpass_semaphore.acquire(timeout=_OVERPASS_SEMAPHORE_WAIT_S):
            logger.warning(
                "Overpass concurrency cap (%d) reached — failing fast instead of queueing",
                _MAX_CONCURRENT_OVERPASS_CALLS,
            )
            raise RuntimeError(
                f"Overpass water-polygon lookup busy "
                f"({_MAX_CONCURRENT_OVERPASS_CALLS} requests already in flight); try again shortly"
            )
        try:
            query = f"[out:json][timeout:{_OVERPASS_QUERY_TIMEOUT_S}];{body}"
            # Overpass rejects requests with no/default User-Agent (406).
            headers = {"User-Agent": "ride-optimizer (exploration water-tile lookup)"}
            try:
                response = requests.post(
                    _OVERPASS_URL, data={"data": query}, headers=headers, timeout=timeout,
                )
                response.raise_for_status()
                elements = response.json().get("elements", [])
            except (requests.RequestException, ValueError, OSError) as exc:
                with self._overpass_failure_lock:
                    self._overpass_failure_until[_OVERPASS_URL] = time.time() + _OVERPASS_NEGATIVE_CACHE_TTL_S
                logger.warning(
                    "Overpass water-polygon query failed: %s — negative-caching endpoint for %ds",
                    exc, _OVERPASS_NEGATIVE_CACHE_TTL_S,
                )
                raise

            # A successful call clears any earlier failure marker so the
            # next request isn't held back by a now-stale negative cache
            # entry.
            with self._overpass_failure_lock:
                self._overpass_failure_until.pop(_OVERPASS_URL, None)
            return elements
        finally:
            self._overpass_semaphore.release()

    def get_roadless_tiles(
        self,
        bounds,
        zoom: Optional[int] = None,
    ) -> dict:
        """Find tiles that fall inside open water — lakes, reservoirs and
        rivers (OSM `natural=water`) plus coastline-bounded water such as
        the Great Lakes and sea coasts (OSM `natural=coastline`, #603).

        The exploration route generator uses this to exclude tiles that
        aren't bikeable or walkable from "new tile" scoring, so routes stop
        being pulled toward tiles they have no way to enter (#525). This
        only catches open water, not genuinely roadless (but dry) terrain.

        `bounds` is either one (south, west, north, east) box or a list of
        them (#604): explore.js's loop/out-and-back area grid and its
        point-to-point corridor chain send every box in ONE request instead
        of one request per box. Each box is evaluated against the water
        fetched for its own snapped grid rectangle; boxes that share a
        snapped rectangle share one fetch. If the Overpass lookup fails (or
        the per-request fetch budget runs out) for some boxes, the others
        still come back, with `failed_boxes` saying how many were skipped;
        the status is "error" only when every box failed.

        Tiles are classified with a numpy scanline rasterizer
        (_rasterize_water_groups) rather than a per-tile ray-cast (#604 —
        the pure-Python tile x polygon sweep took ~5 s per box on the Pi
        even with warm caches). The result is returned as row runs,
        `roadless_runs: [[y, x_start, x_end], ...]` (both x inclusive),
        because an open-lake area at zoom 17 is hundreds of thousands of
        tiles — far too many to ship, or to build on the Pi, as one JSON
        object per tile.
        """
        zoom = zoom or self.zoom
        boxes = _normalize_boxes(bounds)
        if not boxes:
            return {"status": "error", "message": "no bounds given"}

        # One fetch per distinct snapped rectangle, bounded overall so a
        # cold multi-box load can't hold a worker thread for N x the
        # Overpass timeout.
        deadline = time.monotonic() + _ROADLESS_FETCH_BUDGET_S
        groups_by_key: Dict[str, Optional[list]] = {}
        last_error: Optional[str] = None
        for box in boxes:
            key = _bbox_cache_key(_snap_bbox_to_grid(box, _WATER_POLYGON_GRID_DEGREES))
            if key in groups_by_key:
                continue
            if time.monotonic() > deadline:
                groups_by_key[key] = None
                last_error = "water lookup time budget exhausted"
                continue
            try:
                groups_by_key[key] = self._get_or_fetch_water_features(box, deadline)
            except Exception as exc:
                logger.error("Failed to fetch water polygons: %s", exc)
                groups_by_key[key] = None
                last_error = str(exc)

        outer = (
            min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes),
        )
        min_tx, min_ty = lat_lon_to_tile(outer[2], outer[1], zoom)
        max_tx, max_ty = lat_lon_to_tile(outer[0], outer[3], zoom)
        mask = np.zeros((max_ty - min_ty + 1, max_tx - min_tx + 1), dtype=bool)

        failed = 0
        for box in boxes:
            key = _bbox_cache_key(_snap_bbox_to_grid(box, _WATER_POLYGON_GRID_DEGREES))
            groups = groups_by_key.get(key)
            if groups is None:
                failed += 1
                continue
            b_south, b_west, b_north, b_east = box
            bx0, by0 = lat_lon_to_tile(b_north, b_west, zoom)
            bx1, by1 = lat_lon_to_tile(b_south, b_east, zoom)
            relevant = [
                rings for (g_south, g_west, g_north, g_east), rings in groups
                if g_south <= b_north and g_north >= b_south and g_west <= b_east and g_east >= b_west
            ]
            if not relevant:
                continue
            sub = _rasterize_water_groups(relevant, zoom, bx0, bx1, by0, by1)
            mask[by0 - min_ty:by1 - min_ty + 1, bx0 - min_tx:bx1 - min_tx + 1] |= sub

        if failed == len(boxes):
            return {"status": "error", "message": last_error or "water lookup failed"}

        runs = _mask_to_runs(mask, min_tx, min_ty)
        return {
            "status": "success",
            "zoom": zoom,
            "roadless_runs": runs,
            "roadless_count": int(mask.sum()),
            "box_count": len(boxes),
            "failed_boxes": failed,
            "bounds": outer,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _remember_water_polygons(self, key: str, stamp: Tuple[int, int], polygons: list) -> None:
        """Store parsed polygons in the small LRU memo."""
        with self._water_polygon_memo_lock:
            self._water_polygon_memo[key] = (stamp, polygons)
            self._water_polygon_memo.move_to_end(key)
            while len(self._water_polygon_memo) > _WATER_POLYGON_MEMO_SIZE:
                self._water_polygon_memo.popitem(last=False)

    def _evict_old_water_polygon_caches(self) -> None:
        """Keep at most MAX_WATER_POLYGON_CACHES water_*.json files,
        evicting the least-recently-modified ones beyond that cap."""
        for pattern in ("water_*.json", "coast_*.json"):
            caches = sorted(
                self.cache_dir.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for p in caches[MAX_WATER_POLYGON_CACHES:]:
                try:
                    p.unlink()
                except OSError:
                    pass

    def _sweep_legacy_coverage_tile_files(self) -> int:
        """Delete leftover coverage_tiles_*.json files from the per-bbox
        caching scheme that predates the tile-index rewrite (#555).

        Nothing in the current codebase writes these anymore — coverage is
        served from the persisted, incrementally-updated tile_index_{zoom}.json
        instead. The only previous cleanup was inside invalidate_caches(),
        which only runs on a manual resync; in production that apparently
        never happened — 38 of these files (32MB) were still sitting on the
        Pi over five weeks after the rewrite that made them obsolete. Called
        unconditionally at __init__ so a leftover deployment self-heals on
        its next restart instead of waiting on a resync that may never come.

        Returns the number of files removed.
        """
        removed = 0
        for p in self.cache_dir.glob("coverage_tiles_*.json"):
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
        return removed

    def invalidate_caches(self) -> None:
        """Soft-invalidate: clear in-memory state only (#571/#583).

        Drops the cached activities list and the in-memory tile index, so
        the next read reloads the on-disk index and diffs it against
        freshly-loaded activities (see _build_or_update_tile_index) — but
        leaves the on-disk tile_index_{zoom}.json files themselves alone.

        This is what runs automatically after every activity fetch/analyze/
        backfill (the three call sites in app/api/data_bp.py, in turn
        triggered nightly by cron/daily_analysis.py). Those call sites used
        to invoke a fully destructive wipe (see hard_invalidate_caches()
        below) that deleted the on-disk index outright, forcing a full cold
        rebuild — decoding every ridden activity's polyline from scratch —
        on the next Explore page load after every nightly sync. Soft
        invalidation still picks up the new activities (via the diff in
        _build_or_update_tile_index) without paying that cost, since the
        vast majority of previously-indexed tiles didn't change.

        For an explicit, user-initiated "clear my coverage cache" action,
        use hard_invalidate_caches() instead.
        """
        self._activities_cache = None
        self._clear_tile_index_cache()
        logger.info("Coverage caches soft-invalidated (in-memory only)")

    def _clear_tile_index_cache(self) -> None:
        """Drop every zoom's in-memory tile index, one zoom at a time under
        that zoom's own lock (#558) — so this can't race a concurrent
        _build_or_update_tile_index() call for the same zoom (there's no
        single global lock anymore to serialize the two under)."""
        for zoom in set(self._tile_index_cache) | set(self._tile_index_locks):
            with self._get_zoom_lock(zoom):
                self._tile_index_cache.pop(zoom, None)

    def hard_invalidate_caches(self) -> None:
        """Fully wipe all coverage caches, including the on-disk tile index.

        This is the old (pre-#571) invalidate_caches() behaviour, kept
        available for an explicit, user-initiated cache-clear request —
        e.g. after suspected corruption, or a deliberate full rebuild.
        Do NOT wire this into the automatic post-activity-sync path; use
        the soft invalidate_caches() there instead.
        """
        self._activities_cache = None

        # Delete each zoom's on-disk file under that zoom's own lock (#558),
        # so this can't delete a tile_index_{zoom}.json file out from under
        # an in-flight _build_or_update_tile_index() call for the same
        # zoom. Covers zooms known in memory (cache or lock already exists)
        # as well as zooms only seen on disk (e.g. a fresh process that
        # hasn't read/built a given zoom's index yet this run).
        zooms = set(self._tile_index_cache) | set(self._tile_index_locks)
        for path in self.cache_dir.glob("tile_index_*.json"):
            try:
                zooms.add(int(path.stem.rsplit("_", 1)[-1]))
            except ValueError:
                continue
        for zoom in zooms:
            with self._get_zoom_lock(zoom):
                self._tile_index_cache.pop(zoom, None)
                try:
                    self._tile_index_path(zoom).unlink()
                except OSError:
                    pass

        self._sweep_legacy_coverage_tile_files()
        # Water polygons don't change with new activities — not evicted here.
        logger.info("Coverage caches hard-invalidated (on-disk index cleared)")
