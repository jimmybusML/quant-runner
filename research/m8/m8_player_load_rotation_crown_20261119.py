#!/usr/bin/env python3
"""M8 player load / rotation versus Crown AH and OU, strictly time-forward.

Reads only already saved M8/Transfermarkt-derived data. It does not call APIs,
write source stores, change production models, or dispatch orders.
"""
from __future__ import annotations
import bisect, collections, csv, datetime as dt, gzip, hashlib, json, math, pathlib, statistics, sys

import numpy as np
import pandas as pd

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.m3.probabilities import settle_score
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
SRC=WORK/'m8_pregame_info_source_20261117'
OUT=ROOT/'research/m8/player_load_rotation_20261119'
OUT.mkdir(parents=True,exist_ok=True)
DATA_END=dt.date(2026,6,28)
YEAR_TESTS=(2024,2025,2026)
WINDOWS=(7,14,28,42,365)
RIDGE=100.0

def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def qdate(s):
    return dt.date.fromisoformat(str(s)[:10])

def iso_week(s):
    z=qdate(s).isocalendar(); return f'{z.year}-W{z.week:02}'

def settlement(market,line,side,hg,ag,odds):
    # Independent quarter-line settlement: split stake equally across adjacent
    # half-goal lines, then settle each leg as win/push/loss.
    line=float(line); odds=float(odds)
    if abs(line*4-round(line*4))>1e-7: raise ValueError(f'not quarter-grid: {line}')
    if market=='AH':
        adj=(int(hg)-int(ag)+line) if side=='home' else (int(ag)-int(hg)-line)
    elif market=='OU':
        total=int(hg)+int(ag)
        adj=(total-line) if side=='over' else (line-total)
    else: raise ValueError(market)
    twice=round(line*2)
    # Whole and half lines are one leg; quarter lines are adjacent half steps.
    if abs(twice/2-line)<1e-8: legs=[line]
    else: legs=[math.floor(line*2)/2, math.ceil(line*2)/2]
    def leg_pnl(l):
        if market=='AH':
            x=(int(hg)-int(ag)+l) if side=='home' else (int(ag)-int(hg)-l)
        else:
            t=int(hg)+int(ag); x=(t-l) if side=='over' else (l-t)
        return odds-1 if x>1e-9 else -1.0 if x<-1e-9 else 0.0
    return sum(leg_pnl(l) for l in legs)/len(legs)

# Reuse the already audited R49/R50 market + one-to-one team identity bootstrap.
# This prefix is read-only and ends before the old experiment writes any output.
prior= (ROOT/'research/m8/m8_prior_manager_turnover_20261117.py').read_text()
bootstrap=prior[:prior.index('# Build historical coach timeline')]
bootstrap_ns={}
exec(compile(bootstrap,'m8_prior_manager_turnover_20261117.py[prefix]','exec'),bootstrap_ns)
H=bootstrap_ns['H']; R=bootstrap_ns['R']; teammap=bootstrap_ns['teammap']
assert len(H)==38846 and len(R)==1230 and len(teammap)==453

foundation_root=WORK/'m8_foundation_20261115'
foundation=json.loads((foundation_root/'manifest.json').read_text())
members_path=WORK/foundation['historical_membership']['local_file']
members_sha=file_sha(members_path)
assert members_sha==foundation['historical_membership']['sha256']
frozen_rows=[json.loads(x) for x in members_path.open()]
frozen_by_fid={str(x['fid']):x for x in frozen_rows}
assert len(frozen_by_fid)==10294

# Load the 2024–2026 T12 paired Crown market cohort. H is already verified by
# the previous M8 market/FT pipeline; this script independently rechecks the
# raw quote and outcome again in its companion settlement verifier.
market_by_fid={str(x['fid']):dict(x) for x in H if int(x['year'])>=2019}
assert len(market_by_fid)==len(H)

mapped_clubs=set(map(str,teammap.values()))
club_names={str(v):str(k) for k,v in teammap.items()}
compmap={'1':'GB1','12':'IT1','14':'ES1','16':'L1','25':'FR1','29':'A1','31':'BE1','35':'TS1','37':'NL1','48':'PL1','51':'PO1','52':'RO1','61':'C1','62':'TR1','66':'SE1','70':'DK1','73':'JAP1','75':'RSK1','88':'NO1','141':'GR1','262':'SC1','290':'SA1','303':'SER1','319':'UKR1','26540':'KR1'}
comp_by_league={v:k for k,v in compmap.items()}

# Build event inventory from games.csv; preserve incomplete known team-games so
# their presence reduces an explicit source-coverage ratio rather than becoming
# zero-minute observations.
games_path=SRC/'games.csv.gz'
games=pd.read_csv(games_path,compression='gzip',usecols=['game_id','competition_id','date','home_club_id','away_club_id','home_club_goals','away_club_goals'],dtype={'game_id':'string','competition_id':'string','home_club_id':'string','away_club_id':'string'})
games['date']=pd.to_datetime(games['date'],errors='coerce').dt.date
games=games[games.date.notna() & (games.date<=DATA_END) & (games.home_club_id.isin(mapped_clubs)|games.away_club_id.isin(mapped_clubs))].copy()
game_meta={}; team_inventory=collections.defaultdict(list)
for z in games.itertuples(index=False):
    gid=str(z.game_id); comp=str(z.competition_id); day=z.date
    try: finished=pd.notna(z.home_club_goals) and pd.notna(z.away_club_goals)
    except: finished=False
    for side,club,opp in [('home',str(z.home_club_id),str(z.away_club_id)),('away',str(z.away_club_id),str(z.home_club_id))]:
        if club not in mapped_clubs: continue
        key=(gid,club)
        if key in game_meta: continue
        game_meta[key]={'game_id':gid,'club':club,'opponent':opp,'date':day,'ord':day.toordinal(),'competition':comp,'finished':bool(finished),'home_away':side}
        team_inventory[club].append(key)
for club in team_inventory: team_inventory[club].sort(key=lambda k:(game_meta[k]['ord'],k[0]))

# Stream lineups and appearances, retaining only club-games in the known games
# table. Each observed appearance is an actual row, never a missing-as-zero fill.
line_all=collections.defaultdict(set); line_start=collections.defaultdict(set); line_pos={}
lineup_path=SRC/'game_lineups.csv.gz'
with gzip.open(lineup_path,'rt',encoding='utf-8',newline='') as f:
    for z in csv.DictReader(f):
        club=str(z.get('club_id') or ''); gid=str(z.get('game_id') or ''); pid=str(z.get('player_id') or '')
        key=(gid,club)
        if not pid or key not in game_meta: continue
        line_all[key].add(pid)
        if z.get('type')=='starting_lineup':
            line_start[key].add(pid)
            pos=(z.get('position') or '').strip()
            if pos: line_pos[(key,pid)]=pos
        else:
            pos=(z.get('position') or '').strip()
            if pos: line_pos[(key,pid)]=pos

app_players=collections.defaultdict(set); app_positive=collections.defaultdict(set)
app_records=collections.defaultdict(list); app_duplicate=0
app_key_seen=set()
apps_path=SRC/'appearances.csv.gz'
with gzip.open(apps_path,'rt',encoding='utf-8',newline='') as f:
    for z in csv.DictReader(f):
        club=str(z.get('player_club_id') or ''); gid=str(z.get('game_id') or ''); pid=str(z.get('player_id') or '')
        key=(gid,club)
        if not pid or key not in game_meta: continue
        akey=(gid,club,pid)
        if akey in app_key_seen: app_duplicate+=1; continue
        app_key_seen.add(akey)
        try: mins=float(z.get('minutes_played') or 0)
        except: continue
        day=qdate(z['date']); comp=str(z.get('competition_id') or '')
        app_players[key].add(pid)
        if mins>0: app_positive[key].add(pid)
        app_records[key].append((day.toordinal(),gid,pid,comp,mins))

quality=collections.Counter(); events_by_club=collections.defaultdict(list); valid_keys=set()
for key,meta in game_meta.items():
    quality['known_club_games']+=1
    starts=line_start.get(key,set()); squads=line_all.get(key,set()); apps=app_players.get(key,set()); positive=app_positive.get(key,set())
    reasons=[]
    if not meta['finished']: reasons.append('no_verified_ft_in_games')
    if len(starts)!=11: reasons.append('starting_xi_not_11')
    if not starts<=positive: reasons.append('starter_without_positive_appearance')
    if not apps<=squads: reasons.append('appearance_outside_saved_lineup')
    if not squads: reasons.append('no_lineup_rows')
    if not reasons:
        meta['valid']=True; valid_keys.add(key); quality['complete_proxy_games']+=1
        meta['starts']=frozenset(starts); meta['squad']=frozenset(squads); meta['players']=[]
        # Only data rows in a finished, identity-matched, complete-XI proxy enter
        # the burden series. Position mapping comes only from that same prior game.
        for ord_,gid,pid,comp,mins in app_records.get(key,[]):
            if mins<=0: continue
            rawpos=line_pos.get((key,pid),'')
            low=rawpos.lower()
            role='GK' if low=='goalkeeper' else 'DEF' if any(x in low for x in ('back','defender','sweeper')) else 'MID' if 'midfield' in low else 'FWD' if any(x in low for x in ('forward','striker','attack','winger')) else 'OTHER'
            meta['players'].append((pid,mins,comp,role,pid in starts))
        events_by_club[meta['club']].append(meta)
    else:
        quality['incomplete_known_games']+=1
        for reason in reasons: quality['invalid_'+reason]+=1
        meta['valid']=False; meta['invalid_reasons']=reasons
for club in events_by_club:
    events_by_club[club].sort(key=lambda z:(z['ord'],z['game_id']))
    for i,z in enumerate(events_by_club[club]): z['seq']=i

# Coverage checks: date and positional categories are descriptive and not imputed.
pos_counts=collections.Counter()
for evs in events_by_club.values():
    for ev in evs:
        for pid,mins,comp,role,isstart in ev['players']:
            pos_counts[role]+=1
quality['duplicate_appearance_player_game_keys']=app_duplicate
quality['mapped_team_count']=len(mapped_clubs)
quality['mapped_league_count']=len(comp_by_league)

def role_for(pid,club,events):
    # Latest recorded prior match position; if unavailable/ambiguous, return OTHER.
    for e in reversed(events):
        if e['ord']>current_asof: continue
        for p,mi,co,ro,st in e['players']:
            if p==pid: return ro
    return 'OTHER'

def build_team_features(club,target_day,target_comp):
    """Features from verified prior team-game/appearance rows; missing stays NaN."""
    target_ord=target_day.toordinal(); cutoff=target_ord-3 # exclude target day and prior two UTC dates
    all_known=[game_meta[k] for k in team_inventory.get(club,[]) if game_meta[k]['ord']<=cutoff]
    known365=[e for e in all_known if e['ord']>=cutoff-364]
    valid_all=[e for e in events_by_club.get(club,[]) if e['ord']<=cutoff]
    valid365=[e for e in valid_all if e['ord']>=cutoff-364]
    if not valid365: return None, {'reason':'no_verified_prior_365d_game','known365':len(known365),'valid365':0}
    cov365=len(valid365)/len(known365) if known365 else None
    # For each requested window, sum only observed actual minutes from verified
    # team-games. When there is no observed game, retain missing rather than 0.
    rows365=[(e,p) for e in valid365 for p in e['players']]
    byplayer=collections.defaultdict(lambda:{'365':0.0,'7':0.0,'14':0.0,'28':0.0,'42':0.0,'comp365':collections.Counter(),'games':[],'roles365':collections.Counter()})
    for e,p in rows365:
        pid,mins,comp,role,isstart=p
        d=e['ord']; rec=byplayer[pid]; rec['365']+=mins; rec['comp365'][comp]+=mins; rec['roles365'][role]+=mins
        rec['games'].append((d,e['game_id'],mins,comp,role,isstart))
        for w in (7,14,28,42):
            if d>=cutoff-w+1: rec[str(w)]+=mins
    for pid in byplayer:
        byplayer[pid]['games'].sort()
    total365=sum(v['365'] for v in byplayer.values())
    if total365<=0: return None, {'reason':'no_positive_minutes_365d','known365':len(known365),'valid365':len(valid365)}
    ranked=sorted(byplayer,key=lambda p:(-byplayer[p]['365'],p))
    top5=ranked[:5]; top11=ranked[:11]
    def total_window(w):
        vals=[p[1] for e in valid_all if e['ord']>=cutoff-w+1 for p in e['players']]
        return sum(vals) if vals else None
    f={}
    for w in WINDOWS:
        f[f'team_minutes_{w}']=total_window(w)
    for k,ids in [('top1',ranked[:1]),('top5',top5),('top11',top11)]:
        for w in (7,14,28,42,365):
            vals=[byplayer[pid][str(w) if w!=365 else '365'] for pid in ids]
            f[f'{k}_minutes_{w}']=sum(vals) if vals else None
    shares=sorted((v['365']/total365 for v in byplayer.values()),reverse=True)
    f['top1_share_365']=shares[0] if shares else None
    f['top5_share_365']=sum(shares[:5]) if shares else None
    f['top11_share_365']=sum(shares[:11]) if shares else None
    f['hhi_365']=sum(x*x for x in shares) if shares else None
    f['observed_players_365']=len(byplayer)
    f['verified_games_365']=len(valid365); f['known_games_365']=len(known365); f['coverage_365']=cov365
    for w in (7,14,28,42):
        known=[e for e in all_known if e['ord']>=cutoff-w+1]
        valid=[e for e in valid_all if e['ord']>=cutoff-w+1]
        f[f'coverage_{w}']=len(valid)/len(known) if known else None
        f[f'games_{w}']=len(valid) if valid else None
        comps={e['competition'] for e in valid if e['competition']}
        f[f'competitions_{w}']=len(comps) if valid else None
    # Recent load relative to the player's prior-365 usage rate (top 11 only).
    for w in (7,14,28,42):
        ratios=[]
        for pid in top11:
            annual=byplayer[pid]['365']; recent=byplayer[pid][str(w)]
            expected=annual*w/365.0
            if expected>0: ratios.append(recent/expected)
        f[f'top11_load_rate_{w}']=float(np.mean(ratios)) if ratios else None
    # Previous lineups, preceding match rotation and substitute minutes.
    prior=[e for e in valid_all if e['ord']<=cutoff]
    valid_by_key={(e['game_id'],e['club']):e for e in prior}
    known_prior=[e for e in all_known if e['ord']<=cutoff]
    last2_meta=known_prior[-2:]
    last2=[valid_by_key.get((e['game_id'],e['club'])) for e in last2_meta]
    last2=last2 if len(last2)==2 and all(last2) else []
    if len(last2)==2:
        x,y=last2[-2]['starts'],last2[-1]['starts']; inter=len(x&y); union=len(x|y)
        f['xi_repeat_count_prev2']=inter; f['xi_jaccard_prev2']=inter/union if union else None
        e=last2[-1]; total=sum(p[1] for p in e['players']); sub=sum(p[1] for p in e['players'] if not p[4])
        f['last_game_sub_minutes_share']=sub/total if total>0 else None
        f['last_game_sub_minutes']=sub if total>0 else None
        last5_meta=known_prior[-5:]
        five=[valid_by_key.get((z['game_id'],z['club'])) for z in last5_meta]
        five=five if len(five)==5 and all(five) else []
        if len(five)==5:
            f['unique_starters_prev5']=len(set().union(*(e['starts'] for e in five)))
            f['mean_xi_repeat_prev5']=float(np.mean([len(five[j]['starts']&five[j-1]['starts']) for j in range(1,5)]))
        else:
            f['unique_starters_prev5']=None;f['mean_xi_repeat_prev5']=None
    else:
        for k in ('xi_repeat_count_prev2','xi_jaccard_prev2','last_game_sub_minutes_share','last_game_sub_minutes','unique_starters_prev5','mean_xi_repeat_prev5'): f[k]=None
    # Main-player current streak/recency, only across fully verified prior team games.
    streaks=[]; recencies=[]; gaps=[]
    last5_meta=known_prior[-5:]
    tail=[valid_by_key.get((z['game_id'],z['club'])) for z in last5_meta]
    tail=tail if len(tail)==5 and all(tail) else []
    if len(tail)==5:
        for pid in top11:
            played=[pid in {p[0] for p in e['players']} for e in tail]
            streak=0
            for yes in reversed(played):
                if not yes: break
                streak+=1
            streaks.append(streak)
            appearances=[e['ord'] for e in prior if pid in {p[0] for p in e['players']}]
            recencies.append(cutoff-appearances[-1] if appearances else None)
            if len(appearances)>=2: gaps.append(appearances[-1]-appearances[-2])
    f['top11_consecutive_appearances_5max']=max(streaks) if streaks else None
    f['top11_consecutive_appearances_5mean']=float(np.mean(streaks)) if streaks else None
    recencies=[x for x in recencies if x is not None]
    f['top11_days_since_appearance_mean']=float(np.mean(recencies)) if recencies else None
    f['top11_interappearance_gap_mean']=float(np.mean(gaps)) if gaps else None
    # Per-position observed minute loads; OTHER preserves unknown positions.
    for role in ('GK','DEF','MID','FWD'):
        for w in (42,365):
            vals=[p[1] for e in valid365 if e['ord']>=cutoff-w+1 for p in e['players'] if p[3]==role]
            f[f'{role}_minutes_{w}']=sum(vals) if vals else None
    # Current domestic target competition activity; all-competition loads above.
    comp=target_comp
    for w in (14,28,42,365):
        vals=[p[1] for e in valid365 if e['ord']>=cutoff-w+1 and e['competition']==comp for p in e['players']]
        f[f'target_comp_minutes_{w}']=sum(vals) if vals else None
    # Expose the source coverage in model features; no absent-event value is imputed.
    f['invalid_known_games_365']=max(0,len(known365)-len(valid365))
    f['source_team_history_days']=cutoff-min(e['ord'] for e in valid365)
    return f, {'reason':None,'known365':len(known365),'valid365':len(valid365),'coverage365':cov365}

# Compute historical event-time features. Target-day appearances and the prior
# two UTC dates are excluded because no exact completion times are supplied.
rows=[]; feature_qc=collections.Counter(); current_asof=0
target_h=[x for x in H if qdate(x['date'])<=DATA_END]
team_feature_cache={}
for ix,r in enumerate(target_h,1):
    l=str(r['league']); hc=teammap.get((l,str(r['home_id']))); ac=teammap.get((l,str(r['away_id'])))
    if not hc or not ac:
        feature_qc['unmapped_target_team']+=1; continue
    day=qdate(r['date']); current_asof=day.toordinal()-3
    comp=compmap.get(l)
    hk=(str(hc),day.isoformat(),comp); ak=(str(ac),day.isoformat(),comp)
    if hk not in team_feature_cache: team_feature_cache[hk]=build_team_features(str(hc),day,comp)
    if ak not in team_feature_cache: team_feature_cache[ak]=build_team_features(str(ac),day,comp)
    hf,hq=team_feature_cache[hk]; af,aq=team_feature_cache[ak]
    if hf is None or af is None:
        feature_qc['missing_team_history']+=1; continue
    # The common sample is only rows where every experimental family is finite.
    pair={}
    allkeys=set(hf)&set(af)
    for k in sorted(allkeys):
        if hf[k] is not None and af[k] is not None and math.isfinite(float(hf[k])) and math.isfinite(float(af[k])):
            pair['h_'+k]=float(hf[k]); pair['a_'+k]=float(af[k])
    required=['team_minutes_'+str(w) for w in WINDOWS]
    required += [f'{rank}_minutes_{w}' for rank in ('top1','top5','top11') for w in (7,14,28,42,365)]
    required += ['top1_share_365','top5_share_365','top11_share_365','hhi_365','observed_players_365','coverage_365','invalid_known_games_365','source_team_history_days']
    required += [f'coverage_{w}' for w in (7,14,28,42)]+[f'games_{w}' for w in (7,14,28,42)]+[f'competitions_{w}' for w in (7,14,28,42)]
    required += [f'target_comp_minutes_{w}' for w in (14,28,42,365)]
    required += ['xi_jaccard_prev2','last_game_sub_minutes_share','unique_starters_prev5','mean_xi_repeat_prev5','top11_load_rate_7','top11_load_rate_14','top11_load_rate_28','top11_load_rate_42','top11_consecutive_appearances_5mean','top11_consecutive_appearances_5max','top11_days_since_appearance_mean','top11_interappearance_gap_mean']
    required += [f'{role}_minutes_{w}' for role in ('GK','DEF','MID','FWD') for w in (42,365)]
    missing_required=[k for k in required if ('h_'+k not in pair or 'a_'+k not in pair)]
    if missing_required:
        feature_qc['missing_required_model_feature']+=1
        for k in missing_required: feature_qc['missing_required:'+k]+=1
        continue
    z=dict(r); z.update(pair)
    z.update({'fixture_date_cutoff_utc':(day-dt.timedelta(days=3)).isoformat(),'player_data_cutoff_utc':DATA_END.isoformat(),
      'home_tm_club_id':str(hc),'away_tm_club_id':str(ac),'home_source_coverage_365':hq.get('coverage365'),'away_source_coverage_365':aq.get('coverage365'),
      'home_known_tm_games_365':hq.get('known365'),'away_known_tm_games_365':aq.get('known365'),
      'home_verified_tm_games_365':hq.get('valid365'),'away_verified_tm_games_365':aq.get('valid365'),
      'source_observed_minutes_only':True,'player_information_received_at_available':False,
      'frozen_eight_overlap_posthoc':str(r['fid']) in frozen_by_fid})
    rows.append(z); feature_qc['paired_features_built']+=1
    if ix%3000==0: print('FEATURE_PROGRESS',ix,'/',len(target_h),'paired',len(rows),flush=True)

if not rows:
    print('FEATURE_REJECTIONS',dict(feature_qc),flush=True)
    raise RuntimeError('no common features were built')

# Keep one fixed feature matrix and identical row support for all variants.
# Columns are retained only if both clubs have observed values on every row;
# nothing missing is imputed as zero.
all_row_feature_sets=[{k for k in r if k.startswith('h_') or k.startswith('a_')} for r in rows]
ALL_FEATURE_KEYS=sorted(set.intersection(*all_row_feature_sets)) if all_row_feature_sets else []
common_feature_names=sorted({k[2:] for k in ALL_FEATURE_KEYS if k.startswith('h_') and 'a_'+k[2:] in ALL_FEATURE_KEYS})
common_rows=[]
for r in rows:
    if all(('h_'+k in r and 'a_'+k in r and math.isfinite(float(r['h_'+k])) and math.isfinite(float(r['a_'+k]))) for k in common_feature_names): common_rows.append(r)
feature_qc['incomplete_any_model_feature_after_column_intersection']=len(rows)-len(common_rows)
rows=common_rows
ALL_FEATURE_KEYS=[k for k in rows[0] if k.startswith('h_') or k.startswith('a_')]
LOAD_KEYS=[k for k in ALL_FEATURE_KEYS if any(w in k for w in ['team_minutes_','top1_minutes_','top5_minutes_','top11_minutes_','top11_load_rate_','target_comp_minutes_','competitions_','games_'])]
CONC_KEYS=[k for k in ALL_FEATURE_KEYS if any(x in k for x in ['top1_share_365','top5_share_365','top11_share_365','hhi_365','observed_players_365'])]
ROT_KEYS=[k for k in ALL_FEATURE_KEYS if any(x in k for x in ['xi_repeat_','xi_jaccard_','last_game_sub_','unique_starters_','mean_xi_repeat_','consecutive_appearances_','days_since_appearance','interappearance_gap'])]
DIFF_KEYS=[]
for k in sorted(ALL_FEATURE_KEYS):
    if k.startswith('h_'):
        a='a_'+k[2:]
        if a in rows[0]: DIFF_KEYS.append(k)
assert LOAD_KEYS and CONC_KEYS and ROT_KEYS and DIFF_KEYS

def market_vec(r,market):
    if market=='AH': line=float(r['al']); a=float(r['ah']); b=float(r['aa'])
    else: line=float(r['ol']); a=float(r['oo']); b=float(r['ou'])
    inv_a,inv_b=1/a,1/b; s=inv_a+inv_b
    return np.array([line,inv_a/s, s-1, (inv_a-inv_b)/s, abs(line), line*((inv_a-inv_b)/s)],float)

def pair_vectors(r,keys,include_sum=True):
    out=[]
    for k in keys:
        if not k.startswith('h_'): continue
        a='a_'+k[2:]
        if a not in r: continue
        h=float(r[k]); aw=float(r[a])
        out.append(h-aw)
        if include_sum: out.append(h+aw)
    return np.asarray(out,float)

MODEL_GROUPS={
 'A_crown_market_only':('market',[]),
 'B_crown_plus_cumulative_load':('market',LOAD_KEYS),
 'C_crown_plus_load_concentration':('market',CONC_KEYS),
 'D_crown_plus_rotation':('market',ROT_KEYS),
 'E_crown_plus_team_load_differences':('market',DIFF_KEYS),
 'F_crown_plus_all_player_features':('market',ALL_FEATURE_KEYS),
 'G_player_features_only':('players',ALL_FEATURE_KEYS),
}

def design(r,market,group):
    kind,keys=MODEL_GROUPS[group]
    xs=[] if kind=='players' else list(market_vec(r,market))
    if keys: xs+=list(pair_vectors(r,keys,include_sum=(group!='E_crown_plus_team_load_differences')))
    return np.asarray([1.0,*xs],float)

def calc_metrics(records,pnl_key):
    if not records: return {'n':0,'net_U':0.0,'ROI_pct':None,'max_drawdown_U':0.0,'active_weeks':0,'calendar_weeks':0,'avg_per_calendar_week':0.0,'avg_per_active_week':None}
    vs=[float(x[pnl_key]) for x in records]; n=len(vs); dates=sorted(set(x['date'] for x in records))
    daily=collections.defaultdict(float); weekc=collections.Counter(); weeku=collections.defaultdict(float)
    for x in records: daily[x['date']]+=float(x[pnl_key]); week=iso_week(x['date']); weekc[week]+=1; weeku[week]+=float(x[pnl_key])
    c=peak=mdd=0.0
    for d in sorted(daily): c+=daily[d]; peak=max(peak,c); mdd=max(mdd,peak-c)
    d0=qdate(min(x['date'] for x in records)); d1=qdate(max(x['date'] for x in records))
    weeks=set(); day=d0
    while day<=d1:
        weeks.add(iso_week(day.isoformat())); day+=dt.timedelta(days=7)
    u=round(sum(vs),6)
    return {'n':n,'net_U':round(u,6),'ROI_pct':round(100*u/n,6),'max_drawdown_U':round(mdd,6),
      'active_weeks':len(weekc),'calendar_weeks':len(weeks),'avg_per_calendar_week':round(n/max(1,len(weeks)),6),
      'avg_per_active_week':round(n/len(weekc),6) if weekc else None,
      'positive_weeks':sum(1 for w,v in weeku.items() if v>1e-10),'negative_weeks':sum(1 for w,v in weeku.items() if v<-1e-10),
      'weekly_net_U':{k:round(v,6) for k,v in sorted(weeku.items())}}

def score_predictions(pr,market):
    if not pr: return {}
    y=np.array([r['target_delta_U'] for r in pr],float); p=np.array([r['prediction_delta_U'] for r in pr],float)
    mae=float(np.mean(np.abs(y-p))); mse=float(np.mean((y-p)**2)); corr=float(np.corrcoef(y,p)[0,1]) if np.std(p)>0 and np.std(y)>0 else None
    acc=float(np.mean((y>=0)==(p>=0)))
    return {'n':len(pr),'MSE_delta_U':round(mse,6),'MAE_delta_U':round(mae,6),'prediction_realized_correlation':round(corr,6) if corr is not None else None,'side_sign_accuracy':round(acc,6)}

# Only target years have model predictions. 2026 ends at the actual player-file
# cutoff; later-year Crown rows are recorded as not feature-available.
models={}; predictions=[]; train_meta={}; annual_summary={}
for market in ('AH','OU'):
    for model in MODEL_GROUPS:
        key=(market,model); models[key]={};
    for year in YEAR_TESTS:
        train=[r for r in rows if int(r['year'])<year]
        test=[r for r in rows if int(r['year'])==year]
        if not train or not test: continue
        for model in MODEL_GROUPS:
            X=np.vstack([design(r,market,model) for r in train])
            tr_delta=np.array([(float(r['home_U'])-float(r['away_U'])) if market=='AH' else (float(r['over_U'])-float(r['under_U'])) for r in train])
            mu=X.mean(axis=0); sd=X.std(axis=0); mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
            xs=(X-mu)/sd; pen=np.eye(xs.shape[1])*RIDGE;pen[0,0]=0
            beta=np.linalg.solve(xs.T@xs+pen,xs.T@tr_delta)
            tx=np.vstack([design(r,market,model) for r in test]); pred=((tx-mu)/sd)@beta
            train_meta[f'{market}|{model}|{year}']={'training_n':len(train),'train_year_min':min(int(r['year']) for r in train),'train_year_max':max(int(r['year']) for r in train),'test_n':len(test),'ridge_alpha':RIDGE,'feature_count':int(xs.shape[1]-1),'beta':beta.tolist()}
            for r,pred_d in zip(test,pred):
                side_a='home' if market=='AH' else 'over'; side_b='away' if market=='AH' else 'under'
                u_a=float(r[side_a+'_U']);u_b=float(r[side_b+'_U']); side=side_a if pred_d>=0 else side_b
                predictions.append({'fid':str(r['fid']),'market':market,'model':model,'year':year,'date':r['date'],'league':str(r['league']),'side':side,
                  'line':float(r['al'] if market=='AH' else r['ol']),
                  'AH_home_odds':float(r['ah']),'AH_away_odds':float(r['aa']),
                  'OU_over_odds':float(r['oo']),'OU_under_odds':float(r['ou']),
                  'actual_side_U':u_a if side==side_a else u_b,'home_U':float(r['home_U']),'away_U':float(r['away_U']),'over_U':float(r['over_U']),'under_U':float(r['under_U']),
                  'target_delta_U':float((float(r['home_U'])-float(r['away_U'])) if market=='AH' else (float(r['over_U'])-float(r['under_U']))),
                  'prediction_delta_U':float(pred_d),'frozen_eight_overlap_posthoc':bool(r['frozen_eight_overlap_posthoc']),
                  'raw_source_feature_date_cutoff_utc':r['fixture_date_cutoff_utc'],'source_first_published_at':None,'source_received_at':None,
                  'player_data_is_historical_archive_not_real_time_receipt':True})
        print('MODEL_PROGRESS',market,year,'train',len(train),'test',len(test),flush=True)

def set_pnl(records,market,model,year=None,outside_only=False):
    return [x for x in records if x['market']==market and x['model']==model and (year is None or int(x['year'])==year) and (not outside_only or not x['frozen_eight_overlap_posthoc'])]

# Fair common sample and isolated incremental rows by unique FID. Model families
# share exactly the same FIDs; only the side selected by predictions differs.
frozen_valid=[]
for fid,x in frozen_by_fid.items():
    if int(x['year']) in YEAR_TESTS and qdate(x['date'])<=DATA_END:
        frozen_valid.append({'fid':fid,'year':int(x['year']),'date':x['date'],'pnl':float(x['pnl'])})
models_summary={}; market_baseline_loss={}
for market in ('AH','OU'):
    for model in MODEL_GROUPS:
        subset=[x for x in predictions if x['market']==market and x['model']==model]
        inc=[x for x in subset if not x['frozen_eight_overlap_posthoc']]
        peryear={str(y):{'all_feature_common':calc_metrics([x for x in subset if x['year']==y],'actual_side_U'),
                         'outside_frozen_eight_increment':calc_metrics([x for x in inc if x['year']==y],'actual_side_U')} for y in YEAR_TESTS}
        allmetrics=calc_metrics(subset,'actual_side_U'); incmetrics=calc_metrics(inc,'actual_side_U')
        perf=score_predictions(subset,market)
        base_model='A_crown_market_only'
        if model==base_model: market_baseline_loss[(market,'all')]=perf
        if model=='A_crown_market_only': delta_mse=0.0
        else:
            base=[x for x in predictions if x['market']==market and x['model']==base_model]
            b=score_predictions(base,market); delta_mse=(b['MSE_delta_U']-perf['MSE_delta_U'])/b['MSE_delta_U'] if b and b.get('MSE_delta_U') else None
        # A–F AH models are additional Crown AH bets only on FIDs outside the
        # frozen membership. OU is reported separately and never blended into AH.
        combined=None
        if market=='AH':
            out_by={x['fid']:x for x in inc}
            merged=[{'fid':x['fid'],'date':x['date'],'pnl':x['pnl']} for x in frozen_valid]
            merged += [{'fid':x['fid'],'date':x['date'],'pnl':x['actual_side_U']} for x in inc]
            assert len({x['fid'] for x in merged})==len(merged)
            combined=calc_metrics(merged,'pnl')
        models_summary[f'{market}|{model}']={'annual':peryear,'common_sample_all_fids':allmetrics,'unique_outside_frozen_eight':incmetrics,
          'out_of_sample_prediction_quality_common':perf,'MSE_improvement_vs_Crown_only_same_rows_pct':round(100*delta_mse,6) if delta_mse is not None else None,
          'combined_with_frozen_eight_AH_same_horizon':combined}

# Historical sample with data provenance and full model predictions.
pred_map={(x['fid'],x['market'],x['model']):x for x in predictions}
row_fields=[]
for r in rows:
    base={'fid':str(r['fid']),'year':int(r['year']),'date':r['date'],'league':str(r['league']),'home_id':str(r['home_id']),'away_id':str(r['away_id']),
      'home_tm_club_id':r['home_tm_club_id'],'away_tm_club_id':r['away_tm_club_id'],'fixture_date_cutoff_utc':r['fixture_date_cutoff_utc'],
      'frozen_eight_overlap_posthoc':r['frozen_eight_overlap_posthoc'],'source_cutoff_complete':qdate(r['date'])<=DATA_END,
      'home_source_coverage_365':r['home_source_coverage_365'],'away_source_coverage_365':r['away_source_coverage_365'],
      'home_known_tm_games_365':r['home_known_tm_games_365'],'away_known_tm_games_365':r['away_known_tm_games_365'],
      'home_verified_tm_games_365':r['home_verified_tm_games_365'],'away_verified_tm_games_365':r['away_verified_tm_games_365'],
      'crown_T12_AH_line':float(r['al']),'crown_T12_AH_home_odds':float(r['ah']),'crown_T12_AH_away_odds':float(r['aa']),
      'crown_T12_OU_line':float(r['ol']),'crown_T12_OU_over_odds':float(r['oo']),'crown_T12_OU_under_odds':float(r['ou']),
      'FT_home':int(r['hg']),'FT_away':int(r['ag']),'AH_home_U':float(r['home_U']),'AH_away_U':float(r['away_U']),'OU_over_U':float(r['over_U']),'OU_under_U':float(r['under_U'])}
    for k,v in r.items():
        if (k.startswith('h_') or k.startswith('a_')) and k not in base: base[k]=v
    for market in ('AH','OU'):
        for model in MODEL_GROUPS:
            p=pred_map.get((base['fid'],market,model))
            if p:
                prefix=f'{market}|{model}|'
                base[prefix+'side']=p['side'];base[prefix+'prediction_delta_U']=p['prediction_delta_U'];base[prefix+'settled_U']=p['actual_side_U']
    row_fields.append(base)

# Actual-receipt stock: archived verified pairs from M8/MR1 plus post-Nov-14
# verified Crown AH snapshots. Player archive itself has no as-received time.
receipt_archive=WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
receipt_records=[]
if receipt_archive.exists():
    for line in receipt_archive.open():
        z=json.loads(line); receipt_records.append(z)
receipt_fids={str(x['fixture_id']) for x in receipt_records}
receipt_dates={str(x['fixture_id']):str(x['kickoff_utc'])[:10] for x in receipt_records}
mr1_index=pathlib.Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23/snapshot-index.jsonl')
mr1_verified_after=[]; mr1_hashes={'snapshot_check':0,'snapshot_ok':0,'raw_body_check':0,'raw_body_ok':0}
if mr1_index.exists():
    for line in mr1_index.open():
        z=json.loads(line)
        if str(z.get('committed_at',''))<'2026-11-14T00:00:00': continue
        sp=pathlib.Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23')/z.get('snapshot_path','')
        if not sp.is_file(): continue
        mr1_hashes['snapshot_check']+=1
        if file_sha(sp)==z.get('snapshot_sha256'): mr1_hashes['snapshot_ok']+=1
        try: snap=json.loads(sp.read_text())
        except Exception: continue
        if snap.get('classification')!='SNAPSHOT_OK' or snap.get('source_bookmaker')!='crown' or snap.get('source_bookmaker_verified') is not True: continue
        rec=snap.get('received_at'); kick=snap.get('kickoff_at'); ah=snap.get('AH')
        if not (rec and kick and rec<kick and snap.get('prematch_valid') and isinstance(ah,dict) and ah.get('line') is not None and ah.get('home_price') is not None and ah.get('away_price') is not None): continue
        mr1_verified_after.append({'fid':str(snap.get('match_id')),'kickoff_utc':kick,'received_utc':rec,'snapshot_sha256':z.get('snapshot_sha256')})
        receipt_fids.add(str(snap.get('match_id')));receipt_dates[str(snap.get('match_id'))]=str(kick)[:10]

receipt_feature_rows=sum(1 for fid,d in receipt_dates.items() if qdate(d)<=DATA_END and fid in {x['fid'] for x in rows})
receipt_oos_candidate_fids={str(x['fixture_id']) for x in receipt_records if int(str(x.get('kickoff_utc','')[:4] or 0) or 0)>=2026 and x.get('received_utc') and x.get('raw_sha256') and x.get('snapshot_sha256')}
receipt_audit={'archived_actual_receipt_rows':len(receipt_records),'archived_actual_receipt_unique_fids':len({str(x['fixture_id']) for x in receipt_records}),
  'post_2026_11_14_verified_mr1_crown_ah_fids':len({x['fid'] for x in mr1_verified_after}),
  'post_2026_11_14_verified_mr1_receipt_records':len(mr1_verified_after),'snapshot_file_hash_audit':mr1_hashes,
  'receipt_union_unique_fids':len(receipt_fids),'receipt_union_kickoff_min':min(receipt_dates.values()) if receipt_dates else None,'receipt_union_kickoff_max':max(receipt_dates.values()) if receipt_dates else None,
  'receipt_fids_kickoff_after_player_source_cutoff':sum(1 for d in receipt_dates.values() if qdate(d)>DATA_END),
  'receipt_fids_with_historical_player_feature_rows':receipt_feature_rows,
  'archived_R50_verified_paired_receipt_fids':len({str(x['fid']) for x in R}),
  'receipt_real_time_player_information_snapshot_count':0,
  'reason':'appearances and lineups files have no first-published/received timestamps; appearances stop 2026-06-28; archived MR1 receipt sample is Oct-Nov 2026, beyond the personnel data cutoff. No current player feature can be represented as contemporaneously received.'}

# All candidate model variants use the same FIDs in each market/year.
overlap={}
for market in ('AH','OU'):
    fids={m:{x['fid'] for x in predictions if x['market']==market and x['model']==m} for m in MODEL_GROUPS}
    overlap[market]={'unique_test_fids':len(set().union(*fids.values())),'per_model_fids':{m:len(v) for m,v in fids.items()},
      'pairwise_intersection':{f'{a}__{b}':len(fids[a]&fids[b]) for i,a in enumerate(MODEL_GROUPS) for b in list(MODEL_GROUPS)[i+1:]}}

summary={
 'study':'M8_PLAYER_ACTUAL_MINUTES_ROTATION_VS_CROWN_AH_OU_20261119',
 'method':'Event-date-only Transfermarkt-derived player appearances and prior game lineups, strict UTC-date embargo of target match day and previous two days, train on prior target years only, Crown-only AH/OU quote and settlement, equal comparison cohort for each model family. Historical event-time backtest is not real-time player information.',
 'source_data':{},
 'frozen_eight':{
   'members':len(frozen_by_fid),'membership_sha256':members_sha,'manifest_sha256':file_sha(foundation_root/'manifest.json'),
   'AH_horizon':'Original frozen M8 membership PnL is preserved as its own trade. New AH models are added only on FIDs outside membership; OU is never merged into AH.'},
 'data_integrity':dict(quality),
 'position_observed_minutes_rows_by_role':dict(pos_counts),
 'feature_coverage':{
   'targets_2024_2026_to_source_cutoff':len(target_h),'paired_common_features':len(rows),'rejections':dict(feature_qc),
   'year_counts':{str(y):sum(int(r['year'])==y for r in rows) for y in YEAR_TESTS},
   'incremental_outside_frozen_by_year':{str(y):sum(int(r['year'])==y and not r['frozen_eight_overlap_posthoc'] for r in rows) for y in YEAR_TESTS},
   'post_source_cutoff_market_rows_not_used_as_player_features':sum(int(r['year'])==2026 and qdate(r['date'])>DATA_END for r in H),
   'common_sample_uses_recorded_minutes_only_no_missing_as_zero':True
 },
 'receipt_audit':receipt_audit,'models':models_summary,'pairwise_fid_overlap':overlap,'training':train_meta,
 'all_parameters_are_research_only':True,'no_production_changes':True
}

for name in ['appearances.csv.gz','games.csv.gz','game_lineups.csv.gz','transfers.csv.gz','player_valuations.csv.gz','competitions.csv.gz']:
    p=SRC/name
    integrity={'path':str(p),'sha256':file_sha(p),'bytes':p.stat().st_size}
    try:
        with gzip.open(p,'rt',encoding='utf-8',newline='') as f:
            reader=csv.DictReader(f); integrity['columns']=reader.fieldnames; n=0; min_day=None;max_day=None; bad=0
            date_field='date' if 'date' in (reader.fieldnames or []) else 'transfer_date' if 'transfer_date' in (reader.fieldnames or []) else None
            for rr in reader:
                n+=1
                if date_field and rr.get(date_field):
                    v=str(rr[date_field])[:10]
                    try: d=qdate(v); min_day=min(d,min_day) if min_day else d;max_day=max(d,max_day) if max_day else d
                    except: bad+=1
            integrity.update({'rows':n,'date_field':date_field,'date_min':min_day.isoformat() if min_day else None,'date_max':max_day.isoformat() if max_day else None,'bad_dates':bad,'gzip_integrity':'ok'})
    except Exception as e: integrity.update({'gzip_integrity':'error','read_error':type(e).__name__+': '+str(e)})
    summary['source_data'][name]=integrity

# The main predictions file is one complete row per model × market × fixture.
ledger=OUT/'player_load_rotation_walkforward_ledger_20261119.jsonl.gz'
with gzip.open(ledger,'wt',encoding='utf-8',newline='') as f:
    for x in predictions:
        # Attach all research feature values to each model-market forecast row.
        f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
(OUT/'M8_PLAYER_LOAD_ROTATION_RESULTS_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(OUT/'m8_player_load_rotation_feature_rows_20261119.jsonl.gz').write_bytes(b'')
with gzip.open(OUT/'m8_player_load_rotation_feature_rows_20261119.jsonl.gz','wt',encoding='utf-8') as f:
    for x in row_fields: f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'coverage':summary['feature_coverage'],'integrity':summary['data_integrity'],'receipt':receipt_audit,'models':{k:{'all':v['common_sample_all_fids'],'increment':v['unique_outside_frozen_eight'],'combined':v['combined_with_frozen_eight_AH_same_horizon'],'quality':v['out_of_sample_prediction_quality_common'],'mse_lift':v['MSE_improvement_vs_Crown_only_same_rows_pct']} for k,v in models_summary.items()}},ensure_ascii=False,default=str),flush=True)
