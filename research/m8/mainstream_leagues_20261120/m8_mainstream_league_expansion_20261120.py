#!/usr/bin/env python3
"""Auditable M8 mainstream-league coverage and league-local AH side-selection study.

Historical Crown source-event replay only. No production changes, no data fetching.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'research/m8/mainstream_leagues_20261120'
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized')
SCHEDULE=DATA/'schedules'
PATHF=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCOREF=WORK/'m8_independent_score_strength_20261114.jsonl'
MEMF=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RESPIDX=DATA/'crown-response-index.jsonl'
RESP=DATA/'crown-responses'
RECEIPT_FILES=[
 ROOT/'research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl',
 pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'),
 ROOT/'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl',
]
INTENSIVE=ROOT/'research/m8/next_round_20261120/per_fixture_walkforward_20261120.jsonl.gz'
TZ=dt.timezone(dt.timedelta(hours=8))
YEARS=range(2022,2027)
# Patterns cover the user-proposed scope; schedule league ID/name inventory is retained for all cached competitions.
REQUESTED={
 'England Premier League':r'England Premier League',
 'Spain La Liga':r'Spain La Liga',
 'Germany Bundesliga':r'Germany Bundesliga',
 'Italy Serie A':r'Italy Serie A',
 'France Ligue 1':r'France Ligue 1',
 'Netherlands Eredivisie':r'Netherlands Eredivisie',
 'Portugal Primeira Liga':r'Portugal Primeira Liga',
 'Belgium First Division A':r'Belgium First Division A',
 'Turkey Super Lig':r'Türkiye Super Lig|Turkey Super Lig',
 'Scotland Premiership':r'Scotland Premiership',
 'Austria Bundesliga':r'Austria Bundesliga',
 'Switzerland Super League':r'Switzerland Super League',
 'Japan J1':r'Japan J-League',
 'South Korea K League 1':r'South Korea K League 1',
 'USA MLS':r'USA MLS',
 'Brazil Serie A':r'Brazil Serie A',
 'Argentina Primera Division':r'Argentina Liga Profesional',
 'Mexico Liga MX':r'Mexico Liga MX',
}
def sha_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read_jsonl(p):
 with p.open() as f:
  for line in f:
   if line.strip():yield json.loads(line)
def score(side,line,ho,ao,hg,ag):
 signed=float(line) if side=='home' else -float(line)
 gd=int(hg)-int(ag) if side=='home' else int(ag)-int(hg)
 contract=gd+signed
 # quarter lines split to adjacent half-goal legs, half unit each
 q=signed*2
 if abs(q-round(q))<1e-9: legs=[signed]
 else: legs=[math.floor(q)/2,math.ceil(q)/2]
 odds=float(ho) if side=='home' else float(ao)
 legs_result=[]; pnl=0.
 for z in legs:
  x=gd+z
  if x>1e-9: legs_result.append('W');pnl+=(odds-1)/len(legs)
  elif x< -1e-9: legs_result.append('L');pnl-=1/len(legs)
  else: legs_result.append('P')
 state={'W':'full_win','L':'full_loss','P':'push','WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss'}[''.join(legs_result)]
 return round(pnl,10),state

def match_schedule():
 league_meta={}; by_fid=collections.defaultdict(list); league_counts=collections.Counter()
 page_count=0
 for p in sorted(SCHEDULE.glob('*/page-*.raw.json')):
  page_count+=1
  try: doc=json.loads(p.read_text())
  except Exception: continue
  d=doc.get('data',{}); l=d.get('league') or {}
  if l.get('league_id'):league_meta[str(l['league_id'])]={'name':l.get('name',''),'country':l.get('country','')}
  for m in d.get('matches') or []:
   fid=str(m.get('id','')); lid=str(m.get('l_id') or l.get('league_id') or '')
   if not fid or not lid:continue
   by_fid[fid].append(m);league_counts[lid]+=1
 return league_meta,by_fid,league_counts,page_count

def raw_coverage():
 body_ids={p.stem for p in RESP.glob('*.json')}
 indexed={}
 for r in read_jsonl(RESPIDX):
  fid=str(r.get('match_id',''))
  if fid:indexed[fid]=r
 valid={fid for fid in body_ids & indexed.keys() if (indexed[fid].get('ah_valid_prematch_rows') or 0)>0}
 return body_ids,indexed,valid

def receipt_inventory(league_meta, schedules):
 # Keep all distinct actual HTTP receipt FIDs across M8 and MR1 sources; use M8 audited AH+FT rows for the replay.
 m8_rows=[]; all_ids=set(); source_counts={}; registry=collections.defaultdict(lambda:{'fid':None,'sources':[],'league_ids':[],'league_names':[],'receipt_rows':0,'M8_verified_AH_FT_rows':0})
 def add(fid,source,lid=None,lname=None,details=None):
  if not fid:return
  fid=str(fid);all_ids.add(fid);x=registry[fid];x['fid']=fid;x['receipt_rows']+=1
  if source not in x['sources']:x['sources'].append(source)
  if lid and str(lid) not in x['league_ids']:x['league_ids'].append(str(lid))
  if lname and str(lname) not in x['league_names']:x['league_names'].append(str(lname))
  if details:
   x.setdefault('receipt_details',[]).append(details)
 for p in RECEIPT_FILES:
  n=0
  if p.exists():
   for r in read_jsonl(p):
    n+=1
    if p.name=='m8_batch_actual_receipt_independently_audited_20261118.jsonl':
     fid=str(r.get('fid') or '')
     if fid:
      m8_rows.append(r)
      add(fid,'M8_AH_FT_independent_audit',details={'received_utc':r.get('received_utc'),'raw_sha256':r.get('raw_sha256'),'snapshot_sha256':r.get('snapshot_sha256'),'line':r.get('line_home'),'home_odds':r.get('odds_home'),'away_odds':r.get('odds_away'),'ft':r.get('ft'),'source_type':r.get('source_type')})
    elif p.name=='m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl':
     fid=str(r.get('fixture_id') or '');market=r.get('markets',{}).get('AH')
     if fid and market:
      add(fid,'MR1_full_actual_receipt_archive',r.get('league_id'),r.get('league'),{'received_utc':r.get('received_utc'),'raw_sha256':r.get('raw_sha256'),'snapshot_sha256':r.get('snapshot_sha256'),'line':market.get('line'),'odds':market.get('odds')})
    else:
     fid=str(r.get('fid') or '')
     if fid:add(fid,'MR1_verified_receipt_index',details={'received_utc':r.get('received_utc'),'snapshot_sha256':r.get('snapshot_sha256'),'horizon':r.get('horizon')})
  source_counts[str(p)]=n
 # Resolve remaining league identity from a unique saved Crown schedule, then raw FID identity. The raw response is not used to replace the receipt quote.
 for fid,x in registry.items():
  m=schedules.get(fid,[]);sigs={(str(z.get('l_id')),str(z.get('h_id')),str(z.get('a_id')),str(z.get('hg')),str(z.get('ag'))) for z in m}
  lid=next(iter(sigs))[0] if len(sigs)==1 else None
  if len(sigs)>1:x['league_map_conflict']=True;continue
  if not lid and x['league_ids']:lid=x['league_ids'][0]
  if not lid:
   raw=RESP/(fid+'.json')
   if raw.exists():
    try:
     doc=json.loads(raw.read_text());hits=[z for z in doc.get('data',[]) if str(z.get('id'))==fid]
     if len(hits)==1:
      lid=str(hits[0].get('l_id'));x['league_map_source']='raw_FID_identity_only';x['identity_body_sha256']=sha_file(raw)
      if lid not in league_meta:league_meta[lid]={'name':str(hits[0].get('l','')),'country':''}
    except Exception:pass
  x['league_id']=lid
  if lid and not x['league_names'] and lid in league_meta:x['league_names']=[league_meta[lid].get('name','')]
  if lid and lid in league_meta and lid not in x['league_ids']:x['league_ids'].append(lid)
 # Deduplicate M8 model rows per FID and require identical actual quote/FT across rows before replay.
 per=collections.defaultdict(list)
 for r in m8_rows:per[str(r['fid'])].append(r)
 unique=[];conflicts=[]
 for fid,rows in per.items():
  tuples={(float(r['line_home']),float(r['odds_home']),float(r['odds_away']),str(r['ft'])) for r in rows}
  if len(tuples)!=1:
   conflicts.append({'fid':fid,'distinct_quote_ft_sets':len(tuples),'rows':len(rows)});continue
  r=min(rows,key=lambda z:str(z.get('received_utc') or z.get('signal_time_utc') or ''))
  x=registry[fid];r=dict(r);r['schedule_league_id']=x.get('league_id');r['league_mapping_source']=x.get('league_map_source','saved_schedule_or_MR1');
  if r.get('schedule_league_id') and r['schedule_league_id'] in league_meta:r['league_name']=league_meta[r['schedule_league_id']].get('name','')
  unique.append(r)
 for fid,x in registry.items():
  x['sources']=sorted(x['sources']);x['league_ids']=sorted(x['league_ids']);x['league_names']=sorted(x['league_names'])
 return unique,all_ids,source_counts,conflicts,registry

def run():
 OUT.mkdir(parents=True,exist_ok=True)
 league_meta,schedules,sched_counts,pages=match_schedule()
 path_rows=list(read_jsonl(PATHF)); score_rows=list(read_jsonl(SCOREF)); mem_rows=list(read_jsonl(MEMF))
 paths={str(r['fid']):r for r in path_rows}; scores={str(r['fid']):r for r in score_rows}; frozen={str(r['fid']):r for r in mem_rows}
 # Checked prior tested cohort, fixed by FID from M8 2024-26 market_contract model.
 intensive_ids=set()
 with gzip.open(INTENSIVE,'rt',encoding='utf-8') as f:
  for line in f:
   r=json.loads(line)
   if r.get('model')=='market_contract':intensive_ids.add(str(r['fid']))
 bodies,indexed,rawids=raw_coverage()
 receipt_rows,receipt_ids,receipt_source_counts,receipt_conflicts,receipt_registry=receipt_inventory(league_meta,schedules)
 # Calendar inventory: retain schedule only as schedule/FT coverage, never as Crown price evidence.
 sch_summary=collections.defaultdict(lambda:collections.Counter())
 sch_fid_league={}
 sched_ft_ids=set()
 for fid,opts in schedules.items():
  uniq={json.dumps({k:x.get(k) for k in ('id','l_id','h_id','a_id','start','hg','ag','h','a')},sort_keys=True):x for x in opts}
  if len(uniq)!=1:continue
  m=next(iter(uniq.values()));lid=str(m.get('l_id',''));sch_fid_league[fid]=lid
  start=str(m.get('start',''));year=start[:4]
  sch_summary[(lid,year)]['matches']+=1
  if m.get('status')=='full' and m.get('hg') not in (None,'') and m.get('ag') not in (None,''):
   sch_summary[(lid,year)]['trusted_schedule_ft']+=1;sched_ft_ids.add(fid)
 # Identity/FT audit for historical Crown quote rows.
 fixtures=[]; issues=collections.Counter(); duplicate_conflicts=[]
 for fid,p in paths.items():
  sc=scores.get(fid)
  if sc is None:issues['no_score_row']+=1;continue
  opts=schedules.get(fid,[])
  if str(p.get('league'))!=str(sc.get('league')):issues['path_score_league_mismatch']+=1;continue
  schedule_verified=False;m=None
  if opts:
   uniq={json.dumps({k:x.get(k) for k in ('id','l_id','h_id','a_id','start','hg','ag','h','a')},sort_keys=True):x for x in opts}
   if len(uniq)!=1:
    issues['conflicting_schedule_rows']+=1;duplicate_conflicts.append(fid);continue
   m=next(iter(uniq.values()))
   if str(m.get('l_id'))!=str(sc.get('league')) or str(m.get('h_id'))!=str(sc.get('home')) or str(m.get('a_id'))!=str(sc.get('away')):
    issues['schedule_identity_mismatch']+=1;continue
  else:issues['no_saved_schedule_fid_but_exact_score_fid']+=1
  try:
   hg,ag=int(sc['hg']),int(sc['ag'])
   if m is not None and (int(m.get('hg') or -99),int(m.get('ag') or -99))!=(hg,ag):issues['schedule_ft_mismatch']+=1;continue
   ko=dt.datetime.fromisoformat(str(sc['ko']).replace('Z','+00:00'))
   day=ko.astimezone(TZ).date().isoformat()
   if str(p['date'])!=ko.date().isoformat():issues['source_utc_date_mismatch']+=1;continue
   line=float(p['end_line']);ho=float(p['home_price']);ao=float(p['away_price'])
   if min(ho,ao)<=1 or abs(line*4-round(line*4))>1e-8:issues['invalid_crown_price_or_line']+=1;continue
   schedule_verified=m is not None
  except Exception:issues['invalid_score_or_quote_fields']+=1;continue
  fav='home' if ho<=ao else 'away';dog='away' if fav=='home' else 'home'
  pnl={};states={}
  for side in ('home','away'):
   pnl[side],states[side]=score(side,line,ho,ao,hg,ag)
  if abs(pnl['home']-float(p.get('end_home_U') or 0))>1e-8 or abs(pnl['away']-float(p.get('end_away_U') or 0))>1e-8:
   issues['path_settlement_mismatch']+=1;continue
  price_time=p.get('date')
  fixtures.append({'fid':fid,'league':str(p['league']),'league_name':league_meta.get(str(p['league']),{}).get('name','unmapped'),
   'year':int(day[:4]),'date':day,'iso_week':dt.date.fromisoformat(day).strftime('%G-W%V'),'home_id':str(sc['home']),'away_id':str(sc['away']),'ko_utc':ko.isoformat(),
   'home':(m or {}).get('h'),'away':(m or {}).get('a'),'schedule_identity_verified':schedule_verified,'home_line':line,'home_odds':ho,'away_odds':ao,'favorite_side':fav,'underdog_side':dog,
   'FT_home':hg,'FT_away':ag,'home_net_u':pnl['home'],'away_net_u':pnl['away'],'home_settlement':states['home'],'away_settlement':states['away'],
   'frozen_eight':fid in frozen,'frozen_pnl':float(frozen[fid]['pnl']) if fid in frozen else None,
   'raw_http_body_available':fid in rawids,'source_type':'historical Crown source-event T1 replay; not actual receipt'})
 # Training policy: for each league/year, choose prior FAV vs DOG with higher cumulative net U per wager.
 # No yearly parameter tuning, no league/line/price filters, no minimum-sample gate.
 by_lid=collections.defaultdict(list)
 for r in fixtures:by_lid[r['league']].append(r)
 predictions=[]; train_decisions={}
 for lid,rows in by_lid.items():
  for year in YEARS:
   hist=[r for r in rows if r['year']<year]
   target=[r for r in rows if r['year']==year]
   if not target:continue
   fav_u=sum(r['home_net_u'] if r['favorite_side']=='home' else r['away_net_u'] for r in hist)
   dog_u=sum(r['home_net_u'] if r['underdog_side']=='home' else r['away_net_u'] for r in hist)
   fav_roi=fav_u/len(hist) if hist else None;dog_roi=dog_u/len(hist) if hist else None
   # Tie or no history deterministically defaults to Crown favorite.
   choice='underdog' if hist and dog_u>fav_u else 'favorite'
   train_decisions[f'{lid}:{year}']={'league':lid,'league_name':league_meta.get(lid,{}).get('name','unmapped'),'test_year':year,'train_n':len(hist),
    'train_years':sorted({r['year'] for r in hist}),'favorite_train_net_u':round(fav_u,6),'underdog_train_net_u':round(dog_u,6),
    'favorite_train_roi_pct':round(100*fav_roi,6) if fav_roi is not None else None,'underdog_train_roi_pct':round(100*dog_roi,6) if dog_roi is not None else None,'selected_side':choice,
    'selection_rule':'select prior side with larger cumulative per-wager net U; tie/no prior history=>favorite; no target-year outcomes used'}
   for r in target:
    side=r['favorite_side'] if choice=='favorite' else r['underdog_side']
    predictions.append({**r,'strategy':'league_prior_favorite_vs_underdog','selected_prior_side':choice,'direction':side,
     'settlement':r[f'{side}_settlement'],'net_u':r[f'{side}_net_u'],'training_n':len(hist)})
    predictions.append({**r,'strategy':'universal_crown_favorite_baseline','selected_prior_side':'favorite','direction':r['favorite_side'],
     'settlement':r[f"{r['favorite_side']}_settlement"],'net_u':r[f"{r['favorite_side']}_net_u"],'training_n':len(hist)})
    predictions.append({**r,'strategy':'universal_crown_underdog_baseline','selected_prior_side':'underdog','direction':r['underdog_side'],
     'settlement':r[f"{r['underdog_side']}_settlement"],'net_u':r[f"{r['underdog_side']}_net_u"],'training_n':len(hist)})
 # Metrics.
 def metrics(rs):
  if not rs:return {'n':0,'net_u':0.0,'roi_pct':None,'mdd_u':0.0,'weekly_mean_orders_active_weeks':None,'five_state':{},'year':{},'weekly':{},'league':{}}
  rs=sorted(rs,key=lambda r:(r['date'],r['fid']))
  n=len(rs);u=sum(float(r['net_u']) for r in rs);equity=peak=dd=0.;daily=collections.defaultdict(float)
  for r in rs:daily[r['date']]+=float(r['net_u'])
  for d in sorted(daily):
   equity+=daily[d];peak=max(peak,equity);dd=max(dd,peak-equity)
  counts=collections.Counter(r['settlement'] for r in rs)
  weekly=collections.defaultdict(lambda:{'n':0,'net_u':0.})
  annual=collections.defaultdict(list);league=collections.defaultdict(list)
  for r in rs:
   w=weekly[r['iso_week']];w['n']+=1;w['net_u']+=float(r['net_u'])
   annual[str(r['year'])].append(r);league[r['league_name']].append(r)
  weekkeys=sorted(weekly)
  ncalendar=0
  if weekkeys:
   d0=dt.date.fromisocalendar(int(weekkeys[0][:4]),int(weekkeys[0][-2:]),1)
   d1=dt.date.fromisocalendar(int(weekkeys[-1][:4]),int(weekkeys[-1][-2:]),1)
   ncalendar=((d1-d0).days//7)+1
  def mini(x):
   nn=len(x);uu=sum(float(a['net_u']) for a in x);return {'n':nn,'net_u':round(uu,6),'roi_pct':round(100*uu/nn,6) if nn else None}
  return {'n':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6),'mdd_u':round(dd,6),
   'weekly_mean_orders_active_weeks':round(n/len(weekly),6) if weekly else None,'weekly_mean_orders_calendar_span':round(n/ncalendar,6) if ncalendar else None,
   'active_iso_weeks':len(weekly),'calendar_iso_week_span':ncalendar,'five_state':dict(counts),
   'year':{y:mini(x) for y,x in sorted(annual.items())},'weekly':{w:{'n':v['n'],'net_u':round(v['net_u'],6)} for w,v in sorted(weekly.items())},
   'league':{l:mini(x) for l,x in sorted(league.items())}}
 # main test pool all non-frozen and explicit 2022-26.
 result_by_strategy={}
 for strategy in ('league_prior_favorite_vs_underdog','universal_crown_favorite_baseline','universal_crown_underdog_baseline'):
  sr=[r for r in predictions if r['strategy']==strategy and not r['frozen_eight']]
  result_by_strategy[strategy]=metrics(sr)
 # all-unique same-date frozen baseline & combined outcomes for each strategy.
 # Frozen book membership rows are authoritative only for frozen PnL; candidates are only outside-eight IDs.
 frozen_window=[]
 for r in mem_rows:
  try:y=int(r['date'][:4])
  except:continue
  if y in YEARS:
   frozen_window.append({'fid':str(r['fid']),'league':str(r.get('league','')),'year':y,'date':r['date'],
    'iso_week':dt.date.fromisoformat(r['date']).strftime('%G-W%V'),'settlement':'frozen_original_eight','net_u':float(r['pnl']),'frozen_eight':True,'league_name':league_meta.get(str(r.get('league','')),{}).get('name','unknown')})
 combined={}
 for strategy in result_by_strategy:
  candidates=[r for r in predictions if r['strategy']==strategy and not r['frozen_eight']]
  # unique FID union, candidates never overlap eight after explicit exclusion
  allrows=frozen_window+[{k:r[k] for k in ('fid','league','league_name','year','date','iso_week','settlement','net_u','frozen_eight')} for r in candidates]
  assert len({r['fid'] for r in allrows})==len(allrows)
  combined[strategy]=metrics(allrows)
 # requested league coverage details.
 req_ids={name:[] for name in REQUESTED}
 for lid,meta in league_meta.items():
  text=f"{meta.get('name','')} {meta.get('country','')}"
  for nm,pat in REQUESTED.items():
   if re.search(pat,text,re.I):req_ids[nm].append(lid)
 fixtures_by_lid=collections.defaultdict(list)
 for r in fixtures:fixtures_by_lid[r['league']].append(r)
 # study target cohort counts and historical broad-source participation.
 intensive_by_lid=collections.Counter()
 for fid in intensive_ids:
  p=paths.get(fid)
  if p:intensive_by_lid[str(p['league'])]+=1
 coverage=[]
 requested_ids=set(x for ids in req_ids.values() for x in ids)
 for lid,meta in sorted(league_meta.items(),key=lambda x:(x[1].get('country',''),x[1].get('name',''),x[0])):
  fr=fixtures_by_lid.get(lid,[])
  if not fr and lid not in requested_ids:continue
  per_year={}
  for y in YEARS:
   py=[r for r in fr if r['year']==y]
   per_year[str(y)]={'crown_ah_fids':len({r['fid'] for r in py}),'trusted_ft_fids':len({r['fid'] for r in py}),'schedule_identity_verified_fids':sum(r.get('schedule_identity_verified',False) for r in py),
    'frozen_eight_fids':sum(r['frozen_eight'] for r in py),'outside_eight_fids':sum(not r['frozen_eight'] for r in py),
    'previous_intensive_target_fids':sum(r['fid'] in intensive_ids for r in py),
    'raw_crown_response_bodies':sum(r['raw_http_body_available'] for r in py),
    'audited_m8_http_receipt_fids':0}
  receipt_count=collections.Counter();m8receipt_count=collections.Counter()
  for fid,rr in receipt_registry.items():
   if str(rr.get('league_id') or '')==lid:
    # All receipt archives in this audited snapshot set are 2026 receipts; use per-record time for exact year.
    yy=set()
    for det in rr.get('receipt_details',[]):
     rv=det.get('received_utc') or ''
     if rv:yy.add(rv[:4])
    for yr in yy or {'2026'}:receipt_count[str(yr)]+=1
    if 'M8_AH_FT_independent_audit' in rr['sources']:m8receipt_count['2026']+=1
  for y in YEARS:
   per_year[str(y)]['all_actual_http_receipt_unique_fids']=receipt_count[str(y)]
   per_year[str(y)]['m8_audited_actual_receipt_with_ft_fids']=m8receipt_count[str(y)]
  coverage.append({'league_id':lid,'league_name':meta.get('name',''),'country':meta.get('country',''),
   'requested_named_scope':[n for n,ids in req_ids.items() if lid in ids],
   'cached_schedule_fids_2022_2026':sum(sch_summary[(lid,str(y))]['matches'] for y in YEARS),
   'cached_schedule_trusted_ft_2022_2026':sum(sch_summary[(lid,str(y))]['trusted_schedule_ft'] for y in YEARS),
   'path_crown_ah_fids_2022_2026':sum(x['crown_ah_fids'] for x in per_year.values()),
   'trusted_ft_path_fids_2022_2026':sum(x['trusted_ft_fids'] for x in per_year.values()),
   'schedule_identity_verified_path_fids_2022_2026':sum(x['schedule_identity_verified_fids'] for x in per_year.values()),
   'frozen_eight_fids_2022_2026':sum(x['frozen_eight_fids'] for x in per_year.values()),
   'outside_eight_unique_fids_2022_2026':sum(x['outside_eight_fids'] for x in per_year.values()),
   'previous_intensive_target_fids_2024_2026':intensive_by_lid[lid],
   'raw_crown_response_body_fids_2022_2026':sum(x['raw_crown_response_bodies'] for x in per_year.values()),
   'all_actual_http_receipt_unique_fids':sum(receipt_count.values()),'m8_audited_actual_receipt_with_ft_fids':sum(m8receipt_count.values()),'by_year':per_year,
   'all_history_crown_path_fids':sum(1 for r in paths.values() if str(r['league'])==lid),
   'historically_researched_input_universe':sum(1 for r in paths.values() if str(r['league'])==lid),
   'note':'Path FID quote/FT identity was independently linked through saved Crown schedule and score FID; schedule cache may be incomplete and is not treated as Crown AH price coverage.'})
 # compute per-strategy per-league/year and per-week detailed result.
 league_results={}
 for strategy in result_by_strategy:
  sub=[r for r in predictions if r['strategy']==strategy and not r['frozen_eight']]
  league_results[strategy]={}
  for lid,meta in sorted(league_meta.items()):
   rrs=[r for r in sub if r['league']==lid]
   if not rrs:continue
   league_results[strategy][lid]={'league_name':meta.get('name',''),'overall_2022_2026':metrics(rrs),
    'by_year':{str(y):metrics([r for r in rrs if r['year']==y]) for y in YEARS},
    'prior_choices':{str(y):train_decisions.get(f'{lid}:{y}') for y in YEARS if f'{lid}:{y}' in train_decisions}}
 # evaluation source receipts. Select M8 independently audited rows only; one quote/FT per FID, prices must agree across repeated model rows.
 receipt_preds=[]
 for r in receipt_rows:
  fid=str(r['fid']);lid=str(r.get('schedule_league_id') or '')
  if not lid:continue
  recdate=str(r.get('date') or '')
  if not recdate:
   try:recdate=dt.datetime.fromisoformat(str(r['kickoff_utc']).replace('Z','+00:00')).astimezone(TZ).date().isoformat()
   except Exception:continue
  y=int(recdate[:4]);historical=[x for x in fixtures if x['league']==lid and x['date']<=(dt.date.fromisoformat(recdate)-dt.timedelta(days=3)).isoformat()]
  # use all prior eligible history before receipt date; no target FID can enter training.
  fu=sum(x['home_net_u'] if x['favorite_side']=='home' else x['away_net_u'] for x in historical)
  du=sum(x['home_net_u'] if x['underdog_side']=='home' else x['away_net_u'] for x in historical)
  choice='underdog' if historical and du>fu else 'favorite'
  line=float(r['line_home']);ho=float(r['odds_home']);ao=float(r['odds_away']);hg,ag=map(int,str(r['ft']).split('-'))
  fav='home' if ho<=ao else 'away';dog='away' if fav=='home' else 'home';side=fav if choice=='favorite' else dog
  pnl,state=score(side,line,ho,ao,hg,ag)
  favp,favs=score(fav,line,ho,ao,hg,ag)
  receipt_preds.append({'fid':fid,'league':lid,'league_name':league_meta.get(lid,{}).get('name','unmapped'),'year':y,'date':recdate,
   'iso_week':dt.date.fromisoformat(recdate).strftime('%G-W%V'),'home_line':line,'home_odds':ho,'away_odds':ao,'direction':side,'selected_prior_side':choice,
   'favorite_side':fav,'FT_home':hg,'FT_away':ag,'settlement':state,'net_u':pnl,'favorite_net_u':favp,'favorite_settlement':favs,
   'training_n':len(historical),'received_utc':r.get('received_utc'),'raw_sha256':r.get('raw_sha256'),'snapshot_sha256':r.get('snapshot_sha256'),
   'quote_type':'audited actual HTTP Crown receipt','training_history_received_time_proven':False,'duplicate_model_rows_collapsed':True,
   'frozen_eight':str(r['fid']) in frozen})
 # receipt rows may be already out8-only; guarantee FID dedupe.
 receipt_unique={}
 for r in receipt_preds:
  if r['fid'] not in receipt_unique or str(r.get('received_utc') or '')<str(receipt_unique[r['fid']].get('received_utc') or ''):receipt_unique[r['fid']]=r
 receipt_preds=list(receipt_unique.values())
 receipt_result={}
 for strategy,field in [('league_prior_favorite_vs_underdog','net_u'),('universal_crown_favorite_baseline','favorite_net_u')]:
  rr=[r for r in receipt_preds if not r['frozen_eight']]
  use=[]
  for r in rr:
   use.append({**r,'strategy':strategy,'net_u':r[field]})
  receipt_result[strategy]=metrics(use)
 # Merge the exact frozen-book FIDs falling inside this audited six-week receipt window, by unique FID.
 receipt_week_keys=sorted({r['iso_week'] for r in receipt_preds})
 receipt_union={}
 if receipt_week_keys:
  lo,hi=receipt_week_keys[0],receipt_week_keys[-1]
  frows=[r for r in frozen_window if lo<=r['iso_week']<=hi]
  for strategy in receipt_result:
   cc=[r for r in receipt_preds if not r['frozen_eight']]
   if strategy=='universal_crown_favorite_baseline':cc=[{**r,'net_u':r['favorite_net_u'],'settlement':r['favorite_settlement']} for r in cc]
   allr=frows+[{k:r[k] for k in ('fid','league','league_name','year','date','iso_week','settlement','net_u','frozen_eight')} for r in cc]
   assert len({r['fid'] for r in allr})==len(allr)
   receipt_union[strategy]=metrics(allr)
 # write complete prediction ledger (unique FID per method, three model rows currently duplicated purposeful)
 with gzip.open(OUT/'per_fixture_league_predictions_20261120.jsonl.gz','wt',encoding='utf-8') as f:
  for r in sorted(predictions,key=lambda x:(x['date'],x['fid'],x['strategy'])):f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 with gzip.open(OUT/'actual_receipt_replay_per_fixture_20261120.jsonl.gz','wt',encoding='utf-8') as f:
  for r in sorted(receipt_preds,key=lambda x:(x['date'],x['fid'])):f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 with gzip.open(OUT/'actual_receipt_coverage_registry_20261120.jsonl.gz','wt',encoding='utf-8') as f:
  for fid,r in sorted(receipt_registry.items()):f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 with (OUT/'coverage_by_league_20261120.jsonl').open('w') as f:
  for r in coverage:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 result={'study':'M8 requested mainstream leagues plus all other leagues represented in existing Crown AH paths. New, fixed-menu league-local prior favorite-versus-underdog payoff selection; no target-year tuning.','as_of_beijing':'2026-11-20','quote_source':'Historical Crown AH source-event T1 path; not actual received HTTP quotes.','settlement':'Independently implemented single and quarter-line two-leg Asian handicap settlement; 1U per candidate fixture.','coverage_sources':{'path':str(PATHF),'path_sha256':sha_file(PATHF),'score':str(SCOREF),'score_sha256':sha_file(SCOREF),'membership':str(MEMF),'membership_sha256':sha_file(MEMF),'schedule_page_count':pages,'schedule_unique_fids':len(schedules),'response_index_sha256':sha_file(RESPIDX),'response_body_files':len(bodies),'body_and_index_with_prematch_ah':len(rawids),'intensive_2024_26_target_ids':len(intensive_ids),'receipt_rows_by_source':receipt_source_counts,'m8_audited_receipt_method_rows':sum(1 for p in [RECEIPT_FILES[0]] if p.exists() for _ in read_jsonl(p)),'m8_receipt_unique_fids_with_quote_agreement':len(receipt_rows),'m8_receipt_quote_conflicts':len(receipt_conflicts),'all_receipt_registry_unique_fids':len(receipt_registry),'all_receipt_registry_unmapped_to_league':sum(1 for x in receipt_registry.values() if not x.get('league_id')),'all_receipt_fid_union':len(receipt_ids)},
  'input_counts':{'raw_path_rows':len(path_rows),'unique_path_fids':len(paths),'score_rows':len(score_rows),'unique_score_fids':len(scores),'frozen_membership_rows':len(mem_rows),'unique_frozen_fids':len(frozen),'path_score_fid_ft_validated_fids':len(fixtures),'schedule_identity_verified_fids':sum(r.get('schedule_identity_verified',False) for r in fixtures),
   'intensive_2024_26_target_fids_found_in_path_score':len(intensive_ids & {r['fid'] for r in fixtures}),'intensive_2024_26_target_fids_not_found':len(intensive_ids-{r['fid'] for r in fixtures}),'excluded_link_issues':dict(issues),'target_years':[2022,2023,2024,2025,2026],'candidate_unique_fids_2022_2026':len({r['fid'] for r in fixtures if r['year'] in YEARS and not r['frozen_eight']}),'candidate_frozen_overlap':sum(r['frozen_eight'] for r in fixtures if r['year'] in YEARS)},
  'requested_league_ids':req_ids,'requested_scope_missing_crown_path':[n for n,ids in req_ids.items() if not ids or not any(x['league_id'] in ids and x['path_crown_ah_fids_2022_2026'] for x in coverage)],
  'coverage_by_league':coverage,'strategy_results_outside_original_eight':result_by_strategy,'frozen_eight_baseline_2022_2026':metrics(frozen_window),
  'frozen_eight_union_by_strategy':combined,'actual_http_receipt_replay_outside_original_eight':receipt_result,
  'frozen_eight_actual_receipt_window_baseline':metrics([r for r in frozen_window if receipt_week_keys and receipt_week_keys[0]<=r['iso_week']<=receipt_week_keys[-1]]),
  'frozen_eight_actual_receipt_window_union_by_strategy':receipt_union,
  'league_strategy_results_outside_original_eight':league_results,'annual_training_side_choices':train_decisions,
  'receipts':{'unique_m8_candidate_rows':len(receipt_preds),'m8_audited_unique_fids_with_quote_agreement':len({r['fid'] for r in receipt_rows}),'m8_audited_outside_eight_mapped_rows':sum(not r['frozen_eight'] for r in receipt_preds),'m8_audited_outside_eight_unmapped_to_league':sum(1 for x in receipt_registry.values() if 'M8_AH_FT_independent_audit' in x['sources'] and not x.get('league_id') and x['fid'] not in frozen),'net_replay_is_retrospective':True,'history_features_first_seen_timestamp_proven':False,'methods':receipt_result},
  'known_prior_study':'The same 39,101-FID Crown path input has been repeatedly explored. The 2024-2026 21,455-FID target set is explicitly listed in next_round_20261120; all 39,101 rows were also prior broad research inputs. This is not new historical FID coverage. This experiment is a new predeclared mechanism test only, and the data are not unseen.'}
 (OUT/'M8_MAINSTREAM_LEAGUE_RESULTS_20261120.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'validated_fixtures':len(fixtures),'coverage_leagues':len(coverage),'requests':req_ids,'strategies':{k:{x:v for x,v in m.items() if x not in ('year','weekly','league')} for k,m in result_by_strategy.items()},'combined':{k:{x:v for x,v in m.items() if x not in ('year','weekly','league')} for k,m in combined.items()},'receipt':receipt_result},ensure_ascii=False,indent=2))
if __name__=='__main__':run()
