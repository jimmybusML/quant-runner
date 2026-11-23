#!/usr/bin/env python3
"""R6 matched same-fixture direction switch study. Reads only frozen R5 data."""
from pathlib import Path
from collections import Counter
import json,hashlib
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
F=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
OUT=ROOT/'r6_bayes_bivar_20261123/r6_prior_bivar_complement.json'
H=F/'r5_bayes_bivar_CrownT12_20261123.jsonl'
R=F/'r5_bayes_bivar_actual_receipt_20261123.jsonl'
hist=[json.loads(x) for x in H.open()]
receipt=[json.loads(x) for x in R.open()]
assert len(hist)==19816 and len(receipt)==276
MODELS=('independent_poisson','bivar_empirical_c','bivar_fixed_c010',
    'bayes_prior_1_independent','bayes_prior_2_independent','bayes_prior_5_independent',
    'bayes_prior_2_bivar_empirical_c','bayes_prior_2_bivar_fixed_c010')
def compare(rows,a,b):
    changed=[r for r in rows if r['models'][a]['side']!=r['models'][b]['side']]
    diffs=[r['models'][a]['net_U']-r['models'][b]['net_U'] for r in changed]
    n=len(rows);u=sum(diffs)
    return {'n':n,'side_changes':len(changed),'side_change_rate_pct':round(100*len(changed)/n,4) if n else None,
        'gain_U':round(u,5),'gain_ROI_pp':round(100*u/n,5) if n else None,
        'positive_switches':sum(v>0 for v in diffs),
        'negative_switches':sum(v<0 for v in diffs),
        'zero_switches':sum(v==0 for v in diffs),
        'candidate_U':round(sum(r['models'][a]['net_U'] for r in rows),5),
        'baseline_U':round(sum(r['models'][b]['net_U'] for r in rows),5),
        'candidate_mean_pred_EV':round(sum(r['models'][a]['expected_U'] for r in rows)/n,6) if n else None}
def subset(data,season=None,league=None,market=None):
    return [r for r in data if (season is None or r['season']==season) and
            (league is None or r['league']==league) and (market is None or r['market']==market)]
hres={}
for market in ('AH','OU'):
    a=subset(hist,market=market)
    hres[market]={'total':{m:compare(a,m,'independent_poisson') for m in MODELS[1:]},
      'incremental_bivar_on_bayes2':{m:compare(a,m,'bayes_prior_2_independent')
        for m in ('bayes_prior_2_bivar_empirical_c','bayes_prior_2_bivar_fixed_c010')},
      'by_season':{str(y):{m:compare(subset(a,season=y),m,'independent_poisson') for m in
         ('bayes_prior_1_independent','bayes_prior_2_independent','bayes_prior_5_independent',
          'bivar_empirical_c','bivar_fixed_c010')} for y in range(2019,2026)},
      'by_league':{lg:{m:compare(subset(a,league=lg),m,'independent_poisson') for m in
         ('bayes_prior_1_independent','bayes_prior_2_independent','bayes_prior_5_independent',
          'bivar_empirical_c','bivar_fixed_c010')} for lg in sorted({r['league'] for r in a})},
      'by_quarter_line_remainder':{str(i):{m:compare([r for r in a if round(r['line']*4)%4==i],m,'independent_poisson')
         for m in ('bayes_prior_1_independent','bayes_prior_2_independent')}
         for i in range(4)}}
rres={}
for market in ('AH','OU'):
    a=[r for r in receipt if r['market']==market]
    rres[market]={'vs_dynamic_ratio':{m:compare(a,m,'same_season_ratio_independent') for m in
      ('bayes_1_independent','bayes_2_independent','bayes_5_independent',
       'same_season_ratio_bivar_empirical','same_season_ratio_bivar_fixed_c010',
       'bayes_2_bivar_empirical','bayes_2_bivar_fixed_c010')},
      'vs_R3_arithmetic':{m:compare(a,m,'old_arithmetic3_independent') for m in
      ('bayes_1_independent','bayes_2_independent','bayes_5_independent')}}
counts=Counter()
for r in hist:
    counts['historical_market_rows']+=1
    if r['models']['bivar_empirical_c']['common_shock_c']==0:counts['historical_empirical_cov_zero']+=1
for r in receipt:
    counts['actual_receipt_market_rows']+=1
    if r['models']['same_season_ratio_bivar_empirical']['c']==0:counts['receipt_empirical_cov_zero']+=1
report={'name':'R6_PRIOR_BIVARIATE_DISAGREEMENT_STUDY',
 'source_frozen_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H,R)},
 'national_team_rows':0,'samples':dict(counts),'historical_Crown_T12':hres,
 'actual_pre_kickoff_Crown_HTTP_OLD_STUDY':rres,
 'limitations':['Historical Crown T12 collected after games: not actual pregame HTTP receipts',
    'Actual prekickoff HTTP receipts previously researched: not blind new validation',
    'Different prior strengths were research sensitivities; do not select best on observed outcomes',
    'No official Telegram orders, no new strategy / EV Gate / stake selection',
    'Study includes losses and gains on all direction changes; no profitability filtering']}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'AH_bayes1':hres['AH']['total']['bayes_prior_1_independent'],
 'AH_bivar':hres['AH']['total']['bivar_empirical_c'],
 'OU_bayes1':hres['OU']['total']['bayes_prior_1_independent'],
 'AH_receipt_bayes2':rres['AH']['vs_dynamic_ratio']['bayes_2_independent'],
 'OU_receipt_bayes5':rres['OU']['vs_dynamic_ratio']['bayes_5_independent'],
 'covariance_usage':dict(counts)},ensure_ascii=False))