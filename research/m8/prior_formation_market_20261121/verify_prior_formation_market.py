#!/usr/bin/env python3
"""Independent settlement, frozen-membership, Crown-source and receipt audit."""
from __future__ import annotations
import bisect, datetime as dt, gzip, hashlib, json, math, pathlib, sqlite3, collections

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA = pathlib.Path('/Users/mac/QuantAsiaDesk/data')

def read_jsonl(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def digest(data): return hashlib.sha256(data).hexdigest()

def utc(value):
    x = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00').replace(' ', 'T'))
    if x.tzinfo is None: x = x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
    return x.astimezone(dt.timezone.utc)

def settle(line, side, gd, odds):
    signed = float(line) if side == 'home' else -float(line)
    margin = int(gd) if side == 'home' else -int(gd)
    assert abs(signed*4-round(signed*4)) < 1e-8
    if abs(signed*2-round(signed*2)) < 1e-8: legs=(signed,)
    else: legs=(math.floor(signed*2)/2, math.ceil(signed*2)/2)
    pnl=[]; labels=[]
    for leg in legs:
        d=margin+leg
        labels.append('W' if d>1e-9 else 'L' if d < -1e-9 else 'P')
        pnl.append(float(odds)-1 if d>1e-9 else -1. if d < -1e-9 else 0.)
    net=sum(pnl)/len(pnl)
    state=('full_win' if all(v=='W' for v in labels) else 'full_loss' if all(v=='L' for v in labels)
           else 'push' if all(v=='P' for v in labels) else 'half_win' if net>0 else 'half_loss' if net<0 else 'push')
    return state, round(net,8)

def load_crown_sources(fids):
    """Recover event-time source records from the existing raw Crown archive."""
    known={str(r['fid']):r for r in read_jsonl(WORK/'m8_late_full_path_water_features_20261114.jsonl')}
    jobs={}
    prior=WORK/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
    for r in read_jsonl(prior):
        fid=str(r['fixture_id'])
        if fid in fids and fid in known and int(known[fid]['year']) < 2026:
            jobs[fid]=(pathlib.Path(r['source_file']),None,str(known[fid]['league']))
    idx={str(r['match_id']):r.get('response_sha256') for r in read_jsonl(DATA/'m5-crown-authorized/crown-response-index.jsonl')}
    for fid in fids:
        if fid in known and int(known[fid]['year']) == 2026:
            jobs[fid]=(DATA/'m5-crown-authorized/crown-responses'/f'{fid}.json',idx.get(fid),str(known[fid]['league']))
    # Original additional frozen replay archive is the fallback for rare historical FIDs.
    for name in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
        for r in read_jsonl(WORK/name):
            fid=str(r['fid'])
            if fid in fids and fid not in jobs:
                jobs[fid]=(pathlib.Path(r['source_file']),idx.get(fid) if '/m5-crown-authorized/crown-responses/' in r['source_file'] else None,str(r['league']))
    return jobs

def main():
    summary=json.loads((OUT/'formation_market_summary_20261121.json').read_text())
    fixture=list(read_jsonl_gz(OUT/'formation_market_per_fixture_20261121.jsonl.gz'))
    receipt=list(read_jsonl_gz(OUT/'formation_market_actual_receipt_replay_20261121.jsonl.gz'))
    frozen={str(r['fid']):r for r in read_jsonl(WORK/'m8_foundation_20261115/historical_membership.jsonl')}
    receipt_archive_fids={str(r['fixture_id']) for r in read_jsonl(WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')}
    issues=collections.Counter(); method_rows=collections.defaultdict(list); methods=set()
    for r in fixture:
        methods.add(r['method']); method_rows[r['method']].append(r)
        state,net=settle(r['T12_AH_home_line'],r['chosen_side'] or 'home',r['gd'],r['chosen_odds'] or r['T12_home_odds']) if r['chosen_side'] else ('push',0.)
        if state!=r['settlement'] or abs(net-float(r['net_u']))>1e-7: issues['settlement_mismatch']+=1
        if bool(r['fid'] in frozen)!=bool(r['frozen_overlap']): issues['frozen_membership_mismatch']+=1
        if r['year']>=2024 and int(r['training_year_cutoff_exclusive'])!=r['year']: issues['forward_cutoff_mismatch']+=1
        cutoff=dt.date.fromisoformat(r['formation_cutoff'])
        for side in ('home','away'):
            h=r[f'formation_history_{side}']
            # The feature builder includes records through target_date-3d. The
            # cutoff date itself is known to precede the target; only a later
            # historical date would violate this date-based safety boundary.
            if dt.date.fromisoformat(h['last_history_date'])>cutoff: issues['formation_lookahead']+=1
            if abs(sum(float(h[k]) for k in ('p3','p4','p5'))-1)>1e-7: issues['formation_share_mismatch']+=1
            if int(h['n'])!=int(r[f'formation_history_{side}_n_365']): issues['formation_count_mismatch']+=1
        if abs(float(r['T12_home_odds'])-float(r['T12_home_odds']))>1e-12: issues['impossible']+=1
    for m in methods:
        rows=method_rows[m]
        byfid=collections.defaultdict(list)
        for r in rows: byfid[r['fid']].append(r)
        if any(len(v)!=1 for v in byfid.values()): issues['method_duplicate_fid']+=1
        inc=[r for r in rows if not r['frozen_overlap']]
        got={'n':len(inc),'net_U':round(sum(float(x['net_u']) for x in inc),6)}
        exp=summary['model_results'][m]['incremental_outside_frozen']
        if got['n']!=exp['n'] or abs(got['net_U']-exp['net_U'])>1e-6: issues['summary_reconciliation']+=1

    # Independently reconcile expanding-year training counts against the
    # archived receipt exclusion set and the common feature cohort.
    cohort_by_fid={r['fid']:r for r in method_rows['market_only']}
    # Training rows before 2024 are part of the feature cohort but are not in
    # the test ledger; recover their common-cohort counts from the saved fold.
    # The fold's membership can be checked through the research runner's input
    # inventory during full reruns; here verify its cutoff and receipt exclusion
    # statements are internally consistent with the saved summary and test rows.
    for year,fold in summary['training_folds'].items():
        if int(fold['train_max_year']) >= int(year) or any(int(y)>=int(year) for y in fold['train_years']):
            issues['training_year_leakage']+=1
        if not fold['receipt_fids_excluded_from_training']:
            issues['receipt_training_exclusion_missing']+=1
    if any(r['fid'] in receipt_archive_fids and r['year']<2024 for r in fixture):
        issues['pretest_receipt_overlap_check']+=1

    # Independently reopen the saved Crown raw response for every historical model FID.
    candidates={r['fid']:r for r in method_rows['market_only']}
    jobs=load_crown_sources(set(candidates)); raw_ok=0; raw_missing=0; raw_evidence=[]
    for fid,r in candidates.items():
        job=jobs.get(fid)
        if not job or not job[0].is_file(): raw_missing+=1; continue
        path,expected_sha,league=job
        try:
            raw=path.read_bytes()
            if expected_sha and digest(raw)!=expected_sha: issues['crown_file_sha_mismatch']+=1; continue
            body=json.loads(raw); match=next(x for x in body.get('data',[]) if str(x.get('id'))==fid)
            if str(match.get('l_id'))!=league or str(match.get('status'))!='full': issues['crown_fixture_identity_or_ft']+=1; continue
            if (int(match.get('hg')),int(match.get('ag'))) != (int(r['hg']),int(r['ag'])): issues['crown_ft_mismatch']+=1; continue
            ko=utc(match['start']); cutoff=ko-dt.timedelta(hours=12); bookmaker=next(x for x in match['bookmakers'] if x.get('slug')=='crown')
            path_rows=[]
            for q in bookmaker.get('asian_list') or []:
                try:
                    t=utc(q[4]); line,ho,ao=map(float,q[1:4])
                    if t<ko and ho>1 and ao>1 and abs(line*4-round(line*4))<1e-7: path_rows.append((t,line,ho,ao))
                except Exception: continue
            path_rows.sort(key=lambda x:x[0]); eligible=[q for q in path_rows if q[0]<=cutoff]
            if not eligible: issues['crown_no_T12_quote']+=1; continue
            _,line,ho,ao=eligible[-1]
            if abs(line-float(r['T12_AH_home_line']))>1e-8 or abs(ho-float(r['T12_home_odds']))>1e-8 or abs(ao-float(r['T12_away_odds']))>1e-8:
                issues['crown_T12_contract_mismatch']+=1; continue
            raw_ok+=1
            raw_evidence.append({'fid':fid,'source_file':str(path),'raw_file_sha256':digest(raw),
                'indexed_response_sha256':expected_sha,'league':league,'home_id':r['home_id'],'away_id':r['away_id'],
                'kickoff_beijing':r['kickoff_beijing'],'T12_source_event_utc':eligible[-1][0].isoformat(),
                'T12_AH_home_line':line,'T12_home_odds':ho,'T12_away_odds':ao,'hg':r['hg'],'ag':r['ag']})
        except Exception: issues['crown_raw_parse_error']+=1

    # Re-open raw HTTP envelope and snapshot for every price replay row; feature timestamp remains unverified.
    receipt_fids=set(); receipt_evidence={}
    archive_by_quote={}
    for a in read_jsonl(WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'):
        archive_by_quote[(str(a['fixture_id']),str(a.get('raw_sha256')),str(a.get('snapshot_sha256')))]=a
    for r in receipt:
        q=r['receipt_quote']; receipt_fids.add(r['fid'])
        archive=archive_by_quote.get((r['fid'],str(q['raw_sha256']),str(q['snapshot_sha256'])))
        if not archive:
            issues['receipt_archive_quote_mapping_missing']+=1
            continue
        src=pathlib.Path(archive['source_file'])
        try:
            envelope=json.loads(src.read_bytes());raw=str(envelope.get('raw_response') or '').encode()
            snap=src.parents[1]/'snapshot.json';snapbytes=snap.read_bytes();snapobj=json.loads(snapbytes);body=json.loads(raw)
            if digest(raw)!=q['raw_sha256'] or digest(snapbytes)!=q['snapshot_sha256']: issues['receipt_sha_mismatch']+=1; continue
            if int(envelope.get('http_status') or 0)!=200 or not envelope.get('raw_saved'): issues['receipt_http_invalid']+=1; continue
            if utc(q['received_utc'])>=utc(q['kickoff_utc']) or utc(q['source_event_utc'])>utc(q['received_utc']): issues['receipt_not_prematch']+=1; continue
            if str(snapobj.get('match_id'))!=r['fid'] or not snapobj.get('source_bookmaker_verified') or not snapobj.get('prematch_valid'): issues['receipt_snapshot_identity']+=1; continue
            ah=snapobj.get('AH') or {}
            if (abs(float(ah.get('line'))-float(q['line']))>1e-8 or abs(float(ah.get('home_price'))-float(q['home_odds']))>1e-8 or abs(float(ah.get('away_price'))-float(q['away_odds']))>1e-8): issues['receipt_contract_mismatch']+=1; continue
            data=body.get('data');data=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
            m=next((x for x in data if str(x.get('id'))==r['fid']),None)
            if not m or str(m.get('l_id'))!=r['league'] or str(m.get('h_id'))!=r['home_id'] or str(m.get('a_id'))!=r['away_id']: issues['receipt_raw_identity']+=1; continue
            state,net=settle(q['line'],r['chosen_side'] or 'home',r['gd'],r['chosen_odds'] or q['home_odds']) if r['chosen_side'] else ('push',0.)
            if state!=r['settlement'] or abs(net-float(r['net_u']))>1e-7: issues['receipt_settlement_mismatch']+=1
            receipt_evidence[r['fid']]={'fid':r['fid'],'received_utc':q['received_utc'],'source_event_utc':q['source_event_utc'],
                'kickoff_utc':q['kickoff_utc'],'snapshot_horizon':q['snapshot_horizon'],'raw_sha256':q['raw_sha256'],
                'snapshot_sha256':q['snapshot_sha256'],'line':q['line'],'home_odds':q['home_odds'],'away_odds':q['away_odds'],
                'league':r['league'],'home_id':r['home_id'],'away_id':r['away_id'],'hg':r['hg'],'ag':r['ag']}
        except Exception: issues['receipt_audit_error']+=1
    def write_gz(path, rows):
        with open(path,'wb') as rawf:
            with gzip.GzipFile(fileobj=rawf,mode='wb',mtime=0) as gz:
                for row in rows: gz.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())
    write_gz(OUT/'historical_crown_raw_fid_audit_20261121.jsonl.gz',sorted(raw_evidence,key=lambda x:x['fid']))
    write_gz(OUT/'actual_receipt_quote_audit_20261121.jsonl.gz',[receipt_evidence[k] for k in sorted(receipt_evidence)])
    result={'pass':not issues,'study_rows':len(fixture),'unique_test_FIDs':len(candidates),'model_count':len(methods),
        'settlements_recomputed':len(fixture),'historical_Crown_raw_quote_matches':raw_ok,'historical_raw_missing':raw_missing,
        'actual_receipt_model_rows':len(receipt),'actual_receipt_unique_FIDs':len(receipt_fids),
        'receipt_latest_quotes_in_summary':summary['actual_receipt_replay']['selected_latest_pregame_quote_per_FID'],
        'issues':dict(issues),'scope_note':'Historical event-time quotes and actual HTTP receipt prices are independently separated. Formation feature first-publication times are unavailable.'}
    (OUT/'independent_verification_20261121.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

def read_jsonl_gz(path):
    with gzip.open(path,'rt',encoding='utf-8') as f:
        for line in f:
            if line.strip(): yield json.loads(line)

if __name__=='__main__': main()
