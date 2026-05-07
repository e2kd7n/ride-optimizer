# Test Coverage: route_analyzer.py (20% → 50%)

## Labels
`P1-high`, `testing`, `squad-2`, `test-coverage`

## Description
Improve test coverage for `src/route_analyzer.py` from 20% to 50% as part of the effort to reach 70% overall test coverage.

## Current Status
- **Current Coverage**: 20% (153/763 lines)
- **Target Coverage**: 50% (382 lines)
- **Lines to Cover**: +229 lines
- **Impact**: +3.4% to overall coverage

## Module Overview
`route_analyzer.py` is a **critical core module** that handles:
- Route grouping and similarity analysis
- Fréchet and Hausdorff distance calculations
- Route metrics calculation (duration, distance, elevation, consistency)
- Direction detection (home_to_work vs work_to_home)
- Route deduplication and outlier detection

## Testing Strategy

### Phase 1: Core Data Structures (Est: 50 lines)
Test the fundamental dataclasses and their methods:

```python
class TestRoute:
    - test_route_creation()
    - test_route_from_activity()
    - test_route_coordinates_decoding()
    - test_route_metrics_calculation()
    - test_route_equality()

class TestRouteGroup:
    - test_group_creation()
    - test_add_route_to_group()
    - test_representative_route_selection()
    - test_group_metrics_aggregation()
    - test_direction_assignment()

class TestRouteMetrics:
    - test_metrics_creation()
    - test_metrics_from_routes()
    - test_consistency_score_calculation()
```

### Phase 2: Similarity Calculations (Est: 80 lines)
Test the route similarity algorithms:

```python
class TestRouteSimilarity:
    - test_frechet_distance_identical_routes()
    - test_frechet_distance_similar_routes()
    - test_frechet_distance_different_routes()
    - test_hausdorff_distance_calculation()
    - test_similarity_threshold_matching()
    - test_outlier_detection_95th_percentile()
    - test_coordinate_normalization()
    - test_empty_route_handling()
```

### Phase 3: Route Grouping (Est: 60 lines)
Test the route grouping logic:

```python
class TestRouteGrouping:
    - test_group_similar_routes()
    - test_separate_dissimilar_routes()
    - test_direction_based_grouping()
    - test_parallel_processing()
    - test_incremental_grouping()
    - test_group_naming()
    - test_duplicate_detection()
```

### Phase 4: Route Analyzer Main Class (Est: 39 lines)
Test the RouteAnalyzer orchestration:

```python
class TestRouteAnalyzer:
    - test_analyzer_initialization()
    - test_analyze_routes_workflow()
    - test_filter_by_direction()
    - test_get_route_groups()
    - test_get_metrics_for_group()
    - test_error_handling()
```

## Implementation Checklist

### Setup
- [ ] Read existing test patterns in `tests/test_route_analyzer.py`
- [ ] Understand current test coverage gaps
- [ ] Set up test fixtures for routes and coordinates

### Core Tests
- [ ] Test Route dataclass and methods
- [ ] Test RouteGroup dataclass and methods
- [ ] Test RouteMetrics dataclass and methods

### Algorithm Tests
- [ ] Test Fréchet distance calculation
- [ ] Test Hausdorff distance calculation
- [ ] Test similarity threshold logic
- [ ] Test outlier detection (95th percentile)

### Integration Tests
- [ ] Test route grouping workflow
- [ ] Test direction detection
- [ ] Test parallel processing (1-8 workers)
- [ ] Test incremental analysis

### Edge Cases
- [ ] Test empty route lists
- [ ] Test single route
- [ ] Test routes with missing data
- [ ] Test routes with invalid coordinates
- [ ] Test very similar routes (edge of threshold)
- [ ] Test very different routes

### Verification
- [ ] Run tests: `pytest tests/test_route_analyzer.py -v`
- [ ] Check coverage: `pytest --cov=src/route_analyzer --cov-report=term-missing`
- [ ] Verify target: Coverage ≥ 50%
- [ ] Ensure all tests pass

## Test Data Requirements

### Sample Routes
```python
# Create realistic test routes with:
- Valid polyline encodings
- Realistic distances (5-50 km)
- Realistic durations (15-180 minutes)
- Realistic elevation gains (0-500 m)
- Start/end coordinates for direction detection
```

### Similarity Test Cases
```python
# Test route pairs with known similarity:
- Identical routes (100% similar)
- Nearly identical (95% similar)
- Similar with detours (70% similar)
- Different routes (30% similar)
- Completely different (<10% similar)
```

## Success Criteria
- [ ] Coverage increases from 20% to ≥50%
- [ ] All new tests pass
- [ ] No existing tests broken
- [ ] Tests follow established patterns
- [ ] Edge cases covered
- [ ] Integration tests included

## Dependencies
- Existing test file: `tests/test_route_analyzer.py`
- Module: `src/route_analyzer.py`
- Libraries: `similaritymeasures`, `numpy`, `polyline`

## Estimated Effort
- **Complexity**: High (complex algorithms)
- **Time**: 3-5 days
- **Lines of Test Code**: ~400-500 lines

## Related Issues
- Part of: Test Coverage Roadmap to 70%
- Blocks: Overall 70% coverage target
- Related: #XXX (long_ride_analyzer tests)

## Notes
- This is the **highest priority** module due to business criticality
- Route similarity algorithms are complex - focus on correctness
- Parallel processing tests may need special handling
- Consider using real Strava polylines for integration tests
- Document any discovered bugs or edge cases