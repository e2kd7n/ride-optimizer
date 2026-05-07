# Test Coverage: route_namer.py (15% → 50%)

## Labels
`P2-medium`, `testing`, `squad-2`, `test-coverage`

## Description
Improve test coverage for `src/route_namer.py` from 15% to 50% as part of the effort to reach 70% overall test coverage.

## Current Status
- **Current Coverage**: 15% (57/377 lines)
- **Target Coverage**: 50% (189 lines)
- **Lines to Cover**: +132 lines
- **Impact**: +2.0% to overall coverage

## Module Overview
`route_namer.py` handles **intelligent route naming**:
- Generates human-readable route names from coordinates
- Uses reverse geocoding (Nominatim API)
- Samples points along route for naming
- Caches geocoding results
- Handles rate limiting
- Formats names based on landmarks and locations

## Testing Strategy

### Phase 1: Coordinate Sampling (Est: 30 lines)
Test route point selection:

```python
class TestCoordinateSampling:
    - test_sample_route_points_default()
    - test_sample_route_points_custom_count()
    - test_sample_route_points_short_route()
    - test_sample_route_points_long_route()
    - test_sample_route_points_single_point()
    - test_sample_route_points_empty()
```

### Phase 2: Geocoding (Est: 40 lines)
Test reverse geocoding functionality:

```python
class TestGeocoding:
    - test_reverse_geocode_success()
    - test_reverse_geocode_cache_hit()
    - test_reverse_geocode_cache_miss()
    - test_reverse_geocode_rate_limiting()
    - test_reverse_geocode_api_error()
    - test_reverse_geocode_invalid_coordinates()
    - test_geocoding_cache_storage()
    - test_geocoding_cache_loading()
```

### Phase 3: Name Generation (Est: 40 lines)
Test name formatting logic:

```python
class TestNameGeneration:
    - test_generate_name_from_landmarks()
    - test_generate_name_from_neighborhoods()
    - test_generate_name_from_cities()
    - test_generate_name_fallback()
    - test_generate_name_deduplication()
    - test_generate_name_formatting()
    - test_generate_name_max_length()
    - test_generate_name_special_characters()
```

### Phase 4: Route Namer Main Class (Est: 22 lines)
Test the RouteNamer orchestration:

```python
class TestRouteNamer:
    - test_namer_initialization()
    - test_name_route_workflow()
    - test_name_multiple_routes()
    - test_error_handling()
    - test_cache_management()
```

## Implementation Checklist

### Setup
- [ ] Review existing route naming code
- [ ] Understand Nominatim API requirements
- [ ] Set up mock geocoding responses
- [ ] Create test cache files

### Coordinate Tests
- [ ] Test point sampling algorithms
- [ ] Test various route lengths
- [ ] Test edge cases (empty, single point)

### Geocoding Tests
- [ ] Test successful geocoding
- [ ] Test cache hit/miss scenarios
- [ ] Test rate limiting (1 req/sec)
- [ ] Test API errors
- [ ] Test invalid coordinates
- [ ] Test cache persistence

### Name Generation Tests
- [ ] Test name extraction from geocoding results
- [ ] Test name formatting
- [ ] Test deduplication
- [ ] Test fallback naming
- [ ] Test length limits
- [ ] Test special character handling

### Integration Tests
- [ ] Test end-to-end route naming
- [ ] Test batch route naming
- [ ] Test cache warming
- [ ] Test error recovery

### Edge Cases
- [ ] Test routes with no geocoding results
- [ ] Test routes in remote areas
- [ ] Test routes crossing boundaries
- [ ] Test very short routes
- [ ] Test very long routes
- [ ] Test API timeout

### Verification
- [ ] Run tests: `pytest tests/test_route_namer.py -v`
- [ ] Check coverage: `pytest --cov=src/route_namer --cov-report=term-missing`
- [ ] Verify target: Coverage ≥ 50%
- [ ] Ensure all tests pass

## Test Data Requirements

### Sample Routes
```python
# Create test routes with:
- Various lengths (short, medium, long)
- Different locations (urban, suburban, rural)
- Known landmarks
- Boundary crossings
```

### Mock Geocoding Responses
```python
# Mock Nominatim responses with:
- Complete address data
- Partial address data
- Missing data
- Various location types (road, neighborhood, city)
```

## Success Criteria
- [ ] Coverage increases from 15% to ≥50%
- [ ] All new tests pass
- [ ] No existing tests broken
- [ ] Tests follow established patterns
- [ ] Geocoding mocked properly
- [ ] Rate limiting tested

## Dependencies
- Module: `src/route_namer.py`
- API: Nominatim (OpenStreetMap)
- Related: `src/route_analyzer.py` (route coordinates)
- Cache: Geocoding cache file

## Estimated Effort
- **Complexity**: Medium (API integration, caching)
- **Time**: 2-3 days
- **Lines of Test Code**: ~250-300 lines

## Related Issues
- Part of: Test Coverage Roadmap to 70%
- Related: #XXX (route_analyzer tests)
- Blocks: Overall 70% coverage target

## Notes
- Nominatim has rate limiting (1 req/sec) - mock carefully
- Cache is critical for performance - test thoroughly
- Name generation logic may have edge cases
- Consider testing with real geocoding data (optional)
- Document any Nominatim API quirks
- User-Agent header is required for Nominatim