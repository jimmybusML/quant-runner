#!/usr/bin/env python3
"""M8 A-D exploratory replay using frozen Crown history and verified receipts.

All classifiers are research diagnostics. No production rule is changed.
"""
import json, math, collections, datetime, hashlib, statistics
from pathlib import Path
from scipy.spatial import cKDTree
import numpy as np

ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=Path(__file__).resolve().parent
FEATURES=ROOT/'m8_late_full_path_water_features_20261114.jsonl'
FOUNDATION=ROOT/'m8_foundation_20261115/historical_membership.jsonl'
OLD_SCHEDULE=ROOT/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
NEW_SCHEDULE=ROOT/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl'
RECEIPTS=ROOT/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
COVERAGE=ROOT/'m8_independent_receipt_coverage_20261115.jsonl'
SNAPSHOT_INDEX=Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23/snapshot-index.jsonl')
OUT=HERE/'m8_batch_ad_orders_20261118.jsonl'
SUMMARY=HERE/'m8_batch_ad_results_20261118.json'

def readj(path): return [json.loads(s) for s in path.open()]
foundation=readj(FOUNDATION); foundation_ids={str(r['fid']) for r in foundation}
hist=readj(FEATURES)
base_by_id={str(r['fid']):r for r in foundation}
kickoffs={}
for p in (OLD_SCHEDULE,NEW_SCHEDULE):
    for r in readj(p):
        fid=str(r.get('fixture_id',r.get('fid')))
        ko=r.get('kickoff_utc') or r.get('start')
        if ko: kickoffs[fid]=ko.replace('Z','+00:00')

def decprob(h,a):
    ih,ia=1/h,1/a
    return ih/(ih+ia)
def settle(line,side,hg,ag,odds):
    """AH 1U settlement with quarter-line split and home-perspective line."""
    if abs(line*4-round(line*4))>1e-7: raise ValueError(line)
    # Quarter handicap is two half-stake bets on adjacent half-lines.
    if int(round(line*4))%2:
        low=math.floor(line*2)/2
        lines=[low,low+0.5]
    else: lines=[line,line]
    pnl=0.0
    for ln in lines:
        adj=(hg-ag+ln)*(1 if side=='home' else -1)
        if adj>1e-9: pnl += (odds-1)/2
        elif adj < -1e-9: pnl -= 0.5
    return round(pnl,6)
def favside(line,hp,ap):
    if line<0:return 'home'
    if line>0:return 'away'
    return 'home' if hp<=ap else 'away'
def order(fid,date,signal,method,line,hp,ap,side,pnl,source,overlap,extra=None):
    d={'fid':str(fid),'date':date,'kickoff_utc':kickoffs.get(str(fid)),'signal_time_utc':signal,'method':method,
       'line_home':line,'odds_home':hp,'odds_away':ap,'side':side,'pnl_u':round(float(pnl),6),
       'source_type':source,'foundation_overlap':bool(overlap)}
    if extra:d.update(extra)
    return d

def metrics(rows):
    n=len(rows); net=sum(x['pnl_u'] for x in rows)
    days=collections.defaultdict(float); weeks=collections.Counter(); outcomes=collections.Counter()
    for r in rows:
        days[r['date']]+=r['pnl_u']; iso=datetime.date.fromisoformat(r['date']).isocalendar(); weeks[f'{iso.year}-W{iso.week:02}']+=1
        outcomes['win' if r['pnl_u']>1e-8 else 'loss' if r['pnl_u'] < -1e-8 else 'push']+=1
    peak=trough=0.;mdd=0.
    for day in sorted(days):
        trough+=days[day];peak=max(peak,trough);mdd=max(mdd,peak-trough)
    return {'n':n,'U':round(net,3),'ROI_pct':round(100*net/n,4) if n else None,
            'active_weeks':len(weeks),'orders_per_active_week':round(n/len(weeks),3) if weeks else None,
            'daily_MDD_U':round(mdd,3),'win_loss_push':dict(outcomes)}
def byyear(rows):
    return {str(y):metrics([r for r in rows if int(r['date'][:4])==y]) for y in (2024,2025,2026)}
def baseline(rows,key):
    return metrics([{'date':r['date'],'pnl_u':r[key]} for r in rows if r.get(key) is not None])

# A: Continuous geometry of line and price movement. For each target year, a
# nearest-neighbour surface is fitted only on earlier years. The 3 continuous
# coordinates are favorite-relative line displacement, de-vig side-probability
# displacement, and line displacement x probability displacement. k=200 is a
# recorded exploratory parameter; every target is scored, then union overlap is
# assessed only after predictions have been made.
usable=[r for r in hist if r.get('end_line') is not None and r.get('home_price') and r.get('away_price')]
valid=[r for r in usable if r['year']>=2024]
features={}
for r in usable:
    s=-1 if r['end_line']<0 else 1
    p0=decprob(r['start_home_price'],r['start_away_price']);p1=decprob(r['home_price'],r['away_price'])
    line_move=(r['end_line']-r['start_line'])*s
    prob_move=(p1-p0)*s
    features[str(r['fid'])]=np.array([line_move,prob_move,line_move*prob_move],dtype=float)
orders=[]; arows=[]; a_metrics={}
for year in (2024,2025,2026):
    tr=[r for r in usable if r['year']<year and str(r['fid']) in features]
    te=[r for r in valid if r['year']==year and str(r['fid']) in features]
    X=np.stack([features[str(r['fid'])] for r in tr]); mu=X.mean(0); sd=X.std(0);sd[sd<1e-9]=1.
    tree=cKDTree((X-mu)/sd); k=min(200,len(tr))
    batch=[]
    for r in te:
        fid=str(r['fid']); dist,idx=tree.query((features[fid]-mu)/sd,k=k)
        if k==1:idx=[int(idx)]
        near=[tr[int(i)] for i in idx]
        home=sum(x['end_home_U'] for x in near)/len(near);away=sum(x['end_away_U'] for x in near)/len(near)
        side='home' if home>=away else 'away';pnl=r['end_home_U'] if side=='home' else r['end_away_U']
        date=r['date']; ko=kickoffs.get(fid)
        signal=(datetime.datetime.fromisoformat(ko)-datetime.timedelta(hours=1)).isoformat() if ko else None
        row=order(fid,date,signal,
                 'A_continuous_geometry_knn200',r['end_line'],r['home_price'],r['away_price'],side,pnl,
                 'historical_event_replay',fid in foundation_ids,{'training_years':[x for x in range(2019,year)],'neighbor_k':k,'neighbor_avg_home_u':round(home,6),'neighbor_avg_away_u':round(away,6),'distance_mean':round(float(np.mean(dist)),6),
                 'favorite_baseline_pnl_u':r.get('end_fav_U'),'underdog_baseline_pnl_u':r.get('end_dog_U')})
        batch.append(row)
    arows.extend(batch);orders.extend(batch)
    non=[x for x in batch if not x['foundation_overlap']]
    a_metrics[str(year)]={'train_n':len(tr),'target_n':len(te),'all':metrics(batch),'outside_frozen_eight':metrics(non),
                          'outside_eight_favorite_baseline':baseline(non,'favorite_baseline_pnl_u'),'outside_eight_underdog_baseline':baseline(non,'underdog_baseline_pnl_u')}

# D: Explicit transition-state hypotheses on the complete T6-T1 Crown path.
# The state uses whole-path shape and event/line-change count, not R33's
# discrete 6/3/1 two-segment classifier. Trend states follow the closing
# favorite; reverted/oscillating states fade it; unchanged states are reported
# as favorite baseline. This is a diagnostic, not a gate.
drows=[]; dgroups=collections.defaultdict(list)
for r in valid:
    shape=r.get('path_shape','unknown'); nlc=int(r.get('n_line_changes') or 0)
    if shape=='one_way': state='sustained_one_way'
    elif shape=='reverted': state='line_return_to_open'
    elif shape=='oscillating': state='multi_reversal'
    elif nlc==0: state='static'
    else: state='mixed_transition'
    fav=favside(r['end_line'],r['home_price'],r['away_price'])
    side=fav if state in ('sustained_one_way','static','mixed_transition') else ('away' if fav=='home' else 'home')
    pnl=r['end_home_U'] if side=='home' else r['end_away_U']
    ko=kickoffs.get(str(r['fid'])); signal=(datetime.datetime.fromisoformat(ko)-datetime.timedelta(hours=1)).isoformat() if ko else None
    row=order(r['fid'],r['date'],signal,'D_path_transition_state',r['end_line'],r['home_price'],r['away_price'],side,pnl,
              'historical_event_replay',str(r['fid']) in foundation_ids,{'state':state,'path_shape':shape,'line_change_events':nlc,'events_seen':r.get('n_events'),'last_event_age_min':r.get('late_event_age_min'),'last_line_change_age_min':r.get('last_line_change_age_min'),
              'favorite_baseline_pnl_u':r.get('end_fav_U'),'underdog_baseline_pnl_u':r.get('end_dog_U')})
    drows.append(row); dgroups[state].append(row)
    if r['year']>=2024: orders.append(row)

# B: Actual receipt freshness and update-lag diagnostics. Join the already
# SHA-verified archive to the verified FT/receipt index; only last observed
# receipt per fixture is used as one order. Age and receipt delay are outcomes
# diagnostics, not betting rules.
archive=readj(RECEIPTS); cov=readj(COVERAGE)
covmap={(str(r['fid']),str(r['horizon']),str(r['receipt_utc'])):r for r in cov}
obs=[]
for q in archive:
    key=(str(q['fixture_id']),str(q['snapshot_horizon']),str(q['received_utc']))
    c=covmap.get(key)
    if not c or not c.get('verified_receipt') or not c.get('FT'):continue
    ah=q.get('markets',{}).get('AH')
    if not ah or not all(ah.get('odds',{}).get(s,0)>1 for s in ('home','away')):continue
    obs.append((q,c,ah))
last={}
for q,c,ah in obs:
    fid=str(q['fixture_id'])
    if fid not in last or q['received_utc']>last[fid][0]['received_utc']:last[fid]=(q,c,ah)
brows=[]
for q,c,ah in last.values():
    line=float(ah['line']);hp=float(ah['odds']['home']);ap=float(ah['odds']['away']);side=favside(line,hp,ap)
    hg,ag=c['FT'];pnl=settle(line,side,int(hg),int(ag),hp if side=='home' else ap)
    age=float(ah.get('source_age_minutes_at_actual_receipt') or 0)
    ko=datetime.datetime.fromisoformat(q['kickoff_utc'].replace('Z','+00:00'));rec=datetime.datetime.fromisoformat(q['received_utc'].replace('Z','+00:00'))
    row=order(q['fixture_id'],ko.date().isoformat(),q['received_utc'],'B_actual_receipt_freshness_favorite_diagnostic',line,hp,ap,side,pnl,'actual_http_receipt',str(q['fixture_id']) in foundation_ids,
              {'receipt_horizon':q['snapshot_horizon'],'source_event_utc':ah.get('source_event_utc'),'receipt_utc':q['received_utc'],'quote_age_minutes':age,'received_minutes_to_kickoff':round((ko-rec).total_seconds()/60,3),'raw_sha256':q.get('raw_sha256'),'snapshot_sha256':q.get('snapshot_sha256'),'ft':f'{hg}-{ag}'})
    brows.append(row);orders.append(row)
age_edges=np.quantile([r['quote_age_minutes'] for r in brows],[0,.25,.5,.75,1]).tolist() if brows else []
age_bins=[]
for i in range(4):
    lo,hi=age_edges[i],age_edges[i+1]
    z=[r for r in brows if (lo<=r['quote_age_minutes']<=hi if i==3 else lo<=r['quote_age_minutes']<hi)]
    age_bins.append({'q':i+1,'age_min_max':[round(lo,3),round(hi,3)],'favorite_diag':metrics(z)})

# C: Multi-scale path concordance from all already-audited actual HTTP
# snapshots (not only the single verified T12/FT row per fixture). Join only
# fixtures with independently verified FT. Re-verify each selected row's raw
# response SHA, HTTP received time, snapshot-index SHA, and pre-kickoff time.
verified_ft={str(r['fid']):r for r in cov if r.get('verified_receipt') and r.get('FT')}
snap_idx={}
for r in readj(SNAPSHOT_INDEX):
    snap_idx[(str(r.get('match_id')),str(r.get('target_horizon')),str(r.get('snapshot_sha256')))]=r
verified_paths=collections.defaultdict(list); verify_counts=collections.Counter(); rawcache={}
for q in archive:
    fid=str(q['fixture_id']); c=verified_ft.get(fid)
    if not c: continue
    try:
        path=Path(q['source_file']); attempt=json.loads(path.read_text())
        raw=attempt['raw_response']; actual_sha=hashlib.sha256(raw.encode()).hexdigest()
        if actual_sha!=q['raw_sha256'] or actual_sha!=attempt.get('raw_sha256'):
            verify_counts['raw_sha_mismatch']+=1;continue
        if abs((datetime.datetime.fromisoformat(attempt['received_at'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(q['received_utc'].replace('Z','+00:00'))).total_seconds())>.005:
            verify_counts['receipt_time_mismatch']+=1;continue
        sr=snap_idx.get((fid,str(q['snapshot_horizon']),str(q['snapshot_sha256'])))
        if not sr or sr.get('classification')!='SNAPSHOT_OK': verify_counts['snapshot_index_missing']+=1;continue
        snap_path=Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23')/sr['snapshot_path']
        if hashlib.sha256(snap_path.read_bytes()).hexdigest()!=q['snapshot_sha256']:
            verify_counts['snapshot_sha_mismatch']+=1;continue
        snap=json.loads(snap_path.read_text())
        if abs((datetime.datetime.fromisoformat(snap['received_at'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(q['received_utc'].replace('Z','+00:00'))).total_seconds())>.005:
            verify_counts['snapshot_receive_time_mismatch']+=1;continue
        raw_obj=json.loads(raw); match=next(x for x in raw_obj['data'] if str(x['id'])==fid)
        if str(match.get('l_id'))!=str(q['league_id']): verify_counts['match_identity_mismatch']+=1;continue
        book=next((b for b in match.get('bookmakers',[]) if b.get('slug')=='crown'),None)
        close=(book or {}).get('asian',{}).get('close') or {}
        if not close or abs(float(close.get('line'))-float(q['markets']['AH']['line']))>1e-9 or abs(float(close.get('home'))-float(q['markets']['AH']['odds']['home']))>1e-9 or abs(float(close.get('away'))-float(q['markets']['AH']['odds']['away']))>1e-9:
            verify_counts['crown_quote_mismatch']+=1;continue
        ko=datetime.datetime.fromisoformat(q['kickoff_utc'].replace('Z','+00:00'))
        received=datetime.datetime.fromisoformat(q['received_utc'].replace('Z','+00:00'))
        ah=q['markets']['AH']; source=datetime.datetime.fromisoformat(ah['source_event_utc'].replace('Z','+00:00'))
        if not (received<ko and source<=received and source<ko): verify_counts['not_strictly_pregame']+=1;continue
        verified_paths[fid].append((q,c,ah));verify_counts['verified_path_snapshot']+=1
    except Exception: verify_counts['verification_error']+=1
crows=[]; cpath_counts=collections.Counter()
for fid,seq in verified_paths.items():
    seq.sort(key=lambda x:x[0]['received_utc'])
    # Snapshots are one latest successful receipt per horizon; defensively keep
    # only the latest received quote if duplicate horizon snapshots exist.
    ded=[]; by_h={}
    for x in seq:
        h=x[0]['snapshot_horizon']
        if h not in by_h or x[0]['received_utc']>by_h[h][0]['received_utc']:by_h[h]=x
    ded=sorted(by_h.values(),key=lambda x:x[0]['received_utc'])
    cpath_counts['fixtures_with_receipts']+=1;cpath_counts['verified_receipts']+=len(ded)
    if len(ded)<3: continue
    signals=[]
    for i in range(2,len(ded)):
        prev,mid,cur=ded[i-2],ded[i-1],ded[i]
        l0,l1,l2=[float(x[2]['line']) for x in (prev,mid,cur)]
        # Keep only like-for-like contract paths for this experiment.
        if not (abs(l0-l1)<1e-9 and abs(l1-l2)<1e-9):continue
        def move(x):
            ahx=x[2];return decprob(float(ahx['odds']['home']),float(ahx['odds']['away']))
        d1=move(mid)-move(prev);d2=move(cur)-move(mid)
        if abs(d1)<1e-8 or abs(d2)<1e-8 or d1*d2<0:continue
        signals.append((prev,mid,cur,d1,d2,(l0,l1,l2)))
    if not signals:continue
    prev,mid,cur,d1,d2,(l0,l1,l2)=signals[-1]
    q,c,ah=cur;side='home' if d1+d2>0 else 'away';hg,ag=c['FT'];line=float(ah['line']);hp=float(ah['odds']['home']);ap=float(ah['odds']['away'])
    pnl=settle(line,side,int(hg),int(ag),hp if side=='home' else ap)
    ko=datetime.datetime.fromisoformat(q['kickoff_utc'].replace('Z','+00:00'))
    row=order(fid,ko.date().isoformat(),q['received_utc'],'C_multiscale_concordant_actual_receipt',line,hp,ap,side,pnl,'actual_http_receipt',fid in foundation_ids,
              {'window_receipts':[prev[0]['snapshot_horizon'],mid[0]['snapshot_horizon'],q['snapshot_horizon']],'window_received_utc':[prev[0]['received_utc'],mid[0]['received_utc'],q['received_utc']],'window_receipt_evidence':[{'raw_sha256':z[0]['raw_sha256'],'snapshot_sha256':z[0]['snapshot_sha256']} for z in (prev,mid,cur)],'lines_home':[l0,l1,l2],'same_line_windows':True,'delta1_home_prob':round(d1,8),'delta2_home_prob':round(d2,8),'raw_sha256':q.get('raw_sha256'),'snapshot_sha256':q.get('snapshot_sha256'),'ft':f'{hg}-{ag}','eligible_concordant_windows':len(signals)})
    crows.append(row)
orders.extend(crows)

with OUT.open('w') as f:
    for r in sorted(orders,key=lambda r:(r['method'],r['date'],r['fid'])):f.write(json.dumps(r,ensure_ascii=False)+'\n')

summary={'study':'M8 A-D batch research','input_sha256':{},'coverage':{},'A':{'model':'cKDTree nearest-neighbor expected side return, features=[favorite-relative line delta, favorite-relative de-vig probability delta, interaction], k=200; target-year uses only earlier-year history','by_year':a_metrics},
         'B':{'definition':'one verified actual HTTP Crown AH receipt per fixture from the receipt/FT index; bet favorite only as a price-quality diagnostic, not a learned strategy','rows':len(brows),'summary':metrics(brows),'outside_frozen_eight':metrics([r for r in brows if not r['foundation_overlap']]),'by_year':byyear(brows),'quote_age_quartiles':age_bins},
         'C':{'definition':'for independently FT-verified fixtures, revalidate all actual receipts and follow at most one signal per fixture: at the latest receipt with the two preceding successive same-direction normalized home-probability changes at an identical AH line, bet the moved-to side at that receipt Crown AH price.','verification':dict(verify_counts),'coverage':dict(cpath_counts),'rows':len(crows),'summary':metrics(crows),'by_year':byyear(crows),'outside_frozen_eight':metrics([r for r in crows if not r['foundation_overlap']])},
         'D':{'definition':'whole T6-T1 path state transitions: sustained one-way follows final favorite; reversion/multi-reversal fades final favorite; static/mixed state uses favorite diagnostic. Not R33 phase classes.','aggregate_years':[2024,2025,2026],'states':{k:{'all':metrics(v),'by_year':byyear(v),'outside_frozen_eight':metrics([r for r in v if not r['foundation_overlap']])} for k,v in dgroups.items()}},
         'limitations':['Historical rows are post-hoc Crown event-time replays, not real-time received prices.','The 2026 actual receipt rows were designed from previously observed receipts/outcomes and are retrospective, not frozen forward predictions.','B favorite diagnostics do not establish a profitable selection signal.','C uses normalized two-sided AH odds shares as a movement proxy and requires identical home handicap lines across all three quote events.','C recomputed all snapshots within independently FT-verified fixture IDs and checked raw SHA, receipt time, snapshot-index SHA, snapshot SHA, snapshot receive time, fixture/league identity, Crown line/odds, and that source and receipt times preceded kickoff.','A nearest-neighbor classifier and k=200 are exploratory parameters selected for this experiment; selection bias remains.','D aggregates path-shape states already examined within R33; results are a collapse/recheck of existing path structures, not an independent new mechanism.','D uses available path summaries; exact per-update quote sequence is not retained in this feature cache.']}
for p in (FEATURES,FOUNDATION,OLD_SCHEDULE,NEW_SCHEDULE,RECEIPTS,COVERAGE,SNAPSHOT_INDEX):summary['input_sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
summary['foundation']={'rows':len(foundation),'unique_fid':len(foundation_ids),'sha256':summary['input_sha256'][FOUNDATION.name]}
summary['output']={'orders_jsonl':OUT.name,'rows':len(orders),'historical_A':len(arows),'historical_D':len(drows),'actual_receipt_B':len(brows),'actual_receipt_C':len(crows)}
SUMMARY.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
