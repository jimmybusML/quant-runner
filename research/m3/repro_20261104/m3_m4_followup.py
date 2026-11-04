#!/usr/bin/env python3
"""M3 calibration, MR1/M4 risk drivers; no production mutation."""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
import json,sys,statistics,random,math
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o

def average(vals):
    return sum(vals)/len(vals) if vals else None
def pnl(rows):
    return sum(r['pnl'] for r in rows)
def roundv(x,d=4):
    return round(x,d) if x is not None else None
def parse(x):
    return datetime.fromisoformat(x.replace('Z','+00:00'))
def stats_m3():
    rows=[r for r in o.rows_for('m3') if r['market']=='OU' and r['pnl'] is not None and r['submodel']=='泊松']
    by_id={r['id']:r for r in rows}
    forecast={}
    order_fid={}
    book=Path.home()/'QuantAsiaDesk/repos/runner/research/m3/results/totalcorner/forward_ev_ledger.jsonl'
    for line in book.open():
        e=json.loads(line)
        protocol=e.get('protocol')
        if protocol=='M3_SHADOW_ORDER_V1' and e.get('event_id') in by_id:
            order_fid[e['event_id']]=e.get('forecast_id')
        elif protocol=='M3_TOTALCORNER_FORWARD_FORECAST_V1':
            forecast[e['forecast_id']]=e
    d=[]
    for ident,r in by_id.items():
        f=forecast.get(order_fid.get(ident))
        if not f:continue
        grid=f.get('score_probability_grid')
        if not grid:continue
        s=sum(float(q) for row in grid for q in row)
        if abs(s-1)>.01:continue
        exp=sum((i+j)*float(q) for i,row in enumerate(grid) for j,q in enumerate(row))/s
        actual=r['result']['home']+r['result']['away']
        d.append({**r,'exp':exp,'actual':actual,'error':actual-exp,'day':r['kickoff'][:10],'start':parse(r['kickoff'])})
    d.sort(key=lambda r:(r['start'],r['fixture']))
    print('M3_VALIDITY',len(rows),len(d),len({r['fixture'] for r in d}),len({r['day'] for r in d}))
    daily=[]
    for day in sorted(set(r['day'] for r in d)):
        entries=[r for r in d if r['day']==day]
        tr=[r for r in d if r['day']<day]
        bias=average([r['error'] for r in tr]) if tr else 0
        # Prequential shift requires no same-day outcome access.
        pred=[r['exp'] for r in entries]
        baseline_mse=average([(r['actual']-r['exp'])**2 for r in entries])
        shifted_mse=average([(r['actual']-r['exp']-bias)**2 for r in entries])
        daily.append({'day':day,'n':len(entries),'training_games':len(tr),'historical_bias':roundv(bias),
            'mean_real_error':roundv(average([r['error'] for r in entries])),'base_mse':roundv(baseline_mse),
            'corrected_mse':roundv(shifted_mse),'pnl':roundv(pnl(entries))})
    print('M3_DAILY_PREQUENTIAL',json.dumps(daily,ensure_ascii=False))
    predrows=[r for r in d if any(day['day']==r['day'] and day['training_games']>0 for day in daily)]
    shifts={day['day']:day['historical_bias'] for day in daily}
    m0=average([r['error']**2 for r in predrows])
    m1=average([(r['error']-shifts[r['day']])**2 for r in predrows])
    mae0=average([abs(r['error']) for r in predrows])
    mae1=average([abs(r['error']-shifts[r['day']]) for r in predrows])
    print('M3_WALK_FORWARD_GOAL_MEAN',{'n':len(predrows),'base_mse':roundv(m0),'corrected_mse':roundv(m1),'base_mae':roundv(mae0),'corrected_mae':roundv(mae1),
        'change_mse':roundv(m0-m1),'change_mae':roundv(mae0-mae1)})
    groups=[]
    for league in sorted(set(r['league'] for r in d)):
        g=[r for r in d if r['league']==league]
        groups.append({'league':league,'n':len(g),'mean_bias':roundv(average([r['error'] for r in g])),
           'under_selected':sum(r['direction']=='小球' for r in g),'ou_pnl':roundv(pnl(g)),
           'distinct_matches':len({r['fixture'] for r in g})})
    print('M3_LEAGUE_GOAL_BIAS',json.dumps(sorted(groups,key=lambda x:x['ou_pnl'])[:22],ensure_ascii=False))
    print('M3_LEAGUE_WINNERS',json.dumps(sorted(groups,key=lambda x:x['ou_pnl'],reverse=True)[:12],ensure_ascii=False))
    # Pre-declared no-legit training group filter; check if bias mostly driven by high-scoring outliers.
    for maxgoal in (4,5,6):
        subset=[r for r in d if r['actual']<=maxgoal]
        print('M3_GOAL_TAIL_CUTOFF_DIAGNOSTIC',maxgoal,'retained',len(subset),'bias',roundv(average([r['error'] for r in subset])))
    rng=random.Random(20261104)
    days=sorted({r['day'] for r in d})
    day_map={day:[r for r in d if r['day']==day] for day in days}
    b=[]
    for i in range(1200):
        sampled=[r for _ in days for r in day_map[rng.choice(days)]]
        b.append(average([r['error'] for r in sampled]))
    b.sort()
    print('M3_DAY_CLUSTER_BOOTSTRAP_MEAN_BIAS',roundv(average([r['error'] for r in d])),roundv(b[30]),roundv(b[1170]))
    return d
def stats_m4():
    rows=[r for r in o.rows_for('mr1') if r['pnl'] is not None]
    groups=defaultdict(list)
    for r in rows:groups[r['league']].append(r)
    leagues=['Japan J-League','Poland Ekstraklasa','Türkiye Super Lig','England Championship','France Ligue 1','Sweden Allsvenskan','Denmark Division 1','South Korea K League 1','Colombia Primera A']
    print('M4_TOTAL',len(rows),'MATCHES',len({r['fixture'] for r in rows}), 'PNL',roundv(pnl(rows)))
    # By genuine same-game exposures; count matches, don't say each order independent.
    repeats=defaultdict(list)
    for r in rows:repeats[r['fixture']].append(r)
    multip=[g for g in repeats.values() if len(g)>1]
    sing=[g for g in repeats.values() if len(g)==1]
    print('M4_SAME_GAME_RISK',json.dumps({'multi_matches':len(multip),'multi_orders':sum(map(len,multip)),'multi_pnl':roundv(sum(pnl(g) for g in multip)),
       'single_matches':len(sing),'single_orders':len(sing),'single_pnl':roundv(sum(pnl(g) for g in sing)),
       'top_worst_same_match':sorted([{'league':g[0]['league'],'fixture':g[0]['fixture'],'count':len(g),'pnl':roundv(pnl(g))} for g in repeats.values()],key=lambda x:x['pnl'])[:15]},ensure_ascii=False))
    # League and quote age, within league: report exact hours, not impose Gate.
    rng=random.Random(20261104)
    for l in leagues:
        g=groups[l]
        if not g:continue
        m=defaultdict(list)
        for r in g:m[r['fixture']].append(r)
        bydir=defaultdict(list)
        for r in g:bydir[r['direction']].append(r)
        ages=[]
        for r in g:
            try:age=(parse(r['posted_at'])-parse(r['quote_at'])).total_seconds()/60
            except Exception:age=None
            ages.append(age)
        valid=[v for v in ages if v is not None]
        # Clustered bootstrap of mean U per ORDER from resampled independent matches
        matches=list(m.values());vals=[]
        for i in range(1600):
            pick=[matches[rng.randrange(len(matches))] for _ in matches]
            vals.append(sum(pnl(x) for x in pick)/sum(len(x) for x in pick))
        vals.sort()
        quote60=[r for r,age in zip(g,ages) if age is not None and age>=60]
        short=[r for r,age in zip(g,ages) if age is not None and age<60]
        print('M4_LEAGUE_MATCH_BOOT',json.dumps({
          'league':l,'orders':len(g),'matches':len(matches),'pnl':roundv(pnl(g)),
          'mean_roi_pct':roundv(100*pnl(g)/len(g),2),'bootstrap_roi_95': [roundv(100*vals[40],2),roundv(100*vals[1560],2)],
          'sides':{k:[len(v),roundv(pnl(v))] for k,v in bydir.items()},
          'quote_age_median_min':roundv(statistics.median(valid)) if valid else None,
          'old_quote_60m':[len(quote60),roundv(pnl(quote60))],
          'young_quote_60m':[len(short),roundv(pnl(short))],
          'first_last_sent':[min(r['posted_at'] for r in g)[:10],max(r['posted_at'] for r in g)[:10]]
          },ensure_ascii=False))
    # Time-non-leaky sign heuristic: evaluate after accumulated earlier matches ONLY,
    # no front-loaded cherry-picking: show how a global league reversal behaves over time with actual fees.
    for league in leagues[:5]:
        g=sorted(groups[league],key=lambda x:x['posted_at'])
        cut=len(g)//2
        front=pnl(g[:cut]);back=pnl(g[cut:])
        print('M4_HALF_SPLIT_NOT_MODEL',league,len(g),roundv(front),roundv(back))
    return rows
if __name__=='__main__':
    stats_m3();stats_m4()
