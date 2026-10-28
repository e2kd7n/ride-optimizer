# Route-matching benchmark

A regression benchmark for commute route matching (#611, epic #616). Run it before and after
**any** change to `src/route_comparison.py`, `src/route_analyzer.py` or the
`route_analysis` config, and put the before/after numbers in the commit or PR.

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

A full run on the June 2026 snapshot (222 rides, 12,211 pairs) takes about 9 minutes on 16
cores, mostly calibration and the grouping runs under today's Fréchet code. The reference labels
are cached per snapshot, so later runs only pay for the app side.

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
   - **purity:** the share of within-group pairs that are the same route;
   - **pair recall:** the share of same-route pairs that end up in one group;
   - group and single-ride counts;
   - **group pairs that should merge;**
   - how the biggest reference routes are split across groups.

   The snapshot's stored grouping is scored too, as a historical row.
3. **Calibration.** Every pair is scored with the app's pairwise path (prefilter +
   `RouteAnalyzer.calculate_route_similarity`) and tabulated against the reference p95
   deviation. The run reports AUC, the best-F1 threshold, and precision/recall at the configured
   threshold.
   - This assumes "higher score = more similar" and compares against
     `RouteAnalyzer.similarity_threshold`. If #613 changes that contract, update `calibration()`
     in the same change.
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

Known defects are `xfail(strict=True)` with the issue that fixes them. When a fix makes one
pass, remove its marker in the same change. Long-ride matching isn't covered yet; extending
both the benchmark and the tests to long rides is the first step of #615.
