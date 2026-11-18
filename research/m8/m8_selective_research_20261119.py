#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruct A-L raw score ledgers, then evaluate pre-year selective betting.

All source models are executed from their frozen 2026-11-18 scripts with only
output paths redirected. Forecast score reconstruction does not alter targets,
training folds, or frozen foundation membership. Selectivity rules below are
research-only and fit on prior-year model predictions/outcomes.
"""
from __future__ import annotations
import collections, contextlib, datetime as dt, gzip, hashlib, io, json, math, statistics
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
M8=ROOT/'research/m8'
OUT=M8/'selective_research_20261119'
OUT.mkdir(parents=True,exist_ok=True)
SCRIPT_PATHS={
 'AD':M8/'m8_batch_ad_20261118.py',
 'EH':M8/'m8_batch_eh_20261118.py',
 'IL':M8/'m8_batch_il_20261118.py',
}
ORDER_PATHS=[M8/'m8_batch_ad_orders_20261118.jsonl',M8/'m8_batch_eh_orders_20261118.jsonl',M8/'m8_batch_il_orders_20261118.jsonl']
AUDIT_PATH=M8/'m8_batch_actual_receipt_independently_audited_20261118.jsonl'
FOUNDATION=Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')

def readj(path): return [json.loads(s) for s in path.open() if s.strip()]
def run_probe(tag,path,patches):
    source=path.read_text()
    for old,new in patches:
        if old not in source: raise RuntimeError(f'{tag}: expected source fragment missing: {old[:100]!r}')
        source=source.replace(old,new)
    ns={'__file__':str(path),'__name__':f'__m8_selective_{tag.lower()}__'}
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(source,str(path),'exec'),ns,ns)
    return ns

# Re-run each exact model script but redirect its side effects into a disposable
# subdirectory, leaving all original A-L artifacts byte-for-byte untouched.
ad_dir=OUT/'probe_ad';ad_dir.mkdir(exist_ok=True)
ad=run_probe('AD',SCRIPT_PATHS['AD'],[
 ("OUT=HERE/'m8_batch_ad_orders_20261118.jsonl'",f"OUT=HERE/'selective_research_20261119/probe_ad/orders.jsonl'"),
 ("SUMMARY=HERE/'m8_batch_ad_results_20261118.json'",f"SUMMARY=HERE/'selective_research_20261119/probe_ad/summary.json'"),
])
eh_dir=OUT/'probe_eh';eh_dir.mkdir(exist_ok=True)
eh=run_probe('EH',SCRIPT_PATHS['EH'],[
 ("OUT = ROOT / 'research' / 'm8'", "OUT = ROOT / 'research' / 'm8' / 'selective_research_20261119' / 'probe_eh'\nOUT.mkdir(parents=True, exist_ok=True)"),
])
il_dir=OUT/'probe_il';il_dir.mkdir(exist_ok=True)
il=run_probe('IL',SCRIPT_PATHS['IL'],[
 ("OUT = Path(__file__).resolve().parent", "OUT = Path(__file__).resolve().parent / 'selective_research_20261119' / 'probe_il'\nOUT.mkdir(parents=True, exist_ok=True)"),
])

foundation={str(r['fid']):r for r in readj(FOUNDATION)}
original={}
for p in ORDER_PATHS:
    for r in readj(p):
        row=dict(r);row['fid']=str(row['fid'])
        if row.get('source_type')=='actual_http_receipt' and row['method'] in {
          'E_discrete_AH_contract_calibration','F_async_Crown_market_updates','H_team_contract_position_residual'}:
            # Replace with the independent settled result and exact receipt metadata.
            pass
        original[(row['method'],row.get('source_type'),row['fid'])]=row
# Full E/F/H independently audited scores/settlement include T12 and T18 receipts.
audit_by_key={(r['method'],str(r['source_type']) if r.get('source_type') else 'actual_http_receipt',str(r['fid'])):r for r in readj(AUDIT_PATH)}
for key,row in original.items():
    if key[1]=='actual_http_receipt' and key in audit_by_key:
        a=audit_by_key[key];row['pnl_u']=a['audit_pnl_u'];row['received_utc']=a['received_utc'];row['signal_time_utc']=a['received_utc'];row['verified_receipt_horizon']=a['verified_receipt_horizon'];row['ft']=a['ft'];row['FT_source']=a['ft_source'];row['raw_sha256']=a['raw_sha256'];row['snapshot_sha256']=a['snapshot_sha256']

score_rows=[]
def add_score(base, **fields):
    r={k:base.get(k) for k in ('fid','date','kickoff_utc','signal_time_utc','received_utc','verified_receipt_horizon','method','decision_horizon','line_home','odds_home','odds_home_decimal','odds_away','odds_away_decimal','side','pnl_u','source_type','foundation_overlap')}
    r['fid']=str(r['fid']); r['date']=str(r['date'])[:10]
    r['odds_home']=r.get('odds_home') if r.get('odds_home') is not None else r.get('odds_home_decimal')
    r['odds_away']=r.get('odds_away') if r.get('odds_away') is not None else r.get('odds_away_decimal')
    r['line_home']=r.get('line_home')
    r.update(fields);score_rows.append(r)

# A-D scores and non-score diagnostic variables.
# A neighbor variance is computed with one KD-tree per target-year fold.
a_uncertainty={}
for year in (2024,2025,2026):
    tr=[x for x in ad['usable'] if int(x['year'])<year and str(x['fid']) in ad['features']]
    te=[x for x in ad['valid'] if int(x['year'])==year and str(x['fid']) in ad['features']]
    X=np.stack([ad['features'][str(x['fid'])] for x in tr]);mu=X.mean(0);sd=X.std(0);sd[sd<1e-9]=1.
    from scipy.spatial import cKDTree
    tree=cKDTree((X-mu)/sd);k=min(200,len(tr))
    for target in te:
        dist,idx=tree.query((ad['features'][str(target['fid'])]-mu)/sd,k=k)
        if k==1:idx=[int(idx)]
        near=[tr[int(i)] for i in idx]
        hv=np.asarray([float(x['end_home_U']) for x in near]);av=np.asarray([float(x['end_away_U']) for x in near]);dv=hv-av
        a_uncertainty[str(target['fid'])]={'uncertainty_sd_home':float(hv.std(ddof=1)),'uncertainty_sd_away':float(av.std(ddof=1)),'uncertainty_sd_margin':float(dv.std(ddof=1)),'neighbor_se_margin':float(dv.std(ddof=1)/math.sqrt(len(dv)))}
for row in ad['arows']:
    base=original[('A_continuous_geometry_knn200','historical_event_replay',str(row['fid']))]
    add_score(base,score_kind='neighbor_expected_side_pnl',score_home_minus_away=float(row['neighbor_avg_home_u']-row['neighbor_avg_away_u']),predicted_home_return=float(row['neighbor_avg_home_u']),predicted_away_return=float(row['neighbor_avg_away_u']),confidence_abs=float(abs(row['neighbor_avg_home_u']-row['neighbor_avg_away_u'])),**a_uncertainty[str(row['fid'])],neighbor_k=int(row['neighbor_k']),distance_mean=float(row['distance_mean']))
for row in ad['drows']:
    base=original[('D_path_transition_state','historical_event_replay',str(row['fid']))]
    # D has no numeric forecast in A-L; state/action is preserved for separately
    # prior-year empirical calibration, with no target-year outcomes in score.
    add_score(base,score_kind='rule_state_no_raw_probability',path_state=row['state'],path_shape=row['path_shape'],events_seen=row.get('events_seen'),line_change_events=row.get('line_change_events'))
for row in ad['brows']:
    base=original[('B_actual_receipt_freshness_favorite_diagnostic','actual_http_receipt',str(row['fid']))]
    add_score(base,score_kind='no_direction_score_quote_quality_diagnostic',quote_age_minutes=row['quote_age_minutes'],received_minutes_to_kickoff=row.get('received_minutes_to_kickoff'),market_favorite_side=row['side'])
for row in ad['crows']:
    base=original[('C_multiscale_concordant_actual_receipt','actual_http_receipt',str(row['fid']))]
    move=float(row['delta1_home_prob'])+float(row['delta2_home_prob'])
    add_score(base,score_kind='movement_concordance_not_expected_pnl',raw_move_score=move,confidence_abs=float(min(abs(row['delta1_home_prob']),abs(row['delta2_home_prob']))),delta1_home_probability=float(row['delta1_home_prob']),delta2_home_probability=float(row['delta2_home_prob']),same_line_windows=int(row['same_line_windows']),eligible_windows=int(row['eligible_concordant_windows']))

# E/F/G/H base scores from the exact forward-fold arrays in the previous runner.
eh_records=eh['orders']
# Build score arrays keyed by FID from source arrays, never from target realized labels.
EH_ARRAYS={
 'E_discrete_AH_contract_calibration': ('historical',eh['eh'],eh['ea'],eh['pe']),
 'F_async_Crown_market_updates': ('historical',None,None,None),
 'H_team_contract_position_residual': ('historical',None,None,None),
}
Hidx={str(r['fid']):i for i,r in enumerate(eh['H'])};Ridx={str(r['fid']):i for i,r in enumerate(eh['R'])}

def entropy(ps):
    p=np.asarray(ps,dtype=float);return float(-np.sum(np.where(p>0,p*np.log(np.maximum(p,1e-15)),0.0)))
def add_eh_model(name, hist_scores, rec_scores, extra_hist=None, extra_rec=None):
    hs=eh_records[name]
    for row in hs:
        if row.get('source_type')!='historical_event_replay':continue
        i=Hidx[str(row['fid'])];fields=dict(hist_scores(i))
        add_score(original[(name,'historical_event_replay',str(row['fid']))],**fields)
    for row in hs:
        if row.get('source_type')!='actual_http_receipt':continue
        i=Ridx[str(row['fid'])];fields=dict(rec_scores(i))
        add_score(original[(name,'actual_http_receipt',str(row['fid']))],**fields)
# E model predicts 5-state settlement distribution; expose side EVs and entropy.
add_eh_model('E_discrete_AH_contract_calibration',
 lambda i:{'score_kind':'expected_crown_pnl_by_side','predicted_home_return':float(eh['eh'][i]),'predicted_away_return':float(eh['ea'][i]),'score_home_minus_away':float(eh['eh'][i]-eh['ea'][i]),'confidence_abs':float(max(eh['eh'][i],eh['ea'][i])),'settlement_state_probs':[float(x) for x in eh['pe'][i]],'uncertainty_entropy':entropy(eh['pe'][i])},
 lambda i:{'score_kind':'expected_crown_pnl_by_side','predicted_home_return':float(eh['erh'][i]),'predicted_away_return':float(eh['era'][i]),'score_home_minus_away':float(eh['erh'][i]-eh['era'][i]),'confidence_abs':float(max(eh['erh'][i],eh['era'][i])),'settlement_state_probs':[float(x) for x in eh['pr'][i]],'uncertainty_entropy':entropy(eh['pr'][i])})
# F and H are forward Ridge estimates of home-U minus away-U.
for name,hp,rp in [('F_async_Crown_market_updates',eh['fpred'],eh['frpred']),('H_team_contract_position_residual',eh['hpred'],eh['hrpred'])]:
    add_eh_model(name,lambda i,hp=hp:{'score_kind':'ridge_predicted_home_minus_away_return','score_home_minus_away':float(hp[i]),'confidence_abs':float(abs(hp[i]))},lambda i,rp=rp:{'score_kind':'ridge_predicted_home_minus_away_return','score_home_minus_away':float(rp[i]),'confidence_abs':float(abs(rp[i]))})
# G was fit to the earlier-year path history; retain its raw payout-difference forecast.
for row in eh['gorders']:
    base=original[('G_T6_T1_Crown_microstructure_replay','historical_event_replay',str(row['fid']))]
    i=eh['gids'][str(row['fid'])]
    add_score(base,score_kind='ridge_predicted_home_minus_away_return',score_home_minus_away=float(eh['gpred'][i]),confidence_abs=float(abs(eh['gpred'][i])),path_state=row.get('state') or row.get('path_shape'))

# I/K and market-response models return predicted Crown AH PnL on each side.
for name,X,Z in [('market_response',il['X_BASE'],il['Z_BASE']),('I_line_style',il['X_I'],il['Z_I']),('K_path_style',il['X_K'],il['Z_K']),('shot_main_effects',il['X_SHOT'],il['Z_SHOT'])]:
    ht,hf,rt,rf,fits=il['fit_year_forward'](X,Z,name)
    _,_,hev,aev=il['choose_ev'](il['H'],ht,hf);_,_,rhev,raev=il['choose_ev'](il['R'],rt,rf)
    for source,rows,vals_h,vals_a,qindex in [('historical_event_replay',il['H'],hev,aev,il['HY']),('actual_http_receipt',il['R'],rhev,raev,il['RY'])]:
        for i,q in enumerate(rows):
            key=(name,source,str(q['fid']))
            if key not in original:continue
            best=max(float(vals_h[i]),float(vals_a[i]));margin=float(vals_h[i]-vals_a[i])
            add_score(original[key],score_kind='expected_crown_pnl_by_side',predicted_home_return=float(vals_h[i]),predicted_away_return=float(vals_a[i]),score_home_minus_away=margin,predicted_best_side_ev=best,confidence_abs=abs(margin),model_fit_year=int(qindex[i]))

# L depth 2/3 score is a prior-year tree forecast of home-U minus away-U.
for depth in (2,3):
    pred=np.zeros(len(il['H']));rpred=np.zeros(len(il['R']))
    for year in (2024,2025,2026):
        tr=(il['HY']<year)&il['history_ind'];te=il['HY']==year;re=il['RY']==year
        pred[te],_=il['cart_fit_predict'](il['XL'][tr],il['yret'][tr],il['XL'][te],depth,300)
        if re.any():rpred[re],_=il['cart_fit_predict'](il['XL'][tr],il['yret'][tr],il['ZL'][re],depth,300)
    method=f'L_CART_depth{depth}_leaf300'
    for source,rows,scores in [('historical_event_replay',il['H'],pred),('actual_http_receipt',il['R'],rpred)]:
        for i,q in enumerate(rows):
            key=(method,source,str(q['fid']))
            if key in original:
                add_score(original[key],score_kind='cart_predicted_home_minus_away_return',score_home_minus_away=float(scores[i]),confidence_abs=float(abs(scores[i])))

# J time-cutoff trees. T24/T12 history are time-matched; T6/T3/T1 are actual
# receipt migrations of the T12 tree and remain separate analyses.
for hz in ('T24','T12','T6','T3','T1'):
    if hz not in il['actual_by_horizon']:continue
    aq,axj,ashot,aover,arecs=il['actual_by_horizon'][hz]
    Zj=il['feature_L_with_quote'](axj,ashot,aq)
    if hz in ('T24','T12'):
        hq,hxj=il['hist_by_horizon'][hz];Xj=il['feature_L_with_quote'](hxj,il['hs'],hq)
        hp=np.zeros(len(il['H']))
        for yr in (2024,2025,2026):
            tr=(il['HY']<yr)&il['history_ind'];te=il['HY']==yr
            fn,_=il['cart_model'](Xj[tr],np.asarray([float(z['home_U'])-float(z['away_U']) for z in hq])[tr],depth=3,leaf=300)
            hp[te]=fn(Xj[te])
        tr=(il['HY']<2026)&il['history_ind'];fn,_=il['cart_model'](Xj[tr],np.asarray([float(z['home_U'])-float(z['away_U']) for z in hq])[tr],depth=3,leaf=300)
        rp=fn(Zj)
        hist_method=f'J_L_T{hz[1:]}_historical'
        for i,q in enumerate(hq):
            key=(hist_method,'historical_event_replay',str(q['fid']))
            if key in original:add_score(original[key],score_kind='cart_predicted_home_minus_away_return',score_home_minus_away=float(hp[i]),confidence_abs=float(abs(hp[i])),decision_horizon=hz)
    else:
        tr=(il['HY']<2026)&il['history_ind'];target=np.asarray([float(q['home_U'])-float(q['away_U']) for q in il['H']])
        fn,_=il['cart_model'](il['XL'][tr],target[tr],depth=3,leaf=300);rp=fn(Zj)
    method=f'J_L_CART_{hz}'
    for i,q in enumerate(aq):
        key=(method,'actual_http_receipt',str(q['fid']))
        if key in original:add_score(original[key],score_kind='cart_predicted_home_minus_away_return',score_home_minus_away=float(rp[i]),confidence_abs=float(abs(rp[i])),decision_horizon=hz)

# Attach both-side realized Crown AH returns for market-baseline and scoring
# diagnostics. These are labels only; none enters a fold's prediction features.
outcome_maps={}
for source,rows in [('historical_event_replay',ad['usable']),('historical_event_replay',eh['H']),('actual_http_receipt',eh['R']),('historical_event_replay',il['H']),('actual_http_receipt',il['R'])]:
    dest=outcome_maps.setdefault(source,{})
    for q in rows:
        if q.get('home_U') is not None and q.get('away_U') is not None:
            dest[str(q['fid'])]=(float(q['home_U']),float(q['away_U']))
# Horizon-specific I-L rows have their own line and FT but identical fixture score.
for hz,pack in il.get('actual_by_horizon',{}).items():
    dest=outcome_maps.setdefault('actual_http_receipt',{})
    for q in pack[0]:
        if q.get('home_U') is not None and q.get('away_U') is not None:
            dest[str(q['fid'])]=(float(q['home_U']),float(q['away_U']))
# D and G use the late T1 path cache; retain one-side underlying payout labels.
late_by_id={str(r['fid']):r for r in ad['usable']}
for r in eh['G']:
    if r.get('end_home_U') is not None:
        late_by_id[str(r['fid'])]=r
for sr in score_rows:
    source=sr['source_type'];fid=sr['fid'];q=outcome_maps.get(source,{}).get(fid)
    if source=='historical_event_replay' and sr['method'] in {'A_continuous_geometry_knn200','D_path_transition_state','G_T6_T1_Crown_microstructure_replay'}:
        x=late_by_id.get(fid);q=(float(x['end_home_U']),float(x['end_away_U'])) if x else q
    if source=='actual_http_receipt' and sr['method'] in {'B_actual_receipt_freshness_favorite_diagnostic','C_multiscale_concordant_actual_receipt'}:
        x=next((r for r in (ad['brows'] if sr['method'].startswith('B_') else ad['crows']) if str(r['fid'])==fid),None)
        if x:
            q=(ad['settle'](float(x['line_home']),'home',int(x['ft'].split('-')[0]),int(x['ft'].split('-')[1]),float(x['odds_home'])),ad['settle'](float(x['line_home']),'away',int(x['ft'].split('-')[0]),int(x['ft'].split('-')[1]),float(x['odds_away'])))
    if q:
        sr['actual_home_u'],sr['actual_away_u']=q
        oh,oa=float(sr['odds_home']),float(sr['odds_away'])
        sr['market_home_no_vig_prob']=(1/oh)/((1/oh)+(1/oa));sr['market_away_no_vig_prob']=1-sr['market_home_no_vig_prob']
        if float(sr['line_home'])<0:sr['market_favorite_side']='home'
        elif float(sr['line_home'])>0:sr['market_favorite_side']='away'
        else:sr['market_favorite_side']='home' if oh<=oa else 'away'
        sr['market_favorite_odds']=min(oh,oa)
        sr['absolute_ah_line']=abs(float(sr['line_home']))
        if float(sr['line_home'])<0:sr['handicap_favorite']='home'
        elif float(sr['line_home'])>0:sr['handicap_favorite']='away'
        else:sr['handicap_favorite']=sr['market_favorite_side']
        sr['line_bucket']='<0.25' if abs(float(sr['line_home']))<.25 else '0.25-0.75' if abs(float(sr['line_home']))<=.75 else '1.00-1.50' if abs(float(sr['line_home']))<=1.5 else '>1.50'
        sr['favorite_odds_bucket']='<1.60' if min(oh,oa)<1.60 else '1.60-1.90' if min(oh,oa)<1.90 else '1.90-2.30' if min(oh,oa)<2.30 else '>=2.30'

# Full rerun consistency against the committed forced-side rows.
rerun_checks={'AD':{'checked':0,'side_mismatch':0,'pnl_mismatch':0},'EH':{'checked':0,'side_mismatch':0,'pnl_mismatch':0},'IL':{'checked':0,'side_mismatch':0,'pnl_mismatch':0}}
def check_rows(tag,newrows):
    for r in newrows:
        key=(r['method'],r.get('source_type'),str(r['fid']));old=original.get(key)
        if not old:continue
        d=rerun_checks[tag];d['checked']+=1;d['side_mismatch']+=r['side']!=old['side'];d['pnl_mismatch']+=abs(float(r['pnl_u'])-float(old['pnl_u']))>1e-6
check_rows('AD',ad['orders']);check_rows('EH',[r for xs in eh['orders'].values() for r in xs]);check_rows('IL',il['all_rows'])

# Independently validate all actual Crown rows by exact HTTP receipt UTC/horizon,
# Crown line/prices, verified FT, raw-response SHA, snapshot SHA, and AH cashflow.
DATA=Path('/Users/mac/QuantAsiaDesk/research-work')
ARCHIVE=readj(DATA/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
COVERAGE=readj(DATA/'m8_independent_receipt_coverage_20261115.jsonl')
archive_by_time={(str(r['fixture_id']),str(r['received_utc'])):r for r in ARCHIVE}
coverage_by_key={(str(r.get('fid')),str(r.get('horizon')),str(r.get('receipt_utc'))):r for r in COVERAGE}
receipt_audit={'candidate_rows':0,'audited_rows':0,'unique_http_receipts':0,'raw_sha_checks':0,'snapshot_sha_checks':0,'missing_archive_receipt':0,'missing_verified_ft':0,'quote_mismatch':0,'not_pregame':0,'raw_sha_mismatch':0,'snapshot_sha_mismatch':0,'settlement_mismatch':0}
receipt_seen={};
def settle_crown(line,side,hg,ag,odds):
    line=float(line);ticks=round(line*4)
    if abs(line*4-ticks)>1e-8:raise ValueError(f'invalid Crown AH line {line}')
    legs=[math.floor(line*2)/2, math.floor(line*2)/2+.5] if ticks%2 else [line,line]
    total=0.0
    for hl in legs:
        margin=(hg-ag+hl) if side=='home' else (ag-hg-hl)
        total += .5*(odds-1) if margin>1e-9 else -.5 if margin<-1e-9 else 0.0
    return round(total,6)
for sr in score_rows:
    if sr['source_type']!='actual_http_receipt':continue
    receipt_audit['candidate_rows']+=1
    fid=sr['fid'];rec_time=sr.get('received_utc') or sr.get('receipt_utc') or sr.get('signal_time_utc')
    # C's final decision receipt is the final element of its verified window.
    if sr['method']=='C_multiscale_concordant_actual_receipt' and sr.get('window_received_utc'):rec_time=sr['window_received_utc'][-1]
    rec=archive_by_time.get((fid,str(rec_time))) if rec_time else None
    if not rec:receipt_audit['missing_archive_receipt']+=1;continue
    horizon=str(rec.get('snapshot_horizon') or sr.get('decision_horizon') or sr.get('verified_receipt_horizon') or '')
    cov=coverage_by_key.get((fid,horizon,str(rec_time)))
    if not cov or not cov.get('verified_receipt') or cov.get('FT') is None or cov.get('FT_error'):
        # The E/F/H independent audit has the verified FT keyed at fixture level;
        # use that source only if the exact matching receipt was already audited.
        c=next((c for c in COVERAGE if str(c.get('fid'))==fid and c.get('verified_receipt') and c.get('FT') is not None and not c.get('FT_error')),None)
        if not c:receipt_audit['missing_verified_ft']+=1;continue
        cov=c
    ah=rec.get('markets',{}).get('AH') or {};od=ah.get('odds') or {}
    if (abs(float(ah.get('line'))-float(sr['line_home']))>1e-8 or abs(float(od.get('home'))-float(sr['odds_home']))>1e-8 or abs(float(od.get('away'))-float(sr['odds_away']))>1e-8):
        receipt_audit['quote_mismatch']+=1;continue
    ko=dt.datetime.fromisoformat(str(rec['kickoff_utc']).replace('Z','+00:00'));received=dt.datetime.fromisoformat(str(rec_time).replace('Z','+00:00'))
    if received>=ko:receipt_audit['not_pregame']+=1;continue
    rkey=(fid,str(rec_time))
    if rkey not in receipt_seen:
        rawfile=Path(rec['source_file']);attempt=json.loads(rawfile.read_text());raw=attempt['raw_response'];raw_digest=hashlib.sha256(raw.encode()).hexdigest();receipt_audit['raw_sha_checks']+=1
        if raw_digest!=rec['raw_sha256'] or raw_digest!=attempt.get('raw_sha256'):
            receipt_audit['raw_sha_mismatch']+=1;continue
        snapshot=Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23/snapshots')/fid/horizon/'snapshot.json'
        if not snapshot.exists() or hashlib.sha256(snapshot.read_bytes()).hexdigest()!=rec['snapshot_sha256']:
            receipt_audit['snapshot_sha_mismatch']+=1;continue
        receipt_audit['snapshot_sha_checks']+=1
        receipt_seen[rkey]=(rec,cov)
    hg,ag=map(int,cov['FT']);pnl=settle_crown(float(ah['line']),sr['side'],hg,ag,float(od[sr['side']]))
    if abs(pnl-float(sr['pnl_u']))>1e-6:receipt_audit['settlement_mismatch']+=1
    sr['original_pnl_u']=sr['pnl_u'];sr['pnl_u']=pnl;sr['ft']=f'{hg}-{ag}';sr['FT_source']=cov.get('FT_source');sr['received_utc']=str(rec_time);sr['receipt_horizon']=horizon;sr['raw_sha256']=rec['raw_sha256'];sr['snapshot_sha256']=rec['snapshot_sha256']
    receipt_audit['audited_rows']+=1
receipt_audit['unique_http_receipts']=len(receipt_seen)


# Canonical horizons for same-quote model-agreement features.
def horizon_of(r):
    m=r['method']
    if m.startswith(('A_','D_','G_')):return 'T1'
    if 'T24' in m:return 'T24'
    if 'T12' in m:return 'T12'
    if r.get('source_type')=='actual_http_receipt':
        return str(r.get('decision_horizon') or r.get('verified_receipt_horizon') or r.get('receipt_horizon') or (r.get('window_receipts') or ['unknown'])[-1])
    return 'T12'
for r in score_rows:r['analysis_horizon']=horizon_of(r)

# Exact same-match/same-Crown-price cross-model predictions. These supply an
# interpretable epistemic disagreement proxy; scores are not treated as
# independent probabilities.
def quote_group_key(r):
    if r['source_type']=='actual_http_receipt':
        time=r.get('received_utc') or r.get('receipt_utc') or r.get('signal_time_utc')
        if r['method']=='C_multiscale_concordant_actual_receipt' and r.get('window_received_utc'):time=r['window_received_utc'][-1]
    else:time=r['analysis_horizon']
    return (r['source_type'],r['fid'],r['date'],str(time),round(float(r['line_home']),6),round(float(r['odds_home']),6),round(float(r['odds_away']),6))
quote_groups=collections.defaultdict(list)
for r in score_rows:quote_groups[quote_group_key(r)].append(r)
consensus_rows=[]
for key,rs in quote_groups.items():
    numeric=[r for r in rs if isinstance(r.get('score_home_minus_away'),(int,float)) and math.isfinite(float(r['score_home_minus_away']))]
    # D contributes its discrete side vote but no numeric confidence.
    votes=[('home' if float(r['score_home_minus_away'])>=0 else 'away',r['method']) for r in numeric]
    votes += [(r['side'],r['method']) for r in rs if r['method']=='D_path_transition_state']
    if len(numeric)<2:continue
    scores=np.asarray([float(r['score_home_minus_away']) for r in numeric]);mean=float(scores.mean());sd=float(scores.std(ddof=1)) if len(scores)>1 else 0.
    side='home' if mean>=0 else 'away'; first=rs[0]
    outcomes=[(r.get('actual_home_u'),r.get('actual_away_u')) for r in rs if r.get('actual_home_u') is not None]
    if not outcomes:continue
    hu,au=outcomes[0]
    homevotes=sum(v=='home' for v,_ in votes);awayvotes=sum(v=='away' for v,_ in votes);totalv=len(votes)
    consensus_rows.append({'fid':key[1],'date':key[2],'kickoff_utc':first.get('kickoff_utc'),'signal_time_utc':first.get('received_utc') or first.get('signal_time_utc'),'source_type':key[0],'analysis_horizon':first['analysis_horizon'],'line_home':float(first['line_home']),'odds_home':float(first['odds_home']),'odds_away':float(first['odds_away']),'side':side,'pnl_u':float(hu if side=='home' else au),'actual_home_u':float(hu),'actual_away_u':float(au),'score_home_minus_away':mean,'confidence_abs':abs(mean),'model_score_dispersion_sd':sd,'model_count':len(numeric),'vote_count':totalv,'vote_agreement':max(homevotes,awayvotes)/totalv if totalv else None,'foundation_overlap':key[1] in foundation,'methods':[r['method'] for r in numeric]})

# Metrics: one unit per selected unique fixture. Week averages use elapsed ISO
# weeks between the first/last candidate date; all weekly counts are retained.
def metrics(rows):
    rows=[r for r in rows if r.get('date') and r.get('pnl_u') is not None]
    if not rows:return {'orders':0,'net_u':0.0,'roi_pct':None,'weeks_elapsed':0,'active_weeks':0,'avg_orders_per_week':None,'max_drawdown_daily_close_u':0.0,'wins':0,'losses':0,'pushes':0,'weekly':{}}
    byday=collections.defaultdict(float);byweek=collections.Counter();total=0.0;wins=losses=pushes=0
    for r in rows:
        d=str(r['date'])[:10];p=float(r['pnl_u']);total+=p;byday[d]+=p
        iso=dt.date.fromisoformat(d).isocalendar();byweek[(iso.year,iso.week)]+=1
        if p>1e-9:wins+=1
        elif p<-1e-9:losses+=1
        else:pushes+=1
    bal=peak=mdd=0.
    for d in sorted(byday):bal+=byday[d];peak=max(peak,bal);mdd=max(mdd,peak-bal)
    first=min(dt.date.fromisoformat(str(r['date'])[:10]) for r in rows);last=max(dt.date.fromisoformat(str(r['date'])[:10]) for r in rows)
    weeks=((last-dt.timedelta(days=last.weekday()))-(first-dt.timedelta(days=first.weekday()))).days//7+1
    return {'orders':len(rows),'net_u':round(total,6),'roi_pct':round(100*total/len(rows),6),'weeks_elapsed':weeks,'active_weeks':len(byweek),'avg_orders_per_week':round(len(rows)/weeks,6),'avg_orders_per_active_week':round(len(rows)/len(byweek),6),'max_drawdown_daily_close_u':round(mdd,6),'wins':wins,'losses':losses,'pushes':pushes,'weekly':{f'{y}-W{w:02}':n for (y,w),n in sorted(byweek.items())}}
def add_foundation(baseyear,adds):
    ids={str(r['fid']) for r in foundation.values()}
    base_rows=[{'fid':fid,'date':f['date'],'pnl_u':float(f['pnl'])} for fid,f in foundation.items() if int(f['date'][:4]) in baseyear]
    new=[];seen=set()
    for r in adds:
        if str(r['fid']) in ids or str(r['fid']) in seen:continue
        seen.add(str(r['fid']));new.append(r)
    return base_rows+new

def score_conf(r):
    c=r.get('confidence_abs')
    return abs(float(c)) if c is not None and math.isfinite(float(c)) else None

def year_rows(rs,y):return [r for r in rs if int(str(r['date'])[:4])==int(y)]

def quantile_edges(values,n=5):
    vals=np.asarray(values,dtype=float);edges=np.quantile(vals,np.linspace(0,1,n+1));return [float(x) for x in np.unique(edges)]
def assign_bin(value,edges):
    return min(len(edges)-2,max(0,int(np.searchsorted(edges[1:-1],float(value),side='right')))) if len(edges)>1 else 0

def calibrate_gate(train,test,gate):
    train=[r for r in train if score_conf(r) is not None];test=[r for r in test if score_conf(r) is not None]
    if not train:return [],{'reason':'no prior-year training rows; no trained gate is available'}
    cs=[score_conf(r) for r in train];edges=quantile_edges(cs,5);tb=collections.defaultdict(list)
    for r in train:tb[assign_bin(score_conf(r),edges)].append(r)
    bin_train={b:metrics(v) for b,v in tb.items()}
    if gate=='top20_prior_confidence':
        threshold=float(np.quantile(cs,.8));selected=[r for r in test if score_conf(r)>=threshold]
        return selected,{'threshold':threshold,'training_n':len(train),'training_metrics':metrics([r for r in train if score_conf(r)>=threshold]),'edges':edges}
    if gate=='prior_positive_confidence_bins':
        bins=[b for b,v in bin_train.items() if v['roi_pct'] is not None and v['roi_pct']>0]
        selected=[r for r in test if assign_bin(score_conf(r),edges) in bins]
        return selected,{'threshold_bins':bins,'training_n':len(train),'training_bin_metrics':bin_train,'edges':edges}
    if gate=='prior_net_max_threshold':
        grid=[]
        for q in np.linspace(0,.9,10):
            t=float(np.quantile(cs,q));tr=[r for r in train if score_conf(r)>=t];grid.append({'q':round(float(q),2),'threshold':t,'metrics':metrics(tr)})
        best=max(grid,key=lambda x:(x['metrics']['net_u'],x['metrics']['orders']))
        selected=[r for r in test if score_conf(r)>=best['threshold']] if best['metrics']['net_u']>0 else []
        return selected,{'selected_threshold':best['threshold'] if best['metrics']['net_u']>0 else None,'selected_quantile':best['q'] if best['metrics']['net_u']>0 else None,'training_selected_metrics':best['metrics'],'training_threshold_grid':grid,'training_n':len(train),'edges':edges}
    if gate=='prior_roi_max_threshold':
        grid=[]
        for q in np.linspace(0,.9,10):
            t=float(np.quantile(cs,q));tr=[r for r in train if score_conf(r)>=t];grid.append({'q':round(float(q),2),'threshold':t,'metrics':metrics(tr)})
        valid=[x for x in grid if x['metrics']['roi_pct'] is not None]
        best=max(valid,key=lambda x:(x['metrics']['roi_pct'],x['metrics']['orders']))
        selected=[r for r in test if score_conf(r)>=best['threshold']] if best['metrics']['roi_pct']>0 else []
        return selected,{'selected_threshold':best['threshold'] if best['metrics']['roi_pct']>0 else None,'selected_quantile':best['q'] if best['metrics']['roi_pct']>0 else None,'training_selected_metrics':best['metrics'],'training_threshold_grid':grid,'training_n':len(train),'edges':edges}
    raise ValueError(gate)

# Descriptive score/uncertainty calibration. Target-year quantile tables are
# diagnostics only; action gates use training-year score edges and outcomes.
def score_diagnostics(rows):
    out={}
    for source in ('historical_event_replay','actual_http_receipt'):
      for y in (2024,2025,2026):
        z=[r for r in rows if r['source_type']==source and int(r['date'][:4])==y and r.get('score_home_minus_away') is not None and r.get('actual_home_u') is not None and (source!='actual_http_receipt' or r.get('receipt_horizon'))]
        if not z:continue
        x=np.asarray([float(r['score_home_minus_away']) for r in z]);yd=np.asarray([float(r['actual_home_u'])-float(r['actual_away_u']) for r in z]);sel=np.asarray([float(r['pnl_u']) for r in z]);out[f'{source}_{y}']={'n':len(z),'forced_selection_metrics':metrics(z),'pearson_score_vs_realized_home_minus_away':float(np.corrcoef(x,yd)[0,1]) if np.std(x)>0 and np.std(yd)>0 else None,'pearson_abs_confidence_vs_selected_pnl':float(np.corrcoef(np.abs(x),sel)[0,1]) if np.std(x)>0 and np.std(sel)>0 else None,'mean_raw_score':float(x.mean()),'mean_realized_home_minus_away_u':float(yd.mean()),'mean_selected_pnl_u':float(sel.mean()),'mean_market_favorite_odds':float(np.mean([r['market_favorite_odds'] for r in z])),'mean_abs_handicap':float(np.mean([r['absolute_ah_line'] for r in z]))}
    # Market price/handicap state are descriptive slices, not learned cutoffs.
    for field in ('favorite_odds_bucket','line_bucket'):
      groups=collections.defaultdict(list)
      for r in rows:
        if r['source_type']=='historical_event_replay' and r['date'][:4] in {'2024','2025','2026'} and r.get('score_home_minus_away') is not None and r.get(field):groups[r[field]].append(r)
      out[field]={k:metrics(v) for k,v in groups.items()}
    for field in ('uncertainty_sd_margin','uncertainty_entropy','model_score_dispersion_sd','vote_agreement'):
      z=[r for r in rows if r.get(field) is not None and r.get('pnl_u') is not None and (r['source_type']!='actual_http_receipt' or r.get('receipt_horizon'))]
      if z:
       vals=np.asarray([float(r[field]) for r in z]);edges=quantile_edges(vals,5);bins=collections.defaultdict(list)
       for r in z:bins[assign_bin(float(r[field]),edges)].append(r)
       out[field]={'edges':edges,'bins':{str(k):metrics(v) for k,v in sorted(bins.items())},'interpretation':'descriptive after-the-fact grouping; not a trading gate'}
    return out

# D is a state-only rule. Calibrate (state, action) using previous years only.
def d_state_gate(train,test):
    by=collections.defaultdict(list)
    for r in train:by[(r.get('path_state'),r.get('side'))].append(r)
    good={k for k,v in by.items() if metrics(v)['net_u']>0}
    return [r for r in test if (r.get('path_state'),r.get('side')) in good],{'positive_training_states':[{'state':k[0],'side':k[1],'metrics':metrics(v)} for k,v in by.items() if k in good],'all_training_states':{f'{k[0]}|{k[1]}':metrics(v) for k,v in by.items()}}

GATES=('top20_prior_confidence','prior_positive_confidence_bins','prior_net_max_threshold','prior_roi_max_threshold')
selective={};paired={};calibrations={}
for method in sorted({r['method'] for r in score_rows}):
    mrows=[r for r in score_rows if r['method']==method and r.get('pnl_u') is not None and (r['source_type']!='actual_http_receipt' or r.get('receipt_horizon'))]
    selective[method]={};paired[method]={};calibrations[method]={}
    for source in sorted({r['source_type'] for r in mrows}):
      srows=[r for r in mrows if r['source_type']==source]
      for year in (2024,2025,2026):
        test=year_rows(srows,year)
        if not test:continue
        train=[r for r in srows if int(r['date'][:4])<year]
        key=f'{source}_{year}';selective[method][key]={'forced_all':metrics(test)};paired[method][key]={};calibrations[method][key]={}
        if method=='D_path_transition_state':
            chosen,cal=d_state_gate(train,test);gate_results={'prior_positive_state_action':(chosen,cal)}
        elif any(score_conf(r) is not None for r in test):
            gate_results={g:calibrate_gate(train,test,g) for g in GATES}
        else:continue
        for gate,(chosen,cal) in gate_results.items():
            selective[method][key][gate]=metrics(chosen);calibrations[method][key][gate]=cal
            adds=[r for r in chosen if not r.get('foundation_overlap')]
            sameids={r['fid'] for r in chosen};forced_same=[r for r in test if r['fid'] in sameids]
            paired[method][key][gate]={'same_fixture_count':len(test),'forced_all':metrics(test),'selective':metrics(chosen),'same_fid_forced':metrics(forced_same),'added_vs_foundation':metrics(adds),'merged_foundation':metrics(add_foundation({year},adds))}

# Transfer prior historical-event calibrations to 2026 actual Crown receipts.
# Receipt outcomes are never used to fit a threshold.
actual_receipt_transfer={};actual_receipt_transfer_cal={}
for method in sorted({r['method'] for r in score_rows}):
  hist=[r for r in score_rows if r['method']==method and r['source_type']=='historical_event_replay' and r.get('pnl_u') is not None and int(r['date'][:4])<2026]
  test=[r for r in score_rows if r['method']==method and r['source_type']=='actual_http_receipt' and int(r['date'][:4])==2026 and r.get('pnl_u') is not None and r.get('receipt_horizon')]
  if not hist or not test:continue
  actual_receipt_transfer[method]={'forced_same_receipts':metrics(test)};actual_receipt_transfer_cal[method]={}
  for gate in GATES:
    chosen,cal=calibrate_gate(hist,test,gate);ids={r['fid'] for r in chosen};forced_same=[r for r in test if r['fid'] in ids];adds=[r for r in chosen if not r.get('foundation_overlap')]
    actual_receipt_transfer[method][gate]={'selected':metrics(chosen),'same_fid_forced':metrics(forced_same),'added_vs_foundation':metrics(adds),'merged_foundation':metrics(add_foundation({2026},adds))}
    actual_receipt_transfer_cal[method][gate]=cal

consensus_summary={};consensus_cal={};consensus_by_horizon={}
for source in ('historical_event_replay','actual_http_receipt'):
  source_rows=[r for r in consensus_rows if r['source_type']==source]
  consensus_summary[source]={};consensus_cal[source]={}
  for horizon in sorted({r['analysis_horizon'] for r in source_rows}):
    rows=[r for r in source_rows if r['analysis_horizon']==horizon and (source!='actual_http_receipt' or r.get('receipt_horizon'))]
    # One quote horizon per FID; audit and remove any accidental duplicate.
    unique={}
    for r in rows: unique.setdefault(r['fid'],r)
    rows=list(unique.values()); hk=f'{source}|{horizon}'
    consensus_by_horizon[hk]={'all':metrics(rows),'unique_fids':len(rows)}
    consensus_summary[source][horizon]={'all':metrics(rows)};consensus_cal[hk]={}
    for year in (2024,2025,2026):
      test=year_rows(rows,year);train=[r for r in rows if int(r['date'][:4])<year]
      if not test:continue
      consensus_summary[source][horizon][str(year)]={'forced_all':metrics(test)};consensus_cal[hk][str(year)]={}
      for gate in GATES:
        chosen,cal=calibrate_gate(train,test,gate);consensus_summary[source][horizon][str(year)][gate]=metrics(chosen);consensus_cal[hk][str(year)][gate]=cal
        adds=[r for r in chosen if not r.get('foundation_overlap')]
        consensus_summary[source][horizon][str(year)][gate+'_added_vs_foundation']=metrics(adds)
        consensus_summary[source][horizon][str(year)][gate+'_merged_foundation']=metrics(add_foundation({year},adds))

consensus_actual_transfer={};consensus_actual_transfer_cal={}
for horizon in sorted(set(r['analysis_horizon'] for r in consensus_rows if r['source_type']=='actual_http_receipt')):
  hist=[r for r in consensus_rows if r['source_type']=='historical_event_replay' and r['analysis_horizon']==horizon and int(r['date'][:4])<2026]
  test=[r for r in consensus_rows if r['source_type']=='actual_http_receipt' and r['analysis_horizon']==horizon and int(r['date'][:4])==2026 and r.get('pnl_u') is not None and r.get('receipt_horizon')]
  if not hist or not test:continue
  test=list({r['fid']:r for r in test}.values());consensus_actual_transfer[horizon]={'forced_all':metrics(test)};consensus_actual_transfer_cal[horizon]={}
  for gate in GATES:
    chosen,cal=calibrate_gate(hist,test,gate);ids={r['fid'] for r in chosen};forced_same=[r for r in test if r['fid'] in ids];adds=[r for r in chosen if not r.get('foundation_overlap')]
    consensus_actual_transfer[horizon][gate]={'selected':metrics(chosen),'same_fid_forced':metrics(forced_same),'added_vs_foundation':metrics(adds),'merged_foundation':metrics(add_foundation({2026},adds))}
    consensus_actual_transfer_cal[horizon][gate]=cal

actual_diag={}
for method in ('B_actual_receipt_freshness_favorite_diagnostic','C_multiscale_concordant_actual_receipt'):
  rows=[r for r in score_rows if r['method']==method and r.get('pnl_u') is not None and (r['source_type']!='actual_http_receipt' or r.get('receipt_horizon'))]
  actual_diag[method]={'all':metrics(rows)}
  fields=('quote_age_minutes','received_minutes_to_kickoff') if method.startswith('B_') else ('raw_move_score','confidence_abs')
  for field in fields:
    vals=[float(r[field]) for r in rows if r.get(field) is not None]
    if not vals:continue
    edges=quantile_edges(vals,5);groups=collections.defaultdict(list)
    for r in rows:
      if r.get(field) is not None:groups[assign_bin(float(r[field]),edges)].append(r)
    actual_diag[method][field]={'edges':edges,'bins':{str(k):metrics(v) for k,v in groups.items()}}

by_method={}
for method in sorted({r['method'] for r in score_rows}):
  by_method[method]={}
  for source in ('historical_event_replay','actual_http_receipt'):
    rows=[r for r in score_rows if r['method']==method and r['source_type']==source and r.get('pnl_u') is not None and (source!='actual_http_receipt' or r.get('receipt_horizon'))]
    if rows:
      by_method[method][source]={'all':metrics(rows),'by_year':{str(y):metrics(year_rows(rows,y)) for y in (2024,2025,2026) if year_rows(rows,y)},'outside_foundation':metrics([r for r in rows if not r.get('foundation_overlap')]),'outside_foundation_by_year':{str(y):metrics([r for r in year_rows(rows,y) if not r.get('foundation_overlap')]) for y in (2024,2025,2026) if year_rows(rows,y)}}

overlap={}
for source in ('historical_event_replay','actual_http_receipt'):
  methods=sorted({r['method'] for r in score_rows if r['source_type']==source})
  sets={m:{r['fid'] for r in score_rows if r['method']==m and r['source_type']==source} for m in methods}
  overlap[source]={'method_fid_counts':{m:len(v) for m,v in sets.items()},'pairwise_intersection':{f'{a} <> {b}':len(sets[a]&sets[b]) for i,a in enumerate(methods) for b in methods[i+1:]},'union_fids':len(set().union(*sets.values())) if sets else 0,'union_outside_foundation':len(set().union(*sets.values())-{str(x) for x in foundation}) if sets else 0}

summary={'study':'M8 selective profitability research','date':'2026-11-19','foundation_unique_fids':len(foundation),'foundation_sha256':hashlib.sha256(('\n'.join(sorted(foundation))+'\n').encode()).hexdigest(),'score_rows':len(score_rows),'consensus_rows':len(consensus_rows),'methods':by_method,'selective_walk_forward':selective,'paired_same_fixture_and_foundation':paired,'training_calibrations_all_grids':calibrations,'consensus_walk_forward':consensus_summary,'consensus_calibrations':consensus_cal,'consensus_actual_receipt_transfer':consensus_actual_transfer,'consensus_actual_receipt_transfer_calibrations':consensus_actual_transfer_cal,'actual_receipt_transfer_by_method':actual_receipt_transfer,'actual_receipt_transfer_calibrations':actual_receipt_transfer_cal,'consensus_overall_by_horizon':consensus_by_horizon,'diagnostics':score_diagnostics(score_rows),'actual_receipt_B_C_diagnostics':actual_diag,'overlap':overlap,'receipt_audit':receipt_audit,'rerun_checks':rerun_checks,'limitations':['Thresholds and confidence bins are research-only and learned only on prior years.','Forecast features do not include target outcomes; foundation membership is used only after prediction for incremental accounting.','B has no direction score and C is movement concordance, so both are descriptive diagnostics.','Actual Crown rows require exact pregame receipt, quote, response/snapshot SHA and independently verified FT/AH quarter settlement.','Actual receipt coverage differs by method/horizon; historical quote replays and real receipts are not pooled.']}

with gzip.open(OUT/'m8_selective_scores_20261119.jsonl.gz','wt',encoding='utf-8',compresslevel=6) as f:
  for r in score_rows:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
with gzip.open(OUT/'m8_selective_consensus_20261119.jsonl.gz','wt',encoding='utf-8',compresslevel=6) as f:
  for r in consensus_rows:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
(OUT/'M8_SELECTIVE_PROFITABILITY_RESULTS_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
manifest={'input_scripts':{k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in SCRIPT_PATHS.items()},'input_order_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in ORDER_PATHS},'foundation_manifest_sha256':hashlib.sha256(FOUNDATION.read_bytes()).hexdigest(),'score_sha256':hashlib.sha256((OUT/'m8_selective_scores_20261119.jsonl.gz').read_bytes()).hexdigest(),'consensus_sha256':hashlib.sha256((OUT/'m8_selective_consensus_20261119.jsonl.gz').read_bytes()).hexdigest(),'summary_sha256':hashlib.sha256((OUT/'M8_SELECTIVE_PROFITABILITY_RESULTS_20261119.json').read_bytes()).hexdigest(),'receipt_audit':receipt_audit,'rerun_checks':rerun_checks}
(OUT/'execution_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'score_rows':len(score_rows),'consensus_rows':len(consensus_rows),'methods':len(by_method),'actual_receipt_audit':receipt_audit,'rerun_checks':rerun_checks},ensure_ascii=False))
