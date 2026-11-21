"""Diagnostic: selected profitable leagues' matched-year cashflow, weekly uncertainty,
and lookback-then-next-year selection sensitivity. NOT a live filter or prescriptive rule.
"""
import gzip,json,collections,datetime,random,statistics,math
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
quotes={}
for s in gzip.open(P/'full_priced_T6_original_and_expanded.jsonl.gz','rt'):
 r=json.loads(s)
 if r['year']>=2024 and not r['is_m8_member']:quotes[r['fid']]=r
rows=[]
for s in gzip.open(P/'full62_price_models_ledger.jsonl.gz','rt'):
 r=json.loads(s)
 if r['model']=='price_league_binary' and r['training']=='annual_forward' and not r['is_m8_member']:
  q=quotes[r['fid']]
  ko=datetime.datetime.fromisoformat(q['ko'].replace('Z','+00:00'))
  iso=ko.isocalendar()
  rows.append({'fid':r['fid'],'league':r['league'],'year':r['year'],'week':f'{iso.year}-W{iso.week:02d}','pnl':r['pnl_U'],
   'side':r['side']})
assert len(rows)==26523
leagues=sorted(set(r['league'] for r in rows))
by=collections.defaultdict(list)
for r in rows:by[r['league']].append(r)
seed=np.random.default_rng(20261121)
def stats(arr,rep=4000):
 n=len(arr);u=sum(x['pnl'] for x in arr)
 if n==0:return {'n':0,'u':0.,'ROI_pct':None,'weekly_bootstrap95_ROI_pct':None,'active_weeks':0}
 weeks=collections.defaultdict(lambda:[0.,0.])
 for r in arr:
  v=weeks[r['week']];v[0]+=r['pnl'];v[1]+=1
 b=np.array(list(weeks.values()))
 ix=seed.integers(len(b),size=(rep,len(b)))
 a=b[ix]
 boot=100*a[:,:,0].sum(axis=1)/a[:,:,1].sum(axis=1)
 return {'n':n,'u':round(u,4),'ROI_pct':round(100*u/n,4),
  'weekly_bootstrap95_ROI_pct':[round(float(np.quantile(boot,.025)),3),round(float(np.quantile(boot,.975)),3)],
  'active_weeks':len(weeks)}
annual={l:{y:stats([r for r in vals if r['year']==y],rep=1000) for y in (2024,2025,2026)} for l,vals in by.items()}
allpositive=[l for l in leagues if all(annual[l][y]['u']>0 for y in (2024,2025,2026)) and
  all(annual[l][y]['n']>0 for y in (2024,2025,2026))]
twoyr=[l for l in leagues if all(annual[l][y]['u']>0 for y in (2024,2025)) and annual[l][2026]['n']>0]
three={'37':'Netherlands Eredivisie','141':'Greece Super League 1','75':'South Korea K League 1'}
v=[r for r in rows if r['league'] in three]
res={'cohort':'all 62 league annual-forward historical Crown T6 model',
 'input_FIDs':len(rows),'leagues_in_data':len(leagues),
 'three_positive_years':allpositive,'n_3_positive_years':len(allpositive),
 'two_positive_24_25_with_26_data':twoyr,'n_2_positive_24_25_with_26_data':len(twoyr),
 'all_2026_outcome_of_two_year_positive_set':stats([r for r in rows if r['league'] in twoyr and r['year']==2026]),
 'individual_three_selected':{three[l]:stats(by[l]) for l in three},
 'three_selected_combined':stats(v),
 'three_selected_by_year':{y:stats([r for r in v if r['year']==y]) for y in (2024,2025,2026)},
 'all_league_yearly_stats':annual,
 'limitations':['2024-26 results for model and league shortlist already explored; post-hoc hypothesis',
   '2026 historic data may not cover full leagues, per source',
   'Bootstrap is descriptive uncertainty conditional on these specific cohorts, not multiple-comparison corrected',
   'Crown source-event T6 historical quotes are not true live receipts']}
(P/'three_league_stability_summary_20261121.json').write_text(json.dumps(res,indent=2,ensure_ascii=False))
for k in ['three_selected_combined','three_selected_by_year','three_positive_years','two_positive_24_25_with_26_data','all_2026_outcome_of_two_year_positive_set']:
 print(k,res[k],flush=True)
for l in three:print(three[l],res['individual_three_selected'][three[l]],flush=True)
