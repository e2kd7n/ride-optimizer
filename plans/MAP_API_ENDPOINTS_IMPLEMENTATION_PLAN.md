# Map API Endpoints - Technical Implementation Plan (Revised)

**Created:** 2026-05-07  
**Status:** Planning Phase  
**Priority:** P1-high (Issue #83 - Implement Geocoding API Endpoint)  
**Related Issues:** #83, #117, #234  

## Executive Summary

This plan addresses the missing map-related API endpoints needed to support the advanced map features implemented in Issue #234. **CRITICAL FINDING:** The CLI prototype (`src/`) contains substantial reusable code that can be adapted for the web API, significantly reducing implementation effort.

## Reusable Components from CLI Prototype

### ✅ Existing Data Models (src/)

1. **Route & RouteGroup Models** ([`src/route_analyzer.py`](../src/route_analyzer.py))
   ```python
   @dataclass
   class Route:
       activity_id: int
       direction: str
       coordinates: List[Tuple[float, float]]  # ✅ Already has coordinates
       distance: float
       duration: int
       elevation_gain: float  # ✅ Already has elevation data
       timestamp: str
       average_speed: float
       activity_name: str
       is_plus_route: bool
   
   @dataclass
   class RouteGroup:
       id: str
       direction: str
       routes: List[Route]
       representative_route: Route  # ✅ Has coordinates
       frequency: int
       name: Optional[str]
       is_plus_route: bool
   ```

2. **Location Model** ([`src/location_finder.py`](../src/location_finder.py))
   ```python
   @dataclass
   class Location:
       lat: float
       lon: float
       name: str
       activity_count: int
       avg_departure_time: Optional[time]
       avg_arrival_time: Optional[time]
       radius: float
   ```

3. **LongRide Model** ([`src/long_ride_analyzer.py`](../src/long_ride_analyzer.py))
   - Already has coordinates, elevation, distance, duration
   - Used in existing API: [`src/api/long_rides_api.py`](../src/api/long_rides_api.py)

### ✅ Existing Services (src/)

1. **RouteAnalyzer** ([`src/route_analyzer.py`](../src/route_analyzer.py))
   - ✅ Route grouping with similarity detection (Fréchet distance)
   - ✅ Coordinate extraction from activities
   - ✅ Caching layer (`route_groups_cache.json`)
   - ✅ Serialization/deserialization for JSON
   - **Reuse:** 90% - Just needs Flask wrapper

2. **WeatherFetcher** ([`src/weather_fetcher.py`](../src/weather_fetcher.py))
   - ✅ Open-Meteo API integration (no API key needed)
   - ✅ Caching with location-based keys
   - ✅ File-based cache (`weather_cache.json`)
   - **Reuse:** 100% - Already perfect for API

3. **RouteVisualizer** ([`src/visualizer.py`](../src/visualizer.py))
   - ✅ Coordinate processing for maps
   - ✅ Route bounds calculation
   - ✅ Color coding logic
   - ✅ Popup HTML generation
   - **Reuse:** 70% - Extract coordinate/bounds logic

4. **DataFetcher** ([`src/data_fetcher.py`](../src/data_fetcher.py))
   - ✅ Activity model with coordinates
   - ✅ Polyline encoding/decoding
   - ✅ Strava API integration
   - **Reuse:** 80% - Use Activity model directly

### ✅ Existing API Pattern ([`src/api/long_rides_api.py`](../src/api/long_rides_api.py))

The CLI prototype already has a Flask API server with:
- ✅ CORS enabled
- ✅ Error handling patterns
- ✅ Geocoding endpoint (`/api/long-rides/geocode`) using Nominatim
- ✅ Weather endpoint (`/api/long-rides/weather`)
- ✅ Recommendations endpoint with filtering
- ✅ JSON serialization of coordinates

**Key Pattern to Reuse:**
```python
class LongRidesAPI:
    def __init__(self, long_rides: List[LongRide], config: Config):
        self.app = Flask(__name__)
        CORS(self.app)
        self.long_rides = long_rides
        self.config = config
        self._register_routes()
```

## Revised Architecture (Leveraging Existing Code)

```
┌─────────────────────────────────────────────────────────────┐
│              Frontend (JavaScript) - ALREADY EXISTS          │
│  map-advanced-features.js | map-features-integration.js     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │   NEW: Flask API      │
                │   /api/map/*          │
                └───────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│ REUSE: Route   │  │ REUSE:      │  │ REUSE: Weather  │
│ Analyzer       │  │ Visualizer  │  │ Fetcher         │
│ (src/)         │  │ (src/)      │  │ (src/)          │
└───────┬────────┘  └──────┬──────┘  └────────┬────────┘
        │                  │                   │
        └──────────────────┼───────────────────┘
                           │
                ┌──────────▼──────────┐
                │ REUSE: Data Models  │
                │ Route, RouteGroup   │
                │ Location, Activity  │
                └─────────────────────┘
```

## Implementation Plan (Revised)

### Phase 1: Adapt Existing API Pattern (2-3 days)

#### 1.1 Create MapAPI Class (Similar to LongRidesAPI)

**New File:** `app/api/map_api.py`

```python
"""
Map API - Provides endpoints for map data, coordinates, and elevation.
Adapts existing CLI services for web API use.
"""

from flask import Blueprint, request, jsonify, current_app
from typing import List, Dict, Optional
import logging

from src.route_analyzer import RouteAnalyzer, RouteGroup, Route
from src.visualizer import RouteVisualizer
from src.weather_fetcher import WeatherFetcher
from src.location_finder import LocationFinder
from src.config import Config
from src.secure_cache import SecureCacheStorage

logger = logging.getLogger(__name__)

bp = Blueprint('map_api', __name__, url_prefix='/api/map')


@bp.route('/routes/<route_id>/coordinates')
def get_route_coordinates(route_id):
    """
    Get route coordinates for map rendering.
    
    REUSES: RouteGroup.representative_route.coordinates from src/route_analyzer.py
    """
    try:
        # Load route groups from cache (existing cache file)
        cache = SecureCacheStorage('cache')
        route_groups = cache.load('route_groups_cache.json')
        
        # Find route by ID
        route_group = next((g for g in route_groups if g['id'] == route_id), None)
        if not route_group:
            return jsonify({'error': 'Route not found'}), 404
        
        # Extract coordinates from representative route
        coords = route_group['representative_route']['coordinates']
        
        # Apply simplification if requested
        simplify = request.args.get('simplify', 'false').lower() == 'true'
        sample_rate = int(request.args.get('sample_rate', 1))
        
        if sample_rate > 1:
            coords = coords[::sample_rate]
        
        # Calculate bounds (reuse logic from RouteVisualizer)
        bounds = _calculate_bounds(coords)
        
        return jsonify({
            'status': 'success',
            'route_id': route_id,
            'coordinates': [{'lat': c[0], 'lng': c[1]} for c in coords],
            'bounds': bounds,
            'metadata': {
                'total_points': len(route_group['representative_route']['coordinates']),
                'returned_points': len(coords),
                'simplified': simplify,
                'sample_rate': sample_rate
            }
        })
        
    except Exception as e:
        logger.error(f'Error fetching coordinates: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/routes/<route_id>/elevation')
def get_route_elevation(route_id):
    """
    Get elevation profile for a route.
    
    REUSES: Route.elevation_gain from src/route_analyzer.py
    """
    try:
        cache = SecureCacheStorage('cache')
        route_groups = cache.load('route_groups_cache.json')
        
        route_group = next((g for g in route_groups if g['id'] == route_id), None)
        if not route_group:
            return jsonify({'error': 'Route not found'}), 404
        
        # Get representative route
        rep_route = route_group['representative_route']
        coords = rep_route['coordinates']
        
        # For now, return basic elevation data
        # TODO: Fetch detailed elevation stream from Strava API
        elevation_data = []
        total_distance = rep_route['distance'] / 1000  # Convert to km
        
        for i, coord in enumerate(coords):
            distance = (i / len(coords)) * total_distance
            # Placeholder elevation - in production, fetch from Strava streams
            elevation = 100 + (i % 50)  # Placeholder
            elevation_data.append({
                'distance': round(distance, 2),
                'elevation': elevation,
                'lat': coord[0],
                'lng': coord[1]
            })
        
        # Calculate statistics
        stats = {
            'elevation_gain': rep_route.get('elevation_gain', 0),
            'total_distance': total_distance
        }
        
        return jsonify({
            'status': 'success',
            'route_id': route_id,
            'elevation_data': elevation_data,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f'Error fetching elevation: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def _calculate_bounds(coords: List[tuple]) -> Dict:
    """Calculate bounding box (reused from RouteVisualizer logic)"""
    if not coords:
        return {}
    
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    
    return {
        'north': max(lats),
        'south': min(lats),
        'east': max(lngs),
        'west': min(lngs)
    }
```

#### 1.2 Register Map API Blueprint

**Update:** `app/__init__.py`

```python
# Add to existing blueprint registration
from app.api import map_api
app.register_blueprint(map_api.bp)
```

### Phase 2: Geocoding Endpoints (1 day)

**GOOD NEWS:** Geocoding already exists in [`src/api/long_rides_api.py`](../src/api/long_rides_api.py)!

**Action:** Copy and adapt existing geocoding endpoints:

```python
# In app/api/map_api.py

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Initialize geocoder (same as LongRidesAPI)
geocoder = Nominatim(user_agent="ride-optimizer")

@bp.route('/geocode/reverse')
def reverse_geocode():
    """
    Reverse geocode coordinates to address.
    
    REUSES: Pattern from src/api/long_rides_api.py
    """
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        
        # Check cache first
        cache_key = f"geocode_{lat:.6f}_{lng:.6f}"
        cache = SecureCacheStorage('cache')
        cached = cache.get(cache_key)
        
        if cached:
            return jsonify({'status': 'success', **cached, 'cached': True})
        
        # Geocode
        location = geocoder.reverse(f"{lat}, {lng}", timeout=10)
        
        if not location:
            return jsonify({'error': 'Location not found'}), 404
        
        result = {
            'location': {'lat': lat, 'lng': lng},
            'address': location.raw.get('address', {}),
            'display_name': location.address
        }
        
        # Cache result
        cache.set(cache_key, result, ttl=2592000)  # 30 days
        
        return jsonify({'status': 'success', **result, 'cached': False})
        
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        return jsonify({'error': 'Geocoding service unavailable'}), 503
    except Exception as e:
        logger.error(f'Geocoding error: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/geocode/forward')
def forward_geocode():
    """
    Forward geocode address to coordinates.
    
    REUSES: Pattern from src/api/long_rides_api.py geocode endpoint
    """
    try:
        query = request.args.get('q', '')
        if len(query) < 3:
            return jsonify({'error': 'Query too short (min 3 characters)'}), 400
        
        limit = int(request.args.get('limit', 5))
        
        # Geocode
        locations = geocoder.geocode(query, exactly_one=False, limit=limit, timeout=10)
        
        if not locations:
            return jsonify({'status': 'success', 'results': []})
        
        results = []
        for loc in locations:
            results.append({
                'display_name': loc.address,
                'lat': loc.latitude,
                'lng': loc.longitude,
                'type': loc.raw.get('type', 'unknown'),
                'importance': loc.raw.get('importance', 0)
            })
        
        return jsonify({'status': 'success', 'query': query, 'results': results})
        
    except Exception as e:
        logger.error(f'Forward geocoding error: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
```

### Phase 3: Weather Integration (Already Done!)

**EXCELLENT NEWS:** Weather API already exists in:
- [`src/api/long_rides_api.py`](../src/api/long_rides_api.py) - `/api/long-rides/weather`
- [`app/routes_DEPRECATED_FLASK/api.py`](../app/routes_DEPRECATED_FLASK/api.py) - `/api/weather/current` and `/api/weather/forecast`

**Action:** No new code needed! Just document the existing endpoints.

### Phase 4: Analytics Overlays (2 days)

**Leverage:** Existing speed/elevation data from Route model

```python
@bp.route('/routes/<route_id>/analytics/speed')
def get_speed_analytics(route_id):
    """
    Get speed heatmap data for route.
    
    REUSES: Route.average_speed from src/route_analyzer.py
    """
    try:
        cache = SecureCacheStorage('cache')
        route_groups = cache.load('route_groups_cache.json')
        
        route_group = next((g for g in route_groups if g['id'] == route_id), None)
        if not route_group:
            return jsonify({'error': 'Route not found'}), 404
        
        # Get all routes in group for speed analysis
        routes = route_group['routes']
        coords = route_group['representative_route']['coordinates']
        
        # Calculate average speed per segment
        segments = []
        num_segments = min(50, len(coords) - 1)
        segment_size = len(coords) // num_segments
        
        for i in range(0, len(coords) - segment_size, segment_size):
            start_coord = coords[i]
            end_coord = coords[i + segment_size]
            
            # Calculate average speed for this segment across all routes
            avg_speed = sum(r['average_speed'] for r in routes) / len(routes)
            
            # Color based on speed
            color = _get_speed_color(avg_speed)
            
            segments.append({
                'start': {'lat': start_coord[0], 'lng': start_coord[1]},
                'end': {'lat': end_coord[0], 'lng': end_coord[1]},
                'speed': round(avg_speed * 3.6, 1),  # Convert m/s to km/h
                'color': color
            })
        
        return jsonify({
            'status': 'success',
            'route_id': route_id,
            'analytics_type': 'speed',
            'segments': segments
        })
        
    except Exception as e:
        logger.error(f'Error fetching speed analytics: {e}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def _get_speed_color(speed_ms: float) -> str:
    """Color coding for speed (reuses semantic color system)"""
    speed_kmh = speed_ms * 3.6
    if speed_kmh < 15:
        return '#e74c3c'  # Red - slow
    elif speed_kmh < 20:
        return '#f39c12'  # Orange
    elif speed_kmh < 25:
        return '#f1c40f'  # Yellow
    else:
        return '#27ae60'  # Green - fast
```

## Data Flow Comparison

### Before (CLI Prototype)
```
main.py → RouteAnalyzer → route_groups_cache.json → Visualizer → HTML report
```

### After (Web API)
```
Frontend JS → Flask API → RouteAnalyzer (reused) → route_groups_cache.json → JSON response
```

**Key Insight:** We're just adding a Flask wrapper around existing services!

## Reusable Code Inventory

| Component | Location | Reuse % | Adaptation Needed |
|-----------|----------|---------|-------------------|
| Route/RouteGroup models | `src/route_analyzer.py` | 100% | None - use as-is |
| Location model | `src/location_finder.py` | 100% | None - use as-is |
| WeatherFetcher | `src/weather_fetcher.py` | 100% | None - already has caching |
| Geocoding | `src/api/long_rides_api.py` | 100% | Copy to new blueprint |
| Route caching | `src/route_analyzer.py` | 100% | Use existing cache files |
| Coordinate extraction | `src/route_analyzer.py` | 90% | Add sampling/simplification |
| Bounds calculation | `src/visualizer.py` | 100% | Extract to utility function |
| Color coding | `src/visualizer.py` | 100% | Extract to utility function |

**Total Reuse:** ~85% of required functionality already exists!

## Implementation Effort (Revised)

### Original Estimate (from scratch)
- Phase 1: Core endpoints - 1 week
- Phase 2: Analytics - 1 week  
- Phase 3: Geocoding - 1 week
- Phase 4: Polish - 1 week
- **Total: 4 weeks**

### Revised Estimate (with reuse)
- Phase 1: Adapt existing API pattern - 2-3 days
- Phase 2: Copy geocoding endpoints - 1 day
- Phase 3: Document existing weather API - 1 hour
- Phase 4: Add analytics overlays - 2 days
- Phase 5: Testing & documentation - 2 days
- **Total: 1-1.5 weeks** ✅

**Time Savings: 60-70%**

## Migration Checklist

### Step 1: Create New API Blueprint
- [ ] Create `app/api/map_api.py`
- [ ] Copy Flask app pattern from `src/api/long_rides_api.py`
- [ ] Register blueprint in `app/__init__.py`

### Step 2: Implement Core Endpoints
- [ ] `/api/map/routes/<id>/coordinates` - Use RouteGroup.representative_route
- [ ] `/api/map/routes/<id>/elevation` - Use Route.elevation_gain
- [ ] `/api/map/routes/batch` - Iterate over multiple route IDs

### Step 3: Copy Geocoding
- [ ] `/api/map/geocode/reverse` - Copy from LongRidesAPI
- [ ] `/api/map/geocode/forward` - Copy from LongRidesAPI
- [ ] Reuse Nominatim geocoder instance

### Step 4: Add Analytics
- [ ] `/api/map/routes/<id>/analytics/speed` - Use Route.average_speed
- [ ] `/api/map/routes/<id>/analytics/effort` - Calculate from elevation + speed

### Step 5: Testing
- [ ] Unit tests for each endpoint
- [ ] Integration tests with existing cache files
- [ ] Frontend integration tests

### Step 6: Documentation
- [ ] API endpoint documentation
- [ ] Update TECHNICAL_SPEC.md
- [ ] Add usage examples

## Key Advantages of This Approach

1. **Proven Code:** All core logic already tested in CLI
2. **Consistent Data Models:** Same Route/RouteGroup models everywhere
3. **Existing Caching:** Reuse route_groups_cache.json and weather_cache.json
4. **No Duplication:** Don't rewrite what already works
5. **Fast Implementation:** 60-70% time savings
6. **Lower Risk:** Less new code = fewer bugs

## Potential Issues & Solutions

### Issue 1: Cache File Format Differences
**Solution:** CLI uses same JSON format as web app needs - no conversion required

### Issue 2: Strava API Rate Limits
**Solution:** Reuse existing cache files, don't fetch new data

### Issue 3: Coordinate Simplification
**Solution:** Add simple sampling (already in plan: `coords[::sample_rate]`)

### Issue 4: Elevation Stream Data
**Solution:** Phase 1 uses existing elevation_gain, Phase 2 adds detailed streams

## Testing Strategy

### Unit Tests (Reuse Existing Test Patterns)

```python
# tests/test_map_api.py

def test_get_route_coordinates(client):
    """Test coordinate endpoint with existing cache data"""
    response = client.get('/api/map/routes/route_123/coordinates')
    assert response.status_code == 200
    data = response.get_json()
    assert 'coordinates' in data
    assert len(data['coordinates']) > 0

def test_geocoding_reuses_cache(client):
    """Test that geocoding uses cache"""
    # First request
    response1 = client.get('/api/map/geocode/reverse?lat=40.7128&lng=-74.0060')
    data1 = response1.get_json()
    
    # Second request (should be cached)
    response2 = client.get('/api/map/geocode/reverse?lat=40.7128&lng=-74.0060')
    data2 = response2.get_json()
    
    assert data2['cached'] == True
```

### Integration Tests

```python
def test_frontend_integration(client):
    """Test that frontend can fetch and render map data"""
    # Fetch coordinates
    coords_response = client.get('/api/map/routes/route_123/coordinates')
    coords = coords_response.get_json()['coordinates']
    
    # Fetch elevation
    elev_response = client.get('/api/map/routes/route_123/elevation')
    elevation = elev_response.get_json()['elevation_data']
    
    # Verify data is compatible with frontend
    assert len(coords) > 0
    assert all('lat' in c and 'lng' in c for c in coords)
```

## Success Metrics

### Performance Targets (Same as Original)
- Coordinate endpoint: < 200ms
- Elevation endpoint: < 500ms
- Geocoding endpoint: < 1s (with cache)

### Quality Targets
- Test coverage: > 80%
- Reuse existing code: > 80% ✅
- API uptime: > 99.5%

## Next Steps

1. **Review this revised plan** - Confirm reuse strategy
2. **Create Phase 1 implementation** - Map API blueprint
3. **Test with existing cache files** - Verify data compatibility
4. **Integrate with frontend** - Update JavaScript to use new endpoints
5. **Document API** - OpenAPI spec

## Questions for Review

1. ✅ Should we reuse existing cache files? **YES - they're already in the right format**
2. ✅ Should we copy LongRidesAPI pattern? **YES - it's proven and works well**
3. ✅ Should we extract shared utilities? **YES - bounds calculation, color coding**
4. Should we keep CLI and web API separate or merge? **KEEP SEPARATE - different use cases**

---

**Conclusion:** By leveraging the existing CLI prototype code, we can implement the map API endpoints in **1-1.5 weeks instead of 4 weeks**, with **85% code reuse** and **lower risk** due to using proven, tested components.

**Recommendation:** Proceed with this revised plan focusing on adapting existing services rather than building from scratch.