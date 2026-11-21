"""Crown AH league × year repricing and pair-formation conflict decomposition.
Read existing historical research ledgers; no adjustment, filtering or production writes.
All base FIDs retained and distinct by original vs expanded sources.
"""
from pathlib import Path
import gzip,json,math,collections,datetime,csv
import numpy as np
P=Path(__file__).resolve().parent
if not (P/'full_priced_T6_original_and_expanded.jsonl.gz').exists():
 P=P.parent  # Also works when this script is inside report subdirectory of research branch
O=P/'league_price_and_factor_20261121'
O.mkdir(exist_ok=True)
def rows(path):
 with (gzip.open(path,'rt') if str(path).endswith('.gz') else open(path)) as f:
  for line in f:
   if line.strip():yield json.loads(line)
quotes={str(r['fid']):r for r in rows(P/'full_priced_T6_original_and_expanded.jsonl.gz') if r['year']>=2024 and not r['is_m8_member']}
assert len(quotes)==26523,len(quotes)
models=collections.defaultdict(dict)
for r in rows(P/'full62_price_models_ledger.jsonl.gz'):
 if r['is_m8_member']:continue
 k=(r['model'],r['training'])
 models[k][str(r['fid'])]=r
assert all(len(v)==len(quotes) for v in models.values()),[(k,len(v)) for k,v in models.items()]
markets=collections.defaultdict(list)
paired=[]
for fid,q in quotes.items():
 m={}
 for (name,tr),rs in models.items():
  m[(name,tr)]=rs[fid]['pnl_U']
 year=int(q['year']);origin=q['source'];lg=str(q['league'])
 week=datetime.datetime.fromisoformat(q['ko'].replace('Z','+00:00')).isocalendar()
 weekid=f'{week.year}-W{week.week:02d}'
 a={
    'fid':fid,'year':year,'league':lg,'origin':origin,'week':weekid,
    'line':float(q['line']),'odds_home':float(q['home_odds']),'odds_away':float(q['away_odds']),
    'home_u':float(q['home_U']),'away_u':float(q['away_U']),
    'equal_side_net_u':(q['home_U']+q['away_U'])/2,
    'lower_odds_net_u':q['home_U'] if q['home_odds']<=q['away_odds'] else q['away_U'],
    'm_price_fixed':m[('price_only_binary','fixed_2019_23')],
    'm_league_fixed':m[('price_league_binary','fixed_2019_23')],
    'm_price_forward':m[('price_only_binary','annual_forward')],
    'm_league_forward':m[('price_league_binary','annual_forward')],
    'delta_league_fixed':m[('price_league_binary','fixed_2019_23')]-m[('price_only_binary','fixed_2019_23')],
    'delta_league_forward':m[('price_league_binary','annual_forward')]-m[('price_only_binary','annual_forward')],
 }
 paired.append(a)
 for label in [('all','all'),('source',origin),('league',lg),('source_year',origin,year),('league_year',lg,year),('year',year)]:
  markets[label].append(a)
def sums(v,columns):
 return {k:round(sum(float(r[k]) for r in v),4) for k in columns}
cols=['equal_side_net_u','lower_odds_net_u','m_price_fixed','m_league_fixed',
      'm_price_forward','m_league_forward','delta_league_fixed','delta_league_forward']
def summ(v):
 n=len(v);s=sums(v,cols);return {'n':n,'net_U':s,'ROI_pct':{k:round(100*t/n,4) for k,t in s.items()}}
summaries={'|'.join(map(str,k)):summ(v) for k,v in markets.items()}
for i in (('all','all'),('source','original49'),('source','expanded15'),('year',2024),('year',2025),('year',2026)):
 print('MARKET',i,summaries['|'.join(map(str,i))],flush=True)
# Bootstrap over *weeks*, not individual fixtures. Treat as diagnostic uncertainty, no selection.
rng=np.random.default_rng(20261121)
def clustered_ci(v,field,rep=2500):
 byweek=collections.defaultdict(lambda:[0.,0])
 for r in v:
  z=byweek[r['week']];z[0]+=r[field];z[1]+=1
 units=np.array(list(byweek.values()),dtype=float)
 if not len(units):return None
 ix=rng.integers(len(units),size=(rep,len(units)))
 v=units[ix]
 values=100*v[:,:,0].sum(axis=1)/v[:,:,1].sum(axis=1)
 return {'weeks':len(units),'low_ROI_pct':round(float(np.percentile(values,2.5)),3),
    'high_ROI_pct':round(float(np.percentile(values,97.5)),3)}
for k,v in markets.items():
 if k[0] in ('year','source_year','league','league_year') and k[0]=='league_year' and len(v)<30:continue
 if k[0] not in ('all','source','year','league','league_year','source_year'):continue
 z=summaries['|'.join(map(str,k))]
 for field in (('delta_league_fixed','m_league_fixed') if k[0] in ('all','source','year','league') else ('delta_league_fixed',)):
  z.setdefault('week_cluster_bootstrap_95pct',{})[field]=clustered_ci(v,field,rep=1000 if k[0] in ('league','league_year') else 2500)
with (O/'full_pool_market_paired.jsonl.gz').open('wb') as raw:pass
with gzip.open(O/'full_pool_market_paired.jsonl.gz','wt') as f:
 for r in paired:f.write(json.dumps(r,ensure_ascii=False)+'\n')
(O/'league_pricing_summary.json').write_text(json.dumps({'samples':{'priced_outside':len(paired),'unique_leagues':len({r['league'] for r in paired})},
  'notes':['No league/year/odds filters applied to base pool','Weekly clustered bootstrap approximates sampling uncertainty, not selection-adjusted significance',
    'Year 2024-26 outcomes have been researched before; descriptions are post hoc',
    'Historical Crown source-event odds, not verified prospective HTTP receipts','No actual executable profitability inferred'],
  'groups':summaries},ensure_ascii=False,indent=2))
with (O/'league_annual_paired.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['league','year','n','equal_ROI','low_price_ROI','market_fixed_ROI','league_fixed_ROI','delta_ROI',
    'market_annual_ROI','league_annual_ROI','delta_annual_ROI'])
 for k,v in sorted(markets.items(),key=lambda kv:(str(kv[0]))):
  if k[0]!='league_year':continue
  s=summ(v)
  w.writerow([k[1],k[2],len(v)]+[s['ROI_pct'][a] for a in [
   'equal_side_net_u','lower_odds_net_u','m_price_fixed','m_league_fixed',
    'delta_league_fixed','m_price_forward','m_league_forward','delta_league_forward']])
# Pair and formation are only additional measured signals. Keep full pool as denominator.
ROOT=Path('/Users/mac/.codex/worktrees/m8-discipline-referee/quant-runner-m8-goalkeeper/research/m8')
def get_optional(name,method):
 return {str(r['fid']):r for r in rows(name) if r['method']==method and not r['frozen_overlap']}
pair=get_optional(ROOT/'player_pair_cohesion_20261121/pair_cohesion_per_fixture_20261121.jsonl.gz','market_plus_pair')
form=get_optional(ROOT/'prior_formation_market_20261121/formation_market_per_fixture_20261121.jsonl.gz','market_plus_formation')
shared=sorted(set(quotes)&set(pair)&set(form))
assert len(shared)==3949,len(shared)
def settle(line,odds,gd):
 def leg(l):
  z=gd+l
  return odds-1 if z>1e-8 else -1. if z< -1e-8 else 0.
 return (leg(line-.25)+leg(line+.25))/2 if int(round(line*4))%2 else leg(line)
factor=[]
for fid in shared:
 q=quotes[fid];pr=pair[fid];fr=form[fid]
 assert pr['chosen_side'] in ('home','away') and fr['chosen_side'] in ('home','away')
 for x in (pr,fr):
  assert x['hg']==q['hg'] and x['ag']==q['ag']
  assert x['T12_AH_home_line']==pr['T12_AH_home_line']
  assert x['T12_home_odds']==pr['T12_home_odds'] and x['T12_away_odds']==pr['T12_away_odds']
  side=x['chosen_side'];line=x['T12_AH_home_line']*(1 if side=='home' else -1)
  odds=x['T12_home_odds'] if side=='home' else x['T12_away_odds']
  g=(x['hg']-x['ag'])*(1 if side=='home' else -1)
  assert abs(settle(line,odds,g)-x['net_u'])<1e-6,(fid,side)
 is_conflict=pr['chosen_side']!=fr['chosen_side']
 prside=pr['chosen_side'];frside=fr['chosen_side']
 fbase=next(p for p in paired if False) if False else None
 market=quotes[fid]
 week=datetime.datetime.fromisoformat(q['ko'].replace('Z','+00:00')).isocalendar()
 dd={'fid':fid,'year':q['year'],'week':f'{week.year}-W{week.week:02d}',
   'league':q['league'],'ko':q['ko'],'conflict':is_conflict,
   'pair_side':prside,'formation_side':frside,
   'T6_pair_u':q['home_U'] if prside=='home' else q['away_U'],
   'T6_formation_u':q['home_U'] if frside=='home' else q['away_U'],
   'T12_pair_u':pr['net_u'],'T12_formation_u':fr['net_u'],
   'T6_price_pair':q['home_odds'] if prside=='home' else q['away_odds'],
   'T6_price_formation':q['home_odds'] if frside=='home' else q['away_odds'],
   'T12_price_pair':pr['T12_home_odds'] if prside=='home' else pr['T12_away_odds'],
   'T12_price_formation':fr['T12_home_odds'] if frside=='home' else fr['T12_away_odds'],
   'T6_line_home':q['line'],'T12_line_home':pr['T12_AH_home_line'],
   'pair_pred_netgoal':pr['predicted_home_goal_difference'],
   'formation_pred_netgoal':fr['predicted_home_goal_difference'],
   'pair_EV_home':pr['home_EV_U'],'pair_EV_away':pr['away_EV_U'],
   'formation_EV_home':fr['home_EV_U'],'formation_EV_away':fr['away_EV_U'],
   'past_pair_sample_home':pr['pair_features_home']['n_team_matches_365'],
   'past_pair_sample_away':pr['pair_features_away']['n_team_matches_365'],
   'past_formation_sample_home':fr['formation_history_home_n_365'],
   'past_formation_sample_away':fr['formation_history_away_n_365']}
 dd['T6_delta_formation_minus_pair']=dd['T6_formation_u']-dd['T6_pair_u']
 dd['T12_delta_formation_minus_pair']=dd['T12_formation_u']-dd['T12_pair_u']
 dd['T12_minus_T6_formation']=dd['T12_formation_u']-dd['T6_formation_u']
 dd['T12_minus_T6_pair']=dd['T12_pair_u']-dd['T6_pair_u']
 factor.append(dd)
fg=collections.defaultdict(list)
for r in factor:
 for key in [('all',),('year',r['year']),('type','conflict' if r['conflict'] else 'agree'),
             ('year_type',r['year'],'conflict' if r['conflict'] else 'agree'),
             ('league',r['league']),('league_year',r['league'],r['year']),
             ('league_year_type',r['league'],r['year'],'conflict' if r['conflict'] else 'agree')]:
  fg[key].append(r)
fcols=['T6_pair_u','T6_formation_u','T12_pair_u','T12_formation_u',
       'T6_delta_formation_minus_pair','T12_delta_formation_minus_pair',
       'T12_minus_T6_formation','T12_minus_T6_pair']
ff={}
for key,v in fg.items():
 s=summ if False else None
 n=len(v);ff['|'.join(map(str,key))]={
  'n':n,'net_U':sums(v,fcols),
  'ROI_pct':{k:round(100*sum(x[k] for x in v)/n,4) for k in fcols},
  'side_count':{'pair_home':sum(x['pair_side']=='home' for x in v),
        'formation_home':sum(x['formation_side']=='home' for x in v)},
  'line_changed_T12_to_T6_n':sum(x['T6_line_home']!=x['T12_line_home'] for x in v)}
 if key[0] in ('all','year','type','year_type'):
  ff['|'.join(map(str,key))]['bootstrap_95']={field:clustered_ci(v,field,1500)
          for field in ('T6_delta_formation_minus_pair','T12_delta_formation_minus_pair','T6_formation_u')}
for key in [('year_type',2024,'conflict'),('year_type',2025,'conflict'),('year_type',2026,'conflict'),
            ('year',2024),('year',2025),('year',2026)]:
 print('FACTOR',key,ff['|'.join(map(str,key))],flush=True)
# Cross-year league attribution, full rows no cherry-pick
with (O/'factor_conflicts_by_league_year.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['league','year','n','conflict_n','T6_pair_U','T6_formation_U','T6_delta_U',
    'T12_pair_U','T12_formation_U','T12_delta_U'])
 for k,v in sorted(fg.items(),key=lambda kv:(str(kv[0]))):
  if k[0]!='league_year':continue
  w.writerow([k[1],k[2],len(v),sum(x['conflict'] for x in v)]+
   [round(sum(x[field] for x in v),3) for field in
    ('T6_pair_u','T6_formation_u','T6_delta_formation_minus_pair',
      'T12_pair_u','T12_formation_u','T12_delta_formation_minus_pair')])
with gzip.open(O/'pair_formation_reprice_sameFID.jsonl.gz','wt') as f:
 for r in factor:f.write(json.dumps(r,ensure_ascii=False)+'\n')
(O/'factor_conflicts_summary.json').write_text(json.dumps({
 'full_priced_outside':len(quotes),'both_optional_feature_fids':len(factor),
 'limitations':['T6 and T12 different cutoffs; T12 settlement also independently audited',
   'This decomposition is retrospective and not an ex ante selection rule',
   '2025 anomaly must not be promoted to production without future evidence',
   'All comparisons use same frozen-excluded FID and source-event historical Crown quotes'],
 'groups':ff},ensure_ascii=False,indent=2))
print('AUDIT_COMPLETE',len(quotes),len(factor),len(ff),flush=True)
