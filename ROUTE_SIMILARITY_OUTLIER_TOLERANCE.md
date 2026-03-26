# Issue: Implement Outlier-Tolerant Route Similarity Algorithm

## Problem

The current route matching algorithm is **too strict**, causing similar routes to be separated into different groups based on single-point deviations. This leads to over-clustering where substantively identical commute routes are treated as unique.

### Current Behavior

- Uses **Hausdorff distance** which measures the **maximum deviation** at ANY single point
- With similarity threshold 0.70, routes must stay within ~86 meters along the **entire path**
- A single GPS glitch, brief detour, or parallel street deviation creates a "unique" route
- Result: Routes that represent the same commute pattern are fragmented into multiple groups

### Root Cause

From `src/route_analyzer.py` lines 465-493:
```python
# Calculate Hausdorff distance in both directions
dist_forward = directed_hausdorff(coords1, coords2)[0]
dist_backward = directed_hausdorff(coords2, coords1)[0]

# Use maximum distance (this is the maximum deviation at any point)
max_dist = max(dist_forward, dist_backward)
```

**The problem**: Using `max()` means a single outlier point dominates the similarity calculation.

## Proposed Solution: Percentile-Based Distance

Replace maximum deviation with **95th percentile deviation** to tolerate outliers while catching substantive route differences.

### Algorithm Changes

**1. Replace Hausdorff Maximum with Percentile**

```python
def _calculate_hausdorff_similarity_with_tolerance(self, coords1: np.ndarray, 
                                                   coords2: np.ndarray,
                                                   percentile: float = 95.0) -> float:
    """
    Calculate similarity using percentile-based Hausdorff distance.
    
    Instead of using the maximum deviation (which is sensitive to outliers),
    use the Nth percentile of deviations. This allows X% of points to be
    outliers while still detecting substantive route differences.
    
    Args:
        coords1: First route coordinates
        coords2: Second route coordinates
        percentile: Percentile to use (default 95.0 = ignore worst 5% of points)
        
    Returns:
        Similarity score (0-1)
    """
    # Calculate point-to-point distances in both directions
    from scipy.spatial.distance import cdist
    
    # Distance from each point in coords1 to nearest point in coords2
    distances_1_to_2 = cdist(coords1, coords2).min(axis=1)
    
    # Distance from each point in coords2 to nearest point in coords1
    distances_2_to_1 = cdist(coords2, coords1).min(axis=1)
    
    # Use percentile instead of max
    percentile_dist_1 = np.percentile(distances_1_to_2, percentile)
    percentile_dist_2 = np.percentile(distances_2_to_1, percentile)
    
    # Take the larger of the two percentile distances
    percentile_dist = max(percentile_dist_1, percentile_dist_2)
    
    # Convert degrees to meters
    normalized_dist = percentile_dist * 111000
    
    # Convert to similarity score
    distance_threshold = 200  # meters
    similarity = 1 / (1 + normalized_dist / distance_threshold)
    
    return similarity
```

**2. Update Main Similarity Calculation**

In `calculate_route_similarity()` (line 408), replace the call to `_calculate_hausdorff_similarity()` with the new percentile-based version.

**3. Add Configuration Parameter**

Add to `config/config.yaml`:
```yaml
route_analysis:
  similarity_threshold: 0.70
  outlier_tolerance_percentile: 95.0  # Ignore worst 5% of point deviations
```

### Benefits

1. **Tolerates GPS Glitches**: Single-point GPS errors don't create false uniqueness
2. **Handles Brief Detours**: Stopping at a coffee shop or avoiding construction won't fragment routes
3. **Catches Real Differences**: Routes that differ at many points will still separate correctly
4. **Configurable**: Can tune the percentile (90, 95, 99) based on data quality

### Example Impact

**Before (Max Deviation)**:
- Route A: Main Street entire way
- Route B: Main Street, but GPS glitches 150m at one intersection
- Result: **Separate groups** (max deviation = 150m > 86m threshold)

**After (95th Percentile)**:
- Route A: Main Street entire way  
- Route B: Main Street, but GPS glitches 150m at one intersection (5% of points)
- Result: **Same group** (95th percentile deviation = ~20m < 86m threshold)

**Still Separates Different Routes**:
- Route A: Main Street entire way
- Route C: Takes parallel Oak Street for 2km (20% of points deviate >100m)
- Result: **Separate groups** (95th percentile deviation = ~100m > 86m threshold)

## Implementation Steps

1. [ ] Add `_calculate_hausdorff_similarity_with_tolerance()` method to `RouteAnalyzer`
2. [ ] Update `calculate_route_similarity()` to use percentile-based calculation
3. [ ] Add `outlier_tolerance_percentile` config parameter
4. [ ] Update Fréchet calculation to also use percentile approach (optional)
5. [ ] Clear route groups cache to force reanalysis
6. [ ] Test with existing routes to verify improved grouping
7. [ ] Update `ROUTE_MATCHING_EXPLANATION.md` with new algorithm details
8. [ ] Add unit tests for percentile calculation

## Testing Strategy

1. **Before/After Comparison**: Run `debug_route_grouping.py` before and after changes
2. **Expected Outcome**: Fewer route groups, with similar routes properly clustered
3. **Validation**: Manually review grouped routes to ensure no false positives (truly different routes grouped together)

## Priority

**High** - This directly addresses user feedback that "uniqueness is currently being determined based on small deviations at one point in a route rather than substantive overall deviations"

## Related Files

- `src/route_analyzer.py` (lines 408-527) - Main implementation
- `ROUTE_MATCHING_EXPLANATION.md` - Documentation to update
- `debug_route_grouping.py` - Testing tool
- `config/config.yaml` - Configuration

## References

- Hausdorff distance: https://en.wikipedia.org/wiki/Hausdorff_distance
- Percentile-based outlier detection: Standard statistical approach for robust estimation