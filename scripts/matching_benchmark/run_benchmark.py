"""
Route-matching regression benchmark (#611).

Measures how well the app's *current* commute route matching agrees with an
independent, metre-based reference (see reference.py) on a local snapshot of
real rides. Run it before and after any change to route matching and compare.

    python scripts/matching_benchmark/run_benchmark.py --snapshot data/route_groups.json
    python scripts/matching_benchmark/run_benchmark.py --baseline data/cache/matching_benchmark/summary.json

What it does:
  1. Loads every commute ride (coordinates + direction) from a route_groups.json
     snapshot. The snapshot's stored grouping is scored too, as a historical row.
  2. Labels every same-direction ride pair same / diff / ambig with the reference.
     Cached per snapshot under --out, since it doesn't depend on app code.
  3. Scores every pair with the app's own pairwise path (prefilter +
     RouteAnalyzer.calculate_route_similarity) for calibration.
  4. Re-groups the rides with the app's real RouteAnalyzer.group_similar_routes
     (temp cache dir, geocoding off), in snapshot order and in shuffled orders.
  5. Prints purity / recall / group counts / calibration / order stability and
     writes summary.json + pairs.csv to --out.

PRIVACY: the repo is public. Output printed or written here contains no
coordinates, route names or Strava activity IDs except pairs.csv, which stays
under the gitignored data/cache/ directory. Don't paste pairs.csv anywhere.
"""
import argparse
import csv
import hashlib
import json
import os
import random
import sys
import tempfile
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reference  # noqa: E402

DIRECTIONS = ('home_to_work', 'work_to_home')


# ---------------------------------------------------------------- snapshot

def load_snapshot(path):
    """Return (rides, stored_partition, ride_order). Rides keep no names."""
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    rides, stored = {}, {}
    for direction_groups in _iter_groups(data['route_groups']):
        for g in direction_groups:
            for r in g['routes']:
                aid = int(r['activity_id'])
                rides[aid] = dict(
                    activity_id=aid,
                    direction=g['direction'],
                    coordinates=[tuple(p) for p in r['coordinates']],
                    distance=float(r.get('distance') or 0.0),
                    duration=int(r.get('duration') or 0),
                    elevation_gain=float(r.get('elevation_gain') or 0.0),
                    timestamp=r.get('timestamp') or '',
                    average_speed=float(r.get('average_speed') or 0.0),
                )
                stored[aid] = g['id']
    order = [int(a) for a in data.get('activity_ids', []) if int(a) in rides]
    order += [a for a in rides if a not in set(order)]
    return rides, stored, order, hashlib.sha1(raw).hexdigest()


def _iter_groups(route_groups):
    # Snapshots store either {direction: [group, ...]} or a flat [group, ...].
    if isinstance(route_groups, dict):
        yield from route_groups.values()
    else:
        yield route_groups


def make_route(ride):
    from src.route_analyzer import Route
    r = Route(**ride)
    r.compute_geometry()
    return r


def make_analyzer(config, cache_dir, n_workers=1, stop_check=None):
    from src.location_finder import Location
    from src.route_analyzer import RouteAnalyzer
    home = Location(lat=0.0, lon=0.0, name='Home', activity_count=0)
    work = Location(lat=0.0, lon=0.0, name='Work', activity_count=0)
    return RouteAnalyzer([], home, work, config, n_workers=n_workers,
                         force_reanalysis=True, cache_dir=cache_dir,
                         enable_geocoding=False, stop_check=stop_check)


def load_app_config(overrides=None):
    """config/config.yaml with optional {dotted.key: value} overrides (--set)."""
    from src.config_manager import ConfigManager
    config = ConfigManager(str(REPO / 'config' / 'config.yaml'))
    for key, value in (overrides or {}).items():
        config.set(key, value)
    return config


def parse_overrides(pairs):
    import yaml
    out = {}
    for item in pairs or []:
        key, sep, value = item.partition('=')
        if not sep:
            raise SystemExit(f'--set expects key=value, got {item!r}')
        out[key.strip()] = yaml.safe_load(value)
    return out


# ---------------------------------------------------------------- pool workers

_W = {}


def _init_worker(snapshot_path, lat0, want_app, overrides=None):
    rides, _, _, _ = load_snapshot(snapshot_path)
    _W['tracks'] = {a: reference.Track(r['coordinates'], lat0) for a, r in rides.items()}
    if want_app:
        _W['routes'] = {a: make_route(r) for a, r in rides.items()}
        _W['tmp'] = tempfile.mkdtemp(prefix='matchbench_')
        _W['analyzer'] = make_analyzer(load_app_config(overrides), _W['tmp'])


def _ref_pair(pair):
    a, b = pair
    return a, b, reference.compare(_W['tracks'][a], _W['tracks'][b])


def _app_pair(pair):
    a, b = pair
    an, ra, rb = _W['analyzer'], _W['routes'][a], _W['routes'][b]
    passed = an._passes_geometric_filter(ra, rb)
    return a, b, int(passed), (an.calculate_route_similarity(ra, rb) if passed else 0.0)


# ---------------------------------------------------------------- metrics

def pair_key(a, b):
    return (a, b) if a < b else (b, a)


def partition_metrics(partition, ref, rides):
    """Score a {activity_id: group_id} partition against reference pair labels."""
    groups = defaultdict(list)
    for aid, gid in partition.items():
        groups[gid].append(aid)
    within = Counter()
    for k, m in ref.items():
        if partition.get(k[0]) is not None and partition.get(k[0]) == partition.get(k[1]):
            within[m['label']] += 1
    total_same = sum(1 for m in ref.values() if m['label'] == 'same')
    n_within = sum(within.values())
    merge_pairs = {tuple(sorted((str(partition.get(a)), str(partition.get(b)))))
                   for (a, b), m in ref.items()
                   if m['label'] == 'same' and partition.get(a) != partition.get(b)}
    out = dict(
        groups=len(groups),
        singletons=sum(1 for g in groups.values() if len(g) == 1),
        unassigned_rides=len(rides) - len(partition),
        within_pairs=n_within,
        within_same=within['same'], within_diff=within['diff'], within_ambig=within['ambig'],
        purity=within['same'] / n_within if n_within else 1.0,
        precision_excl_ambig=(within['same'] / (within['same'] + within['diff'])
                              if within['same'] + within['diff'] else 1.0),
        pair_recall=within['same'] / total_same if total_same else 1.0,
        group_pairs_that_should_merge=len(merge_pairs),
        by_direction={},
    )
    for d in DIRECTIONS:
        sizes = sorted((len(g) for g in groups.values() if rides[g[0]]['direction'] == d), reverse=True)
        out['by_direction'][d] = dict(groups=len(sizes), largest=sizes[:5])
    out['reference_clusters'] = reference_cluster_splits(partition, ref, rides)
    return out


def reference_components(ref, rides):
    """Connected components of 'same' edges per direction, largest first."""
    parent = {a: a for a in rides}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for (a, b), m in ref.items():
        if m['label'] == 'same':
            parent[find(a)] = find(b)
    comps = defaultdict(list)
    for a in rides:
        comps[find(a)].append(a)
    return sorted(comps.values(), key=len, reverse=True)


def reference_cluster_splits(partition, ref, rides, top=3):
    out = {}
    comps = reference_components(ref, rides)
    for d in DIRECTIONS:
        rows = []
        for c in [c for c in comps if rides[c[0]]['direction'] == d][:top]:
            rows.append(dict(rides=len(c), split_across_groups=len({partition.get(a) for a in c})))
        out[d] = rows
    return out


def adjusted_rand(p1, p2, keys):
    from math import comb
    cont = Counter((p1[k], p2[k]) for k in keys)
    a = Counter(p1[k] for k in keys)
    b = Counter(p2[k] for k in keys)
    s_ij = sum(comb(n, 2) for n in cont.values())
    s_a = sum(comb(n, 2) for n in a.values())
    s_b = sum(comb(n, 2) for n in b.values())
    expected = s_a * s_b / comb(len(keys), 2)
    max_idx = (s_a + s_b) / 2
    return 1.0 if max_idx == expected else (s_ij - expected) / (max_idx - expected)


def auc_and_best_f1(scores, y):
    """AUC (rank formula, ties averaged) and best-F1 threshold for score >= t."""
    scores, y = np.asarray(scores, float), np.asarray(y, int)
    n1, n0 = y.sum(), len(y) - y.sum()
    if n1 == 0 or n0 == 0:
        return None, None, None
    order = np.argsort(scores, kind='mergesort')
    ranks = np.empty(len(scores))
    s_sorted = scores[order]
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    auc = (ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    desc = np.argsort(-scores, kind='mergesort')
    tp = np.cumsum(y[desc])
    fp = np.cumsum(1 - y[desc])
    f1 = 2 * tp / (tp + fp + n1)
    last_of_tie = np.append(scores[desc][1:] != scores[desc][:-1], True)
    f1 = np.where(last_of_tie, f1, -1)
    k = int(np.argmax(f1))
    return float(auc), float(f1[k]), float(scores[desc][k])


def precision_recall_at(scores, y, threshold):
    pred = np.asarray(scores) >= threshold
    y = np.asarray(y, bool)
    tp, fp, fn = (pred & y).sum(), (pred & ~y).sum(), (~pred & y).sum()
    return dict(precision=float(tp / max(1, tp + fp)), recall=float(tp / max(1, tp + fn)))


CAL_BINS = [0, 25, 50, 75, 100, 150, 250, 500, 1000, float('inf')]
# RouteAnalyzer.calculate_route_similarity returns a score where >= 1.0 is a match (#613).
APP_MATCH_SCORE = 1.0


def calibration(ref, app, threshold):
    rows = []
    for lo, hi in zip(CAL_BINS[:-1], CAL_BINS[1:]):
        ks = [k for k, m in ref.items() if lo <= m['dev_p95'] < hi]
        if not ks:
            continue
        sc = [app[k][1] for k in ks]
        rows.append(dict(p95_from_m=lo, p95_to_m=hi, pairs=len(ks),
                         share_same=sum(ref[k]['label'] == 'same' for k in ks) / len(ks),
                         median_app_score=float(np.median(sc)),
                         share_app_match=float(np.mean(np.asarray(sc) >= threshold))))
    keys = list(ref)
    s = [app[k][1] for k in keys]
    y_strict = [ref[k]['label'] == 'same' for k in keys]
    keys_clean = [k for k in keys if ref[k]['label'] != 'ambig']
    s_clean = [app[k][1] for k in keys_clean]
    y_clean = [ref[k]['label'] == 'same' for k in keys_clean]
    auc, f1, f1_at = auc_and_best_f1(s, y_strict)
    auc_c, f1_c, f1_at_c = auc_and_best_f1(s_clean, y_clean)
    same = [k for k in keys if ref[k]['label'] == 'same']
    return dict(
        bins=rows,
        ambig_as_diff=dict(auc=auc, best_f1=f1, best_f1_at_score=f1_at,
                           at_app_threshold=precision_recall_at(s, y_strict, threshold)),
        ambig_excluded=dict(auc=auc_c, best_f1=f1_c, best_f1_at_score=f1_at_c),
        prefilter_rejects_same=sum(1 for k in same if not app[k][0]),
        same_pairs=len(same),
    )


# ---------------------------------------------------------------- app grouping

def run_app_grouping(rides, order, config, cache_dir, n_workers):
    routes = [make_route(rides[a]) for a in order]
    analyzer = make_analyzer(config, cache_dir, n_workers=n_workers)
    groups = analyzer.group_similar_routes(routes)
    partition = {}
    for g in groups:
        for r in g.routes:
            partition[int(r.activity_id)] = g.id
    rule = dict(max_p95_deviation_m=analyzer.max_p95_deviation_m, min_coverage=analyzer.min_coverage)
    return partition, rule


# ---------------------------------------------------------------- report

def fmt_partition(name, m):
    d = m['by_direction']
    clusters = '; '.join(
        f"{di.split('_')[0]}→{di.split('_')[-1]}: " + ', '.join(
            f"{c['rides']} rides in {c['split_across_groups']} groups" for c in rows)
        for di, rows in m['reference_clusters'].items())
    return '\n'.join([
        f"  {name}",
        f"    groups {m['groups']} (singletons {m['singletons']}), unassigned rides {m['unassigned_rides']}",
        f"    largest groups  h→w {d['home_to_work']['largest']}  w→h {d['work_to_home']['largest']}",
        f"    within-group pairs {m['within_pairs']}: same {m['within_same']}, ambig {m['within_ambig']}, "
        f"DIFFERENT {m['within_diff']}",
        f"    purity {m['purity']:.3f}  precision(excl ambig) {m['precision_excl_ambig']:.3f}  "
        f"pair recall {m['pair_recall']:.3f}",
        f"    group pairs that should merge {m['group_pairs_that_should_merge']}",
        f"    biggest reference routes → {clusters}",
    ])


HEADLINE = [('app_current', 'pair_recall'), ('app_current', 'purity'), ('app_current', 'groups'),
            ('app_current', 'singletons'), ('app_current', 'within_diff'),
            ('order_stability', 'min_ari')]


def print_report(s, baseline=None):
    print('\n================ ROUTE MATCHING BENCHMARK ================')
    c = s['corpus']
    print(f"snapshot {c['snapshot_sha1'][:12]}  rides {c['rides']}  pairs {c['pairs']}  "
          f"reference labels {c['labels']}  (reference v{c['reference_version']})")
    print(f"app match rule {s['app_match_rule']} (pairwise score >= {APP_MATCH_SCORE} matches)")
    print('\n-- Grouping vs reference --')
    print(fmt_partition('APP (current code, snapshot order)', s['app_current']))
    print(fmt_partition('SNAPSHOT (stored grouping, historical)', s['snapshot_stored']))
    o = s['order_stability']
    print(f"\n-- Order stability ({o['shuffles']} shuffles) --\n"
          f"  group counts {o['group_counts']}  ARI vs snapshot order: min {o['min_ari']:.3f}  "
          f"median {o['median_ari']:.3f}")
    cal = s.get('calibration')
    if cal:
        print('\n-- Calibration: app pairwise score vs reference p95 deviation --')
        print(f"  {'p95 (m)':>14} {'pairs':>6} {'same':>6} {'med score':>10} {'pass thr':>9}")
        for r in cal['bins']:
            hi = '∞' if r['p95_to_m'] == float('inf') else f"{r['p95_to_m']:.0f}"
            print(f"  {r['p95_from_m']:>6.0f}–{hi:<7} {r['pairs']:>6} {r['share_same']:>6.2f} "
                  f"{r['median_app_score']:>10.3f} {r['share_app_match']:>9.1%}")
        a, e = cal['ambig_as_diff'], cal['ambig_excluded']
        print(f"  ambig counted as diff: AUC {a['auc']:.4f}  best F1 {a['best_f1']:.3f} at score ≥ "
              f"{a['best_f1_at_score']:.3f}  |  at app threshold: P {a['at_app_threshold']['precision']:.3f} "
              f"R {a['at_app_threshold']['recall']:.3f}")
        print(f"  ambig excluded:        AUC {e['auc']:.4f}  best F1 {e['best_f1']:.3f} at score ≥ "
              f"{e['best_f1_at_score']:.3f}")
        print(f"  prefilter rejected {cal['prefilter_rejects_same']} of {cal['same_pairs']} reference-same pairs")
    if baseline:
        print('\n-- Change vs baseline --')
        for section, key in HEADLINE:
            old = baseline.get(section, {}).get(key)
            new = s.get(section, {}).get(key)
            if old is None or new is None:
                continue
            print(f"  {section}.{key:<14} {old:>8.3f} → {new:>8.3f}" if isinstance(new, float)
                  else f"  {section}.{key:<14} {old:>8} → {new:>8}")
    print(f"\n({s['elapsed_s']:.0f}s)")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--snapshot', default=str(REPO / 'data' / 'route_groups.json'),
                    help='route_groups.json snapshot (default: data/route_groups.json)')
    ap.add_argument('--out', default=str(REPO / 'data' / 'cache' / 'matching_benchmark'),
                    help='output dir (keep it gitignored)')
    ap.add_argument('--workers', type=int, default=os.cpu_count() or 4,
                    help='processes for pairwise reference/calibration scoring')
    ap.add_argument('--app-workers', type=int, default=8,
                    help='RouteAnalyzer n_workers for the grouping runs (1-8)')
    ap.add_argument('--shuffles', type=int, default=3, help='shuffled-order regrouping runs')
    ap.add_argument('--skip-calibration', action='store_true',
                    help='skip scoring every pair with the app (the slowest step)')
    ap.add_argument('--baseline', help='previous summary.json to diff headline numbers against')
    ap.add_argument('--set', action='append', metavar='KEY=VALUE',
                    help='override a config.yaml value for this run, e.g. '
                         '--set route_analysis.max_p95_deviation_m=75 (repeatable)')
    args = ap.parse_args()
    overrides = parse_overrides(args.set)
    # RouteAnalyzer prints emoji progress lines; a cp1252 Windows console can't encode them.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding='utf-8', errors='replace')

    t0 = time.time()
    # Read before summary.json is overwritten (the baseline is often the previous run).
    baseline = json.loads(Path(args.baseline).read_text()) if args.baseline else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    snapshot = str(Path(args.snapshot).resolve())
    rides, stored, order, sha = load_snapshot(snapshot)
    pairs = [pair_key(a, b) for i, a in enumerate(order) for b in order[i + 1:]
             if rides[a]['direction'] == rides[b]['direction']]
    lat0 = float(np.mean([p[0] for r in rides.values() for p in r['coordinates']]))
    print(f'{len(rides)} rides, {len(pairs)} same-direction pairs', flush=True)

    # Reference labels: cached per snapshot + reference version.
    ref_cache = out / f'reference_v{reference.REFERENCE_VERSION}_{sha[:12]}.json'
    if ref_cache.exists():
        ref = {pair_key(int(a), int(b)): m for a, b, m in json.loads(ref_cache.read_text())}
        print(f'reference: loaded {len(ref)} cached pair labels', flush=True)
    else:
        print('reference: computing pair labels...', flush=True)
        with Pool(args.workers, initializer=_init_worker, initargs=(snapshot, lat0, False)) as pool:
            rows = pool.map(_ref_pair, pairs, chunksize=64)
        ref = {pair_key(a, b): m for a, b, m in rows}
        ref_cache.write_text(json.dumps([[a, b, m] for (a, b), m in ref.items()]))
    labels = Counter(m['label'] for m in ref.values())

    config = load_app_config(overrides)
    app = None
    if not args.skip_calibration:
        print('calibration: scoring every pair with the app (slow)...', flush=True)
        with Pool(args.workers, initializer=_init_worker, initargs=(snapshot, lat0, True, overrides)) as pool:
            rows = pool.map(_app_pair, pairs, chunksize=16)
        app = {pair_key(a, b): (p, s) for a, b, p, s in rows}

    print('grouping: running RouteAnalyzer.group_similar_routes...', flush=True)
    with tempfile.TemporaryDirectory(prefix='matchbench_') as tmp:
        cache_dir = Path(tmp) / 'cache'
        current, rule = run_app_grouping(rides, order, config, cache_dir, args.app_workers)
        rng = random.Random(611)
        shuffled = []
        for _ in range(args.shuffles):
            o = order[:]
            rng.shuffle(o)
            shuffled.append(run_app_grouping(rides, o, config, cache_dir, args.app_workers)[0])

    keys = sorted(rides)
    aris = [adjusted_rand(current, p, keys) for p in shuffled
            if set(p) == set(current)]
    summary = dict(
        corpus=dict(snapshot_sha1=sha, rides=len(rides), pairs=len(pairs), labels=dict(labels),
                    reference_version=reference.REFERENCE_VERSION),
        app_match_rule=rule,
        app_current=partition_metrics(current, ref, rides),
        snapshot_stored=partition_metrics(stored, ref, rides),
        order_stability=dict(shuffles=len(shuffled),
                             group_counts=[len(set(current.values()))] + [len(set(p.values())) for p in shuffled],
                             min_ari=min(aris) if aris else 1.0,
                             median_ari=float(np.median(aris)) if aris else 1.0),
    )
    if app is not None:
        summary['calibration'] = calibration(ref, app, APP_MATCH_SCORE)
        with open(out / 'pairs.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['activity_a', 'activity_b', 'direction', 'label', 'cov_min', 'dev_p95',
                        'dev_median', 'start_gap_m', 'end_gap_m', 'len_ratio',
                        'app_prefilter', 'app_score', 'app_same_group'])
            for (a, b), m in ref.items():
                w.writerow([a, b, rides[a]['direction'], m['label'], round(m['cov_min'], 4),
                            round(m['dev_p95'], 1), round(m['dev_median'], 1), round(m['start_gap_m']),
                            round(m['end_gap_m']), round(m['len_ratio'], 3), app[(a, b)][0],
                            round(app[(a, b)][1], 4), int(current.get(a) == current.get(b))])
    summary['elapsed_s'] = time.time() - t0
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))

    print_report(summary, baseline)
    print(f'wrote {out / "summary.json"}')


if __name__ == '__main__':
    main()
