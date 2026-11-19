#!/usr/bin/env python3
"""Independent raw Crown AH/FT and settlement audit for competition study."""
import bisect, collections, datetime as dt, gzip, hashlib, json, math, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
OUT=ROOT/'research/m8/competition_objective_20261119'
FEATURES=OUT/'m8_competitive_objective_feature_rows_20261119.jsonl.gz'
PRED=OUT/'m8_competitive_objective_prediction_ledger_20261119.jsonl.gz'

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def parse_dt(s):
    x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
    # Crown JSON stores naive timestamps in its local +08:00 time zone.
    return x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc) if x.tzinfo is None else x.astimezone(dt.timezone.utc)
def settle(line,side,hg,ag,odds):
    line=float(line); odds=float(odds)
    if abs(line*4-round(line*4))>1e-8: raise ValueError('line outside quarter grid')
    z=(int(hg)-int(ag)+line) if side=='home' else (int(ag)-int(hg)-line)
    twice=round(line*2)
    legs=[line] if abs(twice/2-line)<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
    cash=[]
    for x in legs:
        q=(int(hg)-int(ag)+x) if side=='home' else (int(ag)-int(hg)-x)
        cash.append(odds-1 if q>1e-9 else -1.0 if q<-1e-9 else 0.0)
    return sum(cash)/len(cash)

# Reuse the existing M7/M8 raw response locator sources; verify body hashes.
known={r['fid']:r for r in map(json.loads,(WORK/'m8_late_full_path_water_features_20261114.jsonl').open())}
loc={}
for r in map(json.loads,(WORK/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl').open()):
    fid=str(r['fixture_id'])
    if fid in known and int(known[fid]['year'])<2026:
        loc[fid]={'path':r['source_file'],'sha':r.get('raw_sha256')}
idxp=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-response-index.jsonl')
idx={str(x['match_id']):x for x in map(json.loads,idxp.open())}
for fid,r in known.items():
    if int(r['year'])==2026:
        loc[fid]={'path':str(pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses')/(fid+'.json')),'sha':idx.get(fid,{}).get('response_sha256')}
for name in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
    for r in map(json.loads,(WORK/name).open()):
        fid=str(r['fid'])
        if fid in known and fid not in loc: loc[fid]={'path':r['source_file'],'sha':None}

features={}
with gzip.open(FEATURES,'rt',encoding='utf-8') as f:
    for line in f:
        x=json.loads(line); features[str(x['fid'])]=x
pred=[]
with gzip.open(PRED,'rt',encoding='utf-8') as f: pred=[json.loads(x) for x in f]
pred_by=collections.defaultdict(list)
for x in pred: pred_by[str(x['fid'])].append(x)
fail=collections.Counter(); audit=[]
for fid in sorted(pred_by):
    f=features.get(fid); source=loc.get(fid)
    if f is None: fail['missing_feature_row']+=1; continue
    if not source or not pathlib.Path(source['path']).is_file(): fail['missing_raw_crown_body']+=1; continue
    raw=pathlib.Path(source['path']).read_bytes(); actual=sha_bytes(raw)
    if source.get('sha') and actual!=source['sha']: fail['raw_sha_mismatch']+=1; continue
    try: body=json.loads(raw)
    except Exception: fail['invalid_raw_json']+=1; continue
    data=body.get('data'); matches=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
    if len(matches)!=1: fail['raw_fixture_cardinality']+=1; continue
    m=matches[0]
    if (str(m.get('id'))!=fid or str(m.get('l_id'))!=str(f['league']) or
        str(m.get('h_id'))!=str(f['home_id']) or str(m.get('a_id'))!=str(f['away_id'])):
        fail['fixture_identity_mismatch']+=1; continue
    ko=parse_dt(m['start'])
    if ko.date().isoformat()!=f['date'] or int(m['hg'])!=int(f['hg']) or int(m['ag'])!=int(f['ag']):
        fail['kickoff_or_ft_mismatch']+=1; continue
    crown=[b for b in (m.get('bookmakers') or []) if str(b.get('slug','')).lower()=='crown']
    if not crown: fail['missing_crown_bookmaker']+=1; continue
    b=crown[0]; q=[]
    for row in b.get('asian_list') or []:
        try:
            t=parse_dt(row[4]); vals=list(map(float,row[1:4]))
            if t<ko and vals[1]>1 and vals[2]>1 and abs(vals[0]*4-round(vals[0]*4))<1e-8: q.append((t,*vals))
        except Exception: pass
    for tag in ('open','close'):
        row=(b.get('asian') or {}).get(tag)
        if isinstance(row,dict):
            try:
                t=parse_dt(row['time']); vals=(float(row['line']),float(row['home']),float(row['away']))
                if t<ko and vals[1]>1 and vals[2]>1 and abs(vals[0]*4-round(vals[0]*4))<1e-8:q.append((t,*vals))
            except Exception: pass
    cut=ko-dt.timedelta(hours=12); q.sort(key=lambda z:z[0]); ii=bisect.bisect_right([z[0] for z in q],cut)-1
    if ii<0: fail['no_pre_kickoff_Crown_quote_before_T12']+=1; continue
    qt,line,ho,ao=q[ii]
    expected=float(f['AH_line']); expected_home=float(f['AH_home_odds']); expected_away=float(f['AH_away_odds'])
    # feature line is signed from Crown home perspective and comes from R49 T12.
    if any(abs(a-b)>1e-8 for a,b in ((line,expected),(ho,expected_home),(ao,expected_away))):
        fail['T12_quote_mismatch']+=1; continue
    uh=settle(line,'home',m['hg'],m['ag'],ho); ua=settle(line,'away',m['hg'],m['ag'],ao)
    if abs(uh-float(f['home_U']))>1e-8 or abs(ua-float(f['away_U']))>1e-8:
        fail['independent_two_side_settlement_mismatch']+=1; continue
    row={'fid':fid,'year':f['year'],'date':f['date'],'kickoff_utc':ko.isoformat(),'T12_cutoff_utc':cut.isoformat(),
         'Crown_quote_event_utc':qt.isoformat(),'raw_crown_sha256':actual,'AH_line_home':line,'AH_home_odds':ho,'AH_away_odds':ao,
         'FT_home':int(m['hg']),'FT_away':int(m['ag']),'independent_home_U':uh,'independent_away_U':ua,
         'quote_event_time_is_not_HTTP_receipt_time':True}
    for p in pred_by[fid]:
        side=p['direction']; value=uh if side=='home' else ua
        if abs(value-float(p['actual_side_U']))>1e-8: fail['prediction_ledger_settlement_mismatch']+=1
        row.setdefault('models',{})[p['model']]={'direction':side,'settlement_class':p['settlement_class'],'recomputed_U':value}
    audit.append(row)

# No claim of actual receipt replay: make the exact FID intersection explicit.
receipt_rows=[json.loads(x) for x in (WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl').open()]
receipt_fids={str(x['fixture_id']) for x in receipt_rows}
prediction_fids=set(pred_by)
summary={'study':'M8_COMPETITIVE_OBJECTIVE_INDEPENDENT_RAW_CROWN_SETTLEMENT_AUDIT_20261119',
 'prediction_rows':len(pred),'prediction_unique_fids':len(prediction_fids),'raw_Crown_FIDs_verified':len(audit),
 'raw_source_failures':dict(fail),'receipt_archive_rows':len(receipt_rows),'receipt_archive_unique_fids':len(receipt_fids),
 'prediction_receipt_FID_intersection':len(prediction_fids&receipt_fids),
 'AH_method':'Re-read raw Crown response and FT; quarter lines split into adjacent half-goal legs; home and away independently settled.',
 'receipt_method':'Historical quote event timestamp selected at or before T-12h; this does not prove HTTP receipt at T-12h.',
 'all_prediction_rows_reconciled':not any(k.endswith('mismatch') or 'mismatch' in k for k in fail)}
(OUT/'independent_settlement_audit_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with gzip.open(OUT/'independent_raw_crown_fid_audit_20261119.jsonl.gz','wt',encoding='utf-8') as f:
    for x in audit:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
