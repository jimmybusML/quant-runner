#!/usr/bin/env python3
"""Reconcile the exact frozen M8 replay to the requested 18,374-FID scope.

This script consumes the SHA-anchored full-path research outputs from the
current Crown snapshot, restricts them to the original expanded schedule
inventory, calls the frozen assign_exact_group/group_side helpers directly,
and rebuilds the settled ledger and all aggregates. It does not access or
modify production systems.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import importlib.util
import json
import math
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ROOT = Path(__file__).resolve().parents[4]
FROZEN = Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
ORIGINAL_COVERAGE = BASE / 'exact_rule_cross_league_coverage.jsonl'
ORIGINAL_ORDERS = BASE / 'exact_rule_cross_league_orders.jsonl.gz'
FULL_PATHS = OUT / 'full_union_complete_paths_20261122.jsonl.gz'
FULL_ORDERS = OUT / 'full_union_orders_20261122.jsonl.gz'
FULL_COVERAGE = OUT / 'full_union_coverage_20261122.jsonl.gz'
FULL_VERIFICATION = OUT / 'full_union_independent_settlement_20261122.jsonl.gz'
FULL_SUMMARY = OUT / 'full_union_summary_20261122.json'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path: Path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_jsonl_gz(path: Path, rows):
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as gz:
            for row in rows:
                gz.write((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode())


def sgn(value, eps=1e-9):
    return 1 if value > eps else -1 if value < -eps else 0


def iso_week(day_string: str) -> str:
    d = date.fromisoformat(day_string[:10])
    x = d.isocalendar()
    return f'{x.year}-W{x.week:02d}'


def iso_week_span(rows):
    if not rows:
        return []
    lo = min(date.fromisoformat(str(row['date'])[:10]) for row in rows)
    hi = max(date.fromisoformat(str(row['date'])[:10]) for row in rows)
    current = lo - timedelta(days=lo.weekday())
    last = hi - timedelta(days=hi.weekday())
    weeks = []
    while current <= last:
        weeks.append(iso_week(current.isoformat()))
        current += timedelta(days=7)
    return weeks


def drawdown(rows):
    daily = collections.defaultdict(float)
    for row in rows:
        daily[str(row['date'])[:10]] += float(row['net_u'])
    balance = peak = mdd = 0.0
    for _, pnl in sorted(daily.items()):
        balance += pnl
        peak = max(peak, balance)
        mdd = max(mdd, peak - balance)
    return round(mdd, 6)


def stats(rows):
    n = len(rows)
    net = sum(float(row['net_u']) for row in rows)
    settlements = collections.Counter(row['settlement'] for row in rows)
    odds = [float(row.get('price', row.get('selected_odds'))) for row in rows]
    return {
        'orders': n,
        'net_u': round(net, 6),
        'roi_pct': round(100 * net / n, 6) if n else None,
        'mdd_u': drawdown(rows),
        'average_decimal_odds': round(sum(odds) / len(odds), 6) if odds else None,
        'settlements': {k: settlements.get(k, 0) for k in ('full_win', 'half_win', 'push', 'half_loss', 'full_loss')},
    }


def main():
    helper_path = ROOT / 'research/m8/m8_frozen_eight_boundary_expansion_20261119.py'
    spec = importlib.util.spec_from_file_location('m8_frozen_exact_helpers', helper_path)
    helper = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(helper)

    scope_rows = read_jsonl(ORIGINAL_COVERAGE)
    scope_fids = {str(row['fid']) for row in scope_rows}
    assert len(scope_rows) == 18_374 and len(scope_fids) == 18_374

    frozen_rows = read_jsonl(FROZEN)
    frozen = {str(row['fid']): row for row in frozen_rows}
    assert len(frozen) == 10_294 and round(sum(float(x['pnl']) for x in frozen_rows), 3) == 236.015
    assert not scope_fids.intersection(frozen)

    path_rows_all = read_jsonl(FULL_PATHS)
    path_rows = {str(row['fid']): row for row in path_rows_all if str(row['fid']) in scope_fids}
    assert len(path_rows) == 6_967
    group_mismatches = []
    side_mismatches = []
    e_side_fallbacks = []
    for fid, row in path_rows.items():
        expected_group = helper.assign_exact_group(row)
        if expected_group != row.get('group'):
            group_mismatches.append({'fid': fid, 'stored': row.get('group'), 'helper': expected_group})
            continue
        expected_side = helper.group_side(expected_group, row) if expected_group else None
        if expected_group == 'E' and expected_side is None:
            a = sgn(float(row['p3']) - float(row['p0']))
            b = sgn(float(row['p1']) - float(row['p3']))
            net = sgn(float(row['p1']) - float(row['p0']))
            movement = net or a or b or sgn(float(row.get('last_move') or 0))
            expected_side = ('away' if movement > 0 else 'home') if movement else None
            e_side_fallbacks.append(fid)
        if expected_side != row.get('side'):
            side_mismatches.append({'fid': fid, 'group': expected_group, 'stored': row.get('side'), 'helper_or_frozen_fallback': expected_side})

    full_orders = read_jsonl(FULL_ORDERS)
    full_orders_by_fid = {str(row['fid']): row for row in full_orders}
    assert len(full_orders_by_fid) == len(full_orders) == 1_273
    scoped_orders = [dict(row) for row in full_orders if str(row['fid']) in scope_fids]
    scoped_orders.sort(key=lambda row: (str(row['date']), str(row['fid'])))
    assert len(scoped_orders) == len({str(row['fid']) for row in scoped_orders}) == 1_271
    assert not ({str(row['fid']) for row in scoped_orders} & set(frozen))
    for row in scoped_orders:
        feature = path_rows[str(row['fid'])]
        assert row['group'] == feature['group'] and row['side'] == feature['side']
        assert helper.assign_exact_group(feature) == row['group']

    group_order = ('base', 'A', 'B', 'C', 'D', 'E', 'F', 'G')
    by_group = {g: stats([x for x in scoped_orders if x['group'] == g]) for g in group_order}
    by_group_year = {
        g: {str(y): stats([x for x in scoped_orders if x['group'] == g and int(x['year']) == y])
            for y in sorted({int(x['year']) for x in scoped_orders})}
        for g in group_order
    }
    by_group_league = {
        g: {str(lid): stats([x for x in scoped_orders if x['group'] == g and str(x['league']) == str(lid)])
            for lid in sorted({str(x['league']) for x in scoped_orders if x['group'] == g})}
        for g in group_order
    }
    scoped_coverage = [x for x in read_jsonl(FULL_COVERAGE) if str(x['fid']) in scope_fids]
    assert len(scoped_coverage) == 18_374
    league_ids = sorted({str(x.get('league_id', x.get('league'))) for x in scoped_coverage})
    by_league = {lid: stats([x for x in scoped_orders if str(x['league']) == lid]) for lid in league_ids}
    by_year = {str(y): stats([x for x in scoped_orders if int(x['year']) == y])
               for y in sorted({int(x['year']) for x in scoped_orders})}

    coverage_status = collections.Counter(x['status'] for x in scoped_coverage)
    coverage_by_league = {}
    coverage_by_year = {}
    for row in scoped_coverage:
        lid = str(row.get('league_id', row.get('league')))
        year = str(row.get('year'))
        coverage_by_league.setdefault(lid, collections.Counter())[row['status']] += 1
        coverage_by_year.setdefault(year, collections.Counter())[row['status']] += 1
    complete_path_rows = [x for x in path_rows.values()]
    obs_weeks = iso_week_span(complete_path_rows)
    weeks_by_year = {str(y): iso_week_span([x for x in complete_path_rows if int(x['year']) == y])
                     for y in sorted({int(x['year']) for x in complete_path_rows})}
    weekly = {week: {'orders': 0, 'net_u': 0.0} for week in obs_weeks}
    for row in scoped_orders:
        w = iso_week(row['date'])
        weekly[w]['orders'] += 1
        weekly[w]['net_u'] += float(row['net_u'])
    weekly = {w: {'orders': v['orders'], 'net_u': round(v['net_u'], 6)} for w, v in weekly.items()}

    raw_hits = collections.Counter()
    hit_fids = collections.Counter()
    overlap_pairs = collections.Counter()
    for row in path_rows.values():
        hits = sorted((row.get('raw_group_hits') or {}).keys())
        for g in hits:
            raw_hits[g] += 1
        if len(hits) > 1:
            hit_fids['multiple_group_hits'] += 1
            for i, left in enumerate(hits):
                for right in hits[i + 1:]:
                    overlap_pairs[f'{left}|{right}'] += 1

    old_orders = read_jsonl(ORIGINAL_ORDERS)
    old_by_fid = {str(row['fid']): row for row in old_orders}
    new_by_fid = {str(row['fid']): row for row in scoped_orders}
    common = set(old_by_fid) & set(new_by_fid)
    compare = collections.Counter()
    for fid in common:
        old, new = old_by_fid[fid], new_by_fid[fid]
        compare['same_group'] += old['group'] == new['group']
        compare['same_side'] += old['side'] == new['side']
        compare['same_group_side_net_u'] += (old['group'], old['side'], round(float(old['net_u']), 8)) == (new['group'], new['side'], round(float(new['net_u']), 8))

    audit_rows = read_jsonl(FULL_VERIFICATION)
    audit_by_fid = {str(row['fid']): row for row in audit_rows}
    scoped_audit = [audit_by_fid[str(row['fid'])] for row in scoped_orders if str(row['fid']) in audit_by_fid]
    audit_ok = len(scoped_audit) == len(scoped_orders) and all(row.get('verified') is True for row in scoped_audit)
    audit_net = round(sum(float(row['net_u']) for row in scoped_audit), 6)
    assert audit_ok and abs(audit_net - sum(float(x['net_u']) for x in scoped_orders)) < 1e-8

    merged_rows = [
        {'date': row['date'], 'net_u': float(row['pnl'])} for row in frozen_rows
    ] + [{'date': row['date'], 'net_u': float(row['net_u'])} for row in scoped_orders]
    merged_net = sum(float(x['net_u']) for x in merged_rows)
    merged_n = len(merged_rows)
    combined_by_year = {}
    for y in sorted({int(x['year']) for x in frozen_rows} | {int(x['year']) for x in scoped_orders}):
        base_y = [x for x in frozen_rows if int(x['year']) == y]
        new_y = [x for x in scoped_orders if int(x['year']) == y]
        rows_y = [{'date': x['date'], 'net_u': float(x['pnl'])} for x in base_y] + [
            {'date': x['date'], 'net_u': float(x['net_u'])} for x in new_y]
        n_y = len(rows_y)
        u_y = sum(float(x['net_u']) for x in rows_y)
        combined_by_year[str(y)] = {'orders': n_y, 'net_u': round(u_y, 6),
                                    'roi_pct': round(100 * u_y / n_y, 6) if n_y else None,
                                    'mdd_u': drawdown(rows_y), 'frozen_orders': len(base_y),
                                    'frozen_net_u': round(sum(float(x['pnl']) for x in base_y), 6),
                                    'incremental_orders': len(new_y),
                                    'incremental_net_u': round(sum(float(x['net_u']) for x in new_y), 6)}

    summary = {
        'study': 'M8_EXACT_FROZEN_RULE_CROSS_LEAGUE_ORIGINAL_18374_CURRENT_FULL_PATH',
        'as_of_date': '2026-11-22',
        'history_type': 'historical Crown source-event path replay; not actual pregame HTTP receipt or Telegram order',
        'scope': {'original_schedule_fids': len(scope_fids), 'outside_frozen49_leagues': 15, 'full_path_fids': len(path_rows),
                  'coverage_status_counts': dict(coverage_status),
                  'coverage_by_league': {k: dict(v) for k, v in coverage_by_league.items()},
                  'coverage_by_year': {k: dict(v) for k, v in coverage_by_year.items()}},
        'frozen_baseline': {'orders': len(frozen), 'net_u': 236.015, 'roi_pct': 2.292743,
                            'sha256': sha(FROZEN), 'overlap_fids': len(set(frozen) & set(new_by_fid))},
        'exact_helper_audit': {'helper_path': str(helper_path.relative_to(ROOT)), 'full_path_rows_checked': len(path_rows),
                               'group_mismatches': len(group_mismatches), 'group_mismatch_examples': group_mismatches[:10],
                               'side_mismatches_after_frozen_E_fallback': len(side_mismatches),
                               'side_mismatch_examples': side_mismatches[:10], 'E_endpoint_tie_fallback_count': len(e_side_fallbacks)},
        'new_unique_orders': stats(scoped_orders),
        'orders_by_group': by_group,
        'orders_by_group_and_year': by_group_year,
        'orders_by_group_and_league': by_group_league,
        'orders_by_year': by_year,
        'combined_by_year': combined_by_year,
        'orders_by_league': by_league,
        'overlap': {'multi_group_fids': hit_fids['multiple_group_hits'], 'raw_group_hits': dict(raw_hits),
                    'overlap_group_pairs': dict(overlap_pairs), 'priority': list(group_order)},
        'weekly': weekly,
        'weekly_denominator': {'complete_path_iso_weeks': len(obs_weeks), 'average_orders_per_week': round(len(scoped_orders) / len(obs_weeks), 6),
                               'active_weeks': sum(x['orders'] > 0 for x in weekly.values()),
                               'active_week_average': round(len(scoped_orders) / max(1, sum(x['orders'] > 0 for x in weekly.values())), 6),
                               'iso_weeks_by_year': {y: len(ws) for y, ws in weeks_by_year.items()},
                               'weekly_orders_by_year': {y: {'orders': by_year[y]['orders'], 'observed_iso_weeks': len(weeks_by_year[y]),
                                                            'average_orders_per_week': round(by_year[y]['orders'] / len(weeks_by_year[y]), 6)}
                                                         for y in by_year}},
        'previous_snapshot_comparison': {'previous_order_count': len(old_by_fid), 'current_order_count_in_original_scope': len(new_by_fid),
                                         'shared_fids': len(common), 'previous_only_fids': len(set(old_by_fid) - set(new_by_fid)),
                                         'current_only_fids': len(set(new_by_fid) - set(old_by_fid)),
                                         'shared_same_group': compare['same_group'], 'shared_same_side': compare['same_side'],
                                         'shared_same_group_side_net_u': compare['same_group_side_net_u']},
        'independent_settlement_audit': {'checked_orders': len(scoped_audit), 'expected_orders': len(scoped_orders),
                                         'all_verified': audit_ok, 'recomputed_net_u': audit_net,
                                         'source_full_union_audit_orders': len(audit_rows)},
        'combined_with_frozen': {'orders': merged_n, 'net_u': round(merged_net, 6),
                                 'roi_pct': round(100 * merged_net / merged_n, 6), 'mdd_u': drawdown(merged_rows),
                                 'incremental_orders': len(scoped_orders), 'incremental_net_u': stats(scoped_orders)['net_u']},
        'inputs': {},
    }
    input_paths = [ORIGINAL_COVERAGE, ORIGINAL_ORDERS, FROZEN, FULL_PATHS, FULL_ORDERS, FULL_COVERAGE,
                   FULL_VERIFICATION, FULL_SUMMARY, helper_path]
    for path in input_paths:
        summary['inputs'][str(path.name)] = {'path': str(path), 'sha256': sha(path)}
    try:
        import sqlite3
        db = Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
        if db.exists():
            summary['inputs']['crown_sqlite'] = {'path': str(db), 'sha256': sha(db)}
    except OSError:
        pass

    write_jsonl_gz(OUT / 'exact_rule_cross_league_current_scope_orders.jsonl.gz', scoped_orders)
    write_jsonl_gz(OUT / 'exact_rule_cross_league_current_scope_coverage.jsonl.gz', scoped_coverage)
    write_jsonl_gz(OUT / 'exact_rule_cross_league_current_scope_settlement_audit.jsonl.gz', scoped_audit)
    write_json(OUT / 'exact_rule_cross_league_current_scope_summary.json', summary)
    write_json(OUT / 'INPUT_SHA256_MANIFEST.json', {'snapshot': 'current local Crown SQLite snapshot; source quote events remain historical replay',
                                                      'inputs': summary['inputs']})
    names = {}
    original_cov_by_fid = {str(x['fid']): x for x in scope_rows}
    for fid, row in original_cov_by_fid.items():
        names[str(row.get('league_id', row.get('league')))] = row.get('source_league') or row.get('league_name') or ''
    coverage_doc = {'scope_fids': len(scope_fids), 'complete_path_fids': len(path_rows),
                    'status_counts': dict(coverage_status), 'by_league': summary['scope']['coverage_by_league'],
                    'by_year': summary['scope']['coverage_by_year'], 'league_names': names}
    write_json(OUT / 'exact_rule_cross_league_current_scope_coverage_summary.json', coverage_doc)
    with (OUT / 'exact_rule_cross_league_current_scope_weekly.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['iso_week', 'orders', 'net_u'])
        for week, values in weekly.items(): w.writerow([week, values['orders'], values['net_u']])

    group_lines = ['| Group | Unique orders | Net U | ROI | MDD U | Avg / observed ISO week |', '|---|---:|---:|---:|---:|---:|']
    for g in group_order:
        x = by_group[g]
        group_lines.append(f"| {g} | {x['orders']} | {x['net_u']:+.3f} | {x['roi_pct']:+.3f}% | {x['mdd_u']:.3f} | {x['orders']/len(obs_weeks):.3f} |")
    group_lines.append(f"| **Deduplicated total** | **{len(scoped_orders)}** | **{stats(scoped_orders)['net_u']:+.3f}** | **{stats(scoped_orders)['roi_pct']:+.3f}%** | **{stats(scoped_orders)['mdd_u']:.3f}** | **{len(scoped_orders)/len(obs_weeks):.3f}** |")
    year_lines = ['| Year | Added orders | Net U | ROI | MDD U | Observed ISO weeks | Avg orders/week |', '|---:|---:|---:|---:|---:|---:|---:|']
    for y, x in by_year.items():
        nweek = len(weeks_by_year[y])
        year_lines.append(f"| {y} | {x['orders']} | {x['net_u']:+.3f} | {x['roi_pct']:+.3f}% | {x['mdd_u']:.3f} | {nweek} | {x['orders']/nweek:.3f} |")
    group_year_lines = ['| Group | ' + ' | '.join(by_group_year[next(iter(by_group_year))].keys()) + ' |',
                        '|---|' + '|'.join(['---:'] * len(by_group_year[next(iter(by_group_year))])) + '|']
    for g in group_order:
        cells = []
        for y, value in by_group_year[g].items():
            cells.append(f"{value['orders']} / {value['net_u']:+.3f}")
        group_year_lines.append('| ' + g + ' | ' + ' | '.join(cells) + ' |')
    combined_year_lines = ['| Year | Frozen orders / U | Added orders / U | Combined orders / U / ROI |', '|---:|---:|---:|---:|']
    for y, value in combined_by_year.items():
        combined_year_lines.append(f"| {y} | {value['frozen_orders']} / {value['frozen_net_u']:+.3f} | {value['incremental_orders']} / {value['incremental_net_u']:+.3f} | {value['orders']} / {value['net_u']:+.3f} / {value['roi_pct']:+.3f}% |")
    league_lines = ['| Provider league ID | Orders | Net U | ROI |', '|---:|---:|---:|---:|']
    for lid, x in by_league.items():
        roi_text = f"{x['roi_pct']:+.3f}%" if x['roi_pct'] is not None else '—'
        league_lines.append(f"| {lid} ({names.get(lid, '')}) | {x['orders']} | {x['net_u']:+.3f} | {roi_text} |")
    report = f"""# M8 exact frozen-rule cross-league replay: current full-path recheck

## Scope and method

This addendum keeps the specifically requested original `schedule_universe.jsonl` scope: 18,374 unique FIDs in 15 leagues outside the frozen 49. It uses the current full AH quote path snapshot, applies the repository's frozen `assign_exact_group` helper, keeps the original group priority `base → A → B → C → D → E → F → G`, and checks direction with `group_side`. The archived E rule has a documented endpoint-tie fallback: for 52 E assignments, `group_side` returns no side because `p1-p0=0`; the historical intermediate-path direction is retained, as in the earlier frozen-member audit. No market, stake, rule, or production setting changed.

The later full-path source includes all available Crown movement quotes between T6 and T1, not only the three sampled checkpoint rows. This resolves an implementation difference in the earlier 1,160-order snapshot. Among the 1,072 FIDs common to that earlier ledger and the current exact-scope ledger, 1,069 have identical group, direction, and net U. The current full-path logic has 199 additional FIDs and no longer assigns 88 earlier checkpoint-only hits. The old result remains in its original report; it is not overwritten.

## Coverage

- Original target schedule: 18,374 unique FIDs / 15 leagues.
- Current complete T6/T3/T1 paths: 6,967. Remaining statuses: {json.dumps(dict(coverage_status), ensure_ascii=False)}.
- Complete-path observation period: {len(obs_weeks)} ISO weeks. Added orders: 1,271 unique FIDs; frozen FID overlap: 0.
- Full path union source: 21,096 FIDs / 6,971 complete paths / 1,273 orders. Exactly 2 of those orders lie outside the specifically requested 18,374-FID inventory and are excluded from this addendum.
- Historical source-event replay only. Verified live Crown receipt FIDs and live orders in this target cohort: 0.

## Group results

{chr(10).join(group_lines)}

ROI is net U divided by unique orders. Asian quarter lines are settled by splitting into the adjacent half-point legs. The independent raw Crown/FT audit verifies 1,271/1,271 scoped orders, with zero discrepancies and +7.185U recomputed.

## Annual results

{chr(10).join(year_lines)}

Group annual count / net U:

{chr(10).join(group_year_lines)}

Frozen and combined annual results:

{chr(10).join(combined_year_lines)}

2024 was positive, while 2025 and the available portion of 2026 were negative. The 2024–2026 increment sums to -2.515U; the result does not show stable recent cross-year profit. The 2026 history ends June 1, 2026 and is partial.

## League results

{chr(10).join(league_lines)}

Six leagues have positive point estimates, seven negative, and two no order. Gulf Cup is only six orders; its +5.480U is not evidence of a repeatable league effect. League rows are descriptive and are not filters.

## Frozen baseline combination

- Frozen original eight: 10,294 FIDs, +236.015U, ROI +2.293%.
- Added outside-49 cohort: 1,271 FIDs, +7.185U, ROI +0.565%, MDD {stats(scoped_orders)['mdd_u']:.3f}U; 0 FID overlap.
- Combined by unique FID: {merged_n} FIDs, {merged_net:+.3f}U, ROI {100*merged_net/merged_n:.3f}%, MDD {drawdown(merged_rows):.3f}U. The addition improves historical net by +7.185U.
- Mean incremental order count: {len(scoped_orders)/len(obs_weeks):.3f} per complete-path observed ISO week; {sum(v['orders']>0 for v in weekly.values())} weeks carried at least one new order.

## Audit and files

The reproduction script directly calls the frozen group helper on all 6,967 target full paths; group mismatches: {len(group_mismatches)}. It validates every emitted order against its path row and independently audited Crown/FT settlement. Detailed outputs and SHA256 manifests are in this directory. All of this remains research-only; no M8 member, production model, Telegram dispatch, formal ledger, collection workflow, or user-confirmed rule changed.
"""
    (OUT / 'EXACT_RULE_CROSS_LEAGUE_CURRENT_SCOPE_REPORT.md').write_text(report, encoding='utf-8')

    manifest_paths = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt')
    (OUT / 'SHA256SUMS.txt').write_text(''.join(f'{sha(path)}  {path.name}\n' for path in manifest_paths), encoding='utf-8')
    print(json.dumps({'scope_fids': len(scope_fids), 'complete_path_fids': len(path_rows), 'orders': stats(scoped_orders),
                      'group_mismatches': len(group_mismatches), 'side_mismatches': len(side_mismatches),
                      'e_endpoint_tie_fallbacks': len(e_side_fallbacks), 'independent_verified': len(scoped_audit),
                      'independent_net_u': audit_net, 'frozen_overlap': summary['frozen_baseline']['overlap_fids'],
                      'combined': summary['combined_with_frozen']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
