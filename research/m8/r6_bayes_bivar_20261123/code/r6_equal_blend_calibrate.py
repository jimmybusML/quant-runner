#!/usr/bin/env python3
"""R6 independent Poisson/Bayes/bivariate and fixed equal-weight score-distribution
mixtures; Asian five-state contract calibration strictly trained on previous
two seasons and separately evaluated on next season. Pure historical research.
DOES NOT modify frozen R5 data, production, order rules, or Telegram.
"""
import json,math,hashlib
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r6_bayes_bivar_20261123'
SOURCE=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research/r5_bayes_bivar_CrownT12_20261123.jsonl'
LEDGER=HERE/'r6_contract_calibration_ledger.jsonl'
SUMMARY=HERE/'r6_equal_weight_blends_and_rolling_calibration.json'
N=20
K=np.arange(N+1,dtype=float)
H=K[:,None];A=K[None,:]
DH=H-A
TT=H+A
ALL_MODELS=('independent_poisson','bayes_prior_1_independent',
    'bayes_prior_2_independent','bayes_prior_5_independent',
    'bivar_empirical_c','bayes_prior_2_bivar_fixed_c010',
    'equal_blend_independent_and_bayes1','equal_blend_bayes1_and_bayes2')
RAW_MAP={
 'independent_poisson':'independent_poisson',
 'bayes_prior_1_independent':'bayes_prior_1_independent',
 'bayes_prior_2_independent':'bayes_prior_2_independent',
 'bayes_prior_5_independent':'bayes_prior_5_independent',
 'bivar_empirical_c':'bivar_empirical_c',
 'bayes_prior_2_bivar_fixed_c010':'bayes_prior_2_bivar_fixed_c010'}
CHECKS=Counter()
def pois(lam):
    x=np.zeros(N+1,dtype=float);x[0]=math.exp(-lam)
    for i in range(1,N+1):x[i]=x[i-1]*lam/i
    return x/x.sum()
def joint(lh,la,c):
    if c<=0:return np.outer(pois(lh),pois(la))
    x=pois(lh-c);y=pois(la-c);w=pois(c)
    z=np.zeros((N+1,N+1),dtype=float)
    for k,p in enumerate(w):
        if p<1e-16:continue
        m=N+1-k
        z[k:,k:]+=p*np.outer(x[:m],y[:m])
    return z/z.sum()
def legs(v):
    q=round(v*4)
    assert abs(q/4-v)<1e-8
    return [(v,1.)] if q%2==0 else [(math.floor(v*2)/2.,.5),(math.ceil(v*2)/2.,.5)]
def thresholds(mkt,v):
    z=set()
    for leg,w in legs(v):
        k=math.floor(-leg) if mkt=='AH' else math.floor(leg)
        z.add(k)
        if abs(leg-round(leg))<1e-10:z.add(k-1)
    return sorted(z)
def evalue(mkt,line,odds,p):
    dist=DH if mkt=='AH' else TT
    choices=('home','away') if mkt=='AH' else ('over','under')
    ans={}
    for side in choices:
        total=0.
        for v,w in legs(line):
            val=dist+v if side=='home' else -dist-v if side=='away' else dist-v if side=='over' else v-dist
            total+=w*float((p*np.where(val>1e-9,odds[side]-1.,np.where(val< -1e-9,-1.,0.))).sum())
        ans[side]=total
    return ans
def cash(mkt,line,odd,side,score):
    hg,ag=map(int,score.split('-'))
    tot=0.
    for v,w in legs(line):
        margin=hg-ag+v if side=='home' else ag-hg-v if side=='away' else hg+ag-v if side=='over' else v-hg-ag
        tot+=w*((odd-1.) if margin>1e-9 else -1. if margin<-1e-9 else 0.)
    return tot
def surv(mkt,p,ts):
    dist=DH if mkt=='AH' else TT
    return {t:float((p*(dist>t)).sum()) for t in ts}

raw=[json.loads(s) for s in SOURCE.open() if s.strip()]
assert len(raw)==19816
groups=defaultdict(list)
matrix_cache={}
last_fid=None
for r in raw:
    fid=r['fid']
    if fid!=last_fid:
        matrix_cache={}
        last_fid=fid
    def get(label):
        if label not in matrix_cache:
            z=r['models'][label]
            matrix_cache[label]=joint(z['lambda_home'],z['lambda_away'],z['common_shock_c'])
        return matrix_cache[label]
    P={m:get(m) for m in RAW_MAP}
    P['equal_blend_independent_and_bayes1']=(P['independent_poisson']+P['bayes_prior_1_independent'])/2.
    P['equal_blend_bayes1_and_bayes2']=(P['bayes_prior_1_independent']+P['bayes_prior_2_independent'])/2.
    assert set(P)==set(ALL_MODELS)
    mkt=r['market'];line=r['line'];year=r['season'];lg=r['league']
    ts=thresholds(mkt,line)
    score=r['score'];hg,ag=map(int,score.split('-'))
    event=hg-ag if mkt=='AH' else hg+ag
    entry={'fid':fid,'market':mkt,'season':year,'league':lg,
       'line':line,'odds':r['odds'],'score':score,'event':event,
       't':ts,'methods':{}}
    for name,p in P.items():
        assert abs(float(p.sum())-1)<1e-8
        e=evalue(mkt,line,r['odds'],p)
        side=max(e,key=lambda s:e[s])
        cash_u=cash(mkt,line,r['odds'][side],side,score)
        probs=surv(mkt,p,ts)
        if name in RAW_MAP:
            old=r['models'][name]
            if old['side']!=side:CHECKS['baseline_side_mismatch']+=1
            if abs(old['net_U']-cash_u)>1e-8:CHECKS['baseline_cash_mismatch']+=1
            if abs(old['expected_U']-e[side])>1e-7:CHECKS['baseline_EV_mismatch']+=1
        entry['methods'][name]={'raw':{'side':side,'U':cash_u,'estimatedEV':e[side],
                                      'brier':sum((probs[t]-float(event>t))**2 for t in ts)/len(ts),
                                      'prob_survival':{str(t):probs[t] for t in ts}},
                               'survival_probs':{str(t):probs[t] for t in ts}}
    groups[(mkt,year)].append(entry)

assert not CHECKS,CHECKS
print('Built all historical probability vectors without R5 discrepancies',sum(map(len,groups.values())),flush=True)
def fit(train,model,lg=None):
    pairs=[]
    for row in train:
        if lg is not None and row['league']!=lg:continue
        for k,v in row['methods'][model]['survival_probs'].items():
            pairs.append((v,int(row['event']>int(k))))
    if not pairs:return None
    pairs.sort()
    blocks=[]
    for prob,hit in pairs:
        blocks.append([prob,prob,1.,float(hit)])
        while len(blocks)>1 and blocks[-2][3]/blocks[-2][2]>blocks[-1][3]/blocks[-1][2]:
            b=blocks.pop();a=blocks[-1];a[1]=b[1];a[2]+=b[2];a[3]+=b[3]
    return [(b[1],b[3]/b[2]) for b in blocks]
def apply(blocks,p):
    if blocks is None:return p
    l,h=0,len(blocks)
    while l<h:
        i=(l+h)//2
        if blocks[i][0]<p:l=i+1
        else:h=i
    return blocks[min(l,len(blocks)-1)][1]
def calEV(mkt,line,odds,p):
    sides=('home','away') if mkt=='AH' else ('over','under')
    value={}
    for side in sides:
        v=0.
        for part,w in legs(line):
            k=math.floor(-part) if mkt=='AH' else math.floor(part)
            pos=p[k]
            # Whole-number line may push; the relevant loss is P(score<=k-1)
            loss=1.-(p[k-1] if abs(part-round(part))<1e-10 else pos)
            wprob,lprob=(pos,loss) if side in ('home','over') else (loss,pos)
            v+=w*(wprob*(odds[side]-1)-lprob)
        value[side]=v
    return value

# All 2019/20-2025/26 retained. For 2021 onward calibrate using prior two seasons.
for market in ('AH','OU'):
    for year in range(2021,2026):
        training=groups[(market,year-2)]+groups[(market,year-1)]
        training_leagues=sorted({r['league'] for r in training})
        fits={}
        for name in ALL_MODELS:
            fits[name]={'global':fit(training,name)}
            fits[name]['by_league']={lg:fit(training,name,lg) for lg in training_leagues}
        for r in groups[(market,year)]:
            for name in ALL_MODELS:
                base={int(k):v for k,v in r['methods'][name]['survival_probs'].items()}
                for mode,pm in (('global',fits[name]['global']),
                                ('league',fits[name]['by_league'].get(r['league']))):
                    calibrated={k:apply(pm,v) for k,v in base.items()}
                    ts=sorted(calibrated)
                    if any(calibrated[a]<calibrated[b]-1e-10 for a,b in zip(ts,ts[1:])):
                        CHECKS['non_monotone_CDF']+=1
                    e=calEV(market,r['line'],r['odds'],calibrated)
                    side=max(e,key=lambda k:e[k])
                    u=cash(market,r['line'],r['odds'][side],side,r['score'])
                    r['methods'][name][mode]={
                        'side':side,'U':u,'estimatedEV':e[side],
                        'brier':sum((calibrated[t]-float(r['event']>t))**2 for t in ts)/len(ts),
                        'prob_survival':{str(t):calibrated[t] for t in ts}}
        print('Calibrated',market,year,'n',len(groups[(market,year)]),flush=True)
assert not CHECKS,CHECKS
ledger=[r for key in sorted(groups) for r in groups[key]]
with LEDGER.open('w') as f:
    for r in ledger:f.write(json.dumps(r,ensure_ascii=False)+'\n')
def summarize(arr,mode):
    n=len(arr)
    z={'n':n}
    for model in ALL_MODELS:
        valid=[r for r in arr if mode in r['methods'][model]]
        count=len(valid)
        u=sum(r['methods'][model][mode]['U'] for r in valid)
        z[model]={'n':count,'U':round(u,5),
                  'ROI_pct':round(100*u/count,5) if count else None,
                  'mean_estimated_EV':round(sum(r['methods'][model][mode]['estimatedEV'] for r in valid)/count,6) if count else None,
                  'Brier':round(sum(r['methods'][model][mode]['brier'] for r in valid)/count,7) if count else None,
                  'changed_direction_vs_independent_raw':sum(
                    r['methods'][model][mode]['side']!=r['methods']['independent_poisson']['raw']['side'] for r in valid)}
    return z
result={'study':'R6_EQUAL_WEIGHTS_VS_FROZEN_R5_AND_PREVIOUS_TWO_SEASONS_AH_OU_SURVIVAL_CALIBRATION',
 'models':list(ALL_MODELS),'sample_count':len(ledger),
 'frozen_R5_SHA256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'raw':{m:summarize([r for r in ledger if r['market']==m],'raw') for m in ('AH','OU')},
 'rolling_two_season':{m:{v:summarize([r for r in ledger if r['market']==m and r['season']>=2021],v)
    for v in ('raw','global','league')} for m in ('AH','OU')},
 'by_season':{str(y):{m:{v:summarize([r for r in ledger if r['market']==m and r['season']==y],v)
     for v in ('raw','global','league')} for m in ('AH','OU')} for y in range(2019,2026)},
 'by_league':{lg:{m:{v:summarize([r for r in ledger if r['market']==m and r['league']==lg and r['season']>=2021],v)
    for v in ('raw','global','league')} for m in ('AH','OU')}
    for lg in sorted({r['league'] for r in ledger})},
 'methods_summary':{
   'equal_blends':'Fixed equal weights 0.5, chosen for a direct complementarity test without optimizing any ROI, no new trade rule',
   'global_vs_league_isotonic':'Monotone piecewise-constant PAV on previous TWO historical seasons survival events P(goal-difference or total > integer)',
   'quarter_lines':'AH/OU all half/quarter pushes preserved by legs, one side each fixture regardless of EV sign',
   'calibration_is_research_only':'No EV Gate, no user-approved product rule or new actual Telegram order'},
 'limitations':['Historic Crown T12 source events retrieved after games: NOT true pregame received prices',
  'Past explored fixtures and model choices: rolling chronologically fit but overall work is not fresh blinded out-of-sample',
  'Historical published xG original timestamps are unverified',
  'Equal-weight blends are only research sensitivities, not user authorized official combination',
  'No national team matches, no official M8 or TG changes'],
 'checks':dict(CHECKS)}
SUMMARY.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'raw':result['raw'],'rolled':result['rolling_two_season']},ensure_ascii=False))
