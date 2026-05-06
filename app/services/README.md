## Service Layer Documentation

The service layer provides a clean separation between web routes and business logic. Services encapsulate core functionality and can be used by both web routes and CLI commands.

### Architecture Principles

1. **Stateless Services**: Services don't maintain request-specific state
2. **Dependency Injection**: Services receive dependencies via constructor
3. **DTO Pattern**: Services return Data Transfer Objects for web consumption
4. **Testability**: Services can be tested in isolation
5. **Reusability**: Same services used by web and CLI interfaces

### Available Services

#### AnalysisService
**Purpose**: Core route analysis and data processing

**Responsibilities**:
- Fetch activities from Strava
- Analyze and group routes
- Process long rides
- Manage data freshness and caching

**Key Methods**:
```python
run_full_analysis(force_refresh=False) -> Dict[str, Any]
get_analysis_status() -> Dict[str, Any]
get_route_groups() -> List[RouteGroup]
get_long_rides() -> List[LongRide]
get_activities() -> List[Activity]
get_locations() -> Tuple[Location, Location]
clear_cache()
```

**Usage Example**:
```python
from app.services import AnalysisService
from src.config import Config

config = Config('config/config.yaml')
service = AnalysisService(config)

# Run full analysis
result = service.run_full_analysis(force_refresh=True)
print(f"Found {result['route_groups_count']} route groups")

# Get route groups
route_groups = service.get_route_groups()
```

#### CommuteService
**Purpose**: Next commute recommendations

**Responsibilities**:
- Generate time-aware commute recommendations
- Weather-optimized route selection
- Alternative route suggestions
- Departure time optimization

**Key Methods**:
```python
initialize(route_groups, home_location, work_location, enable_weather=True)
get_next_commute(direction=None) -> Dict[str, Any]
get_all_commute_options(direction) -> Dict[str, Any]
get_departure_windows() -> Dict[str, Any]
```

**Usage Example**:
```python
from app.services import CommuteService

service = CommuteService(config)
service.initialize(route_groups, home, work)

# Get next commute recommendation
recommendation = service.get_next_commute()
print(f"Best route: {recommendation['route']['name']}")
print(f"Score: {recommendation['score']}")
```

#### PlannerService
**Purpose**: Long ride planning and recommendations

**Responsibilities**:
- Multi-day weather-optimized recommendations
- Route variety scoring
- Workout fit integration
- Map-based ride discovery

**Key Methods**:
```python
initialize(long_rides)
get_recommendations(forecast_days=7, min_distance=30, max_distance=100) -> Dict[str, Any]
get_rides_near_location(lat, lon, radius_miles=10) -> Dict[str, Any]
get_ride_details(ride_id) -> Dict[str, Any]
```

**Usage Example**:
```python
from app.services import PlannerService

service = PlannerService(config)
service.initialize(long_rides)

# Get 7-day recommendations
recommendations = service.get_recommendations(
    forecast_days=7,
    min_distance=30,
    max_distance=80
)

for day in recommendations['recommendations']:
    print(f"{day['day_name']}: {day['best_ride']['name']}")
```

#### RouteLibraryService
**Purpose**: Route browsing and management

**Responsibilities**:
- Browse all routes (commute + long rides)
- Search and filter capabilities
- Route statistics and details
- Route comparison
- Favorite management

**Key Methods**:
```python
initialize(route_groups, long_rides)
get_all_routes(route_type='all', sort_by='uses', limit=None) -> Dict[str, Any]
search_routes(query, limit=10) -> Dict[str, Any]
get_route_details(route_id, route_type) -> Dict[str, Any]
get_route_statistics() -> Dict[str, Any]
toggle_favorite(route_id, is_favorite) -> Dict[str, Any]
get_favorites() -> Dict[str, Any]
```

**Usage Example**:
```python
from app.services import RouteLibraryService

service = RouteLibraryService(config)
service.initialize(route_groups, long_rides)

# Get all routes sorted by usage
routes = service.get_all_routes(sort_by='uses', limit=10)
print(f"Found {routes['total_count']} routes")

# Search routes
results = service.search_routes('Harrison')
```

### Service Initialization Pattern

Services follow a two-step initialization pattern:

1. **Constructor**: Receives configuration and creates service instance
2. **Initialize**: Receives data dependencies (route groups, long rides, etc.)

This pattern allows services to be created early (e.g., at app startup) and initialized later when data is available.

```python
# Step 1: Create services at app startup
analysis_service = AnalysisService(config)
commute_service = CommuteService(config)
planner_service = PlannerService(config)
library_service = RouteLibraryService(config)

# Step 2: Initialize with data after analysis
result = analysis_service.run_full_analysis()
route_groups = analysis_service.get_route_groups()
long_rides = analysis_service.get_long_rides()
home, work = analysis_service.get_locations()

commute_service.initialize(route_groups, home, work)
planner_service.initialize(long_rides)
library_service.initialize(route_groups, long_rides)
```

### Integration with Flask Routes

Services are designed to be used directly in Flask route handlers:

```python
from flask import Blueprint, jsonify
from app.services import CommuteService

bp = Blueprint('commute', __name__)

@bp.route('/api/commute/next')
def get_next_commute():
    # Service is injected or accessed from app context
    service = current_app.commute_service
    
    # Call service method
    recommendation = service.get_next_commute()
    
    # Return JSON response
    return jsonify(recommendation)
```

### Error Handling

Services return dictionaries with a `status` field:
- `'success'`: Operation completed successfully
- `'error'`: Operation failed, check `message` field

```python
result = service.get_next_commute()

if result['status'] == 'error':
    return jsonify(result), 500
else:
    return jsonify(result), 200
```

### Testing Services

Services are designed for easy testing:

```python
import pytest
from app.services import CommuteService
from src.config import Config

def test_commute_service():
    config = Config('config/config_test.yaml')
    service = CommuteService(config)
    
    # Mock data
    route_groups = [...]
    home = Location(...)
    work = Location(...)
    
    service.initialize(route_groups, home, work)
    
    result = service.get_next_commute()
    assert result['status'] == 'success'
    assert 'route' in result
```

### Future Enhancements

1. **Caching**: Add Redis/Memcached for service-level caching
2. **Async Support**: Convert to async/await for better performance
3. **Event System**: Emit events for service actions (analysis complete, etc.)
4. **Metrics**: Add Prometheus metrics for service calls
5. **Rate Limiting**: Add rate limiting for expensive operations

### Service Dependencies

```
AnalysisService
├── DataFetcher (Strava API)
├── LocationFinder
├── RouteAnalyzer
└── LongRideAnalyzer

CommuteService
├── NextCommuteRecommender
├── WeatherFetcher
└── WindImpactCalculator

PlannerService
├── LongRideAnalyzer
└── WeatherFetcher

RouteLibraryService
└── (No external dependencies)
```

### Performance Considerations

1. **Analysis Service**: Most expensive operation, cache results
2. **Weather Fetching**: Rate-limited by API, cache forecasts
3. **Route Grouping**: CPU-intensive, use background jobs
4. **Geocoding**: Rate-limited, use background processing

### Best Practices

1. Always check service initialization before calling methods
2. Handle errors gracefully and return meaningful messages
3. Use type hints for better IDE support
4. Document return value structures
5. Keep services focused on single responsibility
6. Avoid circular dependencies between services
7. Use dependency injection for testability