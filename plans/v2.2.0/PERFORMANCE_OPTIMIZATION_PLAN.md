# Performance Optimization Plan

## Performance Analysis Summary

**Total Runtime**: 16.785 seconds  
**Total Function Calls**: 28,402,375 (28,210,614 primitive calls)  
**Analysis Date**: Based on `output/profile_stats.txt`

## Top Performance Bottlenecks

### 1. Weather/Wind Analysis - 8.3 seconds (49% of runtime)

**Primary Culprit**: `_fetch_weather_data()` and wind impact calculations

#### Breakdown:
- **Weather data fetching**: 8.313s total
  - `RouteOptimizer.__init__()` → `_fetch_weather_data()`: 8.319s
  - HTTP requests to weather API: 2.850s (9 requests)
  - Network I/O (SSL, DNS): ~2.8s
  
- **Wind impact analysis**: 5.964s total (201 calls)
  - `analyze_route_wind_impact()`: 5.964s
  - Geopy distance calculations: 5.797s (75,973 calls)
  - Geographic calculations dominate this time

#### Root Cause:
```python
# src/weather_fetcher.py:496
def analyze_route_wind_impact(self, route_coords, wind_speed_kph, wind_direction):
    # Called 201 times
    # Each call performs 75,973 distance calculations
    # Uses geopy.distance.geodesic() which is expensive
```

#### Optimization Strategies:

**A. Cache Wind Analysis Results** (High Impact - Est. 5s savings)
```python
# Add to weather_fetcher.py
@lru_cache(maxsize=1000)
def _cached_wind_analysis(self, route_hash, wind_speed, wind_direction):
    """Cache wind analysis by route geometry hash"""
    pass
```

**B. Reduce Distance Calculation Frequency** (Medium Impact - Est. 2s savings)
- Sample route coordinates instead of analyzing every point
- Use every Nth coordinate (e.g., every 10th point)
- Maintain accuracy while reducing calculations by 90%

**C. Batch Weather API Requests** (Low Impact - Est. 0.5s savings)
- Current: 9 sequential requests
- Proposed: Batch requests where possible
- Use async/await for parallel requests

**D. Simplify Distance Calculations** (Medium Impact - Est. 1.5s savings)
- Replace `geopy.distance.geodesic()` with faster haversine formula
- Acceptable for wind analysis (doesn't need geodesic precision)
- 10-20x faster for this use case

### 2. Browser Opening - 6.1 seconds (36% of runtime)

**Issue**: `webbrowser.open_new_tab()` blocks for 6.085s

#### Breakdown:
```
_open_report_in_browser: 6.096s
  └─ webbrowser.open_new_tab: 6.094s
      └─ subprocess.wait: 6.085s
          └─ posix.waitpid: 6.085s (blocking)
```

#### Root Cause:
The browser opening process waits synchronously for the browser to launch.

#### Optimization Strategy:

**Make Browser Opening Non-Blocking** (High Impact - Est. 6s savings)
```python
# main.py:525
def _open_report_in_browser(report_path: Path) -> None:
    """Open report in browser without blocking."""
    import subprocess
    import sys
    
    if sys.platform == 'darwin':  # macOS
        subprocess.Popen(['open', str(report_path)])
    elif sys.platform == 'win32':  # Windows
        subprocess.Popen(['start', str(report_path)], shell=True)
    else:  # Linux
        subprocess.Popen(['xdg-open', str(report_path)])
    
    # Don't wait - return immediately
```

### 3. HTTP/Network Operations - 2.8 seconds (17% of runtime)

#### Breakdown:
- SSL handshakes: 1.134s (2 connections)
- DNS lookups: 0.228s (2 lookups)
- HTTP response reading: 1.693s
- Connection establishment: 0.740s

#### Optimization Strategies:

**A. Connection Pooling** (Low Impact - Est. 0.3s savings)
- Reuse HTTP connections across requests
- Already using `requests.Session()` - verify it's being used consistently

**B. Reduce API Calls** (Medium Impact - Est. 1s savings)
- Cache weather data more aggressively
- Batch route weather requests
- Use weather cache from previous runs when appropriate

### 4. Visualization Generation - 0.5 seconds (3% of runtime)

#### Breakdown:
- `generate_map()`: 0.500s
- Folium rendering: 0.272s
- Route layer additions: 0.129s (201 calls)

#### Status: **Acceptable Performance**
This is reasonable for generating interactive maps. No optimization needed unless it becomes a bottleneck.

### 5. Route Analysis - 0.2 seconds (1% of runtime)

#### Breakdown:
- `group_similar_routes()`: 0.176s
- `extract_routes()`: 0.170s
- Route grouping cache loading: 0.039s

#### Status: **Excellent Performance**
Route analysis is already well-optimized with caching. No changes needed.

## Performance Optimization Priority

### Priority 1: High Impact, Low Effort

1. **Make browser opening non-blocking** 
   - Impact: -6s (36% improvement)
   - Effort: 10 minutes
   - Risk: Very low
   - File: `main.py:525`

2. **Cache wind analysis results**
   - Impact: -5s (30% improvement)
   - Effort: 30 minutes
   - Risk: Low
   - File: `src/weather_fetcher.py`

### Priority 2: Medium Impact, Medium Effort

3. **Sample route coordinates for wind analysis**
   - Impact: -2s (12% improvement)
   - Effort: 1 hour
   - Risk: Medium (need to validate accuracy)
   - File: `src/weather_fetcher.py:496`

4. **Replace geodesic with haversine for wind calculations**
   - Impact: -1.5s (9% improvement)
   - Effort: 2 hours
   - Risk: Low (wind analysis doesn't need geodesic precision)
   - File: `src/weather_fetcher.py`

### Priority 3: Low Impact, High Effort

5. **Batch weather API requests**
   - Impact: -0.5s (3% improvement)
   - Effort: 3 hours
   - Risk: Medium (API changes, error handling)
   - File: `src/weather_fetcher.py`

## Implementation Plan

### Phase 1: Quick Wins (Est. 11s improvement, 65% faster)

**Week 1**:
- [ ] Implement non-blocking browser opening
- [ ] Add wind analysis caching with LRU cache
- [ ] Test and validate changes

**Expected Result**: Runtime reduced from 16.8s to ~5.8s

### Phase 2: Medium Optimizations (Est. 3.5s improvement)

**Week 2**:
- [ ] Implement coordinate sampling for wind analysis
- [ ] Replace geodesic with haversine for wind calculations
- [ ] Add configuration option for sampling rate
- [ ] Validate accuracy of wind analysis with sampling

**Expected Result**: Runtime reduced from 5.8s to ~2.3s

### Phase 3: Advanced Optimizations (Est. 0.5s improvement)

**Future**:
- [ ] Implement async weather API requests
- [ ] Add request batching
- [ ] Optimize connection pooling

**Expected Result**: Runtime reduced from 2.3s to ~1.8s

## Measurement Strategy

### Before Each Change:
```bash
python3 scripts/profile_analysis.py --analyze
```

### After Each Change:
1. Run profiling again
2. Compare results
3. Document actual vs. expected improvement
4. Verify functionality still works correctly

### Key Metrics to Track:
- Total runtime
- Weather fetching time
- Wind analysis time
- Browser opening time
- Number of distance calculations
- API request count

## Risk Mitigation

### For Wind Analysis Changes:
1. **Validation**: Compare results with/without optimization
2. **Accuracy Threshold**: Ensure wind impact scores differ by <5%
3. **Fallback**: Keep original implementation as option
4. **Testing**: Add unit tests for wind calculations

### For Browser Opening:
1. **Cross-platform Testing**: Test on macOS, Windows, Linux
2. **Error Handling**: Graceful fallback if browser fails to open
3. **User Feedback**: Log when browser opening fails

## Expected Final Performance

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|---------------|
| Total Runtime | 16.8s | 5.8s | 2.3s | 1.8s |
| Weather/Wind | 8.3s | 3.3s | 0.8s | 0.3s |
| Browser Opening | 6.1s | 0.1s | 0.1s | 0.1s |
| Network I/O | 2.8s | 2.8s | 2.8s | 2.3s |
| Other | 1.6s | 1.6s | 1.6s | 1.6s |

**Target**: Sub-2-second analysis time (88% improvement)

## Code Quality Considerations

1. **Maintain Readability**: Don't sacrifice code clarity for minor gains
2. **Add Comments**: Document why optimizations were made
3. **Configuration**: Make optimization levels configurable
4. **Backward Compatibility**: Keep old behavior as fallback option
5. **Testing**: Add performance regression tests

## Monitoring

### Add Performance Logging:
```python
# Add to main.py
import time

def log_performance(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__}: {duration:.2f}s")
        return result
    return wrapper
```

### Track Over Time:
- Create `performance_history.json`
- Log runtime for each analysis
- Alert if performance degrades >20%

## Success Criteria

- [ ] Total runtime reduced by >60% (to <7s)
- [ ] No accuracy degradation in wind analysis (within 5%)
- [ ] All existing tests pass
- [ ] No new bugs introduced
- [ ] User experience improved (faster, non-blocking)
- [ ] Code remains maintainable

## Related Files

- `src/weather_fetcher.py` - Primary optimization target
- `main.py` - Browser opening optimization
- `src/optimizer.py` - Weather data fetching
- `scripts/profile_analysis.py` - Performance measurement
- `output/profile_stats.txt` - Current performance baseline