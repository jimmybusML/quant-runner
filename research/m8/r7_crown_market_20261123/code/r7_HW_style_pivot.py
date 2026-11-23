#!/usr/bin/env python3
"""R7 B: Hegarty-Whelan-style Asian handicap implied 3-event probabilities.
Condition on empirically estimated pivotal goal-difference probability by
handicap fraction, using strictly preceding two FULL seasons. Market prices
determine other two probabilities under equal expected gross return.
Not a verbatim published-paper reproduction; source code/data provenance
differs, but follows paper section 4.1 payout-equation idea.
Club leagues only. No EV eligibility condition or real trades.
"""
from pathlib import Path
from collections import defaultdict,Counter
import math,json,hashlib
from scipy.stats import skellam
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r7_market_pricing_20261123'
F=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
SRC=F/'r5_bayes_bivar_CrownT12_20261123.jsonl'
ACT=F/'r5_bayes_bivar_actual_receipt_20261123.jsonl'
LEDGER=HERE/'r7_empirical_refund_AH_ledger.jsonl'
SUMMARY=HERE/'r7_empirical_refund_AH_summary.json'
a=[json.loads(s) for s in SRC.open() if '"market": "AH"' in s]
if len(a)!=9908:
    a=[r for r in map(json.loads,SRC.open()) if r['market']=='AH']
assert len(a)==9908
recv=[r for r in map(json.loads,ACT.open()) if r['market']=='AH']
assert len(recv)==138
def legs(h):
    n=round(h*4)
    assert abs(n/4-h)<1e-9
    return [(h,1.)] if n%2==0 else [(math.floor(2*h)/2.,.5),(math.ceil(2*h)/2.,.5)]
def payout(side,handicap,odd,diff):
    z=0.
    for leg,w in legs(handicap):
        x=diff+leg if side=='home' else -diff-leg
        z+=w*((odd-1.) if x>1e-9 else -1. if x< -1e-9 else 0.)
    return z
def classify(diff,line):
    n=round(line*4)
    if n%4==2: # half-point: no push/partial
        return 'home_full' if diff+line>0 else 'away_full'
    pivot=round(-line)
    return 'home_full' if diff>pivot else 'away_full' if diff<pivot else 'pivot'
def quote_type(line):
    return abs(round(line*4))%4 # 0 integer, 1 .25, 2 .5, 3 .75
def estimate_q(rows):
    by=defaultdict(lambda: [0,0])
    for r in rows:
        qt=quote_type(r['line'])
        if qt==2:continue
        d=lambda sc: (int(sc.split('-')[0])-int(sc.split('-')[1])) 
        kind=classify(d(r['score']),r['line'])
        by[qt][0]+=int(kind=='pivot')
        by[qt][1]+=1
    return {key:(v[0]/v[1] if v[1] else None) for key,v in by.items()},dict(by)
def implied(ah,rate):
    line=ah['line'];odd=ah['odds'];typ=quote_type(line)
    q=0. if typ==2 else rate.get(typ)
    if q is None:return None
    oh,oa=odd['home'],odd['away']
    pivot=round(-line)
    gh=1.+payout('home',line,oh,pivot)
    ga=1.+payout('away',line,oa,pivot)
    ph=((1-q)*oa+q*(ga-gh))/(oh+oa)
    pa=1-q-ph
    if min(ph,pa,q)<-1e-10:return None
    mu=ph*oh+q*gh
    mu_away=pa*oa+q*ga
    assert abs(mu-mu_away)<1e-9,(line,oh,oa,mu,mu_away)
    return {'p_home_full':ph,'p_pivot':q,'p_away_full':pa,
        'market_implied_expected_gross_payout':mu,
        'market_implied_expected_net_return':mu-1.,
        'pivot_gross_home':gh,'pivot_gross_away':ga}
def poisson_prob(ah,model):
    lh,la=(ah['models'][model]['lambda_home'],ah['models'][model]['lambda_away'])
    line=ah['line']
    if quote_type(line)==2:
        n=math.floor(-line)
        ph=float(skellam.sf(n,lh,la));pa=float(skellam.cdf(n,lh,la))
        return [ph,0.,pa]
    pivot=round(-line)
    return [float(skellam.sf(pivot,lh,la)),
            float(skellam.pmf(pivot,lh,la)),
            float(skellam.cdf(pivot-1,lh,la))]
def scored(probs,actual):
    outcome={'home_full':0,'pivot':1,'away_full':2}[actual]
    return {'brier':sum((p-float(i==outcome))**2 for i,p in enumerate(probs)),
            'logloss':-math.log(max(probs[outcome],1e-15)),
            'pivot_Brier':(probs[1]-float(outcome==1))**2}
groups=defaultdict(list)
for r in a:groups[r['season']].append(r)
years=sorted(groups)
assert years==list(range(2019,2026))
output=[];audit=Counter()
for yr in years:
    if yr<2021:continue
    train=groups[yr-2]+groups[yr-1]
    q,counts=estimate_q(train)
    audit['training_year_'+str(yr)+'_n']=len(train)
    for r in groups[yr]:
        market=implied(r,q)
        if market is None:
            audit['ill_conditioned_market_probability']+=1
            continue
        hg,ag=map(int,r['score'].split('-'))
        actual=classify(hg-ag,r['line'])
        mprobs=[market['p_home_full'],market['p_pivot'],market['p_away_full']]
        scores={'market':scored(mprobs,actual)}
        for model in ('independent_poisson','bayes_prior_1_independent','bayes_prior_2_independent'):
            pr=poisson_prob(r,model)
            scores[model]=scored(pr,actual)
        actual_cash_home=payout('home',r['line'],r['odds']['home'],hg-ag)
        actual_cash_away=payout('away',r['line'],r['odds']['away'],hg-ag)
        output.append({'fid':r['fid'],'season':yr,'league':r['league'],
            'line':r['line'],'odds':r['odds'],'score':r['score'],
            'observed':actual,'trained_pivot_q':q[quote_type(r['line'])] if quote_type(r['line'])!=2 else 0.,
            'trained_pivot_rate_by_type':{str(key):v for key,v in q.items()},
            'market_prob':market,'scores':scores,
            'actual_net_home':actual_cash_home,'actual_net_away':actual_cash_away})
# 2026 old actual HTTP prices tested using PRIOR two years 2024+2025 prices.
q_recv,c_recv=estimate_q(groups[2024]+groups[2025])
rcvd=[]
for r in recv:
    m=implied(r,q_recv)
    if m is None:
        audit['receipt_invalid_market_probability']+=1
        continue
    hg,ag=map(int,r['score'].split('-'))
    outcome=classify(hg-ag,r['line'])
    scores={'market':scored([m['p_home_full'],m['p_pivot'],m['p_away_full']],outcome)}
    for name in ('same_season_ratio_independent','bayes_1_independent','bayes_2_independent'):
        scores[name]=scored(poisson_prob(r,name),outcome)
    rcvd.append({'fid':r['fid'],'season':2026,'league':r['league_id'],
          'cohort':'actual_old_pre_kickoff_HTTP_receipt','score':r['score'],
          'line':r['line'],'odds':r['odds'],'observed':outcome,
          'market_prob':m,'scores':scores,'trained_pivot_q':q_recv[quote_type(r['line'])] if quote_type(r['line'])!=2 else 0.,
          'actual_net_home':payout('home',r['line'],r['odds']['home'],hg-ag),
          'actual_net_away':payout('away',r['line'],r['odds']['away'],hg-ag)})
with LEDGER.open('w') as fd:
    for r in output+rcvd:fd.write(json.dumps(r,ensure_ascii=False)+'\n')
def agg(rows):
    n=len(rows);result={'n':n}
    for key in sorted({model for r in rows for model in r['scores']}):
        valid=[r['scores'][key] for r in rows if key in r['scores']]
        d=len(valid)
        result[key]={'n':d,'Brier_three_outcomes':round(sum(r['brier'] for r in valid)/d,7) if d else None,
            'logloss_three_outcomes':round(sum(r['logloss'] for r in valid)/d,7) if d else None,
            'pivot_binary_Brier':round(sum(r['pivot_Brier'] for r in valid)/d,7) if d else None}
    result['mean_implied_net_book_margin']=round(sum(r['market_prob']['market_implied_expected_net_return'] for r in rows)/n,6) if n else None
    result['observed_equal_home_away_net']=round(sum((r['actual_net_home']+r['actual_net_away'])/2 for r in rows)/n,6) if n else None
    return result
summary={'research':'R7_HW_STYLE_PAST_TWO_SEASON_REFUND_PROBABILITY_FOR_ASIAN_HANDICAP',
    'research_method':'Hegarty-Whelan 2025 Section 4.1 idea: solve 3 event probabilities with market-equal-gross-return and historical class-specific pivot probability; strictly PRIOR TWO seasons in this R7 implementation. NOT claiming exact paper replication for Crown.',
    'source':'https://www.karlwhelan.com/Papers/IJF.pdf',
    'sample':{'historical_2021_2025':agg(output),'actual_2026_old_HTTP':agg(rcvd)},
    'by_season':{str(y):agg([r for r in output if r['season']==y]) for y in range(2021,2026)},
    'q_training_by_target_season':{str(y):{'q':{str(k):v for k,v in estimate_q(groups[y-2]+groups[y-1])[0].items()},
      'counts':{str(k):v for k,v in estimate_q(groups[y-2]+groups[y-1])[1].items()}} for y in range(2021,2026)},
    'q_training_2026_receipt':{'q':{str(k):v for k,v in q_recv.items()},'counts':{str(k):v for k,v in c_recv.items()}},
    'audit':dict(audit),'historical_source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
    'limitations':['AH-only Hegarty-Whelan style empirical class pivotal probability; no goal model needed for market probability, except model comparison.',
       'For .5 lines pivotal probability identically zero; for integer/.25/.75 estimated from previous seasons, no target outcome in estimated q.',
       'Results conditional on equal expected gross payout on both sides; market inefficiencies may violate assumption.',
       'Historical Crown T12 prices collected post-match, not actual pregame HTTP receipt; 2026 receipt old offline cohort uses previous historic type-q transferred across years and provider.',
       'No national teams; no trading eligibility gate or official TG orders.']}
SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sample':summary['sample'],'q_2026':summary['q_training_2026_receipt'],'audit':dict(audit)},ensure_ascii=False))