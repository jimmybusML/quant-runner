#!/usr/bin/env python3
"""Reconcile and materialize two completed TotalCorner historical schedule batches.

Read-only for private raw pages and Crown SQLite. Does not issue network calls,
write production data, inspect strategies, or calculate betting performance.
"""
from __future__ import annotations
import collections, csv, datetime as dt, gzip, hashlib, io, json, pathlib, re, sqlite3

REPO=pathlib.Path(__file__).resolve().parents[2]
OUT=REPO/'research/data_recovery_2019_2026'
PRIVATE=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/totalcorner_schedule_recovery')
RAW=PRIVATE/'raw'; DIAG=PRIVATE.parent/'totalcorner_schedule_diagnostics'
SHARED=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
PROG15=PRIVATE/'progress_before_m7_mapped_targets_20261122.json'
PROG38=PRIVATE/'progress.json'
LEDGER=PRIVATE/'fixtures_2019_2026.jsonl'
REQUESTS=PRIVATE/'requests.jsonl'
TARGET15=OUT/'unresolved_schedule_competition_candidates_20261121.json'
TARGET38=OUT/'m7_named_competition_schedule_targets_20261122.json'
BASE_INV=OUT/'fixture_inventory_2019_2026.jsonl.gz'
AUDIT38=OUT/'completed_schedule_league_year_coverage_2019_2026.json'
OLD120=OUT/'supplemental_totalcorner_league15_schedule_20261121.jsonl.gz'
OLD_SOURCE=pathlib.Path('/Users/mac/QuantAsiaDesk/repos/runner/research/shared_history/totalcorner/league-15.jsonl')
OLD_IDENTITY=PRIVATE/'identity_conflicts.jsonl'
UTC=dt.timezone.utc

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:pathlib.Path)->str:return sha_bytes(p.read_bytes())
def read_jsonl(p:pathlib.Path):
    with p.open(encoding='utf-8') as f:
        for ln in f:
            try:yield json.loads(ln)
            except json.JSONDecodeError:continue

def read_gzip_jsonl(p:pathlib.Path):
    with gzip.open(p,'rt',encoding='utf-8') as f:
        for ln in f:
            try:yield json.loads(ln)
            except json.JSONDecodeError:continue

def write_gzip_jsonl(path:pathlib.Path, rows):
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
            with io.TextIOWrapper(gz,encoding='utf-8') as txt:
                for r in rows:txt.write(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')

def page_matches(body):
    d=body.get('data') or body.get('payload',{}).get('data') or {}
    return d if isinstance(d,list) else d.get('matches') or []
def response_league(body):
    d=body.get('data') or body.get('payload',{}).get('data') or {}
    return (d.get('league') or {}) if isinstance(d,dict) else {}
def parse_dt(v):
    if not v:return None
    try:
        x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00'))
        return x.astimezone(UTC) if x.tzinfo else None
    except Exception:return None

def normalize_from_raw(match,lid,name,page,digest,received,collector):
    row=collector.normalize_fixture(lid,name,page,match,{'response_sha256':digest,'response_received_at_utc':received})
    if row is None:return None
    row['season_raw']=match.get('season')
    row['season_status']='provided_by_source' if match.get('season') not in (None,'') else 'not_provided_by_source'
    row['capture_mode']='historical'
    row['record_kind']='schedule_and_result_snapshot'
    row['verified_full_time_score']=(str(row.get('status_raw') or '').lower()=='full' and all(re.fullmatch(r'\d+',str(row.get(k) or '')) for k in ('home_goals_raw','away_goals_raw')))
    row['utc_calendar_year']=int(row['kickoff_utc'][:4]) if row.get('kickoff_utc') else None
    return row

def load_page_index(ids, run_start, run_end, ledger_rows, request_rows):
    expected=collections.defaultdict(set);received={};page_req=collections.defaultdict(list)
    for r in ledger_rows:
        lid=str(r.get('provider_league_id'));page=int(r.get('source_page') or 0)
        if lid in ids and page and r.get('source_page_response_sha256'):
            expected[(lid,page)].add(str(r['source_page_response_sha256']))
    for r in request_rows:
        lid=str(r.get('league_id',''));page=int(r.get('page') or 0)
        if lid not in ids or not page:continue
        t=parse_dt(r.get('response_received_at_utc')) or parse_dt(r.get('request_started_at_utc'))
        if t and run_start<=t<=run_end and r.get('event')=='page_succeeded' and r.get('success'):
            page_req[(lid,page)].append(r)
    return expected,page_req

def locate_page(lid,page,digest,reqs):
    paths=[]
    for r in reqs:
        if r.get('response_sha256')==digest and r.get('raw_file'):paths.append(pathlib.Path(r['raw_file']))
    paths.extend([RAW/f'league-{lid}-page-{page}-{digest}.json',DIAG/f'league-{lid}-page-{page}-{digest}.json'])
    paths.extend([SHARED/lid/f'page-{page}.raw.json',SHARED/lid/f'page-{page}.json'])
    seen=set()
    for p in paths:
        if p in seen or not p.is_file():continue
        seen.add(p)
        try:
            b=p.read_bytes()
            if sha_bytes(b)==digest:return p,b
        except OSError:pass
    # For cached pages without ledger rows, find exact league/page response hashes
    # under all existing raw schedule caches and verify page identity below.
    for folder in (RAW,DIAG):
        for p in folder.glob(f'league-{lid}-page-{page}-*.json'):
            if p.name.endswith('.meta.json') or p.suffix!='.json':continue
            try:
                b=p.read_bytes()
                if sha_bytes(b)==digest:return p,b
            except OSError:pass
    return None,None

def build_batch15(collector, progress, targets, ledger_rows, request_rows):
    target_by_id={str(x['provider_league_id']):x for x in targets['competitions']}
    ids=set(progress['targets']);assert ids==set(target_by_id),(ids^set(target_by_id))
    start=parse_dt(progress['started_at_utc']);end=parse_dt(progress['finished_at_utc'])
    expected,reqidx=load_page_index(ids,start,end,ledger_rows,request_rows)
    rows_by_fid=collections.defaultdict(list);pages=[];issues=collections.Counter();page_count=0;source_pages=set();row_hash_verified=0;ledger_by_pair={(str(r.get('provider_league_id')),str(r.get('fid'))):r for r in ledger_rows if str(r.get('provider_league_id')) in ids}
    for lid,st in sorted(progress['targets'].items(),key=lambda kv:int(kv[0])):
        assert st.get('pagination_status')=='complete_to_2019_cutoff_or_provider_end', (lid,st.get('pagination_status'))
        assert not st.get('failed_pages'), (lid,st.get('failed_pages'))
        last=int(st.get('latest_page') or st.get('pages_read') or 0)
        assert last==int(st.get('pages_read') or 0),(lid,last,st.get('pages_read'))
        name=target_by_id[lid]['league_name']
        for page in range(1,last+1):
            candidates=sorted(expected.get((lid,page),set()))
            reqs=reqidx.get((lid,page),[])
            if len(candidates)>1:issues['multiple_ledger_page_shas']+=1
            digest=candidates[0] if candidates else None
            if not digest and reqs:
                digest=sorted(reqs,key=lambda r:r.get('response_received_at_utc') or '')[-1].get('response_sha256')
            if not digest:
                # A cached first page may have no newly normalized row. Resolve
                # its SHA only from the content-addressed local cache.
                found=[]
                for folder in (RAW,DIAG):found.extend(folder.glob(f'league-{lid}-page-{page}-*.json'))
                for p in (SHARED/lid/f'page-{page}.raw.json',SHARED/lid/f'page-{page}.json'):
                    if p.is_file():found.append(p)
                valid=[]
                for p in found:
                    if p.name.endswith('.meta.json') or p.suffix!='.json':continue
                    try:
                        b=p.read_bytes();body=json.loads(b)
                        if body.get('success',body.get('status')) not in (1,'1',True):continue
                        pag=body.get('pagination') or {}
                        if int(pag.get('current') or pag.get('page') or page)!=page:continue
                        lg=response_league(body)
                        if lg.get('league_id') and str(lg['league_id'])!=lid:continue
                        valid.append((sha_bytes(b),p,b))
                    except Exception:continue
                valid=sorted({x[0]:x for x in valid}.values(),key=lambda x:x[0])
                if len(valid)!=1:
                    issues['cached_page_missing_or_ambiguous']+=1;pages.append({'league_id':lid,'page':page,'status':'unverified_cached_page','candidate_shas':[x[0] for x in valid]});continue
                digest,p,b=valid[0]
            else:p,b=locate_page(lid,page,digest,reqs)
            if p is None:
                issues['raw_page_missing_or_sha_mismatch']+=1;pages.append({'league_id':lid,'page':page,'sha256':digest,'status':'raw_missing'});continue
            try:body=json.loads(b)
            except Exception:issues['raw_page_json_error']+=1;continue
            if body.get('success',body.get('status')) not in (1,'1',True):issues['provider_page_not_success']+=1;continue
            lg=response_league(body);reported=str(lg.get('league_id') or '')
            if reported and reported!=lid:issues['top_level_league_mismatch']+=1;continue
            matches=page_matches(body);row_lids={str(m.get('l_id')) for m in matches if m.get('l_id') is not None}
            if row_lids and row_lids!={lid}:issues['row_league_mismatch']+=1;continue
            page_count+=1;source_pages.add(digest)
            if reqs:
                received=sorted(reqs,key=lambda r:r.get('response_received_at_utc') or '')[-1].get('response_received_at_utc')
            else:
                meta=p.with_name(p.stem+'.meta.json')
                try:received=json.loads(meta.read_text()).get('response_received_at_utc') if meta.exists() else None
                except Exception:received=None
            pag=body.get('pagination') or {}
            if pag.get('pages') and int(pag['pages'])!=int(st.get('reported_pages') or pag['pages']):issues['reported_page_count_changed']+=1
            selected=0
            for m in matches:
                norm=normalize_from_raw(m,lid,name,page,digest,received,collector)
                if norm is None:continue
                selected+=1;norm['source_page_references']=[{'source_page':page,'source_page_response_sha256':digest,'response_received_at_utc':received,'local_raw_path_kind':'private_raw' if str(p).startswith(str(RAW)) else 'local_reused_cache'}];rows_by_fid[norm['fid']].append(norm)
                led=ledger_by_pair.get((lid,norm['fid']))
                if led:
                    if led.get('source_record_sha256')!=norm['source_record_sha256']:
                        issues['append_only_ledger_raw_record_mismatch']+=1
                    elif led.get('source_page_response_sha256')!=digest:
                        # A match repeated identically on two adjacent pages is
                        # retained as two page references, not treated as a
                        # conflicting source record.
                        issues['same_record_duplicate_on_other_page']+=1
                    else:row_hash_verified+=1
            pages.append({'league_id':lid,'league_name':name,'page':page,'sha256':digest,'path_kind':'private_raw' if str(p).startswith(str(RAW)) else 'local_reused_cache','response_received_at_utc':received,'match_rows_in_target_period':selected,'pagination':{'current':pag.get('current'),'pages':pag.get('pages'),'next':pag.get('next')}})
        target_fids={fid for fid,versions in rows_by_fid.items() if any(x['provider_league_id']==lid for x in versions)}
        if len(target_fids)!=int(st.get('unique_2019_2026_fids') or 0):issues['target_fid_count_mismatch']+=1
    unique=[];version_rows=[];duplicate_exact=0;fid_conflicts=[]
    for fid,versions in sorted(rows_by_fid.items()):
        grouped=collections.defaultdict(list)
        for x in versions:grouped[x['source_record_sha256']].append(x)
        bysha={}
        for record_sha,dupes in grouped.items():
            representative=sorted(dupes,key=lambda x:(x['provider_league_id'],x['source_page'],x['source_page_response_sha256']))[0]
            refs={json.dumps(ref,sort_keys=True):ref for row in dupes for ref in row.get('source_page_references',[])}
            representative['source_page_references']=[refs[k] for k in sorted(refs)]
            bysha[record_sha]=representative
        if len(versions)>len(bysha):duplicate_exact+=len(versions)-len(bysha)
        for i,x in enumerate(sorted(bysha.values(),key=lambda x:(x['provider_league_id'],x['source_page'],x['source_record_sha256'])),1):
            version_rows.append({**x,'source_version_index':i,'source_version_count':len(bysha)})
        if len(bysha)>1:
            identities={(x['provider_league_id'],x.get('kickoff_utc'),x.get('home_id'),x.get('away_id')) for x in bysha.values()}
            fid_conflicts.append({'fid':fid,'record_sha256s':sorted(bysha),'identity_tuples':[list(x) for x in sorted(identities,key=str)],'canonical_row_emitted':False})
        else:unique.append(next(iter(bysha.values())))
    return unique,version_rows,{'progress':progress,'target_count':len(progress['targets']),'fixture_count_unique':len(rows_by_fid),'canonical_unique_fids':len(unique),'raw_page_count_verified':page_count,'raw_page_digest_count':len(source_pages),'source_record_sha_checks_against_ledger':row_hash_verified,'raw_page_issues':dict(issues),'exact_duplicate_rows_deduplicated':duplicate_exact,'within_batch_fid_conflicts':fid_conflicts,'page_ledger':pages,'target_mapping_source_sha256':sha_file(TARGET15),'source_target_count':len(targets['competitions'])}

def main():
    # Import the existing collector's tested timestamp and normalization methods;
    # this module import performs no collection or writes.
    import sys
    sys.path.insert(0,str(OUT))
    import collect_supplemental_totalcorner_schedules as collector
    p15=json.loads(PROG15.read_text());p38=json.loads(PROG38.read_text())
    t15=json.loads(TARGET15.read_text());t38=json.loads(TARGET38.read_text())
    ids15={str(x['provider_league_id']) for x in t15['competitions']};ids38={str(x['provider_league_id']) for x in t38['competitions']}
    all_ledger=list(read_jsonl(LEDGER));requests=list(read_jsonl(REQUESTS))
    rows15,versions15,audit15=build_batch15(collector,p15,t15,all_ledger,requests)
    # The 38-target raw-page audit was rerun in this session. Materialize its
    # normalized rows from the append-only source ledger and assert that it
    # agrees with the SHA-bound public coverage audit.
    led38=[r for r in all_ledger if str(r.get('provider_league_id')) in ids38]
    rows38=[]
    for r in led38:
        y=int(str(r['kickoff_utc'])[:4]) if r.get('kickoff_utc') else None
        rows38.append({**r,'season_raw':None,'season_status':'not_provided_by_source','capture_mode':'historical','record_kind':'schedule_and_result_snapshot','verified_full_time_score':str(r.get('status_raw') or '').lower()=='full' and all(re.fullmatch(r'\d+',str(r.get(k) or '')) for k in ('home_goals_raw','away_goals_raw')),'utc_calendar_year':y})
    a38=json.loads(AUDIT38.read_text())
    assert len(led38)==62339 and a38['unique_schedule_fids']==62339 and not a38['raw_source_page_audit']['errors']
    assert len({r['fid'] for r in led38})==62339
    # The previous scope inventory is deduplicated by provider FID. Compare the
    # new page-derived FIDs against it without changing or replacing the source.
    baseline={}
    for r in read_gzip_jsonl(BASE_INV):baseline[str(r['fid'])]=r
    b15={str(r['fid']) for r in rows15};b38={str(r['fid']) for r in rows38};baseids=set(baseline)
    overlap15=b15&baseids;overlap38=b38&baseids;cross=b15&b38
    assert not cross and len(overlap38)==0
    # Verify the previously saved 120-row 2026 source is contained in the full
    # 15-league page replay; retain its four version conflicts for review.
    old120={str(r.get('fid',r.get('id',''))):r for r in read_gzip_jsonl(OLD120)}
    oldoverlap=set(old120)&b15
    old_conflicts=[]
    if OLD_IDENTITY.exists():
        for r in read_jsonl(OLD_IDENTITY):
            if str(r.get('provider_league_id'))=='15':old_conflicts.append(r)
    # Read-only Crown query, preserving historical/live and layer distinctions.
    dbsha=sha_file(DB);cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=30);cx.row_factory=sqlite3.Row
    quote_agg=collections.defaultdict(lambda:{'capture_fids':set(),'movement_capture_fids':set(),'summary_capture_fids':set(),'historical_capture_fids':set(),'live_capture_fids':set(),'movement_quote_fids':set(),'summary_quote_fids':set(),'quote_rows':collections.Counter(),'source_times':collections.defaultdict(set),'valid_pregame_movement_fids':set()})
    fixture_meta={}
    for group,rr in [('15',rows15),('38',rows38)]:
        for r in rr:fixture_meta[str(r['fid'])]=(group,str(r['provider_league_id']),str(r.get('utc_calendar_year') or 'UNKNOWN'))
    fids=sorted(fixture_meta)
    for st in range(0,len(fids),600):
        chunk=fids[st:st+600];marks=','.join('?' for _ in chunk)
        for c in cx.execute(f'SELECT fixture_id,data_layer,capture_mode FROM capture WHERE fixture_id IN ({marks})',chunk):
            fid=str(c['fixture_id']);group,lid,year=fixture_meta[fid];a=quote_agg[(group,lid,year)];a['capture_fids'].add(fid)
            if c['data_layer']=='movement':a['movement_capture_fids'].add(fid)
            if c['data_layer']=='summary':a['summary_capture_fids'].add(fid)
            if c['capture_mode']=='historical':a['historical_capture_fids'].add(fid)
            if c['capture_mode']=='live':a['live_capture_fids'].add(fid)
        for q in cx.execute(f'''SELECT q.fixture_id,c.data_layer,c.capture_mode,q.quote_kind,q.quote_source_at_utc,q.quote_before_kickoff,q.prospective_observation
            FROM asian_quote q JOIN capture c USING(capture_key) WHERE q.fixture_id IN ({marks})''',chunk):
            fid=str(q['fixture_id']);group,lid,year=fixture_meta[fid];a=quote_agg[(group,lid,year)];kind=str(q['quote_kind']);layer=str(q['data_layer']);a['quote_rows'][layer+':'+kind]+=1
            if q['quote_source_at_utc']:a['source_times'][layer+':'+kind].add(str(q['quote_source_at_utc']))
            if layer=='movement':a['movement_quote_fids'].add(fid)
            if layer=='summary':a['summary_quote_fids'].add(fid)
            if layer=='movement' and q['quote_before_kickoff'] and not q['prospective_observation']:
                a['valid_pregame_movement_fids'].add(fid)
    cx.close();assert sha_file(DB)==dbsha
    all_rows=rows15+rows38
    by_ly=collections.defaultdict(lambda:{'fixture_fids':set(),'verified_full_ft_fids':set(),'unverified_or_nonfull_fids':set(),'future_at_audit_fids':set(),'past_unverified_fids':set(),'season_status_counts':collections.Counter(),'status_counts':collections.Counter(),'legacy_120_overlap_fids':set()})
    now=dt.datetime.now(UTC)
    for r in all_rows:
        group='15' if str(r['provider_league_id']) in ids15 else '38';lid=str(r['provider_league_id']);year=str(r.get('utc_calendar_year') or 'UNKNOWN');key=(group,lid,year);a=by_ly[key];fid=str(r['fid']);a['fixture_fids'].add(fid);a['status_counts'][str(r.get('status_raw') or 'MISSING_STATUS')]+=1;a['season_status_counts'][r.get('season_status','not_provided_by_source')]+=1
        if r.get('verified_full_time_score'):a['verified_full_ft_fids'].add(fid)
        else:
            a['unverified_or_nonfull_fids'].add(fid);ko=parse_dt(r.get('kickoff_utc'))
            if ko and ko>now:a['future_at_audit_fids'].add(fid)
            else:a['past_unverified_fids'].add(fid)
        if group=='15' and fid in oldoverlap:a['legacy_120_overlap_fids'].add(fid)
    # Construct machine-readable league-year matrix with quote coverage.
    matrix=[]
    for key,v in sorted(by_ly.items(),key=lambda kv:(kv[0][0],int(kv[0][1]),kv[0][2])):
        group,lid,year=key;q=quote_agg[(group,lid,year)]
        matrix.append({'batch':group,'provider_league_id':lid,'provider_league_name':next((x.get('provider_league_name') for x in all_rows if str(x['provider_league_id'])==lid),None),'utc_year':year,
          'schedule_fids':len(v['fixture_fids']),'verified_full_ft_fids':len(v['verified_full_ft_fids']),'unverified_or_nonfull_fids':len(v['unverified_or_nonfull_fids']),'future_not_due_fids':len(v['future_at_audit_fids']),'past_unverified_fids':len(v['past_unverified_fids']),
          'season_provided_fids':sum(c for s,c in v['season_status_counts'].items() if s=='provided_by_source'),'season_missing_fids':v['season_status_counts'].get('not_provided_by_source',0),
          'status_counts':dict(v['status_counts']),'capture_fids':len(q['capture_fids']),'movement_capture_fids':len(q['movement_capture_fids']),'summary_capture_fids':len(q['summary_capture_fids']),'historical_capture_fids':len(q['historical_capture_fids']),'live_capture_fids':len(q['live_capture_fids']),
          'movement_quote_fids':len(q['movement_quote_fids']),'summary_quote_fids':len(q['summary_quote_fids']),'valid_pregame_movement_fids':len(q['valid_pregame_movement_fids']),'quote_rows':dict(q['quote_rows']),'distinct_source_event_times':{k:len(t) for k,t in q['source_times'].items()}})
    # Files and invariants.
    output_rows=[];seen=set()
    for r in sorted(all_rows,key=lambda x:(x.get('kickoff_utc') or '',str(x['provider_league_id']),str(x['fid']))):
        fid=str(r['fid']);assert fid not in seen,('cross_batch_or_fid_collision',fid);seen.add(fid)
        output_rows.append(r)
    assert len(rows15)==len(b15) and len(rows38)==len(b38)
    assert len(b15)==27503,(len(b15),audit15['target_count'])
    assert len(b38)==62339
    assert len(overlap15)==len(b15),(len(overlap15),len(b15))
    assert len(oldoverlap)==120,(len(oldoverlap),len(old120))
    # Export all non-full status rows; zero score placeholders remain unverified.
    unverified=[r for r in output_rows if not r.get('verified_full_time_score')]
    out_fixtures=OUT/'supplemental_totalcorner_schedules_53leagues_2019_2026.jsonl.gz'
    out_unverified=OUT/'supplemental_totalcorner_unverified_ft_53leagues_2019_2026.jsonl.gz'
    write_gzip_jsonl(out_fixtures,output_rows);write_gzip_jsonl(out_unverified,unverified)
    with (OUT/'supplemental_totalcorner_53_league_year_coverage_2019_2026.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(matrix[0]) if matrix else []);w.writeheader()
        for row in matrix:
            rr=dict(row);rr['status_counts']=json.dumps(rr['status_counts'],sort_keys=True);rr['quote_rows']=json.dumps(rr['quote_rows'],sort_keys=True);rr['distinct_source_event_times']=json.dumps(rr['distinct_source_event_times'],sort_keys=True);w.writerow(rr)
    # Per-target run completeness, page hashes and source-record verification.
    p15_summary={k:{x:st.get(x) for x in ['expected_name','pages_read','reported_pages','unique_2019_2026_fids','new_fids','conflicts','empty_pages','kickoff_missing_rows','pagination_status','failed_pages']} for k,st in p15['targets'].items()}
    total15=collections.Counter();
    for x in rows15:total15['full_ft' if x['verified_full_time_score'] else 'unverified_or_nonfull']+=1
    batchquote={}
    for group in ('15','38'):
        rr=[r for r in all_rows if (str(r['provider_league_id']) in ids15)==(group=='15')];ff={str(r['fid']) for r in rr}
        ag=collections.defaultdict(set)
        for fid in ff:
            meta=fixture_meta[fid];a=quote_agg[(meta[0],meta[1],meta[2])]
            for k in ['capture_fids','movement_capture_fids','summary_capture_fids','historical_capture_fids','live_capture_fids','movement_quote_fids','summary_quote_fids','valid_pregame_movement_fids']:ag[k]|=a[k]
        batchquote[group]={k:len(v) for k,v in ag.items()}
    result={'audit':'2019-2026 supplemental TotalCorner schedule recovery, schedule/FT/Crown coverage only; no strategy/model/backtest','as_of_utc':now.isoformat().replace('+00:00','Z'),
      'batches':{'15_competition_run':{'progress_path_private':str(PROG15),'progress_sha256':sha_file(PROG15),'started_at_utc':p15['started_at_utc'],'finished_at_utc':p15['finished_at_utc'],'network_requests':p15['network_requests'],'new_unique_fids':p15['new_unique_fids'],'identity_conflicts_reported_by_collector':p15['identity_conflicts'],'targets':p15_summary,'raw_page_count_verified':audit15['raw_page_count_verified'],'raw_page_digest_count':audit15['raw_page_digest_count'],'raw_page_issues':audit15['raw_page_issues'],'row_hash_verified_against_private_ledger':audit15['source_record_sha_checks_against_ledger'],'page_ledger':audit15['page_ledger'],'fixture_unique_fids':len(b15),'verified_full_ft_fids':sum(r['verified_full_time_score'] for r in rows15),'unverified_or_nonfull_fids':sum(not r['verified_full_time_score'] for r in rows15),'source_season_missing_fids':sum(r['season_raw'] in (None,'') for r in rows15),'prior_120_fid_overlap':len(oldoverlap),'prior_120_source_sha256':sha_file(OLD_SOURCE),'prior_120_record_count':len(old120),'four_prior_record_version_conflicts':old_conflicts},
      '38_competition_run':{'progress_sha256':sha_file(PROG38),'targets':len(ids38),'unique_fids':len(b38),'verified_full_ft_fids':a38['verified_full_ft_fids'],'unverified_or_nonfull_fids':a38['unverified_or_nonfull_fids'],'raw_pages_referenced':a38['raw_source_page_audit']['distinct_referenced_pages'],'source_record_sha_verified':a38['raw_source_page_audit']['source_record_rows_sha_verified'],'raw_source_errors':a38['raw_source_page_audit']['errors'],'season_missing_fids':sum(r['season_counts'].get('MISSING_SEASON_IN_VERIFIED_RAW_ROW',0) for r in a38['by_league_year'])}},
      'global_unique_fid_reconciliation':{'baseline_inventory_fids':len(baseids),'15_batch_fids':len(b15),'15_batch_overlap_baseline':len(overlap15),'15_batch_new_global_fids':len(b15-overlap15),'38_batch_fids':len(b38),'38_batch_overlap_baseline':len(overlap38),'38_batch_new_global_fids':len(b38-overlap38),'cross_batch_fid_overlap':len(cross),'post_addition_global_fids':len(baseids|b15|b38),'post_addition_delta':len((baseids|b15|b38)-baseids)},
      'crown_sqlite_read_only':{'path':str(DB),'sha256_before_and_after':dbsha,'database_opened_read_only':True,'coverage_by_batch_unique_fids':batchquote,'no_network_requests_or_sqlite_writes':True,'quote_source_event_time_and_http_received_time_are_not_conflated':True},
      'summary':{'target_leagues':len(ids15|ids38),'unique_schedule_fids_across_batches':len(seen),'new_global_schedule_fids':len((b15|b38)-baseids),'total_verified_full_ft_fids':sum(r['verified_full_time_score'] for r in output_rows),'total_unverified_or_nonfull_fids':len(unverified),'future_or_not_yet_due_at_audit':sum(1 for r in unverified if parse_dt(r.get('kickoff_utc')) and parse_dt(r['kickoff_utc'])>now),'past_unverified_or_nonfull':sum(1 for r in unverified if not parse_dt(r.get('kickoff_utc')) or parse_dt(r['kickoff_utc'])<=now),'schedule_quote_fids_are_not_implied_by_the_request':True},
      'input_sha256':{'15_target_scope':sha_file(TARGET15),'38_target_manifest':sha_file(TARGET38),'existing_global_inventory':sha_file(BASE_INV),'private_append_only_fixture_ledger':sha_file(LEDGER),'private_append_only_request_log':sha_file(REQUESTS),'38_raw_page_coverage_audit':sha_file(AUDIT38),'crown_sqlite':dbsha},
      'outputs':{'normalized_fixture_jsonl_gz':out_fixtures.name,'unverified_ft_jsonl_gz':out_unverified.name,'league_year_csv':'supplemental_totalcorner_53_league_year_coverage_2019_2026.csv'},
      'limits':['The 15-target run was completed from its saved progress snapshot; its original per-target progress.json was retained privately before the 38-target run replaced progress.json.','Raw TotalCorner response bodies remain private; public normalized rows include source-page and source-record SHA256 references.','No provider season field is inferred from kickoff year.','No Crown collection was requested during this audit; local SQLite coverage only is reported.','Schedule page fields such as p_asian are not Crown bookmaker quote histories and are not treated as Crown AH.']}
    (OUT/'supplemental_totalcorner_53_schedule_coverage_2019_2026.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'summary':result['summary'],'global_unique_fid_reconciliation':result['global_unique_fid_reconciliation'],'batch15':{k:v for k,v in result['batches']['15_competition_run'].items() if k not in ['targets','page_ledger','four_prior_record_version_conflicts']},'batch38':result['batches']['38_competition_run'],'crown_sqlite':result['crown_sqlite_read_only']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
