#!/usr/bin/env python3
"""R9-A: detect actual new Crown price information versus stale HTTP re-receipt.
Read ONLY frozen R8 468 verified domestic-club fixtures, each real pre-kickoff.
Observe price updates; never infer 'market movement' from receipt count.
No official betting strategy, no ROI-based Gate.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,datetime,math
import numpy as np
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r9_crown_event_update_bayes_20261123'
SRC=ROOT/'frozen_research_snapshots/R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123/r8_11club_Crown_actual_receipt_market_timing.jsonl'
LEDGER=HERE/'r9_crown_true_source_event_transition_ledger.jsonl'
OUT=HERE/'r9_crown_true_source_event_transition_summary.json'
Z=[json.loads(s) for s in SRC.open()]
assert len(Z)==468
BIG5={'1','12','14','16','25'}
def stamp(x):
    return datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
def quote(s,m):
    return (round(float(s[m]['line']),8),tuple(sorted((key,round(float(v),8)) for key,v in s[m]['odds'].items())))
def sha(x):return hashlib.sha256(x.read_bytes()).hexdigest()
fixed_rng=np.random.default_rng(20261123)
output=[];audit=Counter()
for r in Z:
    s=r['snapshots']
    assert len(s)>=2
    assert all(stamp(s[i]['HTTP_received_utc'])<=stamp(s[i+1]['HTTP_received_utc']) for i in range(len(s)-1))
    all_transitions=[]
    for j in range(1,len(s)):
        prev,curr=s[j-1],s[j]
        meta={}
        delta=curr['1X2_Brier']-prev['1X2_Brier']
        for m in ('AH','OU'):
            same=quote(prev,m)==quote(curr,m)
            t0=stamp(prev[m+'_quote_source_event_utc'])
            t1=stamp(curr[m+'_quote_source_event_utc'])
            meta[m]={'price_changed':not same,
                     'line_changed':float(prev[m]['line'])!=float(curr[m]['line']),
                     'source_event_time_advanced':t1>t0,
                     'source_event_time_regressed':t1<t0,
                     'source_event_clock_delta_minutes':(t1-t0).total_seconds()/60,
                     'quote_age_before_hours':prev[m+'_quote_age_hours'],
                     'quote_age_after_hours':curr[m+'_quote_age_hours']}
        price_changed=any(meta[m]['price_changed'] for m in ('AH','OU'))
        advanced_for_changed=any(meta[m]['price_changed'] and meta[m]['source_event_time_advanced'] for m in ('AH','OU'))
        regressed_for_changed=any(meta[m]['price_changed'] and meta[m]['source_event_time_regressed'] for m in ('AH','OU'))
        any_event_advanced=any(meta[m]['source_event_time_advanced'] for m in ('AH','OU'))
        raw_changed=prev['raw_SHA256']!=curr['raw_SHA256']
        if not price_changed:
            if any_event_advanced:klass='source_timestamp_advance_same_price'
            elif raw_changed:klass='new_raw_response_same_price_no_event_advance'
            else:klass='repeat_identical_quote_and_raw'
        elif advanced_for_changed and not regressed_for_changed:
            klass='price_change_matching_source_event_advance'
        elif regressed_for_changed:
            klass='price_change_with_event_clock_regression'
        else:
            klass='price_change_without_matching_source_event_advance'
        same_market_score=abs(delta)<=1e-12
        if not price_changed and not same_market_score:audit['unchanged_price_different_Brier']+=1
        if price_changed and same_market_score:audit['price_changed_equal_Brier']+=1
        horizon_hours=curr['minutes_before_kickoff']/60
        transition={'from_http_received_utc':prev['HTTP_received_utc'],
            'to_http_received_utc':curr['HTTP_received_utc'],
            'from_snapshot_label':prev['source_snapshot_horizon'],
            'to_snapshot_label':curr['source_snapshot_horizon'],
            'to_hours_before_kickoff':horizon_hours,
            'both_receipts_before_kickoff':prev['minutes_before_kickoff']>0 and curr['minutes_before_kickoff']>0,
            'both_receipts_before_T6':prev['minutes_before_kickoff']>=360 and curr['minutes_before_kickoff']>=360,
            'price_changed':price_changed,'raw_http_sha_changed':raw_changed,
            'AH_and_OU':meta,'state':klass,
            'Brier_before':prev['1X2_Brier'],'Brier_after':curr['1X2_Brier'],
            'Brier_delta_after_minus_before':delta,
            'market_lambda_total_delta':curr['market']['lambda_total']-prev['market']['lambda_total'],
            'market_lambda_home_delta':curr['market']['lambda_home']-prev['market']['lambda_home']}
        all_transitions.append(transition)
        audit['all_transition_observations']+=1
        audit['class_'+klass]+=1
        if price_changed:
            audit['price_changed_transitions']+=1
        if curr['minutes_before_kickoff']>=360:
            audit['T6plus_transitions']+=1
        if any(meta[m]['source_event_time_regressed'] for m in ('AH','OU')):
            audit['any_source_clock_regression']+=1
        if any(meta[m]['source_event_time_advanced'] for m in ('AH','OU')):
            audit['any_source_clock_advance']+=1
    assert abs(sum(t['Brier_delta_after_minus_before'] for t in all_transitions)-r['last_minus_first_Brier'])<=1e-10
    output.append({'fid':r['fid'],'league_id':r['league_id'],'league':r['league'],
       'month':r['month'],'R5_old_2026_sample':r['R5_old_2026_sample'],
       'score':r['score'],'snapshots':r['snapshot_count'],
       'transitions':all_transitions,
       'earliest_Brier':r['first_Brier'],'latest_Brier':r['last_Brier']})
def summaries(g):
    ts=[t for r in g for t in r['transitions']]
    n=len(g)
    by_class=defaultdict(list)
    for t in ts:
        by_class[t['state']].append(t)
    def summarizetrans(z):
        return {'n':len(z),
          'mean_delta_Brier':round(sum(t['Brier_delta_after_minus_before'] for t in z)/len(z),7) if z else None,
          'improved_Brier':sum(t['Brier_delta_after_minus_before']< -1e-12 for t in z),
          'worsened_Brier':sum(t['Brier_delta_after_minus_before']>1e-12 for t in z),
          'unchanged_Brier':sum(abs(t['Brier_delta_after_minus_before'])<=1e-12 for t in z),
          'AH_source_event_advance':sum(t['AH_and_OU']['AH']['source_event_time_advanced'] for t in z),
          'OU_source_event_advance':sum(t['AH_and_OU']['OU']['source_event_time_advanced'] for t in z),
          'quote_changes_at_T6plus':sum(t['price_changed'] and t['both_receipts_before_T6'] for t in z)}
    changed=[t for t in ts if t['price_changed']]
    perfixture=np.array([sum(t['Brier_delta_after_minus_before'] for t in r['transitions'] if t['price_changed']) for r in g])
    # all price updates within fixture are ONE resampling cluster
    resamp=fixed_rng.integers(0,len(g),(5000,len(g))) if g else []
    means=perfixture[resamp].mean(axis=1) if g else np.array([])
    return {'fixtures':n,'transitions':len(ts),
      'quote_update_transition_count':len(changed),
      'quote_update_fixtures':sum(any(t['price_changed'] for t in r['transitions']) for r in g),
      'earliest_Brier':round(sum(r['earliest_Brier'] for r in g)/n,7) if n else None,
      'latest_Brier':round(sum(r['latest_Brier'] for r in g)/n,7) if n else None,
      'per_fixture_net_Brier_delta_due_to_price_updates':round(perfixture.mean(),7) if n else None,
      'per_fixture_bootstrap_95pct_Brier_delta':[round(float(v),7) for v in np.quantile(means,[.025,.975])] if n else None,
      'transitions_by_state':{key:summarizetrans(z) for key,z in sorted(by_class.items())},
      'T6plus_update_transitions':summarizetrans([t for t in ts if t['price_changed'] and t['both_receipts_before_T6']]),
      'after_T6_update_transitions':summarizetrans([t for t in ts if t['price_changed'] and not t['both_receipts_before_T6']])}
groups={'all_11_domestic_club_leagues':Z,
        'big5_club_leagues':[r for r in Z if r['league_id'] in BIG5],
        'R5_old_138':[r for r in Z if r['R5_old_2026_sample']],
        'R5_old_big5_71':[r for r in Z if r['R5_old_2026_sample'] and r['league_id'] in BIG5]}
# Output contains private original fixture-level chronology, locally only.
with LEDGER.open('w') as f:
    for r in output:f.write(json.dumps(r,ensure_ascii=False)+'\n')
res={'study':'R9_ACTUAL_HTTP_CROWN_RECEIPT_VS_SOURCE_EVENT_UPDATE',
     'source_R8_frozen_sha256':sha(SRC),
     'description':'Price change classified per market alongside source_event_utc monotonicity. Raw HTTP SHA alone is NOT treated as a market update. Delta Brier is purely retrospective score outcome.',
     'all':{key:summaries([r for r in output if (key=='all_11_domestic_club_leagues' or
         (key=='big5_club_leagues' and r['league_id'] in BIG5) or
         (key=='R5_old_138' and r['R5_old_2026_sample']) or
         (key=='R5_old_big5_71' and r['R5_old_2026_sample'] and r['league_id'] in BIG5))])
         for key in groups},
     'by_month':{mo:summaries([r for r in output if r['month']==mo]) for mo in sorted({r['month'] for r in output})},
     'audit':dict(audit),
     'limitations':['Only 468 previously researched domestic club fixtures with verified FT and two AH+OU snapshots, not new blind data or 1607 all receipts.',
       'Source-event clock advancement with quoted price change indicates observable market update; it does not establish instantaneous true time of actual executable change.',
       'Non-changed quotes inherently have unchanged market-implied Brier; they cannot be modeled as independent predictions.',
       'Bootstrap clusters at fixture, not snapshot, and is descriptive, not proof of causal information edge.',
       'All national team matches excluded. No betting ROI gate, no official TG, no changes to production logic.']}
OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':res['all']['all_11_domestic_club_leagues'],
       'five_big':res['all']['big5_club_leagues'],
       'audit':dict(audit)},ensure_ascii=False))
