# Long Rides API Documentation

**Module:** `src/long_ride_analyzer.py`  
**Version:** 2.4.0+  
**Last Updated:** 2026-05-07

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
    activity_ids: List[int] = None            # All activity IDs for this route
    activity_dates: List[str] = None          # Dates for each activity
```

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
def __init__(self, activities: List[Activity], config)
```

**Parameters:**
- `activities` (List[Activity]): List of all Strava Activity objects
- `config`: Configuration object with settings

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

### 2. group_rides_by_name

Group long ride activities by their Strava activity names.

```python
def group_rides_by_name(
    self,
    long_ride_activities: List[Activity]
) -> Tuple[Dict[str, List[Activity]], List[Activity]]
```

**Parameters:**
- `long_ride_activities`: List of Activity objects

**Returns:**
- Tuple of (name_groups dict, unnamed_rides list)

**Behavior:**
- Groups activities with identical names
- Treats generic names ("Morning Ride", etc.) as unnamed
- Normalizes names (strips whitespace)

**Example:**
```python
name_groups, unnamed = analyzer.group_rides_by_name(long_rides)
print(f"Created {len(name_groups)} named groups")
print(f"Found {len(unnamed)} unnamed rides")
```

---

### 3. consolidate_similar_named_groups

Consolidate named groups with similar routes despite different names.

```python
def consolidate_similar_named_groups(
    self,
    name_groups: Dict[str, List[Activity]],
    similarity_threshold: float = 0.20
) -> Dict[str, List[Activity]]
```

**Parameters:**
- `name_groups`: Dictionary mapping activity names to lists of activities
- `similarity_threshold`: Maximum Fréchet distance (km) to consider routes similar (default: 0.20)

**Returns:**
- Updated name_groups dictionary with similar routes consolidated

**Algorithm:**
- Uses Fréchet distance + Hausdorff distance
- Compares representative routes from each group
- Merges groups below similarity threshold
- Preserves most common or shortest name

**Example:**
```python
consolidated = analyzer.consolidate_similar_named_groups(name_groups, 0.15)
```

---

### 4. consolidate_named_groups

Convert named activity groups into representative LongRide objects.

```python
def consolidate_named_groups(
    self,
    name_groups: Dict[str, List[Activity]]
) -> List[LongRide]
```

**Parameters:**
- `name_groups`: Dictionary mapping activity names to lists of activities

**Returns:**
- List of LongRide objects representing each unique named route

**Behavior:**
- Selects most recent activity as representative
- Aggregates usage count across all activities
- Collects all activity IDs and dates
- Detects loop routes (start/end within 500m)

**Example:**
```python
consolidated_rides = analyzer.consolidate_named_groups(name_groups)
```

---

### 5. match_unnamed_rides_to_groups

Match unnamed/generic rides to existing named groups using route similarity.

```python
def match_unnamed_rides_to_groups(
    self,
    unnamed_rides: List[Activity],
    named_groups: Dict[str, List[Activity]],
    similarity_threshold: float = 0.15,
    use_parallel: bool = True,
    max_workers: int = None
) -> Tuple[Dict[str, List[Activity]], List[Activity]]
```

**Parameters:**
- `unnamed_rides`: List of activities with generic/no names
- `named_groups`: Dictionary of existing named route groups
- `similarity_threshold`: Maximum Fréchet distance (km) for similarity (default: 0.15)
- `use_parallel`: Whether to use parallel processing (default: True)
- `max_workers`: Maximum worker processes (default: auto 2-6 based on workload)

**Returns:**
- Tuple of (updated_named_groups, still_unnamed_rides)

**Performance:**
- Automatic worker selection based on dataset size:
  - < 20 rides: 2 workers
  - 20-100 rides: 4 workers
  - > 100 rides: 6 workers
- Sequential processing for < 10 rides
- Uses ProcessPoolExecutor for parallelization

**Example:**
```python
updated_groups, still_unnamed = analyzer.match_unnamed_rides_to_groups(
    unnamed_rides,
    name_groups,
    similarity_threshold=0.15,
    use_parallel=True
)
```

---

### 6. generate_fallback_names

Generate geocoded names for rides that couldn't be matched to named groups.

```python
def generate_fallback_names(
    self,
    unnamed_rides: List[Activity]
) -> Dict[str, List[Activity]]
```

**Parameters:**
- `unnamed_rides`: List of activities without specific names

**Returns:**
- Dictionary mapping generated names to activities

**Naming Convention:**
- Loop rides: "Loop Ride (XX.Xkm)"
- Out & back: "Out & Back (XX.Xkm)"
- Generic: "Ride (XX.Xkm)"
- No data: "Unnamed Ride"

**Example:**
```python
fallback_groups = analyzer.generate_fallback_names(still_unnamed)
```

---

### 7. extract_long_rides

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

### 8. find_rides_near_location

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

### 9. calculate_wind_score

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

### 10. get_ride_recommendations

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

### 11. format_wind_analysis

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
  
  # Route similarity thresholds (km)
  similarity_threshold: 0.15
  consolidation_threshold: 0.20
  
  # Search radius for location-based recommendations (km)
  search_radius_km: 5.0
  
  # Parallel processing
  use_parallel: true
  max_workers: null  # null = auto-detect (2-6 workers)

route_naming:
  # Number of sample points along route for naming
  sample_points: 10
  
  # Maximum length of generated route names
  max_name_length: 50
```

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

# Step 2: Group by name
name_groups, unnamed = analyzer.group_rides_by_name(long_rides)

# Step 3: Consolidate similar named groups
name_groups = analyzer.consolidate_similar_named_groups(name_groups)

# Step 4: Match unnamed rides
name_groups, still_unnamed = analyzer.match_unnamed_rides_to_groups(
    unnamed, name_groups
)

# Step 5: Generate fallback names
fallback_groups = analyzer.generate_fallback_names(still_unnamed)
name_groups.update(fallback_groups)

# Step 6: Create LongRide objects
consolidated_rides = analyzer.consolidate_named_groups(name_groups)

# Step 7: Get recommendations for a location
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

### Parallel Processing Example

```python
# Automatic worker selection (recommended)
updated_groups, still_unnamed = analyzer.match_unnamed_rides_to_groups(
    unnamed_rides,
    name_groups,
    use_parallel=True,
    max_workers=None  # Auto: 2-6 workers based on dataset size
)

# Manual worker count
updated_groups, still_unnamed = analyzer.match_unnamed_rides_to_groups(
    unnamed_rides,
    name_groups,
    use_parallel=True,
    max_workers=4  # Force 4 workers
)

# Disable parallel processing
updated_groups, still_unnamed = analyzer.match_unnamed_rides_to_groups(
    unnamed_rides,
    name_groups,
    use_parallel=False
)
```

### Custom Similarity Thresholds

```python
# Stricter matching (routes must be very similar)
name_groups = analyzer.consolidate_similar_named_groups(
    name_groups,
    similarity_threshold=0.10  # 100m tolerance
)

# Looser matching (group more variations together)
name_groups = analyzer.consolidate_similar_named_groups(
    name_groups,
    similarity_threshold=0.30  # 300m tolerance
)
```

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

- **< 100 rides**: Fast, no optimization needed
- **100-500 rides**: Use parallel processing (automatic)
- **> 500 rides**: Consider increasing `max_workers` to 6-8

### Memory Usage

- Each LongRide object: ~1-5 KB (depends on GPS point count)
- 1000 rides: ~1-5 MB memory
- Parallel processing: Additional memory per worker process

### Optimization Tips

1. **Use caching**: Cache activity data to avoid repeated API calls
2. **Filter early**: Apply distance filters before grouping
3. **Adjust thresholds**: Higher similarity thresholds = faster processing
4. **Limit search radius**: Smaller radius = fewer comparisons

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