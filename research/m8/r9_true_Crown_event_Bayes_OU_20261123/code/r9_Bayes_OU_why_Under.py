#!/usr/bin/env python3
"""R9-B mathematical decomposition of R8 Over->Under shifts into:
(i) uncertainty-driven Poisson rate mixture at the *same sampled mean*,
(ii) numerical shift of sampled mean vs R5 posterior-point mean.
The physical Asian OU payouts and Crown price never change. Reconstruct
the SAME R8 Sobol posterior draws, recompute both sides independently.
No ROI-based selectors, no official model change.
"""
import json,hashlib,math
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
from scipy.stats import qmc,invgamma,poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r9_crown_event_update_bayes_20261123'
F5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
F8=ROOT/'frozen_research_snapshots/R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123'
FEATURE=F5/'r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=F5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
POST=F8/'r8_full_posterior_predictive_club_20261123.jsonl'
OUT=HERE/'r9_Bayes_OU_Over_to_Under_mechanism.jsonl'
SUMMARY=HERE/'r9_Bayes_OU_Over_to_Under_summary.json'
feature={(r['league'],r['fixture_id']):r for r in map(json.loads,FEATURE.open())}
post={(r['league'],r['fixture_id']):r for r in map(json.loads,POST.open()) if r['Crown_matched']}
crown={(r['league'],r['fixture_id']):r for r in map(json.loads,CROWN.open()) if r['market']=='OU'}
assert len(crown)==len(post)==9908
for key in crown:assert key in feature
U=qmc.Sobol(d=4,scramble=True,seed=20261123).random_base2(8)
def split(v):
    q=round(v*4)
    assert abs(q/4-v)<1e-9
    return [(v,1.)] if q%2==0 else [(math.floor(v*2)/2.,.5),(math.ceil(v*2)/2.,.5)]
def wl(lam,line):
    lam=np.asarray(lam,dtype=float).reshape((-1,))
    wins=np.zeros(len(lam));loss=np.zeros(len(lam))
    for part,w in split(line):
        # win Over iff total > part; loss Over iff total < part
        wins+=w*poisson.sf(math.floor(part),lam)
        loss+=w*poisson.cdf(math.ceil(part)-1,lam)
    return float(wins.mean()),float(loss.mean())
def ev(w,l,odds):
    return {'over':(odds['over']-1)*w-l,
            'under':(odds['under']-1)*l-w,
            'over_minus_under':odds['over']*w-odds['under']*l,
            'over_win':w,'over_loss':l,'middle_push_mass':1-w-l}
def point(lam,line,odds):
    a,b=wl([lam],line)
    return ev(a,b,odds)
def ensemble(lams,line,odds):
    a,b=wl(lams,line)
    return ev(a,b,odds)
def get_lams(f,k):
    hom=f['effective_venue_history']['home'];away=f['effective_venue_history']['away']
    means=f['posterior_means']['bayes_prior_'+str(k)]
    ct=[hom,away,away,hom]
    fields=['home_attack','away_defense','away_attack','home_defense']
    vals=[]
    for j in range(4):
        shape=k+1+ct[j]
        scale=(k+ct[j])*means[fields[j]]
        vals.append(invgamma.ppf(U[:,j],a=shape,scale=scale))
    lh=vals[0]*vals[1]/f['league_mean_home_xg']
    la=vals[2]*vals[3]/f['league_mean_away_xg']
    return lh+la,lh,la
def pct(p):return round(100*p,4)
audit=Counter();rs=[]
for key,p in crown.items():
    f=feature[key];r8=post[key]
    assert f['score']==p['score']==r8['score']
    line=float(p['line']);odds=p['odds']
    row={'league':f['league'],'fixture_id':f['fixture_id'],
      'season':f['season'],'date':f['date'],'score':f['score'],
      'OU_line':line,'OU_price_over':odds['over'],'OU_price_under':odds['under'],
      'models':{}}
    for k in (1,2):
        name='posterior_predictive_k'+str(k)
        oldkey='bayes_prior_'+str(k)+'_independent'
        old=r8['models'][name]['OU'];orig=p['models'][oldkey]
        lams,lh,la=get_lams(f,k)
        oldlambda=orig['lambda_home']+orig['lambda_away']
        Emean=lams.mean()
        baseline=point(oldlambda,line,odds)
        pointMC=point(Emean,line,odds)
        mixed=ensemble(lams,line,odds)
        raw_diff=mixed['over_minus_under']-baseline['over_minus_under']
        variance_effect=mixed['over_minus_under']-pointMC['over_minus_under']
        mean_effect=pointMC['over_minus_under']-baseline['over_minus_under']
        if abs(raw_diff-(variance_effect+mean_effect))>1e-12:audit['decomposition_identity']+=1
        if old['side']!=max(mixed,key=lambda x:mixed[x] if x in ('under','over') else -9999):
            audit['R8_side_reproduction_mismatch']+=1
        if orig['side']!=max(('under','over'),key=lambda side:baseline[side]):
            audit['R5_side_reproduction_mismatch']+=1
        if abs(mixed[old['side']]-old['expected_U'])>1e-7:
            audit['R8_EU_reproduction_mismatch']+=1
        if abs(baseline[orig['side']]-orig['expected_U'])>1e-7:
            audit['R5_EU_reproduction_mismatch']+=1
        new={'baseline_side':orig['side'],'mixture_side':old['side'],
           'R5_point_OU_U':orig['net_U'],'R8_mixture_OU_U':old['realized_U'],
           'R5_point_mean_total_lambda':oldlambda,
           'posterior_sample_mean_total_lambda':Emean,
           'posterior_var_total_lambda':float(lams.var()),
           'posterior_cv_total_lambda':float(lams.std()/Emean),
           'quote_total_line_minus_point_mean':line-oldlambda,
           'net_switches':old['side']!=orig['side'],
           'R5_point_price_prob':baseline,'R8_sampling_mean_point_price_prob':pointMC,
           'R8_full_posterior_price_prob':mixed,
           'over_minus_under_EV_margin_point':baseline['over_minus_under'],
           'over_minus_under_EV_margin_mixture':mixed['over_minus_under'],
           'over_minus_under_EV_margin_total_delta':raw_diff,
           'mean_shift_component':mean_effect,
           'uncertainty_mixture_component':variance_effect,
           'prob_OverWin_delta':mixed['over_win']-baseline['over_win'],
           'prob_OverLose_delta':mixed['over_loss']-baseline['over_loss'],
           'prob_OverWin_uncertainty_component':mixed['over_win']-pointMC['over_win'],
           'prob_OverLose_uncertainty_component':mixed['over_loss']-pointMC['over_loss']}
        row['models']['k'+str(k)]=new
        audit['OU_model_fixture_comparisons']+=1
    rs.append(row)
assert not {k:v for k,v in audit.items() if k!='OU_model_fixture_comparisons' and v},audit
def agg(rows):
    n=len(rows);z={'n':n}
    for k in (1,2):
        arr=[r['models']['k'+str(k)] for r in rows]
        switched=[x for x in arr if x['net_switches']]
        def avg(key,s=arr):
            return round(sum(x[key] for x in s)/len(s),7) if s else None
        def dir_counts(s):
            return dict(Counter(x['baseline_side']+' -> '+x['mixture_side'] for x in s))
        z['k'+str(k)]={'n':n,'switch_n':len(switched),'switch_direction':dir_counts(switched),
         'R5_point_return_U':round(sum(x['R5_point_OU_U'] for x in arr),5),
         'R8_posterior_return_U':round(sum(x['R8_mixture_OU_U'] for x in arr),5),
         'mean_posterior_lambda_variance':avg('posterior_var_total_lambda'),
         'mean_posterior_lambda_cv':avg('posterior_cv_total_lambda'),
         'mean_total_lambda_mean_shift':round(sum(x['posterior_sample_mean_total_lambda']-x['R5_point_mean_total_lambda'] for x in arr)/n,7) if n else None,
         'mean_margin_shift_all':avg('over_minus_under_EV_margin_total_delta'),
         'mean_uncertainty_component_all':avg('uncertainty_mixture_component'),
         'mean_MC_sample_mean_component_all':avg('mean_shift_component'),
         'mean_Pover_win_shift_all':avg('prob_OverWin_delta'),
         'mean_Pover_loss_shift_all':avg('prob_OverLose_delta'),
         'shift_toward_under_n':sum(x['over_minus_under_EV_margin_total_delta']<0 for x in arr),
         'shift_toward_over_n':sum(x['over_minus_under_EV_margin_total_delta']>0 for x in arr),
         'switching_fixtures':{
            'n':len(switched),
            'mean_total_EV_margin_shift':avg('over_minus_under_EV_margin_total_delta',switched),
            'mean_uncertainty_component':avg('uncertainty_mixture_component',switched),
            'mean_MC_sample_mean_component':avg('mean_shift_component',switched),
            'mean_Pover_win_shift':avg('prob_OverWin_delta',switched),
            'mean_Pover_loss_shift':avg('prob_OverLose_delta',switched),
            'mean_variance_of_total_lambda':avg('posterior_var_total_lambda',switched),
            'mean_line_minus_expected_goal_total':avg('quote_total_line_minus_point_mean',switched),
            'OU_result_difference_U':round(sum(x['R8_mixture_OU_U']-x['R5_point_OU_U'] for x in switched),5),
            'uncertainty_negative_direction_count':sum(x['uncertainty_mixture_component']<0 for x in switched),
            'sample_mean_shift_negative_direction_count':sum(x['mean_shift_component']<0 for x in switched)}}
    return z
report={'study':'R9_BAYES_OU_SWITCH_MARGIN_DECOMPOSITION',
    'source_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in (FEATURE,CROWN,POST)},
    'formula':'For Asian OU, Over-minus-Under expected U = decimal_odds_over * P_OverWin - decimal_odds_under * P_OverLoss; split quarter lines into equal payout legs. Mixture effect is full posterior POU minus Poisson at SAME Monte-Carlo sample mean total lambda. Mean-drift effect = Poisson at MC sample mean minus R5 point lambda.',
    'Sobol_seed':20261123,'draws':256,
    'overall':agg(rs),
    'by_season':{str(y):agg([r for r in rs if r['season']==y]) for y in sorted({r['season'] for r in rs})},
    'by_league':{lg:agg([r for r in rs if r['league']==lg]) for lg in sorted({r['league'] for r in rs})},
    'by_line_quarter_remainder':{str(i):agg([r for r in rs if round(r['OU_line']*4)%4==i]) for i in range(4)},
    'audit':dict(audit),
    'limitations':['R5 exponential xG likelihood with IG latent rate prior and independent attack/defense posteriors is one research hypothesis, not a verified process for football goals.',
       'This decomposition uses same fixed posterior samples and Crown quotes as prior R8; no out-of-sample edge or independent ROI test.',
       'Sample mean component includes Sobol finite-sample error, not just a theory change; focus on uncertainty-only component.',
       'No automatic Under strategy, EV gate or stake rule; all originally selected AH/OU models remain frozen, national team matches excluded.']}
with OUT.open('w') as f:
    for z in rs:f.write(json.dumps(z,ensure_ascii=False)+'\n')
SUMMARY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':report['overall'],'audit':dict(audit)},ensure_ascii=False))
