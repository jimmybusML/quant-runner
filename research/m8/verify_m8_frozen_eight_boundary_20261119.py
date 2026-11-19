#!/usr/bin/env python3
"""Independent raw Crown T1 quote, FT and AH settlement audit."""
import bisect, collections, datetime as dt, gzip, hashlib, json, math, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
OUT=ROOT/'research/m8/frozen_eight_boundary_expansion_20261119'
PRED=OUT/'boundary_candidate_prediction_ledger_20261119.jsonl.gz'
FEATURE=WORK/'m8_late_full_path_water_features_20261114.jsonl'

def sha(b): return hashlib.sha256(b).hexdigest()
def dateparse(x):
    z=dt.datetime.fromisoformat(str(x).replace('Z','+00:00').replace(' ','T'))
    return z.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc) if z.tzinfo is None else z.astimezone(dt.timezone.utc)
def settle(line,side,hg,ag,odds):
    line=float(line); odds=float(odds)
    if abs(line*4-round(line*4))>1e-8: raise ValueError('bad quarter line')
    legs=[line] if abs(round(line*2)/2-line)<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
    out=[]
    for l in legs:
        m=int(hg)-int(ag)+l if side=='home' else int(ag)-int(hg)-l
        out.append(odds-1 if m>1e-9 else -1.0 if m<-1e-9 else 0.0)
    return sum(out)/len(out)
def settle_class(line,side,hg,ag):
    line=float(line)
    legs=[line] if abs(round(line*2)/2-line)<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
    states=[]
    for l in legs:
        m=int(hg)-int(ag)+l if side=='home' else int(ag)-int(hg)-l
        states.append('W' if m>1e-9 else 'L' if m<-1e-9 else 'P')
    return {'WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss'}.get(''.join(states),states[0].lower())

features={r['fid']:r for r in map(json.loads,FEATURE.open())}
loc={}
for name in ('m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1733Z.jsonl',
             'm7_original49_historical_Crown_T30_2h_movement_inventory_20261114.jsonl'):
    p=WORK/'m7'/name
    for r in map(json.loads,p.open()):
        fid=str(r['fixture_id'])
        if r.get('source_file'):
            loc.setdefault(fid,{'path':r['source_file'],'sha':r.get('raw_sha256')})
for name in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
    p=WORK/name
    if not p.exists(): continue
    for r in map(json.loads,p.open()):
        fid=str(r['fid'])
        if r.get('source_file'):
            loc.setdefault(fid,{'path':r['source_file'],'sha':r.get('raw_sha256')})
idxp=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-response-index.jsonl')
idx={str(x['match_id']):x for x in map(json.loads,idxp.open())}
for fid,f in features.items():
    if int(f['year'])==2026:
        loc[fid]={'path':str(pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses')/(fid+'.json')),'sha':idx.get(fid,{}).get('response_sha256')}
extra_rows={}
for x in map(json.loads,(WORK/'m8_extra_inventory_frozen_eight_20261115.jsonl').open()):
    extra_rows[str(x['fid'])]=x

pred=[]
with gzip.open(PRED,'rt',encoding='utf-8') as f:
    pred=[json.loads(x) for x in f]
pred_by=collections.defaultdict(list)
for p in pred: pred_by[str(p['fid'])].append(p)
fails=collections.Counter(); audit=[]
for fid,items in pred_by.items():
    f=features.get(fid) or extra_rows.get(fid); source=loc.get(fid)
    if not f: fails['feature_missing']+=1; continue
    if not source or not pathlib.Path(source['path']).is_file(): fails['raw_body_missing']+=1; continue
    body=pathlib.Path(source['path']).read_bytes(); body_sha=sha(body)
    if source.get('sha') and source['sha']!=body_sha: fails['raw_sha_mismatch']+=1; continue
    try: data=json.loads(body).get('data')
    except Exception: fails['bad_json']+=1; continue
    matches=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
    matches=[x for x in matches if str(x.get('id'))==fid]
    if len(matches)!=1: fails['raw_fid_cardinality']+=1; continue
    m=matches[0]
    sample=items[0]
    league=str(f.get('league') or sample.get('league'))
    home_id=str(sample.get('home_team_id') or f.get('home_team') or '')
    away_id=str(sample.get('away_team_id') or f.get('away_team') or '')
    if str(m.get('l_id'))!=league or str(m.get('h_id'))!=home_id or str(m.get('a_id'))!=away_id:
        fails['identity_mismatch']+=1; continue
    ko=dateparse(m['start'])
    if ko.date().isoformat()!=str(f['date'])[:10] or int(m.get('hg'))!=int(sample['FT_home']) or int(m.get('ag'))!=int(sample['FT_away']):
        fails['kickoff_or_FT_mismatch']+=1; continue
    crown=[x for x in m.get('bookmakers',[]) if str(x.get('slug','')).lower()=='crown']
    if not crown: fails['Crown_missing']+=1; continue
    q=[]
    for x in crown[0].get('asian_list') or []:
        try:
            t=dateparse(x[4]); ln,ho,ao=map(float,x[1:4])
            if t<ko and t<=ko-dt.timedelta(hours=1) and min(ho,ao)>1 and abs(ln*4-round(ln*4))<1e-8:q.append((t,ln,ho,ao))
        except Exception: pass
    if not q: fails['no_valid_Crown_quote_at_T1']+=1; continue
    q.sort(key=lambda z:z[0]); qt,line,ho,ao=q[-1]
    if any(abs(a-b)>1e-8 for a,b in ((line,float(sample['AH_line_home'])),(ho,float(sample['AH_home_odds'])),(ao,float(sample['AH_away_odds'])))):
        fails['T1_quote_mismatch']+=1; continue
    checks=[]
    for p in items:
        side=p['direction']; odds=ho if side=='home' else ao
        pnl=settle(line,side,m['hg'],m['ag'],odds)
        checks.append({'source_group':p['source_group'],'model':p['model'],'q':p['similarity_quantile'],'side':side,'ledger_pnl':p['pnl'],'independent_pnl':pnl,'match':abs(pnl-float(p['pnl']))<1e-8})
        if not checks[-1]['match']: fails['prediction_settlement_mismatch']+=1
    audit.append({'fid':fid,'year':f['year'],'date':f['date'],'Crown_quote_event_utc':qt.isoformat(),
        'kickoff_utc':ko.isoformat(),'AH_line_home':line,'AH_home_odds':ho,'AH_away_odds':ao,
        'FT_home':int(m['hg']),'FT_away':int(m['ag']),'raw_body_sha256':body_sha,
        'quote_event_time_is_not_HTTP_receipt_time':True,'candidate_selections':checks})

# Re-read all frozen members independently; preserve any ambiguous legacy
# direction while still verifying the Crown quote, FT and frozen cashflow.
members=[json.loads(x) for x in (WORK/'m8_foundation_20261115/historical_membership.jsonl').open()]
baseline_audit=[];baseline_fail=collections.Counter()
for member in members:
    fid=str(member['fid']);source=loc.get(fid)
    if not source or not pathlib.Path(source['path']).is_file():baseline_fail['raw_body_missing']+=1;continue
    raw=pathlib.Path(source['path']).read_bytes();body_sha=sha(raw)
    if source.get('sha') and source['sha']!=body_sha:baseline_fail['raw_sha_mismatch']+=1;continue
    try:data=json.loads(raw).get('data')
    except Exception:baseline_fail['bad_json']+=1;continue
    matches=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
    matches=[x for x in matches if str(x.get('id'))==fid]
    if len(matches)!=1:baseline_fail['raw_fid_cardinality']+=1;continue
    m=matches[0];ko=dateparse(m['start'])
    if str(m.get('l_id'))!=str(member['league']) or ko.date().isoformat()!=str(member['date'])[:10]:
        baseline_fail['identity_date_mismatch']+=1;continue
    crown=[x for x in m.get('bookmakers',[]) if str(x.get('slug','')).lower()=='crown']
    if not crown:baseline_fail['Crown_missing']+=1;continue
    q=[]
    for x in crown[0].get('asian_list') or []:
        try:
            t=dateparse(x[4]);ln,ho,ao=map(float,x[1:4])
            if t<ko and t<=ko-dt.timedelta(hours=1) and min(ho,ao)>1 and abs(ln*4-round(ln*4))<1e-8:q.append((t,ln,ho,ao))
        except Exception:pass
    if not q:baseline_fail['no_valid_Crown_quote_at_T1']+=1;continue
    q.sort(key=lambda z:z[0]);qt,line,ho,ao=q[-1]
    hg,ag=int(m['hg']),int(m['ag']);home_u=settle(line,'home',hg,ag,ho);away_u=settle(line,'away',hg,ag,ao);target=float(member['pnl'])
    sides=[s for s,u in (('home',home_u),('away',away_u)) if abs(u-target)<1e-8]
    if not sides:baseline_fail['frozen_PnL_not_reproduced_by_either_side']+=1;continue
    baseline_audit.append({'fid':fid,'group':member['cohort'],'year':member['year'],'date':member['date'],
        'league':member['league'],'home_team_id':str(m.get('h_id') or ''),'away_team_id':str(m.get('a_id') or ''),
        'kickoff_utc':ko.isoformat(),'Crown_quote_event_utc':qt.isoformat(),'AH_line_home':line,
        'AH_home_odds':ho,'AH_away_odds':ao,'FT_home':hg,'FT_away':ag,'frozen_PnL':target,
        'independent_home_U':home_u,'independent_away_U':away_u,'matching_frozen_PnL_sides':sides,
        'home_settlement_class':settle_class(line,'home',hg,ag),'away_settlement_class':settle_class(line,'away',hg,ag),
        'side_uniquely_reconstructed':len(sides)==1,'raw_body_sha256':body_sha,
        'quote_event_time_is_not_HTTP_receipt_time':True})

summary={'study':'M8_FROZEN_EIGHT_BOUNDARY_RAW_CROWN_INDEPENDENT_AUDIT_20261119',
    'predicted_rows':len(pred),'predicted_unique_FIDs':len(pred_by),'raw_Crown_rows_verified':len(audit),
    'failures':dict(fails),'settlement_checks':sum(map(len,(x['candidate_selections'] for x in audit))),
    'all_verified_selections_match':not any('mismatch' in k for k in fails),
    'frozen_member_n':len(members),'frozen_members_raw_quote_FT_and_PnL_reproduced_n':len(baseline_audit),
    'frozen_member_failures':dict(baseline_fail),'frozen_member_unique_original_side_n':sum(x['side_uniquely_reconstructed'] for x in baseline_audit),
    'method':'Re-read stored raw Crown response body, verify body SHA when indexed, fixture ID/league/teams/kickoff/FT, take last Crown asian_list event at or before T-1, independently settle whole/quarter Asian handicap. Source event time is not HTTP receipt time; historical event replay only.'}
(OUT/'independent_raw_crown_settlement_audit_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with gzip.open(OUT/'independent_raw_crown_settlement_audit_20261119.jsonl.gz','wt',encoding='utf-8') as f:
    for r in audit:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
with gzip.open(OUT/'independent_frozen_member_raw_quote_audit_20261119.jsonl.gz','wt',encoding='utf-8') as f:
    for r in baseline_audit:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
