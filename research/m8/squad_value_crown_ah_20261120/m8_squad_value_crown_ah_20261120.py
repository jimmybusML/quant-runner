#!/usr/bin/env python3
"""M8 exploratory historical squad market-value vs Crown AH study.

Squad membership is reconstructed only from appearances strictly before the
target cutoff; player values use only complete dated rows from the locally
truncated valuation archive and a fixed 30-day date embargo. This is not
evidence that source data was published/received at those dates.
"""
from __future__ import annotations

import bisect
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
import pathlib
import re
import zlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
SRC = WORK / 'm8_pregame_info_source_20261117'
GAMES = SRC / 'games.csv.gz'
APPEARANCES = SRC / 'appearances.csv.gz'
VALUATIONS = SRC / 'player_valuations.csv.gz'
MARKET = WORK / 'm8_early_joint_market_inventory_20261115.jsonl'
FROZEN_FILE = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
RECEIPTS = WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
CROSS_LEAGUE_SUMMARY = ROOT / 'research/m8/exact_rules_outside_original49_20261120/exact_rule_cross_league_summary.json'
PLAYER_BOOTSTRAP = ROOT / 'research/m8/m8_player_load_rotation_crown_20261119.py'
YEAR_TESTS = (2024, 2025, 2026)
RIDGE_ALPHA = 100.0
VALUE_PUBLISH_LAG_DAYS = 30
HISTORY_DAY_EMBARGO = 3


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def settle(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[float, str]:
    line = float(line)
    if abs(line * 4 - round(line * 4)) > 1e-7:
        raise ValueError(f'AH not on quarter line grid: {line}')
    legs = [line] if abs(line * 2 - round(line * 2)) < 1e-8 else [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
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


def read_crown() -> tuple[list[dict], dict]:
    text = PLAYER_BOOTSTRAP.read_text(encoding='utf-8')
    prefix = text[:text.index('foundation_root=')]
    ns = {'__file__': str(PLAYER_BOOTSTRAP)}
    exec(compile(prefix, str(PLAYER_BOOTSTRAP) + '[read-only-prefix]', 'exec'), ns)
    h, teammap = [dict(x) for x in ns['H']], ns['teammap']
    if len(h) != 38846 or len({str(x['fid']) for x in h}) != len(h):
        raise AssertionError('unexpected paired Crown T24/T12 inventory')
    return h, teammap


def read_complete_truncated_csv(path: pathlib.Path) -> tuple[list[dict], dict]:
    """Read CRC/EOF-incomplete gzip, retaining newline-terminated CSV records only."""
    d = zlib.decompressobj(31)
    raw = bytearray()
    with path.open('rb') as f:
        while block := f.read(1 << 20):
            raw.extend(d.decompress(block))
    is_truncated = not d.eof
    if raw.endswith(b'\n'):
        complete = bytes(raw)
        partial_bytes = 0
    else:
        last = raw.rfind(b'\n')
        complete = bytes(raw[:last + 1]) if last >= 0 else b''
        partial_bytes = len(raw) - len(complete)
    rows = list(csv.DictReader(io.StringIO(complete.decode('utf-8'))))
    return rows, {
        'compressed_bytes': path.stat().st_size,
        'decompressed_complete_bytes': len(complete),
        'complete_csv_data_rows': len(rows),
        'truncated_gzip_eof': is_truncated,
        'partial_final_record_bytes_discarded': partial_bytes,
        'complete_last_date': max((str(r['date']) for r in rows), default=None),
    }


def read_history_inputs(teammap: dict) -> tuple[dict, dict, dict]:
    vals_raw, val_audit = read_complete_truncated_csv(VALUATIONS)
    val_by_player = collections.defaultdict(list)
    val_duplicates = collections.defaultdict(list)
    for r in vals_raw:
        try:
            day = dt.date.fromisoformat(str(r['date'])).toordinal()
            value = float(re.sub(r'[^0-9.]', '', str(r['market_value_in_eur'])))
            pid = str(r['player_id'])
            if not pid or value <= 0:
                continue
            val_by_player[pid].append((day, value))
            val_duplicates[(pid, day)].append(value)
        except (KeyError, ValueError):
            continue
    conflicting = {k for k,v in val_duplicates.items() if max(v)-min(v) > 0.01}
    val_by_player = {p: sorted(rows) for p, rows in val_by_player.items()}
    val_days = {p: [x[0] for x in rows] for p, rows in val_by_player.items()}

    mapped_clubs = set(str(x) for x in teammap.values())
    app_by_player_club = collections.defaultdict(lambda: collections.defaultdict(list))
    player_events = collections.defaultdict(list)
    app_audit = collections.Counter()
    with gzip.open(APPEARANCES, 'rt', encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            try:
                club, pid = str(r['player_club_id']), str(r['player_id'])
                day = dt.date.fromisoformat(str(r['date'])).toordinal()
                if club not in mapped_clubs or not pid:
                    continue
                app_by_player_club[pid][club].append(day)
                player_events[pid].append((day, club))
                app_audit['mapped_appearance_rows'] += 1
            except (KeyError, ValueError):
                app_audit['invalid_appearance_rows'] += 1
    for pid, clubs in app_by_player_club.items():
        for club in clubs:
            clubs[club].sort()
    player_days = {}
    for pid in player_events:
        player_events[pid].sort()
        player_days[pid] = [x[0] for x in player_events[pid]]
    players_by_club = collections.defaultdict(list)
    for pid, clubs in app_by_player_club.items():
        for club in clubs:
            players_by_club[club].append(pid)
    games_rows = 0
    try:
        with gzip.open(GAMES, 'rt', encoding='utf-8', newline='') as f:
            games_rows = sum(1 for _ in csv.DictReader(f))
    except Exception:
        pass
    value_audit = {
        **val_audit,
        'valuation_rows_loaded': sum(map(len, val_by_player.values())),
        'unique_players_with_valuation': len(val_by_player),
        'conflicting_player_date_valuation_keys': len(conflicting),
        'valuation_max_day': max((x[0] for rows in val_by_player.values() for x in rows), default=None),
    }
    source_audit = {
        'games_source_rows': games_rows,
        'mapped_appearance_rows': app_audit['mapped_appearance_rows'],
        'invalid_appearance_rows': app_audit['invalid_appearance_rows'],
        'mapped_transfermarkt_clubs': len(mapped_clubs),
        'mapped_competitions': len({str(k[0]) for k in teammap}),
        'teams_crosswalked': len(teammap),
        'appearance_max_day': max((v[-1][0] for v in player_events.values() if v), default=None),
    }
    return ({'values': val_by_player, 'value_days': val_days, 'conflicts': conflicting},
            {'by_player_club': app_by_player_club, 'players_by_club': players_by_club, 'player_events': player_events, 'player_days': player_days},
            {'valuation': value_audit, 'other': source_audit})


def make_team_value_builder(value_data: dict, app_data: dict):
    cache = {}
    conflicts = value_data['conflicts']

    def team_value(club: str, target_day: int) -> dict | None:
        key = (club, target_day)
        if key in cache:
            return cache[key]
        cutoff = target_day - HISTORY_DAY_EMBARGO
        value_cutoff = cutoff - VALUE_PUBLISH_LAG_DAYS
        roster_values = []
        roster_known = 0
        active_roster = 0
        ages = []
        for pid in app_data['players_by_club'].get(club, ()):
            club_days = app_data['by_player_club'][pid].get(club)
            if not club_days:
                continue
            ci = bisect.bisect_right(club_days, cutoff) - 1
            if ci < 0 or club_days[ci] < cutoff - 365:
                continue
            p_days = app_data['player_days'].get(pid, [])
            pi = bisect.bisect_right(p_days, cutoff) - 1
            if pi < 0:
                continue
            latest_day = p_days[pi]
            same_day_clubs = {c for d, c in app_data['player_events'][pid] if d == latest_day}
            if len(same_day_clubs) != 1 or next(iter(same_day_clubs)) != club:
                continue
            active_roster += 1
            vals = value_data['values'].get(pid, [])
            val_days = value_data['value_days'].get(pid, [])
            vi = bisect.bisect_right(val_days, value_cutoff) - 1
            if vi < 0:
                continue
            vday, eur = vals[vi]
            if (pid, vday) in conflicts:
                continue
            roster_known += 1
            roster_values.append(float(eur))
            ages.append(cutoff - vday)
        if not roster_values:
            result = None
        else:
            roster_values.sort(reverse=True)
            top11 = sum(roster_values[:11])
            total = sum(roster_values)
            med = float(np.median(roster_values))
            result = {
                'log_top11_sum': math.log1p(top11),
                'log_total_sum': math.log1p(total),
                'log_median': math.log1p(med),
                'log_mean': math.log1p(total / len(roster_values)),
                'log_valued_n': math.log1p(roster_known),
                'log_active_n': math.log1p(active_roster),
                'coverage_share': roster_known / active_roster if active_roster else 0.0,
                'mean_value_age_days': float(np.mean(ages)),
                'top5_share': sum(roster_values[:5]) / total if total else 0.0,
            }
        cache[key] = result
        return result
    return team_value


def crown_features(r: dict) -> list[float]:
    home, away, line = float(r['ah']), float(r['aa']), float(r['al'])
    return [line, abs(line), math.log(home / away), math.log((home + away) / 2), 1 / home + 1 / away - 1]


VALUE_FEATURES = ('log_top11_sum','log_total_sum','log_median','log_mean','log_valued_n','log_active_n','coverage_share','mean_value_age_days','top5_share')


def value_features(h: dict, a: dict) -> list[float]:
    return [h[k]-a[k] for k in VALUE_FEATURES] + [h[k]+a[k] for k in VALUE_FEATURES]


def ridge_predict(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    mu, sd = x.mean(0), x.std(0)
    sd[sd < 1e-10] = 1.0
    xx = np.column_stack((np.ones(len(x)), (x-mu)/sd))
    zz = np.column_stack((np.ones(len(z)), (z-mu)/sd))
    penalty = np.eye(xx.shape[1]) * RIDGE_ALPHA
    penalty[0,0] = 0.0
    beta = np.linalg.solve(xx.T @ xx + penalty, xx.T @ y)
    return zz @ beta


def iso(d: str) -> str:
    q = dt.date.fromisoformat(d).isocalendar()
    return f'{q.year}-W{q.week:02}'


def metrics(rows: list[dict], span: list[str] | None = None) -> dict:
    byday=collections.defaultdict(float); byweek=collections.defaultdict(lambda:[0,0.0]); byleague=collections.defaultdict(lambda:[0,0.0])
    for r in rows:
        u=float(r['net_u']); byday[r['date']]+=u; byweek[r['iso_week']][0]+=1;byweek[r['iso_week']][1]+=u
        byleague[str(r['league'])][0]+=1;byleague[str(r['league'])][1]+=u
    cum=peak=mdd=0.0
    for d,u in sorted(byday.items()):
        cum+=u;peak=max(peak,cum);mdd=max(mdd,peak-cum)
    dates=span or [r['date'] for r in rows]
    weeks=set()
    if dates:
        lo=min(dt.date.fromisoformat(x) for x in dates);hi=max(dt.date.fromisoformat(x) for x in dates)
        for i in range((hi-lo).days+1): weeks.add(iso((lo+dt.timedelta(days=i)).isoformat()))
    n=len(rows);u=sum(float(r['net_u']) for r in rows)
    return {'orders':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(mdd,6),
      'observation_iso_weeks':len(weeks),'weekly_avg_orders':round(n/len(weeks),6) if weeks else 0,
      'active_iso_weeks':len(byweek),'orders_per_active_week':round(n/len(byweek),6) if byweek else 0,
      'settlements':dict(collections.Counter(r.get('settlement','frozen_membership_pnl') for r in rows)),
      'weekly':{k:{'orders':v[0],'net_u':round(v[1],6)} for k,v in sorted(byweek.items())},
      'by_league':{k:{'orders':v[0],'net_u':round(v[1],6),'roi_pct':round(100*v[1]/v[0],6)} for k,v in sorted(byleague.items(),key=lambda z:int(z[0]))}}


def main() -> None:
    crown, teammap = read_crown()
    cross_league_summary=json.loads(CROSS_LEAGUE_SUMMARY.read_text(encoding='utf-8'))
    expanded15=set(map(str,cross_league_summary['target_league_ids']))
    crown_leagues={str(r['league']) for r in crown}
    crosswalk_leagues={str(k[0]) for k in teammap}
    value_data, app_data, coverage = read_history_inputs(teammap)
    builder=make_team_value_builder(value_data,app_data)
    appearance_source_end=int(coverage['other']['appearance_max_day'])
    # Reverse only the already audited one-to-one Crown -> TM club mapping.
    reverse={(str(l),str(cid)):str(tm) for (l,cid),tm in teammap.items()}
    feats=[]; bad=collections.Counter(); roster_diag=collections.defaultdict(list)
    for r in crown:
        l=str(r['league']); target=dt.date.fromisoformat(str(r['date'])).toordinal()
        if target-HISTORY_DAY_EMBARGO > appearance_source_end:
            bad['appearance_history_does_not_reach_feature_cutoff']+=1
            continue
        hc=reverse.get((l,str(r['home_id'])));ac=reverse.get((l,str(r['away_id'])) )
        if not hc or not ac:
            bad['team_mapping_missing']+=1;continue
        hv=builder(hc,target);av=builder(ac,target)
        if hv is None or av is None:
            bad['one_or_both_team_value_unavailable']+=1;continue
        q=dict(r);q.update({'home_tm_club_id':hc,'away_tm_club_id':ac,'home_value_features':hv,'away_value_features':av,
          'feature_cutoff_date':dt.date.fromordinal(target-HISTORY_DAY_EMBARGO).isoformat(),
          'valuation_cutoff_date':dt.date.fromordinal(target-HISTORY_DAY_EMBARGO-VALUE_PUBLISH_LAG_DAYS).isoformat(),
          'home_value_age_days':hv['mean_value_age_days'],'away_value_age_days':av['mean_value_age_days']})
        feats.append(q);roster_diag[str(q['year'])].append((hv['mean_value_age_days'],av['mean_value_age_days']))
    if not feats:raise AssertionError('no fixtures with complete two-side squad valuation features')
    # Independently compute both-side Crown AH quarter-line cash flows.
    for r in feats:
        r['home_u'],r['home_state']=settle(r['al'],'home',int(r['hg']),int(r['ag']),float(r['ah']))
        r['away_u'],r['away_state']=settle(r['al'],'away',int(r['hg']),int(r['ag']),float(r['aa']))
        r['payout_diff_y']=r['home_u']-r['away_u']
    frozen={}
    with FROZEN_FILE.open(encoding='utf-8') as f:
        for line in f:
            z=json.loads(line);frozen[str(z['fid'])]=z
    if len(frozen)!=10294:raise AssertionError('frozen M8 membership changed')
    target=[r for r in feats if int(r['year']) in YEAR_TESTS]
    valid_year={y:[r for r in feats if int(r['year'])==y] for y in YEAR_TESTS}
    model_names=('CROWN_ONLY','VALUE_ONLY','CROWN_PLUS_VALUE','LOWER_PRICE')
    preds={m:{} for m in model_names};train_audit={}
    for year in YEAR_TESTS:
        tr=[r for r in feats if int(r['year'])<year]
        te=valid_year[year]
        if not tr or not te:train_audit[str(year)]={'train_n':len(tr),'test_n':len(te)};continue
        yc=np.array([r['payout_diff_y'] for r in tr])
        xc=np.array([crown_features(r) for r in tr]);zc=np.array([crown_features(r) for r in te])
        xv=np.array([value_features(r['home_value_features'],r['away_value_features']) for r in tr]);zv=np.array([value_features(r['home_value_features'],r['away_value_features']) for r in te])
        model_pred={'CROWN_ONLY':ridge_predict(xc,yc,zc),'VALUE_ONLY':ridge_predict(xv,yc,zv),'CROWN_PLUS_VALUE':ridge_predict(np.column_stack((xc,xv)),yc,np.column_stack((zc,zv)))}
        for method,values in model_pred.items():
            for row,value in zip(te,values):
                side='home' if value>=0 else 'away'
                preds[method][str(row['fid'])]={'fid':str(row['fid']),'year':int(row['year']),'date':str(row['date']),'iso_week':iso(str(row['date'])),'league':str(row['league']),
                  'home_id':str(row['home_id']),'away_id':str(row['away_id']),
                  'side':side,'price':float(row['ah'] if side=='home' else row['aa']),'line':float(row['al']),'net_u':float(row['home_u'] if side=='home' else row['away_u']),
                  'settlement':row['home_state'] if side=='home' else row['away_state'],'predicted_home_minus_away_u':float(value),'home_odds':float(row['ah']),'away_odds':float(row['aa']),
                  'FT_home':int(row['hg']),'FT_away':int(row['ag']),'feature_cutoff_date':row['feature_cutoff_date'],'valuation_cutoff_date':row['valuation_cutoff_date'],
                  'mean_value_age_home_days':row['home_value_age_days'],'mean_value_age_away_days':row['away_value_age_days'],'frozen_eight_overlap_posthoc':str(row['fid']) in frozen}
        for row in te:
            side='home' if float(row['ah'])<=float(row['aa']) else 'away'
            preds['LOWER_PRICE'][str(row['fid'])]={'fid':str(row['fid']),'year':int(row['year']),'date':str(row['date']),'iso_week':iso(str(row['date'])),'league':str(row['league']),
              'home_id':str(row['home_id']),'away_id':str(row['away_id']),
              'side':side,'price':float(row['ah'] if side=='home' else row['aa']),'line':float(row['al']),'net_u':float(row['home_u'] if side=='home' else row['away_u']),
              'settlement':row['home_state'] if side=='home' else row['away_state'],'predicted_home_minus_away_u':None,'home_odds':float(row['ah']),'away_odds':float(row['aa']),
              'FT_home':int(row['hg']),'FT_away':int(row['ag']),'feature_cutoff_date':row['feature_cutoff_date'],'valuation_cutoff_date':row['valuation_cutoff_date'],
              'mean_value_age_home_days':row['home_value_age_days'],'mean_value_age_away_days':row['away_value_age_days'],'frozen_eight_overlap_posthoc':str(row['fid']) in frozen}
        train_audit[str(year)]={'train_n':len(tr),'test_n':len(te),'training_years':f'<{year}','ridge_alpha':RIDGE_ALPHA}
    common_ids=set.intersection(*(set(preds[m]) for m in model_names)) if model_names else set()
    if any(not common_ids for m in model_names):raise AssertionError('missing common predicted FIDs')
    span=[str(r['date']) for r in target if str(r['fid']) in common_ids]
    models={}
    for m in model_names:
        all_rows=list(preds[m].values());inc=[r for r in all_rows if r['fid'] not in frozen]
        byyear={str(y):metrics([r for r in inc if r['year']==y],[r['date'] for r in target if int(r['year'])==y and r['fid'] in common_ids]) for y in YEAR_TESTS}
        models[m]={'test_unique_fids':len(all_rows),'frozen_overlap':len(set(r['fid'] for r in all_rows)&set(frozen)),
          'incremental_unique_fids':len({r['fid'] for r in inc}),'same_sample':metrics(all_rows,span),'incremental':metrics(inc,span),'incremental_by_year':byyear}
    # Same-horizon frozen baseline and model unions.
    fr=[{'fid':str(fid),'date':str(x['date']),'year':int(x['year']),'league':str(x.get('league','')),'iso_week':iso(str(x['date'])),'net_u':float(x['pnl'])} for fid,x in frozen.items() if int(x['year']) in YEAR_TESTS]
    frozen_same=metrics(fr,span)
    combined={}
    for m in ('CROWN_ONLY','VALUE_ONLY','CROWN_PLUS_VALUE'):
        inc=[r for r in preds[m].values() if r['fid'] not in frozen]
        combined[m]=metrics(fr+inc,span)
    # Live receipt inventory cannot establish a value snapshot timestamp; count FID overlap only.
    receipt_ids=set();receipt_rows=0
    with RECEIPTS.open(encoding='utf-8') as f:
        for line in f:
            x=json.loads(line);receipt_rows+=1;receipt_ids.add(str(x['fixture_id']))
    result={'study':'M8 retrospective squad-value proxy vs Crown T12 AH; historical source data has no publication/receipt evidence',
      'method':{'squad_proxy':'players with an appearance for a team during prior 365 days whose latest pre-cutoff appearance across mapped clubs remains at that team; use each player latest dated market value before target date minus 30 days',
        'no_target_lineup':True,'appearance_embargo_days':HISTORY_DAY_EMBARGO,'valuation_embargo_days':VALUE_PUBLISH_LAG_DAYS,
        'features':list(VALUE_FEATURES),'value_model':'fixed expanding-year Ridge alpha 100 predicts difference between Crown home and away one-unit net AH payout',
        'test_years':'2024, 2025, 2026; train only on earlier calendar years','frozen_eight':'post-prediction FID attribution only; not a feature','quarter_lines':'split into equal half-line legs','threshold_search':False},
      'coverage':{'crown_paired_fids':len(crown),'crown_league_ids':len(crown_leagues),'mapped_transfermarkt_league_ids':len(crosswalk_leagues),
        'expanded15_league_ids':sorted(expanded15,key=int),'expanded15_ids_in_paired_crown_inventory':sorted(expanded15&crown_leagues,key=int),
        'expanded15_ids_with_team_crosswalk':sorted(expanded15&crosswalk_leagues,key=int),
        'expanded15_paired_crown_fids':sum(1 for r in crown if str(r['league']) in expanded15),
        'features_two_sides':len(feats),'feature_missing_reasons':dict(bad),
        'test_feature_fids':len(common_ids),'test_fids_by_year':{str(y):sum(1 for r in target if str(r['fid']) in common_ids and int(r['year'])==y) for y in YEAR_TESTS},
        'test_date_range':[min(span),max(span)] if span else None,'frozen_overlap':len(set(common_ids)&set(frozen)),
        'incremental_unique_fids':len(set(common_ids)-set(frozen)),'valuation_age_days_by_year':{y:{'mean_home_away_days':round(float(np.mean([a for pair in pairs for a in pair])),2),'max':round(float(np.max([a for pair in pairs for a in pair])),2),'n':len(pairs)} for y,pairs in roster_diag.items()},
        'roster_snapshot_time_proven':False,'valuation_publication_time_proven':False,
        'true_receipt_archive_rows':receipt_rows,'true_receipt_unique_fids':len(receipt_ids),'receipt_fid_overlap_with_feature_test':len(receipt_ids & common_ids),'receipt_value_snapshot_timestamp_rows':0},
      'source_audit':{**coverage,'valuation_input_sha256':sha(VALUATIONS),'appearance_input_sha256':sha(APPEARANCES),'games_input_sha256':sha(GAMES),'crown_market_input_sha256':sha(MARKET)},
      'training_folds':train_audit,'frozen_eight_same_horizon':frozen_same,'models':models,'merged_frozen_eight_by_model':combined,
      'candidate_overlap':{'common_test_unique_fids':len(common_ids),'pairwise_test_overlap':{f'{a}__{b}':len(set(preds[a])&set(preds[b])) for i,a in enumerate(model_names) for b in model_names[i+1:]},
        'pairwise_incremental_overlap':{f'{a}__{b}':len(({r['fid'] for r in preds[a].values() if r['fid'] not in frozen}) & ({r['fid'] for r in preds[b].values() if r['fid'] not in frozen})) for i,a in enumerate(model_names) for b in model_names[i+1:]}},
      'inputs_sha256':{str(p):sha(p) for p in (GAMES,APPEARANCES,VALUATIONS,MARKET,FROZEN_FILE,RECEIPTS,PLAYER_BOOTSTRAP,CROSS_LEAGUE_SUMMARY)},
      'limits':['The valuation gzip is truncated; only complete newline-terminated records are retained, and its final partial CSV record is excluded.','Market-value record date is not proof of source publication or receipt time; valuation cutoff is a fixed conservative 30-day lag.','Appearance history is bulk retrospective data without observed receipt timestamps.','Active squad is an appearance-based proxy, not a verified roster or target lineup.','The valuation archive ends in 2024, so value ages in 2025-2026 grow stale; age is retained and reported.','Historical Crown event-time quotes are not live HTTP execution evidence.','2024-2026 are previously inspected M8 periods and not an untouched holdout.'],
      'original_eight_unchanged':len(frozen)==10294}
    ledger=[]
    for m in model_names:
        ledger.extend([{**r,'model':m,'historical_event_time_replay':True,'true_pregame_information_verified':False} for r in preds[m].values()])
    (OUT/'m8_squad_value_results_20261120.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with gzip.open(OUT/'squad_value_per_fixture_20261120.jsonl.gz','wt',encoding='utf-8') as f:
        for r in sorted(ledger,key=lambda x:(x['date'],x['fid'],x['model'])):f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print(json.dumps({'coverage':result['coverage'],'models':{k:v['incremental'] for k,v in models.items()},'years':{k:v['incremental_by_year'] for k,v in models.items()},'receipt':{'rows':receipt_rows,'unique_fids':len(receipt_ids),'overlap':len(receipt_ids&common_ids)}},ensure_ascii=False,default=str),flush=True)


if __name__ == '__main__':
    main()
