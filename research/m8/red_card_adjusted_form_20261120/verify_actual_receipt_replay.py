#!/usr/bin/env python3
"""Independent audit of Crown T1 receipts and receipt-price settlements.

Reads the archived raw HTTP bodies, the saved time-forward model coefficients,
the historical feature ledger and the receipt-price replay output. It does not
trust receipt replay totals or price fields without checking the raw Crown body.
"""
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).resolve().parent
ARCHIVE = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
LEDGER = HERE / 'red_card_adjusted_form_per_fixture.jsonl.gz'
SUMMARY = HERE / 'red_card_adjusted_form_summary.json'
REPLAY = HERE / 'actual_receipt_reprice_orders.jsonl.gz'
REPLAY_SUMMARY = HERE / 'actual_receipt_reprice_summary.json'
OUT = HERE / 'actual_receipt_independent_verification.json'
TZ = ZoneInfo('Asia/Shanghai')
UTC = dt.timezone.utc
METHODS = ('market', 'market_plus_raw_form', 'market_plus_red_adjusted_form',
           'market_plus_raw_and_red_context', 'low_price')


def stamp(value):
    d = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return d.astimezone(UTC) if d.tzinfo else d.replace(tzinfo=TZ).astimezone(UTC)


def settle(line, side, gd, odds):
    signed_line = float(line) if side == 'home' else -float(line)
    margin = int(gd) if side == 'home' else -int(gd)
    q = round(signed_line * 4)
    if abs(signed_line * 4 - q) > 1e-8:
        raise ValueError(f'AH line not on quarter grid: {line}')
    legs = [signed_line] if q % 2 == 0 else [math.floor(signed_line * 2) / 2,
                                                   math.floor(signed_line * 2) / 2 + .5]
    pnl = []
    states = []
    for leg in legs:
        z = margin + leg
        if z > 1e-9:
            states.append('W'); pnl.append(float(odds) - 1)
        elif z < -1e-9:
            states.append('L'); pnl.append(-1.)
        else:
            states.append('P'); pnl.append(0.)
    state = ('full_win' if all(x == 'W' for x in states) else
             'full_loss' if all(x == 'L' for x in states) else
             'push' if all(x == 'P' for x in states) else
             'half_win' if 'W' in states else 'half_loss')
    return state, sum(pnl) / len(pnl)


def features(row, method, beta, line, home_odds, away_odds):
    h, a = row['raw_form']['home'], row['raw_form']['away']
    hc, ac = row['card_form']['home'], row['card_form']['away']
    rh, ra = float(h['gd_avg']), float(a['gd_avg'])
    dh = -beta * float(hc['red_adv_avg']) if hc['red_adv_avg'] is not None else 0.
    da = -beta * float(ac['red_adv_avg']) if ac['red_adv_avg'] is not None else 0.
    nh, na = int(hc['n']), int(ac['n'])
    gap = float(hc['red_adv_avg'] or 0.) - float(ac['red_adv_avg'] or 0.)
    market = [-float(line) + .25 * math.log(float(away_odds) / float(home_odds)),
              float(line), .25 * math.log(float(away_odds) / float(home_odds))]
    raw = [rh, ra, rh-ra, rh+ra, h['last_gd'], a['last_gd'],
           math.log1p(h['n']), math.log1p(a['n'])]
    adjusted = [rh+dh, ra+da, (rh+dh)-(ra+da), (rh+dh)+(ra+da), dh, da]
    context = [gap, math.log1p(nh), math.log1p(na), int(nh == 0), int(na == 0),
               nh/max(h['n'], 1), na/max(a['n'], 1)]
    if method == 'market':
        return market
    if method == 'market_plus_raw_form':
        return market + raw
    if method == 'market_plus_red_adjusted_form':
        return market + adjusted + context
    if method == 'market_plus_raw_and_red_context':
        return market + raw + adjusted + context
    raise ValueError(method)


def choose_side(row, method, fold, quote):
    line = float(quote['line']); ho = float(quote['odds']['home']); ao = float(quote['odds']['away'])
    if method == 'low_price':
        return 'home' if ho <= ao else 'away'
    z = features(row, method, float(fold['beta_red_adv_to_goal_diff']), line, ho, ao)
    model = fold['models'][method]
    coef, means, scales = model['coef_intercept_first'], model['mean'], model['scale']
    pred = float(coef[0] + sum((z[i] - means[i]) / scales[i] * coef[i+1] for i in range(len(z))))
    return 'home' if pred > 0 else 'away'


def main():
    ledger = {r['fid']: r for r in (json.loads(x) for x in gzip.open(LEDGER, 'rt', encoding='utf-8'))}
    summary = json.loads(SUMMARY.read_text())
    model_summary = json.loads(REPLAY_SUMMARY.read_text())
    saved_orders = [json.loads(x) for x in gzip.open(REPLAY, 'rt', encoding='utf-8')]
    saved = {(x['fid'], x['method']): x for x in saved_orders}
    any_receipts = set(); t1 = {}; raw_errors = collections.Counter(); exact_path = set()
    archive_rows = 0
    for line in ARCHIVE.open(encoding='utf-8'):
        x = json.loads(line); archive_rows += 1
        fid = str(x.get('fixture_id') or '')
        row = ledger.get(fid)
        if row is None or row['frozen_eight_overlap'] or 'AH' not in (x.get('markets') or {}):
            continue
        try:
            if stamp(x['received_utc']) < stamp(row['kickoff_utc']):
                any_receipts.add(fid)
        except Exception:
            pass
        if x.get('snapshot_horizon') != 'T1':
            continue
        quote = x['markets']['AH']
        try:
            capture_path = pathlib.Path(x['source_file'])
            capture = json.loads(capture_path.read_bytes())
            raw_body = str(capture.get('raw_response') or '')
            if hashlib.sha256(raw_body.encode()).hexdigest() != x.get('raw_sha256') or capture.get('raw_sha256') != x.get('raw_sha256'):
                raw_errors['raw_sha256'] += 1; continue
            body = json.loads(raw_body); matches = body.get('data') or []
            match = matches[0]
            if (str(match.get('id')) != fid or str(match.get('l_id')) != row['league'] or
                str(match.get('h_id')) != row['home_id'] or str(match.get('a_id')) != row['away_id']):
                raw_errors['identity'] += 1; continue
            if capture.get('received_at') != x.get('received_utc') or stamp(x['received_utc']) >= stamp(row['kickoff_utc']):
                raw_errors['timing'] += 1; continue
            crown = next((b for b in match.get('bookmakers', []) if b.get('slug') == 'crown'), None)
            close = (crown or {}).get('asian', {}).get('close') or {}
            if (close.get('line') is None or abs(float(close['line'])-float(quote['line'])) > 1e-8 or
                abs(float(close['home'])-float(quote['odds']['home'])) > 1e-8 or
                abs(float(close['away'])-float(quote['odds']['away'])) > 1e-8 or
                stamp(close['time']) != stamp(quote['source_event_utc'])):
                raw_errors['market_price'] += 1; continue
            if (abs(float(quote['line'])-row['line']) < 1e-8 and
                abs(float(quote['odds']['home'])-row['home_odds']) < 1e-8 and
                abs(float(quote['odds']['away'])-row['away_odds']) < 1e-8):
                exact_path.add(fid)
            t1[fid] = (row, x, quote)
        except Exception as exc:
            raw_errors[f'parse:{type(exc).__name__}'] += 1
    if raw_errors:
        raise AssertionError(f'raw receipt audit failed: {dict(raw_errors)}')
    if len(t1) != 832 or len(any_receipts) != 873 or len(exact_path) != 449:
        raise AssertionError(f'receipt inventory mismatch {len(t1)=} {len(any_receipts)=} {len(exact_path)=}')

    comparison_errors = collections.Counter(); metrics = {}
    by_method = collections.defaultdict(list)
    beta_fold = summary['folds']['2026']
    for fid, (row, receipt, quote) in t1.items():
        for method in METHODS:
            saved_row = saved.get((fid, method))
            if saved_row is None:
                comparison_errors['missing_order'] += 1; continue
            side = choose_side(row, method, beta_fold, quote)
            if side != saved_row['receipt_repriced_side']:
                comparison_errors['predicted_side'] += 1
            if float(saved_row['AH_line']) != float(quote['line']) or float(saved_row['AH_home_odds']) != float(quote['odds']['home']) or float(saved_row['AH_away_odds']) != float(quote['odds']['away']):
                comparison_errors['saved_price'] += 1
            state, pnl = settle(quote['line'], side, int(row['gd']), quote['odds'][side])
            if state != saved_row['settlement'] or abs(pnl-float(saved_row['net_u'])) > 1e-9:
                comparison_errors['settlement'] += 1
            by_method[method].append((row, saved_row, pnl))
    if comparison_errors:
        raise AssertionError(f'repriced order mismatch: {dict(comparison_errors)}')

    for method, items in by_method.items():
        pnl = [x[2] for x in items]
        by_day = collections.defaultdict(float)
        weeks = set(); states = collections.Counter()
        for row, saved_row, value in items:
            by_day[row['kickoff_beijing'][:10]] += value
            weeks.add(row['iso_week']); states[saved_row['settlement']] += 1
        cum = peak = mdd = 0.
        for day in sorted(by_day):
            cum += by_day[day]; peak = max(peak, cum); mdd = max(mdd, peak-cum)
        net = sum(pnl)
        metrics[method] = {'orders': len(items), 'net_u': round(net, 6),
                           'roi_pct': round(100*net/len(items), 6), 'mdd_u': round(mdd, 6),
                           'active_iso_weeks': len(weeks), 'settlements': dict(states)}
        reported = model_summary['metrics_by_method'][method]
        for key in ('orders', 'net_u', 'roi_pct', 'mdd_u', 'active_weeks'):
            field = 'active_iso_weeks' if key == 'active_weeks' else key
            if metrics[method][field] != reported[key]:
                raise AssertionError(f'{method} summary mismatch at {key}: {metrics[method][field]} != {reported[key]}')
    result = {'pass': True, 'archive_sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
              'archive_rows': archive_rows, 'candidate_any_pregame_receipt_fids': len(any_receipts),
              'candidate_T1_fids': len(t1), 'candidate_T1_exact_historical_path_price_fids': len(exact_path),
              'candidate_T1_price_mismatch_fids': len(t1)-len(exact_path),
              'kickoff_metadata_differences': sum(1 for _, x, _ in t1.values()
                                                   if stamp(x['kickoff_utc']) != stamp(_kickoff_for_receipt(x, ledger))),
              'raw_sha_identity_timing_market_errors': dict(raw_errors),
              'order_rows_independently_repriced': len(saved_orders),
              'prediction_price_settlement_errors': dict(comparison_errors),
              'metrics_by_method': metrics,
              'scope_note': 'Receipt prices and HTTP raw bodies are verified. Feature snapshots are not time-verified; outcomes are retrospective, not prospective.'}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _kickoff_for_receipt(x, ledger):
    return ledger[str(x['fixture_id'])]['kickoff_utc']


if __name__ == '__main__':
    main()
