#!/usr/bin/env python3
"""Test player-pair cohesion on expanded15 with an Original49 T12 training pool.

Historical lineups are explicit complete starting-XI records. Appearance minutes
are independently tracked as a source coverage diagnostic but are neither a
feature nor imputed. AH contracts are T12 Crown-only in both train and test.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import sqlite3
import sys
from typing import Any

import numpy as np

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA = pathlib.Path('/Users/mac/QuantAsiaDesk/data')
DB = DATA / 'crown_quote_store/crown_quotes.sqlite3'
FOUNDATION = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
RECEIPTS = WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
MARKET49 = WORK / 'm8_early_joint_market_inventory_20261115.jsonl'
EXPANDED15 = ROOT / 'research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
IDENTITY = OUT / 'identity_coverage_audit.json'
TM_SOURCE = WORK / 'm8_pregame_info_source_20261117'
GAMES, LINEUPS, APPEARANCES = (TM_SOURCE / n for n in ('games.csv.gz', 'game_lineups.csv.gz', 'appearances.csv.gz'))
MANAGER = WORK / 'm8_prior_manager_turnover_20261117.py'
EXACT_T1 = ROOT / 'research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_orders.jsonl.gz'
ALPHA = 100.0

sys.path.insert(0, str(ROOT / 'research/m8/player_pair_cohesion_20261121'))
import run_player_pair_cohesion as pair_helper  # noqa: E402
from run_expanded15_pair_cohesion import load_lineup_history  # noqa: E402


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path: pathlib.Path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def read_gz(path: pathlib.Path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_gz(path: pathlib.Path, rows) -> None:
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode())


def utc(value: str) -> dt.datetime:
    x = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if x.tzinfo is None:
        x = x.replace(tzinfo=dt.timezone.utc)
    return x.astimezone(dt.timezone.utc)


def t12_quotes_for_expanded(rows: list[dict]) -> tuple[dict[str, dict], dict[str, int]]:
    cx = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    cx.row_factory = sqlite3.Row
    quote_map: dict[str, list[dict]] = collections.defaultdict(list)
    counts = collections.Counter()
    fids = [str(row['fid']) for row in rows]
    for start in range(0, len(fids), 700):
        chunk = fids[start:start + 700]
        marks = ','.join('?' for _ in chunk)
        sql = f'''SELECT q.fixture_id,q.handicap_home,q.home_decimal,q.away_decimal,
                         q.quote_source_at_utc,q.response_received_at_utc,q.sequence_index,
                         c.capture_mode,c.response_sha256,c.source_file,c.prospective_observation
                  FROM asian_quote q JOIN capture c USING(capture_key)
                  WHERE q.fixture_id IN ({marks}) AND q.quote_kind='movement'
                    AND c.data_layer='movement'
                  ORDER BY q.fixture_id,q.quote_source_at_utc,q.response_received_at_utc,
                           c.response_sha256,q.sequence_index'''
        for q in cx.execute(sql, chunk):
            quote_map[str(q['fixture_id'])].append(dict(q))
    cx.close()

    chosen = {}
    for row in rows:
        fid = str(row['fid'])
        kickoff = utc(row['kickoff_utc'])
        cutoff = kickoff - dt.timedelta(hours=12)
        valid = []
        for q in quote_map.get(fid, []):
            try:
                source_time = utc(q['quote_source_at_utc'])
                line, home, away = float(q['handicap_home']), float(q['home_decimal']), float(q['away_decimal'])
                if source_time <= cutoff and source_time < kickoff and home > 1 and away > 1 and abs(line * 4 - round(line * 4)) < 1e-7:
                    valid.append((source_time, q))
            except (ValueError, TypeError, KeyError):
                continue
        counts['expanded15_fids'] += 1
        if not valid:
            counts['missing_T12_quote'] += 1
            continue
        source_time, q = max(valid, key=lambda x: (x[0], x[1].get('response_received_at_utc') or '',
                                                     x[1].get('response_sha256') or '', int(x[1]['sequence_index'])))
        chosen[fid] = {'line': float(q['handicap_home']), 'home_odds': float(q['home_decimal']),
            'away_odds': float(q['away_decimal']), 'source_event_utc': source_time.isoformat(),
            'response_received_utc': q['response_received_at_utc'], 'capture_mode': q['capture_mode'],
            'response_sha256': q['response_sha256'], 'source_file': q['source_file'],
            'prospective_observation': int(q['prospective_observation'] or 0),
            'kickoff_utc': kickoff.isoformat(), 'T12_cutoff_utc': cutoff.isoformat()}
        counts['has_T12_quote'] += 1
        counts[f'capture_mode:{q["capture_mode"]}'] += 1
    return chosen, dict(counts)


def load_schedule_ids() -> dict[str, dict]:
    target_leagues = json.loads(IDENTITY.read_text(encoding='utf-8'))['coverage']['target_leagues']
    schedule_dir = DATA / 'm5-crown-authorized/schedules'
    out = {}
    for league in target_leagues:
        for page in sorted((schedule_dir / str(league)).glob('page-*.raw.json')):
            blob = json.loads(page.read_bytes())
            for row in (blob.get('data') or {}).get('matches') or []:
                if row.get('status') != 'full' or str(row.get('l_id')) != str(league):
                    continue
                fid = str(row.get('id') or '')
                if fid:
                    out[fid] = {'league': str(league), 'home_id': str(row.get('h_id') or ''),
                        'away_id': str(row.get('a_id') or ''), 'home': row.get('h'), 'away': row.get('a'),
                        'hg': int(row['hg']), 'ag': int(row['ag'])}
    return out


def mdd(rows):
    daily = collections.defaultdict(float)
    for row in rows:
        daily[row['date']] += float(row['net_u'])
    total = peak = drawdown = 0.0
    for day in sorted(daily):
        total += daily[day]
        peak = max(peak, total)
        drawdown = max(drawdown, peak - total)
    return round(drawdown, 6)


def summarize(rows, span_weeks=None):
    if not rows:
        return {'n': 0, 'net_U': 0.0, 'ROI_pct': None, 'MDD_U': 0.0, 'orders_per_week': 0.0, 'five_state': {}}
    net = sum(float(row['net_u']) for row in rows)
    dates = [dt.date.fromisoformat(row['date']) for row in rows]
    weeks = span_weeks if span_weeks is not None else ((max(dates) - min(dates)).days // 7 + 1)
    return {'n': len(rows), 'net_U': round(net, 6), 'ROI_pct': round(net / len(rows) * 100, 6),
            'MDD_U': mdd(rows), 'orders_per_week': round(len(rows) / weeks, 6) if weeks else 0.0,
            'five_state': dict(collections.Counter(row['settlement'] for row in rows))}


def grouped(rows, key):
    d = collections.defaultdict(list)
    for row in rows:
        d[str(row[key])].append(row)
    return {k: summarize(v) for k, v in sorted(d.items())}


def main() -> None:
    # Reuse the audited Original49 crosswalk; expanded15 maps only through the
    # exact repeated anchor audit. No future outcomes enter model features.
    sys.path.insert(0, str(ROOT))
    legacy = pair_helper.exec_prefix(MANAGER, '# Build historical coach timeline', 'm8_pooled_pair_identity')
    crosswalk = {str(k): str(v) for k, v in legacy['cm'].items()}
    teammap = {(str(k[0]), str(k[1])): str(v) for k, v in legacy['teammap'].items()}
    expanded_identity = json.loads(IDENTITY.read_text(encoding='utf-8'))
    for league, comp in expanded_identity['coverage']['clear_competition_crosswalks'].items():
        if league in crosswalk and crosswalk[league] != comp:
            raise ValueError(f'Crosswalk conflict for league {league}')
        crosswalk[league] = str(comp)
    for key, tm_id in expanded_identity['team_mappings'].items():
        league, crown_id = key.split('|', 1)
        k = (league, crown_id)
        if k in teammap and teammap[k] != str(tm_id):
            raise ValueError(f'Team-map conflict for {k}')
        teammap[k] = str(tm_id)
    history, lineup_audit = load_lineup_history(crosswalk, teammap)

    # Original49 T12 rows are the pooled training/control source.
    foundation = {str(row['fid']): row for row in read_jsonl(FOUNDATION)}
    receipt_ids = {str(row['fixture_id']) for row in read_jsonl(RECEIPTS)}
    allrows = [row for row in read_jsonl(MARKET49) if int(row['T']) == 12]
    if len({str(row['fid']) for row in allrows}) != len(allrows):
        raise AssertionError('Original49 T12 inventory has duplicate FIDs')
    features_cache = {}
    pool = []
    missing49 = collections.Counter()
    for row in allrows:
        fid, league, day = str(row['fid']), str(row['league']), dt.date.fromisoformat(row['date'])
        home_id, away_id = str(row['home_id']), str(row['away_id'])
        if not teammap.get((league, home_id)) or not teammap.get((league, away_id)):
            missing49['unmapped_Original49_target_team'] += 1
            continue
        hk, ak = (league, home_id, day), (league, away_id, day)
        if hk not in features_cache:
            features_cache[hk] = pair_helper.team_cohesion(history, (league, home_id), day)
        if ak not in features_cache:
            features_cache[ak] = pair_helper.team_cohesion(history, (league, away_id), day)
        hf, af = features_cache[hk], features_cache[ak]
        if hf is None or af is None:
            missing49['insufficient_complete_prior_XI_history'] += 1
            continue
        pool.append({'fid': fid, 'source': 'Original49', 'league': league, 'date': row['date'],
            'year': int(row['year']), 'home_id': home_id, 'away_id': away_id,
            'home_tm_club_id': teammap[(league, home_id)], 'away_tm_club_id': teammap[(league, away_id)],
            'hg': int(row['hg']), 'ag': int(row['ag']), 'gd': int(row['hg']) - int(row['ag']),
            'line': float(row['al']), 'home_odds': float(row['ah']), 'away_odds': float(row['aa']),
            'pair_features': pair_helper.pair_features(hf, af), 'pair_features_home': hf, 'pair_features_away': af,
            'frozen_overlap': fid in foundation, 'actual_receipt_fid_overlap': fid in receipt_ids,
            'feature_cutoff_date': (day - dt.timedelta(days=3)).isoformat(),
            'source_class': 'historical_Crown_T12_event_replay'})

    expanded_rows = list(read_gz(EXPANDED15))
    t12_map, t12_audit = t12_quotes_for_expanded(expanded_rows)
    schedule = load_schedule_ids()
    target_rows = []
    missing15 = collections.Counter()
    for row in expanded_rows:
        fid, league = str(row['fid']), str(row['league'])
        quote = t12_map.get(fid)
        if quote is None:
            missing15['T12_quote_missing'] += 1
            continue
        sched = schedule.get(fid)
        if sched is None:
            missing15['Crown_schedule_FID_missing'] += 1
            continue
        if (sched['league'], sched['hg'], sched['ag']) != (league, int(row['hg']), int(row['ag'])):
            raise ValueError(f'Expanded15 score/league mismatch for FID {fid}')
        if fid in foundation:
            missing15['unexpected_frozen_FID_overlap'] += 1
            continue
        home_id, away_id = sched['home_id'], sched['away_id']
        htm, atm = teammap.get((league, home_id)), teammap.get((league, away_id))
        if not htm or not atm:
            missing15['one_or_both_expanded15_team_ids_unmapped'] += 1
            continue
        day = dt.date.fromisoformat(str(row['date']))
        hk, ak = (league, home_id, day), (league, away_id, day)
        if hk not in features_cache:
            features_cache[hk] = pair_helper.team_cohesion(history, (league, home_id), day)
        if ak not in features_cache:
            features_cache[ak] = pair_helper.team_cohesion(history, (league, away_id), day)
        hf, af = features_cache[hk], features_cache[ak]
        if hf is None or af is None:
            missing15['insufficient_complete_prior_XI_history'] += 1
            continue
        line, ho, ao = quote['line'], quote['home_odds'], quote['away_odds']
        target_rows.append({'fid': fid, 'source': 'expanded15', 'league': league,
            'league_name': row.get('league_name'), 'date': str(row['date']), 'year': int(row['year']),
            'iso_week': f'{day.isocalendar().year}-W{day.isocalendar().week:02d}',
            'home': sched['home'], 'away': sched['away'], 'home_id': home_id, 'away_id': away_id,
            'home_tm_club_id': htm, 'away_tm_club_id': atm, 'hg': int(row['hg']), 'ag': int(row['ag']),
            'gd': int(row['hg']) - int(row['ag']), 'line': line, 'home_odds': ho, 'away_odds': ao,
            'pair_features': pair_helper.pair_features(hf, af), 'pair_features_home': hf, 'pair_features_away': af,
            'feature_cutoff_date': (day - dt.timedelta(days=3)).isoformat(),
            'Crown_T12_source_event_utc': quote['source_event_utc'],
            'Crown_T12_response_received_utc': quote['response_received_utc'],
            'capture_mode': quote['capture_mode'], 'response_sha256': quote['response_sha256'],
            'source_file': quote['source_file'], 'kickoff_utc': quote['kickoff_utc'],
            'T12_cutoff_utc': quote['T12_cutoff_utc'], 'prospective_observation': quote['prospective_observation'],
            'frozen_overlap': False, 'actual_receipt_fid_overlap': fid in receipt_ids,
            'source_class': 'historical_Crown_T12_source_event_replay'})
    target_rows.sort(key=lambda row: (row['date'], row['fid']))
    if len({row['fid'] for row in target_rows}) != len(target_rows):
        raise AssertionError('Expanded15 T12 candidate set has duplicate FIDs')
    if set(row['fid'] for row in target_rows) & set(foundation):
        raise AssertionError('Expanded15 candidate FIDs overlap frozen Original49')

    # Unified, no-future training pool; tests are only expanded15 FIDs.
    historical_pool = pool + target_rows
    if len({row['fid'] for row in historical_pool}) != len(historical_pool):
        raise AssertionError('Original49 and expanded15 pools overlap by FID')
    methods = ('market_only', 'pair_only', 'market_plus_pair')
    years = (2024, 2025, 2026)
    prediction = {method: [] for method in methods}
    fold_meta = {}
    for year in years:
        train = [row for row in historical_pool if 2019 <= row['year'] < year and row['fid'] not in receipt_ids]
        test = [row for row in target_rows if row['year'] == year]
        fold_meta[str(year)] = {'train_n': len(train), 'train_years': sorted({row['year'] for row in train}),
            'train_max_year': max((row['year'] for row in train), default=None), 'test_n': len(test),
            'receipt_fids_excluded_from_training': True, 'fixed_ridge_alpha': ALPHA}
        if not test:
            continue
        if not train:
            raise ValueError(f'No prior-year combined training examples for expanded15 {year}')
        for method in methods:
            def x(row):
                market = [-row['line'] + .25 * math.log(row['away_odds'] / row['home_odds']),
                          row['line'], .25 * math.log(row['away_odds'] / row['home_odds'])]
                return market if method == 'market_only' else row['pair_features'] if method == 'pair_only' else market + row['pair_features']
            fit = pair_helper.ridge_fit([x(row) for row in train], [row['gd'] for row in train])
            fold_meta[str(year)].setdefault('model_sigma', {})[method] = round(fit[3], 8)
            for row in test:
                mu = pair_helper.predict(fit, x(row))
                side, hev, aev = pair_helper.choose(row['line'], row['home_odds'], row['away_odds'], mu, fit[3])
                if side is None:
                    state, net, odds = 'push', 0.0, None
                else:
                    odds = row['home_odds'] if side == 'home' else row['away_odds']
                    state, net = pair_helper.settle(row['line'], side, row['gd'], odds)
                prediction[method].append({**row, 'method': method, 'predicted_home_goal_difference': round(mu, 8),
                    'residual_sigma': round(fit[3], 8), 'home_EV_U': round(hev, 8), 'away_EV_U': round(aev, 8),
                    'chosen_side': side, 'chosen_odds': odds, 'settlement': state, 'net_u': round(net, 8),
                    'training_year_cutoff_exclusive': year, 'training_n': len(train),
                    'training_max_year': max(r['year'] for r in train)})

    frozen_rows = []
    for row in foundation.values():
        try:
            frozen_rows.append({'fid': str(row['fid']), 'date': str(row['date'])[:10], 'year': int(row['year']),
                                'net_u': float(row['pnl'])})
        except (KeyError, ValueError, TypeError):
            continue
    span_dates = [dt.date.fromisoformat(row['date']) for row in target_rows if row['year'] in years]
    span_weeks = (max(span_dates) - min(span_dates)).days // 7 + 1 if span_dates else 0
    model_summary, annual, weekly, league, combined = {}, {}, {}, {}, {}
    for method, rows in prediction.items():
        rows.sort(key=lambda row: (row['date'], row['fid']))
        model_summary[method] = {'expanded15_incremental': summarize(rows, span_weeks)}
        annual[method] = {str(year): summarize([row for row in rows if row['year'] == year]) for year in years}
        weekly[method] = grouped(rows, 'iso_week')
        league[method] = grouped(rows, 'league')
        if rows:
            low, high = min(row['date'] for row in rows), max(row['date'] for row in rows)
            frozen_same = [row for row in frozen_rows if low <= row['date'] <= high]
        else:
            frozen_same = []
        merged = frozen_same + rows
        combined[method] = {'frozen_same_period_n': len(frozen_same), 'candidate_n': len(rows),
            'unique_fids': len({row['fid'] for row in merged}), 'net_U': round(sum(row['net_u'] for row in merged), 6),
            'ROI_pct': round(sum(row['net_u'] for row in merged) / len(merged) * 100, 6) if merged else None,
            'candidate_incremental_net_U': round(sum(row['net_u'] for row in rows), 6),
            'frozen_same_period_net_U': round(sum(row['net_u'] for row in frozen_same), 6)}

    receipt_test_ids = sorted({row['fid'] for row in target_rows if row['year'] in years} & receipt_ids)
    write_gz(OUT / 'expanded15_T12_contract_inventory.jsonl.gz',
             sorted(t12_map.values(), key=lambda row: row['kickoff_utc']))
    write_gz(OUT / 'pooled_pair_cohesion_predictions.jsonl.gz',
             [row for method in methods for row in prediction[method]])
    write_gz(OUT / 'pooled_pair_cohesion_market_plus_pair_ledger.jsonl.gz', prediction['market_plus_pair'])
    source_rows = [{'fid': row['fid'], 'league': row['league'], 'date': row['date'],
        'T12_source_event_utc': row['Crown_T12_source_event_utc'],
        'T12_response_received_utc': row['Crown_T12_response_received_utc'],
        'capture_mode': row['capture_mode'], 'response_sha256': row['response_sha256'],
        'source_file': row['source_file'], 'T12_home_line': row['line'],
        'T12_home_odds': row['home_odds'], 'T12_away_odds': row['away_odds'], 'hg': row['hg'], 'ag': row['ag']}
        for row in target_rows]
    write_gz(OUT / 'expanded15_T12_candidate_source_audit.jsonl.gz', source_rows)

    summary = {'study': 'expanding-year player-pair cohesion model trained on Original49 and expanded15, tested only on expanded15',
        'execution_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'inputs_sha256': {str(path): sha(path) for path in (FOUNDATION, RECEIPTS, MARKET49, EXPANDED15,
            GAMES, LINEUPS, APPEARANCES, MANAGER, IDENTITY)},
        'sqlite_db_path': str(DB), 'sqlite_db_size_bytes': DB.stat().st_size,
        'coverage': {'Original49_T12_rows': len(allrows), 'Original49_feature_pool_rows': len(pool),
            'Original49_missing_reasons': dict(missing49), 'expanded15_complete_T6_T3_T1_rows': len(expanded_rows),
            'expanded15_FIDs_with_T12_quote': len(t12_map), 'expanded15_T12_quote_audit': t12_audit,
            'expanded15_feature_complete_rows': len(target_rows),
            'expanded15_feature_rows_by_league': dict(collections.Counter(row['league'] for row in target_rows)),
            'expanded15_feature_rows_by_year': dict(collections.Counter(str(row['year']) for row in target_rows)),
            'expanded15_missing_reasons': dict(missing15), 'expanded15_original_frozen_overlap': 0,
            'candidate_test_fids_with_true_receipt_archive_overlap': receipt_test_ids,
            'lineup_history_audit': dict(lineup_audit), 'strict_positive_appearance_feature_ready_count': 0,
            'source_capture_modes': dict(collections.Counter(row['capture_mode'] for row in target_rows)),
            'source_prospective_observation_count': sum(int(row['prospective_observation']) for row in target_rows)},
        'identity': {'Original49_leagues': len(legacy['cm']), 'Original49_team_mappings': len(legacy['teammap']),
            'expanded15_crosswalks': expanded_identity['coverage']['clear_competition_crosswalks'],
            'expanded15_team_mappings': len(expanded_identity['team_mappings']),
            'expanded15_identity_method': expanded_identity['identity_method']},
        'methodology': {'target_market': 'Crown T12 AH only. Original49 training targets use the existing T12 market inventory; expanded15 T12 is latest valid Crown source event at or before kickoff minus 12 hours, recovered read-only from SQLite movement rows.',
            'features': 'Prior 365-day pair co-start recurrence and concentration; target-date-minus-3-day cutoff. Completed prior match XI is accepted only when game_lineups explicitly records exactly 11 distinct starting_lineup IDs. Appearance minutes are audited but not used or imputed because this feature measures pair co-starts, not playing time. Target XI never used.',
            'training': 'Expanding-year: 2024 trained on 2019-2023; 2025 on 2019-2024; 2026 on 2019-2025. Training rows pool feature-complete Original49 and expanded15 matches from years strictly before the test year; verified receipt FIDs excluded from training.',
            'model': 'Fixed Ridge alpha=100; same Gaussian integer goal-difference payoff comparison and one-side choice across market-only, pair-only, market+pair. No EV/no-bet threshold and no parameter search.',
            'settlement': 'Crown AH T12 line and correct home/away decimal odds; quarter-line split into adjacent half-goal legs at half stake; original Frozen8 FIDs excluded from candidate set and audited separately.',
            'quote_time_classification': 'All expanded15 T12 price rows in this experiment are historical event-time replay; database actual response-received time retained and never represented as contemporaneous.'},
        'training_folds': fold_meta, 'models': model_summary, 'annual_incremental': annual,
        'weekly_incremental': weekly, 'league_incremental': league,
        'frozen_eight_same_period_union': combined,
        'historical_vs_receipt': {'expanded15_true_receipt_replay_orders': 0,
            'verified_receipt_intersection_candidates': receipt_test_ids,
            'note': 'No real receipt replay is asserted. Any archive FID intersection is only reported unless its exact pregame quote is independently available.'},
        'formal_orders': 0, 'formal_ledger_writes': 0, 'production_changes': False}
    (OUT / 'pooled_pair_cohesion_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'coverage': summary['coverage'], 'identity': summary['identity'],
        'models': model_summary, 'annual': annual, 'frozen_eight_same_period_union': combined}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
