# Test Fixtures

Realistic, PII-free test data for integration testing. All coordinates use the Chicago metro area.

## Files

| File | Description | Records |
|------|-------------|---------|
| `activities.json` | Strava activities (commutes, long rides, edge cases) | 22 |
| `route_groups.json` | Pre-analyzed route groupings with representative routes | 3 groups |
| `weather.json` | Current conditions + 7-day forecast + hourly forecast | 1 + 7 + 6 |
| `sample_weather.json` | Simplified weather (current + daily forecast) | 1 + 7 |
| `workouts.json` | TrainerRoad workout calendar | 10 |
| `sample_route_groups.json` | Minimal route groups for quick tests | 2 groups |
| `sample_recommendations.json` | Long ride recommendations with scoring | 3 |

## Loading Fixtures

```python
from tests.fixtures import load_activities, load_route_groups, load_weather, load_workouts
from tests.fixtures import make_activity, make_activities, make_route, make_route_group, make_route_groups

# Raw JSON dicts
activities = load_activities()
groups = load_route_groups()
weather = load_weather()

# Typed dataclass instances
activity = make_activity()                          # first fixture as Activity
activity = make_activity({"distance": 99000.0})     # with overrides
activities = make_activities(n=5)                    # first 5 as Activity list
route_groups = make_route_groups()                   # all groups as RouteGroup list
```

## Activity Types

The activities fixture covers:
- **Commutes** (IDs 10000001–10000010): morning/evening rides, ~12 km
- **Long rides** (IDs 10000011–10000016): 45–160 km, various terrain
- **Edge cases** (IDs 10000017–10000022): short ride, no GPS, virtual ride, gravel, MTB, incomplete data

## Coordinate System

All fixtures use Chicago-area coordinates:
- Home: `(41.8800, -87.6300)`
- Work: `(41.8900, -87.6200)`
- Long ride areas: suburban Chicago and surrounding region
