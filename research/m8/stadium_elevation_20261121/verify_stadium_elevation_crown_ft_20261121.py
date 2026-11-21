#!/usr/bin/env python3
"""Independently re-read Crown SQLite raw responses and settle each AH model."""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, sqlite3

OUT = pathlib.Path(__file__).resolve().parent
DB = pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
SCORES = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl')
FROZEN = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
TZ = dt.timezone(dt.timedelta(hours=8))
UTC = dt.timezone.utc
METHODS = ('market_only', 'market_team', 'market_team_elevation')

def readj(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def parse_time(value):
    x = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00').replace(' ', 'T'))
    if x.tzinfo is None:
        x = x.replace(tzinfo=TZ)
    return x.astimezone(UTC)

def settle(line, side, odds, gd):
    hcap = float(line) if side == 'home' else -float(line)
    signed_gd = int(gd) if side == 'home' else -int(gd)
    if abs(hcap * 2 - round(hcap * 2)) < 1e-9:
        legs = [hcap]
    else:
        legs = [math.floor(hcap * 2) / 2, math.ceil(hcap * 2) / 2]
    pays = [float(odds) - 1 if signed_gd + leg > 1e-9 else
            -1. if signed_gd + leg < -1e-9 else 0. for leg in legs]
    label = ('full_win' if all(p > 0 for p in pays) else
             'half_win' if any(p > 0 for p in pays) else
             'push' if all(p == 0 for p in pays) else
             'half_loss' if any(p == 0 for p in pays) else 'full_loss')
    return sum(pays) / len(pays), label

def performance(rows, method, year=None, ev_only=False):
    rows = [r for r in rows if year is None or int(r['year']) == int(year)]
    if ev_only:
        rows = [r for r in rows if r.get('models', {}).get(method, {}).get('max_predicted_EV_U', 0) > 0]
    net = sum(float(r['models'][method]['net_u_independent']) for r in rows)
    daily = collections.defaultdict(float)
    states = collections.Counter()
    for r in rows:
        daily[r['date_beijing']] += float(r['models'][method]['net_u_independent'])
        states[r['models'][method]['settlement']] += 1
    equity = peak = mdd = 0.0
    for day in sorted(daily):
        equity += daily[day]
        peak = max(peak, equity)
        mdd = max(mdd, peak - equity)
    n = len(rows)
    return {'orders': n, 'net_u': round(net, 6),
            'roi_pct': round(100 * net / n, 6) if n else None,
            'mdd_u': round(mdd, 6), 'settlements': dict(states)}

def portfolio_stats(candidates, method, frozen_rows):
    rows = list(frozen_rows)
    rows.extend({'date': r['date_beijing'], 'net_u': float(r['models'][method]['net_u_independent'])}
                 for r in candidates)
    daily = collections.defaultdict(float)
    for r in rows: daily[r['date']] += float(r['net_u'])
    eq = peak = mdd = 0.0
    for day in sorted(daily):
        eq += daily[day]; peak = max(peak, eq); mdd = max(mdd, peak-eq)
    net = sum(float(r['net_u']) for r in rows)
    return {'orders': len(rows), 'net_u': round(net, 6),
            'roi_pct': round(net / len(rows) * 100, 6) if rows else None,
            'mdd_u': round(mdd, 6), 'incremental_orders': len(candidates),
            'incremental_net_u': round(sum(float(r['models'][method]['net_u_independent']) for r in candidates), 6)}

def main():
    predictions = {str(r['fid']): r for r in readj(OUT / 'altitude_per_fixture_predictions_20261121.jsonl.gz')
                  if int(r['year']) in (2024, 2025, 2026) and not r['frozen_original_eight']}
    score_by_fid = {str(r['fid']): r for r in readj(SCORES)}
    ledgers = {m: {str(r['fid']): r for r in readj(OUT / f'altitude_orders_{m}_always_bet_20261121.jsonl.gz')}
               for m in METHODS}
    conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    qrows = conn.execute('''
        SELECT a.fixture_id,a.quote_source_at_utc,a.handicap_home,a.home_decimal,a.away_decimal,
               c.capture_key,c.source_file,c.response_sha256,c.response_received_at_utc,c.kickoff_at_utc,
               c.prospective_observation,c.data_layer,a.quote_kind,a.quote_before_kickoff
        FROM asian_quote a JOIN capture c USING(capture_key)
        WHERE a.quote_kind='movement' AND c.data_layer='movement' AND a.quote_before_kickoff=1
        ORDER BY a.fixture_id,a.quote_source_at_utc
    ''').fetchall()
    by_fid = collections.defaultdict(list)
    for row in qrows:
        fid = str(row[0])
        if fid in predictions:
            by_fid[fid].append(row)
    capture_meta = collections.defaultdict(list)
    for row in conn.execute('''
        SELECT c.fixture_id,c.capture_key,c.data_layer,c.capture_mode,c.status,c.source_file,
               c.response_sha256,c.response_received_at_utc,c.kickoff_at_utc,c.quote_count,
               c.prospective_observation
        FROM capture c
    '''):
        if str(row[0]) in predictions:
            capture_meta[str(row[0])].append(row)
    failures = collections.Counter()
    received = collections.Counter()
    audits = []
    unverified = []
    for fid, pred in sorted(predictions.items()):
        score = score_by_fid.get(fid)
        if score is None:
            failures['score_row_missing'] += 1
            continue
        ko = parse_time(score['ko'])
        cutoff = ko - dt.timedelta(hours=1)
        eligible = [r for r in by_fid.get(fid, []) if r[1] and parse_time(r[1]) <= cutoff]
        quote_verification_path = 'sqlite_movement_row'
        if not eligible:
            # Some summary-layer captures persist open/close rows in SQLite but
            # retain the complete Crown asian_list in the SHA-bound raw body.
            # Recover T-60 from that raw response rather than calling the quote absent.
            raw_event_rows = []
            raw_items = []
            for c in capture_meta.get(fid, []):
                (cfid, ckey, layer, mode, status, source_file, want_sha, received_at,
                 capture_ko, quote_count, prospective) = c
                if not source_file or not pathlib.Path(source_file).exists():
                    continue
                body = pathlib.Path(source_file).read_bytes()
                if hashlib.sha256(body).hexdigest() != want_sha:
                    continue
                try:
                    doc = json.loads(body)
                    matches = [m for m in doc.get('data', []) if str(m.get('id')) == fid]
                    if len(matches) != 1:
                        continue
                    crown = [b for b in matches[0].get('bookmakers', []) if str(b.get('slug', '')).lower() == 'crown']
                    if len(crown) != 1:
                        continue
                    for raw_q in crown[0].get('asian_list') or []:
                        try:
                            qtime = parse_time(raw_q[4])
                            line, ho, ao = map(float, raw_q[1:4])
                            if qtime <= cutoff and min(ho, ao) > 1:
                                raw_event_rows.append((fid, qtime.isoformat(), line, ho, ao, ckey,
                                    source_file, want_sha, received_at, capture_ko, prospective,
                                    layer, 'raw_' + str(mode), 1))
                        except Exception:
                            continue
                    raw_items.append({'capture_key': ckey, 'data_layer': layer, 'capture_mode': mode,
                        'status': status, 'response_sha256': want_sha, 'response_received_at_utc': received_at,
                        'quote_count_indexed_in_sqlite': quote_count, 'raw_events_before_cutoff':
                            sum(1 for x in raw_event_rows if x[5] == ckey)})
                except Exception:
                    continue
            if raw_event_rows:
                eligible = [max(raw_event_rows, key=lambda r: parse_time(r[1]))]
                quote_verification_path = 'sha_verified_raw_response_fallback'
                received['raw_summary_capture_quote_fallback'] += 1
            else:
                failures['sqlite_and_raw_crown_tminus1_quote_missing'] += 1
                records = []
                for c in capture_meta.get(fid, []):
                    (cfid, ckey, layer, mode, status, source_file, want_sha, received_at,
                     capture_ko, quote_count, prospective) = c
                    records.append({'capture_key': ckey, 'data_layer': layer, 'capture_mode': mode,
                        'status': status, 'response_sha256_expected': want_sha,
                        'response_received_at_utc': received_at, 'quote_count': quote_count,
                        'prospective_observation': bool(prospective), 'raw_file_available': bool(source_file and pathlib.Path(source_file).exists())})
                unverified.append({'fid': fid, 'year': int(pred['year']), 'date_beijing': pred['date'],
                    'league': str(pred['league']), 'home': pred['home'], 'away': pred['away'],
                    'kickoff_utc': ko.isoformat(), 'reason': 'no SHA-valid Crown raw event at or before kickoff minus 60 minutes',
                    'candidate_line_home': pred['crown_line_home'], 'candidate_home_odds': pred['crown_home_decimal'],
                    'candidate_away_odds': pred['crown_away_decimal'], 'capture_records': records})
                continue
        q = max(eligible, key=lambda r: parse_time(r[1]))
        _, event_utc, line, ho, ao, capture_key, source_file, want_sha, received_at, capture_ko, prospective, layer, kind, before = q
        if not source_file or not pathlib.Path(source_file).exists():
            failures['raw_response_file_missing'] += 1
            continue
        body = pathlib.Path(source_file).read_bytes()
        actual_sha = hashlib.sha256(body).hexdigest()
        if actual_sha != want_sha:
            failures['raw_response_sha_mismatch'] += 1
            continue
        try:
            doc = json.loads(body)
            matches = [m for m in doc.get('data', []) if str(m.get('id')) == fid]
            if len(matches) != 1:
                raise ValueError('raw_fid_cardinality')
            match = matches[0]
            if (str(match.get('l_id')) != str(pred['league']) or
                str(match.get('h_id')) != str(score['home']) or
                str(match.get('a_id')) != str(score['away'])):
                raise ValueError('identity_mismatch')
            if (int(match['hg']), int(match['ag'])) != (int(score['hg']), int(score['ag'])):
                raise ValueError('raw_ft_mismatch')
            if (int(match['hg']), int(match['ag'])) != (int(pred['ft_home']), int(pred['ft_away'])):
                raise ValueError('prediction_ft_mismatch')
            if parse_time(match['start']) != ko:
                raise ValueError('kickoff_mismatch')
            if int(prospective or 0) != 1:
                received['historical_capture'] += 1
            receive_utc = parse_time(received_at)
            received['before_kickoff' if receive_utc <= ko else 'after_kickoff'] += 1
            crown = [b for b in match.get('bookmakers', []) if str(b.get('slug', '')).lower() == 'crown']
            if len(crown) != 1:
                raise ValueError('crown_cardinality')
            matching_raw = []
            for raw_q in crown[0].get('asian_list') or []:
                try:
                    qtime = parse_time(raw_q[4])
                    values = tuple(map(float, raw_q[1:4]))
                    if qtime == parse_time(event_utc) and values == (float(line), float(ho), float(ao)):
                        matching_raw.append(raw_q)
                except Exception:
                    continue
            if not matching_raw:
                raise ValueError('sqlite_quote_not_in_raw_response')
            for expected, actual, name in ((float(pred['crown_line_home']), float(line), 'line'),
                                           (float(pred['crown_home_decimal']), float(ho), 'home_odds'),
                                           (float(pred['crown_away_decimal']), float(ao), 'away_odds')):
                if abs(expected - actual) > 1e-8:
                    raise ValueError(name + '_mismatch')
            row = {'fid': fid, 'year': int(pred['year']), 'date_beijing': pred['date'],
                   'league': str(pred['league']), 'home': pred['home'], 'away': pred['away'],
                   'kickoff_utc': ko.isoformat(), 'quote_source_event_utc': parse_time(event_utc).isoformat(),
                   'http_response_received_at_utc': receive_utc.isoformat(),
                   'raw_response_sha256': actual_sha, 'capture_key': capture_key,
                   'quote_verification_path': quote_verification_path,
                   'crown_line_home': float(line), 'crown_home_decimal': float(ho),
                   'crown_away_decimal': float(ao), 'ft_home': int(match['hg']), 'ft_away': int(match['ag']),
                   'models': {}, 'formal_order': False}
            for method in METHODS:
                ledger = ledgers[method].get(fid)
                if ledger is None:
                    raise ValueError(method + '_ledger_row_missing')
                model = pred['models'][method]
                odds = float(ho) if model['direction'] == 'home' else float(ao)
                pnl, state = settle(float(line), model['direction'], odds, int(match['hg']) - int(match['ag']))
                if abs(pnl - float(model['net_u'])) > 1e-8 or abs(pnl - float(ledger['net_u'])) > 1e-8:
                    raise ValueError(method + '_net_u_mismatch')
                if state != model['settlement'] or state != ledger['settlement']:
                    raise ValueError(method + '_settlement_mismatch')
                row['models'][method] = {'direction': model['direction'], 'settlement': state,
                                         'net_u_independent': round(pnl, 8),
                                         'max_predicted_EV_U': float(model['max_predicted_EV_U'])}
            audits.append(row)
        except Exception as exc:
            failures[str(exc)] += 1
    frozen_rows = []
    for r in readj(FROZEN):
        if int(r['year']) not in (2024, 2025, 2026): continue
        if int(r['year']) == 2026 and r['date'] > '2026-07-06': continue
        frozen_rows.append({'date': r['date'], 'net_u': float(r['pnl'])})
    result = {'sample': '2024-2026 forward-test FIDs outside frozen original eight',
              'candidate_fids': len(predictions), 'raw_verified_fids': len(audits),
              'method_settlement_comparisons': len(audits) * len(METHODS),
              'method_fids': {m: len(ledgers[m]) for m in METHODS},
              'frozen_overlap': 0, 'capture_timing': dict(received),
              'failures': dict(failures),
              'all_candidates_independently_verified': len(audits) == len(predictions) and not failures,
              'verified_subset_performance': {m: {'all': performance(audits, m),
                    **{str(y): performance(audits, m, y) for y in (2024, 2025, 2026)}} for m in METHODS},
              'verified_subset_EV_positive_no_bet_diagnostic': {m: {'all': performance(audits, m, ev_only=True),
                    **{str(y): performance(audits, m, y, ev_only=True) for y in (2024, 2025, 2026)}} for m in METHODS},
              'same_window_frozen_original_eight': {
                    'orders': len(frozen_rows), 'net_u': round(sum(x['net_u'] for x in frozen_rows), 6)},
              'verified_subset_combined_with_frozen_baseline': {m: portfolio_stats(audits, m, frozen_rows) for m in METHODS},
              'quote_definition': 'latest Crown movement source-event no later than kickoff minus 60 minutes',
              'settlement': 'raw response SHA, fixture identity, kickoff, Crown AH line/odds and FT re-read; quarter-lines split into equal legs'}
    (OUT / 'independent_crown_ft_audit_20261121.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    with gzip.open(OUT / 'independent_crown_ft_per_fixture_20261121.jsonl.gz', 'wt', encoding='utf-8') as f:
        for row in audits:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    with (OUT / 'unverified_quote_fids_20261121.jsonl').open('w', encoding='utf-8') as f:
        for row in unverified:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
