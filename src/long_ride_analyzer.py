"""
Long Ride Analysis Module

Analyzes non-commute cycling activities for recreational ride recommendations.

Long rides are grouped by geometry with the same metric as commutes (#613):
tracks in metres, resampled by arc length, compared by p95 deviation and 50 m
coverage, then grouped by centre clustering (#614). Coverage doesn't care
where a loop starts, and the rides are compared as sets of points, so a loop
ridden in reverse or started elsewhere still matches. The Strava name is only
a prior: two rides with the same name match at a lower coverage bar, but never
without geometric agreement. Rides that lie along part of another route (a
sub-segment, or the other is an extension) are linked to it, not merged (#615).
"""

import hashlib
import json
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from geopy.distance import geodesic
import polyline

from .data_fetcher import Activity
from .json_storage import secure_chmod
from .route_comparison import (
    COVERAGE_RADIUS_M, LONG_RIDE_DENSE_STEP_M, LONG_RIDE_SAMPLE_STEP_M,
    PreparedTrack, cluster_by_centres, coverage_bound_pairs, coverage_cells,
    directed_deviation_metrics, match_score,
)
from .secure_logger import SecureLogger

logger = SecureLogger(__name__)

# Bump when the pairwise metric, the resample steps or the track hash change,
# so cached metrics from the old code are discarded (#612).
SIMILARITY_CACHE_VERSION = 2

# Start and end within this of each other: a loop or an out-and-back.
LOOP_RADIUS_M = 500
# An out-and-back retraces itself: this share of the outbound half lies along
# the return half.
OUT_AND_BACK_MIN_COVERAGE = 0.7
# Prepared tracks kept in memory while computing pair metrics. Each long ride is
# a few hundred KB prepared, so this bounds memory on the Pi.
TRACK_CACHE_SIZE = 256

# Strava's default names ("Morning Ride", "Night Gravel Ride", "Afternoon
# Mountain Bike Ride", ...) and other placeholders say nothing about the route.
_RIDE_KIND = r'((gravel|road|mountain bike|e-?bike|e-?mountain bike|bike|cycling|velomobile) )?ride'
_GENERIC_NAME = re.compile(
    rf'^((early )?morning|afternoon|evening|night|lunch|midday) {_RIDE_KIND}$'
    rf'|^{_RIDE_KIND}$|^untitled( ride)?$|^unnamed( (ride|activity))?$')

VIRTUAL_KEYWORDS = ('zwift', 'trainer', 'indoor', 'rouvy', 'sufferfest', 'peloton')


def normalize_name(name: Optional[str]) -> str:
    """Case- and whitespace-insensitive form of a ride name."""
    return ' '.join((name or '').casefold().split())


@dataclass
class LongRide:
    """Represents a long/recreational ride."""
    activity_id: int
    name: str
    coordinates: List[Tuple[float, float]]
    distance: float  # meters
    duration: int  # seconds
    elevation_gain: float  # meters
    timestamp: str  # ISO format
    average_speed: float  # m/s
    start_location: Tuple[float, float]
    end_location: Tuple[float, float]
    is_loop: bool  # True if start and end are close
    type: str  # Activity type (Ride, GravelRide, VirtualRide, etc.)
    uses: int = 1  # Number of times this route has been ridden
    activity_ids: List[int] = None  # List of all activity IDs that make up this route
    activity_dates: List[str] = None  # List of dates for each activity
    activity_names: List[str] = None  # Strava names for each activity
    # Linked, not merged (#615): representative activity IDs of the long rides
    # this route lies along (part_of) and of those lying along it (contains).
    part_of: List[int] = field(default_factory=list)
    contains: List[int] = field(default_factory=list)

    @property
    def distance_km(self) -> float:
        """Distance in kilometers."""
        return self.distance / 1000

    @property
    def duration_hours(self) -> float:
        """Duration in hours."""
        return self.duration / 3600

    @property
    def midpoint(self) -> Tuple[float, float]:
        """Calculate midpoint of the ride."""
        if not self.coordinates:
            return self.start_location
        mid_idx = len(self.coordinates) // 2
        return self.coordinates[mid_idx]


class LongRideAnalyzer:
    """Analyzes non-commute rides for recreational recommendations."""

    _SIMILARITY_CACHE_FILE = "long_ride_similarity_cache.json"

    def __init__(self, activities: List[Activity], config, cache_dir: str = "cache"):
        """
        Initialize long ride analyzer.

        Args:
            activities: List of all Activity objects
            config: Configuration object
            cache_dir: Directory for the pair-metrics cache
        """
        self.activities = activities
        self.config = config
        self.cache_file = Path(cache_dir) / self._SIMILARITY_CACHE_FILE
        # Two rides are the same route when at least min_coverage of each lies
        # within 50 m of the other, and (if set) 95% of each lies within
        # max_p95_deviation_m. Unlike commutes, a long-ride variant (a longer
        # turnaround, a different few km) is still the route, so by default
        # only coverage decides.
        p95 = config.get('long_rides.max_p95_deviation_m', None)
        self.max_p95_deviation_m = float(p95) if p95 is not None else None
        self.min_coverage = float(config.get('long_rides.min_coverage', 0.9))
        # ... except that rides sharing a (non-generic) name only need this coverage.
        self.name_min_coverage = float(config.get('long_rides.name_min_coverage', 0.75))
        # Coverage can't tell one lap from two, or a one-way ride from the
        # out-and-back on the same road: same-route rides must also be within
        # this length ratio.
        self.max_length_ratio = float(config.get('long_rides.max_length_ratio', 1.5))
        # A ride is part of another when this share of it lies along the other
        # (and it's the shorter of the two).
        self.contains_min_coverage = float(config.get('long_rides.contains_min_coverage', 0.9))
        extra = config.get('long_rides.generic_names', None) or []
        self.extra_generic_names = {normalize_name(n) for n in extra}
        self._similarity_cache: Dict[str, List[float]] = self._load_similarity_cache()

    # ------------------------------------------------------------ cache

    def _load_similarity_cache(self) -> Dict[str, List[float]]:
        """Load the pair-metrics cache, discarding one from older code."""
        if not self.cache_file.exists():
            return {}
        try:
            cache = json.loads(self.cache_file.read_text())
        except Exception as e:
            logger.warning(f"Could not load long-ride similarity cache: {e}")
            return {}
        if not isinstance(cache, dict) or cache.get('version') != SIMILARITY_CACHE_VERSION:
            # Includes the pre-#615 format: a flat {"id:id": km} dict whose
            # prefilter rejections were stored as a permanent inf.
            logger.info("Discarding long-ride similarity cache from an older version")
            return {}
        metrics = cache.get('metrics', {})
        logger.info(f"Loaded {len(metrics)} long-ride pair metrics from cache")
        return metrics

    def _save_similarity_cache(self, used_keys) -> None:
        """Persist the metrics of the pairs this run used. Pairs of rides that no
        longer exist are dropped, so the file doesn't grow without bound."""
        metrics = {k: self._similarity_cache[k] for k in used_keys if k in self._similarity_cache}
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps({'version': SIMILARITY_CACHE_VERSION,
                                                   'metrics': metrics}))
            secure_chmod(self.cache_file)
            logger.debug(f"Saved {len(metrics)} long-ride pair metrics to cache")
        except Exception as e:
            logger.warning(f"Could not save long-ride similarity cache: {e}")

    @staticmethod
    def _track_hash(coords: np.ndarray) -> str:
        return hashlib.sha256(np.ascontiguousarray(coords, dtype=np.float64).tobytes()).hexdigest()[:16]

    # ------------------------------------------------------------ classification

    def classify_activities(self, commute_activities: List[Activity]) -> Tuple[List[Activity], List[Activity]]:
        """
        Classify activities into commutes and long rides.

        Args:
            commute_activities: List of identified commute activities

        Returns:
            Tuple of (commute_activities, long_ride_activities)
        """
        commute_ids = {act.id for act in commute_activities}

        # Filter for cycling activities that are not commutes
        long_rides = []
        for activity in self.activities:
            # Skip if it's a commute
            if activity.id in commute_ids:
                continue

            # Must be a cycling activity, but exclude virtual rides
            if 'Ride' not in activity.type:
                continue

            # Skip virtual rides by activity type
            if 'VirtualRide' in activity.type or 'Virtual' in activity.type:
                logger.debug(f"Skipping virtual ride: {activity.name} (type={activity.type})")
                continue

            # Must have GPS data (virtual rides often don't have real GPS)
            if not activity.start_latlng or not activity.end_latlng or not activity.polyline:
                continue

            # Additional check: Skip by activity name keywords
            if activity.name:
                name_lower = activity.name.lower()
                if any(keyword in name_lower for keyword in VIRTUAL_KEYWORDS):
                    logger.debug(f"Skipping virtual ride: {activity.name} (name contains virtual keyword)")
                    continue

            # Apply distance filter (configurable, default > 15km for long rides)
            min_distance = self.config.get('long_rides.min_distance_km', 15) * 1000
            if activity.distance < min_distance:
                continue

            long_rides.append(activity)

        logger.info(f"Classified {len(commute_activities)} commutes and {len(long_rides)} long rides")

        return commute_activities, long_rides

    def is_generic_name(self, name: Optional[str]) -> bool:
        """True for an empty name or a Strava default such as "Morning Ride",
        "Night Ride" or "Afternoon Gravel Ride", which says nothing about the
        route. Localised defaults can be added via long_rides.generic_names."""
        n = normalize_name(name)
        return not n or bool(_GENERIC_NAME.match(n)) or n in self.extra_generic_names

    # ------------------------------------------------------------ grouping

    def group_similar_rides(self, long_ride_activities: List[Activity],
                            on_progress=None) -> List[LongRide]:
        """
        Group long-ride activities into unique routes.

        1. Each ride's track is projected and resampled (coarser than commutes).
        2. coverage_bound_pairs rules out, exactly and cheaply, the pairs whose
           coverage can't reach the bar; only the rest get the exact metric
           (cached across runs).
        3. Two rides match when mutual coverage >= min_coverage (or
           name_min_coverage if they share a non-generic name), their lengths
           are within max_length_ratio, and (if set) p95 deviation <=
           max_p95_deviation_m. cluster_by_centres groups them; each group's
           centre is its representative.
        4. A group whose representative is shorter than another's and lies
           along it is linked to it (part_of / contains).

        Rides are processed in activity-ID order, so the result doesn't depend
        on input order.

        Args:
            long_ride_activities: Activities already filtered to non-commute long rides
            on_progress: Optional callable(label=str) for status updates

        Returns:
            List of LongRide objects, most-ridden first
        """
        def notify(label):
            if on_progress:
                try:
                    on_progress(label=label)
                except Exception:
                    pass

        rides, coords = [], []
        for activity in sorted(long_ride_activities, key=lambda a: a.id):
            try:
                c = np.asarray(polyline.decode(activity.polyline), dtype=float).reshape(-1, 2)
                if len(c) == 0:
                    raise ValueError("empty polyline")
            except Exception as e:
                logger.warning(f"Long ride {activity.id} has no usable track, skipping it: {e}")
                continue
            rides.append(activity)
            coords.append(c)
        if not rides:
            return []

        n = len(rides)
        notify(f'Preparing {n} long-ride tracks…')
        lat0 = round(float(np.median([c[:, 0].mean() for c in coords])), 1)
        hashes = [self._track_hash(c) for c in coords]
        # Non-generic names as integer codes (0 = no name prior).
        name_ids = {}
        name_code = np.array([0 if self.is_generic_name(a.name) else
                              name_ids.setdefault(normalize_name(a.name), len(name_ids) + 1)
                              for a in rides])
        tracks = _TrackCache(coords, lat0)
        cells, lengths = [], np.empty(n)
        for k in range(n):
            t = tracks.get(k)
            cells.append(coverage_cells(t))
            lengths[k] = float(np.linalg.norm(np.diff(t.samples, axis=0), axis=1).sum())

        tracks.clear()  # the screen's peak doesn't need them; pairs rebuild them lazily
        notify(f'Screening {n} long rides for possible matches…')
        # Pairs stay numpy arrays: a real corpus leaves ~1M of them after the
        # screen, too many for Python tuples on the Pi.
        bi, bj, b_ij, b_ji = coverage_bound_pairs(
            cells, min(self.min_coverage, self.name_min_coverage), self.contains_min_coverage)
        del cells
        pair_min_cov = np.where((name_code[bi] > 0) & (name_code[bi] == name_code[bj]),
                                self.name_min_coverage, self.min_coverage)
        similar_length = (np.maximum(lengths[bi], lengths[bj])
                          <= np.minimum(lengths[bi], lengths[bj]) * self.max_length_ratio)
        candidate = (np.minimum(b_ij, b_ji) >= pair_min_cov - 1e-9) & similar_length
        min_cov_of = {(i, j): c for i, j, c in zip(bi[candidate].tolist(), bj[candidate].tolist(),
                                                    pair_min_cov[candidate].tolist())}
        used_keys = set()
        metrics = self._pair_metrics(list(min_cov_of), tracks, hashes, coords, used_keys, notify)

        edges = []
        for (i, j), m in metrics.items():
            score = self._match_score(m, min_cov_of[(i, j)])
            if score >= 1.0:
                edges.append((i, j, score))
        clusters = cluster_by_centres(n, edges)

        notify(f'Linking {len(clusters)} long-ride routes…')
        centres = {centre for centre, _ in clusters}
        is_centre = np.zeros(n, dtype=bool)
        is_centre[list(centres)] = True
        thr = self.contains_min_coverage - 1e-9
        # The shorter of the two must be able to lie along the longer.
        could_link = (is_centre[bi] & is_centre[bj]
                      & (((lengths[bi] < lengths[bj]) & (b_ij >= thr))
                         | ((lengths[bj] < lengths[bi]) & (b_ji >= thr))))
        link_pairs = list(zip(bi[could_link].tolist(), bj[could_link].tolist()))
        del bi, bj, b_ij, b_ji
        link_metrics = self._pair_metrics(link_pairs, tracks, hashes, coords, used_keys, notify)
        part_of = {c: [] for c in centres}
        contains = {c: [] for c in centres}
        for (i, j), (p95_ij, cov_ij, p95_ji, cov_ji) in link_metrics.items():
            # Centres never match each other (the later one would have joined
            # the earlier one's group), so a link is never a hidden match.
            if lengths[i] < lengths[j] and self._lies_along(p95_ij, cov_ij):
                part_of[i].append(rides[j].id)
                contains[j].append(rides[i].id)
            elif lengths[j] < lengths[i] and self._lies_along(p95_ji, cov_ji):
                part_of[j].append(rides[i].id)
                contains[i].append(rides[j].id)

        self._save_similarity_cache(used_keys)

        long_rides = []
        for centre, members in clusters:
            ride = self._make_long_ride(rides[centre], coords[centre], [rides[m] for m in members],
                                        tracks.get(centre))
            ride.part_of = sorted(part_of[centre])
            ride.contains = sorted(contains[centre])
            long_rides.append(ride)
        long_rides.sort(key=lambda r: (-r.uses, r.activity_id))

        logger.info(f"Grouped {n} long rides into {len(long_rides)} routes "
                    f"({sum(1 for r in long_rides if r.uses > 1)} ridden more than once, "
                    f"{sum(1 for r in long_rides if r.part_of)} part of another)")
        return long_rides

    def _match_score(self, metrics, min_coverage: float) -> float:
        """>= 1.0 when two rides are the same route (route_comparison.match_score)."""
        p95_ij, cov_ij, p95_ji, cov_ji = metrics
        coverage = min(cov_ij, cov_ji)
        if self.max_p95_deviation_m is None:
            return coverage / min_coverage
        return match_score(max(p95_ij, p95_ji), coverage, self.max_p95_deviation_m, min_coverage)

    def _lies_along(self, p95_m: float, coverage: float) -> bool:
        """One direction of a pair: does this ride lie along the other?"""
        return (coverage >= self.contains_min_coverage
                and (self.max_p95_deviation_m is None or p95_m <= self.max_p95_deviation_m))

    def _pair_metrics(self, pairs, tracks, hashes, coords, used_keys, notify) -> Dict:
        """{(i, j): (p95_ij, cov_ij, p95_ji, cov_ji)} for the given pairs, from
        the cache where possible. A failed comparison is logged and left out
        (no match, no link) rather than recorded as a distance."""
        result, todo = {}, []
        for i, j in pairs:
            key, flipped = self._pair_key(hashes[i], hashes[j])
            used_keys.add(key)
            cached = self._similarity_cache.get(key)
            if cached is not None:
                result[(i, j)] = tuple(cached[2:] + cached[:2]) if flipped else tuple(cached)
            else:
                todo.append((i, j, key, flipped))
        if not todo:
            return result

        # Visit pairs area by area, so the tracks they need stay in the cache.
        def area(k):
            c = coords[k][0]
            return (round(c[0] * 20), round(c[1] * 20))  # ~5 km cells
        todo.sort(key=lambda t: (area(t[0]), t[0], t[1]))
        logger.info(f"Comparing {len(todo)} long-ride pairs ({len(result)} cached)")
        failures = 0
        for done, (i, j, key, flipped) in enumerate(todo):
            if done % 2000 == 0:
                notify(f'Comparing long rides… {done}/{len(todo)}')
            try:
                m = directed_deviation_metrics(tracks.get(i), tracks.get(j))
            except Exception as e:
                failures += 1
                logger.warning(f"Long-ride comparison failed, treating as no match: {e}")
                continue
            result[(i, j)] = m
            self._similarity_cache[key] = list(m[2:] + m[:2]) if flipped else list(m)
        if failures:
            logger.warning(f"{failures} long-ride comparisons failed")
        return result

    @staticmethod
    def _pair_key(hash1: str, hash2: str) -> Tuple[str, bool]:
        """Order-independent cache key, and whether (hash1, hash2) is the
        reverse of the stored order (directed metrics are stored for it)."""
        if hash1 <= hash2:
            return f"{hash1}_{hash2}", False
        return f"{hash2}_{hash1}", True

    # ------------------------------------------------------------ output

    def _make_long_ride(self, representative: Activity, coords: np.ndarray,
                        members: List[Activity], track: PreparedTrack) -> LongRide:
        """One LongRide for a group, described by its representative ride."""
        by_date = sorted(members, key=lambda a: (a.start_date or '', a.id), reverse=True)
        if representative.start_latlng and representative.end_latlng:
            is_loop = geodesic(representative.start_latlng,
                               representative.end_latlng).meters < LOOP_RADIUS_M
        else:
            is_loop = False
        return LongRide(
            activity_id=representative.id,
            name=self._group_name(members, representative, is_loop, track),
            coordinates=[tuple(p) for p in coords.tolist()],
            distance=representative.distance,
            duration=representative.moving_time,
            elevation_gain=representative.total_elevation_gain,
            timestamp=representative.start_date,
            average_speed=representative.average_speed,
            start_location=representative.start_latlng or (0.0, 0.0),
            end_location=representative.end_latlng or (0.0, 0.0),
            is_loop=is_loop,
            type=representative.sport_type if representative.sport_type else representative.type,
            uses=len(members),
            activity_ids=[a.id for a in by_date],
            activity_dates=[a.start_date[:10] if a.start_date else "Unknown" for a in by_date],
            activity_names=[a.name or "" for a in by_date],
        )

    def _group_name(self, members: List[Activity], representative: Activity,
                    is_loop: bool, track: PreparedTrack) -> str:
        """The members' most common non-generic name (ties: the shorter, then
        alphabetical), else a description of the representative's shape."""
        counts = Counter((a.name or '').strip() for a in members if not self.is_generic_name(a.name))
        if counts:
            return min(counts.items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0]))[0]
        km = (representative.distance or 0) / 1000
        if not is_loop:
            kind = "Point to Point"
        elif _retraces_itself(track):
            kind = "Out & Back"
        else:
            kind = "Loop Ride"
        return f"{kind} ({km:.1f}km)"


def _retraces_itself(track: PreparedTrack) -> bool:
    """True if the outbound half of the track mostly lies along the return half."""
    from scipy.spatial import cKDTree
    s = track.samples
    if len(s) < 4:
        return False
    half = len(s) // 2
    d = cKDTree(s[half:]).query(s[:half])[0]
    # Samples are LONG_RIDE_SAMPLE_STEP_M apart, so allow half a step on top.
    return float(np.mean(d <= COVERAGE_RADIUS_M + LONG_RIDE_SAMPLE_STEP_M / 2)) >= OUT_AND_BACK_MIN_COVERAGE


class _TrackCache:
    """Prepared long-ride tracks on demand, keeping the TRACK_CACHE_SIZE most
    recently used: preparing every track at once would hold hundreds of MB."""

    def __init__(self, coords: List[np.ndarray], lat0: float):
        self.coords, self.lat0 = coords, lat0
        self._tracks: "OrderedDict[int, PreparedTrack]" = OrderedDict()

    def get(self, k: int) -> PreparedTrack:
        track = self._tracks.get(k)
        if track is not None:
            self._tracks.move_to_end(k)
            return track
        track = PreparedTrack(self.coords[k], self.lat0,
                              LONG_RIDE_SAMPLE_STEP_M, LONG_RIDE_DENSE_STEP_M)
        self._tracks[k] = track
        if len(self._tracks) > TRACK_CACHE_SIZE:
            self._tracks.popitem(last=False)
        return track

    def clear(self) -> None:
        self._tracks.clear()
