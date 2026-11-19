#!/usr/bin/env python3
"""FID-deduplicated combination and overlap audit for M8 independent lines."""
import argparse
import collections
import datetime as dt
import json
from pathlib import Path


def read_jsonl(path):
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def stats(rows):
    rows = sorted(rows, key=lambda r: (r['date'][:10], str(r['fid'])))
    n = len(rows)
    net = sum(r['pnl'] for r in rows)
    daily = collections.defaultdict(float)
    weekly = collections.defaultdict(lambda: {'n': 0, 'net_u': 0.0})
    for r in rows:
        day = dt.date.fromisoformat(r['date'][:10])
        daily[day] += r['pnl']
        week = day.strftime('%G-W%V')
        weekly[week]['n'] += 1
        weekly[week]['net_u'] += r['pnl']
    equity = peak = drawdown = 0.0
    for _, value in sorted(daily.items()):
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    span = 0
    if rows:
        start = dt.date.fromisoformat(rows[0]['date'][:10]).isocalendar()
        end = dt.date.fromisoformat(rows[-1]['date'][:10]).isocalendar()
        span = (dt.date.fromisocalendar(end.year, end.week, 1) -
                dt.date.fromisocalendar(start.year, start.week, 1)).days // 7 + 1
    return {
        'n': n, 'net_u': round(net, 6),
        'roi_pct': round(net / n * 100, 6) if n else None,
        'week_span': span,
        'orders_per_week': round(n / span, 6) if span else None,
        'max_drawdown_u': round(drawdown, 6),
        'weekly': {k: {'n': v['n'], 'net_u': round(v['net_u'], 6)}
                   for k, v in sorted(weekly.items())},
    }


def order_row(r):
    return {'fid': str(r['fid']), 'date': r['date'][:10], 'pnl': float(r['pnl'])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument('--frozen-membership', type=Path,
                    default=Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl'))
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    root = a.repo
    outdir = root / 'research/m8/independent_info_20261119'
    h2h_file = outdir / 'context/h2h_candidate_orders.jsonl'
    team_file = outdir / 'team/team_familiarity_selected_orders.jsonl'
    base = read_jsonl(a.frozen_membership)
    h2h = [r for r in read_jsonl(h2h_file)
           if r['method'] == 'all_prior_mean' and r['selected_side']
           and not r['frozen_member']]
    team = [r for r in read_jsonl(team_file) if r['model'] == 'market_plus_familiarity']
    hmap = {str(r['fid']): r for r in h2h}
    tmap = {str(r['fid']): r for r in team}
    result = {'base_years': {}, 'h2h_years': {}, 'team_familiarity_years': {},
              'overlap': {}, 'unique_union_priority_h2h_then_team': {}, 'full_2024_2026': {}}
    for year in (2024, 2025, 2026):
        b = [order_row(r) for r in base if int(r['year']) == year]
        h = [order_row(r) for r in h2h if int(r['year']) == year]
        t = [order_row(r) for r in team if int(r['year']) == year]
        result['base_years'][str(year)] = stats(b)
        result['h2h_years'][str(year)] = {'standalone': stats(h), 'merged': stats(b + h)}
        result['team_familiarity_years'][str(year)] = {'standalone': stats(t), 'merged': stats(b + t)}
        union = {**tmap, **hmap}  # diagnostic only; H2H priority on duplicate FID
        u = [order_row(r) for r in union.values() if int(r['year']) == year]
        result['unique_union_priority_h2h_then_team'][str(year)] = {
            'standalone_deduplicated': stats(u), 'merged': stats(b + u)}
    both = hmap.keys() & tmap.keys()
    result['overlap'] = {
        'h2h_n': len(hmap), 'team_familiarity_n': len(tmap),
        'intersection_n': len(both), 'h2h_only_n': len(hmap.keys() - tmap.keys()),
        'team_only_n': len(tmap.keys() - hmap.keys()),
        'intersection_h2h_net_u': round(sum(hmap[f]['pnl'] for f in both), 6),
        'intersection_team_net_u': round(sum(tmap[f]['pnl'] for f in both), 6),
    }
    base3 = [order_row(r) for r in base if 2024 <= int(r['year']) <= 2026]
    result['full_2024_2026'] = {
        'base': stats(base3),
        'h2h': stats([order_row(r) for r in h2h if 2024 <= int(r['year']) <= 2026]),
        'team_familiarity': stats([order_row(r) for r in team if 2024 <= int(r['year']) <= 2026]),
        'union_dedup': stats([order_row(r) for r in {**tmap, **hmap}.values()
                              if 2024 <= int(r['year']) <= 2026]),
    }
    target = a.output or (outdir / 'integrated_overlap_and_union.json')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(target), 'overlap': result['overlap'],
                      'full_2024_2026': {k: {m: v for m, v in x.items() if m != 'weekly'}
                                         for k, x in result['full_2024_2026'].items()}},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
