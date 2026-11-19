#!/usr/bin/env python3
"""Crown AH + Crown 1X2 robust cross-contract dominance LP (research, no trading).
Prices are source-event timestamps from retrospective historical responses. A
positive theoretical LP outcome is NOT proof of simultaneous live executable odds.
"""
import collections,datetime as dt,hashlib,json,math,os
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from scipy.optimize import linprog

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses')
FROZEN=Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
OUT=ROOT/'research/m8/m8_cross_contract_dominance_20261119'
def utc(s):
    if not s:return None
    a=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
    return a if a.tzinfo else a.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(dt.timezone.utc)
def settle(line,side,dec,delta):
    if side=='away':line,delta=-line,-delta
    # each Asian quarter settles on two half lines; non-quarter both legs same
    lo=math.floor(line*2+1e-9)/2
    hi=math.ceil(line*2-1e-9)/2
    v=0.
    for l in (lo,hi):
        x=delta+l
        v+=0.5*((dec-1) if x>1e-8 else (-1 if x<-1e-8 else 0))
    return v
def solve(ah,odd):
    # outcomes of match goal difference cover AH win/push/lose thresholds and 1X2 outcomes.
    line,h,a=ah;h1,d1,a1=odd
    diff=list(range(-40,41))
    pay=np.array([[settle(line,'home',h,del_),
                   settle(line,'away',a,del_),
                   h1-1 if del_>0 else -1,
                   d1-1 if del_==0 else -1,
                   a1-1 if del_<0 else -1] for del_ in diff])
    c=np.array([0.,0.,0.,0.,0.,-1.])
    A_ub=np.column_stack((-pay,np.ones(len(diff))))
    b_ub=np.zeros(len(diff))
    A_eq=np.array([[1.,1.,1.,1.,1.,0.]])
    result=linprog(c,A_ub=A_ub,b_ub=b_ub,A_eq=A_eq,b_eq=np.array([1.]),
                   bounds=[(0,None)]*5+[(None,None)],method='highs')
    if not result.success:raise RuntimeError(result.message)
    return float(result.x[-1]),[float(x) for x in result.x[:5]]
def run():
    frozen={str(json.loads(x)['fid']) for x in FROZEN.open() if x.strip()}
    quality=collections.Counter();year=collections.defaultdict(lambda:collections.Counter())
    examples=[];allrows=[]
    for idx,p in enumerate(sorted(SOURCE.glob('*.json'))):
        quality['files']+=1
        try:
            body=json.loads(p.read_text());matches=body.get('data') or []
            if not isinstance(matches,list):quality['not_list']+=1;continue
            for m in matches:
                fid=str(m.get('id',''))
                if not fid or fid in frozen:quality['frozen_or_missing']+=1;continue
                ko=utc(m.get('start'))
                if not ko or not 2019<=ko.year<=2026:continue
                cutoff=ko-dt.timedelta(hours=1)
                b=next((x for x in m.get('bookmakers',[]) if x.get('slug')=='crown'),None)
                if not b:quality['no_crown']+=1;continue
                # only source quotes known strictly by T-1h; never use final close if later.
                ah=[]
                for q in b.get('asian_list') or []:
                    try:
                        t=utc(q[4]);l=float(q[1]);h=float(q[2]);a=float(q[3])
                        if t and t<=cutoff and all(math.isfinite(z) for z in (l,h,a)) and h>1 and a>1 and abs(l*4-round(l*4))<1e-8:
                            ah.append((t,(l,h,a)))
                    except Exception:continue
                odds=[]
                for label in ('open','close'):
                    q=(b.get('odds') or {}).get(label)
                    if not q:continue
                    try:
                        t=utc(q['time'])
                        dec=tuple(float(q[k]) for k in ('home','draw','away'))
                        if t and t<=cutoff and all(math.isfinite(z) and z>1 for z in dec):
                            odds.append((t,dec,label))
                    except Exception:continue
                if not ah or not odds:
                    quality['missing_pregame_AH_or_1x2']+=1;continue
                ah.sort(key=lambda x:x[0]);odds.sort(key=lambda x:x[0])
                ah_t,ah_quote=ah[-1];o_t,o_quote,label=odds[-1]
                age=(max(ah_t,o_t)-min(ah_t,o_t)).total_seconds()/3600
                worst,stakes=solve(ah_quote,o_quote)
                result={'fid':fid,'year':ko.year,'kickoff_utc':ko.isoformat(),
                        'ah_event_utc':ah_t.isoformat(),'1x2_event_utc':o_t.isoformat(),
                        'source_event_skew_hours':round(age,6),'1x2_quote_type':label,
                        'ah':list(ah_quote),'1x2':list(o_quote),
                        'LP_min_profit_unit_stake':round(worst,8),
                        'theoretical_positive':worst>1e-8,
                        'stake_AH_home_away_1x2_home_draw_away':[round(x,8) for x in stakes],
                        'historical_source_only_not_live_receipt':True}
                allrows.append(result)
                year[ko.year]['total']+=1
                if worst>1e-8:
                    year[ko.year]['theoretical_positive']+=1
                    if len(examples)<30:examples.append(result)
                if age>0.5:year[ko.year]['cross_market_skew_over_30m']+=1
        except Exception as e:
            quality['error_'+type(e).__name__]+=1
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'per_fid_research.jsonl').open('w') as f:
        for r in allrows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
    results={'study':'Crown AH+1X2 score-independent multi-contract LP feasibility',
             'not_executable':'historical prices are post-retrieved, 1X2 quote can be old relative to AH; no proof both legs tradable together',
             'math':'maximize min profit over football result goal differences, total stake=1, nonnegative stake, correct quarter-line legs',
             'source':str(SOURCE),'frozen_sha256':hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
             'quality':dict(quality),'by_year':{str(y):dict(c) for y,c in sorted(year.items())},
             'unique_fids':len({r['fid'] for r in allrows}),'records':len(allrows),
             'positive_theoretical':sum(r['theoretical_positive'] for r in allrows),
             'skew_over_30min':sum(r['source_event_skew_hours']>0.5 for r in allrows),
             'examples':examples,'actual_live_contract_arbitrage_confirmed':0}
    (OUT/'summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in results.items() if k!='examples'},ensure_ascii=False))
if __name__=='__main__':run()
