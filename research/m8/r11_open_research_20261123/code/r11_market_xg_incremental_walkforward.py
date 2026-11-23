#!/usr/bin/env python3
"""R11-B: prior-season trained market calibration and independent xG residual
information, no profit fitting. All score probabilities are quoted Crown
AH+OU market-implied and R10 Gamma observation xG posterior.

For every test year 2021..2025: train on EXACT two completed prior seasons
2019..2024, then test the new entire target year.
Modes: Crown raw, market-only learned temperature,
market plus xG log-probability correction, market-temperature plus xG
correction. Brier and logloss only, no picks, no EV gates.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,math
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r11_open_method_research_20261123'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
R10=ROOT/'frozen_research_snapshots/R10_XG_GAMMA_OBS_DYNAMIC_NB_20261123'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
GAMMA=R10/'r10_Gamma_xG_posterior_predictive_20261123.jsonl'
ORIG=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research/r5_bayes_bivar_CrownT12_20261123.jsonl'
OUT=HERE/'r11_market_residual_walk_forward_2021_2025.jsonl'
SUMMARY=HERE/'r11_market_residual_walk_forward_summary.json'
m={r['fid']:r for r in map(json.loads,MARKET.open()) if r['cohort']=='historical_Crown_T12'}
g=[json.loads(s) for s in GAMMA.open()]
assert len(g)==len(m)==9908
original_id={(r['league'],r['fixture_id']):r['fid']
    for r in map(json.loads,ORIG.open()) if r['market']=='AH'}
market_match={key:m[fid] for key,fid in original_id.items()}
assert len(market_match)==len(g)==9908
prepared=defaultdict(list)
for r in g:
    key=(r['league'],r['fixture_id'])
    u=market_match[key]
    assert u['score']==r['score']
    pmarket=np.array([u['models']['market_implied_Poisson'][t] for t in
       ('1X2_p_home','1X2_p_draw','1X2_p_away')],dtype=float)
    px1=np.array(r['methods']['gamma_obs_k1']['prob_1X2'],dtype=float)
    px2=np.array(r['methods']['gamma_obs_k2']['prob_1X2'],dtype=float)
    hg,ag=map(int,r['score'].split('-'))
    obs=0 if hg>ag else 1 if hg==ag else 2
    if max(abs(pmarket.sum()-1),abs(px1.sum()-1),abs(px2.sum()-1))>1e-9:raise RuntimeError('invalid probability')
    prepared[r['season']].append({'key':key,'season':r['season'],'score':r['score'],
        'market':pmarket,'xGk1':px1,'xGk2':px2,'obs':obs})
def fit(data,selector,mode):
    M=np.array([row['market'] for row in data],dtype=float)
    E=np.array([row[selector] for row in data],dtype=float)
    y=np.array([row['obs'] for row in data],dtype=int)
    logm=np.log(np.maximum(M,1e-15));extra=np.log(np.maximum(E,1e-15))-logm
    if mode=='market_temperature':X=logm[:,:,None];init=np.array([1.])
    elif mode=='market_plus_xG':X=extra[:,:,None];init=np.array([0.])
    elif mode=='market_temperature_plus_xG':X=np.stack([logm,extra],axis=-1);init=np.array([1.,0.])
    else:raise ValueError(mode)
    if mode=='market_plus_xG':
        def get_logits(theta):return logm+np.einsum('nct,t->nc',X,theta)
    else:
        def get_logits(theta):return np.einsum('nct,t->nc',X,theta)
    def obj(theta):
        s=get_logits(theta)
        lo=s-logsumexp(s,axis=1,keepdims=True)
        probs=np.exp(lo)
        loss=-float(lo[np.arange(len(data)),y].mean())
        residual=probs.copy()
        residual[np.arange(len(data)),y]-=1
        grad=np.einsum('nc,nct->t',residual,X)/len(data)
        return loss,grad
    res=minimize(obj,init,jac=True,method='BFGS',
        options={'gtol':1e-10,'maxiter':1000})
    # BFGS precision-loss warning possible; verify gradient instead.
    loss,grad=obj(res.x)
    if not np.all(np.isfinite(res.x)) or np.max(np.abs(grad))>1e-6:
        raise RuntimeError(('bad convergence',selector,mode,res.message,grad,res.x))
    return {'params':res.x.tolist(),'train_logloss':float(loss),
        'train_gradient_max_abs':float(np.max(np.abs(grad))),
        'train_n':len(data),'optimizer_message':str(res.message)}
def predict(pm,px,mode,p):
    logm=np.log(np.maximum(pm,1e-15))
    diff=np.log(np.maximum(px,1e-15))-logm
    if mode=='market_temperature':
        z=p[0]*logm
    elif mode=='market_plus_xG':
        z=logm+p[0]*diff
    else:z=p[0]*logm+p[1]*diff
    z=z-logsumexp(z)
    return np.exp(z)
def score(p,y):
    return (float(sum((p[i]-float(i==y))**2 for i in range(3))),
            -math.log(max(p[y],1e-15)))
pred=[];trainparams={};audit=Counter()
for yy in range(2021,2026):
    train=prepared[yy-2]+prepared[yy-1]
    test=prepared[yy]
    assert len(train)>2600 and len(test)>1300
    trainparams[str(yy)]={}
    per={}
    for model in ('xGk1','xGk2'):
        per[model]={}
        for mode in ('market_temperature','market_plus_xG','market_temperature_plus_xG'):
            per[model][mode]=fit(train,model,mode)
    trainparams[str(yy)]=per
    for r in test:
        b={'key':list(r['key']),'season':yy,'score':r['score'],'obs':r['obs'],
           'models':{}}
        pm=r['market']
        b['models']['market_raw']=dict(zip(('Brier','logloss'),score(pm,r['obs'])))
        for model in ('xGk1','xGk2'):
            px=r[model]
            b['models'][model+'_alone']=dict(zip(('Brier','logloss'),score(px,r['obs'])))
            for mode in ('market_temperature','market_plus_xG','market_temperature_plus_xG'):
                out=predict(pm,px,mode,per[model][mode]['params'])
                b['models'][model+'_'+mode]=dict(zip(('Brier','logloss'),score(out,r['obs'])))
        pred.append(b)
    audit['test_season_'+str(yy)]=len(test)
assert len(pred)==sum(len(prepared[y]) for y in range(2021,2026))
def summ(a):
    names=a[0]['models'] if a else []
    result={'n':len(a)}
    for name in names:
        result[name]={'Brier':round(sum(r['models'][name]['Brier'] for r in a)/len(a),7),
                      'logloss':round(sum(r['models'][name]['logloss'] for r in a)/len(a),7)}
    return result
summary={'study':'R11_TWO_SEASON_OUT_OF_YEAR_CROWN_MARKET_CALIBRATION_AND_XG_INCREMENTAL',
 'scope':'Five domestic club leagues, historic Crown T12 source-event 2021-2025 test seasons; train on exactly two previously completed seasons, not target outcomes; no national teams.',
 'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (MARKET,GAMMA,ORIG)},
 'method':'Fit market-only log-probability temperature tau and incremental xG log probability residual beta in multinomial softmax, minimizing TRAIN prior two seasons only multiclass logloss (proper score). Market-only, fixed-tau1+xG beta, joint tau+beta. Compare all 2021-2025 target years without fitting or selecting trading ROI. The unbounded numerical BFGS optimization is only research coefficient estimation, not a bet selection Gate.',
 'learned_parameters_by_test_year':trainparams,
 'overall':summ(pred),
 'by_test_year':{str(yy):summ([r for r in pred if r['season']==yy]) for yy in range(2021,2026)},
 'audit':dict(audit),
 'limitations':['Train and test periods separated by year, but all underlying historic Crown T12 source-event prices retrieved AFTER match and xG time of publication not verified; NOT true as-of historic executable prices.',
 'All models repeatedly explored historical dataset; not fresh blind or valid production alpha.',
 'Crown market baseline uses same AH+OU odds to infer odds-based probability; predicted probability improvement does not imply bet profitability.',
 'Market-only temperature repeated identically when displayed under k1 and k2, for comparison only.',
 'No goals from a target test year enter training for that year; all target fixtures evaluated with no EV gate or selection.']}
with OUT.open('w') as f:
    for row in pred:f.write(json.dumps(row,ensure_ascii=False)+'\n')
SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'n':len(pred),'overall':summary['overall'],
                  'coeffs':{yy:{m:{mod:tuple(round(z,4) for z in v['params']) for mod,v in x.items()} for m,x in p.items()} for yy,p in trainparams.items()}},ensure_ascii=False))
