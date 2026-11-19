#!/usr/bin/env python3
"""MR1 real receipt AH + 1X2 joint theoretical dominance research.
Only hashes/quote timing; no trading or API requests. Multiple horizons per FID counted separately.
"""
import collections,datetime as dt,hashlib,json,math,os
from pathlib import Path
from m8_cross_contract_dominance_20261119 import solve,utc,OUT

MR1=Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23')
def main():
    quality=collections.Counter();bins=collections.Counter();seen=set();allrows=[];examples=[]
    for l in (MR1/'snapshot-index.jsonl').open():
        r=json.loads(l)
        if r.get('classification')!='SNAPSHOT_OK':continue
        try:
            p=MR1/r['snapshot_path'];raw=p.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=r['snapshot_sha256']:
                quality['snapshot_sha_fail']+=1;continue
            s=json.loads(raw);received=utc(s.get('received_at'));kick=utc(s.get('kickoff_at'))
            if not received or not kick or received>=kick:quality['not_pregame']+=1;continue
            if s.get('source_bookmaker')!='crown' or not s.get('source_bookmaker_verified'):
                quality['not_crown_verified']+=1;continue
            ah=s.get('AH') or {};one=s.get('X1X2') or {}
            try:
                line=float(ah['line']) # comma-separated two-lines are not same singular AH
                prices=tuple(float(ah[k]) for k in ('home_price','away_price'))
                prices1=tuple(float(one[k]) for k in ('home_price','draw_price','away_price'))
                if not all(math.isfinite(z) and z>1 for z in prices+prices1):raise ValueError()
            except Exception:quality['missing_or_ambiguous_contract']+=1;continue
            at=utc(ah.get('observed_at_utc'));ot=utc(one.get('observed_at_utc'))
            if not at or not ot or max(at,ot)>received:
                quality['source_event_not_known_at_receive']+=1;continue
            skew=abs((ot-at).total_seconds())/3600
            payoff,stakes=solve((line,*prices),prices1)
            row={'fid':str(r['match_id']),'horizon':r['target_horizon'],
                 'receive_utc':received.isoformat(),'kickoff_utc':kick.isoformat(),
                 'AH_source_utc':at.isoformat(),'X1X2_source_utc':ot.isoformat(),
                 'cross_market_quote_skew_hours':round(skew,8),
                 'min_profit_unit_stake':round(payoff,8),'theoretical_positive':payoff>1e-8,
                 'snapshot_sha256':r['snapshot_sha256'],
                 'not_proven_executable':True,'odds_AH':[line,*prices],'odds_1X2':list(prices1),
                 'LP_stakes_AH_home_away_1X2_home_draw_away':[round(x,8) for x in stakes]}
            allrows.append(row);seen.add(row['fid'])
            z='within_5m' if skew<=5/60 else '5m_30m' if skew<=0.5 else '30m_6h' if skew<=6 else '6h_24h' if skew<=24 else 'over_24h'
            bins[(z,'positive' if payoff>1e-8 else 'nonpositive')]+=1
            quality['valid']+=1
            if payoff>1e-8 and len(examples)<15:examples.append(row)
        except Exception as e:quality['error_'+type(e).__name__]+=1
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'actual_MR1_cross_contract_per_snapshot.jsonl').open('w') as f:
        for row in allrows:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
    summary={'source':'MR1 actual verified pregame Crown snapshot AH+1X2, exact same FID receipt','quality':dict(quality),
             'valid_quote_snapshot_rows':len(allrows),'unique_fids':len(seen),
             'theoretical_positive_rows':sum(x['theoretical_positive'] for x in allrows),
             'skew_counts':{f'{a}|{b}':n for (a,b),n in sorted(bins.items())},
             'examples':examples,
             'interpretation':'Positive LP on saved quotes is theoretical and not proof of simultaneously accepted live stakes, or actual profit. Snapshot is not a trading order.'}
    (OUT/'actual_MR1_cross_contract_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='examples'},ensure_ascii=False))
if __name__=='__main__':main()
