#!/usr/bin/env python3
"""R8 non-selected attribution: fixed R5 posterior mean vs integrated IG.
Every historical AH/OU side counts, including deteriorations, by season.
No economic gates, no exclusions based on the result.
"""
import json,hashlib
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r8_market_timing_bayes_20261123'
P=HERE/'r8_full_posterior_predictive_club_20261123.jsonl'
BASE=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research/r5_bayes_bivar_prediction_scores_20261123.jsonl'
OUT=HERE/'r8_posterior_vs_point_mean_attribution_20261123.json'
r5={(r['league'],r['fixture_id']):r for r in map(json.loads,BASE.open())}
rows=[json.loads(s) for s in P.open()]
def agg(entries):
 d={'n':len(entries),'historical_Crown_n':sum(r['Crown_matched'] for r in entries)}
 for k in (1,2):
  m='posterior_predictive_k'+str(k)
  b='bayes_prior_'+str(k)+'_independent'
  n=len(entries)
  diff=sum(r['models'][m]['Brier']-r5[(r['league'],r['fixture_id'])]['models'][b]['Brier'] for r in entries)
  z={'n':n,'mean_Brier_posterior':round(sum(r['models'][m]['Brier'] for r in entries)/n,7) if n else None,
     'mean_Brier_point':round(sum(r5[(r['league'],r['fixture_id'])]['models'][b]['Brier'] for r in entries)/n,7) if n else None,
     'mean_Brier_diff_posterior_minus_point':round(diff/n,7) if n else None}
  for mk in ('AH','OU'):
   rr=[r['models'][m][mk] for r in entries if r['Crown_matched']]
   sn=len(rr)
   if not sn:continue
   shifts=[q for q in rr if q['side']!=q['R5_mean_model_side']]
   diffs=[x['realized_U']-x['R5_mean_model_U'] for x in shifts]
   z[mk]={'n':sn,'net_U_point':round(sum(q['R5_mean_model_U'] for q in rr),5),
      'net_U_posterior':round(sum(q['realized_U'] for q in rr),5),
      'paired_delta_U':round(sum(diffs),5),
      'switched_n':len(shifts),
      'switch_improved':sum(x>0 for x in diffs),
      'switch_worsened':sum(x<0 for x in diffs),
      'switch_equal':sum(x==0 for x in diffs),
      'switched_to_over_or_home':sum(x['side'] in ('over','home') for x in shifts),
      'switched_to_under_or_away':sum(x['side'] in ('under','away') for x in shifts)}
  d[m]=z
 return d
res={'source_SHA256':hashlib.sha256(P.read_bytes()).hexdigest(),
 'source_R5_mean_SHA256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
 'overall':agg(rows),
 'by_season':{str(y):agg([r for r in rows if r['season']==y]) for y in sorted({r['season'] for r in rows})},
 'by_league':{lg:agg([r for r in rows if r['league']==lg]) for lg in sorted({r['league'] for r in rows})},
 'scope':'Five club domestic leagues, frozen R5 historical source-event quotes, posterior uncertainty vs point model; no production rules',
 'notes':['All previously studied historical source-event quotes; posthoc result, not executable price.',
          'Positive or negative model switch increases/decreases are not new order eligibility criteria.',
          'Individual fixture Brier differences are paired, same matches, not independent trials.']}
OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
year_summary={}
for y,v in res['by_season'].items():
 year_summary[y]={}
 for k in (1,2):
  for market in ('AH','OU'):
   year_summary[y]['k'+str(k)+market]=v['posterior_predictive_k'+str(k)].get(market,{}).get('paired_delta_U')
print(json.dumps({'overall':res['overall'],'years':year_summary},ensure_ascii=False))
