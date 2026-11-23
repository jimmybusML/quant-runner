#!/usr/bin/env python3
"""R7 cross-source independent validation of AH/OU inverse market fitting,
Hegarty/Whelan-style pivotal-event market prices, proper scoring, mixtures,
and R5/R6 frozen integrity. Contains no model training or optimizers.
"""
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime
import math,json,hashlib
import numpy as np
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r7_market_pricing_20261123'
FREEZE=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123'
MARKET=HERE/'r7_market_implied_2market_20261123.jsonl'
REFUND=HERE/'r7_empirical_refund_AH_ledger.jsonl'
BLEND=HERE/'r7_market_vs_Bayes_fixed_blend_score.jsonl'
OUT=HERE/'r7_independent_market_audit.json'
M=18
i=np.arange(M+1,dtype=float)
D=i[:,None]-i[None,:]
T=i[:,None]+i[None,:]
errors=Counter()
checks=Counter()
def pmf(lam):
    p=np.zeros(M+1)
    p[0]=math.exp(-lam)
    for j in range(1,M+1):p[j]=p[j-1]*lam/j
    return p/p.sum()
def split(line):
    n=round(line*4)
    if abs(n/4-line)>1e-9:raise ValueError(line)
    return [(line,1.)] if n%2==0 else [(math.floor(2*line)/2.,.5),(math.ceil(2*line)/2.,.5)]
def payoff(side,mkt,line,odd,a,b):
    val=0.
    for leg,w in split(line):
        margin=a-b+leg if side=='home' else b-a-leg if side=='away' else a+b-leg if side=='over' else leg-a-b
        val+=w*((odd-1.) if margin>1e-9 else -1. if margin< -1e-9 else 0.)
    return val
def policy_events(line,d):
    n=round(line*4)
    if n%4==2:return 'home_full' if d+line>0 else 'away_full'
    mid=round(-line)
    return 'home_full' if d>mid else 'away_full' if d<mid else 'pivot'
def brier3(p,sc):
    h,a=map(int,sc.split('-'))
    y=0 if h>a else 1 if h==a else 2
    return sum((q-(k==y))**2 for k,q in enumerate(p))
old_receipt=defaultdict(dict)
r5path=FREEZE/'research/r5_bayes_bivar_actual_receipt_20261123.jsonl'
for ln in r5path.open():
    r=json.loads(ln);old_receipt[r['fid']][r['market']]=r
lastMarket={}
for ln in MARKET.open():
    r=json.loads(ln);checks['market_rows']+=1
    m=r.get('market_model_lambda')
    if not m:errors['missing_market_fit']+=1;continue
    lh,la=m['lambda_home'],m['lambda_away']
    p=np.outer(pmf(lh),pmf(la))
    if abs(p.sum()-1)>1e-10:errors['market_score_mass']+=1
    for name,grid,opts in [('AH',D,('home','away')),('OU',T,('over','under'))]:
        contract=r['market_'+name]
        W=L=0.
        for part,w in split(contract['line']):
            boundary=-part if name=='AH' else part
            W+=w*float(p[grid>boundary+1e-10].sum())
            L+=w*float(p[grid<boundary-1e-10].sum())
        residual=contract['odds'][opts[0]]*W-contract['odds'][opts[1]]*L
        checks['market_ratio_checks']+=1
        if abs(residual)>1e-7:errors['market_two_price_no_vig_equal_return']+=1
    q=[float(p[D>0].sum()),float(p[D==0].sum()),float(p[D<0].sum())]
    if abs(brier3(q,r['score'])-r['models']['market_implied_Poisson']['1X2_brier'])>1e-9:
        errors['market_Brier_error']+=1
    if r['cohort']=='actual_HTTP_2026_receipt':
        a=old_receipt[r['fid']]['AH'];o=old_receipt[r['fid']]['OU']
        if a['source_Crown_raw_sha256']!=o['source_Crown_raw_sha256']:
            errors['actual_price_sha_pair']+=1
        if a['Crown_quote_received_utc']!=o['Crown_quote_received_utc']:
            errors['actual_receipt_quote_times_differ']+=1
        time=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
        if not time(a['Crown_quote_received_utc'])<time(a['kickoff_utc']):
            errors['actual_receipt_after_kickoff']+=1
        checks['actual_same_Crown_HTTP_sha_time_pair']+=1
    key=(r['cohort'],r['fid'])
    if key in lastMarket:errors['market_duplicate']+=1
    lastMarket[key]=r
byhist=defaultdict(list)
raw_hist=FREEZE/'research/r5_bayes_bivar_CrownT12_20261123.jsonl'
for ln in raw_hist.open():
    r=json.loads(ln)
    if r['market']=='AH':
        byhist[r['season']].append(r)
def typ(v):return abs(round(v*4))%4
def qrates(rs):
    x=defaultdict(lambda:[0,0])
    for z in rs:
        j=typ(z['line'])
        if j==2:continue
        h,a=map(int,z['score'].split('-'))
        x[j][1]+=1
        x[j][0]+=int(policy_events(z['line'],h-a)=='pivot')
    return {i:h/n for i,(h,n) in x.items()}
for ln in REFUND.open():
    r=json.loads(ln);checks['refund_rows']+=1
    hist=r['season']<2026
    trained=(byhist[r['season']-2]+byhist[r['season']-1]) if hist else (byhist[2024]+byhist[2025])
    # Cache fitted q by year, calculation cheap only 6 times
    q=qrates(trained)
    realq=0. if typ(r['line'])==2 else q[typ(r['line'])]
    if abs(realq-r['trained_pivot_q'])>1e-10:errors['pivot_from_prior_seasons']+=1
    o=r['odds'];h,a=map(int,r['score'].split('-'))
    actual=policy_events(r['line'],h-a)
    if actual!=r['observed']:errors['actual_pivot_classification']+=1
    m=r['market_prob']
    ph,pp,pa=m['p_home_full'],m['p_pivot'],m['p_away_full']
    if min(ph,pp,pa)<-1e-8 or abs(ph+pp+pa-1)>1e-9:errors['market_pivot_mass']+=1
    mid=round(-r['line'])
    homepivot=1.+payoff('home','AH',r['line'],o['home'],mid,0)
    awaypivot=1.+payoff('away','AH',r['line'],o['away'],mid,0)
    mugrosshome=ph*o['home']+pp*homepivot
    mugrossaway=pa*o['away']+pp*awaypivot
    if max(abs(mugrosshome-mugrossaway),abs(mugrosshome-m['market_implied_expected_gross_payout']))>1e-8:
        errors['market_pivotal_cash_inconsistency']+=1
    checks['market_pivotal_expected_cash_checks']+=1
    expectedcash_home=payoff('home','AH',r['line'],o['home'],h,a)
    expectedcash_away=payoff('away','AH',r['line'],o['away'],h,a)
    if max(abs(expectedcash_home-r['actual_net_home']),abs(expectedcash_away-r['actual_net_away']))>1e-9:
        errors['refund_realized_cash_mismatch']+=1
    probs=[ph,pp,pa]
    y=['home_full','pivot','away_full'].index(actual)
    br=sum((v-float(j==y))**2 for j,v in enumerate(probs))
    if abs(br-r['scores']['market']['brier'])>1e-10:errors['refund_market_Brier_mismatch']+=1
for ln in BLEND.open():
    r=json.loads(ln)
    src=lastMarket.get((r['cohort'],r['fid']))
    if not src:errors['blend_market_source_missing']+=1;continue
    pmarket=[src['models']['market_implied_Poisson'][p] for p in ('1X2_p_home','1X2_p_draw','1X2_p_away')]
    key='bayes_prior_2_independent' if r['cohort']=='historical_Crown_T12' else 'bayes_2_independent'
    pbayes=[src['models'][key][p] for p in ('1X2_p_home','1X2_p_draw','1X2_p_away')]
    bm=r['forecast']['market_plus_Bayes_k2_50_50']
    pp=[bm['p_home'],bm['p_draw'],bm['p_away']]
    checks['blend_prob_ratio_checks']+=1
    if max(abs(a-.5*(b+c)) for a,b,c in zip(pp,pmarket,pbayes))>1e-10:
        errors['equal_score_blend_wrong_weight']+=1
    if abs(brier3(pp,r['score'])-bm['Brier'])>1e-9:errors['blend_Brier_wrong']+=1
manifest=FREEZE/'FROZEN_SHA256_MANIFEST.json'
snapshot=json.loads(manifest.read_text())
for meta in snapshot['files']:
    file=FREEZE/meta['file']
    checks['R5_frozen_sha_file_checks']+=1
    if not file.exists() or file.stat().st_size!=meta['bytes']:
        errors['R5_frozen_lost_or_sizediff']+=1;continue
    if hashlib.sha256(file.read_bytes()).hexdigest()!=meta['sha256']:
        errors['R5_frozen_sha_changed']+=1
for key,val in {'market_rows':10046,'market_ratio_checks':20092,
    'refund_rows':7211,'blend_prob_ratio_checks':10046,
    'actual_same_Crown_HTTP_sha_time_pair':138,
    'R5_frozen_sha_file_checks':218}.items():
    if checks[key]!=val:errors['audit_expected_count_'+key]+=1
result={'status':'PASS' if not errors else 'FAIL','checks':dict(checks),
        'errors':dict(errors),'R5_manifest_SHA256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'data_SHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (MARKET,REFUND,BLEND)},
        'scope':'Five domestic club leagues only. Crown T12 historic source event vs actual HTTP old receipt distinguished. Independent math/recovery checks.'}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':result['checks'],'errors':result['errors']},ensure_ascii=False))
assert result['status']=='PASS'