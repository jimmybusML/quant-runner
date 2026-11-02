#!/usr/bin/env python3
# coding: utf-8
"""Read-only MR1 AH EV calibration experiment; no production or Telegram writes.

Input: official MR1 V6 formal/settled.json. The ridge slope penalty is a
research parameter, not a production rule. All adaptive training uses only
orders settled before the evaluated Telegram send time.
"""
import argparse
import collections
import datetime
import json
from pathlib import Path


def when(iso):
    return datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))


def adjusted_ev(history, current_ev, price, ridge=5.0):
    if not history:
        return current_ev
    x = [p - 1.9 for p, _ in history]
    y = [outcome_minus_ev for _, outcome_minus_ev in history]
    mean_y = sum(y) / len(y)
    centered_cov = sum(xi * (yi - mean_y) for xi, yi in zip(x, y))
    slope = centered_cov / (sum(xi * xi for xi in x) + ridge)
    intercept = mean_y - slope * sum(x) / len(x)
    return current_ev + intercept + slope * (price - 1.9)


def metrics(rows, key):
    return {
        'n': len(rows),
        'mean_forecast_ev': round(sum(r[key] for r in rows) / len(rows), 6),
        'mean_realized_profit': round(sum(r['realized'] for r in rows) / len(rows), 6),
        'bias': round(sum(r[key] - r['realized'] for r in rows) / len(rows), 6),
        'mse': round(sum((r[key] - r['realized']) ** 2 for r in rows) / len(rows), 6),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('settled_json', type=Path)
    args = parser.parse_args()
    book = json.loads(args.settled_json.read_text(encoding='utf8'))
    rows = sorted(book['entries'].values(), key=lambda v: (v['sent_at'], v['signal_id']))
    live = []
    for order in rows:
        before = [o for o in rows if when(o['settled_at']) <= when(order['sent_at'])]
        history = [(float(o['price']), float(o['realized_pnl']) - float(o['EV'])) for o in before]
        baseline = float(order['EV'])
        global_adjustment = baseline + sum(y for _, y in history) / len(history) if history else baseline
        live.append({'n_prior':len(history), 'sent_at':order['sent_at'],
                     'price':float(order['price']), 'realized':float(order['realized_pnl']),
                     'raw':baseline, 'global_bias':global_adjustment,
                     'price_ridge':adjusted_ev(history, baseline, float(order['price']))})
    half = len(live) // 2
    tests = {'all_prequential':live, 'later_half_prequential':live[half:]}
    output = {'source_generated_at':book['generated_at'], 'n':len(live),
              'model':'EV + historical residual intercept + ridge-regularized price slope',
              'research_only':True, 'ridge_study_parameter':5.0,
              'comparisons':{k:{model:metrics(part, model) for model in ('raw','global_bias','price_ridge')}
                             for k,part in tests.items()}}
    # Descriptive only: the odds ranges below are diagnostic bins, not gates.
    price_groups = collections.defaultdict(list)
    for r in live:
        if r['price'] < 1.85: label='under_1.85'
        elif r['price'] < 2.00: label='1.85_to_under_2.00'
        else: label='2.00_and_up'
        price_groups[label].append(r)
    output['descriptive_price_groups'] = {
        name:{'full':metrics(v,'raw'),
              'earlier':metrics([r for r in v if r['sent_at'] < live[half]['sent_at']], 'raw')
              if any(r['sent_at'] < live[half]['sent_at'] for r in v) else None,
              'later':metrics([r for r in v if r['sent_at'] >= live[half]['sent_at']], 'raw')
              if any(r['sent_at'] >= live[half]['sent_at'] for r in v) else None}
        for name,v in sorted(price_groups.items())}
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
