# Test Coverage: long_ride_analyzer.py (13% → 50%)

## Labels
`P1-high`, `testing`, `squad-2`, `test-coverage`

## Description
Improve test coverage for `src/long_ride_analyzer.py` from 13% to 50% as part of the effort to reach 70% overall test coverage.

## Current Status
- **Current Coverage**: 13% (54/409 lines)
- **Target Coverage**: 50% (205 lines)
- **Lines to Cover**: +151 lines
- **Impact**: +2.2% to overall coverage

## Module Overview
`long_ride_analyzer.py` handles **long ride recommendations** and analysis:
- Identifies suitable long ride routes (>30km)
- Analyzes weather conditions for multi-hour rides
- Calculates optimal departure times
- Provides route recommendations based on distance, elevation, and weather
- Generates detailed ride reports with weather forecasts

## Testing Strategy

### Phase 1: Core Data Structures (Est: 30 lines)
Test the fundamental dataclasses:

```python
class TestLongRideRecommendation:
    - test_recommendation_creation()
    - test_recommendation_from_route_group()
    - test_weather_integration()
    - test_optimal_time_calculation()
    - test_recommendation_scoring()

class TestWeatherWindow:
    - test_weather_window_creation()
    - test_window_averaging()
    - test_favorability_calculation()
```

### Phase 2: Route Filtering (Est: 40 lines)
Test route selection logic:

```python
class TestLongRideFiltering:
    - test_filter_by_distance_min()
    - test_filter_by_distance_max()
    - test_filter_by_elevation()
    - test_filter_by_direction()
    - test_exclude_commute_routes()
    - test_filter_by_recent_usage()
    - test_combined_filters()
```

### Phase 3: Weather Analysis (Est: 50 lines)
Test weather-based recommendations:

```python
class TestWeatherAnalysis:
    - test_get_hourly_forecast()
    - test_calculate_weather_windows()
    - test_find_optimal_departure_time()
    - test_wind_impact_analysis()
    - test_precipitation_probability()
    - test_temperature_suitability()
    - test_multi_hour_forecast_aggregation()
```

### Phase 4: Recommendation Engine (Est: 31 lines)
Test the main recommendation logic:

```python
class TestLongRideAnalyzer:
    - test_analyzer_initialization()
    - test_get_recommendations_for_date()
    - test_get_recommendations_for_date_range()
    - test_rank_routes_by_score()
    - test_generate_ride_report()
    - test_error_handling()
    - test_no_suitable_routes()
```

## Implementation Checklist

### Setup
- [ ] Read existing test patterns
- [ ] Understand long ride criteria (distance, elevation, etc.)
- [ ] Set up test fixtures for long ride routes
- [ ] Mock weather forecast data

### Core Tests
- [ ] Test LongRideRecommendation dataclass
- [ ] Test WeatherWindow dataclass
- [ ] Test route filtering logic

### Weather Integration
- [ ] Test hourly forecast retrieval
- [ ] Test weather window calculations
- [ ] Test optimal departure time finding
- [ ] Test wind impact for long rides
- [ ] Test multi-hour weather aggregation

### Recommendation Logic
- [ ] Test route scoring algorithm
- [ ] Test route ranking
- [ ] Test recommendation generation
- [ ] Test report generation

### Edge Cases
- [ ] Test no suitable routes
- [ ] Test weather API failures
- [ ] Test routes at distance boundaries
- [ ] Test extreme weather conditions
- [ ] Test missing weather data
- [ ] Test date range edge cases

### Verification
- [ ] Run tests: `pytest tests/test_long_ride_analyzer.py -v`
- [ ] Check coverage: `pytest --cov=src/long_ride_analyzer --cov-report=term-missing`
- [ ] Verify target: Coverage ≥ 50%
- [ ] Ensure all tests pass

## Test Data Requirements

### Sample Long Ride Routes
```python
# Create test routes with:
- Distances: 30-150 km
- Durations: 1.5-6 hours
- Elevation gains: 200-2000 m
- Various directions and start locations
- Mix of flat and hilly routes
```

### Weather Scenarios
```python
# Test with various weather conditions:
- Perfect conditions (mild temp, light wind, no rain)
- Hot conditions (>30°C)
- Cold conditions (<5°C)
- Windy conditions (>25 kph)
- Rainy conditions (>50% precipitation)
- Mixed conditions throughout the day
```

## Success Criteria
- [ ] Coverage increases from 13% to ≥50%
- [ ] All new tests pass
- [ ] No existing tests broken
- [ ] Tests follow established patterns
- [ ] Weather integration tested
- [ ] Edge cases covered

## Dependencies
- Module: `src/long_ride_analyzer.py`
- Related: `src/route_analyzer.py` (route groups)
- Related: `src/weather_fetcher.py` (weather data)
- Related: `src/optimizer.py` (scoring logic)

## Estimated Effort
- **Complexity**: High (weather integration, complex logic)
- **Time**: 2-4 days
- **Lines of Test Code**: ~300-400 lines

## Related Issues
- Part of: Test Coverage Roadmap to 70%
- Depends on: #XXX (route_analyzer tests)
- Related: #XXX (weather_service tests - already complete)

## Notes
- Long ride feature is important for user engagement
- Weather forecasting is critical for multi-hour rides
- Test with realistic weather patterns
- Consider seasonal variations in testing
- Document any discovered edge cases in weather analysis