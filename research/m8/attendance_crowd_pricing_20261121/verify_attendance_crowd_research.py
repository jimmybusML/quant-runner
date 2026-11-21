#!/usr/bin/env python3
"""Independent raw Crown AH/FT/settlement and FID ledger verification."""
from __future__ import annotations

import bisect
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
from collections import Counter
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def parse_dt(v: str) -> dt.datetime:
    x = dt.datetime.fromisoformat(str(v).replace('Z', '+00:00').replace(' ', 'T'))
    if x.tzinfo is None:
        x = x.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
    return x.astimezone(dt.timezone.utc)


def settle(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[float, str]:
    line, odds = float(line), float(odds)
    if abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError(f'invalid quarter line {line}')
    legs = [line] if abs(line * 2 - round(line * 2)) < 1e-8 else [math.floor(line*2)/2, math.ceil(line*2)/2]
    values = []
    for leg in legs:
        adjusted = hg - ag + leg if side == 'home' else ag - hg - leg
        values.append(odds - 1 if adjusted > 1e-9 else -1.0 if adjusted < -1e-9 else 0.0)
    result = sum(values) / len(values)
    if all(x > 0 for x in values): label = 'full_win'
    elif any(x > 0 for x in values): label = 'half_win'
    elif all(x == 0 for x in values): label = 'push'
    elif any(x == 0 for x in values): label = 'half_loss'
    else: label = 'full_loss'
    return result, label


def load_gz(path: pathlib.Path) -> list[dict]:
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def main() -> None:
    fixture_path = OUT / 'attendance_crowd_per_fixture_20261121.jsonl.gz'
    order_path = OUT / 'attendance_crowd_orders_20261121.jsonl.gz'
    summary_path = OUT / 'attendance_crowd_summary_20261121.json'
    fixtures = load_gz(fixture_path)
    order_rows = load_gz(order_path)
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    errors = Counter()
    checked_contracts = 0
    method_fids: dict[str, set[str]] = {}
    fixture_by_fid = {}
    for row in fixtures:
        fid = str(row['fid'])
        if fid in fixture_by_fid:
            errors['duplicate_fixture_fid'] += 1
        fixture_by_fid[fid] = row
        raw_path = pathlib.Path(row['market_raw_path'])
        try:
            raw_bytes = raw_path.read_bytes()
            if hashlib.sha256(raw_bytes).hexdigest() != row['market_raw_sha256']:
                errors['raw_sha_mismatch'] += 1
                continue
            data = json.loads(raw_bytes)['data']
            x = next(v for v in data if str(v.get('id')) == fid)
            if (str(x.get('l_id')) != str(row['league_id']) or
                    str(x.get('h_id')) != str(row['home_id']) or
                    str(x.get('a_id')) != str(row['away_id']) or
                    [int(x['hg']), int(x['ag'])] != list(map(int, row['ft'])) or x.get('status') != 'full'):
                errors['fixture_identity_ft_mismatch'] += 1
                continue
            kickoff = parse_dt(x['start'])
            cut = kickoff - dt.timedelta(hours=12)
            crown = next(b for b in x.get('bookmakers', []) if b.get('slug') == 'crown')
            paths = []
            for q in crown.get('asian_list') or []:
                try:
                    t = parse_dt(q[4]); line, ho, ao = map(float, q[1:4])
                    if t < kickoff and t <= cut and ho > 1 and ao > 1 and abs(line*4-round(line*4)) < 1e-7:
                        paths.append((t, 1, line, ho, ao, 'movement'))
                except Exception:
                    continue
            asian = crown.get('asian') or {}
            for tag in ('open', 'close'):
                q = asian.get(tag)
                if not isinstance(q, dict):
                    continue
                try:
                    t = parse_dt(q['time']); line, ho, ao = float(q['line']), float(q['home']), float(q['away'])
                    if t < kickoff and t <= cut and ho > 1 and ao > 1 and abs(line*4-round(line*4)) < 1e-7:
                        paths.append((t, 0, line, ho, ao, tag))
                except Exception:
                    continue
            if not paths:
                errors['no_raw_T12_quote'] += 1
                continue
            paths.sort(key=lambda q: (q[0], q[1]))
            t, _, line, ho, ao, kind = paths[-1]
            if (abs(line-float(row['crown_t12_line_home'])) > 1e-8 or
                    abs(ho-float(row['crown_t12_home_decimal'])) > 1e-8 or
                    abs(ao-float(row['crown_t12_away_decimal'])) > 1e-8 or
                    kind != row['crown_t12_quote_kind'] or
                    abs((t-parse_dt(row['crown_t12_source_event_utc'])).total_seconds()) > 1):
                errors['T12_line_price_time_mismatch'] += 1
                continue
            home_u, home_cls = settle(line, 'home', int(x['hg']), int(x['ag']), ho)
            away_u, away_cls = settle(line, 'away', int(x['hg']), int(x['ag']), ao)
            if (abs(home_u-float(row['settle_home_u'])) > 1e-9 or
                    abs(away_u-float(row['settle_away_u'])) > 1e-9 or
                    home_cls != row['settle_home_class'] or away_cls != row['settle_away_class']):
                errors['AH_quarter_settlement_mismatch'] += 1
                continue
            checked_contracts += 1
        except Exception as e:
            errors['raw_error_' + type(e).__name__] += 1

    ledger_counts = Counter()
    ledger_pnl = Counter()
    ledger_seen: dict[str, set[str]] = {}
    for row in order_rows:
        method = str(row['method']); fid = str(row['fid'])
        seen = ledger_seen.setdefault(method, set())
        if fid in seen:
            errors['duplicate_method_fid'] += 1
        seen.add(fid)
        ledger_counts[method] += 1
        ledger_pnl[method] += float(row['net_u'])
        fixture = fixture_by_fid.get(fid)
        if not fixture:
            errors['ledger_fixture_missing'] += 1
            continue
        if fixture['frozen_eight_overlap']:
            errors['candidate_overlaps_frozen_eight'] += 1
        if abs(float(row['crown_t12_line_home']) - float(fixture['crown_t12_line_home'])) > 1e-8:
            errors['ledger_market_mismatch'] += 1
        expected = fixture.get('models', {}).get(method)
        if not expected or expected['selected_side'] != row['side'] or abs(float(expected['net_u'])-float(row['net_u'])) > 1e-9:
            errors['ledger_model_result_mismatch'] += 1
    for method, vals in summary['models'].items():
        if ledger_counts[method] != vals['all_test']['n']:
            errors['ledger_summary_count_mismatch'] += 1
        if abs(ledger_pnl[method]-vals['all_test']['net_U']) > 1e-6:
            errors['ledger_summary_pnl_mismatch'] += 1
    result = {
        'study': 'M8_ATTENDANCE_CROWD_INDEPENDENT_RAW_CROWN_SETTLEMENT_AUDIT',
        'fixture_rows': len(fixtures), 'unique_fixture_fids': len(fixture_by_fid),
        'raw_crown_quote_FT_and_AH_settlement_checked': checked_contracts,
        'method_ledger_rows': dict(ledger_counts), 'method_ledger_net_U': {k: round(v,6) for k,v in ledger_pnl.items()},
        'issues': dict(errors), 'pass': not errors and checked_contracts == len(fixtures),
        'inputs': {str(p): sha(p) for p in (fixture_path, order_path, summary_path)},
    }
    (OUT/'attendance_crowd_independent_verification_20261121.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if not result['pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
