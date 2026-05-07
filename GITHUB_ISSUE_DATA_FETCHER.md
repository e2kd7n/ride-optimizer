# Test Coverage: data_fetcher.py (49% → 80%)

## Labels
`P1-high`, `testing`, `squad-2`, `test-coverage`

## Description
Improve test coverage for `src/data_fetcher.py` from 49% to 80% as part of the effort to reach 70% overall test coverage.

## Current Status
- **Current Coverage**: 49% (132/271 lines)
- **Target Coverage**: 80% (217 lines)
- **Lines to Cover**: +85 lines
- **Impact**: +1.3% to overall coverage

## Module Overview
`data_fetcher.py` handles **Strava API integration** and data caching:
- Fetches activities from Strava API
- Caches activity data to reduce API calls
- Converts Strava activity objects to internal Activity dataclass
- Handles polyline encoding/decoding
- Manages cache validation and expiration
- Filters activities by date range

## Testing Strategy

### Phase 1: Activity Dataclass (Est: 25 lines)
Expand tests for Activity dataclass:

```python
class TestActivity:
    # Existing tests (keep)
    - test_activity_creation()
    - test_from_strava_activity()
    - test_from_dict()
    
    # New tests needed
    - test_to_dict()
    - test_from_strava_with_sport_type()
    - test_from_strava_with_detailed_polyline()
    - test_from_strava_missing_fields()
    - test_time_conversion_timedelta()
    - test_time_conversion_duration_object()
    - test_nested_latlng_extraction()
    - test_invalid_latlng_handling()
```

### Phase 2: Cache Management (Est: 30 lines)
Test cache operations:

```python
class TestCacheManagement:
    - test_is_cache_valid_fresh()
    - test_is_cache_valid_expired()
    - test_is_cache_valid_missing()
    - test_load_cached_activities()
    - test_save_cached_activities()
    - test_cache_age_calculation()
    - test_test_cache_vs_production_cache()
    - test_cache_path_creation()
```

### Phase 3: Activity Fetching (Est: 30 lines)
Test API interaction:

```python
class TestActivityFetching:
    - test_fetch_activities_no_filters()
    - test_fetch_activities_with_limit()
    - test_fetch_activities_with_after_date()
    - test_fetch_activities_with_before_date()
    - test_fetch_activities_date_range()
    - test_fetch_with_cache_enabled()
    - test_fetch_with_cache_disabled()
    - test_fetch_api_error_handling()
    - test_fetch_progress_reporting()
```

### Phase 4: Activity Details & Filtering (Est: 0 lines - already tested)
Verify existing tests cover:

```python
class TestStravaDataFetcher:
    # Existing tests (verify coverage)
    - test_fetcher_initialization()
    - test_decode_polyline()
    - test_filter_commute_activities()
    - test_get_activity_details()
```

## Implementation Checklist

### Setup
- [ ] Review existing tests in `tests/test_data_fetcher.py`
- [ ] Identify coverage gaps from coverage report
- [ ] Set up mock Strava client responses
- [ ] Create test cache files

### Activity Dataclass Tests
- [ ] Test all conversion methods (to_dict, from_dict, from_strava)
- [ ] Test handling of optional fields
- [ ] Test sport_type vs type field handling
- [ ] Test polyline selection (detailed vs summary)
- [ ] Test time conversion edge cases
- [ ] Test latlng extraction from nested structures

### Cache Tests
- [ ] Test cache validation logic
- [ ] Test cache loading and saving
- [ ] Test cache expiration
- [ ] Test separate test/production caches
- [ ] Test cache directory creation

### API Integration Tests
- [ ] Test fetch with various parameters
- [ ] Test cache hit/miss scenarios
- [ ] Test date filtering
- [ ] Test API error handling
- [ ] Test activity processing errors
- [ ] Test progress reporting

### Edge Cases
- [ ] Test empty activity list
- [ ] Test activities with missing data
- [ ] Test invalid polylines
- [ ] Test timezone handling in dates
- [ ] Test cache corruption
- [ ] Test API rate limiting

### Verification
- [ ] Run tests: `pytest tests/test_data_fetcher.py -v`
- [ ] Check coverage: `pytest --cov=src/data_fetcher --cov-report=term-missing`
- [ ] Verify target: Coverage ≥ 80%
- [ ] Ensure all tests pass

## Test Data Requirements

### Mock Strava Activities
```python
# Create mock activities with:
- Various activity types (Ride, Run, VirtualRide)
- Various sport types (GravelRide, MountainBikeRide, etc.)
- Complete and incomplete data
- Different polyline formats
- Different time formats (timedelta, Duration, int)
- Nested and flat latlng structures
```

### Cache Scenarios
```python
# Test cache states:
- Fresh cache (< 2 hours old)
- Stale cache (> 7 days old)
- Missing cache
- Corrupted cache
- Empty cache
```

## Success Criteria
- [ ] Coverage increases from 49% to ≥80%
- [ ] All new tests pass
- [ ] No existing tests broken
- [ ] Tests follow established patterns
- [ ] API mocking is realistic
- [ ] Cache behavior is well-tested

## Dependencies
- Existing test file: `tests/test_data_fetcher.py`
- Module: `src/data_fetcher.py`
- Libraries: `stravalib`, `polyline`
- Related: Strava API authentication

## Estimated Effort
- **Complexity**: Medium (API mocking, cache logic)
- **Time**: 1-2 days
- **Lines of Test Code**: ~200-250 lines

## Related Issues
- Part of: Test Coverage Roadmap to 70%
- Related: #XXX (route_analyzer tests)
- Blocks: Overall 70% coverage target

## Notes
- This module is **already 49% covered** - easier to complete
- Focus on uncovered branches and error paths
- Mock Strava API responses realistically
- Test both test and production cache paths
- Document any Strava API quirks discovered
- Consider adding integration tests with real API (optional)