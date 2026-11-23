#!/usr/bin/env python3
"""R8-A retrospective study of truly HTTP-received Crown AH/OU time sequence.
Reads original archived receipts + separately verified FT for same match.
Keep quote-receipt time distinct from source-event time; no FT in market fitting.
Domestic club leagues represented by R5 actual old cohort (11), not national teams.
All research output separate from R5/R6/R7 frozen artifacts or production orders.
"""
import json,hashlib,math,datetime
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from scipy.optimize import brentq
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r8_market_timing_bayes_20261123'
ARCH=ROOT/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
FT=ROOT/'m7/m7_full_scope_8_axis_combo_pending_FT_recovered_20261110.jsonl'
R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research/r5_bayes_bivar_actual_receipt_20261123.jsonl'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123/r7_market_implied_2market_20261123.jsonl'
OUT=HERE/'r8_11club_Crown_actual_receipt_market_timing.jsonl'
SUMMARY=HERE/'r8_11club_Crown_actual_receipt_market_timing_summary.json'
CLUB_IDS=set()
r5receipt=defaultdict(dict)
for ln in R5.open():
    r=json.loads(ln);CLUB_IDS.add(r['league_id'])
    r5receipt[r['fid']][r['market']]=r
assert len(CLUB_IDS)==11,len(CLUB_IDS)
BIG5={'1','14','16','12','25'}
assert BIG5.issubset(CLUB_IDS)
score_idx={}
for ln in FT.open():
    r=json.loads(ln)
    if r['fixture_id'] in score_idx:raise RuntimeError('duplicate independently verified FT score')
    score_idx[r['fixture_id']]=r
def dt(x):return datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
I=np.arange(19,dtype=float);H=I[:,None];A=I[None,:]
DIFF=H-A
def legs(x):
    n=round(x*4)
    if abs(n/4-x)>1e-8:raise ValueError(x)
    return [(x,1.)] if n%2==0 else [(math.floor(x*2)/2.,.5),(math.ceil(x*2)/2.,.5)]
def pois(x):
    z=np.empty(19);z[0]=math.exp(-x)
    for i in range(1,19):z[i]=z[i-1]*x/i
    return z/z.sum()
def market_moments(ah,ou):
    if any(float(p)<=1 or not math.isfinite(float(p)) for m in (ah,ou) for p in m['odds'].values()):
        return None,'invalid_odds'
    def outot(t):
        z=np.zeros(42);z[0]=math.exp(-t)
        for k in range(1,len(z)):z[k]=z[k-1]*t/k
        z/=z.sum()
        indexes=np.arange(len(z))
        win=loss=0.
        for leg,w in legs(float(ou['line'])):
            win+=w*float(z[indexes>leg+1e-9].sum())
            loss+=w*float(z[indexes<leg-1e-9].sum())
        return ou['odds']['over']*win-ou['odds']['under']*loss
    if outot(.05)*outot(12)>=0:return None,'OU_no_identified_root'
    total=brentq(outot,.05,12,xtol=1e-8)
    def ahfunc(frac):
        dist=np.outer(pois(total*frac),pois(total*(1-frac)))
        win=loss=0.
        for leg,w in legs(float(ah['line'])):
            win+=w*float(dist[DIFF+leg>1e-9].sum())
            loss+=w*float(dist[DIFF+leg< -1e-9].sum())
        return ah['odds']['home']*win-ah['odds']['away']*loss
    if ahfunc(.003)*ahfunc(.997)>=0:return None,'AH_no_identified_root'
    share=brentq(ahfunc,.003,.997,xtol=1e-8)
    lh=share*total;la=(1-share)*total
    p=np.outer(pois(lh),pois(la))
    return {'lambda_home':lh,'lambda_away':la,'lambda_total':total,
        '1X2_probs':[float(p[DIFF>0].sum()),float(p[DIFF==0].sum()),float(p[DIFF<0].sum())]},None
def measures(prob,score):
    h,a=map(int,score.split('-'))
    target=0 if h>a else 1 if h==a else 2
    return {'1X2_Brier':sum((pr-float(j==target))**2 for j,pr in enumerate(prob)),
      '1X2_logloss':-math.log(max(prob[target],1e-15))}
archived=defaultdict(list);audit=Counter();names={}
for ln in ARCH.open():
    r=json.loads(ln);audit['all_crown_receipt_rows']+=1
    lg=r['league_id']
    if lg not in CLUB_IDS:
        audit['outside_11_domestic_club_leagues']+=1;continue
    names[lg]=r['league']
    try:
        receipt=dt(r['received_utc']);kickoff=dt(r['kickoff_utc'])
    except Exception:
        audit['time_parse_error']+=1;continue
    if not receipt<kickoff:
        audit['not_before_kickoff']+=1;continue
    if set(r['markets'])!={'AH','OU'}:
        audit['market_pair_incomplete']+=1;continue
    score=score_idx.get(r['fixture_id'])
    if score is None or not score.get('verified_FT_score'):
        audit['FT_unavailable']+=1;continue
    if dt(score['kickoff_utc'])!=kickoff:
        audit['kickoff_inconsistent_with_verified_FT']+=1;continue
    try:
        model,msg=market_moments(r['markets']['AH'],r['markets']['OU'])
    except Exception as exc:
        audit['market_solver_error']+=1
        continue
    if not model:
        audit['market_'+msg]+=1
        continue
    source_times={}
    for m in ('AH','OU'):
        t=dt(r['markets'][m]['source_event_utc'])
        source_times[m]=t.isoformat()
        if t>receipt:audit['source_event_after_HTTP_receipt']+=1
    row={'fid':r['fixture_id'],'league_id':lg,'league':r['league'],
      'month':kickoff.strftime('%Y-%m'),'kickoff_utc':kickoff.isoformat(),
      'score':score['verified_FT_score'],
      'HTTP_received_utc':receipt.isoformat(),'source_snapshot_horizon':r['snapshot_horizon'],
      'minutes_before_kickoff':(kickoff-receipt).total_seconds()/60,
      'AH_quote_source_event_utc':source_times['AH'],'OU_quote_source_event_utc':source_times['OU'],
      'AH_quote_age_hours':(receipt-dt(source_times['AH'])).total_seconds()/3600,
      'OU_quote_age_hours':(receipt-dt(source_times['OU'])).total_seconds()/3600,
      'raw_SHA256':r['raw_sha256'],'snapshot_SHA256':r['snapshot_sha256'],
      'AH':r['markets']['AH'],'OU':r['markets']['OU'],
      'market':model,**measures(model['1X2_probs'],score['verified_FT_score'])}
    archived[r['fixture_id']].append(row)
    audit['fit_successful_received_club_snapshots']+=1
def quote_state(row):
    return ((float(row['AH']['line']),tuple(sorted(row['AH']['odds'].items()))),
            (float(row['OU']['line']),tuple(sorted(row['OU']['odds'].items()))))
fixtures=[];r5miss=Counter()
for fid,snapshots in archived.items():
    s=sorted(snapshots,key=lambda r:r['HTTP_received_utc'])
    # Retain every actual receipt, including duplicates, for source age,
    # but ensure strictly later receipts are a separate observational state.
    statechange=[i for i in range(1,len(s)) if quote_state(s[i])!=quote_state(s[i-1])]
    u={v['raw_SHA256'] for v in s}
    first,last=s[0],s[-1]
    pair={
        'fid':fid,'league_id':first['league_id'],'league':first['league'],
        'month':first['month'],'score':first['score'],
        'source_cohort':'Actual Crown HTTP receipts archived as snapshots before kickoff; result verified independently; posthoc R8',
        'snapshots':s,
        'snapshot_count':len(s),'unique_raw_SHA':len(u),
        'unique_AH_OU_quote_states':len(set(map(quote_state,s))),
        'num_changed_successive_quote_states':len(statechange),
        'first_Brier':first['1X2_Brier'],'last_Brier':last['1X2_Brier'],
        'last_minus_first_Brier':last['1X2_Brier']-first['1X2_Brier'],
        'first_hours_to_kickoff':first['minutes_before_kickoff']/60,
        'last_hours_to_kickoff':last['minutes_before_kickoff']/60,
        'first_AH_event_age_hours':first['AH_quote_age_hours'],
        'first_OU_event_age_hours':first['OU_quote_age_hours'],
        'last_AH_event_age_hours':last['AH_quote_age_hours'],
        'last_OU_event_age_hours':last['OU_quote_age_hours'],
        'AH_line_delta_last_minus_first':float(last['AH']['line'])-float(first['AH']['line']),
        'OU_line_delta_last_minus_first':float(last['OU']['line'])-float(first['OU']['line']),
        'market_lambda_total_delta_last_minus_first':last['market']['lambda_total']-first['market']['lambda_total'],
        'market_lambda_home_delta_last_minus_first':last['market']['lambda_home']-first['market']['lambda_home']}
    six=[r for r in s if r['minutes_before_kickoff']>=360]
    if six:
        pair['T6plus_earliest']=six[0]['1X2_Brier']
        pair['T6plus_latest']=six[-1]['1X2_Brier']
        pair['T6plus_received_count']=len(six)
        pair['T6plus_quote_changes']=sum(quote_state(six[i])!=quote_state(six[i-1]) for i in range(1,len(six)))
    if fid in r5receipt:
        old=r5receipt[fid]
        matches=[q for q in s if
            q['HTTP_received_utc']==dt(old['AH']['Crown_quote_received_utc']).isoformat() and
            q['raw_SHA256']==old['AH']['source_Crown_raw_sha256']]
        pair['R5_old_2026_sample']=True
        pair['R5_exact_original_snapshot_matched']=len(matches)==1
        if len(matches)!=1:r5miss['old_R5_exact_match_missing_or_duplicate']+=1
    else:pair['R5_old_2026_sample']=False
    fixtures.append(pair)
assert len(fixtures)>0
def agg(rows):
    n=len(rows)
    changed=[r for r in rows if r['num_changed_successive_quote_states']>0]
    paired=[r for r in rows if r['snapshot_count']>=2]
    early=[r for r in rows if r.get('T6plus_received_count',0)>=2]
    def mean(rs,key):return round(sum(r[key] for r in rs)/len(rs),7) if rs else None
    return {'fixtures':n,'snapshot_rows':sum(r['snapshot_count'] for r in rows),
        'two_plus_received_fixtures':len(paired),'changed_quote_fixtures':len(changed),
        'pct_changed_quotes':round(100*len(changed)/n,3) if n else None,
        'first_Brier':mean(rows,'first_Brier'),'last_Brier':mean(rows,'last_Brier'),
        'paired_latest_minus_first_Brier':mean(paired,'last_minus_first_Brier'),
        'last_improved':sum(r['last_minus_first_Brier']< -1e-10 for r in paired),
        'last_worsened':sum(r['last_minus_first_Brier']>1e-10 for r in paired),
        'unchanged':sum(abs(r['last_minus_first_Brier'])<=1e-10 for r in paired),
        'T6plus_at_least_two_receipts':len(early),
        'T6plus_earliest_Brier':mean(early,'T6plus_earliest'),
        'T6plus_latest_Brier':mean(early,'T6plus_latest'),
        'T6plus_quote_changes_fixtures':sum(r['T6plus_quote_changes']>0 for r in early),
        'first_AH_age_hours':mean(rows,'first_AH_event_age_hours'),
        'first_OU_age_hours':mean(rows,'first_OU_event_age_hours'),
        'last_AH_age_hours':mean(rows,'last_AH_event_age_hours'),
        'last_OU_age_hours':mean(rows,'last_OU_event_age_hours')}
groups={
  'all_11_domestic_club_leagues':fixtures,
  'five_big_domestic_club_leagues':[r for r in fixtures if r['league_id'] in BIG5],
  'R5_old_2026_receipt_fixture_cohort':[r for r in fixtures if r['R5_old_2026_sample']],
  'R5_old_2026_five_big_only':[r for r in fixtures if r['R5_old_2026_sample'] and r['league_id'] in BIG5]}
summary={'study':'R8_ACTUAL_RECEIVED_CROWN_MARKET_PRICE_TIME_SERIES',
  'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ARCH,FT,R5,R7)},
  'source_club_league_ids':sorted(CLUB_IDS),'source_league_names':names,
  'historical_R7_market_predictions_not_used_for_training':'only independent actual Crown AH+OU quote-based market moments per receipt',
  'sample':{name:agg(z) for name,z in groups.items()},
  'by_horizon':{h:agg([r for r in fixtures if any(s['source_snapshot_horizon']==h for s in r['snapshots'])]) for h in
    ('T48','T36','T24','T18','T12','T6','T3','T1','T0.5')},
  'by_month':{mon:agg([r for r in fixtures if r['month']==mon]) for mon in sorted({r['month'] for r in fixtures})},
  'audit':dict(audit),'R5_receipt_exact_source_match_audit':dict(r5miss),
  'limitations':['Eleven domestic club leagues from prior R5 old real-HTTP study, not just five; five-big-league subcohort reported independently. No national teams.',
   'M8 archive development and locked evaluation labels retained in source, but R8 research occurs after known results; NOT blind forward real orders.',
   'Crown source-event age differs from actual HTTP received time; repeated stale quotes are NOT new independent price updates.',
   'Earliest/latest compares different time-to-kickoff, not proof of ability to trade at all times or of arbitrage.',
   'Market implied scores assume one joint independent-Poisson match score distribution for both AH and OU at each HTTP receipt.',
   'FT from archived verified results; no future FT used to estimate market score distribution.',
   'T6plus is a descriptive analysis of user-practical timing; NOT a new trade eligibility Gate.',
   'No model ROI or EV/threshold tuned, no national teams, no formal Telegram messages.']}
with OUT.open('w') as fd:
    for r in sorted(fixtures,key=lambda x:x['fid']):fd.write(json.dumps(r,ensure_ascii=False)+'\n')
SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'summary':summary['sample'],'audit':dict(audit),'R5match':dict(r5miss)},ensure_ascii=False))
