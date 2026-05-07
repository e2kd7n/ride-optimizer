# Technical Specification - Strava Commute Route Analyzer

## 1. Authentication Module (`auth.py`)

### Purpose
Handle Strava OAuth 2.0 authentication flow and token management.

### Key Functions

```python
class StravaAuthenticator:
    def __init__(self, client_id: str, client_secret: str)
    def get_authorization_url(self) -> str
    def exchange_code_for_token(self, code: str) -> dict
    def refresh_access_token(self, refresh_token: str) -> dict
    def save_tokens(self, tokens: dict) -> None
    def load_tokens(self) -> dict
    def get_authenticated_client(self) -> stravalib.Client
```

### Implementation Details
- Use `stravalib.Client` for API interactions
- Store tokens in `config/credentials.json` (gitignored)
- Implement automatic token refresh when expired
- Handle OAuth callback with local server on port 8000

### Error Handling
- Invalid credentials
- Expired tokens
- Network errors during authentication
- Missing scope permissions

---

## 2. Data Fetcher Module (`data_fetcher.py`)

### Purpose
Retrieve and cache activity data from Strava API.

### Key Functions

```python
class StravaDataFetcher:
    def __init__(self, client: stravalib.Client)
    def fetch_activities(self, limit: int = None, after: datetime = None) -> List[Activity]
    def get_activity_details(self, activity_id: int) -> DetailedActivity
    def get_activity_streams(self, activity_id: int) -> dict
    def cache_activities(self, activities: List[Activity]) -> None
    def load_cached_activities(self) -> List[Activity]
    def filter_commute_activities(self, activities: List[Activity]) -> List[Activity]
```

### Data Structure

```python
@dataclass
class Activity:
    id: int
    name: str
    type: str
    start_date: datetime
    distance: float  # meters
    moving_time: int  # seconds
    elapsed_time: int  # seconds
    total_elevation_gain: float  # meters
    start_latlng: Tuple[float, float]
    end_latlng: Tuple[float, float]
    polyline: str  # encoded polyline
    average_speed: float  # m/s
    max_speed: float  # m/s
```

### Caching Strategy
- Save activities to `data/cache/activities.json`
- Include timestamp of last fetch
- Only fetch new activities on subsequent runs
- Compress polyline data for storage efficiency

### Filtering Criteria
- Activity type: Ride, EBikeRide
- Distance: 2-30 km (configurable)
- Has GPS data (polyline exists)
- Exclude virtual rides

---

## 3. Location Finder Module (`location_finder.py`)

### Purpose
Identify home and work locations using clustering algorithms.

### Key Functions

```python
class LocationFinder:
    def __init__(self, activities: List[Activity])
    def extract_endpoints(self) -> List[Tuple[float, float, datetime]]
    def cluster_locations(self, eps: float = 0.002) -> List[Cluster]
    def identify_home_work(self) -> Tuple[Location, Location]
    def get_location_statistics(self, location: Location) -> dict
```

### Algorithm: DBSCAN Clustering

**Parameters:**
- `eps`: 0.002 degrees (~200 meters at mid-latitudes)
- `min_samples`: 5 activities minimum

**Process:**
1. Extract all start and end coordinates with timestamps
2. Apply DBSCAN to find location clusters
3. Rank clusters by frequency
4. Use time-of-day heuristics to distinguish home from work:
   - Calculate average departure/arrival times for each cluster
   - Morning departures (6-10 AM) → likely home
   - Evening arrivals (4-8 PM) → likely home
   - Inverse patterns → likely work

### Data Structure

```python
@dataclass
class Location:
    lat: float
    lon: float
    name: str  # "Home" or "Work"
    activity_count: int
    avg_departure_time: time
    avg_arrival_time: time
    radius: float  # cluster radius in meters
```

### Edge Cases
- Multiple work locations (choose most frequent)
- Irregular schedules (use median times)
- Insufficient data (require minimum 10 activities)

---

## 4. Route Analyzer Module (`route_analyzer.py`)

### Purpose
Extract, group, and analyze route variants between home and work.

### Key Functions

```python
class RouteAnalyzer:
    def __init__(self, activities: List[Activity], home: Location, work: Location)
    def extract_routes(self, direction: str) -> List[Route]
    def decode_polylines(self, route: Route) -> List[Tuple[float, float]]
    def calculate_route_similarity(self, route1: Route, route2: Route) -> float
    def group_similar_routes(self, threshold: float = 0.85) -> List[RouteGroup]
    def calculate_route_metrics(self, route_group: RouteGroup) -> RouteMetrics
```

### Route Similarity Algorithm

**Primary Method: Fréchet Distance (as of March 2026)**

The system uses Fréchet distance as the primary similarity metric, with Hausdorff distance as a secondary validation check.

```python
def calculate_route_similarity(route1, route2):
    # Primary: Fréchet distance (path similarity with point order)
    frechet_sim = calculate_frechet_similarity(coords1, coords2)
    
    # Secondary: Hausdorff validation (spatial proximity check)
    hausdorff_sim = calculate_hausdorff_similarity(coords1, coords2)
    
    # If routes are spatially far apart, penalize
    if hausdorff_sim < 0.50:
        return frechet_sim * 0.7  # 30% penalty
    else:
        return frechet_sim
```

**Why Fréchet Distance?**
- Considers point order (like walking a dog on a leash)
- Better captures routes that follow the same path
- More robust to GPS sampling differences (~76m average point spacing)
- Validated on 9,251 route pairs with 100% agreement with Hausdorff

**Grouping Threshold:**
- Similarity > 0.70 → same route variant (configurable)
- Fréchet distance threshold: 300m
- Hausdorff validation threshold: 0.50 (spatial sanity check)
- Consider both forward and reverse directions

**Legacy Method: Hausdorff Distance**
```python
def hausdorff_distance(route1_coords, route2_coords):
    # Calculate maximum minimum distance between point sets
    # Normalize by route length
    # Return similarity score (0-1)
```
Still used as secondary validation to catch spatially distant routes.

### Data Structures

```python
@dataclass
class Route:
    activity_id: int
    direction: str  # "home_to_work" or "work_to_home"
    coordinates: List[Tuple[float, float]]
    distance: float
    duration: int
    elevation_gain: float
    timestamp: datetime
    
@dataclass
class RouteGroup:
    id: str
    routes: List[Route]
    representative_route: Route  # median route
    frequency: int
    
@dataclass
class RouteMetrics:
    avg_duration: float
    std_duration: float
    avg_distance: float
    avg_speed: float
    avg_elevation: float
    consistency_score: float  # 1 - (std/mean)
    usage_frequency: int
```

### Metrics Calculation

**Duration Statistics:**
- Mean, median, std deviation
- Remove outliers (>2 std deviations)

**Speed Analysis:**
- Average speed
- Speed consistency
- Identify stop patterns (speed < 1 m/s)

**Elevation Profile:**
- Total gain/loss
- Maximum gradient
- Flat vs hilly classification

---

## 5. Optimizer Module (`optimizer.py`)

### Purpose
Score and rank routes based on multiple criteria.

### Key Functions

```python
class RouteOptimizer:
    def __init__(self, route_groups: List[RouteGroup], weights: dict)
    def calculate_time_score(self, metrics: RouteMetrics) -> float
    def calculate_distance_score(self, metrics: RouteMetrics) -> float
    def calculate_safety_score(self, route_group: RouteGroup) -> float
    def calculate_composite_score(self, route_group: RouteGroup) -> float
    def rank_routes(self) -> List[Tuple[RouteGroup, float]]
    def get_optimal_route(self) -> RouteGroup
```

### Scoring Formulas

**Time Score (0-100):**
```python
time_score = 100 * (1 - (duration - min_duration) / (max_duration - min_duration))
consistency_bonus = consistency_score * 10
final_time_score = time_score + consistency_bonus
```

**Distance Score (0-100):**
```python
distance_score = 100 * (1 - (distance - min_distance) / (max_distance - min_distance))
```

**Safety Score (0-100):**
```python
# Frequency component (40%)
frequency_score = min(100, (usage_count / max_usage_count) * 100)

# Road type inference (30%)
# Analyze speed patterns and GPS track smoothness
straightness_score = calculate_path_straightness()
speed_variance_score = 100 - (speed_std / speed_mean * 100)
road_score = (straightness_score + speed_variance_score) / 2

# Elevation component (30%)
elevation_penalty = min(50, elevation_gain / 10)  # -5 points per 100m
elevation_score = 100 - elevation_penalty

safety_score = (frequency_score * 0.4 + road_score * 0.3 + elevation_score * 0.3)
```

**Composite Score:**
```python
composite = (
    time_score * weights['time'] +
    distance_score * weights['distance'] +
    safety_score * weights['safety']
)
```

### Default Weights
- Time: 0.4 (40%)
- Distance: 0.3 (30%)
- Safety: 0.3 (30%)

---

## 6. Visualizer Module (`visualizer.py`)

### Purpose
Generate interactive maps using Folium.

### Key Functions

```python
class RouteVisualizer:
    def __init__(self, route_groups: List[RouteGroup], home: Location, work: Location)
    def create_base_map(self) -> folium.Map
    def add_route_layer(self, route_group: RouteGroup, color: str, weight: int) -> None
    def add_location_markers(self) -> None
    def add_heatmap_layer(self) -> None
    def add_route_statistics_popup(self, route_group: RouteGroup) -> str
    def generate_map(self, output_path: str) -> None
```

### Map Features

**Base Map:**
- Center on midpoint between home and work
- Zoom level: 13 (configurable)
- Tile layer: OpenStreetMap or CartoDB Positron

**Route Layers:**
- Each route group in different color
- Optimal route: thick red line (weight=5)
- Alternative routes: thinner lines (weight=3)
- Opacity: 0.7 for non-optimal routes

**Markers:**
- Home: green house icon
- Work: blue building icon
- Custom icons from Font Awesome

**Interactive Elements:**
- Click route for statistics popup
- Hover for route name
- Layer control to toggle routes
- Legend with route comparison

**Heatmap:**
- Show most frequently used paths
- Gradient: blue (low) → red (high)
- Radius: 15 pixels

---

## 7. Report Generator Module (`report_generator.py`)

### Purpose
Create comprehensive HTML reports with embedded maps and statistics.

### Key Functions

```python
class ReportGenerator:
    def __init__(self, analysis_results: dict)
    def generate_summary_section(self) -> str
    def generate_comparison_table(self) -> str
    def generate_statistics_section(self) -> str
    def generate_recommendations(self) -> str
    def render_template(self, template_name: str, context: dict) -> str
    def save_report(self, output_path: str) -> None
```

### Report Structure

**HTML Template (Jinja2):**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Strava Commute Analysis Report</title>
    <style>/* Bootstrap + custom CSS */</style>
</head>
<body>
    <div class="container">
        <h1>Commute Route Analysis</h1>
        
        <!-- Executive Summary -->
        <section id="summary">
            <h2>Recommended Route</h2>
            <div class="alert alert-success">
                <strong>Route {{ optimal_route.id }}</strong>
                <p>{{ optimal_route.description }}</p>
            </div>
        </section>
        
        <!-- Comparison Table -->
        <section id="comparison">
            <h2>Route Comparison</h2>
            <table class="table">
                <!-- Route metrics table -->
            </table>
        </section>
        
        <!-- Interactive Map -->
        <section id="map">
            <h2>Route Visualization</h2>
            <div id="map-container">
                {{ map_html | safe }}
            </div>
        </section>
        
        <!-- Detailed Statistics -->
        <section id="statistics">
            <h2>Detailed Analysis</h2>
            <!-- Charts and graphs -->
        </section>
        
        <!-- Recommendations -->
        <section id="recommendations">
            <h2>Recommendations</h2>
            <ul>
                <li>Primary route: {{ primary_route }}</li>
                <li>Alternative for variety: {{ alternative_route }}</li>
                <li>Weather considerations: {{ weather_notes }}</li>
            </ul>
        </section>
    </div>
</body>
</html>
```

### Statistics to Include

**Summary Metrics:**
- Total activities analyzed
- Date range
- Total distance/time commuted
- Average commute time
- Potential time savings with optimal route

**Route Comparison:**
- Distance, duration, speed for each route
- Elevation profile
- Usage frequency
- Composite score

**Visualizations:**
- Bar chart: route comparison
- Line chart: commute time trends
- Pie chart: route usage distribution

---

## 8. Configuration System

### Configuration File (`config/config.yaml`)

```yaml
strava:
  client_id: ${STRAVA_CLIENT_ID}
  client_secret: ${STRAVA_CLIENT_SECRET}

data_fetching:
  cache_enabled: true
  cache_duration_days: 365  # Extended to 1 year - historical data doesn't change
  max_activities: 500

location_detection:
  clustering:
    eps: 0.002  # ~200 meters
    min_samples: 5
  time_windows:
    morning_start: "06:00"
    morning_end: "10:00"
    evening_start: "16:00"
    evening_end: "20:00"

route_filtering:
  min_distance_km: 2
  max_distance_km: 30
  activity_types:
    - Ride
    - EBikeRide
  exclude_virtual: true

route_analysis:
  similarity_threshold: 0.70  # Fréchet distance threshold (0.70 = routes follow similar paths)
  min_route_frequency: 2
  enable_geocoding: true  # Enable reverse geocoding for route naming
  outlier_tolerance_percentile: 95.0  # Ignore worst 5% of point deviations

route_naming:
  sampling_density: 10              # Number of points to sample along route
  min_segment_length_pct: 10        # Minimum % to be considered significant segment
  show_full_path: true              # Show start → middle → end format
  max_segments_in_name: 3           # Maximum segments to include in name
  enable_segment_naming: true       # Feature flag to enable/disable segment-based naming

optimization:
  weights:
    time: 0.35      # Speed and duration
    distance: 0.25  # Route length
    safety: 0.25    # Familiarity and road conditions
    weather: 0.15   # Wind impact on cycling efficiency
  weather_enabled: true  # Enable real-time weather analysis

visualization:
  map:
    zoom_level: 13
    tile_layer: "CartoDB Positron"
  colors:
    optimal: "#FF0000"
    alternative: ["#00FF00", "#0000FF", "#FFA500", "#800080"]
  route_weight:
    optimal: 5
    alternative: 3

long_rides:
  enabled: true
  min_distance_km: 15  # Minimum distance to be considered a long ride
  search_radius_km: 5  # Radius to search for rides near clicked location
  default_target_duration_hours: 2.0
  default_target_distance_km: 40

output:
  report_directory: "output/reports"
  map_filename: "route_map.html"
  report_filename: "commute_analysis.html"

units:
  system: "imperial"  # Options: "metric" or "imperial"
  # metric: km, km/h, m/s (wind), °C
  # imperial: mi, mph, mph (wind), °F
```

---

## 9. Main Entry Point (`main.py`)

### Command-Line Interface

```python
import argparse

def main():
    parser = argparse.ArgumentParser(description='Analyze Strava commute routes')
    parser.add_argument('--auth', action='store_true', help='Authenticate with Strava')
    parser.add_argument('--fetch', action='store_true', help='Fetch new activities')
    parser.add_argument('--analyze', action='store_true', help='Analyze routes')
    parser.add_argument('--config', type=str, default='config/config.yaml')
    parser.add_argument('--output', type=str, default='output/reports')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Authentication
    if args.auth:
        authenticate_strava(config)
        return
    
    # Main workflow
    client = get_authenticated_client(config)
    
    if args.fetch:
        fetch_activities(client, config)
    
    if args.analyze:
        analyze_and_generate_report(client, config, args.output)

if __name__ == '__main__':
    main()
```

### Workflow

1. **Authentication** (first run only)
   - Open browser for OAuth
   - Save tokens

2. **Data Fetching**
   - Load cached activities
   - Fetch new activities if needed
   - Update cache

3. **Location Identification**
   - Cluster endpoints
   - Identify home and work

4. **Route Analysis**
   - Extract routes between locations
   - Group similar routes
   - Calculate metrics

5. **Optimization**
   - Score all routes
   - Rank by composite score

6. **Visualization**
   - Generate interactive map
   - Create HTML report

7. **Output**
   - Save report to output directory
   - Print summary to console

---

## 10. Error Handling Strategy

### Exception Hierarchy

```python
class StravaAnalyzerError(Exception):
    """Base exception"""

class AuthenticationError(StravaAnalyzerError):
    """Authentication failed"""

class DataFetchError(StravaAnalyzerError):
    """Failed to fetch data"""

class InsufficientDataError(StravaAnalyzerError):
    """Not enough activities for analysis"""

class LocationDetectionError(StravaAnalyzerError):
    """Could not identify home/work locations"""
```

### Error Handling Patterns

```python
try:
    activities = fetch_activities(client)
except RateLimitExceeded:
    logger.warning("Rate limit exceeded, using cached data")
    activities = load_cached_activities()
except NetworkError as e:
    logger.error(f"Network error: {e}")
    raise DataFetchError("Could not fetch activities")

if len(activities) < 10:
    raise InsufficientDataError(
        f"Need at least 10 activities, found {len(activities)}"
    )
```

---

## 11. Testing Strategy

### Unit Tests

```python
# tests/test_location_finder.py
def test_cluster_locations():
    activities = create_mock_activities()
    finder = LocationFinder(activities)
    clusters = finder.cluster_locations()
    assert len(clusters) >= 2

def test_identify_home_work():
    activities = create_commute_activities()
    finder = LocationFinder(activities)
    home, work = finder.identify_home_work()
    assert home.name == "Home"
    assert work.name == "Work"
```

### Integration Tests

```python
# tests/test_integration.py
def test_full_workflow():
    # Mock Strava API
    with mock_strava_api():
        client = get_authenticated_client()
        activities = fetch_activities(client)
        home, work = identify_locations(activities)
        routes = analyze_routes(activities, home, work)
        optimal = optimize_routes(routes)
        assert optimal is not None
```

### Test Data

- Create synthetic activity data
- Mock Strava API responses
- Test edge cases:
  - No activities
  - Single location
  - Irregular patterns
  - Missing GPS data

---

## 12. Performance Considerations

### Optimization Strategies

1. **Caching**
   - Cache API responses
   - Store processed data
   - Avoid redundant calculations

2. **Batch Processing**
   - Fetch activities in batches
   - Process routes in parallel (if needed)

3. **Memory Management**
   - Stream large datasets
   - Clear unused data
   - Use generators for iteration

4. **API Rate Limiting**
   - Respect Strava limits
   - Implement exponential backoff
   - Use cached data when possible

### Expected Performance

- Authentication: < 5 seconds
- Fetch 100 activities: 10-30 seconds
- Location clustering: < 1 second
- Route analysis: 5-10 seconds
- Map generation: 2-5 seconds
- Total runtime: 30-60 seconds

---

## 13. Dependencies

### Core Requirements

```
stravalib>=0.10.0
pandas>=1.5.0
numpy>=1.23.0
scikit-learn>=1.1.0
geopy>=2.3.0
folium>=0.14.0
jinja2>=3.1.0
pyyaml>=6.0
python-dotenv>=0.21.0
polyline>=2.0.0
requests>=2.28.0
```

### Development Requirements

```
pytest>=7.2.0
pytest-cov>=4.0.0
pytest-mock>=3.11.0
black>=22.10.0
flake8>=5.0.0
mypy>=0.991

---

## 8. Weather Fetcher Module (`weather_fetcher.py`)

### Purpose
Fetch real-time weather data and analyze wind impact on cycling routes.

### Key Functions

```python
class WeatherFetcher:
    def __init__(self, cache_radius_km: float = 2.0, cache_duration_hours: float = 1.5)
    def get_weather(self, lat: float, lon: float) -> Dict[str, Any]
    def get_route_weather(self, coordinates: List[Tuple[float, float]]) -> Dict[str, Any]
    def calculate_wind_impact(self, route_coords: List[Tuple[float, float]], 
                             wind_speed: float, wind_direction: float) -> Dict[str, float]
    def _calculate_bearing(self, coord1: Tuple[float, float], 
                          coord2: Tuple[float, float]) -> float
```

### Weather Data Structure

```python
{
    'temperature': float,  # Celsius
    'wind_speed': float,   # km/h
    'wind_direction': float,  # degrees (0-360, direction FROM)
    'wind_gusts': float,   # km/h
    'humidity': float,     # percentage
    'precipitation': float,  # mm/h
    'timestamp': str       # ISO format
}
```

### Wind Impact Calculation

**Algorithm:**
1. Sample weather at 3 points along route (start, middle, end)
2. Calculate route bearing for each segment
3. Determine relative wind angle
4. Calculate headwind/tailwind component: `wind_speed × cos(angle)`
5. Calculate crosswind component: `wind_speed × |sin(angle)|`
6. Estimate time impact based on research coefficients

**Impact Coefficients:**
- Headwind: +1.5% time per 1 km/h
- Tailwind: -1.0% time per 1 km/h  
- Crosswind: +0.5% time per 1 km/h

**Weather Score (0-100):**
```python
base_score = 50
tailwind_bonus = min(40, avg_tailwind * 2)  # Up to +40
headwind_penalty = min(40, avg_headwind * 2)  # Up to -40
crosswind_penalty = min(10, avg_crosswind)  # Up to -10
score = base_score + tailwind_bonus - headwind_penalty - crosswind_penalty
```

### Caching Strategy

- **Spatial Cache**: Locations within 2km share cached data
- **Temporal Cache**: Data valid for 90 minutes
- **Cache Key**: SHA256 hash of rounded coordinates + timestamp
- **Cache File**: `cache/weather_cache.json`

### API Integration

**Provider:** Open-Meteo (free, no API key required)
- **Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **Rate Limit:** None (reasonable use)
- **Data Freshness:** Updated hourly

---

## 9. Route Namer Module (`route_namer.py`)

### Purpose
Generate human-readable route names based on route segments, showing connection streets and main routes to provide complete journey context.

### Key Functions

```python
class RouteNamer:
    def __init__(self, config=None)
    def name_route(self, coordinates: List[Tuple[float, float]], route_id: str, direction: str) -> str
    def _analyze_route_geography(self, coordinates: List[Tuple[float, float]]) -> Dict
    def _get_strategic_sample_points(self, coordinates: List[Tuple[float, float]]) -> List
    def _identify_route_segments(self, coordinates: List[Tuple[float, float]]) -> List[Dict]
    def _get_location_details(self, point: Tuple[float, float]) -> Optional[Dict]
    def _generate_descriptive_name(self, route_info: Dict, route_id: str, direction: str) -> str
    def _generate_descriptive_name_legacy(self, route_info: Dict, route_id: str, direction: str) -> str
```

### Naming Algorithm

**Current Implementation (v0.8.0 - Segment-Based Naming):**

1. **Sample Strategic Points** (10 points)
   - First 3 points: Capture start street
   - Middle 4 points: At 20%, 40%, 60%, 80% to capture transitions
   - Last 3 points: Capture end street

2. **Identify Route Segments**
   - Detect street changes along the route
   - Calculate segment length percentages
   - Classify segments by position (start/middle/end)

3. **Generate Segment-Based Names**
   - **3+ segments**: "Start St → Main St → End St"
   - **2 segments**: "Main St via Connection St" (if main > 60%) or "Start St → End St"
   - **1 segment**: "Via Main St"
   - **Fallback**: Legacy naming strategies

4. **Filter Significant Segments**
   - Only include segments ≥ 10% of route length (configurable)
   - Ignore segments without street names

**Legacy Implementation (v0.6.0 - Still available as fallback):**
1. Sample 5 strategic points along route (start, 25%, 50%, 75%, end)
2. Reverse geocode each point to get street/path names
3. Count frequency of each street name
4. Select most common street as route name
5. Format as "Via [Street Name]"

### Geocoding

**Provider:** Nominatim (OpenStreetMap)
- **Rate Limit:** 1 request per second
- **Timeout:** 10 seconds per request
- **User Agent:** "strava_commute_analyzer"

**Cache Strategy:**
- Persistent cache in `cache/geocoding_cache.json`
- Key: Rounded coordinates (4 decimal places ≈ 11m precision)
- Never expires (street names rarely change)

### Configuration Options (v0.8.0)

```yaml
route_naming:
  sampling_density: 10              # Number of points to sample along route
  min_segment_length_pct: 10        # Minimum % to be considered significant segment
  show_full_path: true              # Show start → middle → end format
  max_segments_in_name: 3           # Maximum segments to include in name
  enable_segment_naming: true       # Feature flag to enable/disable
```

### Segment Identification Algorithm

```python
def _identify_route_segments(self, coordinates):
    """
    Identify distinct route segments based on street changes.
    
    Returns:
        List of segments with:
        - street: Street name
        - length_pct: Percentage of route on this street
        - position: 'start', 'middle', or 'end'
        - sample_points: Number of sample points on this street
    """
    sample_points = self._get_strategic_sample_points(coordinates)
    segments = []
    current_street = None
    
    for point in sample_points:
        location_info = self._get_location_details(point)
        street = location_info.get('street') if location_info else None
        
        if street != current_street:
            # Street changed - start new segment
            segments.append({
                'street': street,
                'sample_points': 1
            })
            current_street = street
        else:
            # Same street - extend current segment
            segments[-1]['sample_points'] += 1
    
    # Calculate percentages and positions
    total_points = len(sample_points)
    for i, segment in enumerate(segments):
        segment['length_pct'] = (segment['sample_points'] / total_points) * 100
        segment['position'] = 'start' if i == 0 else 'end' if i == len(segments)-1 else 'middle'
    
    return segments
```

### Name Selection Logic

**Segment-Based Selection (Primary):**
```python
def _generate_descriptive_name(self, route_info, route_id, direction):
    segments = route_info.get('segments', [])
    
    # Filter significant segments (≥ min_segment_length_pct)
    significant = [s for s in segments
                   if s.get('street') and s.get('length_pct', 0) >= self.min_segment_length_pct]
    
    if len(significant) >= 3:
        # Full path: "Start St → Main St → End St"
        start = significant[0]['street']
        main = max(significant[1:-1], key=lambda s: s['length_pct'])['street']
        end = significant[-1]['street']
        return f"{start} → {main} → {end}"
    
    elif len(significant) == 2:
        # Two segments
        main = max(significant, key=lambda s: s['length_pct'])
        if main['length_pct'] > 60:
            connection = min(significant, key=lambda s: s['length_pct'])
            return f"{main['street']} via {connection['street']}"
        else:
            return f"{significant[0]['street']} → {significant[1]['street']}"
    
    elif len(significant) == 1:
        # Single route
        return f"Via {significant[0]['street']}"
    
    # Fallback to legacy naming
    return self._generate_descriptive_name_legacy(route_info, route_id, direction)
```

**Legacy Selection (Fallback):**
```python
def _generate_descriptive_name_legacy(self, route_info, route_id, direction):
    major_streets = route_info.get('major_streets', [])
    neighborhoods = route_info.get('neighborhoods', [])
    
    # Priority order:
    # 1. Multiple major streets: "Street A → Street B"
    # 2. Single street + neighborhood: "Through [Neighborhood] via [Street]"
    # 3. Just major street: "Via [Street]"
    # 4. Just neighborhood: "Through [Neighborhood]"
    # 5. Generic fallback: "Route X to Work/Home"
```

### Error Handling

- **Geocoding Timeout**: Use cached data or skip point (with debug logging)
- **Rate Limit**: Automatic 1-second delay between requests
- **No Results**: Mark as "Unknown Street" and continue
- **Network Error**: Graceful degradation with generic names
- **Segment Naming Disabled**: Falls back to legacy naming automatically
- **All Exceptions**: Specific exception types (ValueError, AttributeError, TypeError) with debug logging

---

## 10. Long Ride Analyzer Module (`long_ride_analyzer.py`)

### Purpose
Analyze and recommend long recreational rides separate from commute analysis. Uses advanced route similarity algorithms and weather integration for intelligent recommendations.

### Key Classes

```python
@dataclass
class LongRide:
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
    is_loop: bool  # True if start/end within 500m
    type: str  # Activity type
    uses: int = 1  # Number of times route ridden
    activity_ids: List[int] = None
    activity_dates: List[str] = None

@dataclass
class RideRecommendation:
    ride: LongRide
    distance_to_location: float  # meters
    weather_score: float  # 0-1
    precipitation_risk: str  # "none", "low", "medium", "high"
    recommended_start_time: Optional[str]
    estimated_duration: Optional[float]  # hours
    route_description: str
    wind_analysis: Optional[Dict[str, Any]]
```

### Key Functions

```python
class LongRideAnalyzer:
    def __init__(self, activities: List[Activity], config)
    
    # Classification & Grouping
    def classify_activities(self, commute_activities: List[Activity]) -> Tuple[List[Activity], List[Activity]]
    def group_rides_by_name(self, long_ride_activities: List[Activity]) -> Tuple[Dict[str, List[Activity]], List[Activity]]
    def consolidate_similar_named_groups(self, name_groups: Dict[str, List[Activity]], similarity_threshold: float = 0.20) -> Dict[str, List[Activity]]
    def consolidate_named_groups(self, name_groups: Dict[str, List[Activity]]) -> List[LongRide]
    
    # Route Matching (with Parallel Processing)
    def match_unnamed_rides_to_groups(self, unnamed_rides: List[Activity], named_groups: Dict[str, List[Activity]], similarity_threshold: float = 0.15, use_parallel: bool = True, max_workers: int = None) -> Tuple[Dict[str, List[Activity]], List[Activity]]
    def generate_fallback_names(self, unnamed_rides: List[Activity]) -> Dict[str, List[Activity]]
    
    # Extraction & Discovery
    def extract_long_rides(self, long_ride_activities: List[Activity]) -> List[LongRide]
    def find_rides_near_location(self, long_rides: List[LongRide], clicked_lat: float, clicked_lon: float, search_radius_km: float = 5.0) -> List[LongRide]
    
    # Weather Analysis
    def calculate_wind_score(self, ride: LongRide, current_weather: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]
    def format_wind_analysis(self, wind_analysis: Dict[str, Any]) -> str
    
    # Recommendations
    def get_ride_recommendations(self, long_rides: List[LongRide], clicked_lat: float, clicked_lon: float, target_duration_hours: Optional[float] = None, target_distance_km: Optional[float] = None) -> List[RideRecommendation]
```

### Long Ride Criteria

- **Minimum Distance**: 15 km (configurable via `long_rides.min_distance_km`)
- **Activity Type**: Ride, GravelRide, EBikeRide (excludes VirtualRide)
- **GPS Data**: Must have valid polyline and start/end coordinates
- **Exclude**: Commutes, virtual rides (by type and name keywords)
- **Virtual Ride Detection**: Filters by type (VirtualRide) and keywords (Zwift, Trainer, Indoor, Rouvy, Sufferfest, Peloton)

### Route Similarity Algorithm

Uses dual-metric approach for accurate route matching:

1. **Fréchet Distance**: Measures route shape similarity
   - Threshold: 0.15-0.20 km (configurable)
   - Primary metric for route matching

2. **Hausdorff Distance**: Measures maximum deviation
   - Combined with Fréchet for robust matching
   - Handles GPS drift and minor variations

3. **Loop Detection**: Start/end within 500m

### Parallel Processing

Intelligent worker allocation based on dataset size:
- **< 20 rides**: 2 workers (minimum parallelism)
- **20-100 rides**: 4 workers (balanced)
- **> 100 rides**: 6 workers (maximum efficiency)
- **< 10 rides**: Sequential processing (no overhead)

### Weather Integration

Wind analysis with strong preference for tailwinds on return:

**Wind Score Calculation:**
- Divides route into 8 segments
- Calculates bearing for each segment
- Determines wind type (headwind, tailwind, quartering)
- **70% weight on second half** (favors tailwinds coming back)
- 10% bonus for consistent tailwinds in second half

**Wind Types & Scores:**
- Headwind (< 45°): 0.3
- Quartering headwind (45-90°): 0.5
- Quartering tailwind (90-135°): 0.8
- Tailwind (> 135°): 1.0

### Configuration

```yaml
long_rides:
  min_distance_km: 15  # Minimum distance for long rides
  similarity_threshold: 0.15  # Route matching threshold (km)
  consolidation_threshold: 0.20  # Group consolidation threshold (km)
  search_radius_km: 5.0  # Location search radius
  use_parallel: true  # Enable parallel processing
  max_workers: null  # Auto-detect (2-6 workers)

route_naming:
  sample_points: 10  # Points along route for naming
  max_name_length: 50  # Maximum name length
```

### Performance Characteristics

- **Memory**: ~1-5 KB per LongRide object
- **Processing**: O(n²) for route comparison, optimized with parallel processing
- **Caching**: Route similarity results cached for repeated queries
- **Scalability**: Handles 1000+ rides efficiently with parallel processing

### Documentation

- **User Guide**: [docs/guides/LONG_RIDES_USER_GUIDE.md](guides/LONG_RIDES_USER_GUIDE.md)
- **API Reference**: [docs/api/LONG_RIDES_API.md](api/LONG_RIDES_API.md)

---

## 11. Units Module (`units.py`)

### Purpose
Handle unit conversions and formatting for international users.

### Key Functions

```python
class UnitConverter:
    def __init__(self, system: str = 'metric')  # 'metric' or 'imperial'
    def distance(self, meters: float) -> str
    def speed(self, meters_per_second: float) -> str
    def elevation(self, meters: float) -> str
    def temperature(self, celsius: float) -> str
    def wind_speed(self, meters_per_second: float) -> str
```

### Conversion Factors

**Metric System:**
- Distance: meters → kilometers (÷ 1000)
- Speed: m/s → km/h (× 3.6)
- Elevation: meters (no conversion)
- Temperature: Celsius (no conversion)
- Wind: m/s (no conversion)

**Imperial System:**
- Distance: meters → miles (÷ 1609.34)
- Speed: m/s → mph (× 2.23694)
- Elevation: meters → feet (× 3.28084)
- Temperature: Celsius → Fahrenheit (× 9/5 + 32)
- Wind: m/s → mph (× 2.23694)

### Formatting

```python
# Metric examples
converter.distance(5280)  # "5.3 km"
converter.speed(8.33)     # "30.0 km/h"
converter.elevation(152)  # "152 m"

# Imperial examples
converter.distance(5280)  # "3.3 mi"
converter.speed(8.33)     # "18.6 mph"
converter.elevation(152)  # "499 ft"
```

---

## 12. Forecast Generator Module (`forecast_generator.py`)

### Purpose
Generate 7-day weather forecasts for commute planning.

### Key Functions

```python
class ForecastGenerator:
    def __init__(self, location: Tuple[float, float])
    def get_7day_forecast(self) -> List[Dict]
    def get_commute_windows(self, date: str) -> Dict[str, Dict]
    def calculate_comfort_score(self, weather: Dict) -> int
    def generate_recommendations(self, forecast: List[Dict]) -> List[str]
```

### Forecast Data Structure

```python
{
    'date': str,  # YYYY-MM-DD
    'morning': {  # 7-9 AM
        'temperature': float,
        'wind_speed': float,
        'wind_direction': float,
        'precipitation': float,
        'comfort_score': int  # 0-100
    },
    'evening': {  # 4-6 PM
        # Same structure as morning
    },
    'summary': str,  # "Good", "Fair", "Poor"
    'recommendations': List[str]
}
```

### Comfort Score Calculation

```python
score = 100
# Temperature penalties
if temp < 0: score -= 30
elif temp < 5: score -= 20
elif temp > 30: score -= 20
elif temp > 35: score -= 30

# Wind penalties
if wind > 30: score -= 30
elif wind > 20: score -= 20
elif wind > 15: score -= 10

# Precipitation penalties
if precip > 5: score -= 40  # Heavy rain
elif precip > 1: score -= 20  # Light rain
elif precip > 0: score -= 10  # Drizzle

return max(0, score)
```

### Recommendations

Based on comfort scores:
- **80-100**: "Excellent conditions for cycling"
- **60-79**: "Good conditions, dress appropriately"
- **40-59**: "Fair conditions, consider alternatives"
- **20-39**: "Poor conditions, transit recommended"
- **0-19**: "Dangerous conditions, avoid cycling"

---

## 13. Test Infrastructure

### Test Organization

```
tests/
├── __init__.py
├── README.md
├── TEST_DATA_README.md
├── setup_test_data.py       # Synthetic test data generator
├── test_config.py           # Configuration tests (8 tests)
├── test_units.py            # Unit conversion tests (13 tests)
├── test_data_fetcher.py     # Data fetching tests (7 tests)
├── test_route_analyzer.py   # Route analysis tests (7 tests)
└── test_integration.py      # End-to-end tests (8 tests)
```

### Test Data System

**Separate Cache Files:**
- Production: `data/cache/activities.json`
- Test: `data/cache/activities_test.json`

**Test Data Generator:**
```python
# tests/setup_test_data.py
def create_test_activities():
    """Generate 12 synthetic activities for testing."""
    # 3 route variants × 2 directions × 2 instances
    # Realistic polylines, metrics, timestamps
```

**Usage in Tests:**
```python
from src.data_fetcher import StravaDataFetcher

# Always use test cache in tests
fetcher = StravaDataFetcher(client, config, use_test_cache=True)
```

### Test Coverage (as of v0.7.0)

- **Overall**: 17% (baseline)
- **config.py**: 100%
- **units.py**: 92%
- **data_fetcher.py**: 45%
- **route_analyzer.py**: 38%

**Target**: 80% coverage for core modules

### Running Tests

```bash
# All tests
./run_tests.sh all

# With coverage
./run_tests.sh coverage

# Specific test file
pytest -v tests/test_units.py

# Specific test
pytest -v tests/test_units.py::TestUnitConverter::test_metric_distance
```

### Test Status

**Current**: 43/43 tests passing (100% pass rate) ✅

---

## 14. Security & Code Quality

### Security Enhancements (v0.8.0)

**Hash Algorithm (v0.6.0 → v0.8.0):**
- ✅ Replaced MD5 with SHA256 for all cache keys
- Used in `route_analyzer.py` for route similarity cache
- Used in `weather_fetcher.py` for wind analysis cache
- Prevents collision attacks and provides better integrity verification
- Cache files regenerated with new algorithm

**Dependency Management:**
- Regular security audits with `pip-audit`
- Automated vulnerability scanning
- Minimum version requirements in `requirements.txt`

**Exception Handling (v0.8.0):**
- ✅ No bare `except:` statements (all replaced with specific types)
- Specific exception types for all handlers:
  - `ValueError`: Invalid data formats
  - `AttributeError`: Missing object attributes
  - `TypeError`: Incorrect data types
  - `IndexError`: Array access errors
- Debug logging added for all caught exceptions
- Improved troubleshooting capabilities

**Affected Files:**
- `src/data_fetcher.py`: Date parsing exceptions
- `src/route_analyzer.py`: Fréchet distance calculation, cache key generation
- `src/long_ride_analyzer.py`: Polyline decoding, route similarity
- `src/weather_fetcher.py`: Wind analysis cache keys

### Code Quality Standards

**Style:**
- PEP 8 compliant
- Type hints for function signatures
- Docstrings for all public methods

**Error Handling:**
```python
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except NetworkError as e:
    logger.warning(f"Network issue: {e}")
    return cached_fallback()
```

**Logging Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Recoverable issues (using fallbacks)
- `ERROR`: Serious problems requiring attention

---

## 15. Performance Optimizations

### Caching Strategy

**Multi-Level Caching:**
1. **API Response Cache**: Strava activities (7 days)
2. **Geocoding Cache**: Street names (permanent)
3. **Weather Cache**: Current conditions (90 minutes)
4. **Route Similarity Cache**: Fréchet calculations (permanent)
5. **Route Groups Cache**: Grouped routes (until config changes)

**Cache Invalidation:**
- Time-based for weather and activities
- Config-based for route analysis
- Manual clear with `--force-reanalysis` flag

### Parallel Processing

**Route Grouping:**
- Disabled by default (overhead > benefit for typical datasets)
- Available with `--parallel N` flag (N = 1-8 workers)
- ~1.5-2x speedup for >100 routes

**When to Use:**
```bash
# Small dataset (<50 routes): Sequential is faster
python main.py --analyze

# Large dataset (>100 routes): Parallel helps
python main.py --analyze --parallel 4
```

### Memory Management

**Streaming:**
- Activities loaded in batches
- Polylines decoded on-demand
- Large datasets processed incrementally

**Cleanup:**
- Explicit cache clearing when needed
- Temporary data structures freed after use
- Generator patterns for large iterations

---

## 16. API Rate Limiting

### Strava API

**Limits:**
- 100 requests per 15 minutes
- 1,000 requests per day

**Handling:**
```python
try:
    activities = client.get_activities(limit=100)
except RateLimitExceeded:
    logger.warning("Rate limit hit, using cached data")
    activities = load_cached_activities()
```

### Nominatim (Geocoding)

**Limits:**
- 1 request per second
- No daily limit (reasonable use)

**Handling:**
```python
def _reverse_geocode_batch(self, points):
    results = []
    for point in points:
        result = self._geocode_with_cache(point)
        results.append(result)
        time.sleep(1.0)  # Respect rate limit
    return results
```

### Open-Meteo (Weather)

**Limits:**
- No strict limits
- Reasonable use expected

**Best Practices:**
- Cache aggressively (90 minutes)
- Batch requests when possible
- Use spatial caching (2km radius)

---

## 17. Deployment & Configuration

### Environment Variables

```bash
# Required
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret

# Optional
CACHE_DURATION_DAYS=7
LOG_LEVEL=INFO
```

### Configuration File

**Location:** `config/config.yaml`

**Key Sections:**
- `strava`: API credentials
- `data_fetching`: Cache settings
- `location_detection`: Clustering parameters
- `route_filtering`: Distance and type filters
- `route_analysis`: Similarity thresholds
- `optimization`: Scoring weights
- `visualization`: Map settings

### First-Time Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env with your Strava API credentials

# 3. Authenticate
python main.py --auth

# 4. Fetch and analyze
python main.py --fetch --analyze
```

### Maintenance

**Weekly:**
- Fetch new activities: `python main.py --fetch`
- Re-run analysis: `python main.py --analyze`

**Monthly:**
- Clear old caches: `rm cache/*.json`
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Run security audit: `pip-audit`

---

## 18. Future Enhancements

### Planned Features

**P1 (High Priority):**
- Segment-based route naming with connection streets
- Time-aware next commute recommendations
- CI/CD integration with GitHub Actions

**P2 (Medium Priority):**
- Progressive disclosure UI for mobile
- Map direction indicators
- Feature discovery & onboarding

**P4 (Future):**
- Long rides analysis dashboard
- Weather dashboard with 7-day forecast
- Traffic pattern analysis
- Social features (compare with other commuters)

### Technical Debt

- Increase test coverage to 80%
- Add type hints to all modules
- Implement comprehensive error recovery
- Add performance benchmarks
- Create API documentation

---

*Last Updated: 2026-05-07*
*Version: 2.5.0+*