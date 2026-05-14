# Issue #73: Route Matching Analysis for Routes 78 and 62

**Date:** 2026-05-14  
**Issue:** [#73](https://github.com/user/repo/issues/73)  
**Status:** Investigation Complete  
**Conclusion:** Routes are correctly NOT being grouped - they are genuinely different routes

---

## Executive Summary

Routes 78 and 62 (specifically `home_to_work_78` and `home_to_work_62`) are **correctly NOT being grouped together** by the route matching algorithm. Despite both using the Lakefront Trail and having similar start/end points, they follow significantly different paths with a Fréchet distance of **2,305 meters** - far exceeding the 300m threshold.

**Key Finding:** The algorithm is working as designed. These routes should remain separate.

---

## Route Details

### Route 62: `home_to_work_62`
- **Name:** Lakefront Trail → Lincoln Park Fitness Course
- **Activity ID:** 10807575434
- **Distance:** 14,587m (9.1 miles)
- **Duration:** 2,131s (35.5 minutes)
- **Elevation Gain:** 38.0m
- **Coordinates:** 374 GPS points
- **Start Point:** [41.98736, -87.65451]
- **End Point:** [41.88154, -87.63378]

### Route 78: `home_to_work_78`
- **Name:** Via Lakefront Trail
- **Activity ID:** 9834092279
- **Distance:** 16,577m (10.3 miles)
- **Duration:** 2,254s (37.6 minutes)
- **Elevation Gain:** 45.0m
- **Coordinates:** 354 GPS points
- **Start Point:** [41.98736, -87.65453]
- **End Point:** [41.88371, -87.63676]

### Comparison
- **Distance Difference:** 1,990m (12% difference)
- **Duration Difference:** 123 seconds (2 minutes)
- **Elevation Difference:** 7.0m
- **Start Point Distance:** 1.66m (essentially identical)
- **End Point Distance:** 345m (different destinations)

---

## Similarity Metrics (Using Actual Algorithm)

### 1. Fréchet Distance (Primary Metric)
The Fréchet distance measures how similar two curves are by considering the order of points (like walking a dog on a leash).

- **Fréchet Distance:** 2,305.55 meters
- **Threshold:** 300 meters
- **Similarity Score:** 0.1151 (out of 1.0)
- **Status:** ✗ **FAIL** (threshold: 0.70)

**Interpretation:** The routes follow significantly different paths. The Fréchet distance is **7.7x higher** than the threshold.

### 2. Hausdorff Distance (Secondary Validation - 95th Percentile)
The Hausdorff distance measures the maximum spatial separation between routes, using the 95th percentile to tolerate GPS glitches.

- **95th Percentile Distance:** 2,255.29 meters
- **Threshold:** 200 meters
- **Similarity Score:** 0.0815 (out of 1.0)
- **Status:** ✗ **FAIL** (threshold: 0.50)

**Interpretation:** The routes are spatially far apart. Even ignoring the worst 5% of deviations, 95% of points are over 2km apart.

### 3. Combined Similarity (Algorithm Logic)
Since Hausdorff similarity (0.0815) is below 0.50, the algorithm applies a **30% penalty** to the Fréchet score:

- **Combined Similarity:** 0.1151 × 0.7 = **0.0806**
- **Threshold:** 0.70 (from `config.yaml`)
- **Gap:** 0.6194 below threshold
- **Status:** ✗ **FAIL**

**Verdict:** Routes should **NOT** be grouped together.

---

## Root Cause Analysis

### Why Aren't These Routes Matching?

1. **Different Path Topology**
   - Despite both using "Lakefront Trail," they take substantially different routes
   - Route 78 is 1,990m (12%) longer, suggesting a detour or different path segment
   - The Fréchet distance of 2.3km indicates they diverge significantly at some point

2. **Spatial Separation**
   - The 95th percentile Hausdorff distance of 2.3km means that even after ignoring outliers, the routes are over 2km apart at their most divergent points
   - This is **11.3x higher** than the 200m threshold

3. **Different Destinations**
   - End points are 345m apart, suggesting they end at different locations
   - Route 62 ends at Lincoln Park Fitness Course
   - Route 78 has a more generic "Via Lakefront Trail" name

### Visual Assessment

Both routes:
- ✓ Start from essentially the same location (1.66m apart)
- ✓ Use the Lakefront Trail
- ✗ Follow different paths along the trail (2.3km divergence)
- ✗ End at different locations (345m apart)
- ✗ Have 12% distance difference (1,990m)

**Conclusion:** These are genuinely different route variants, not the same route with GPS noise.

---

## Algorithm Validation

### Is the Algorithm Working Correctly?

**YES.** The route matching algorithm is functioning as designed:

1. **Fréchet Distance (Primary)**
   - Correctly identifies that routes follow different paths
   - 2,305m distance is well above the 300m threshold
   - Similarity score of 0.1151 is far below the 0.70 grouping threshold

2. **Hausdorff Distance (Secondary Validation)**
   - Correctly identifies spatial separation
   - 95th percentile approach successfully tolerates GPS noise
   - 2,255m distance confirms routes are genuinely different

3. **Dual Validation Logic**
   - Hausdorff < 0.50 triggered the 30% penalty (correct behavior)
   - This prevents grouping routes that are spatially far apart even if Fréchet suggests similarity

4. **Thresholds Are Appropriate**
   - Fréchet threshold (300m) is reasonable for urban cycling routes
   - Hausdorff threshold (200m) appropriately catches spatial divergence
   - Similarity threshold (0.70) provides good balance

---

## Recommendations

### No Changes Needed

The algorithm is working correctly. Routes 78 and 62 should remain separate because:

1. They follow genuinely different paths (2.3km Fréchet distance)
2. They are spatially far apart (2.3km Hausdorff distance)
3. They have different distances (12% difference)
4. They end at different locations (345m apart)

### If User Believes They Should Match

If the user believes these routes should be grouped together, they would need to:

1. **Increase Fréchet Threshold** in `config.yaml`:
   ```yaml
   route_analysis:
     similarity_threshold: 0.70  # Would need to be ~0.12 or lower
   ```
   **NOT RECOMMENDED:** This would cause many unrelated routes to be grouped together.

2. **Adjust Distance Thresholds:**
   - Increase Fréchet threshold from 300m to ~2,500m
   - Increase Hausdorff threshold from 200m to ~2,500m
   **NOT RECOMMENDED:** This would make the algorithm too permissive.

3. **Manual Grouping:**
   - Add a feature to manually merge route groups
   - This would be the safest approach if grouping is truly desired

---

## Technical Details

### Algorithm Implementation
- **File:** `src/route_analyzer.py`
- **Method:** `calculate_route_similarity()` (lines 419-474)
- **Fréchet Calculation:** `_calculate_frechet_similarity()` (lines 522-554)
- **Hausdorff Calculation:** `_calculate_hausdorff_similarity()` (lines 476-520)

### Configuration
- **File:** `config/config.yaml`
- **Similarity Threshold:** 0.70 (line 39)
- **Outlier Tolerance:** 95th percentile (line 42)

### Data Storage
- **File:** `data/route_groups.json`
- **Route 62 Group ID:** `home_to_work_62`
- **Route 78 Group ID:** `home_to_work_78`

---

## Conclusion

**Issue #73 can be closed as "Working as Intended."**

The route matching algorithm correctly identified that routes 78 and 62 are different routes. The Fréchet distance of 2,305 meters and Hausdorff distance of 2,255 meters both far exceed their respective thresholds, indicating these routes follow substantially different paths despite sharing the Lakefront Trail.

No algorithm changes are needed. The dual validation approach (Fréchet + Hausdorff) is working correctly to distinguish between:
- Similar routes with GPS noise (should be grouped)
- Different route variants (should remain separate) ← **Routes 78 and 62 fall here**

---

## Appendix: Calculation Details

### Similarity Score Formula

**Fréchet Similarity:**
```
similarity = 1 / (1 + distance_meters / threshold_meters)
similarity = 1 / (1 + 2305.55 / 300)
similarity = 1 / (1 + 7.685)
similarity = 0.1151
```

**Hausdorff Similarity:**
```
similarity = 1 / (1 + distance_meters / threshold_meters)
similarity = 1 / (1 + 2255.29 / 200)
similarity = 1 / (1 + 11.276)
similarity = 0.0815
```

**Combined Similarity (with penalty):**
```
combined = frechet_similarity × 0.7  (because hausdorff < 0.50)
combined = 0.1151 × 0.7
combined = 0.0806
```

**Grouping Decision:**
```
0.0806 < 0.70 → DO NOT GROUP
```

---

**Analysis completed by:** Bob (AI Assistant)  
**Date:** 2026-05-14  
**Issue Status:** Investigation complete, no changes needed