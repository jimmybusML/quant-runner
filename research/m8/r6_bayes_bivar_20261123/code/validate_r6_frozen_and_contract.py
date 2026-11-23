#!/usr/bin/env python3
"""R6 independent cash/expected-EV/probability-mass audit from stored
contract threshold probabilities. No imports from R5/R6 model settlement code.
Also verify the freeze manifest for R5 is still byte-identical.
"""
from pathlib import Path
from collections import Counter
import math,json,hashlib
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r6_bayes_bivar_20261123'
LEDGER=HERE/'r6_contract_calibration_ledger.jsonl'
RECEIPTS=HERE/'r6_actual_receipt_equal_weight_blends.jsonl'
REPORT=HERE/'r6_independent_math_and_freeze_audit.json'
FREEZE=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123'
MANIFEST=json.loads((FREEZE/'FROZEN_SHA256_MANIFEST.json').read_text())
C=Counter();err=Counter();maxEV=0.;maxmass=0.
def legs(h):
    n=round(h*4)
    assert abs(n/4-h)<1e-9
    return [(h,1.)] if n%2==0 else [(math.floor(2*h)/2.,.5),(math.ceil(2*h)/2.,.5)]
def payoff(market,line,odd,side,score_or_margin,margin_input=False):
    if margin_input:
        x=score_or_margin
        if market=='AH':home,away=x,0.
        else:home,away=x,0.
    else:home,away=map(int,score_or_margin.split('-'))
    val=0.
    for v,w in legs(line):
        if side=='home':d=home-away+v
        elif side=='away':d=away-home-v
        elif side=='over':d=home+away-v
        elif side=='under':d=v-home-away
        else:raise RuntimeError(side)
        val+=w*((odd-1.) if d>1e-9 else -1. if d<-1e-9 else 0.)
    return val
def regions(P):
    x=sorted(P)
    z=[(x[0]-2,1.-P[x[0]])]
    for a,b in zip(x,x[1:]):z.append((a+1,P[a]-P[b]))
    z.append((x[-1]+2,P[x[-1]]))
    return z
for line in LEDGER.open():
    r=json.loads(line)
    C['historical_market_rows']+=1
    for name,params in r['methods'].items():
        for mode in ('raw','global','league'):
            if mode not in params:continue
            z=params[mode]
            C['historical_model_state_checks']+=1
            actual=payoff(r['market'],r['line'],r['odds'][z['side']],z['side'],r['score'])
            if abs(actual-z['U'])>1e-9:err['historical_cash']+=1
            surv={int(k):v for k,v in z['prob_survival'].items()}
            mass=regions(surv)
            sx=sum(p for d,p in mass)
            maxmass=max(maxmass,abs(sx-1.))
            if abs(sx-1)>1e-9 or min(p for d,p in mass)<-1e-9:
                err['invalid_survival_mass']+=1
            pred=sum(p*payoff(r['market'],r['line'],r['odds'][z['side']],z['side'],d,True) for d,p in mass)
            maxEV=max(maxEV,abs(pred-z['estimatedEV']))
            if abs(pred-z['estimatedEV'])>1e-7:err['historical_expected_EV']+=1
            br=sum((p-float(r['event']>t))**2 for t,p in surv.items())/len(surv)
            if abs(br-z['brier'])>1e-10:err['historical_brier']+=1

for line in RECEIPTS.open():
    r=json.loads(line);C['receipt_market_rows']+=1
    for name,p in r['model'].items():
        C['receipt_method_cash_checks']+=1
        expected=payoff(r['market'],r['line'],r['odds'][p['side']],p['side'],r['score'])
        if abs(expected-p['U'])>1e-9:err['receipt_cash']+=1

# Audit independent freeze integrity after the entire R6 experiment.
for item in MANIFEST['files']:
    C['frozen_file_sha256_checks']+=1
    path=FREEZE/item['file']
    if not path.exists():
        err['freeze_file_missing']+=1
        continue
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if sha!=item['sha256']:err['freeze_sha_changed']+=1
    if path.stat().st_size!=item['bytes']:err['freeze_file_size_changed']+=1
if len(MANIFEST['files'])!=218:err['freeze_inventory_count']+=1
if C['historical_market_rows']!=19816:err['historical_rowcount']+=1
if C['receipt_market_rows']!=276:err['receipt_rowcount']+=1
assert not err,err
report={'status':'PASS','errors':dict(err),'checks':dict(C),
    'max_independent_EV_error':maxEV,'max_probability_mass_error':maxmass,
    'R5_frozen_manifest_sha256':hashlib.sha256((FREEZE/'FROZEN_SHA256_MANIFEST.json').read_bytes()).hexdigest(),
    'R6_ledger_sha256':hashlib.sha256(LEDGER.read_bytes()).hexdigest(),
    'note':'Independent R6 cash + contract probability audit and full unchanged 218-file R5 freeze check'}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))