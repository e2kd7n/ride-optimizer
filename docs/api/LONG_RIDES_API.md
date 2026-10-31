# Long Rides API Documentation

**Module:** `src/long_ride_analyzer.py`  
**Version:** 2.4.0+  
**Last Updated:** 2026-10-31

---

## Overview

The Long Rides API provides functionality for analyzing, grouping, and recommending recreational cycling routes. It uses advanced route similarity algorithms and weather integration to help cyclists discover and plan longer rides.

## Table of Contents

1. [Data Classes](#data-classes)
2. [LongRideAnalyzer Class](#longrideanalyzer-class)
3. [Public Methods](#public-methods)
4. [Configuration](#configuration)
5. [Examples](#examples)

---

## Data Classes

### LongRide

Represents a long/recreational ride with comprehensive metadata.

```python
@dataclass
class LongRide:
    activity_id: int                          # Strava activity ID
    name: str                                 # Route name
    coordinates: List[Tuple[float, float]]    # GPS coordinates [(lat, lng), ...]
    distance: float                           # Distance in meters
    duration: int                             # Duration in seconds
    elevation_gain: float                     # Elevation gain in meters
    timestamp: str                            # ISO format timestamp
    average_speed: float                      # Average speed in m/s
    start_location: Tuple[float, float]       # Start coordinates (lat, lng)
    end_location: Tuple[float, float]         # End coordinates (lat, lng)
    is_loop: bool                             # True if start/end within 500m
    type: str                                 # Activity type (Ride, GravelRide, etc.)
    uses: int = 1                             # Number of times route ridden
    activity_ids: List[int] = None            # All activity IDs for this route, most recent first
    activity_dates: List[str] = None          # Dates for each activity
    activity_names: List[str] = None          # Strava names for each activity
    part_of: List[int] = []                   # Representative IDs of routes this one lies along
    contains: List[int] = []                  # Representative IDs of routes lying along this one
```

`activity_id` and the other ride fields describe the group's **representative**: its
clustering centre, the ride that matches the most others (see `group_similar_rides`).

**Properties:**
- `distance_km: float` - Distance in kilometers
- `duration_hours: float` - Duration in hours
- `midpoint: Tuple[float, float]` - Midpoint coordinates of the route

### RideRecommendation

Represents a ride recommendation with weather analysis.

```python
@dataclass
class RideRecommendation:
    ride: LongRide                            # The recommended ride
    distance_to_location: float               # Meters from clicked location
    weather_score: float                      # 0-1, wind favorability score
    precipitation_risk: str                   # "none", "low", "medium", "high"
    recommended_start_time: Optional[str]     # Suggested start time
    estimated_duration: Optional[float]       # Estimated duration in hours
    route_description: str                    # Human-readable description
    wind_analysis: Optional[Dict[str, Any]]   # Detailed wind analysis
```

---

## LongRideAnalyzer Class

### Constructor

```python
def __init__(self, activities: List[Activity], config, cache_dir: str = "cache")
```

**Parameters:**
- `activities` (List[Activity]): List of all Strava Activity objects
- `config`: Configuration object with settings
- `cache_dir`: Directory for the pair-metrics cache (`long_ride_similarity_cache.json`)

**Example:**
```python
from src.long_ride_analyzer import LongRideAnalyzer
from src.data_fetcher import StravaDataFetcher
from src.config import Config

config = Config('config/config.yaml')
fetcher = StravaDataFetcher(client)
activities = fetcher.fetch_activities()

analyzer = LongRideAnalyzer(activities, config)
```

---

## Public Methods

### 1. classify_activities

Classify activities into commutes and long rides.

```python
def classify_activities(
    self,
    commute_activities: List[Activity]
) -> Tuple[List[Activity], List[Activity]]
```

**Parameters:**
- `commute_activities`: List of identified commute activities

**Returns:**
- Tuple of (commute_activities, long_ride_activities)

**Filtering Criteria:**
- Excludes commute activities
- Must be cycling activity type
- Excludes virtual rides (VirtualRide type, indoor keywords)
- Must have valid GPS data
- Distance > 15 km (configurable via `long_rides.min_distance_km`)

**Example:**
```python
commutes, long_rides = analyzer.classify_activities(commute_activities)
print(f"Found {len(long_rides)} long rides")
```

---

### 2. group_similar_rides

Group long-ride activities into unique routes by geometry (#615).

```python
def group_similar_rides(
    self,
    long_ride_activities: List[Activity],
    on_progress=None
) -> List[LongRide]
```

**Parameters:**
- `long_ride_activities`: Activities already filtered by `classify_activities`
- `on_progress`: Optional `callable(label=str)` for status updates

**Returns:** `LongRide` objects, most-ridden first.

**How it matches.** It uses the same metric as commutes (`src/route_comparison.py`, #613). Tracks
are projected to metres and resampled by arc length (every 25 m, measured against a 10 m copy of
the other track). Two rides are the **same route** when:
- at least `min_coverage` (0.85) of each lies within 50 m of the other;
- their lengths are within `max_length_ratio` (1.5), because coverage can't tell one lap from
  two, or a one-way ride from the out-and-back on the same road;
- and, only if `max_p95_deviation_m` is set, 95% of each lies within that many metres.

Coverage treats a track as a set of points. So a loop ridden in reverse, or started somewhere
else, still matches, and a longer turnaround or a short detour is still the same route.

**Names are only a prior.** Two rides with the same non-generic name (case and spacing ignored)
need just `name_min_coverage` (0.6), but they never match on the name alone. Generic Strava names
("Morning Ride", "Night Gravel Ride", ...) carry no prior. Rides with different names merge when
the geometry agrees.

**Clustering.** Rides are grouped by centre (Butina) clustering, the same as commutes (#614). The
result doesn't depend on input order, and every member matches its group's representative.

**Links, not merges.** When a group's representative is shorter than another group's and at
least `contains_min_coverage` (0.9) of it lies along that one, the shorter route gets
`part_of=[other]` and the longer gets `contains=[this]`. This covers a sub-segment, a one-way ride
along an out-and-back, or a route plus a long extension.

**Names.** Each group takes the most common non-generic name among its rides. If there is none,
it gets a description of its shape: `Loop Ride (42.3km)`, `Out & Back (50.0km)` or
`Point to Point (25.0km)`.

**Cost.** An exact cell-grid bound (`coverage_bound_pairs`) rules out every pair that can't reach
the coverage bar, so only plausible pairs get the exact metric. Their directed metrics are cached
in `cache_dir` under a versioned key. A failed comparison is logged and counts as no match;
nothing is cached as "infinitely far".

**Example:**
```python
commutes, long_ride_acts = analyzer.classify_activities(commute_activities)
routes = analyzer.group_similar_rides(long_ride_acts)
for r in routes[:5]:
    print(r.name, r.uses, r.part_of)
```

---

### 3. is_generic_name

```python
def is_generic_name(self, name: Optional[str]) -> bool
```

True for an empty name or a Strava default ("Morning Ride", "Afternoon Mountain Bike Ride", ...).
Add localised defaults with `long_rides.generic_names`.

---

### 4. extract_long_rides

Convert activities to LongRide objects.

```python
def extract_long_rides(
    self,
    long_ride_activities: List[Activity]
) -> List[LongRide]
```

**Parameters:**
- `long_ride_activities`: List of Activity objects

**Returns:**
- List of LongRide objects

**Behavior:**
- Decodes polyline GPS data
- Detects loop routes
- Skips activities missing required data

**Example:**
```python
long_rides = analyzer.extract_long_rides(long_ride_activities)
```

---

### 5. find_rides_near_location

Find rides that pass near a clicked location.

```python
def find_rides_near_location(
    self,
    long_rides: List[LongRide],
    clicked_lat: float,
    clicked_lon: float,
    search_radius_km: float = 5.0
) -> List[LongRide]
```

**Parameters:**
- `long_rides`: List of LongRide objects
- `clicked_lat`: Latitude of clicked location
- `clicked_lon`: Longitude of clicked location
- `search_radius_km`: Search radius in kilometers (default: 5.0)

**Returns:**
- List of LongRide objects that pass near the location

**Algorithm:**
- Checks every coordinate point on each route
- Returns rides with any point within search radius
- Uses geodesic distance calculation

**Example:**
```python
nearby_rides = analyzer.find_rides_near_location(
    long_rides,
    41.8781,  # Chicago latitude
    -87.6298,  # Chicago longitude
    search_radius_km=10.0
)
```

---

### 6. calculate_wind_score

Calculate wind favorability score for a ride.

```python
def calculate_wind_score(
    self,
    ride: LongRide,
    current_weather: Dict[str, Any]
) -> Tuple[float, Dict[str, Any]]
```

**Parameters:**
- `ride`: LongRide object
- `current_weather`: Current weather data dictionary

**Returns:**
- Tuple of (score from 0-1 where 1 is best, detailed wind analysis dict)

**Algorithm:**
- Divides route into 8 segments
- Calculates bearing for each segment
- Determines wind type (headwind, tailwind, quartering)
- **70% weight on second half** (strong preference for tailwinds coming back)
- 10% bonus for consistent tailwinds in second half

**Wind Types:**
- Headwind: relative angle < 45° (score: 0.3)
- Tailwind: relative angle > 135° (score: 1.0)
- Quartering headwind: 45° < angle < 90° (score: 0.5)
- Quartering tailwind: 90° < angle < 135° (score: 0.8)

**Example:**
```python
weather = {
    'wind_speed_kph': 20,
    'wind_direction_deg': 270  # West wind
}
score, analysis = analyzer.calculate_wind_score(ride, weather)
print(f"Wind score: {score:.2f}")
print(f"Recommendation: {analysis['recommendation']}")
```

---

### 7. get_ride_recommendations

Get ride recommendations for a clicked location with weather analysis.

```python
def get_ride_recommendations(
    self,
    long_rides: List[LongRide],
    clicked_lat: float,
    clicked_lon: float,
    target_duration_hours: Optional[float] = None,
    target_distance_km: Optional[float] = None
) -> List[RideRecommendation]
```

**Parameters:**
- `long_rides`: List of LongRide objects
- `clicked_lat`: Latitude of clicked location
- `clicked_lon`: Longitude of clicked location
- `target_duration_hours`: Desired ride duration in hours (optional)
- `target_distance_km`: Desired ride distance in km (optional)

**Returns:**
- List of RideRecommendation objects, sorted by score

**Filtering:**
- Duration filter: ±1 hour tolerance
- Distance filter: ±10 km tolerance

**Scoring:**
- Wind favorability (0-1)
- Distance to location
- Precipitation risk assessment

**Example:**
```python
recommendations = analyzer.get_ride_recommendations(
    long_rides,
    41.8781,
    -87.6298,
    target_duration_hours=3.0,
    target_distance_km=50.0
)

for rec in recommendations[:5]:  # Top 5
    print(f"{rec.ride.name}: Wind score {rec.weather_score:.2f}")
```

---

### 8. format_wind_analysis

Format wind analysis into human-readable description.

```python
def format_wind_analysis(
    self,
    wind_analysis: Dict[str, Any]
) -> str
```

**Parameters:**
- `wind_analysis`: Wind analysis dictionary from calculate_wind_score

**Returns:**
- Formatted string describing wind conditions

**Output Format:**
```
Wind: 20.0 km/h from W (270°)
First half score: 0.45 | Second half score: 0.85
Excellent! Headwind out, strong tailwind back - perfect for a long ride
Seg 1: Headwind | Seg 2: Quartering Headwind | ... | Seg 7: Tailwind | Seg 8: Tailwind
```

**Example:**
```python
score, analysis = analyzer.calculate_wind_score(ride, weather)
description = analyzer.format_wind_analysis(analysis)
print(description)
```

---

## Configuration

### Config File Settings

Add to `config/config.yaml`:

```yaml
long_rides:
  # Minimum distance to classify as long ride (km)
  min_distance_km: 15

  # Route matching (#615); see group_similar_rides
  min_coverage: 0.85
  max_p95_deviation_m: null
  name_min_coverage: 0.6
  max_length_ratio: 1.5
  contains_min_coverage: 0.9
  generic_names: []

  # Search radius for location-based recommendations (km)
  search_radius_km: 5

  # Long-ride planner defaults
  default_target_duration_hours: 2.0
  default_target_distance_km: 40
```

There is no `long_rides.use_parallel`/`long_rides.max_workers` config key. Route-naming density is controlled by the top-level `route_naming` block (`sampling_density`, `commute_sampling_density`, etc. — see `docs/TECHNICAL_SPEC.md` § Configuration System); there is no `sample_points`/`max_name_length` key.

---

## Examples

### Complete Workflow Example

```python
from src.long_ride_analyzer import LongRideAnalyzer
from src.data_fetcher import StravaDataFetcher
from src.config import Config

# Initialize
config = Config('config/config.yaml')
fetcher = StravaDataFetcher(client)
activities = fetcher.fetch_activities()
analyzer = LongRideAnalyzer(activities, config)

# Step 1: Classify activities
commutes, long_rides = analyzer.classify_activities(commute_activities)

# Step 2: Group into unique routes
consolidated_rides = analyzer.group_similar_rides(long_rides)

# Step 3: Get recommendations for a location
recommendations = analyzer.get_ride_recommendations(
    consolidated_rides,
    41.8781,  # Chicago
    -87.6298,
    target_duration_hours=3.0
)

# Display results
for rec in recommendations[:5]:
    print(f"\n{rec.ride.name}")
    print(f"  Distance: {rec.ride.distance_km:.1f} km")
    print(f"  Duration: {rec.ride.duration_hours:.1f} hours")
    print(f"  Wind Score: {rec.weather_score:.2f}")
    print(f"  Precipitation: {rec.precipitation_risk}")
    if rec.wind_analysis:
        print(f"  {analyzer.format_wind_analysis(rec.wind_analysis)}")
```

### Custom Matching Thresholds

Thresholds come from config:

```yaml
long_rides:
  min_coverage: 0.9          # stricter: variants must share more of the route
  max_p95_deviation_m: 150   # also require 95% of each ride within 150 m of the other
```

Measure the effect on real rides with `scripts/matching_benchmark/run_long_ride_benchmark.py`
before changing the defaults.

---

## Error Handling

### Common Exceptions

```python
try:
    recommendations = analyzer.get_ride_recommendations(
        long_rides, lat, lon
    )
except ValueError as e:
    # Invalid coordinates or parameters
    print(f"Invalid input: {e}")
except Exception as e:
    # Weather API failure, network issues, etc.
    print(f"Error getting recommendations: {e}")
```

### Logging

The module uses Python's logging framework:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger('src.long_ride_analyzer')
logger.setLevel(logging.INFO)
```

---

## Performance Considerations

### Dataset Size

Grouping cost is dominated by the pairs that survive the coverage screen; later runs reuse cached
pair metrics. See `scripts/matching_benchmark/README.md` for timings on real data.

### Memory Usage

- Prepared tracks are built on demand and only the 256 most recently used are kept, so memory
  doesn't grow with the number of rides.
- The screen works on compact per-ride cell lists, in blocks of rows.

### Optimization Tips

1. **Use caching**: Cache activity data to avoid repeated API calls
2. **Filter early**: Apply distance filters before grouping
3. **Limit search radius**: Smaller radius = fewer comparisons

---

## Version History

### v2.4.0 (March 2026)
- Initial Long Rides API release
- Route grouping and similarity detection
- Weather-based recommendations
- Parallel processing support

### v2.5.0 (Planned)
- Enhanced route comparison algorithms
- Machine learning-based route classification
- Historical weather analysis
- Performance optimizations

---

## See Also

- [Long Rides User Guide](../guides/LONG_RIDES_USER_GUIDE.md)
- [Technical Specification](../TECHNICAL_SPEC.md)
- [Configuration Guide](../../config/config.yaml)