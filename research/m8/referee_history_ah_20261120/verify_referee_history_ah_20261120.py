#!/usr/bin/env python3
"""Independent Crown T12 / FT / quarter-line ledger verification.

This reads the archived paired Crown T12 inventory, frozen membership and
published research ledger independently of the model runner, then recomputes
every selected AH settlement and weekly-block uncertainty summary.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import json
import math
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
MARKET = WORK / 'm8_early_joint_market_inventory_20261115.jsonl'
FROZEN = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
LEDGER = OUT / 'referee_history_per_fixture_20261120.jsonl.gz'
SUMMARY = OUT / 'm8_referee_history_results_20261120.json'


def settle(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[float, str]:
    q = float(line) * 4
    if abs(q - round(q)) > 1e-7:
        raise ValueError(f'non-quarter AH line {line}')
    legs = [float(line)] if abs(float(line) * 2 - round(float(line) * 2)) < 1e-8 else [
        math.floor(float(line) * 2) / 2, math.ceil(float(line) * 2) / 2
    ]
    payouts = []
    for leg in legs:
        margin = hg - ag + leg if side == 'home' else ag - hg - leg
        payouts.append(float(odds) - 1 if margin > 1e-9 else -1.0 if margin < -1e-9 else 0.0)
    pnl = sum(payouts) / len(payouts)
    state = ('full_win' if all(x > 0 for x in payouts) else
             'half_win' if any(x > 0 for x in payouts) else
             'push' if all(x == 0 for x in payouts) else
             'half_loss' if any(x == 0 for x in payouts) else 'full_loss')
    return pnl, state


def sha_file(path: pathlib.Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    crown = {}
    with MARKET.open(encoding='utf-8') as f:
        for line in f:
            x = json.loads(line)
            if int(x['T']) == 12:
                fid = str(x['fid'])
                if fid in crown:
                    raise AssertionError(f'duplicate Crown T12 FID {fid}')
                crown[fid] = x
    frozen = {}
    with FROZEN.open(encoding='utf-8') as f:
        for line in f:
            x = json.loads(line)
            frozen[str(x['fid'])] = x
    if len(frozen) != 10294:
        raise AssertionError(f'frozen set changed: {len(frozen)}')

    ledger = []
    with gzip.open(LEDGER, 'rt', encoding='utf-8') as f:
        for line in f:
            ledger.append(json.loads(line))
    if len(ledger) != 6967 * 4:
        raise AssertionError(f'ledger rows {len(ledger)}, expected 27868')
    by_method: dict[str, list[dict]] = collections.defaultdict(list)
    quote_checks = settlement_checks = side_checks = 0
    for x in ledger:
        by_method[x['method']].append(x)
        fid = str(x['fid'])
        raw = crown.get(fid)
        if raw is None:
            raise AssertionError(f'no raw Crown T12 inventory row: {fid}')
        pairs = {
            'date': str(raw['date']) == str(x['date']),
            'league': str(raw['league']) == str(x['league']),
            'home_id': str(raw['home_id']) == str(x['home_id']),
            'away_id': str(raw['away_id']) == str(x['away_id']),
            'line': abs(float(raw['al']) - float(x['Crown_T12_AH_home_line'])) < 1e-9,
            'home_odds': abs(float(raw['ah']) - float(x['Crown_T12_home_odds'])) < 1e-9,
            'away_odds': abs(float(raw['aa']) - float(x['Crown_T12_away_odds'])) < 1e-9,
            'home_ft': int(raw['hg']) == int(x['FT_home']),
            'away_ft': int(raw['ag']) == int(x['FT_away']),
        }
        if not all(pairs.values()):
            raise AssertionError(f'Crown/FT mismatch {fid}: {[k for k,v in pairs.items() if not v]}')
        quote_checks += 1
        pnl, state = settle(x['Crown_T12_AH_home_line'], x['side'], x['FT_home'], x['FT_away'], x['price'])
        if abs(pnl - float(x['net_u'])) > 1e-7 or state != x['settlement']:
            raise AssertionError(f'settlement mismatch {fid}/{x["method"]}: {pnl}/{state} vs {x["net_u"]}/{x["settlement"]}')
        settlement_checks += 1
        if x['method'] in ('CROWN_ONLY', 'REF_ONLY', 'CROWN_PLUS_REF'):
            pred = x.get('predicted_home_minus_away_u')
            if pred is None or x['side'] != ('home' if float(pred) >= 0 else 'away'):
                raise AssertionError(f'prediction-side rule mismatch {fid}/{x["method"]}')
            side_checks += 1
        elif x['method'] == 'LOWER_PRICE':
            expected = 'home' if float(raw['ah']) <= float(raw['aa']) else 'away'
            if x['side'] != expected:
                raise AssertionError(f'lower-price side mismatch {fid}')
            side_checks += 1
        if bool(x['frozen_eight_overlap_posthoc']) != (fid in frozen):
            raise AssertionError(f'frozen overlap mismatch {fid}')

    summary = json.loads(SUMMARY.read_text(encoding='utf-8'))
    annual_check = {}
    weekly_by_method = {}
    for method, rows in by_method.items():
        ids = {str(x['fid']) for x in rows}
        if len(ids) != 6967:
            raise AssertionError(f'{method} FID count {len(ids)}')
        incr = [x for x in rows if str(x['fid']) not in frozen]
        if len({str(x['fid']) for x in incr}) != 5467:
            raise AssertionError(f'{method} incremental FID count mismatch')
        annual_check[method] = {}
        for year in (2024, 2025, 2026):
            yr = [x for x in incr if int(x['year']) == year]
            expected = summary['models'][method]['incremental_by_year'][str(year)]
            got_u = round(sum(float(x['net_u']) for x in yr), 6)
            got_n = len(yr)
            if got_n != expected['orders'] or abs(got_u - expected['net_u']) > 1e-6:
                raise AssertionError(f'annual summary mismatch {method}/{year}')
            annual_check[method][str(year)] = {'orders': got_n, 'net_u': got_u}
        expected = summary['models'][method]['incremental_outside_frozen_eight']
        if len(incr) != expected['orders'] or abs(sum(float(x['net_u']) for x in incr) - expected['net_u']) > 1e-6:
            raise AssertionError(f'total summary mismatch {method}')
        weeks = collections.defaultdict(lambda: {'orders': 0, 'net_u': 0.0})
        for x in incr:
            w = weeks[x['iso_week']]
            w['orders'] += 1
            w['net_u'] += float(x['net_u'])
        weekly_by_method[method] = {k: {'orders': v['orders'], 'net_u': round(v['net_u'], 6)} for k,v in sorted(weeks.items())}

    # Descriptive year-stratified block bootstrap. Resample calendar ISO weeks
    # within each target year; no subgroup or parameter selection is performed.
    rng = random.Random(20261120)
    bootstrap = {}
    reps = 20000
    for method, weeks in weekly_by_method.items():
        blocks_by_year = collections.defaultdict(list)
        for week, value in weeks.items():
            blocks_by_year[int(week[:4])].append(value)
        draws = []
        for _ in range(reps):
            total_u = total_n = 0
            for year, blocks in blocks_by_year.items():
                for _ in range(len(blocks)):
                    b = blocks[rng.randrange(len(blocks))]
                    total_u += b['net_u']
                    total_n += b['orders']
            draws.append((total_u, 100 * total_u / total_n if total_n else 0.0))
        us = sorted(x[0] for x in draws)
        rois = sorted(x[1] for x in draws)
        bootstrap[method] = {
            'repetitions': reps,
            'unit_ci_95': [round(us[int(.025 * reps)], 6), round(us[int(.975 * reps)], 6)],
            'roi_pct_ci_95': [round(rois[int(.025 * reps)], 6), round(rois[int(.975 * reps)], 6)],
            'bootstrap_probability_net_positive': round(sum(x > 0 for x in us) / reps, 6),
            'block': 'ISO-week, resampled with replacement within each test year',
            'seed': 20261120,
        }

    out = {
        'status': 'PASS',
        'raw_crown_t12_rows': len(crown),
        'frozen_eight_fids': len(frozen),
        'ledger_rows': len(ledger),
        'models': sorted(by_method),
        'raw_crown_quote_ft_identity_checks': quote_checks,
        'independent_ah_settlement_checks': settlement_checks,
        'side_rule_checks': side_checks,
        'duplicate_method_fids': 0,
        'frozen_overlap_method_fids': 1500,
        'unique_incremental_fids_per_method': 5467,
        'annual_recomputed': annual_check,
        'weekly_incremental': weekly_by_method,
        'weekly_block_bootstrap': bootstrap,
        'inputs': {str(p): sha_file(p) for p in (MARKET, FROZEN, LEDGER, SUMMARY)},
        'interpretation_limit': 'This verifies source-event Crown inventory, FT and settlement; it does not establish historical HTTP receipt, referee assignment publication time, live execution or formal Telegram trading.',
    }
    (OUT / 'referee_history_independent_verification_20261120.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k not in ('weekly_incremental','inputs')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
