#!/usr/bin/env python3
"""R8-B: actually integrate R5 independent inverse-Gamma Bayesian attack and
defense posteriors into predictive match-goal distributions (not only posterior
MEANS). Deterministic nested Sobol 128/256 draws, R5 as-of feature inputs.
Same 13,312 fixtures, Crown T12 9,908 original historically-retrieved prices.
No fitted ROI thresholds or new strategy; every side chosen, keep losses.
This is a generalized Bayes posterior predictive under an explicit independent
latent-attack/defense assumption, NOT a complete hierarchical team model.
"""
import json,hashlib,math
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from scipy.stats import qmc,invgamma
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r8_market_timing_bayes_20261123'
F=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
FEAT=F/'r5_bayes_bivar_asof_features_20261123.jsonl'
ORIG=F/'r5_bayes_bivar_CrownT12_20261123.jsonl'
MARK=R7/'r7_market_implied_2market_20261123.jsonl'
OUT=HERE/'r8_full_posterior_predictive_club_20261123.jsonl'
REPORT=HERE/'r8_full_posterior_predictive_club_summary_20261123.json'
QMC=qmc.Sobol(d=4,scramble=True,seed=20261123).random_base2(8)
N=45
K=np.arange(N+1,dtype=int)
FACTORIAL=np.array([math.factorial(int(k)) for k in K],dtype=float) # N45 double factorial finite
# price match R5 from same fixture, not team-name+FT anchor rejoined in R8.
prices=defaultdict(dict)
by_crown={}
for s in ORIG.open():
    r=json.loads(s);key=(r['league'],r['fixture_id'])
    assert r['market'] not in prices[key]
    prices[key][r['market']]=r
    by_crown[r['fid']]=key
market={}
for s in MARK.open():
    r=json.loads(s)
    if r['cohort']=='historical_Crown_T12':market[(r['league'],r['fid'])]=r
assert len(prices)==9908 and len(market)==9908
FEATURES=[json.loads(s) for s in FEAT.open()]
assert len(FEATURES)==13312
def pmf_matrix(lambdas):
    values=lambdas.reshape((-1,1))
    z=np.empty((len(lambdas),N+1),dtype=float)
    z[:,0]=np.exp(-lambdas)
    for g in range(1,N+1):
        z[:,g]=z[:,g-1]*lambdas/g
    return z
def cdf_index(cdf,indexes):
    ix=np.asarray(indexes,dtype=int)
    result=np.zeros((cdf.shape[0],len(ix)))
    take=np.flatnonzero(ix>=0)
    if len(take):result[:,take]=cdf[:,np.clip(ix[take],0,N)]
    return result
def diff_win_loss(hp,ap,leg):
    cdf=np.cumsum(ap,axis=1)
    # H-A+leg>0 iff A <= ceil(H+leg)-1; loss iff A> floor(H+leg)
    idxwin=np.ceil(K+leg-1e-12).astype(int)-1
    idxloss=np.floor(K+leg+1e-12).astype(int)
    win=(hp*cdf_index(cdf,idxwin)).sum(axis=1)
    lose=(hp*(1-cdf_index(cdf,idxloss))).sum(axis=1)
    # H>N, A<=N => home definitely wins. H>N and A>N both tails unresolved.
    th=np.maximum(0.,1-hp.sum(axis=1))
    ta=np.maximum(0.,1-ap.sum(axis=1))
    win+=th*(1-ta)
    return win,lose,th*ta
def sum_cdf(lh,la):
    total=lh+la
    p=pmf_matrix(total)
    return np.cumsum(p,axis=1)
def point_cdf(cdf,n):
    if n<0:return np.zeros(len(cdf))
    if n>=N:return cdf[:,-1]
    return cdf[:,n]
def split(line):
    q=round(float(line)*4)
    assert abs(q/4-float(line))<1e-8
    if q%2==0:return [(float(line),1.)]
    return [(math.floor(float(line)*2)/2.,.5),(math.ceil(float(line)*2)/2.,.5)]
def market_EV(pH,pA,lh,la,market,line,odds):
    if market=='AH':
        pos=neg=np.zeros(len(lh))
        pos=np.zeros(len(lh));neg=np.zeros(len(lh))
        for leg,w in split(line):
            a,b,_=diff_win_loss(pH,pA,leg)
            pos+=w*a;neg+=w*b
        return {'home':float(((odds['home']-1.)*pos-neg).mean()),
                'away':float(((odds['away']-1.)*neg-pos).mean())}
    if market=='OU':
        cdf=sum_cdf(lh,la)
        pos=np.zeros(len(lh));neg=np.zeros(len(lh))
        for leg,w in split(line):
            over=1-point_cdf(cdf,math.floor(leg))
            under=point_cdf(cdf,math.ceil(leg)-1)
            pos+=w*over;neg+=w*under
        return {'over':float(((odds['over']-1.)*pos-neg).mean()),
                'under':float(((odds['under']-1.)*neg-pos).mean())}
    raise ValueError(market)
def cash(market,line,odds,side,sc):
    hg,ag=map(int,sc.split('-'))
    ret=0.
    for leg,w in split(line):
        diff=hg-ag+leg if side=='home' else ag-hg-leg if side=='away' else hg+ag-leg if side=='over' else leg-hg-ag
        ret+=w*((odds-1) if diff>1e-10 else (-1 if diff<-1e-10 else 0))
    return ret
def score(prob,sc):
    h,a=map(int,sc.split('-'))
    t=0 if h>a else 1 if h==a else 2
    return {'Brier':float(sum((p-int(j==t))**2 for j,p in enumerate(prob))),
        'logloss':float(-math.log(max(prob[t],1e-15)))}
def predict_marginal(lh,la,ah_quote=None,ou_quote=None):
    hp=pmf_matrix(lh);ap=pmf_matrix(la)
    win,loss,tail=diff_win_loss(hp,ap,0.)
    draw=np.maximum(0.,1-win-loss)
    probs=[float(win.mean()),float(draw.mean()),float(loss.mean())]
    s=sum(probs);probs=[max(0.,p/s) for p in probs]
    result={'prob':probs,'tail_both_mean':float(tail.mean()),
       'lambda_home_mean':float(lh.mean()),'lambda_away_mean':float(la.mean()),
       'lambda_max':float(max(lh.max(),la.max()))}
    for market,quote in [('AH',ah_quote),('OU',ou_quote)]:
        if quote is None:continue
        ev=market_EV(hp,ap,lh,la,market,float(quote['line']),quote['odds'])
        side=max(ev,key=lambda s:ev[s])
        result[market]={'side':side,'expected_U':ev[side],
            'realized_U':cash(market,quote['line'],quote['odds'][side],side,quote['score'])}
    return result
audit=Counter()
out=[]
for batch_start in range(0,len(FEATURES),64):
    fs=FEATURES[batch_start:batch_start+64]
    batch=len(fs)
    for k in (1,2):
        name='bayes_prior_'+str(k)
        # Posterior mean = scale/(shape-1) for IG posterior; reconstruct
        # scale only from R5 prior as-of features (not target scores).
        homect=np.array([f['effective_venue_history']['home'] for f in fs])
        awayct=np.array([f['effective_venue_history']['away'] for f in fs])
        means=np.array([[f['posterior_means'][name][field] for field in
          ('home_attack','away_defense','away_attack','home_defense')] for f in fs])
        counts=np.stack([homect,awayct,awayct,homect],axis=1)
        shape=k+1+counts
        scale=(k+counts)*means
        # Inverse Gamma, deterministic scrambled Sobol 256 draws per match.
        dims=[]
        for dim in range(4):
            sample=invgamma.ppf(QMC[None,:,dim],a=shape[:,dim,None],
                              scale=scale[:,dim,None])
            dims.append(sample)
        lh=(dims[0]*dims[1])/np.array([f['league_mean_home_xg'] for f in fs])[:,None]
        la=(dims[2]*dims[3])/np.array([f['league_mean_away_xg'] for f in fs])[:,None]
        if k==1:
            pending=[{'fixture_id':f['fixture_id'],'league':f['league'],
                'season':f['season'],'date':f['date'],'score':f['score'],
                'source':'R5 frozen strict prior-date xG features, uncertainty integrated as R8',
                'market_price_origin':'Historic Crown T12 source-event retrieved after game',
                'Crown_matched':(f['league'],f['fixture_id']) in prices,
                'models':{}} for f in fs]
        for j,f in enumerate(fs):
            key=(f['league'],f['fixture_id'])
            pricepair=prices.get(key)
            args=(pricepair['AH'],pricepair['OU']) if pricepair else (None,None)
            row=pending[j]
            market_mean=np.array(f['candidate_lambda'][name])
            result256=predict_marginal(lh[j],la[j],*args)
            result128=predict_marginal(lh[j,:128],la[j,:128],*args)
            result256.update(score(result256['prob'],f['score']))
            result256['MC128_prob'] =result128['prob']
            result256['MC128_vs_256_max_p_diff']=float(max(abs(x-y) for x,y in zip(result256['prob'],result128['prob'])))
            result256['reference_R5_means']=list(map(float,market_mean))
            result256['reference_lambda_mean_diff']=float(max(abs(market_mean[0]-result256['lambda_home_mean']),abs(market_mean[1]-result256['lambda_away_mean'])))
            row['models']['posterior_predictive_k'+str(k)]=result256
            audit['processed_model_fixture']+=1
            if pricepair:
                for mk in ('AH','OU'):
                    # old R5 point-estimate model must exist for comparison,
                    # only its realized_U is comparable, not same choice.
                    old=pricepair[mk]['models'][name+'_independent']
                    row['models']['posterior_predictive_k'+str(k)][mk]['R5_mean_model_U']=old['net_U']
                    row['models']['posterior_predictive_k'+str(k)][mk]['R5_mean_model_side']=old['side']
            if k==1:
                row['market_Crown_fid']=pricepair['AH']['fid'] if pricepair else None
                row['market_R7_1X2_Brier']=market[(f['league'],pricepair['AH']['fid'])]['models']['market_implied_Poisson']['1X2_brier'] if pricepair else None
                row['market_R7_1X2_prob']=[
                  market[(f['league'],pricepair['AH']['fid'])]['models']['market_implied_Poisson'][x]
                  for x in ('1X2_p_home','1X2_p_draw','1X2_p_away')] if pricepair else None
    out+=pending
    if (batch_start//64)%15==0:print('processed',len(out),'of',len(FEATURES),flush=True)
assert len(out)==len(FEATURES)
def agg(rs):
    z={'n':len(rs),'Crown_matched_n':sum(r['Crown_matched'] for r in rs)}
    for model in ('posterior_predictive_k1','posterior_predictive_k2'):
        r=[x['models'][model] for x in rs]
        z[model]={'n':len(r),
          'Brier':round(sum(x['Brier'] for x in r)/len(r),7),
          'logloss':round(sum(x['logloss'] for x in r)/len(r),7),
          'mean_lambda_home_reference_diff':round(sum(abs(x['lambda_home_mean']-x['reference_R5_means'][0]) for x in r)/len(r),7),
          'mean_lambda_away_reference_diff':round(sum(abs(x['lambda_away_mean']-x['reference_R5_means'][1]) for x in r)/len(r),7),
          'mean_QMC128_vs256_max_probability_gap':round(sum(x['MC128_vs_256_max_p_diff'] for x in r)/len(r),7),
          'max_QMC128_vs256_prob_gap':round(max(x['MC128_vs_256_max_p_diff'] for x in r),7),
          'max_lambda_sampled':round(max(x['lambda_max'] for x in r),4),
          'mean_missing_tail_both':round(sum(x['tail_both_mean'] for x in r)/len(r),9)}
        for market_name in ('AH','OU'):
            x=[r['models'][model][market_name] for r in rs if r['Crown_matched']]
            if not x:continue
            u=sum(a['realized_U'] for a in x);old=sum(a['R5_mean_model_U'] for a in x)
            z[model][market_name]={'n':len(x),'net_U':round(u,5),
              'ROI_pct':round(100*u/len(x),5),
              'R5_point_mean_net_U':round(old,5),
              'paired_delta_U':round(u-old,5),
              'switches':sum(a['side']!=a['R5_mean_model_side'] for a in x),
              'mean_predicted_EV':round(sum(a['expected_U'] for a in x)/len(x),6)}
    if z['Crown_matched_n']:
        z['Crown_market_1X2_Brier']=round(sum(r['market_R7_1X2_Brier'] for r in rs if r['Crown_matched'])/z['Crown_matched_n'],7)
    return z
summary={'name':'R8_GENERALIZED_BAYES_INVERSE_GAMMA_FULL_POSTERIOR_PREDICTIVE',
    'source_R5_features_SHA256':hashlib.sha256(FEAT.read_bytes()).hexdigest(),
    'source_R5_Crown_SHA256':hashlib.sha256(ORIG.read_bytes()).hexdigest(),
    'source_R7_market_SHA256':hashlib.sha256(MARK.read_bytes()).hexdigest(),
    'method':'R5 independent IG theta attack/defense posteriors, k=1 and k=2; use Sobol randomized deterministic 256 draws from four latent distributions, multiply xGF*xGA/league average; each draw generates independent Poisson score distribution; average score probabilities AND contract EV before choosing a side, no EV gate',
    'QMC_seed':20261123,'QMC_draws':256,'nested_convergence_draws':128,
    'source_scope':'Five domestic European club leagues only, no national teams',
    'audit':dict(audit),'overall':agg(out),
    'matched_Crown_only':agg([r for r in out if r['Crown_matched']]),
    'by_season':{str(yy):agg([r for r in out if r['season']==yy]) for yy in sorted({r['season'] for r in out})},
    'by_league':{lg:agg([r for r in out if r['league']==lg]) for lg in sorted({r['league'] for r in out})},
    'limitations':['R5 underlying IG observation likelihood assumes independent exponential xG and power-weighted pseudo-observations. Not full hierarchical Bayes; correlations between team latent attack and defense posterior are ignored.',
       'Sobol integration approximate; 128 vs 256 nested predictions saved per fixture; high goal-count tails truncated at 45 goals per side with ambiguous double high tails counted as draw; track average both-tail mass.',
       'Historical source-event Crown T12 downloaded AFTER games, not true actual pregame received/executable price.',
       'Research cohort previously studied; even forward-as-of match-date xG has unknown actual provider publishing time; no new blind sample.',
       'No historical ROIs used to fit hyperparameters or thresholds; no national teams, no official TG/order/ledger changes.']}
with OUT.open('w') as fd:
    for r in out:fd.write(json.dumps(r,ensure_ascii=False)+'\n')
REPORT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':summary['overall'],'matched_Crown':summary['matched_Crown_only'],'audit':summary['audit']},ensure_ascii=False))
