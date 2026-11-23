#!/usr/bin/env python3
"""R9-D unfiltered total-goal variance calibration diagnostics
of previously estimated Bayes posterior rate variance.
The residual of total goals is scored against each fixture's prediction.
No thresholds, ROI optimization, ex-post subgroup selection or model edits.
"""
from pathlib import Path
from collections import defaultdict
import json,hashlib,math
import numpy as np
from scipy.stats import nbinom,poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r9_crown_event_update_bayes_20261123'
SRC=HERE/'r9_Bayes_OU_Over_to_Under_mechanism.jsonl'
OUT=HERE/'r9_Bayes_OU_variance_calibration_by_year.json'
ROWS=[json.loads(x) for x in SRC.open()]
rng=np.random.default_rng(20261123)
def agg(rs,k):
 n=len(rs)
 var_mix=var_point=sq_mix=sq_point=0.
 actlt2=actlt3=pred_pointlt2=pred_gamma_lt2=pred_pointlt3=pred_gamma_lt3=0.
 for r in rs:
  z=r['models']['k'+str(k)]
  target=sum(map(int,r['score'].split('-')))
  mean=z['posterior_sample_mean_total_lambda'];v=z['posterior_var_total_lambda']
  old=z['R5_point_mean_total_lambda']
  var_mix+=mean+v;var_point+=old
  sq_mix+=(target-mean)**2
  sq_point+=(target-old)**2
  actlt2+=int(target<=1);actlt3+=int(target<=2)
  pred_pointlt2+=float(poisson.cdf(1,old))
  pred_pointlt3+=float(poisson.cdf(2,old))
  shape=mean*mean/v
  success=shape/(shape+mean)
  pred_gamma_lt2+=float(nbinom.cdf(1,shape,success))
  pred_gamma_lt3+=float(nbinom.cdf(2,shape,success))
 return {'n':n,
  'actual_total_squared_error_vs_R5_point':round(sq_point/n,6),
  'actual_total_squared_error_vs_posterior_mc_mean':round(sq_mix/n,6),
  'R5_point_Poisson_mean_pred_variance':round(var_point/n,6),
  'posterior_mixture_mean_pred_variance':round(var_mix/n,6),
  'variance_excess_mix_minus_actual':round((var_mix-sq_mix)/n,6),
  'MSE_to_pred_mix_var_ratio':round(sq_mix/var_mix,6),
  'MSE_to_pred_point_var_ratio':round(sq_point/var_point,6),
  'actual_P_total_le1':round(actlt2/n,6),
  'point_P_total_le1':round(pred_pointlt2/n,6),
  'matched_mean_var_Gamma_P_total_le1':round(pred_gamma_lt2/n,6),
  'actual_P_total_le2':round(actlt3/n,6),
  'point_P_total_le2':round(pred_pointlt3/n,6),
  'matched_mean_var_Gamma_P_total_le2':round(pred_gamma_lt3/n,6)}
def block_boot(k):
 blocks=[]
 for year in sorted({r['season'] for r in ROWS}):
  sub=[r for r in ROWS if r['season']==year]
  s=0;w=0;n=len(sub)
  for r in sub:
   z=r['models']['k'+str(k)]
   target=sum(map(int,r['score'].split('-')))
   m=z['posterior_sample_mean_total_lambda'];v=z['posterior_var_total_lambda']
   s+=(m+v)-(target-m)**2;w+=m+v
  blocks.append((year,n,s,w))
 samples=[]
 for i in range(5000):
  idx=rng.integers(0,len(blocks),len(blocks))
  den=sum(blocks[j][1] for j in idx)
  excess=sum(blocks[j][2] for j in idx)/den
  samples.append(excess)
 return {'resampled_whole_seasons':5000,
         'season_blocks':len(blocks),
         'bootstrap_95pct_mean_excess_pred_variance':[round(float(x),6) for x in np.quantile(samples,[.025,.975])],
         'years_posterior_variance_excess_positive':sum(s>0 for yr,n,s,w in blocks)}
summary={'study':'R9_GENERALIZED_BAYES_RATE_MIXTURE_PREDICTED_VS_ACTUAL_TOTAL_GOAL_VARIANCE',
 'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
 'overall':{'k1':agg(ROWS,1),'k2':agg(ROWS,2)},
 'by_season':{str(y):{'k1':agg([r for r in ROWS if r['season']==y],1),
                     'k2':agg([r for r in ROWS if r['season']==y],2)}
              for y in sorted({r['season'] for r in ROWS})},
 'by_league':{lg:{'k1':agg([r for r in ROWS if r['league']==lg],1),
                  'k2':agg([r for r in ROWS if r['league']==lg],2)}
              for lg in sorted({r['league'] for r in ROWS})},
 'whole_season_block_bootstrap':{'k1':block_boot(1),'k2':block_boot(2)},
 'limitations':['Full historical 9908 Crown-matched five-league fixtures already explored; observed score outcome used ONLY for retrospective score. No blind future data.',
  'MSE versus predictive variance is marginal diagnostic: cannot prove conditional calibration and is sensitive to model mean misspecification.',
  'Gamma low-tail probability approximates mixing distribution with same mean/variance as original IG; not exact IG low-tail probability.',
  'A calibration discrepancy does not directly imply monetary edge or order filter. National team excluded, no production changes.']}
OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':summary['overall'],'block_bootstrap':summary['whole_season_block_bootstrap'],
   'year_excess':{year:{k:z[k]['variance_excess_mix_minus_actual'] for k in ('k1','k2')} for year,z in summary['by_season'].items()}},ensure_ascii=False))