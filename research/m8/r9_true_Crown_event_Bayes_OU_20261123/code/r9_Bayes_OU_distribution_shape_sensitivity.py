#!/usr/bin/env python3
"""R9-C fixed moments, different mixing law.
Does the Under bias require inverse Gamma specifically, or does ANY similarly
wide goal-rate mixture do it? Compare IG-Sobol R8 mixture to Gamma-Poisson NB
and lognormal-Poisson Gauss-Hermite, all constrained to SAME per-fixture
sampled mean and variance total lambda. Compare forecast variance with
actual 2019-25 total-goal squared residual; not a betting strategy.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,math
import numpy as np
from scipy.stats import nbinom,poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r9_crown_event_update_bayes_20261123'
SRC=HERE/'r9_Bayes_OU_Over_to_Under_mechanism.jsonl'
OUT=HERE/'r9_Bayes_OU_distribution_shape_sensitivity.json'
rows=[json.loads(x) for x in SRC.open()]
assert len(rows)==9908
X,W=np.polynomial.hermite.hermgauss(32)
W=W/math.sqrt(math.pi)
def parts(line):
 q=round(line*4)
 assert abs(q/4-line)<1e-8
 return [(line,1.)] if q%2==0 else [(math.floor(line*2)/2.,.5),(math.ceil(line*2)/2.,.5)]
def events_gamma(mu,v,line):
 shape=mu*mu/v
 p=shape/(shape+mu)
 w=l=0.
 for leg,a in parts(line):
  w+=a*float(nbinom.sf(math.floor(leg),shape,p))
  l+=a*float(nbinom.cdf(math.ceil(leg)-1,shape,p))
 return w,l
def events_log(mu,v,line):
 sigma2=math.log1p(v/mu**2)
 loc=math.log(mu)-sigma2/2
 lams=np.exp(loc+np.sqrt(2*sigma2)*X)
 w=l=0.
 for leg,a in parts(line):
  w+=a*float(np.dot(W,poisson.sf(math.floor(leg),lams)))
  l+=a*float(np.dot(W,poisson.cdf(math.ceil(leg)-1,lams)))
 return w,l
def over_margin(w,l,odds):
 return odds['over']*w-odds['under']*l
def eventmetrics(mu,v,actual):
 return {'sq_error':(actual-mu)**2,
  'poisson_variance':mu,
  'mixture_variance':mu+v,
  'actual_below2':int(actual<=1),
  'actual_below3':int(actual<=2),
  'actual_ge4':int(actual>=4),
  'point_prob_below2':float(poisson.cdf(1,mu)),
  'point_prob_below3':float(poisson.cdf(2,mu)),
  'point_prob_ge4':float(poisson.sf(3,mu)),
  'gamma_prob_below2':float(nbinom.cdf(1,mu*mu/v,(mu*mu/v)/(mu+mu*mu/v))),
  'gamma_prob_below3':float(nbinom.cdf(2,mu*mu/v,(mu*mu/v)/(mu+mu*mu/v))),
  'gamma_prob_ge4':float(nbinom.sf(3,mu*mu/v,(mu*mu/v)/(mu+mu*mu/v)))}
def aggregate(k):
 m=['k'+str(k)]
 a=[r['models'][m[0]] for r in rows]
 out=Counter();metric=defaultdict(float)
 for r,z in zip(rows,a):
  line=r['OU_line'];odds={'over':r['OU_price_over'],'under':r['OU_price_under']}
  mu=z['posterior_sample_mean_total_lambda'];v=z['posterior_var_total_lambda']
  true=sum(map(int,r['score'].split('-')))
  assert v>0
  center=z['R8_sampling_mean_point_price_prob']
  mix=z['R8_full_posterior_price_prob']
  gamma=events_gamma(mu,v,line)
  lognorm=events_log(mu,v,line)
  vals={'point':center['over_minus_under'],
        'IG_actual_full':mix['over_minus_under'],
        'gamma_matched_moments':over_margin(gamma[0],gamma[1],odds),
        'lognormal_matched_moments':over_margin(lognorm[0],lognorm[1],odds)}
  for name,zmargin in vals.items():
   marginshift=zmargin-vals['point']
   metric['avg_margin_shift_'+name]+=marginshift
   metric['signed_margin_'+name]+=zmargin
   out['under_favored_'+name]+=int(zmargin<0)
   if name!='point':
    out['shift_toward_under_'+name]+=int(marginshift<0)
    out['point_over_to_under_'+name]+=int(vals['point']>=0 and zmargin<0)
    out['point_under_to_over_'+name]+=int(vals['point']<=0 and zmargin>0)
  true_metrics=eventmetrics(mu,v,true)
  for key,val in true_metrics.items():metric[key]+=val
  # moments of full original IG mixture relative to point model: use direct
  # R9 A+B result, no recompute raw private samples.
  out['n']+=1
 for key in metric:metric[key]=round(metric[key]/out['n'],7)
 return {'n':out['n'],'summary':dict(metric),
  'counts':dict(out),
  'distribution_notes':'Three uncertainty distributions share the SAME sampled mean and sample variance total lambda; Gaussian-Hermite 32 nodes for lognormal, negative-binomial exact for Gamma, original 256 Sobol independent four IG latent params. Gamma/lognormal are NOT fitted to observed betting ROI.'}
res={'study':'R9_OU_RATE_MIXTURE_SHAPE_SENSITIVITY_FIXED_FIRST_TWO_MOMENTS',
 'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
 'k1':aggregate(1),'k2':aggregate(2),
 'limitations':['Only same historical Crown T12 source-event old cohort, collected after match.',
  'Gamma/lognormal same-moment mixing deliberately isolates distribution-shape effects from mean/variance size; not trained or selected for ROI.',
  'Goal total observed MSE vs predictive variance is an unconditional diagnostic, not proof of conditional calibration.',
  'National teams excluded. No new user-authorized probability/EV/market Gate or live TG order.']}
OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'k1':res['k1'],'k2':res['k2']},ensure_ascii=False))