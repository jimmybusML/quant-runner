#!/usr/bin/env python3
"""R10-B: xG Gamma observation likelihood, inverse-Gamma posterior predictive.
Replace R5 Exponential observation shape=1 with actual as-of league estimate
from TWO PREVIOUS complete seasons (xG only; no ROI or scores trained).
Keep the SAME prior mean k=1 or 2, same R5 posterior means and matches,
same Sobol256 deterministic integration. Posterior latent variance becomes
smaller; it has no user-authorized production/trade status.
Compare all 9908 Crown T12 historical source-event matches, no EV gate.
"""
import json,hashlib,math
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from scipy.stats import qmc,invgamma
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r10_xg_observation_bayes_dynamic_20261123'
R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
R8=ROOT/'frozen_research_snapshots/R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123'
PARAM=HERE/'r10_prior_two_season_xg_Gamma_shape.json'
FEATURE=R5/'r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=R5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
R8P=R8/'r8_full_posterior_predictive_club_20261123.jsonl'
OUT=HERE/'r10_Gamma_xG_posterior_predictive_20261123.jsonl'
SUMMARY=HERE/'r10_Gamma_xG_posterior_predictive_summary_20261123.json'
N=45
G=np.arange(N+1,dtype=float)
SOBOL=qmc.Sobol(d=4,scramble=True,seed=20261123).random_base2(8)
tune=json.loads(PARAM.read_text())['by_league_season']
features={(x['league'],x['fixture_id']):x for x in map(json.loads,FEATURE.open())}
crown=defaultdict(dict)
for r in map(json.loads,CROWN.open()):
    crown[(r['league'],r['fixture_id'])][r['market']]=r
market={(r['league'],r['fid']):r for r in map(json.loads,MARKET.open()) if r['cohort']=='historical_Crown_T12'}
base8={(r['league'],r['fixture_id']):r for r in map(json.loads,R8P.open()) if r['Crown_matched']}
assert len(crown)==len(base8)==len(market)==9908,(len(crown),len(base8),len(market))
audit=Counter()
def pmf(lams):
    z=np.empty((len(lams),N+1))
    z[:,0]=np.exp(-lams)
    for j in range(1,N+1):z[:,j]=z[:,j-1]*lams/j
    return z
def cdf_at(cdf,indices):
    ix=np.asarray(indices,dtype=int)
    result=np.zeros((len(cdf),len(ix)))
    pos=np.flatnonzero(ix>=0)
    if len(pos):result[:,pos]=cdf[:,np.clip(ix[pos],0,N)]
    return result
def hw_probs(hp,ap):
    cc=np.cumsum(ap,axis=1)
    win=(hp*cdf_at(cc,(G-1).astype(int))).sum(axis=1)
    loss=(hp*(1-cdf_at(cc,G.astype(int)))).sum(axis=1)
    # Tail outside grid: current λ stay small, retain original R8 rule.
    tailh=np.maximum(0.,1-hp.sum(axis=1));taila=np.maximum(0.,1-ap.sum(axis=1))
    win+=tailh*(1-taila)
    draw=np.maximum(0.,1-win-loss)
    return float(win.mean()),float(draw.mean()),float(loss.mean())
def legs(v):
    q=round(float(v)*4)
    assert abs(q/4-float(v))<1e-9
    return [(float(v),1.)] if q%2==0 else [(math.floor(float(v)*2)/2.,.5),(math.ceil(float(v)*2)/2.,.5)]
def asianEV(hp,ap,lh,la,quote):
    mkt=quote['market'];line=float(quote['line']);odd=quote['odds']
    win=np.zeros(len(lh));loss=np.zeros(len(lh))
    if mkt=='AH':
        cdf=np.cumsum(ap,axis=1)
        for v,w in legs(line):
            # R8 exact quarter contract via discrete difference H-A+v.
            ix_win=np.ceil(G+v-1e-12).astype(int)-1
            ix_loss=np.floor(G+v+1e-12).astype(int)
            pwin=(hp*cdf_at(cdf,ix_win)).sum(axis=1)
            ploss=(hp*(1-cdf_at(cdf,ix_loss))).sum(axis=1)
            th=np.maximum(0,1-hp.sum(axis=1))
            ta=np.maximum(0,1-ap.sum(axis=1))
            pwin+=th*(1-ta)
            win+=w*pwin;loss+=w*ploss
        return {'home':float(((odd['home']-1)*win-loss).mean()),
                'away':float(((odd['away']-1)*loss-win).mean())}
    if mkt=='OU':
        p=pmf(lh+la)
        cdf=np.cumsum(p,axis=1)
        for v,w in legs(line):
            a=math.floor(v);b=math.ceil(v)-1
            win+=w*(1-(cdf[:,a] if a>=0 else 0.))
            loss+=w*(cdf[:,b] if b>=0 else 0.)
        return {'over':float(((odd['over']-1)*win-loss).mean()),
                'under':float(((odd['under']-1)*loss-win).mean())}
    raise ValueError(mkt)
def realized(mkt,line,odd,side,sc):
    hg,ag=map(int,sc.split('-'))
    val=0.
    for v,w in legs(line):
        margin=hg-ag+v if side=='home' else ag-hg-v if side=='away' else hg+ag-v if side=='over' else v-hg-ag
        val+=w*((odd-1) if margin>1e-9 else -1 if margin<-1e-9 else 0.)
    return val
def prediction(f,k,obs_shape,with_prob=True):
    posterior=f['posterior_means']['bayes_prior_'+str(k)]
    hcount=f['effective_venue_history']['home']
    acount=f['effective_venue_history']['away']
    count=[hcount,acount,acount,hcount]
    fields=('home_attack','away_defense','away_attack','home_defense')
    arr=[]
    for j,key in enumerate(fields):
        n=count[j];mu=posterior[key]
        # Gamma xG observation with known shape r per match and IG mean prior
        # produces conjugate posterior IG(alpha=1+r*(k+n),
        # beta=r*(k+n)*mu); mean stays EXACTLY as in R5.
        alpha=1+obs_shape*(k+n)
        beta=obs_shape*(k+n)*mu
        arr.append(invgamma.ppf(SOBOL[:,j],a=alpha,scale=beta))
    lh=arr[0]*arr[1]/f['league_mean_home_xg']
    la=arr[2]*arr[3]/f['league_mean_away_xg']
    hp=pmf(lh);ap=pmf(la)
    p1=hw_probs(hp,ap)
    tot=lh+la
    sc=f['score'];hg,ag=map(int,sc.split('-'))
    outcome=0 if hg>ag else 1 if hg==ag else 2
    out={'prob_1X2':list(p1),
         'Brier':sum((x-float(i==outcome))**2 for i,x in enumerate(p1)),
         'logloss':-math.log(max(p1[outcome],1e-15)),
         'xG_observation_shape':obs_shape,
         'posterior_lambda_total_mean':float(tot.mean()),
         'posterior_lambda_total_variance':float(tot.var()),
         'posterior_pred_total_variance':float(tot.mean()+tot.var()),
         'actual_total_sq_error':float((hg+ag-tot.mean())**2),
         'pred_total_le1':float((np.exp(-tot)*(1+tot)).mean()),
         'pred_total_le2':float((np.exp(-tot)*(1+tot+tot**2/2)).mean()),
         'price':{}}
    return out,hp,ap,lh,la
z=[]
for idx,(key,quotes) in enumerate(sorted(crown.items())):
    if set(quotes)!={'AH','OU'}:raise RuntimeError(('missing quote',key))
    f=features[key];lg=f['league'];year=str(f['season'])
    shape=tune[lg][year]['shape']
    base=base8[key];idmarket=(lg,quotes['AH']['fid'])
    if idmarket not in market:raise RuntimeError(('missing market',idmarket))
    r={'fixture_id':f['fixture_id'],'league':lg,'season':f['season'],
       'score':f['score'],'date':f['date'],'research_quote_source':'Crown T12 historical event retrieved AFTER match',
       'r_xg_from_preceding_two_complete_seasons':shape,
       'R7_Crown_implied_market_Brier':market[idmarket]['models']['market_implied_Poisson']['1X2_brier'],
       'methods':{}}
    assert quotes['AH']['score']==quotes['OU']['score']==f['score']
    for k in (1,2):
        pred,hp,ap,lh,la=prediction(f,k,shape)
        old=base['models']['posterior_predictive_k'+str(k)]
        # Numeric sanity on small, mixed-league/season fixture sample: Gamma
        # observation shape 1 must reconstruct exact R8 posterior mathematics.
        if idx<120:
            old_again,h0,a0,l0,l1=prediction(f,k,1.)
            if max(abs(x-y) for x,y in zip(old_again['prob_1X2'],old['prob']))>1e-9:
                audit['shape1_R8_Brier_prob_reproduction_fail']+=1
            for m in ('AH','OU'):
                old_ev=asianEV(h0,a0,l0,l1,quotes[m])
                if abs(old_ev[old[m]['side']]-old[m]['expected_U'])>1e-7:
                    audit['shape1_R8_contractEV_reproduction_fail']+=1
            audit['shape1_R8_independent_fixture_spotcheck']+=1
        for mk in ('AH','OU'):
            oldprice=quotes[mk]
            E=asianEV(hp,ap,lh,la,oldprice)
            side=max(E,key=E.get)
            actual=realized(mk,oldprice['line'],oldprice['odds'][side],side,f['score'])
            old5=oldprice['models']['bayes_prior_'+str(k)+'_independent']
            pred['price'][mk]={
                'side':side,'expected_U':E[side],'actual_U':actual,
                'old_R5_mean_U':old5['net_U'],'old_R5_mean_side':old5['side'],
                'old_R8_exp_integral_U':old[mk]['realized_U'],
                'old_R8_exp_integral_side':old[mk]['side']}
            audit['Crown_contract_model_checked']+=1
        pred['R5_point_Brier']=None # resolved via independent R5 Brier formula in next validator
        pred['R8_shape1_Brier']=old['Brier']
        r['methods']['gamma_obs_k'+str(k)]=pred
    z.append(r)
    if (idx+1)%1200==0:print('R10 gamma xG post processed',idx+1,flush=True)
assert not {k:v for k,v in audit.items() if 'fail' in k and v},audit
def stats(rows):
    n=len(rows);s={'n':n}
    for k in (1,2):
        name='gamma_obs_k'+str(k)
        a=[r['methods'][name] for r in rows]
        s[name]={
          'n':n,'mean_xG_obs_shape':round(sum(r['r_xg_from_preceding_two_complete_seasons'] for r in rows)/n,6) if n else None,
          'mean_Brier':round(sum(x['Brier'] for x in a)/n,7) if n else None,
          'mean_logloss':round(sum(x['logloss'] for x in a)/n,7) if n else None,
          'mean_R8_shape1_Brier':round(sum(x['R8_shape1_Brier'] for x in a)/n,7) if n else None,
          'mean_total_goal_pred_variance':round(sum(x['posterior_pred_total_variance'] for x in a)/n,6) if n else None,
          'mean_actual_total_goal_squared_error':round(sum(x['actual_total_sq_error'] for x in a)/n,6) if n else None,
          'P_total_le1':round(sum(x['pred_total_le1'] for x in a)/n,6) if n else None,
          'P_total_le2':round(sum(x['pred_total_le2'] for x in a)/n,6) if n else None}
        for m in ('AH','OU'):
            pp=[x['price'][m] for x in a]
            u=sum(x['actual_U'] for x in pp)
            delta8=sum(x['actual_U']-x['old_R8_exp_integral_U'] for x in pp)
            delta5=sum(x['actual_U']-x['old_R5_mean_U'] for x in pp)
            s[name][m]={'n':n,'net_U':round(u,5),
                  'ROI_pct':round(100*u/n,5) if n else None,
                  'R5_point_U':round(sum(x['old_R5_mean_U'] for x in pp),5),
                  'R8_shape1_integral_U':round(sum(x['old_R8_exp_integral_U'] for x in pp),5),
                  'delta_v_R8_full_integration_U':round(delta8,5),
                  'delta_v_R5_point_U':round(delta5,5),
                  'switch_from_R8':sum(x['side']!=x['old_R8_exp_integral_side'] for x in pp),
                  'switch_from_R5':sum(x['side']!=x['old_R5_mean_side'] for x in pp),
                  'mean_estimated_EV':round(sum(x['expected_U'] for x in pp)/n,6) if n else None}
    if n:s['mean_Crown_market_Brier']=round(sum(x['R7_Crown_implied_market_Brier'] for x in rows)/n,7)
    return s
report={'name':'R10_LEAGUE_PREVIOUS_TWO_SEASON_ESTIMATED_GAMMA_OBSERVATION_BAYES_POSTERIOR_PREDICTIVE',
 'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (FEATURE,CROWN,MARKET,R8P,PARAM)},
 'method':'Replace R5 xG exponential observation (Gamma shape=1) by Gamma(shape=r, mean=latent strength), with r estimated solely from two previous seasons within team venue role. IG prior and power posterior both scale k and n by r, keeping posterior mean, sample 4 independent IG posteriors with original R8 Sobol256, integrate score and full AH/OU quarter payoff; no EV gate.',
 'sampling_seed':20261123,'draws':256,'audit':dict(audit),
 'overall':stats(z),
 'by_season':{str(y):stats([r for r in z if r['season']==y]) for y in range(2019,2026)},
 'by_league':{lg:stats([r for r in z if r['league']==lg]) for lg in sorted({r['league'] for r in z})},
 'limitations':['Previous-two-season Gamma shape is inferred from Understat xG venue-role residuals but may confound strength drift and xG noise.',
    'Historical Crown source-event T12 collected after each target match; cannot be claimed as actual available bet quote.',
    'This is same repeatedly explored 9908 old fixtures, not new blinded profit validation.',
    'R5 xG original historical publication time unknown; strict match dates do not prove exact API availability.',
    'All matches and negative outcomes retained. No trading strategy, EV eligibility gate, stake rule, national teams or production changes.']}
with OUT.open('w') as file:
    for row in z:file.write(json.dumps(row,ensure_ascii=False)+'\n')
SUMMARY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':report['overall'],'audit':report['audit']},ensure_ascii=False))
