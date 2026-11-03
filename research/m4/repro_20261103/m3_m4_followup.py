from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone,timedelta
import sys,json,math,statistics
import numpy as np
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o
M3=o.rows_for('m3');M4=o.rows_for('mr1');by=defaultdict(dict)
for r in M3:
 if r['pnl'] is not None:by[(r['fixture'],r['market'])][r['submodel']]=r
models=['泊松','迪克森-科尔斯','双变量泊松'];rng=np.random.default_rng(20261103)
def interval(points):
 a=np.array(points,float)
 if len(a)<2:return [None,None]
 sampler=rng.integers(0,len(a),size=(4000,len(a)))
 return list(map(lambda v:round(float(v),4),np.quantile(a[sampler].mean(axis=1),[.025,.975])))
def record(label,data): print(label,json.dumps(data,ensure_ascii=False,sort_keys=True))
for market in ('AH','OU'):
 groups=[v for (fixture,m),v in by.items() if m==market and len(v)==3]
 record('COMPLETE_PAIRED_MARKET_'+market,{'n_matches':len(groups),'by_model':{k:{'pnl':round(sum(g[k]['pnl'] for g in groups),4),'CI_roi_95':interval([g[k]['pnl'] for g in groups])} for k in models}})
 a=models[0];b=models[1];c=models[2]
 record('PAIR_IDENTITY_'+market,{'poisson_vs_DC_same_side':sum(g[a]['direction']==g[b]['direction'] for g in groups),'poisson_vs_DC_same_return':sum(abs(g[a]['pnl']-g[b]['pnl'])<1e-8 for g in groups),'biv_vs_poisson_same_side':sum(g[c]['direction']==g[a]['direction'] for g in groups),'biv_vs_poisson_same_return':sum(abs(g[c]['pnl']-g[a]['pnl'])<1e-8 for g in groups)})
 different=[g for g in groups if abs(g[c]['pnl']-g[a]['pnl'])>1e-9]
 record('BIVARIATE_VS_POISSON_'+market,{'total_difference_U':round(sum(g[c]['pnl']-g[a]['pnl'] for g in groups),4),'mean_diff_U_per_fixture':round(statistics.mean(g[c]['pnl']-g[a]['pnl'] for g in groups),4),'CI_95_mean_diff':interval([g[c]['pnl']-g[a]['pnl'] for g in groups]),'diff_matches':len(different),'diff_fixtures':[{'fixture':g[a]['fixture'],'league':g[a]['league'],'poisson':g[a]['direction'],'bivariate':g[c]['direction'],'poisson_pnl':g[a]['pnl'],'bivariate_pnl':g[c]['pnl']} for g in different][:25]})
# AH+OU across fixture, for independent unit view
fixtures=defaultdict(dict)
for (fixture,market),g in by.items():
 if len(g)==3:fixtures[fixture][market]=g
record('M3_PAIR_MARKET_COVERAGE',{'both_markets':sum(set(g)=={'AH','OU'} for g in fixtures.values()),'total_fixtures':len(fixtures)})
# M3 league-by-model top negative, positive (with independent fixtures)
for model in models:
 for market in ('AH','OU'):
  d=defaultdict(list)
  for (fixture,m),g in by.items():
   if m==market and model in g:d[g[model]['league']].append(g[model]['pnl'])
  records=sorted([{'league':k,'matches':len(v),'pnl':round(sum(v),4),'ROI_pct':round(statistics.mean(v)*100,2)} for k,v in d.items()],key=lambda x:x['pnl'])
  record('M3_LEAGUES_'+model+'_'+market,{'worst':records[:8],'best':records[-8:]})
# MR1 chronological stable splits, same-match multi-orders, prior 497 vs recently 60.
settled=[r for r in M4 if r['pnl'] is not None]
bydate=defaultdict(list)
for r in settled:bydate[r['league']].append(r)
ranked=sorted([{'league':l,'orders':len(v),'fixtures':len({r['fixture'] for r in v}),'pnl_U':round(sum(r['pnl'] for r in v),3),'roi_pct':round(sum(r['pnl'] for r in v)/len(v)*100,2)} for l,v in bydate.items()],key=lambda x:x['pnl_U'])
record('M4_LEAGUE_RANKING_BOTTOM',ranked[:8]);record('M4_LEAGUE_RANKING_TOP',ranked[-8:])
# Twice pre-specified windows as descriptive, not out of sample.
cut=datetime.fromisoformat('2026-10-29T00:00:00+00:00')
for l in ['Japan J-League','Türkiye Super Lig','Poland Ekstraklasa','France Ligue 1','England Championship','Sweden Allsvenskan','Denmark Division 1','Colombia Primera A','Portugal Primeira Liga']:
 v=bydate.get(l,[])
 before=[r for r in v if datetime.fromisoformat(r['posted_at'].replace('Z','+00:00'))<cut]
 after=[r for r in v if datetime.fromisoformat(r['posted_at'].replace('Z','+00:00'))>=cut]
 record('M4_LEAGUE_PERIOD_'+l,{'all':{'n':len(v),'pnl':round(sum(r['pnl'] for r in v),3)},'before_sent':{'n':len(before),'pnl':round(sum(r['pnl'] for r in before),3)},'after_sent':{'n':len(after),'pnl':round(sum(r['pnl'] for r in after),3)},'unique_match':len({r['fixture'] for r in v})})
# Ex-post loss cuts not yet production - check top 3 vs worst 3 stability under correlated fixture
for label,subset in [('all',settled),('bottom3',[r for r in settled if r['league'] in {x['league'] for x in ranked[:3]}]),('top3',[r for r in settled if r['league'] in {x['league'] for x in ranked[-3:]}])]:
 bags=defaultdict(list)
 for r in subset:bags[r['fixture']].append(r['pnl'])
 z=np.array([sum(v) for v in bags.values()]);units=sum(len(v) for v in bags.values())
 record('M4_MATCH_CLUSTER_'+label,{'n_signals':len(subset),'n_unique_games':len(bags),'total_U':round(float(z.sum()),4),'signals_per_game':round(units/len(bags),2),'mean_profit_per_match':round(float(z.mean()),4),'match_mean_CI_95':interval(list(z))})
