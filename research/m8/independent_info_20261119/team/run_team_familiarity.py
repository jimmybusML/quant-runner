#!/usr/bin/env python3
"""Expanding-year Crown AH payoff test of strictly prior team exposure counts.

Research only: uses historical Crown event quote paths (not true receipt quotes),
prior finished-score inventory with a 72-hour lag, and never changes production.
"""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, math
from bisect import bisect_right, bisect_left
from pathlib import Path
import numpy as np

OUT=Path(__file__).resolve().parent
BASE=Path('/Users/mac/QuantAsiaDesk/research-work')
PATHS=BASE/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=BASE/'m8_independent_score_strength_20261114.jsonl'
MEMBERS=BASE/'m8_foundation_20261115/historical_membership.jsonl'


def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def read(p):
 with open(p) as f:
  for line in f:
   if line.strip(): yield json.loads(line)

def parse_dt(x):
 if not x: return None
 try: return dt.datetime.fromisoformat(x.replace('Z','+00:00')).astimezone(dt.timezone.utc)
 except Exception: return None

def settle(line, odds, gd):
 q=round(float(line)*4)/4; twice=q*2
 if abs(twice-round(twice))<1e-9: legs=[q]
 else: legs=[math.floor(twice)/2,math.ceil(twice)/2]
 rets=[]
 for leg in legs:
  m=gd+leg
  rets.append(float(odds)-1 if m>1e-9 else (-1.0 if m < -1e-9 else 0.0))
 return sum(rets)/len(rets)

def stats(rows, key='pnl'):
 n=len(rows); u=sum(float(r[key]) for r in rows)
 dates=[r['date'][:10] for r in rows]
 weeks=sorted({dt.date.fromisoformat(d).isocalendar()[:2] for d in dates})
 span=0
 if dates:
  a=dt.date.fromisoformat(min(dates)); b=dt.date.fromisoformat(max(dates))
  wa=a.isocalendar(); wb=b.isocalendar()
  span=((dt.date.fromisocalendar(wb.year,wb.week,1)-dt.date.fromisocalendar(wa.year,wa.week,1)).days//7)+1
 byweek=collections.defaultdict(list)
 for r in rows:
  iso=dt.date.fromisoformat(r['date'][:10]).isocalendar(); byweek[f'{iso.year}-W{iso.week:02d}'].append(r)
 eq=high=dd=0.0
 byday=collections.defaultdict(float)
 for r in rows: byday[r['date'][:10]]+=float(r[key])
 for d,v in sorted(byday.items()):
  eq+=v; high=max(high,eq); dd=max(dd,high-eq)
 return {'n':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'week_span':span,'weeks_with_orders':len(weeks),'orders_per_week_span':round(n/span,6) if span else None,'max_drawdown_u':round(dd,6),'weekly':{w:{'n':len(v),'net_u':round(sum(float(r[key]) for r in v),6)} for w,v in sorted(byweek.items())}}

# Source rows are joined by FID; no future T1 cohort state is used.
paths={str(r['fid']):r for r in read(PATHS)}
scores={str(r['fid']):r for r in read(SCORES)}
member={str(r['fid']) for r in read(MEMBERS)}
joined=[]
for fid,p in paths.items():
 s=scores.get(fid)
 if not s or s.get('hg') is None or s.get('ag') is None: continue
 ko=parse_dt(s.get('ko'))
 line=p.get('end_line'); hp=p.get('home_price'); ap=p.get('away_price')
 if ko is None or line is None or hp is None or ap is None: continue
 try:
  hg,ag=int(s['hg']),int(s['ag']); home=str(s['home']); away=str(s['away']); league=str(s['league'])
  line=float(line); hp=float(hp); ap=float(ap)
 except (TypeError,ValueError): continue
 joined.append({'fid':fid,'ko':ko,'year':ko.year,'date':ko.isoformat(),'league':league,'home':home,'away':away,'hg':hg,'ag':ag,'line':line,'home_odds':hp,'away_odds':ap,'line_range':float(p.get('line_range') or 0),'stored_home_return':p.get('end_home_U'),'stored_away_return':p.get('end_away_U'),'n_line_changes':int(p.get('n_line_changes') or 0),'final_line_minutes':float(p.get('final_line_minutes') or 0),'pstd':float(p.get('pstd') or 0),'outside_eight':fid not in member})
joined.sort(key=lambda r:(r['ko'],r['fid']))
# Build time-safe exposure features using only games completed at least 72h earlier.
byteam=collections.defaultdict(list); byteamleague=collections.defaultdict(list); bypair=collections.defaultdict(list)
for r in joined:
 cutoff=r['ko']-dt.timedelta(hours=72)
 def count_before(arr): return bisect_right(arr,cutoff)
 for side,op in [('home','away'),('away','home')]:
  team=r[side]; opp=r[op]; league=r['league']
  team_n=count_before(byteam[team]); opp_n=count_before(byteam[opp])
  team_l_n=count_before(byteamleague[(team,league)]); opp_l_n=count_before(byteamleague[(opp,league)])
  pair=tuple(sorted((team,opp)))
  h2h=count_before(bypair[pair])
  recent_cut=cutoff-dt.timedelta(days=365)
  team_times=byteam[team]; opp_times=byteam[opp]
  team_365=bisect_right(team_times,cutoff)-bisect_right(team_times,recent_cut)
  opp_365=bisect_right(opp_times,cutoff)-bisect_right(opp_times,recent_cut)
  prior={'team_n':team_n,'opp_n':opp_n,'team_l_n':team_l_n,'opp_l_n':opp_l_n,'h2h_n':h2h,'team_365':team_365,'opp_365':opp_365}
  r.setdefault('asof',{})[side]=prior
 # Add the just completed fixture to future known history; same fixture only once per team/pair.
 for team in (r['home'],r['away']):
  byteam[team].append(r['ko'])
  byteamleague[(team,r['league'])].append(r['ko'])
 bypair[tuple(sorted((r['home'],r['away'])))].append(r['ko'])
# Create two-side rows and X blocks.
market_names=['side_home','side_line','side_odds','opposite_odds','favorite_side','line_range','n_line_changes','final_line_minutes','pstd']
fam_names=['log_team_n','log_opp_n','log_team_league_n','log_opp_league_n','log_h2h_n','log_team_365','log_opp_365','log_exposure_gap']
side_rows=[]
for r in joined:
 gd=r['hg']-r['ag']
 for side,sgn,price,oppprice in [('home',1,r['home_odds'],r['away_odds']),('away',-1,r['away_odds'],r['home_odds'])]:
  prior=r['asof'][side]
  # Positive signed line means selected side receives points; favorite if selected contract line is negative.
  signed_line=r['line']*sgn
  market=[float(side=='home'),signed_line,price,oppprice,float(signed_line<0),r['line_range'],r['n_line_changes'],r['final_line_minutes'],r['pstd']]
  fam=[math.log1p(prior['team_n']),math.log1p(prior['opp_n']),math.log1p(prior['team_l_n']),math.log1p(prior['opp_l_n']),math.log1p(prior['h2h_n']),math.log1p(prior['team_365']),math.log1p(prior['opp_365']),math.log1p(prior['team_n'])-math.log1p(prior['opp_n'])]
  ret=settle(signed_line,price,gd if side=='home' else -gd)
  side_rows.append({'fid':r['fid'],'year':r['year'],'date':r['date'],'league':r['league'],'outside_eight':r['outside_eight'],'side':side,'pnl':ret,'market':market,'familiarity':fam,'market_names':market_names,'fam_names':fam_names,'quote_line':r['line'],'home_odds':r['home_odds'],'away_odds':r['away_odds'],'team_history':prior})

settlement_checks=[]
for r in joined:
 # The settle helper accepts side-adjusted line and goal difference; use explicit contracts.
 check={'fid':r['fid'],'home_calc':settle(r['line'],r['home_odds'],r['hg']-r['ag'])}
 check['away_calc']=settle(-r['line'],r['away_odds'],-(r['hg']-r['ag']))
 check['home_stored']=r['stored_home_return']; check['away_stored']=r['stored_away_return']
 settlement_checks.append(check)
settlement_audit={'fixtures_checked':len(settlement_checks),'home_side_matched':sum(abs(float(x['home_calc'])-float(x['home_stored']))<1e-8 for x in settlement_checks if x['home_stored'] is not None),'away_side_matched':sum(abs(float(x['away_calc'])-float(x['away_stored']))<1e-8 for x in settlement_checks if x['away_stored'] is not None),'home_side_missing_stored':sum(x['home_stored'] is None for x in settlement_checks),'away_side_missing_stored':sum(x['away_stored'] is None for x in settlement_checks),'mismatch_fids':sorted(x['fid'] for x in settlement_checks if x['home_stored'] is not None and abs(float(x['home_calc'])-float(x['home_stored']))>=1e-8 or x['away_stored'] is not None and abs(float(x['away_calc'])-float(x['away_stored']))>=1e-8)}

def fit_predict(train, test, include_fam):
 cols=len(market_names)+(len(fam_names) if include_fam else 0)
 X=np.array([r['market']+(r['familiarity'] if include_fam else []) for r in train],dtype=float)
 Y=np.array([r['pnl'] for r in train],dtype=float)
 mu=X.mean(axis=0); sd=X.std(axis=0); sd[sd<1e-10]=1.0
 Z=(X-mu)/sd
 # Fit an unpenalized intercept and ridge=100 standardized slopes.
 Z=np.column_stack([np.ones(len(Z)),Z]); eye=np.eye(cols+1); eye[0,0]=0
 beta=np.linalg.solve(Z.T@Z+100*eye,Z.T@Y)
 Xt=np.array([r['market']+(r['familiarity'] if include_fam else []) for r in test],dtype=float)
 Zt=np.column_stack([np.ones(len(Xt)),(Xt-mu)/sd])
 return Zt@beta, beta.tolist(), mu.tolist(),sd.tolist()

all_years=sorted({r['year'] for r in joined})
# Fit each annual model once and retain every side prediction plus selected action.
annual={}; predictions=[]; side_prediction_rows=[]; model_params={}
for year in [2024,2025,2026]:
 train=[r for r in side_rows if r['year']<year]
 test=[r for r in side_rows if r['year']==year]
 if not train or not test: continue
 model_predictions={}
 for label,inc in [('market_only',False),('market_plus_familiarity',True)]:
  pv,beta,mu,sd=fit_predict(train,test,inc)
  model_params[f'{year}_{label}']={'train_side_rows':len(train),'features':market_names+(fam_names if inc else []),'beta_standardized':beta,'alpha':100}
  model_predictions[label]=pv
 # all records, including frozen-eight overlap, retained for auditing; out-eight actions separately.
 byfid=collections.defaultdict(dict); source_byfid={}
 for idx,r in enumerate(test):
  d={'fid':r['fid'],'year':year,'date':r['date'],'league':r['league'],'side':r['side'],'actual_return':r['pnl'],'market_predicted_return':float(model_predictions['market_only'][idx]),'familiarity_predicted_return':float(model_predictions['market_plus_familiarity'][idx]),'outside_eight':r['outside_eight'],'familiarity':r['team_history'],'line_home':r['quote_line'],'home_odds':r['home_odds'],'away_odds':r['away_odds']}
  side_prediction_rows.append(d); byfid[r['fid']][r['side']]=d; source_byfid[r['fid']]=r
 out_actions={k:[] for k in ['market_only','market_plus_familiarity']}
 for fid,sides in byfid.items():
  if not sides.get('home') or not sides.get('away') or fid in member: continue
  for model,predkey in [('market_only','market_predicted_return'),('market_plus_familiarity','familiarity_predicted_return')]:
   choice=max((sides['home'],sides['away']),key=lambda x:x[predkey])
   if choice[predkey]>0:
    out_actions[model].append({'fid':fid,'date':choice['date'],'league':choice['league'],'side':choice['side'],'pnl':choice['actual_return'],'predicted_return':choice[predkey]})
 for model,orders in out_actions.items():
  annual.setdefault(str(year),{'train_years':sorted({r['year'] for r in train}),'train_side_rows':len(train),'test_unique_fids':len(byfid),'outside_eight_test_fids':sum(1 for fid in byfid if fid not in member),'models':{}})['models'][model]=stats(orders)
  for o in orders: predictions.append({'model':model,'year':year,**o})
# Distinct fixture coverage and mean/median counts of test targets.
fam_diagnostics={}
for year in [2024,2025,2026]:
 rows=[r for r in joined if r['year']==year and r['fid'] not in member]
 if not rows: continue
 def arr(k): return [r['asof']['home'][k] for r in rows]
 fam_diagnostics[str(year)]={'outside_eight_fids':len(rows),'home_team_prior_events':{'mean':round(float(np.mean(arr('team_n'))),4),'median':float(np.median(arr('team_n')))},'home_team_prior_league_events':{'mean':round(float(np.mean(arr('team_l_n'))),4),'median':float(np.median(arr('team_l_n')))},'prior_head_to_head':{'mean':round(float(np.mean(arr('h2h_n'))),4),'positive_fids':sum(v>0 for v in arr('h2h_n'))},'team_exposure_features_time_ordered_with_72h_lag':True}
# Merge each candidate model with frozen membership after FID de-duplication; calculate out-of-sample prediction errors on both sides.
member_rows=list(read(MEMBERS))
merged={}; prediction_error={}; selection_overlap={}
orders_by_model=collections.defaultdict(dict)
for o in predictions: orders_by_model[o['model']][o['fid']]=o
for year in [2024,2025,2026]:
 base=[{'fid':str(r['fid']),'date':str(r['date']),'pnl':float(r['pnl'])} for r in member_rows if int(str(r.get('date',''))[:4])==year]
 merged[str(year)]={'frozen_eight':stats(base)}
 for model in ['market_only','market_plus_familiarity']:
  extra=[dict(fid=fid,date=o['date'],pnl=o['pnl']) for fid,o in orders_by_model[model].items() if o['year']==year and fid not in member]
  allrows=base+extra
  merged[str(year)][model]={'candidate_increment':stats(extra),'combined':stats(allrows),'unique_added_fids':len(extra),'new_net_u':round(sum(r['pnl'] for r in extra),6)}
 predrows=[r for r in side_prediction_rows if r['year']==year and r['outside_eight']]
 if predrows:
  prediction_error[str(year)]={'outside_eight_side_contract_rows':len(predrows),'market_only_mae':round(sum(abs(r['actual_return']-r['market_predicted_return']) for r in predrows)/len(predrows),8),'market_plus_familiarity_mae':round(sum(abs(r['actual_return']-r['familiarity_predicted_return']) for r in predrows)/len(predrows),8),'mae_change_with_familiarity':round((sum(abs(r['actual_return']-r['familiarity_predicted_return']) for r in predrows)-sum(abs(r['actual_return']-r['market_predicted_return']) for r in predrows))/len(predrows),8)}
 a=orders_by_model['market_only']; b=orders_by_model['market_plus_familiarity']; af={fid:o for fid,o in a.items() if o['year']==year}; bf={fid:o for fid,o in b.items() if o['year']==year}; common=set(af)&set(bf)
 selection_overlap[str(year)]={'market_only_selected_fids':len(af),'market_plus_familiarity_selected_fids':len(bf),'common_selected_fids':len(common),'same_side_on_common':sum(af[f]['side']==bf[f]['side'] for f in common),'same_side_common_net_market':round(sum(af[f]['pnl'] for f in common if af[f]['side']==bf[f]['side']),6),'same_side_common_net_familiarity':round(sum(bf[f]['pnl'] for f in common if af[f]['side']==bf[f]['side']),6)}
summary={'study':'M8 team familiarity / repeat opportunity incremental AH payoff test','research_only':True,'source_mode':'Historical Crown event-path quotes; not actual HTTP-received prices except if explicitly matched in a separate receipt audit. Historical feature/score snapshots lack contemporaneous receipt proof for all prior team results, so results are time-ordered reconstruction, not live-as-of proof.','scope':'Crown AH fixtures in saved path archive; unique FID; target outcomes and features restricted to 2019-2026 joined inventory; all candidate betting scores exclude frozen eight FIDs; prior outcomes may use only earlier fixtures at least 72 hours before target.','question':'Do prior observed team fixture counts, prior within-league exposure, head-to-head repeats, or 365-day exposure add forward predictive value beyond the same historical Crown market-path inputs?','novelty_vs_prior':'Earlier M8 rounds tested team scoring/defense/shot residuals, transfers, lineups, managers, absences, opponent-email identity, market-only path Ridge, and market timing. This tests exposure/familiarity counts and repeated-opponent counts as information-volume predictors; it does not repeat the prior team strength residual or add new market-only Ridge tuning.','input_files':{str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in [PATHS,SCORES,MEMBERS]},'inventory':{'path_fixtures':len(paths),'score_fixtures':len(scores),'frozen_member_fids':len(member),'joined_unique_fids':len(joined),'joined_years':{str(y):sum(1 for r in joined if r['year']==y) for y in all_years}},'settlement':'Quarter-line Asian handicap split into two half-stakes; away margin uses - (home goal difference + home AH line). One unit per selected fixture.','settlement_audit':settlement_audit,'feature_definition':{'lag_hours':72,'exposure_counts':'prior joined fixtures through target UTC kickoff minus 72 hours; all competitions and same-league counts','head_to_head':'prior joined matches between the same mapped team IDs through target UTC kickoff minus 72 hours','last365':'same prior fixture counts in preceding 365 days','market_features':market_names,'added_familiarity_features':fam_names,'training':'expanding calendar-year; test 2024 fits 2019-2023, 2025 fits through 2024, 2026 fits through 2025; alpha=100 ridge on standardized features; fit side-specific realized Crown AH returns','action':'per unique FID select higher predicted side only if predicted net return > 0, else abstain; research-only; no posthoc target-year tuning'},'annual_outside_eight_increment':annual,'team_exposure_distribution':fam_diagnostics,'merged_with_frozen_eight':merged,'forward_side_return_mae':prediction_error,'selection_overlap_market_vs_familiarity':selection_overlap,'actual_receipt_validation':{'new_team_familiarity_model_replayed_on_verified_receipts':False,'reason':'Independent team history records do not carry contemporaneous receipt/availability timestamps; historical model target price/path is event-time T1, while live receipt snapshots use different T horizons. No horizon-matched, time-stamped training+features were available; no substitute quote used.'},'models':model_params,'outputs':{'selected_orders':'team_familiarity_selected_orders.jsonl','side_predictions':'team_familiarity_side_predictions.jsonl','summary':'team_familiarity_results.json'},'production_models_telegram_ledger_changed':False}
for name,rows in [('team_familiarity_selected_orders.jsonl',predictions),('team_familiarity_side_predictions.jsonl',side_prediction_rows)]:
 with open(OUT/name,'w') as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
(OUT/'team_familiarity_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'inventory':summary['inventory'],'annual':annual,'exposure':fam_diagnostics},ensure_ascii=False,indent=2))
