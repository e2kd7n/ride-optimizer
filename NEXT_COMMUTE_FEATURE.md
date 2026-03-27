# Time-Aware Next Commute Recommendations

## Overview

The Ride Optimizer now provides **time-aware next commute recommendations** that show you which route to take for your upcoming commutes based on the current time and forecast weather conditions.

## Feature Description

Instead of showing a single "optimal route" based on current weather, the system now displays **two separate recommendations**:

1. **Next Commute to Work** - Best route for your next morning commute
2. **Next Commute Home** - Best route for your next evening commute

Each recommendation includes:
- Route name and score
- Time window (e.g., "Today 7-9 AM" or "Tomorrow 3-6 PM")
- Duration and distance metrics
- **Forecast weather conditions** for that specific time window
- Wind favorability assessment

## Time-Based Logic

The system intelligently determines which commutes to show based on the current time:

### Morning (Before 10 AM)
- **To Work**: Today's morning commute (7-9 AM)
- **To Home**: Today's evening commute (3-6 PM)

### Midday (10 AM - 6 PM)
- **To Work**: Tomorrow's morning commute (7-9 AM)
- **To Home**: Today's evening commute (3-6 PM)

### Evening (After 6 PM)
- **To Work**: Tomorrow's morning commute (7-9 AM)
- **To Home**: Tomorrow's evening commute (3-6 PM)

## Technical Implementation

### New Module: `src/next_commute_recommender.py`

The `NextCommuteRecommender` class provides:

1. **Time Detection** - Determines which commutes are relevant based on current time
2. **Forecast Weather Fetching** - Gets hourly forecast for specific time windows
3. **Route Scoring** - Scores routes using forecast conditions instead of current weather
4. **Recommendation Generation** - Creates time-aware recommendations for both directions

### Key Components

#### CommuteRecommendation Dataclass
```python
@dataclass
class CommuteRecommendation:
    direction: str              # "to_work" or "to_home"
    time_window: str           # e.g., "Today 7-9 AM"
    route_group: RouteGroup    # Best route for this commute
    score: float               # Route score (0-100)
    breakdown: Dict            # Score breakdown
    forecast_weather: Dict     # Forecast weather for time window
    is_today: bool            # Whether this is for today
    window_start: time        # Start of commute window
    window_end: time          # End of commute window
```

#### Weather Forecast Integration

The system fetches hourly weather forecasts and averages conditions within the commute time window:
- **Morning window**: 7:00 AM - 9:00 AM
- **Evening window**: 3:00 PM - 6:00 PM

Forecast data includes:
- Temperature
- Wind speed and direction
- Precipitation probability
- Wind impact analysis (headwind/tailwind/crosswind)

### Integration Points

1. **main.py** - Generates next commute recommendations during analysis
2. **report_generator.py** - Passes recommendations to template context
3. **report_template.html** - Displays two recommendation cards with forecast weather

## User Benefits

### Actionable Recommendations
Users know exactly which route to take for their **next** commute, not just a generic "best route."

### Proactive Planning
Shows tomorrow's conditions when today's commute is done, allowing advance planning.

### Weather-Aware
Uses **forecast** weather instead of current conditions, providing more relevant information.

### Time-Appropriate
Recommendations match actual commute times (morning vs. evening).

## Configuration

Commute time windows can be configured in the `NextCommuteRecommender` class:

```python
self.morning_window_start = time(7, 0)   # 7:00 AM
self.morning_window_end = time(9, 0)     # 9:00 AM
self.evening_window_start = time(15, 0)  # 3:00 PM
self.evening_window_end = time(18, 0)    # 6:00 PM
```

## Testing

Run the test script to verify time detection logic:

```bash
python3 scripts/test_next_commute.py
```

This will show which commutes are recommended at different times of day.

## Example Output

### Morning (8:00 AM)
```
🌅 Next Commute to Work
Today 7-9 AM
Route: Main Street Route
Score: 87.5/100
Duration: 23 min | Distance: 5.2 mi
Forecast: 65°F, 8 mph wind, 10% precip, Favorable wind
```

```
🌆 Next Commute Home
Today 3-6 PM
Route: Lakefront Route
Score: 82.3/100
Duration: 25 min | Distance: 5.5 mi
Forecast: 72°F, 12 mph wind, 20% precip, Neutral wind
```

### Evening (7:00 PM)
```
🌅 Next Commute to Work
Tomorrow 7-9 AM
Route: Main Street Route
Score: 91.2/100
Duration: 23 min | Distance: 5.2 mi
Forecast: 58°F, 5 mph wind, 5% precip, Favorable wind
```

```
🌆 Next Commute Home
Tomorrow 3-6 PM
Route: Lakefront Route
Score: 78.5/100
Duration: 25 min | Distance: 5.5 mi
Forecast: 68°F, 15 mph wind, 30% precip, Unfavorable wind
```

## Future Enhancements

Potential improvements for future versions:

1. **Configurable Time Windows** - Allow users to set their own commute times
2. **Weekend Detection** - Different logic for weekends
3. **Holiday Awareness** - Skip work commutes on holidays
4. **Multi-Day Forecast** - Show recommendations for next 3-5 days
5. **Push Notifications** - Alert users to significant weather changes
6. **Route Comparison** - Show alternative routes with different weather impacts

## Related Issues

- GitHub Issue #58 - Show time-aware next commute recommendations (to work & to home)

## Implementation Date

March 27, 2026

---

*Made with Bob*