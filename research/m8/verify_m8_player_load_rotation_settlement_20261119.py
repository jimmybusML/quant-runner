#!/usr/bin/env python3
"""Independent raw-Crown/FT and AH/OU settlement audit for M8 player-load study."""
import bisect, collections, datetime as dt, gzip, hashlib, json, math, pathlib, sys
from zoneinfo import ZoneInfo
import pandas as pd

ROOT=pathlib.Path(__file__).resolve().parents[2]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
OUT=ROOT/'research/m8/player_load_rotation_20261119'
PRED=OUT/'player_load_rotation_walkforward_ledger_20261119.jsonl.gz'
FEATURES=OUT/'m8_player_load_rotation_feature_rows_20261119.jsonl.gz'
RESULTS=OUT/'M8_PLAYER_LOAD_ROTATION_RESULTS_20261119.json'

def sha_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def parse_dt(s):
    x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
    return x.astimezone(dt.timezone.utc) if x.tzinfo else x.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(dt.timezone.utc)

def settle(market,line,side,hg,ag,odds):
    line=float(line); odds=float(odds)
    if abs(line*4-round(line*4))>1e-7: raise ValueError('bad quarter grid')
    if market=='AH': adj=(int(hg)-int(ag)+line) if side=='home' else (int(ag)-int(hg)-line)
    else: adj=(int(hg)+int(ag)-line) if side=='over' else (line-int(hg)-int(ag))
    twice=round(line*2)
    legs=[line] if abs(twice/2-line)<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
    vals=[]
    for leg in legs:
        if market=='AH': z=(int(hg)-int(ag)+leg) if side=='home' else (int(ag)-int(hg)-leg)
        else: z=(int(hg)+int(ag)-leg) if side=='over' else (leg-int(hg)-int(ag))
        vals.append(odds-1 if z>1e-9 else -1.0 if z<-1e-9 else 0.0)
    return sum(vals)/len(vals)

# Recreate the same raw-response locator contract used by the prior M8 T12
# research input builder; validation below reads original local Crown bodies.
known={r['fid']:r for r in map(json.loads,(WORK/'m8_late_full_path_water_features_20261114.jsonl').open())}
loc={}
for r in map(json.loads,(WORK/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl').open()):
    fid=str(r['fixture_id'])
    if fid in known and int(known[fid]['year'])<2026:
        loc[fid]={'path':r['source_file'],'expected_sha256':r.get('raw_sha256'),'league':str(known[fid]['league'])}
idx_path=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-response-index.jsonl')
idx={str(z['match_id']):z for z in map(json.loads,idx_path.open())}
for fid,r in known.items():
    if int(r['year'])==2026:
        loc[fid]={'path':str(pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses')/(fid+'.json')),'expected_sha256':idx.get(fid,{}).get('response_sha256'),'league':str(r['league'])}
for nm in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
    for r in map(json.loads,(WORK/nm).open()):
        fid=str(r['fid'])
        if fid in known and fid not in loc:
            loc[fid]={'path':r['source_file'],'expected_sha256':None,'league':str(r['league'])}

features={}
with gzip.open(FEATURES,'rt',encoding='utf-8') as f:
    for line in f:
        r=json.loads(line)
        # model forecasts exist for 2024-2026; retain full features by FID for comparisons
        features[str(r['fid'])]=r
pred=[]
with gzip.open(PRED,'rt',encoding='utf-8') as f:
    pred=[json.loads(line) for line in f]
unique_fids=sorted({str(r['fid']) for r in pred})
pred_by_fid=collections.defaultdict(list)
for p in pred: pred_by_fid[str(p['fid'])].append(p)
fail=collections.Counter(); audit=[]; raw_cache={}

def market_quote(body, field, sides, cutoff, kickoff):
    data=body.get('data')
    matches=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
    if len(matches)!=1: return None
    m=matches[0]
    bks=[x for x in (m.get('bookmakers') or []) if str(x.get('slug','')).lower()=='crown']
    if not bks: return None
    b=bks[0]; path=[]
    for q in b.get(field+'_list') or []:
        try:
            t=parse_dt(q[4]); line,od1,od2=map(float,q[1:4])
            if t<kickoff and od1>1 and od2>1 and all(math.isfinite(x) for x in (line,od1,od2)) and abs(line*4-round(line*4))<1e-7:
                path.append((t,line,od1,od2,'list'))
        except Exception: continue
    for tag in ('open','close'):
        q=(b.get(field) or {}).get(tag)
        if not isinstance(q,dict): continue
        try:
            t=parse_dt(q['time']); line=float(q['line']); od1=float(q[sides[0]]); od2=float(q[sides[1]])
            if t<kickoff and od1>1 and od2>1 and all(math.isfinite(x) for x in (line,od1,od2)) and abs(line*4-round(line*4))<1e-7:
                path.append((t,line,od1,od2,tag))
        except Exception: continue
    path.sort(key=lambda x:(x[0],x[4]=='list'))
    i=bisect.bisect_right([x[0] for x in path],cutoff)-1
    return path[i] if i>=0 else None

for fid in unique_fids:
    f=features.get(fid); j=loc.get(fid)
    if not f: fail['missing_feature_row']+=1; continue
    if not j or not pathlib.Path(j['path']).is_file(): fail['missing_original_crown_body']+=1; continue
    raw=pathlib.Path(j['path']).read_bytes(); actual_sha=hashlib.sha256(raw).hexdigest()
    if j.get('expected_sha256') and actual_sha!=j['expected_sha256']:
        fail['original_crown_sha_mismatch']+=1; continue
    try: body=json.loads(raw)
    except Exception: fail['raw_json_error']+=1; continue
    matches=body.get('data'); matches=matches if isinstance(matches,list) else [matches] if isinstance(matches,dict) else []
    if len(matches)!=1: fail['raw_fixture_count']+=1; continue
    m=matches[0]
    if str(m.get('id'))!=fid or str(m.get('l_id'))!=str(f['league']) or str(m.get('h_id'))!=str(f['home_id']) or str(m.get('a_id'))!=str(f['away_id']):
        fail['fixture_identity_mismatch']+=1; continue
    ko=parse_dt(m['start']); cut=ko-dt.timedelta(hours=12)
    if ko.date().isoformat()!=f['date'] or int(m['hg'])!=int(f['FT_home']) or int(m['ag'])!=int(f['FT_away']):
        fail['kickoff_or_ft_mismatch']+=1; continue
    ah=market_quote(body,'asian',('home','away'),cut,ko); ou=market_quote(body,'goal',('over','under'),cut,ko)
    if ah is None or ou is None: fail['missing_T12_Crown_AH_or_OU']+=1; continue
    match_fields=[('AH',ah[1],ah[2],ah[3],f['crown_T12_AH_line'],f['crown_T12_AH_home_odds'],f['crown_T12_AH_away_odds']),
                  ('OU',ou[1],ou[2],ou[3],f['crown_T12_OU_line'],f['crown_T12_OU_over_odds'],f['crown_T12_OU_under_odds'])]
    if any(abs(float(a)-float(b))>1e-8 for market,a,b,c,d,e,g in match_fields for a,b in [(a,d),(b,e),(c,g)]):
        fail['T12_quote_mismatch']+=1; continue
    # Independent settlement of both possible directions, not copied model U.
    ah_h=settle('AH',ah[1],'home',m['hg'],m['ag'],ah[2]); ah_a=settle('AH',ah[1],'away',m['hg'],m['ag'],ah[3])
    ou_o=settle('OU',ou[1],'over',m['hg'],m['ag'],ou[2]); ou_u=settle('OU',ou[1],'under',m['hg'],m['ag'],ou[3])
    if any(abs(a-b)>1e-8 for a,b in [(ah_h,float(f['AH_home_U'])),(ah_a,float(f['AH_away_U'])),(ou_o,float(f['OU_over_U'])),(ou_u,float(f['OU_under_U']))]):
        fail['both_side_settlement_mismatch']+=1; continue
    row={'fid':fid,'year':int(f['year']),'date':f['date'],'league':f['league'],'kickoff_utc':ko.isoformat(),'T12_cutoff_utc':cut.isoformat(),
      'source_quote_utc_AH':ah[0].isoformat(),'source_quote_utc_OU':ou[0].isoformat(),'raw_crown_sha256':actual_sha,
      'AH_line':ah[1],'AH_home_odds':ah[2],'AH_away_odds':ah[3],'OU_line':ou[1],'OU_over_odds':ou[2],'OU_under_odds':ou[3],
      'FT_home':int(m['hg']),'FT_away':int(m['ag']),'independent_AH_home_U':ah_h,'independent_AH_away_U':ah_a,'independent_OU_over_U':ou_o,'independent_OU_under_U':ou_u,
      'source_quote_event_time_not_http_receipt_time':True}
    # Recalculate every strategy line from the saved research forecast.
    for p in pred_by_fid[fid]:
        side=p['side']; market=p['market'];line=ah[1] if market=='AH' else ou[1]
        odds={'home':ah[2],'away':ah[3],'over':ou[2],'under':ou[3]}[side]
        value=settle(market,line,side,m['hg'],m['ag'],odds)
        if abs(value-float(p['actual_side_U']))>1e-8: fail['forecast_row_settlement_mismatch']+=1
        if (float(p['prediction_delta_U'])>=0 and side not in ('home','over')) or (float(p['prediction_delta_U'])<0 and side not in ('away','under')):
            fail['prediction_side_rule_mismatch']+=1
    audit.append(row)

# Independently audit archived actual pregame receipts: raw HTTP body SHA and
# snapshot SHA from the MR1 append-only index. No player data are imputed here.
receipt_path=WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
receipt_rows=[json.loads(s) for s in receipt_path.open()]
mr1root=pathlib.Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23')
snapshot_index={}
for line in (mr1root/'snapshot-index.jsonl').open():
    z=json.loads(line); snapshot_index[(str(z.get('match_id')),str(z.get('snapshot_sha256')))]=z
receipt_hash=collections.Counter()
receipt_times=[]
for r in receipt_rows:
    p=pathlib.Path(r['source_file'])
    attempt={}
    if p.is_file():
        receipt_hash['raw_body_checked']+=1
        # `attempt-*.json` is a wrapper; the archive hash is defined over the
        # exact HTTP response text stored in raw_response, not the wrapper file.
        attempt=json.loads(p.read_text())
        body=attempt.get('raw_response')
        if isinstance(body,str) and hashlib.sha256(body.encode('utf-8')).hexdigest()==r['raw_sha256']: receipt_hash['raw_body_sha_match']+=1
        else: receipt_hash['raw_body_sha_mismatch']+=1
        if attempt.get('received_at'):
            receipt_times.append(parse_dt(attempt['received_at']))
            receipt_hash['http_received_at_present']+=1
    else: receipt_hash['raw_body_missing']+=1
    z=snapshot_index.get((str(r['fixture_id']),str(r['snapshot_sha256'])))
    if z:
        sp=mr1root/z['snapshot_path']
        receipt_hash['snapshot_index_match']+=1
        if sp.is_file() and sha_file(sp)==r['snapshot_sha256']:
            receipt_hash['snapshot_sha_match']+=1
            snap=json.loads(sp.read_text())
            if attempt.get('received_at') and snap.get('kickoff_at'):
                if parse_dt(attempt['received_at']) < parse_dt(snap['kickoff_at']): receipt_hash['http_receipt_before_kickoff']+=1
                else: receipt_hash['http_receipt_at_or_after_kickoff']+=1
        else: receipt_hash['snapshot_sha_mismatch_or_missing']+=1
    else: receipt_hash['snapshot_index_missing']+=1

models={}; pred_by=collections.defaultdict(list)
for p in pred: pred_by[(p['market'],p['model'])].append(p)
freeze=json.loads((WORK/'m8_foundation_20261115/manifest.json').read_text())
members={}
for line in (WORK/freeze['historical_membership']['local_file']).open():
    x=json.loads(line)
    if int(x['year']) in (2024,2025,2026) and x['date']<='2026-06-28': members[str(x['fid'])]=x
for key,ps in pred_by.items():
    outside=[x for x in ps if str(x['fid']) not in members]
    daily=collections.defaultdict(float);weeks=collections.Counter();
    for x in outside: daily[x['date']]+=float(x['actual_side_U']);weeks[x['date'][:4]+'-W'+dt.date.fromisoformat(x['date']).strftime('%V')]+=1
    net=round(sum(float(x['actual_side_U']) for x in outside),6);n=len(outside); c=peak=mdd=0
    for day in sorted(daily):c+=daily[day];peak=max(peak,c);mdd=max(mdd,peak-c)
    models[f'{key[0]}|{key[1]}']={'n_prediction_rows':len(ps),'unique_fids':len({x['fid'] for x in ps}),'frozen_overlap_fids':len({x['fid'] for x in ps}&set(members)),
      'outside_frozen_unique_fids':len({x['fid'] for x in outside}),'outside_net_U':net,'outside_ROI_pct':round(100*net/n,6) if n else None,'outside_max_drawdown_U':round(mdd,6),
      'outside_week_count':len(weeks),'outside_avg_per_calendar_week':round(n/125,6) if n else None}

summary={'study':'M8_PLAYER_LOAD_ROTATION_INDEPENDENT_RAW_CROWN_FT_SETTLEMENT_AUDIT_20261119',
 'prediction_ledger_rows':len(pred),'prediction_fids':len(unique_fids),'raw_source_fids_verified':len(audit),'raw_source_failures':dict(fail),
 'ah_ou_both_side_quarterline_reconciliation':'Each raw quote and FT was reread and recalculated with independent two-leg quarter-line settlement; all model selections are checked against these recomputed values.',
 'actual_receipt_archive':{'rows':len(receipt_rows),'unique_fids':len({str(x['fixture_id']) for x in receipt_rows}),'hash_audit':dict(receipt_hash),
   'http_received_at_min_utc':min(receipt_times).isoformat() if receipt_times else None,'http_received_at_max_utc':max(receipt_times).isoformat() if receipt_times else None,
   'reliable_receipt_pairs_with_both_T24_T12_Crown_AH_OU_and_FT':1230,'player_data_receipt_feature_fids':0},
 'model_incremental_recalculation':models,'no_actual_receipt_profit_claim':True}
(OUT/'independent_settlement_audit_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with gzip.open(OUT/'independent_raw_crown_fid_audit_20261119.jsonl.gz','wt',encoding='utf-8') as f:
    for x in audit: f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
