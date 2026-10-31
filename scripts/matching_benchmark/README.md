# Route-matching benchmark

A regression benchmark for route matching (#611, epic #616): commutes (`run_benchmark.py`) and
long rides (`run_long_ride_benchmark.py`, see [Long rides](#long-rides-615)). Run it before and
after **any** change to `src/route_comparison.py`, `src/route_analyzer.py`,
`src/long_ride_analyzer.py` or the `route_analysis` / `long_rides` config, and put the
before/after numbers in the commit or PR.

Background and the original audit: [docs/analysis/route-matching-review-2026-10.md](../../docs/analysis/route-matching-review-2026-10.md).

## Run

```bash
# Baseline, from a route_groups.json snapshot (gitignored; the default is data/route_groups.json)
python scripts/matching_benchmark/run_benchmark.py --snapshot data/route_groups.json

# Keep the baseline somewhere it won't be overwritten, then compare after a change
cp data/cache/matching_benchmark/summary.json /tmp/before.json
python scripts/matching_benchmark/run_benchmark.py --baseline /tmp/before.json
```

| Option | Default | Effect |
|---|---|---|
| `--snapshot` | `data/route_groups.json` | Snapshot to read rides from. From a worktree, point this at the main checkout's `data/`. |
| `--out` | `data/cache/matching_benchmark/` | Where `summary.json`, `pairs.csv` and the reference cache are written. Keep it gitignored. |
| `--workers` | CPU count | Processes for pairwise scoring. |
| `--app-workers` | 8 | `RouteAnalyzer` `n_workers` for the grouping runs. |
| `--shuffles` | 3 | Extra grouping runs in shuffled ride order (order stability). |
| `--skip-calibration` | off | Skip scoring every pair with the app. This is the slowest step. |
| `--baseline` | none | A previous `summary.json` to diff the headline numbers against. |
| `--set KEY=VALUE` | none | Override a `config.yaml` value for this run only (repeatable), e.g. `--set route_analysis.max_p95_deviation_m=75`. Use it to sweep thresholds. |

A full run on the June 2026 snapshot (222 rides, 12,211 pairs) takes under 2 minutes on 16
cores since #613 (it was about 9 minutes under the old Fréchet code). The reference labels are
cached per snapshot, so later runs only pay for the app side.

## What it measures

1. **Reference labels** ([reference.py](reference.py)). This code shares nothing with the app.
   - Tracks are projected to metres with a cos(lat) correction and resampled every 20 m. Each
     pair is measured against the other track densified to 5 m.
   - A pair is **same** if each track has at least 90% of its samples within 50 m of the other
     and the p95 deviation is 75 m or less. It is **diff** if coverage is 50% or less, and
     **ambig** otherwise.
   - Bump `REFERENCE_VERSION` if the definition changes.
2. **App grouping.** The app's real `RouteAnalyzer.group_similar_routes` is run in a temp cache
   dir with geocoding off, in snapshot order and in `--shuffles` random orders. Each grouping is
   scored for:
   - **purity:** the share of within-group pairs the reference labels **same**. This is strict:
     an **ambig** pair counts against it. "precision (excl ambig)" and the DIFFERENT count are
     the measure of wrongly merged routes;
   - **pair recall:** the share of same-route pairs that end up in one group;
   - group and single-ride counts;
   - **group pairs that should merge;**
   - how the biggest reference routes are split across groups.

   The snapshot's stored grouping is scored too, as a historical row.
3. **Calibration.** Every pair is scored with the app's pairwise path (prefilter +
   `RouteAnalyzer.calculate_route_similarity`) and tabulated against the reference p95
   deviation. The run reports AUC, the best-F1 threshold, and precision/recall at the configured
   threshold.
   - This assumes "higher score = more similar", and that a score of 1.0 or more is a match
     (`APP_MATCH_SCORE`, the contract of `RouteAnalyzer.calculate_route_similarity` since #613).
     If that contract changes, update `calibration()` in the same change.
4. **Order stability.** The adjusted Rand index between the snapshot-order grouping and each
   shuffled grouping (1.0 = identical).

## Baseline (June 2026 snapshot, code as of #611)

Snapshot sha1 `9f183a42157d`: 222 rides and 12,211 pairs, labelled 416 same, 7,711 diff and
4,084 ambig.

**Grouping vs the reference**

| | App (current code, snapshot order) | Stored snapshot grouping |
|---|---|---|
| Groups | 203 | 203 |
| Single-ride groups | 193 | 192 |
| Purity | 1.000 | 1.000 |
| Pair recall | **0.084** | 0.070 |
| Group pairs that should merge | 215 | 215 |
| Main h→w reference route | 19 rides in 12 groups | 19 rides in 12 groups |
| Main w→h reference route | 25 rides in 19 groups | 25 rides in 19 groups |

**Order stability:** group counts are 203 / 205 / 204 / 205 across shuffles. ARI vs snapshot
order has a minimum of **0.607**.

**Calibration**

| Measure | Result |
|---|---|
| AUC, ambig counted as diff | 0.988 |
| Best F1 | 0.737, at score ≥ 0.334 |
| At the 0.70 threshold | precision 1.000, recall 0.072 |
| Pairs with p95 under 25 m passing 0.70 | 16% |
| Reference-same pairs rejected by the prefilter | 0 of 416 |

Targets for the epic (#616): recall ≥ 0.9, purity ≥ 0.99, min ARI = 1.0, and each main commute
in one group.

## After #613 (metric replacement)

Same snapshot. Match rule: p95 deviation ≤ 100 m and mutual 50 m coverage ≥ 0.85.

| | #611 baseline | After #613 |
|---|---|---|
| Groups | 203 | **115** |
| Single-ride groups | 193 | 82 |
| Pair recall | 0.084 | **0.978** |
| Different-route pairs grouped | 0 | **0** |
| Precision, ambig excluded | 1.000 | 1.000 |
| Purity (strict, ambig counts against) | 1.000 | 0.689 |
| Group pairs that should merge | 215 | 5 |
| Main w→h reference route | 25 rides in 19 groups | 25 rides in 1 group |
| Main h→w reference route | 19 rides in 12 groups | 19 rides in 2 groups |
| Min ARI across shuffles | 0.607 | 0.794 |
| Calibration AUC (ambig as diff) | 0.988 | 0.9997 |

The strict purity drop is the 184 grouped pairs the reference calls **ambig**: most (about 146) have a
p95 deviation of 75–100 m, which the reference (75 m) deliberately leaves undecided and the app
(100 m) accepts. No pair the reference calls **diff** is grouped.

**Threshold sweep** (`--set route_analysis.max_p95_deviation_m=…`, coverage fixed at 0.85):

| p95 limit | Groups | Recall | Strict purity | Different grouped | Should merge |
|---|---|---|---|---|---|
| 75 m | 142 | 0.837 | 0.902 | 0 | 19 |
| 90 m | 120 | 0.981 | 0.716 | 0 | 6 |
| **100 m** | **115** | **0.978** | **0.689** | **0** | **5** |
| 125 m | 110 | 0.988 | 0.661 | 0 | 4 |

Recall plateaus from about 90 m, and nothing different is merged up to 125 m. 100 m is the
recommended value from the analysis and sits in the middle of that plateau.

## After #614 (clustering)

Same snapshot and match rule. The greedy pass (each ride compared only with the first ride of
each group, in input order) is replaced by centre (Butina) clustering: the ride matching the most
other ungrouped rides becomes a centre and takes every ungrouped ride that matches it, repeated
until none are left.

| | After #613 | After #614 |
|---|---|---|
| Groups | 115 | **112** |
| Single-ride groups | 82 | 81 |
| Pair recall | 0.978 | **0.990** |
| Different-route pairs grouped | 0 | **0** |
| Purity (strict, ambig counts against) | 0.689 | 0.659 |
| Group pairs that should merge | 5 | 3 |
| Main h→w reference route | 19 rides in 2 groups | **19 rides in 1 group** |
| Main w→h reference route | 25 rides in 1 group | **25 rides in 1 group** |
| Min ARI across shuffles | 0.794 | **1.000** |

The small strict-purity drop is 29 more **ambig** pairs inside the now-larger groups; nothing the
reference calls **diff** is grouped.

**Why not hierarchical linkage** (the analysis's first suggestion). Cut at the match threshold on
exact all-pairs distances (`d = max(p95 / limit, min_coverage / coverage)`):

| Method | Recall | Strict purity | Main h→w / w→h split into |
|---|---|---|---|
| complete | 0.748 | 0.896 | 3 / 2 groups |
| average | 0.938 | 0.793 | 2 / 2 |
| single | 1.000 | 0.591 | 1 / 1 (but chains, unbounded) |
| **centre (Butina)** | **0.990** | **0.659** | **1 / 1** |

Identical rides sit at `d ≈ 0.87` on this scale (coverage tops out near 98%), so complete and
average linkage have almost no room under the cut, and one borderline ride splits a main route.
Single linkage chains with no bound on how far apart two members can be. Centre clustering
bounds every member by the match rule against its centre.

**Speed.** Each ride is projected and resampled once, and `possible_match_pairs` exactly rules
out (via 50 m grid bounds and two sparse matrix products) the ~95% of pairs that can't match, so
only plausible pairs get the exact metric. On ~1,100 synthetic rides (jittered copies of this
snapshot, 2 workers) a cold grouping took 30 s and an incremental run 16 s on a desktop; the
greedy code took 20.5 minutes for 1,141 rides on the Pi.

## Long rides (#615)

[run_long_ride_benchmark.py](run_long_ride_benchmark.py) does the same for `LongRideAnalyzer`. Its
input is a copy of `data/cache/activities.json` plus a JSON list of commute activity IDs (the
IDs in the live `route_groups.json`), which the app excludes from long rides. Both go under the
gitignored `data/cache/matching_benchmark/`.

```bash
python scripts/matching_benchmark/run_long_ride_benchmark.py \
    --activities data/cache/matching_benchmark/activities.json \
    --commute-ids data/cache/matching_benchmark/commute_ids.json
# Threshold sweep: --app-cache keeps pair metrics between runs (they don't depend on thresholds)
python scripts/matching_benchmark/run_long_ride_benchmark.py --app-cache data/cache/matching_benchmark/app_cache \
    --shuffles 0 --set long_rides.min_coverage=0.85
```

**Reference.** It uses the same labels as for commutes (`reference.compare_long`), plus a one-way
"part of" relation: one ride meets the "same" bar against the other, but not the other way round.
A real corpus has millions of pairs, so `reference.long_ride_candidates` first rules out, with an
exact 100 m-cell bound, every pair that can only be **diff**. The labels are cached per input and
take about 20 minutes on 16 cores the first time.

The report covers:
- purity and recall, as for commutes;
- **same-name rides on different geometry** that get grouped;
- **link recall/precision:** of the reference part-of relations between rides in different
  groups, how many group pairs the app links (`LongRide.part_of`);
- order stability.

### Baseline and after (October 2026 activities, 3,753 long rides)

Input sha1 `67ee1b6d7dd4`: 7.04M pairs, of which 1.12M survive the screen. Labels: 33,876 same,
396,686 ambig, everything else diff; 102,001 part-of pairs.

| | Before (#614 code: names + Fréchet/Hausdorff < 1.2 km) | After #615 |
|---|---|---|
| Groups | 1,620 | 1,886 |
| Single-ride groups | 1,285 | 1,610 |
| Pair recall | 0.408 | **0.980** |
| Different-route pairs grouped | **7,683** | **0** |
| Precision, ambig excluded | 0.643 | **1.000** |
| Purity (strict) | 0.269 | 0.590 |
| Same-name, different-geometry pairs grouped (of 5,308) | 2,040 | **0** |
| Group links (reference wants about 6–7.5k) | none | 5,809 (recall 0.731, precision 0.748) |
| Min ARI across shuffles | 0.801 | **1.000** |
| Cold grouping, one process, desktop | 2,588 s | 263 s (67 s with a warm cache) |

The old code's compact-looking 1,620 groups (production showed 1,626) came from merging
different routes: by exact name, and by a 1.2 km average distance that spans parallel roads. The
new code has more groups because it stops doing that, but it finds 2.4× as many same-route pairs.

**Rule (defaults in `config.yaml`).** Two rides are the same route when mutual 50 m coverage is
≥ 0.9 (≥ 0.75 if they share a non-generic name) and their lengths are within 1.5×. There is no
p95 limit, so a longer turnaround or a short detour still matches. A shorter route with ≥ 0.9 of
itself along a longer one is linked to it.

**Sweep** (one shared `--app-cache`, so mostly warm):

| min_coverage / name prior | Groups | Recall | Different grouped | Same-name different | Link recall / precision |
|---|---|---|---|---|---|
| 0.85 / 0.60 | 1,568 | 0.970 | 110 | 73 | 0.643 / 0.821 |
| 0.85 / 0.75 | 1,622 | 0.971 | 36 | 0 | 0.647 / 0.815 |
| 0.85 / 0.75, p95 ≤ 200 m | 2,107 | 0.980 | 0 | 0 | 0.778 / 0.807 |
| 0.88 / 0.75 | 1,792 | 0.965 | 0 | 0 | 0.723 / 0.756 |
| 0.90 / 0.70 | 1,857 | 0.979 | 1 | 1 | 0.716 / 0.749 |
| **0.90 / 0.75** | **1,886** | **0.980** | **0** | **0** | **0.731 / 0.748** |
| 0.90 / 0.80 | 1,926 | 0.978 | 0 | 0 | 0.758 / 0.747 |
| 0.90 / none (0.90) | 2,004 | 0.982 | 0 | 0 | 0.769 / 0.739 |
| 0.92 / 0.75 | 2,006 | 0.968 | 0 | 0 | 0.771 / 0.697 |

- A name prior of 0.6 merges same-named different routes, and 0.70 lets the first one through.
  At 0.75 it merges about 120 groups with no errors.
- Length-ratio limits from 1.3 to 2.0 change recall by under 0.005.
- A p95 limit gives the same recall with no errors. But it splits off any variant with more
  than 5% of its length elsewhere, so it stays off by default.

Strict purity stays low because the reference's "same" bar (p95 ≤ 75 m) is far stricter than
"a variant of the same route". Most within-group ambig pairs are such variants. "Different
grouped" is the error measure.

## Privacy

The repo is public, and these rides start and end at the user's home and workplace.

- The printed report and `summary.json` contain **no coordinates, route names or activity IDs**.
- `pairs.csv` has activity IDs (Strava activity IDs can be looked up) and must stay under the
  gitignored `data/cache/`. Never commit it or paste it into an issue.
- Don't commit snapshots or fixtures made from real rides. Use synthetic tracks, as
  `tests/test_route_matching_quality.py` does.

## Related tests

`tests/test_route_matching_quality.py` holds the synthetic, end-to-end regression tests:
- offset symmetry;
- point spacing;
- endpoint shift;
- detour;
- GPS spike;
- order invariance;
- stable group IDs;
- cache invalidation;
- a stopped run.

For long rides (#615) it also covers:
- reversed, rotated, and reversed-and-rotated loops;
- point spacing;
- parallel roads;
- a longer turnaround and a short detour (same route);
- a sub-segment and an extension (linked, not merged);
- one-way vs out-and-back;
- same name on different geometry (not merged);
- the name prior;
- generic Strava names;
- fallback shape names;
- order invariance;
- member-to-centre matching;
- cache reuse and discard.

Known defects are `xfail(strict=True)` with the issue that fixes them. When a fix makes one
pass, remove its marker in the same change.
