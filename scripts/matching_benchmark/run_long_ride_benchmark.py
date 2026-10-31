"""
Long-ride matching benchmark (#615).

The long-ride counterpart of run_benchmark.py: measures how well the app's
LongRideAnalyzer grouping agrees with the independent reference (reference.py)
on a local copy of real activities.

    python scripts/matching_benchmark/run_long_ride_benchmark.py \
        --activities data/cache/matching_benchmark/activities.json \
        --commute-ids data/cache/matching_benchmark/commute_ids.json

What it does:
  1. Loads activities.json and picks the long rides the way the app does
     (LongRideAnalyzer.classify_activities), excluding the commute IDs given.
  2. Labels ride pairs with the reference: same / diff / ambig, plus "part of"
     (one ride lies along the other). Pairs the reference's exact screen rules
     out are 'diff'. Cached per input, since it doesn't depend on app code.
  3. Runs the app's real LongRideAnalyzer.group_similar_rides in a temp
     working directory (no shared cache), in input order and shuffled orders.
  4. Prints purity / recall / group counts / name checks / links / order
     stability and writes summary_long.json to --out.

PRIVACY: the repo is public. Printed output and summary_long.json contain no
coordinates, ride names or Strava activity IDs. Keep the inputs under the
gitignored data/cache/ directory.
"""
import argparse
import hashlib
import json
import os
import random
import sys
import tempfile
import time
from collections import Counter, OrderedDict, defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import polyline

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reference  # noqa: E402
from run_benchmark import adjusted_rand, load_app_config, parse_overrides  # noqa: E402

DEFAULT_DIR = REPO / 'data' / 'cache' / 'matching_benchmark'


# ---------------------------------------------------------------- corpus

def load_long_rides(activities_path, commute_ids_path, config):
    from src.data_fetcher import Activity
    from src.long_ride_analyzer import LongRideAnalyzer
    raw = Path(activities_path).read_bytes()
    data = json.loads(raw)
    acts = [Activity.from_dict(a) for a in (data['activities'] if isinstance(data, dict) else data)]
    commute_raw = Path(commute_ids_path).read_bytes() if commute_ids_path else b'[]'
    commute_ids = set(json.loads(commute_raw))
    commutes = [a for a in acts if a.id in commute_ids]
    _, long_rides = LongRideAnalyzer(acts, config).classify_activities(commutes)
    long_rides.sort(key=lambda a: a.id)
    sha = hashlib.sha1(raw + commute_raw).hexdigest()
    return long_rides, sha


def normalized_name(name):
    return ' '.join((name or '').lower().split())


# ---------------------------------------------------------------- reference

_W = {}
LRU_TRACKS = 600


def _init_ref_worker(coords_list, lat0):
    _W['coords'], _W['lat0'], _W['tracks'] = coords_list, lat0, OrderedDict()


def _track(k):
    tracks = _W['tracks']
    if k in tracks:
        tracks.move_to_end(k)
    else:
        tracks[k] = reference.Track(_W['coords'][k], _W['lat0'])
        if len(tracks) > LRU_TRACKS:
            tracks.popitem(last=False)
    return tracks[k]


def _ref_chunk(chunk):
    return [(i, j, reference.compare_long(_track(i), _track(j))) for i, j in chunk]


def reference_labels(rides, sha, out, workers):
    path = out / f'reference_long_v{reference.LONG_REFERENCE_VERSION}_{sha[:12]}.json'
    ids = [a.id for a in rides]
    if path.exists():
        rows = json.loads(path.read_text())
        print(f'reference: loaded {len(rows)} cached pair labels', flush=True)
    else:
        coords = [np.array(polyline.decode(a.polyline), dtype=float) for a in rides]
        lat0 = float(np.mean(np.concatenate([c[:, 0] for c in coords])))
        t = time.time()
        cand = reference.long_ride_candidates(coords, lat0)
        print(f'reference: {len(cand)} candidate pairs of {len(rides) * (len(rides) - 1) // 2} '
              f'({time.time() - t:.0f}s); comparing...', flush=True)
        chunks = [cand[k:k + 500] for k in range(0, len(cand), 500)]
        with Pool(workers, initializer=_init_ref_worker, initargs=(coords, lat0)) as pool:
            rows = [[ids[i], ids[j], m] for res in pool.imap(_ref_chunk, chunks) for i, j, m in res]
        path.write_text(json.dumps(rows))
    ref = {}
    for a, b, m in rows:
        if a > b:  # keep keys ordered; flip the directed part
            a, b = b, a
            m = dict(m, part_of={'a_in_b': 'b_in_a', 'b_in_a': 'a_in_b'}.get(m['part_of'], ''))
        ref[(a, b)] = m
    return ref


# ---------------------------------------------------------------- app

def run_app(rides, config, order_seed=None, app_cache=None):
    """Group with the app's LongRideAnalyzer in a fresh temp working dir, so
    nothing touches the real cache. Its cache/ starts empty unless app_cache
    (a directory kept between runs) is given. Returns
    (partition {activity_id: group key}, links [(part, whole)], seconds)."""
    from src.long_ride_analyzer import LongRideAnalyzer
    rs = list(rides)
    if order_seed is not None:
        random.Random(order_seed).shuffle(rs)
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory(prefix='longbench_') as tmp:
        os.chdir(app_cache or tmp)
        try:
            t = time.time()
            groups = LongRideAnalyzer(rs, config).group_similar_rides(rs)
            elapsed = time.time() - t
        finally:
            os.chdir(cwd)
    partition, links = {}, []
    for g in groups:
        for aid in (g.activity_ids or [g.activity_id]):
            partition[int(aid)] = g.activity_id
        for whole in getattr(g, 'part_of', None) or []:
            links.append((g.activity_id, whole))
    return partition, links, elapsed


# ---------------------------------------------------------------- metrics

def partition_metrics(partition, ref, rides):
    names = {a.id: normalized_name(a.name) for a in rides}
    groups = defaultdict(list)
    for aid, gid in partition.items():
        groups[gid].append(aid)
    within = Counter()
    same_name_diff = 0
    for members in groups.values():
        members = sorted(members)
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                a, b = members[x], members[y]
                lab = ref.get((a, b), {}).get('label', 'diff')
                within[lab] += 1
                if lab == 'diff' and names[a] and names[a] == names[b]:
                    same_name_diff += 1
    same_pairs = [k for k, m in ref.items() if m['label'] == 'same']
    recalled = sum(1 for a, b in same_pairs if partition.get(a) == partition.get(b))
    n_within = sum(within.values())
    # Same-named rides the reference calls diff (unscreened pairs are diff too):
    # the name alone mustn't merge them.
    by_name = defaultdict(list)
    for aid, nm in names.items():
        if nm:
            by_name[nm].append(aid)
    same_name_diff_pairs = 0
    for members in by_name.values():
        members.sort()
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                if ref.get((members[x], members[y]), {}).get('label', 'diff') == 'diff':
                    same_name_diff_pairs += 1
    sizes = sorted((len(g) for g in groups.values()), reverse=True)
    return dict(
        groups=len(groups),
        singletons=sum(1 for s in sizes if s == 1),
        largest=sizes[:8],
        unassigned_rides=len(rides) - len(partition),
        within_pairs=n_within, within_same=within['same'], within_ambig=within['ambig'],
        within_diff=within['diff'],
        purity=within['same'] / n_within if n_within else 1.0,
        precision_excl_ambig=(within['same'] / (within['same'] + within['diff'])
                              if within['same'] + within['diff'] else 1.0),
        pair_recall=recalled / len(same_pairs) if same_pairs else 1.0,
        same_name_diff_grouped=same_name_diff,
        same_name_diff_pairs_seen=same_name_diff_pairs,
    )


def link_metrics(partition, links, ref):
    """Reference part-of relations between rides in different groups, and how
    many of those group pairs the app links (part -> whole)."""
    wanted = set()
    for (a, b), m in ref.items():
        part, whole = {'a_in_b': (a, b), 'b_in_a': (b, a)}.get(m['part_of'], (None, None))
        if part is None or partition.get(part) == partition.get(whole):
            continue
        wanted.add((partition.get(part), partition.get(whole)))
    got = set(links)
    return dict(reference_group_links=len(wanted), app_links=len(got),
                recalled=len(wanted & got),
                link_recall=len(wanted & got) / len(wanted) if wanted else 1.0,
                link_precision=len(wanted & got) / len(got) if got else 1.0)


# ---------------------------------------------------------------- main

def fmt(m):
    return '\n'.join([
        f"    groups {m['groups']} (singletons {m['singletons']}), largest {m['largest']}, "
        f"unassigned rides {m['unassigned_rides']}",
        f"    within-group pairs {m['within_pairs']}: same {m['within_same']}, ambig {m['within_ambig']}, "
        f"DIFFERENT {m['within_diff']}",
        f"    purity {m['purity']:.3f}  precision(excl ambig) {m['precision_excl_ambig']:.3f}  "
        f"pair recall {m['pair_recall']:.3f}",
        f"    same-name rides on different geometry: {m['same_name_diff_grouped']} pairs grouped "
        f"(of {m['same_name_diff_pairs_seen']} such pairs)",
    ])


HEADLINE = ['pair_recall', 'purity', 'precision_excl_ambig', 'groups', 'singletons',
            'within_diff', 'same_name_diff_grouped']


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--activities', default=str(DEFAULT_DIR / 'activities.json'))
    ap.add_argument('--commute-ids', default=str(DEFAULT_DIR / 'commute_ids.json'),
                    help='JSON list of commute activity IDs to exclude (empty string: none)')
    ap.add_argument('--out', default=str(DEFAULT_DIR))
    ap.add_argument('--workers', type=int, default=os.cpu_count() or 4)
    ap.add_argument('--shuffles', type=int, default=1, help='shuffled-order regrouping runs')
    ap.add_argument('--app-cache',
                    help="keep the app's pair-metrics cache in this directory between runs "
                         "(the metrics don't depend on thresholds, so a --set sweep reuses them)")
    ap.add_argument('--baseline', help='previous summary_long.json to diff headline numbers against')
    ap.add_argument('--set', action='append', metavar='KEY=VALUE',
                    help='override a config.yaml value for this run (repeatable)')
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding='utf-8', errors='replace')

    t0 = time.time()
    baseline = json.loads(Path(args.baseline).read_text()) if args.baseline else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    config = load_app_config(parse_overrides(args.set))
    rides, sha = load_long_rides(args.activities, args.commute_ids or None, config)
    print(f'{len(rides)} long rides', flush=True)
    ref = reference_labels(rides, sha, out, args.workers)
    labels = Counter(m['label'] for m in ref.values())
    part_of = sum(1 for m in ref.values() if m['part_of'])

    print('grouping: running LongRideAnalyzer.group_similar_rides...', flush=True)
    app_cache = str(Path(args.app_cache).resolve()) if args.app_cache else None
    if app_cache:
        Path(app_cache).mkdir(parents=True, exist_ok=True)
    current, links, seconds = run_app(rides, config, app_cache=app_cache)
    shuffled = [run_app(rides, config, order_seed=615 + k, app_cache=app_cache)[0]
                for k in range(args.shuffles)]
    keys = sorted(current)
    aris = [adjusted_rand(current, p, keys) for p in shuffled if set(p) == set(current)]

    summary = dict(
        corpus=dict(sha1=sha, rides=len(rides), screened_pairs=len(ref), labels=dict(labels),
                    part_of_pairs=part_of, reference_version=reference.LONG_REFERENCE_VERSION),
        app=partition_metrics(current, ref, rides),
        links=link_metrics(current, links, ref),
        order_stability=dict(shuffles=len(shuffled), min_ari=min(aris) if aris else 1.0,
                             group_counts=[len(set(current.values()))] +
                                          [len(set(p.values())) for p in shuffled]),
        grouping_seconds=seconds,
        overrides=parse_overrides(args.set),
    )
    summary['elapsed_s'] = time.time() - t0
    (out / 'summary_long.json').write_text(json.dumps(summary, indent=2))

    c = summary['corpus']
    print('\n================ LONG-RIDE MATCHING BENCHMARK ================')
    print(f"input {c['sha1'][:12]}  rides {c['rides']}  screened pairs {c['screened_pairs']}  "
          f"labels {c['labels']}  part-of {c['part_of_pairs']}  (reference v{c['reference_version']})")
    print('  APP (current code)')
    print(fmt(summary['app']))
    lk = summary['links']
    print(f"    links: {lk['app_links']} made, reference wants {lk['reference_group_links']} group links; "
          f"recall {lk['link_recall']:.3f} precision {lk['link_precision']:.3f}")
    o = summary['order_stability']
    print(f"  order stability: group counts {o['group_counts']}, min ARI {o['min_ari']:.3f}")
    print(f"  grouping took {seconds:.0f}s ({'--app-cache' if app_cache else 'cold cache'})")
    if baseline:
        print('\n-- Change vs baseline --')
        for key in HEADLINE:
            old, new = baseline['app'].get(key), summary['app'].get(key)
            if old is not None and new is not None:
                print(f"  {key:<24} {old:>8.3f} → {new:>8.3f}" if isinstance(new, float)
                      else f"  {key:<24} {old:>8} → {new:>8}")
    print(f"\n({summary['elapsed_s']:.0f}s)  wrote {out / 'summary_long.json'}")


if __name__ == '__main__':
    main()
