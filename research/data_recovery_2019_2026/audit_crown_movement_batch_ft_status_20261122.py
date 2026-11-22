#!/usr/bin/env python3
"""Audit whether newly retrieved Crown movement bodies add trusted FT evidence.

This is an offline, read-only source reconciliation. Numeric/unknown TotalCorner
status values are not interpreted as full-time without a documented mapping.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, pathlib, sqlite3

ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'research/data_recovery_2019_2026'
FT_QUEUE=OUT/'unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz'
INVENTORY=OUT/'fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz'
LOG=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/crown_quote_recovery/queues_20261122/movement_collection.log.jsonl')
DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
RUN_START='2026-11-21T23:18:38.032113Z'
STAMP='20261122T0433Z'
AS_OF='2026-11-22T04:33:45.154611Z'

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def dt_utc(s:str)->dt.datetime:
    x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
    if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
    return x.astimezone(dt.timezone.utc)
def main()->None:
    missing={}
    with gzip.open(FT_QUEUE,'rt',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                x=json.loads(line);missing[str(x['fid'])]=x
    inventory={}
    with gzip.open(INVENTORY,'rt',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                x=json.loads(line);inventory[str(x['fid'])]=x
    latest={}
    with LOG.open(encoding='utf-8') as f:
        for line in f:
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            received=r.get('response_received_at_utc') or ''
            if (r.get('fixture_id') and r.get('status') in {'SAVED','NO_CROWN_AH_QUOTES'}
                    and RUN_START<=received<=AS_OF):
                latest[str(r['fixture_id'])]=r
    batch={fid:r for fid,r in latest.items()
           if r.get('response_received_at_utc','')>=RUN_START}
    candidates=sorted(set(batch)&set(missing));batch_ids=sorted(batch)
    db=sqlite3.connect(f'file:{DB}?mode=ro',uri=True);db.row_factory=sqlite3.Row
    rows=[];issues=collections.Counter();capture_map={}
    for start in range(0,len(batch_ids),600):
        chunk=batch_ids[start:start+600];marks=','.join('?' for _ in chunk)
        for c in db.execute(f"""SELECT fixture_id,response_sha256,source_file,response_received_at_utc,
                status,quote_count FROM capture WHERE data_layer='movement'
                AND capture_mode='historical' AND fixture_id IN ({marks})""",chunk):
            capture_map.setdefault(str(c['fixture_id']),[]).append(dict(c))
    for fid in candidates:
        logrow=batch[fid]; inv=missing[fid]
        receive=logrow.get('response_received_at_utc')
        cap=next((c for c in capture_map.get(fid,[])
                  if c['response_received_at_utc']==receive),None)
        row={'fid':fid,'provider_league_id':str(inv['provider_league_id']),
             'inventory_kickoff_utc':inv['kickoff_utc'],
             'collector_status':logrow.get('status'),'quote_count':int(logrow.get('quote_count') or 0),
             'response_received_at_utc':receive,'response_sha256':None,'source_file':None,
             'raw_fixture_status':None,'raw_home_goals':None,'raw_away_goals':None,
             'identity_exact':False,'classification':'capture_not_found'}
        canonical=inventory.get(fid,{})
        canonical_statuses=[]
        for sr in canonical.get('totalcorner_page_records',[]):
            try:
                if (str(sr.get('provider_league_id'))==str(inv['provider_league_id'])
                    and str(sr.get('home_id'))==str((inv.get('evidence_records') or [{}])[0].get('home_id'))
                    and str(sr.get('away_id'))==str((inv.get('evidence_records') or [{}])[0].get('away_id'))
                    and dt_utc(sr['kickoff_utc'])==dt_utc(inv['kickoff_utc'])
                    and sr.get('status') is not None):canonical_statuses.append(str(sr['status']))
            except Exception:continue
        row['exact_totalcorner_page_statuses']=sorted(set(canonical_statuses))
        if cap is None:
            issues['capture_not_found']+=1;rows.append(row);continue
        row['response_sha256']=cap['response_sha256'];row['source_file']=cap['source_file']
        try:
            body_bytes=pathlib.Path(cap['source_file']).read_bytes()
            digest=sha(body_bytes)
            if digest!=cap['response_sha256']:
                row['classification']='raw_sha_mismatch';issues['raw_sha_mismatch']+=1;rows.append(row);continue
            body=json.loads(body_bytes)
            fixtures=[x for x in body.get('data',[]) if str(x.get('id'))==fid]
            if len(fixtures)!=1:
                row['classification']='raw_fixture_id_not_unique';issues['raw_fixture_id_not_unique']+=1;rows.append(row);continue
            fx=fixtures[0];ev=inv.get('evidence_records') or []
            identity_set={(str(e.get('provider_league_id') or inv['provider_league_id']),
                           str(e.get('home_id') or ''),str(e.get('away_id') or ''),
                           str(e.get('kickoff_utc') or inv['kickoff_utc'])) for e in ev}
            identity=(str(fx.get('l_id'))==str(inv['provider_league_id'])
                      and len(identity_set)<=1
                      and (not ev or str(fx.get('h_id'))==next(iter(identity_set))[1])
                      and (not ev or str(fx.get('a_id'))==next(iter(identity_set))[2])
                      and dt_utc(fx['start'])==dt_utc(inv['kickoff_utc']))
            row.update({'raw_fixture_status':fx.get('status'),
                        'raw_home_goals':fx.get('hg'),'raw_away_goals':fx.get('ag'),
                        'raw_home_id':str(fx.get('h_id') or ''),'raw_away_id':str(fx.get('a_id') or ''),
                        'raw_home':fx.get('h'),'raw_away':fx.get('a'),
                        'identity_exact':identity})
            if not identity:
                row['classification']='identity_mismatch';issues['identity_mismatch']+=1
            elif str(fx.get('status')).lower()=='full' and str(fx.get('hg','')).isdigit() and str(fx.get('ag','')).isdigit():
                row['classification']='explicit_full_exact_identity';issues[row['classification']]+=1
            elif str(fx.get('status')).lower()=='half':
                row['classification']='explicit_half_exact_identity';issues[row['classification']]+=1
            elif fx.get('status') is None:
                row['classification']='status_missing_exact_identity';issues[row['classification']]+=1
            else:
                row['classification']='unmapped_status_exact_identity';issues[row['classification']]+=1
        except Exception as e:
            row['classification']='audit_error_'+type(e).__name__;issues[row['classification']]+=1
        rows.append(row)
    # Empirical exact-FID/identity status crosswalk for all this batch's raw
    # responses; this demonstrates whether a raw numeric code means "full".
    status_pairs=collections.Counter();crosswalk_issues=collections.Counter();crosswalk_n=0
    for fid in batch_ids:
        logrow=batch[fid];cap=next((c for c in capture_map.get(fid,[])
                    if c['response_received_at_utc']==logrow.get('response_received_at_utc')),None)
        srcrecs=inventory.get(fid,{}).get('totalcorner_page_records',[])
        if cap is None or not srcrecs:continue
        try:
            body_bytes=pathlib.Path(cap['source_file']).read_bytes()
            if sha(body_bytes)!=cap['response_sha256']:
                crosswalk_issues['raw_sha_mismatch']+=1;continue
            fs=[x for x in json.loads(body_bytes).get('data',[]) if str(x.get('id'))==fid]
            if len(fs)!=1:crosswalk_issues['raw_fid_mismatch']+=1;continue
            fx=fs[0]; ko=dt_utc(fx['start']); exact_statuses=set()
            for sr in srcrecs:
                try:
                    if (str(sr.get('provider_league_id'))==str(inventory[fid]['provider_league_id'])
                        and str(sr.get('home_id'))==str(fx.get('h_id'))
                        and str(sr.get('away_id'))==str(fx.get('a_id'))
                        and dt_utc(sr['kickoff_utc'])==ko and sr.get('status') is not None):
                        exact_statuses.add(str(sr['status']))
                except Exception:continue
            for st in exact_statuses:status_pairs[(str(fx.get('status')),st)]+=1
            if exact_statuses:crosswalk_n+=1
        except Exception as e:crosswalk_issues['error_'+type(e).__name__]+=1
    db.close()
    statuses=collections.Counter(str(r['raw_fixture_status']) for r in rows)
    result={'study':'READ_ONLY_CROWN_MOVEMENT_RAW_FT_STATUS_REUSE_AUDIT',
      'as_of_utc':AS_OF,'run_start_utc':RUN_START,
      'unverified_ft_candidate_input_sha256':sha(FT_QUEUE.read_bytes()),
      'schedule_inventory_input_sha256':sha(INVENTORY.read_bytes()),
      'ft_unresolved_input_fids':len(missing),'batch_terminal_unique_fids':len(batch),
      'batch_fids_intersecting_unresolved_ft_queue':len(candidates),
      'audited_rows':len(rows),'exact_identity_rows':sum(r['identity_exact'] for r in rows),
      'raw_status_counts':dict(statuses),'classifications':dict(issues),
      'exact_identity_source_status_crosswalk_rows':crosswalk_n,
      'raw_crown_status_vs_totalcorner_page_status':{f'{a}|{b}':n for (a,b),n in sorted(status_pairs.items())},
      'crosswalk_issues':dict(crosswalk_issues),
      'explicit_full_trusted_new_ft':issues['explicit_full_exact_identity'],
      'note':'Raw numeric status values are preserved and not mapped to full-time; no score was merged into the verified FT inventory.',
      'network_requests':0,'database_writes':0,
      'pass':len(rows)==len(candidates) and not any(k.startswith('audit_error_') or k in {'capture_not_found','raw_sha_mismatch','raw_fixture_id_not_unique','identity_mismatch'} for k in issues)}
    result['pass']=result['pass'] and not crosswalk_issues
    (OUT/f'crown_movement_batch_ft_status_audit_{STAMP}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with gzip.open(OUT/f'crown_movement_batch_ft_candidates_{STAMP}.jsonl.gz','wt',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
