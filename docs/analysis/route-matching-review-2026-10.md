# Route Matching Review — October 2026

**Date:** 2026-10-27
**Scope:** commute route matching (`src/route_comparison.py`, `src/route_analyzer.py`), long-ride matching (`src/long_ride_analyzer.py`), and the caches and services around them.
**Method:** three independent reviews, plus an empirical audit on real data:
1. a trajectory-similarity / geometry review of the distance math;
2. a clustering review of grouping, representatives, incremental merge and caching;
3. an empirical evaluation of all 12,211 same-direction ride pairs in the June 2026 `route_groups.json` snapshot (222 commute rides, 203 groups), measured against an independent reference in true metres.

> **Privacy:** this document is public. Groups are referred to by ID only. Route names, coordinates and home/work locations are deliberately left out.

---

## TL;DR

Matching is **precise but has terrible recall**. Every pair of rides the app puts in one group really is the same route (purity 1.000). But **93% of same-route ride pairs end up in different groups**, which leaves **192 of 203 groups (95%) as single rides**. The user's two main commutes are each one physical route of 19 and 25 rides. The app shows each as 12–19 separate "routes" under 9–12 different names, and no group has a frequency above 4.

The root cause is the **metric and threshold**, not the prefilters.
- The commute score is `1/(1 + Fréchet_m/300)` with a threshold of 0.70, so two rides match only if their discrete Fréchet distance is **≤ 128.6 m**.
- Fréchet is a *max* statistic. One different parking spot, a one-block detour or one GPS spike rejects an otherwise identical ride.
- Same-route pairs have a median Fréchet of about 240 m, while their 95th-percentile point-to-track deviation is about 26 m.

Several further defects make it worse:
- longitude is not scaled by cos(lat);
- tracks are not resampled before comparison;
- the Hausdorff "disagreement penalty" never runs on a pair that could still match;
- greedy clustering depends on input order;
- the representative ride is not a medoid;
- **several cache bugs** can silently corrupt or freeze the groups.

A coverage-based rule in true metres finds **97.8% of same-route pairs with zero different routes in any group** on the same data.

---

## 1. Measured accuracy (empirical audit)

**Reference.** Built independently of the app's code:
- tracks projected to local metres with a cos(lat) correction;
- resampled every 20 m;
- distances measured to the other track resampled every 5 m.

Labels:
- **Same route:** both tracks have at least 90% of their points within 50 m of the other, and the p95 deviation is 75 m or less.
- **Different route:** 50% coverage or less.
- Anything in between is ambiguous.

Result: 416 same pairs, 7,711 different, 4,084 ambiguous. The conclusions hold from strict (0.95 / 50 m) to loose (0.8 / 150 m) definitions; recall at the current threshold stays between 0.045 and 0.11.

**Reproducibility.** Re-running the app's grouping code on these scores reproduces exactly 203 groups.

| Measure | Result |
|---|---|
| Purity (within-group pairs that are the same route) | **1.000** (29/29) |
| Pair-level recall | **0.070** (F1 0.13) |
| Same-route pairs split across groups | 387 / 416 |
| Group pairs that should have merged | 215 |
| Single-ride groups | 192 / 203 |
| Main home→work route (reference) | 19 rides → 12 groups, 9 names, max frequency 4 |
| Main work→home route (reference) | 25 rides → 19 groups, 12 names, max frequency 4 |
| Groups sharing a name with another group | 81 / 203 |

### Calibration: app score vs real deviation

| p95 deviation (m) | Pairs | Share same | Median app score | Share passing 0.70 |
|---|---|---|---|---|
| 0–25 | 149 | 1.00 | 0.56 | 16% |
| 25–50 | 134 | 1.00 | 0.54 | 4.5% |
| 50–75 | 142 | 0.94 | 0.56 | 0% |
| 75–100 | 170 | ambiguous | 0.52 | 0% |
| 150–250 | 192 | 0 | 0.31 | 0% |
| > 1000 | 7,647 | 0 | 0.08 | 0% |

Rides that agree to within 25 m almost all fail.

**Ranking quality.** The score *ranks* pairs well but the threshold is in the wrong place. Counting ambiguous pairs as different:

| Predictor | AUC | Best F1 |
|---|---|---|
| App score | 0.988 | 0.74, at score ≥ 0.334 |
| App's own p95-Hausdorff component | 0.9945 | 0.81, at ≤ 122 m |
| True-metre Fréchet | 0.981 | 0.66 |

Fréchet is the weakest signal for commutes, whatever form it takes.

**Retuning the threshold alone is not enough.** At 0.50: 140 groups, recall 0.60. At 0.25: 71 groups, but 18 different-route pairs land in the same group.

**There is a natural gap in the data.** For pairs with at least 80% coverage, p95 deviation clusters at 0–100 m (590 pairs). It thins out at 100–200 m (108 pairs) before a "variant routes" bulge at 200–300 m (296 pairs). A threshold of about 100 m sits in the gap.

### Worst examples (group IDs from the June snapshot)

1. `work_to_home_17` vs `work_to_home_54`: coverage 0.98, p95 deviation **5.4 m**. A 172 m start offset pushes Fréchet to 231 m and the score to 0.57, so they are separate groups.
2. `home_to_work_17` vs `home_to_work_20`: 99% coverage, p95 **3.9 m**, median 2 m, score 0.56. Separate.
3. `work_to_home_82` vs `work_to_home_84`: p95 5.8 m, start offset 337 m, Fréchet 452 m, score 0.40. Separate.
4. `home_to_work_16` (frequency 4) vs `home_to_work_4` (frequency 3): three cross-group pairs at p95 5.7–6.3 m with full coverage. The same route is shown as two routes under two names.
5. `work_to_home_17` vs `work_to_home_28`: score 0.73 passes the threshold, yet they are separate groups, because the greedy grouping only compares against each group's first ride.

### Sanity checks (all passed)

- 222 unique activity IDs, and no ride appears in two groups.
- Every group's frequency equals its member count, and every representative is a member.
- No degenerate tracks: at least 243 points and at least 12 km each.

---

## 2. Geometry and metric defects

| # | Defect | Location | Evidence |
|---|---|---|---|
| G1 | **A max-type metric (discrete Fréchet) gates the match.** It is dominated by endpoint offsets and local detours. | `route_comparison.py:205-217`, `route_analyzer.py:490-592` | Same-route pairs: median Fréchet 185–240 m vs median p95 deviation 26 m. In 85% of pairs the max is more than 3× the p95. Synthetic tests on an identical track: start 150 m off → 0.545; one-block 100 m detour → 0.690; 500 m spike → 0.536. All rejected. |
| G2 | **Longitude is not scaled by cos(lat)** in any degree-space path. | `route_comparison.py:216, 235`, `passes_prefilter_deg`, `Route.compute_geometry` (`route_analyzer.py:98-111`) | The same 100 m offset scores 0.751 north and 0.691 east. East-west distance is inflated about 1.35× at this latitude. The centroid prefilter is anisotropic (1.65 km east-west vs 2.2 km north-south). |
| G3 | **No arc-length resampling.** Strava `summary_polyline` points are spaced unevenly (31 m median, 1.59 km max). | whole comparison path | The same geometry at 10 m vs 300 m spacing gives a 201 m distance and a score of 0.598. On real pairs, resampling cut some distances from 137 to 59 m. |
| G4 | **The Hausdorff disagreement penalty is dead code.** Because p95-Hausdorff ≤ Fréchet, the penalty only fires on pairs that already failed. It also measures vertex-to-vertex distance, not point-to-segment. | `route_comparison.py:256`, `route_analyzer.py:529-531` | Changed 0 of 12,211 decisions. |
| G5 | **Silent fallback to a different metric.** `except Exception: pass` falls back to Hausdorff with a 200 m scale, so the matching rule changes with no flag. | `commute_similarity_score`, `route_analyzer.py:590-592` | Code inspection. |
| G6 | **The threshold has no physical meaning, and two values disagree.** The config says 0.70 (128.6 m); the code default is 0.85 (52.9 m). | `config.yaml:60`, `route_analyzer.py:178` | Off by a factor of 2.4 in metres. |
| G7 | **Extent-point prefilter false negative.** On a loop with two far corners at about the same distance, moving them 50 m flips which one `argmax` picks. | `route_comparison.py:61-64, 118` | Rejected a pair whose combined distance was 0.108 km. |

The commute prefilters are otherwise fine in practice: they rejected 0 of 323 true same-route pairs.

> **Note on how much of the problem is endpoints:** the reviews differ here. The empirical audit attributes 236 of 386 misses to the start/end gap alone exceeding 128.6 m. The clustering review, using densified tracks and a different attribution test, found endpoints explain only a small share and interior max-deviation dominates. Both conclusions point to the same fix: a robust, coverage-based metric removes both failure modes.

---

## 3. Clustering and pipeline defects

| # | Defect | Location | Evidence |
|---|---|---|---|
| C1 | **Greedy leader clustering depends on input order.** Each ride is compared only to the group's pivot (its first ride). | `route_analyzer.py:953-1018` | 300 shuffled orders: median ARI 0.77 / 0.70, minimum 0.53. 32 of 45 co-grouped pairs depend on order. 6 pairs scoring ≥ 0.70 still ended up in different groups. |
| C2 | **The representative is the median-*duration* ride, not a geometric medoid.** New rides are compared to it, not to the pivot, so the comparison point drifts. | `:1064-1080`, `:803-808` | It matched the medoid in only 2 of 6 groups with 3+ rides. |
| C3 | **Incremental merge ≠ full recompute.** Groups are never merged, split or re-pivoted, and unmatched rides are clustered only among themselves. | `:776-837` | Code inspection. |
| C4 | **The groups cache ignores the threshold, algorithm and home/work.** They are saved but never checked, and the "configuration changed" branch can't be reached. | `:615-628`, `:295`, `:665` | A threshold change has no effect until a ride is deleted or `force_reanalysis` is set. |
| C5 | **The preview pass corrupts the real cache.** It runs `force_reanalysis=True` against the default `cache/` dir, which deletes the real groups cache. It then saves groups for ≤ 10 activities using home/work detected from only those 10 rides. | `analysis_service.py:460-464`, `route_analyzer.py:192-194` | Verified in code. The main run then usually takes the incremental path on top of the preview groups. |
| C6 | **Stopping mid-run drops rides permanently.** The loop breaks after partial grouping, but *all* activity IDs are saved. The next run is a "perfect cache hit". | `:1048`, `:716` | Verified in code. |
| C7 | **The similarity cache stores scores**, keyed on a 5-point hash with no version. Prefilter rejections are persisted as a permanent 0.0. | `:349-388`, `:968` | 988 of 4,963 and 740 of 5,773 live entries differ from a fresh computation by up to 0.12. No decision flips at 0.70 today, but any formula change will reuse stale values. |
| C8 | **Group IDs are positional**, but favourites are keyed on them. | `:1038`, `:830`, `route_library_service.py:309,334` | After a recompute, a favourite can point to a different route. |
| C9 | **Plus-route flags only ever get set**, and they compare a group representative against the median of all rides pooled together. | `:839-895` | Flags stick across runs. With mostly single-ride groups, "plus" is effectively a per-ride label (28 of 110 rides). |
| C10 | **Misclassified rides are dropped, not bucketed.** Direction is decided with a 500 m radius at both ends, and there is no "other" bucket. | `:458-488` | Suspected silent loss from privacy-zone trimming or mid-commute stops. Not quantified. |

---

## 4. Long-ride matching defects (code review and synthetic tests; not yet measured on real data)

| # | Defect | Location |
|---|---|---|
| L1 | The match rule is `(Fréchet + Hausdorff)/2 < 1.2 km`. A uniform parallel offset merges at up to **1.2 km**, which spans several parallel roads. Yet a 2 km longer turnaround scores 2.0 and is rejected. Too loose sideways, too strict on length. | `long_ride_analyzer.py:302, 446`, `config.yaml:105` |
| L2 | **No reversal or start-rotation invariance.** A 38 km loop ridden in reverse scores 6.0 km; started 9 km further round, it scores 4.28 km. Both are rejected. | `combined_distance_km` |
| L3 | **No partial-overlap credit.** A 15 km sub-segment of a 25 km ride scores 10 km. | `combined_distance_km` |
| L4 | **Exact-name grouping does no geometry check.** The generic-name list misses common Strava defaults ("Night Ride", "Morning Gravel Ride", localised names). | `:174-185` |
| L5 | **Consolidation is star-shaped** around the most recent ride and depends on dict order. Unnamed rides are matched only to group representatives and never clustered with each other. | `:222`, `:408-560` |
| L6 | **Fallback names bucket by distance to 0.1 km.** This merges unrelated loops of the same length and splits one route ridden at 42.3 km vs 42.4 km. Every point-to-point ride is labelled "Out & Back". | `:583-626` |
| L7 | **Prefilter rejections are cached as `inf` under representative IDs**, which go stale as group membership changes. Errors are also mapped to `inf` (not similar). | `:283`, `:307-309`, `:443-452` |

---

## 5. Recommendations

### R1. One metric, in metres, robust to endpoints and detours (commutes and long rides)

- Project once to a local metric frame with the cos(lat) correction, and delete the degree-space path.
- Resample both tracks by arc length every 10–20 m. Use point-to-segment distances via a KD-tree on a densified copy of the other track.
- **Match rule:**
  - p95 symmetric nearest-point deviation ≤ **100 m**;
  - **and** mutual coverage (the share of each track within 50 m of the other, taking the minimum of the two directions) ≥ **0.85**.

  In simulation on the June data this gives **115 groups (vs 203), recall 0.978, and 0 different-route pairs in any group**.
- Express thresholds in metres in `config.yaml`. Drop the `1/(1+d/300)` mapping.
- If ride order matters for a use case, keep Fréchet only as a secondary order check, on resampled tracks with the first and last ~300 m trimmed.
- Remove the dead Hausdorff penalty (G4) and the silent fallback (G5). Surface errors instead.

### R2. Deterministic agglomerative clustering

- Build a pairwise distance matrix (n is a few hundred, so this is cheap with `scipy.cluster.hierarchy`). Cut complete or average linkage at the metre threshold.
  - Average linkage on mean closest-point distance at 40 m gives 26 / 46 groups (largest 21 / 25), vs 98 / 105 today.
  - Complete linkage on p95 at 60 m gives 75 / 81.

  The final cut is chosen with the benchmark in R5.
- Use the **geometric medoid** as the representative (minimum summed distance), recomputed whenever a group changes. Keep median duration as a displayed statistic only.
- **Incremental updates:** add new rides to the matrix and re-cut. This must give the same result as a full recompute (add a test).
- **Stable group IDs**, e.g. derived from the medoid's activity ID, so favourites survive a recompute.
- **Plus routes:** reset flags on every run, and compare each ride against its own group's median.
- **Direction:** add an "other / unclassified" bucket instead of dropping rides, and count how many rides fall in it.

### R3. Cache correctness (data-integrity bugs; fix first or alongside R1)

- Key the groups cache on (activity-ID set, threshold, metric/algorithm version, home/work). A mismatch forces a regroup.
- Give the preview pass its own `cache_dir`, or no cache at all. It must never delete or overwrite the real groups cache.
- Never save the groups cache after a stopped or partial run, or save only the IDs that were actually grouped.
- Cache **distances**, not scores, under a versioned key. Don't persist prefilter rejections.

### R4. Long rides

- Use the R1 coverage metric instead of the 1.2 km average.
- Make loops rotation- and direction-invariant: also try the reversed track, and coverage scoring is already start-invariant.
- Keep a separate asymmetric **"contains"** score, so sub-segments and extensions can be *linked* to a route without being *merged* into it.
- Treat the ride name only as a prior: require geometric agreement within a name group, and cluster unnamed rides geometrically with R2.
- Drop the distance-string fallback buckets and the extent-point prefilter (G7).

### R5. Regression benchmark and tests

- Turn the audit scripts into a repeatable benchmark that reports purity, recall, number of groups and calibration on a local snapshot. Run it before and after every matching change.
- Add unit tests for:
  - north/east offset symmetry;
  - resampling invariance;
  - a one-block detour;
  - an endpoint shift;
  - a GPS spike;
  - loop reversal and rotation;
  - a sub-segment ride;
  - order invariance of clustering;
  - incremental vs full recompute equality;
  - cache invalidation when the threshold changes;
  - stop-mid-run behaviour.

---

## 6. Limits of this review

- Commute results come from one June 2026 snapshot (n = 222). Long-ride findings come from code review and synthetic tests, not real data.
- The "same route" label depends on a chosen reference definition. The conclusions held across a wide range of definitions.
- The tracks are Strava `summary_polyline`. Whether full-resolution `polyline` changes the numbers materially is untested.
