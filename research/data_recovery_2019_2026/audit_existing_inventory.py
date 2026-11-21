#!/usr/bin/env python3
"""Read-only inventory of existing 2019-2026 fixtures and Crown AH captures."""
from __future__ import annotations
import collections, csv, datetime as dt, gzip, hashlib, json, os, sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/Users/mac/QuantAsiaDesk')
OUT = Path(__file__).resolve().parent
UNIVERSE = BASE/'research-work/crown-drop-expanded-62/schedule_universe.jsonl'
SCHEDULES = BASE/'data/m5-crown-authorized/schedules'
CROWN_DB = BASE/'data/crown_quote_store/crown_quotes.sqlite3'
M5_INDEX = BASE/'data/m5-crown-authorized/crown-response-index.jsonl'
PRICED_T6 = BASE/'research-work/recovered_factors_20261121/full_priced_T6_original_and_expanded.jsonl.gz'
M1_CACHE = BASE/'repos/m1/data/m1_history_cache'
SUPPLEMENTAL_SCHEDULE = Path(__file__).resolve().parent/'supplemental_totalcorner_league15_schedule_20261121.jsonl.gz'
RECOVERED_SCHEDULE = BASE/'research-work/full_history_backfill_20261121/totalcorner_schedule_recovery/fixtures_2019_2026.verified.jsonl.gz'
EXTERNAL_FT_OVERLAY = Path(__file__).resolve().parent/'external_verified_ft_2019_2026.jsonl'
CROWN_FIXTURE_OVERLAY = Path(__file__).resolve().parent/'crown_only_fixture_identity_candidates_2019_2026.jsonl.gz'
TZ_SH = ZoneInfo('Asia/Shanghai')


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def dtutc(value):
    if not value:return None
    try:
        d=dt.datetime.fromisoformat(str(value).replace('Z','+00:00').replace(' ','T'))
        if d.tzinfo is None:d=d.replace(tzinfo=TZ_SH)
        return d.astimezone(dt.timezone.utc).isoformat().replace('+00:00','Z')
    except Exception:return None

def parse_year(value):
    try:return int(str(value)[:4])
    except:return None

def nonnegative_int(value):
    try:
        text=str(value).strip();parsed=int(text)
        return parsed if parsed>=0 and text==str(parsed) else None
    except (TypeError,ValueError):return None

def main():
    fixtures={}; page_rows=0; universe_rows=0; m1_cache_rows=0; bad_pages=[]
    # Both immutable raw pages and normalized legacy page caches are valid schedule sources.
    page_paths=sorted(set(SCHEDULES.glob('*/*.raw.json')) | set(SCHEDULES.glob('*/*.json')))
    page_catalog=collections.defaultdict(lambda:{'page_numbers':set(),'reported_totals':set(),'league_names':set(),'rows_by_page':{},'page_date_ranges':{},'date_min':None,'date_max':None})
    def row_for(fid):
        return fixtures.setdefault(str(fid),{'fid':str(fid),'expanded_universe':[],'totalcorner_schedule':[],'supplemental_schedule':[],'crown_fixture_metadata':[],'priced_t6':[]})
    for line in UNIVERSE.open(encoding='utf-8'):
        x=json.loads(line); fid=str(x.get('match_id') or '')
        if not fid:continue
        universe_rows+=1; r=row_for(fid)
        r['expanded_universe'].append({'league_id':str(x.get('league_id') or ''),'season':x.get('season'),
          'kickoff_source_local':x.get('kickoff_source_local'),'home_name':x.get('home'),'away_name':x.get('away'),
          'home_goals':x.get('home_goals'),'away_goals':x.get('away_goals')})
    for path in page_paths:
        lid=path.parent.name
        try:
            payload=json.loads(path.read_bytes())
            data=payload.get('data') or payload.get('payload',{}).get('data') or {}
            matches=data.get('matches',[])
        except Exception as e:bad_pages.append({'file':str(path),'error':type(e).__name__});continue
        page_sha=sha256(path)
        try:page_no=int(path.name.split('-')[1].split('.')[0])
        except Exception:page_no=-1
        pc=page_catalog[lid];pc['page_numbers'].add(page_no);page_dates=[]
        try:pc['reported_totals'].add(int((payload.get('pagination') or payload.get('payload',{}).get('pagination') or {}).get('pages')))
        except Exception:pass
        if data.get('league',{}).get('name'):pc['league_names'].add(str(data['league']['name']))
        pc['rows_by_page'][page_no]=len(matches)
        for x in matches:
            fid=str(x.get('id') or '')
            if not fid:continue
            page_rows+=1;r=row_for(fid)
            date=str(x.get('start') or '')[:10]
            if date:
                page_dates.append(date)
                pc['date_min']=min(date,pc['date_min']) if pc['date_min'] else date
                pc['date_max']=max(date,pc['date_max']) if pc['date_max'] else date
            r['totalcorner_schedule'].append({'page_file':str(path),'page_sha256':page_sha,'provider_league_id':str(x.get('l_id') or lid),
              'league_name':x.get('l') or data.get('league',{}).get('name'),'kickoff_source':x.get('start'),'kickoff_utc':dtutc(x.get('start')),'home_id':str(x.get('h_id') or ''),
              'away_id':str(x.get('a_id') or ''),'home_name':x.get('h'),'away_name':x.get('a'),'status':x.get('status'),
              'home_goals':x.get('hg'),'away_goals':x.get('ag')})
        if page_dates:pc['page_date_ranges'][page_no]={'min':min(page_dates),'max':max(page_dates)}
    for path in sorted(M1_CACHE.glob('*.json')):
        try:obj=json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:bad_pages.append({'file':str(path),'error':type(e).__name__});continue
        league=str(obj.get('league_id') or path.stem)
        for x in obj.get('rows',[]):
            fid=str(x.get('id') or '')
            if not fid:continue
            m1_cache_rows+=1
            row_for(fid).setdefault('m1_history_cache',[]).append({'source_file':str(path),'league_id':league,
              'kickoff_source':x.get('start'),'kickoff_utc':dtutc(x.get('start')),'home_id':str(x.get('h_id') or ''),
              'away_id':str(x.get('a_id') or ''),'home_name':x.get('h'),'away_name':x.get('a'),'status':x.get('status'),
              'home_goals':x.get('hg'),'away_goals':x.get('ag')})
    supplemental_rows=0
    if SUPPLEMENTAL_SCHEDULE.exists():
        with gzip.open(SUPPLEMENTAL_SCHEDULE,'rt',encoding='utf-8') as f:
            for line in f:
                if not line.strip():continue
                x=json.loads(line);fid=str(x.get('fid') or '')
                if not fid:continue
                supplemental_rows+=1
                row_for(fid)['supplemental_schedule'].append({'source_file':x.get('source_record_file'),
                  'source_response_sha256':x.get('source_response_sha256'),'source_line_sha256':x.get('source_line_sha256'),
                  'provider_league_id':str(x.get('provider_league_id') or ''),'league_name':x.get('league_name'),
                  'kickoff_source':x.get('kickoff_source_raw'),'kickoff_utc':x.get('kickoff_utc'),
                  'home_id':str(x.get('home_id') or ''),'away_id':str(x.get('away_id') or ''),
                  'home_name':x.get('home_name'),'away_name':x.get('away_name'),'status':x.get('status_raw'),
                  'home_goals':x.get('home_goals_raw'),'away_goals':x.get('away_goals_raw'),
                  'season':x.get('season'),'observed_at_utc':x.get('observed_at_utc')})
    recovered_rows=0
    if RECOVERED_SCHEDULE.exists():
        with gzip.open(RECOVERED_SCHEDULE,'rt',encoding='utf-8') as f:
            for line in f:
                if not line.strip():continue
                x=json.loads(line);fid=str(x.get('fid') or '')
                if not fid:continue
                recovered_rows+=1
                source_bytes=json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
                row_for(fid)['supplemental_schedule'].append({'source_file':str(RECOVERED_SCHEDULE),
                  'source_response_sha256':x.get('source_page_response_sha256'),
                  'source_line_sha256':hashlib.sha256(source_bytes).hexdigest(),
                  'source_record_sha256':x.get('source_record_sha256'),
                  'provider_league_id':str(x.get('provider_league_id') or ''),'league_name':x.get('provider_league_name'),
                  'kickoff_source':x.get('kickoff_source_raw'),'kickoff_utc':x.get('kickoff_utc'),
                  'home_id':str(x.get('home_id') or ''),'away_id':str(x.get('away_id') or ''),
                  'home_name':x.get('home_name'),'away_name':x.get('away_name'),'status':x.get('status_raw'),
                  'home_goals':x.get('home_goals_raw'),'away_goals':x.get('away_goals_raw'),
                  'season':x.get('season_raw'),'observed_at_utc':x.get('response_received_at_utc')})
    crown_fixture_rows=0
    if CROWN_FIXTURE_OVERLAY.exists():
        with gzip.open(CROWN_FIXTURE_OVERLAY,'rt',encoding='utf-8') as f:
            for line in f:
                if not line.strip():continue
                x=json.loads(line)
                # The China-local 2019 boundary record is retained in the source
                # artifact but remains outside the UTC 2019-2026 matrix.
                if x.get('scope_position')!='within_utc_2019_2026':continue
                fid=str(x.get('fid') or '')
                if not fid:continue
                crown_fixture_rows+=1
                refs=[{'data_layer':z[0],'capture_mode':z[1],'response_sha256':z[2],
                       'source_basename':z[3],'response_received_at_utc':z[4]}
                      for z in x.get('response_references',[])]
                row_for(fid)['crown_fixture_metadata'].append({'source':x.get('source'),
                  'provider_league_id':str(x.get('provider_league_id') or ''),
                  'provider_league_name':x.get('provider_league_name'),
                  'kickoff_source':x.get('kickoff_source_raw'),'kickoff_utc':x.get('kickoff_utc'),
                  'kickoff_china':x.get('kickoff_china'),'home_id':str(x.get('home_id') or ''),
                  'away_id':str(x.get('away_id') or ''),'home_name':x.get('home_name'),
                  'away_name':x.get('away_name'),'status':x.get('status_raw'),
                  'home_goals':x.get('home_goals_raw'),'away_goals':x.get('away_goals_raw'),
                  'crown_bookmaker_present':x.get('crown_bookmaker_present_in_selected_raw_response'),
                  'source_identity_consistent':x.get('source_identity_consistent_across_captures'),
                  'response_references':refs})
    external_ft_rows=0
    if EXTERNAL_FT_OVERLAY.exists():
        for line in EXTERNAL_FT_OVERLAY.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            x=json.loads(line);fid=str(x.get('match_id') or '')
            if fid:
                row_for(fid).setdefault('external_ft_evidence',[]).append(x)
                external_ft_rows+=1
    priced_t6_rows=0
    if PRICED_T6.exists():
        with gzip.open(PRICED_T6,'rt',encoding='utf-8') as f:
            for line in f:
                x=json.loads(line);fid=str(x.get('fid') or x.get('match_id') or '')
                if not fid:continue
                priced_t6_rows+=1;row_for(fid)['priced_t6'].append({k:x.get(k) for k in ('league','league_id','year','date','T','home_id','away_id','al','ah','aa','source_file','source_sha256') if k in x})
    # SQLite stays open read-only; preserve source-event and HTTP receive clocks independently.
    c=sqlite3.connect(f'file:{CROWN_DB}?mode=ro',uri=True)
    capture_sql='''select fixture_id,data_layer,capture_mode,status,count(*),sum(quote_count),min(response_received_at_utc),max(response_received_at_utc),min(processed_at_utc),max(processed_at_utc),sum(prospective_observation),min(kickoff_at_utc),max(kickoff_at_utc) from capture group by fixture_id,data_layer,capture_mode,status'''
    for fid,layer,mode,status,n,decl,recv_min,recv_max,proc_min,proc_max,pros,kick_min,kick_max in c.execute(capture_sql):
        r=row_for(fid);r.setdefault('crown_captures',[]).append({'layer':layer,'capture_mode':mode,'status':status,'capture_count':n,
          'declared_quote_count':decl or 0,'response_received_min_utc':recv_min,'response_received_max_utc':recv_max,
          'processed_min_utc':proc_min,'processed_max_utc':proc_max,'prospective_capture_count':pros or 0,
          'kickoff_min_utc':kick_min,'kickoff_max_utc':kick_max})
    crown_raw_refs=[];raw_missing=0;raw_mismatch=0
    for source_file,db_sha in c.execute('select distinct source_file,response_sha256 from capture order by source_file'):
        path=Path(source_file);exists=path.is_file();actual=sha256(path) if exists else None
        if not exists:raw_missing+=1
        elif actual!=db_sha:raw_mismatch+=1
        try:display=path.relative_to(BASE).as_posix()
        except ValueError:display=str(path)
        crown_raw_refs.append({'source_path':display,'response_sha256_db':db_sha,'response_sha256_actual':actual,'exists':exists,'sha256_match':bool(exists and actual==db_sha)})
    quote_sql='''select q.fixture_id,c.data_layer,c.capture_mode,q.quote_kind,count(*),count(distinct q.quote_source_at_utc),
       min(q.quote_source_at_utc),max(q.quote_source_at_utc),min(q.response_received_at_utc),max(q.response_received_at_utc),
       sum(q.quote_before_kickoff),sum(q.prospective_observation)
       from asian_quote q join capture c using(capture_key)
       group by q.fixture_id,c.data_layer,c.capture_mode,q.quote_kind'''
    for fid,layer,mode,kind,n,nt,srcmin,srcmax,rcvmin,rcvmax,before,pros in c.execute(quote_sql):
        r=row_for(fid);r.setdefault('crown_quote_groups',[]).append({'layer':layer,'capture_mode':mode,'quote_kind':kind,
          'quote_rows':n,'distinct_source_timestamps':nt,'source_event_min_utc':srcmin,'source_event_max_utc':srcmax,
          'http_received_min_utc':rcvmin,'http_received_max_utc':rcvmax,'quote_before_kickoff_rows':before or 0,
          'prospective_quote_rows':pros or 0})
    failures=collections.defaultdict(collections.Counter)
    for fid,layer,mode,code,n in c.execute('select fixture_id,data_layer,capture_mode,error_code,count(*) from failed_attempt group by 1,2,3,4'):
        failures[str(fid)][f'{layer}|{mode}|{code}']=n
    # Build a conservative league/year denominator from every schedule source; only exact provider IDs are joined.
    group=collections.defaultdict(lambda:{'fids':set(),'schedule_page_fids':set(),'supplemental_schedule_fids':set(),'crown_fixture_metadata_fids':set(),'m1_history_cache_fids':set(),'expanded_fids':set(),'priced_t6_fids':set(),'external_ft_fids':set(),
      'complete_ft_fids':set(),'unverified_ft_fids':set(),'schedule_status':collections.Counter(),'capture_fids':set(),'movement_capture_fids':set(),'movement_quotes_fids':set(),
      'summary_quotes_fids':set(),'live_quote_fids':set(),'movement_quote_rows':0,'summary_quote_rows':0,'live_quote_rows':0,
      'source_event_timestamps':0,'failures':0,'no_quote_fids':set(),'capture_sha_file_missing':0})
    inventory=[];conflicts=[];missing_movement=[]
    for fid,r in fixtures.items():
        # Identity dimensions are kept per source. Conflicts are not auto-collapsed.
        page=r['totalcorner_schedule'];supp=r['supplemental_schedule'];crown_meta=r['crown_fixture_metadata'];uni=r['expanded_universe'];
        league_ids={z['provider_league_id'] for z in page if z.get('provider_league_id')}
        league_ids.update(z['provider_league_id'] for z in supp if z.get('provider_league_id'))
        league_ids.update(z['provider_league_id'] for z in crown_meta if z.get('provider_league_id'))
        league_ids.update(z['league_id'] for z in uni if z.get('league_id'))
        league_ids.update(str(z.get('league') or z.get('league_id')) for z in r['priced_t6'] if z.get('league') or z.get('league_id'))
        m1_records=r.get('m1_history_cache',[])
        league_ids.update(z['league_id'] for z in m1_records if z.get('league_id'))
        if len(league_ids)>1:conflicts.append({'fid':fid,'type':'league_id_conflict','league_ids':sorted(league_ids)})
        league=sorted(league_ids)[0] if len(league_ids)==1 else (sorted(league_ids)[0] if league_ids else 'UNKNOWN')
        date_values=set()
        for z in page+m1_records+supp+crown_meta:
            if z.get('kickoff_utc'):date_values.add(z['kickoff_utc'][:10])
        for z in uni:
            # Keep source-local date independently; do not treat it as UTC.
            if z.get('kickoff_source_local'):date_values.add('LOCAL:'+str(z['kickoff_source_local'])[:10])
        calendar_dates={x for x in date_values if not x.startswith('LOCAL:')}
        if len(calendar_dates)>1:conflicts.append({'fid':fid,'type':'totalcorner_kickoff_utc_conflict','dates':sorted(calendar_dates)})
        utc_values=sorted([z['kickoff_utc'] for z in page+m1_records+supp+crown_meta if z.get('kickoff_utc')])
        kickoff_utc=utc_values[0] if utc_values else None
        year=parse_year(kickoff_utc) if kickoff_utc else next((parse_year(z.get('kickoff_source_local')) for z in uni if z.get('kickoff_source_local')),None)
        if year is None:
            for z in r['priced_t6']:
                year=int(z['year']) if z.get('year') is not None else parse_year(z.get('date'))
                if year:break
        if year is None or not 2019<=year<=2026:continue
        d=group[(league,year)];d['fids'].add(fid)
        if page:d['schedule_page_fids'].add(fid)
        if supp:d['supplemental_schedule_fids'].add(fid)
        if crown_meta:d['crown_fixture_metadata_fids'].add(fid)
        if m1_records:d['m1_history_cache_fids'].add(fid)
        if uni:d['expanded_fids'].add(fid)
        if r['priced_t6']:d['priced_t6_fids'].add(fid)
        status_set={str(z.get('status') or 'unknown') for z in page+m1_records+supp+crown_meta}
        for s in status_set:d['schedule_status'][s]+=1
        external_ft=r.get('external_ft_evidence',[])
        if external_ft:d['external_ft_fids'].add(fid)
        verified_ft=bool(external_ft) or any(z.get('status')=='full' and nonnegative_int(z.get('home_goals')) is not None and nonnegative_int(z.get('away_goals')) is not None for z in page+m1_records+supp+crown_meta)
        if verified_ft:d['complete_ft_fids'].add(fid)
        else:d['unverified_ft_fids'].add(fid)
        caps=r.get('crown_captures',[]);qgs=r.get('crown_quote_groups',[])
        if caps:d['capture_fids'].add(fid)
        if any(x['layer']=='movement' for x in caps):d['movement_capture_fids'].add(fid)
        if not any(x['layer']=='movement' for x in caps):
            identity=(page or m1_records or supp or crown_meta or [None])[0]
            missing_movement.append({'match_id':fid,'kickoff_utc':kickoff_utc,
              'kickoff_source':identity.get('kickoff_source') if identity else None,
              'provider_league_id':league,'league_name':identity.get('league_name') if identity else None,
              'calendar_year_utc':year,'home_id':identity.get('home_id') if identity else None,
              'away_id':identity.get('away_id') if identity else None,
              'home_name':identity.get('home_name') if identity else None,'away_name':identity.get('away_name') if identity else None,
              'status':identity.get('status') if identity else None,
              'home_goals':identity.get('home_goals') if identity else None,'away_goals':identity.get('away_goals') if identity else None})
        if any(x['layer']=='movement' and x['quote_rows']>0 for x in qgs):d['movement_quotes_fids'].add(fid)
        if any(x['layer']=='summary' and x['quote_rows']>0 for x in qgs):d['summary_quotes_fids'].add(fid)
        for x in qgs:
            if x['layer']=='movement':d['movement_quote_rows']+=x['quote_rows'];d['source_event_timestamps']+=x['distinct_source_timestamps']
            elif x['layer']=='summary':d['summary_quote_rows']+=x['quote_rows']
            if x['capture_mode']=='live':d['live_quote_rows']+=x['quote_rows'];d['live_quote_fids'].add(fid)
        if any(x['layer']=='movement' and x['status']=='NO_CROWN_AH_QUOTES' for x in caps):d['no_quote_fids'].add(fid)
        d['failures']+=sum(failures.get(fid,{}).values())
        inventory.append({'fid':fid,'provider_league_id':league,'year':year,'totalcorner_kickoff_utc':kickoff_utc,
          'totalcorner_page_records':page,'supplemental_schedule_records':supp,'crown_fixture_metadata_records':crown_meta,'M1_history_cache_records':m1_records,'expanded_universe_records':uni,'priced_t6_records':r['priced_t6'],
          'crown_captures':caps,'crown_quote_groups':qgs,'external_ft_evidence':external_ft,'failed_attempts':dict(failures.get(fid,{})),
          'identity_conflicts':[x for x in conflicts if x['fid']==fid]})
    # Output full league/year coverage matrix and source inventories.
    matrix=[]
    all_leagues=sorted({league for league,year in group})
    for league in all_leagues:
      for year in range(2019,2027):
        d=group.get((league,year),{'fids':set(),'schedule_page_fids':set(),'supplemental_schedule_fids':set(),'crown_fixture_metadata_fids':set(),'m1_history_cache_fids':set(),'expanded_fids':set(),'priced_t6_fids':set(),'external_ft_fids':set(),
          'complete_ft_fids':set(),'unverified_ft_fids':set(),'schedule_status':collections.Counter(),'capture_fids':set(),'movement_capture_fids':set(),'movement_quotes_fids':set(),
          'summary_quotes_fids':set(),'live_quote_fids':set(),'movement_quote_rows':0,'summary_quote_rows':0,'live_quote_rows':0,
          'source_event_timestamps':0,'failures':0,'no_quote_fids':set(),'capture_sha_file_missing':0})
        matrix.append({'provider_league_id':league,'calendar_year_utc':year,'schedule_fids_union':len(d['fids']),
          'totalcorner_schedule_fids':len(d['schedule_page_fids']),'expanded_universe_fids':len(d['expanded_fids']),
          'supplemental_schedule_fids':len(d['supplemental_schedule_fids']),
          'crown_fixture_metadata_fids':len(d['crown_fixture_metadata_fids']),
          'M1_history_cache_fids':len(d['m1_history_cache_fids']),'T6_priced_inventory_fids':len(d['priced_t6_fids']),'complete_FT_fids':len(d['complete_ft_fids']),
          'unverified_FT_fids':len(d['unverified_ft_fids']),
          'external_verified_FT_fids':len(d['external_ft_fids']),
          'any_Crown_capture_fids':len(d['capture_fids']),'movement_with_quotes_fids':len(d['movement_quotes_fids']),
          'movement_capture_fids':len(d['movement_capture_fids']),
          'movement_quote_rows':d['movement_quote_rows'],'distinct_movement_source_event_timestamps':d['source_event_timestamps'],
          'summary_with_quotes_fids':len(d['summary_quotes_fids']),'summary_quote_rows':d['summary_quote_rows'],
          'live_quote_receipt_fids':len(d['live_quote_fids']),'live_quote_rows':d['live_quote_rows'],
          'explicit_no_Crown_AH_movement_fids':len(d['no_quote_fids']),'failed_attempts':d['failures'],
          'uncovered_schedule_fids':len(d['fids']-d['movement_quotes_fids'])})
    with (OUT/'league_year_coverage_2019_2026.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(matrix[0]),lineterminator='\n');w.writeheader();w.writerows(matrix)
    # Preserve season labels where a source actually supplies them. For source
    # rows without a season field, keep an explicit unknown bucket rather than
    # inferring a season from kickoff date or later standings.
    season_group=collections.defaultdict(lambda:{'fids':set(),'complete_ft_fids':set(),'unverified_ft_fids':set(),
      'movement_capture_fids':set(),'movement_quotes_fids':set(),'summary_quotes_fids':set(),'live_quote_fids':set(),
      'movement_quote_rows':0,'summary_quote_rows':0,'live_quote_rows':0,'no_quote_fids':set(),'failed_attempts':0,
      'expanded_universe_fids':set(),'season_metadata_records':0,'season_conflict_fids':set()})
    for inv in inventory:
        fid=inv['fid'];league_id=inv['provider_league_id']
        page=inv['totalcorner_page_records'];supp=inv['supplemental_schedule_records'];crown_meta=inv['crown_fixture_metadata_records'];uni=inv['expanded_universe_records'];m1_records=inv['M1_history_cache_records']
        seasons=sorted({str(z.get('season')).strip() for z in uni if z.get('season') is not None and str(z.get('season')).strip()})
        season_key=seasons[0] if len(seasons)==1 else ('UNKNOWN_SOURCE_SEASON' if not seasons else 'SEASON_SOURCE_CONFLICT:'+'|'.join(seasons))
        sources=page+m1_records+supp+crown_meta
        external_ft=inv.get('external_ft_evidence',[])
        verified_ft=bool(external_ft) or any(z.get('status')=='full' and nonnegative_int(z.get('home_goals')) is not None and nonnegative_int(z.get('away_goals')) is not None for z in sources)
        caps=inv.get('crown_captures',[]);qgs=inv.get('crown_quote_groups',[])
        d=season_group[(league_id,season_key)];d['fids'].add(fid)
        if uni:d['expanded_universe_fids'].add(fid)
        if seasons:d['season_metadata_records']+=sum(1 for z in uni if z.get('season') is not None and str(z.get('season')).strip())
        if len(seasons)>1:d['season_conflict_fids'].add(fid)
        (d['complete_ft_fids'] if verified_ft else d['unverified_ft_fids']).add(fid)
        if any(x.get('layer')=='movement' for x in caps):d['movement_capture_fids'].add(fid)
        if any(x.get('layer')=='movement' and x.get('quote_rows',0)>0 for x in qgs):d['movement_quotes_fids'].add(fid)
        if any(x.get('layer')=='summary' and x.get('quote_rows',0)>0 for x in qgs):d['summary_quotes_fids'].add(fid)
        if any(x.get('capture_mode')=='live' for x in qgs):d['live_quote_fids'].add(fid)
        if any(x.get('layer')=='movement' and x.get('status')=='NO_CROWN_AH_QUOTES' for x in caps):d['no_quote_fids'].add(fid)
        d['failed_attempts']+=sum(failures.get(fid,{}).values())
        for x in qgs:
            if x.get('layer')=='movement':d['movement_quote_rows']+=x.get('quote_rows',0)
            elif x.get('layer')=='summary':d['summary_quote_rows']+=x.get('quote_rows',0)
            if x.get('capture_mode')=='live':d['live_quote_rows']+=x.get('quote_rows',0)
    season_matrix=[]
    for (league_id,season),d in sorted(season_group.items()):
        season_matrix.append({'provider_league_id':league_id,'source_season':season,'schedule_fids_union':len(d['fids']),
          'expanded_universe_fids':len(d['expanded_universe_fids']),'complete_FT_fids':len(d['complete_ft_fids']),
          'unverified_FT_fids':len(d['unverified_ft_fids']),'movement_capture_fids':len(d['movement_capture_fids']),
          'movement_with_quotes_fids':len(d['movement_quotes_fids']),'movement_quote_rows':d['movement_quote_rows'],
          'summary_with_quotes_fids':len(d['summary_quotes_fids']),'summary_quote_rows':d['summary_quote_rows'],
          'live_quote_receipt_fids':len(d['live_quote_fids']),'live_quote_rows':d['live_quote_rows'],
          'explicit_no_Crown_AH_movement_fids':len(d['no_quote_fids']),'failed_attempts':d['failed_attempts'],
          'season_metadata_records':d['season_metadata_records'],'season_source_conflict_fids':len(d['season_conflict_fids'])})
    with (OUT/'league_season_coverage_2019_2026.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(season_matrix[0]),lineterminator='\n');w.writeheader();w.writerows(season_matrix)
    # Deterministic compressed row inventory.
    with (OUT/'fixture_inventory_2019_2026.jsonl.gz').open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
            for row in sorted(inventory,key=lambda x:(x['provider_league_id'],x['year'],x['fid'])):
                gz.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())
    missing_movement.sort(key=lambda x:(x['provider_league_id'],x['calendar_year_utc'],x['match_id']))
    with (OUT/'movement_missing_capture_candidates.jsonl').open('w',encoding='utf-8') as f:
        for row in missing_movement:f.write(json.dumps(row,separators=(',',':'))+'\n')
    missing_ft=[]
    for row in inventory:
        sources=row['totalcorner_page_records']+row['supplemental_schedule_records']+row['M1_history_cache_records']+row['crown_fixture_metadata_records']
        if row.get('external_ft_evidence') or any(z.get('status')=='full' and nonnegative_int(z.get('home_goals')) is not None and nonnegative_int(z.get('away_goals')) is not None for z in sources):continue
        latest=next((z for z in sources if z.get('kickoff_utc')),sources[0] if sources else {})
        missing_ft.append({'match_id':row['fid'],'kickoff_utc':row['totalcorner_kickoff_utc'],'provider_league_id':row['provider_league_id'],
          'calendar_year_utc':row['year'],'home_name':latest.get('home_name'),'away_name':latest.get('away_name'),
          'home_id':latest.get('home_id'),'away_id':latest.get('away_id'),'observed_statuses':sorted({str(z.get('status')) for z in sources}),
          'observed_scores':sorted({f"{z.get('home_goals')}:{z.get('away_goals')}" for z in sources if z.get('home_goals') is not None or z.get('away_goals') is not None}),
          'external_ft_evidence':row.get('external_ft_evidence',[])})
    missing_ft.sort(key=lambda x:(x['provider_league_id'],x['calendar_year_utc'],x['match_id']))
    with (OUT/'unverified_FT_candidates.jsonl').open('w',encoding='utf-8') as f:
        for row in missing_ft:f.write(json.dumps(row,separators=(',',':'))+'\n')
    files=[UNIVERSE,M5_INDEX,PRICED_T6,SUPPLEMENTAL_SCHEDULE,RECOVERED_SCHEDULE,EXTERNAL_FT_OVERLAY,CROWN_FIXTURE_OVERLAY]
    inputs=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in files if p.exists()]
    page_manifest=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in page_paths]
    with (OUT/'schedule_page_sha256.jsonl').open('w',encoding='utf-8') as f:
        for x in page_manifest:f.write(json.dumps(x,separators=(',',':'))+'\n')
    m1_manifest=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(M1_CACHE.glob('*.json'))]
    with (OUT/'m1_history_cache_sha256.jsonl').open('w',encoding='utf-8') as f:
        for x in m1_manifest:f.write(json.dumps(x,separators=(',',':'))+'\n')
    with (OUT/'crown_raw_response_sha256.jsonl').open('w',encoding='utf-8') as f:
        for x in crown_raw_refs:f.write(json.dumps(x,separators=(',',':'))+'\n')
    db_parts=[]
    for path in (CROWN_DB,Path(str(CROWN_DB)+'-wal'),Path(str(CROWN_DB)+'-shm')):
        if path.exists():db_parts.append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha256(path)})
    db_stat={'path':str(CROWN_DB),'bytes':CROWN_DB.stat().st_size,'sha256':sha256(CROWN_DB),'state_files':db_parts}
    page_completeness=[]
    for lid,pc in sorted(page_catalog.items()):
        total=max(pc['reported_totals']) if pc['reported_totals'] else None
        present=sorted(p for p in pc['page_numbers'] if p>0)
        missing=[p for p in range(1,total+1) if p not in pc['page_numbers']] if total else []
        target_pages=[p for p,rng in pc['page_date_ranges'].items() if rng['max']>='2019-01-01' and rng['min']<='2026-12-31']
        last_target_page=max(target_pages) if target_pages else None
        missing_target_pages=[p for p in range(1,last_target_page+1) if p not in pc['page_numbers']] if last_target_page else []
        page_completeness.append({'provider_league_id':lid,'league_names':sorted(pc['league_names']),'reported_pages_max':total,
          'cached_page_count':len(present),'cached_min_page':min(present) if present else None,'cached_max_page':max(present) if present else None,
          'missing_page_numbers':missing,'cached_date_min_source':pc['date_min'],'cached_date_max_source':pc['date_max'],
          'last_page_with_2019_2026_rows':last_target_page,'missing_page_numbers_through_target_range':missing_target_pages,
          'page_total_disagreements':sorted(pc['reported_totals']),'cached_rows':sum(pc['rows_by_page'].values())})
    out={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'inputs':inputs,'crown_database':db_stat,
      'schedule_page_count':len(page_paths),'schedule_page_manifest_sha256':sha256(OUT/'schedule_page_sha256.jsonl'),
      'schedule_page_parse_errors':bad_pages,'expanded_schedule_rows':universe_rows,'schedule_page_rows':page_rows,
      'schedule_page_completeness':page_completeness,
      'supplemental_schedule_rows':supplemental_rows,
      'new_recovered_schedule_fixture_versions':recovered_rows,
      'strictly_reconciled_external_FT_rows':external_ft_rows,
      'M1_history_cache_file_count':len(m1_manifest),'M1_history_cache_rows':m1_cache_rows,
      'M1_history_cache_manifest_sha256':sha256(OUT/'m1_history_cache_sha256.jsonl'),
      'unique_crown_raw_response_files':len(crown_raw_refs),'crown_raw_response_files_missing':raw_missing,
      'crown_raw_response_files_sha256_mismatch':raw_mismatch,
      'crown_raw_response_sha256_manifest_sha256':sha256(OUT/'crown_raw_response_sha256.jsonl'),
      'union_unique_fids':sum(len(d['fids']) for (l,y),d in group.items() if 2019<=y<=2026),'league_year_rows':len(matrix),'league_ids':all_leagues,
      'input_FID_identity_conflicts':conflicts,'totals_2019_2026':{k:sum(x[k] for x in matrix) for k in matrix[0] if k not in ('provider_league_id','calendar_year_utc')},
      'coverage_rows':matrix,'outputs':{}}
    for name in ('fixture_inventory_2019_2026.jsonl.gz','league_year_coverage_2019_2026.csv','league_season_coverage_2019_2026.csv','schedule_page_sha256.jsonl','m1_history_cache_sha256.jsonl','crown_raw_response_sha256.jsonl','movement_missing_capture_candidates.jsonl','unverified_FT_candidates.jsonl'):
        p=OUT/name;out['outputs'][name]={'bytes':p.stat().st_size,'sha256':sha256(p)}
    (OUT/'inventory_audit_2019_2026.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    conflict_counts=collections.Counter(x.get('type','unknown') for x in conflicts)
    public_summary={
      'generated_at_utc':out['generated_at'],
      'scope':'All currently identified provider league IDs, UTC calendar years 2019-2026; this is a moving inventory snapshot, not a completion claim.',
      'source_file_sha256':[{'file':Path(x['path']).name,'sha256':x['sha256'],'bytes':x['bytes']} for x in inputs],
      'crown_store_snapshot':{
        'main_db_bytes':db_stat['bytes'],'main_db_sha256_at_snapshot':db_stat['sha256'],
        'inventory_mapped_raw_response_file_count':out['unique_crown_raw_response_files'],
        'raw_response_files_missing':raw_missing,'raw_response_sha256_mismatches':raw_mismatch,
      },
      'schedule_pages':{
        'physical_page_files':len(page_paths),'page_records_including_repeats':page_rows,
        'expanded_schedule_rows':universe_rows,'completeness':page_completeness,
        'supplemental_schedule_record_versions':supplemental_rows,
        'recovered_schedule_record_versions':recovered_rows,
      },
      'inventory_totals_2019_2026':out['totals_2019_2026'],
      'provider_league_ids':all_leagues,
      'league_year_coverage':matrix,
        'league_season_coverage':season_matrix,
      'identity_conflict_counts_by_type':dict(conflict_counts),
      'local_unpublished_audit_artifact_hashes':out['outputs'],
      'privacy_note':'Raw Crown response bodies, SQLite, full per-FID inventory and exact private response locations remain in the authorized local data store; this public summary carries aggregate coverage and content digests only.',
    }
    (OUT/'inventory_coverage_summary_2019_2026.json').write_text(json.dumps(public_summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'expanded_schedule_rows':universe_rows,'schedule_page_rows':page_rows,'M1_history_cache_rows':m1_cache_rows,'union_unique_fids':out['union_unique_fids'],
      'league_ids':len(out['league_ids']),'league_year_rows':len(matrix),'totals':out['totals_2019_2026'],
      'conflicts':len(conflicts),'bad_pages':len(bad_pages),'sqlite_fids':len(capture_by_fid) if False else None,
      'output':str(OUT/'inventory_audit_2019_2026.json')},ensure_ascii=False))
    c.close()

if __name__=='__main__':main()
