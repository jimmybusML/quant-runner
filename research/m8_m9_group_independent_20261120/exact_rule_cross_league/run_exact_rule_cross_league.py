#!/usr/bin/env python3
"""Exact frozen M8 base/A-G rules on the 15 provider leagues outside frozen 49.
Research-only; reads existing Crown SQLite and TotalCorner schedule archive.
"""
from __future__ import annotations
import bisect, collections, datetime as dt, gzip, hashlib, json, math, pathlib, sqlite3, statistics
from zoneinfo import ZoneInfo
import sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from research.m3.probabilities import settle_score

OUT=pathlib.Path(__file__).resolve().parent
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
SCHEDULE=WORK/'crown-drop-expanded-62/schedule_universe.jsonl'
FOUNDATION=WORK/'m8_foundation_20261115/historical_membership.jsonl'
GROUPS=('base','A','B','C','D','E','F','G')
OLD49=set('1 10480 109 116 12 14 141 1439 145 152 16 177 25 262 26540 29 290 297 298 299 303 31 319 328 330 332 345 35 37 40 43 45 46 47 48 51 52 55 60 61 62 66 68 70 73 75 8172 88 979'.split())
TZ=ZoneInfo('Asia/Shanghai'); UTC=dt.timezone.utc

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def parse_dt(s):
 x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return x.astimezone(UTC) if x.tzinfo else x.replace(tzinfo=TZ).astimezone(UTC)
def sign(x,eps=1e-9): return 1 if x>eps else -1 if x<-eps else 0
def prob(q): return q[3]/(q[2]+q[3])
def state(x,y,end):
 z=(y-x)*end
 return 'deepen' if z>1e-9 else 'weaken' if z<-1e-9 else 'same'
def poisson(lam,kmax=40):
 p=[math.exp(-lam)]
 for j in range(1,kmax): p.append(p[-1]*lam/j)
 return p

def expected_ev(line,home_odds,away_odds,rates):
 hp,ap=map(poisson,rates); wh=lh=wa=la=0.
 legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 for leg in legs:
  for i,pi in enumerate(hp):
   for j,pj in enumerate(ap):
    m=i-j+leg; mass=pi*pj/len(legs)
    if m>1e-9: wh+=mass
    elif m<-1e-9: lh+=mass
    ma=j-i-leg
    if ma>1e-9: wa+=mass
    elif ma<-1e-9: la+=mass
 return wh*(home_odds-1)-lh,wa*(away_odds-1)-la

def model_direction(line,h,a,rates):
 eh,ea=expected_ev(line,h,a,rates)
 return sign(eh-ea) or 1,eh,ea

# Original saved dynamic independent score model: league baseline plus decayed
# team attack/defence residual updates; only results at least two calendar days
# before a target may update its rates.
attack=collections.defaultdict(float); defense=collections.defaultdict(float)
baseline=collections.defaultdict(lambda:[math.log(1.45),math.log(1.15)])
def pred_rates(r):
 l=str(r['league_id']); ht=(l,str(r['home_id'])); at=(l,str(r['away_id'])); b=baseline[l]
 return (math.exp(max(-2.5,min(2.3,b[0]+attack[ht]+defense[at]))),
         math.exp(max(-2.5,min(2.3,b[1]+attack[at]+defense[ht]))))
def update_score(r):
 l=str(r['league_id']); h=(l,str(r['home_id'])); a=(l,str(r['away_id'])); b=baseline[l]
 x,y=pred_rates(r); e1=int(r['home_goals'])-x; e2=int(r['away_goals'])-y
 for k,e in ((h,e1),(a,e2)): attack[k]=.997*attack[k]+.025*max(-4.,min(4.,e))
 for k,e in ((a,e1),(h,e2)): defense[k]=.997*defense[k]+.025*max(-4.,min(4.,e))
 b[0]+=.003*max(-4.,min(4.,e1)); b[1]+=.003*max(-4.,min(4.,e2))

def all_triggers(r):
 """Independent predicates behind the exact priority chain; no thresholds added."""
 p=r['path']; start,mid,end=p; l=end[1]; sl=start[1]; ml=mid[1]
 seq=[q for q in p if start[0]<=q[0]<=end[0]]
 steps=[(u,v) for u,v in zip(seq,seq[1:]) if u[1]!=v[1]]
 shape='never_changed' if not steps else 'reverted' if sl==l else 'one_way' if all((v[1]-u[1])*(l-sl)>0 for u,v in steps) else 'oscillating'
 out=[]
 if (l-sl)*l>1e-9: out.append('base')
 if l and state(sl,ml,l)=='deepen' and state(ml,l,l)=='weaken': out.append('A')
 if l and state(sl,ml,l)=='weaken' and state(ml,l,l)=='same': out.append('B')
 if l and shape=='oscillating': out.append('C')
 if abs(l)<1e-9 and shape=='reverted':
  dur=sh=sa=0.
  for n,q in enumerate(seq):
   if abs(q[1])>1e-9: continue
   lo=max(start[0],q[0]); hi=seq[n+1][0] if n+1<len(seq) else end[0]
   d=max(0.,(hi-lo).total_seconds());dur+=d;sh+=d*q[2];sa+=d*q[3]
  if dur and (end[2]-sh/dur)-(end[3]-sa/dur)<-1e-9: out.append('D')
 if abs(l)<1e-9 and shape=='never_changed':
  p0,p3,p1=map(prob,(start,mid,end)); a=sign(p3-p0); b=sign(p1-p3); net=sign(p1-p0)
  moves=[prob(v)-prob(u) for u,v in zip(seq,seq[1:]) if abs(prob(v)-prob(u))>1e-10]
  s=net or a or b or sign(moves[-1] if moves else 0)
  if s and moves:
   up=any(z>0 for z in moves); down=any(z<0 for z in moves)
   if up and down and not net: out.append('E')
   if (not up or not down) and a==0 and b*s==1: out.append('F')
 if shape=='reverted' and r.get('score_rates'):
  market=sign(prob(end)-prob(start)); model,_,_=model_direction(l,end[2],end[3],r['score_rates'])
  if market and market==model: out.append('G')
 return out,shape,seq

def assign(r):
 hits,shape,seq=all_triggers(r)
 # Frozen priority is the source chain order: base, A, B, C, D, E, F, G.
 group=next((g for g in GROUPS if g in hits),None)
 l=r['path'][-1][1]
 if group in ('base','A','B'): side=('home' if l>0 else 'away') if l else None
 elif group=='C': side=('away' if l>0 else 'home') if l else None
 elif group=='D': side='away'
 elif group=='E':
  p0,p3,p1=map(prob,r['path']);a=sign(p3-p0);b=sign(p1-p3);net=sign(p1-p0)
  last=sign(prob(seq[-1])-prob(seq[-2])) if len(seq)>1 else 0
  s=net or a or b or last;side=('away' if s>0 else 'home') if s else None
 elif group=='F':
  a=sign(prob(r['path'][1])-prob(r['path'][0]));b=sign(prob(r['path'][2])-prob(r['path'][1]));net=sign(prob(r['path'][2])-prob(r['path'][0]));s=net or a or b
  side=('home' if s>0 else 'away') if s else None
 elif group=='G':
  market=sign(prob(r['path'][2])-prob(r['path'][0])); model,_,_=model_direction(l,r['path'][2][2],r['path'][2][3],r['score_rates'])
  side=('away' if model>0 else 'home') if market and market==model else None
 else: side=None
 return group,side,hits,shape,seq

def cashflow(line,side,hg,ag,price):
 state0,pnl=settle_score('AH',float(line),side,int(hg),int(ag),float(price))
 return state0.lower(),float(pnl)

def stat(rows):
 n=len(rows);u=sum(x['net_u'] for x in rows);d=collections.defaultdict(lambda:[0,0.])
 for x in rows:
  date=x['kickoff_beijing'][:10]; d[date][0]+=1;d[date][1]+=x['net_u']
 cum=peak=mdd=0.
 for day,(nn,uu) in sorted(d.items()):cum+=uu;peak=max(peak,cum);mdd=max(mdd,peak-cum)
 weeks=collections.defaultdict(lambda:[0,0.])
 for x in rows:
  day=dt.date.fromisoformat(x['kickoff_beijing'][:10]); iso=day.isocalendar();k=f'{iso.year}-W{iso.week:02d}';weeks[k][0]+=1;weeks[k][1]+=x['net_u']
 if not rows: return {'n':0,'net_U':0.,'ROI_pct':None,'max_drawdown_U':0.,'calendar_weeks':0,'avg_orders_per_calendar_week':0.,'active_weeks':0,'weekly':{}}
 d0=min(dt.date.fromisoformat(x['kickoff_beijing'][:10]) for x in rows);d1=max(dt.date.fromisoformat(x['kickoff_beijing'][:10]) for x in rows);cw=(d1-d0).days//7+1
 return {'n':n,'net_U':round(u,6),'ROI_pct':round(100*u/n,6),'max_drawdown_U':round(mdd,6),'calendar_weeks':cw,'avg_orders_per_calendar_week':round(n/cw,6),'active_weeks':len(weeks),'positive_weeks':sum(v[1]>1e-10 for v in weeks.values()),'negative_weeks':sum(v[1]<-1e-10 for v in weeks.values()),'weekly':{k:{'n':v[0],'net_U':round(v[1],6)} for k,v in sorted(weeks.items())}}

def main():
 assert DB.exists() and SCHEDULE.exists() and FOUNDATION.exists()
 frozen=[json.loads(x) for x in FOUNDATION.open() if x.strip()]; frozen_ids={str(x['fid']) for x in frozen}
 assert len(frozen_ids)==10294
 all_schedule=[json.loads(x) for x in SCHEDULE.open() if x.strip()]
 assert len(all_schedule)==96504 and len({str(x['match_id']) for x in all_schedule})==96504
 outside=[r for r in all_schedule if str(r['league_id']) not in OLD49]
 assert len(OLD49)==49 and len(outside)==18374 and len({str(x['league_id']) for x in outside})==15
 assert not frozen_ids.intersection(str(x['match_id']) for x in outside)
 # Schedule records are already finished fixtures, but retain only valid exact identity/FT.
 for r in outside:
  r['match_id']=str(r['match_id']);r['league_id']=str(r['league_id']);r['home_id']=str(r.get('home_id') or '')
 # Canonical schedule rows do not include provider team IDs. Crown raw fixture will supply them.
 ids=[r['match_id'] for r in outside]; byid={r['match_id']:r for r in outside}
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True);cx.row_factory=sqlite3.Row
 capmap={}
 for j in range(0,len(ids),700):
  chunk=ids[j:j+700];marks=','.join('?' for _ in chunk)
  sql=f'''SELECT c.fixture_id,c.data_layer,c.capture_mode,c.response_received_at_utc,c.processed_at_utc,c.source_file,c.response_sha256,c.kickoff_at_utc,c.prospective_observation,c.quote_count,c.status
  FROM capture c WHERE c.capture_mode='historical' AND c.fixture_id IN ({marks}) AND c.data_layer='movement'
  ORDER BY c.fixture_id,c.quote_count DESC,c.processed_at_utc DESC'''
  for z in cx.execute(sql,chunk): capmap.setdefault(str(z['fixture_id']),[]).append(dict(z))
 cx.close()
 # Select one most complete movement capture per event and validate response SHA + identity/FT.
 coverage_rows=[];selected_raw={};preliminary={}
 for r in outside:
  fid=r['match_id']; caps=capmap.get(fid,[])
  rec={'fid':fid,'league_id':r['league_id'],'source_league':r.get('source_league'),'kickoff_beijing':str(r['kickoff_source_local']),'schedule_home':r['home'],'schedule_away':r['away'],'FT_home':r['home_goals'],'FT_away':r['away_goals'],'capture_rows':len(caps),'capture_status_counts':dict(collections.Counter(c['status'] for c in caps)),'status':'no_movement_capture'}
  chosen=next((c for c in caps if int(c['quote_count'])>0),None)
  if not chosen:
   rec['status']='movement_capture_without_quotes' if caps else 'no_movement_capture';coverage_rows.append(rec);continue
  path=pathlib.Path(chosen['source_file'])
  try: raw=path.read_bytes()
  except Exception as e: rec['status']='raw_response_missing';rec['raw_error']=type(e).__name__;coverage_rows.append(rec);continue
  if sha_bytes(raw)!=chosen['response_sha256']:
   rec['status']='raw_sha_mismatch';coverage_rows.append(rec);continue
  try: body=json.loads(raw); fixture=next(x for x in body.get('data',[]) if str(x.get('id'))==fid)
  except Exception as e: rec['status']='raw_fixture_missing';rec['raw_error']=type(e).__name__;coverage_rows.append(rec);continue
  if str(fixture.get('l_id'))!=r['league_id']:
   rec['status']='league_id_mismatch';coverage_rows.append(rec);continue
  try:
   ko=parse_dt(fixture['start']); expected=parse_dt(r['kickoff_source_local'])
   ft=(int(fixture['hg']),int(fixture['ag']))
   same=(ko==expected and ft==(int(r['home_goals']),int(r['away_goals'])) and str(fixture.get('h'))==str(r['home']) and str(fixture.get('a'))==str(r['away']))
  except Exception: same=False
  if not same:
   rec['status']='fixture_or_FT_mismatch';coverage_rows.append(rec);continue
  bookmaker=next((b for b in fixture.get('bookmakers',[]) if b.get('slug')=='crown'),None)
  if bookmaker is None: rec['status']='no_crown_in_verified_body';coverage_rows.append(rec);continue
  quotes=[]; badq=0
  for item in bookmaker.get('asian_list') or []:
   try:
    t=parse_dt(item[4]);line,ho,ao=map(float,item[1:4])
    if t<ko and ho>1 and ao>1 and all(math.isfinite(v) for v in (line,ho,ao)) and abs(line*4-round(line*4))<1e-8:
     quotes.append((t,line,ho,ao))
   except Exception: badq+=1
  quotes.sort(key=lambda x:x[0])
  rec.update({'status':'verified_raw','raw_sha256':chosen['response_sha256'],'quote_count_raw':len(quotes),'bad_quote_rows':badq,'earliest_quote_utc':quotes[0][0].isoformat() if quotes else None,'latest_pregame_quote_utc':quotes[-1][0].isoformat() if quotes else None,'quote_source_after_receipt_count':sum(q[0]>parse_dt(chosen['response_received_at_utc']) for q in quotes),'actual_http_received_at_utc':chosen['response_received_at_utc'],'prospective_observation':bool(chosen['prospective_observation']),'capture_layer':chosen['data_layer']})
  selected_raw[fid]={'fixture':fixture,'path':quotes,'capture':chosen,'source_file':str(path),'sha256':chosen['response_sha256'],'kickoff':ko}
  # Classify path completeness against the original frozen T6/T3/T1 cutoffs.
  cuts=[ko-dt.timedelta(hours=h) for h in (6,3,1)]
  indexes=[bisect.bisect_right([x[0] for x in quotes],cut)-1 for cut in cuts]
  if not quotes: rec['status']='verified_raw_no_pregame_AH'
  elif indexes[0]<0: rec['status']='no_quote_at_or_before_T6'
  else: rec['status']='complete_T6_T3_T1_path'
  rec['T6_quote_utc']=quotes[indexes[0]][0].isoformat() if indexes[0]>=0 else None
  rec['T3_quote_utc']=quotes[indexes[1]][0].isoformat() if indexes[1]>=0 else None
  rec['T1_quote_utc']=quotes[indexes[2]][0].isoformat() if indexes[2]>=0 else None
  coverage_rows.append(rec)
 # Replay the original independent score model with time-lagged schedule history.
 # It uses the same per-league baseline and team attack/defence residual update;
 # exact schedule team names are the historical identity tokens, and each candidate's
 # names are checked against its SHA-verified Crown raw fixture. Only FT matches at
 # least two China calendar days before the candidate are admitted to the model state.
 outside_leagues={r['league_id'] for r in outside}
 hist=[]
 for x in all_schedule:
  league=str(x['league_id'])
  if league not in outside_leagues: continue
  try:
   day=dt.datetime.fromisoformat(str(x['kickoff_source_local']).replace(' ','T')).date().isoformat()
   hg=int(x['home_goals']);ag=int(x['away_goals'])
   if not x.get('home') or not x.get('away') or hg<0 or ag<0: continue
   hist.append({'fid':str(x['match_id']),'league_id':league,'date':day,'home_id':str(x['home']),'away_id':str(x['away']),'home_goals':hg,'away_goals':ag})
  except Exception: continue
 hist.sort(key=lambda x:(x['date'],x['fid']))
 targets=[]
 for x in outside:
  if x['match_id'] not in selected_raw: continue
  day=dt.datetime.fromisoformat(str(x['kickoff_source_local']).replace(' ','T')).date().isoformat()
  targets.append({'fid':x['match_id'],'league_id':x['league_id'],'date':day,'home_id':str(x['home']),'away_id':str(x['away'])})
 attack.clear();defense.clear();baseline.clear();score_rates={};hist_ix=0
 for target in sorted(targets,key=lambda x:(x['date'],x['fid'])):
  day=dt.date.fromisoformat(target['date'])
  while hist_ix<len(hist) and (day-dt.date.fromisoformat(hist[hist_ix]['date'])).days>=2:
   update_score(hist[hist_ix]);hist_ix+=1
  score_rates[target['fid']]=list(pred_rates(target))
 # Reconstruct exact frozen 6/3/1 rule triggers for every complete path.
 orders=[]; group_raw_hits=collections.Counter(); status_by_league=collections.defaultdict(collections.Counter); status_by_year=collections.defaultdict(collections.Counter); coverage_by_fid={x['fid']:x for x in coverage_rows}
 frozen_overlap=[]; no_rule=[]; trigger_overlap=collections.Counter(); assigned_rule_hits=collections.Counter(); direction_unavailable=collections.Counter()
 for r in outside:
  fid=r['match_id']; cr=coverage_by_fid[fid]; status=cr['status']
  status_by_league[r['league_id']][status]+=1; year=str(r['season_year']);status_by_year[year][status]+=1
  if status!='complete_T6_T3_T1_path': continue
  z=selected_raw[fid];ko=z['kickoff'];path=z['path'];times=[x[0] for x in path];cuts=[ko-dt.timedelta(hours=h) for h in (6,3,1)]
  indexes=[bisect.bisect_right(times,cut)-1 for cut in cuts]
  r0={'fid':fid,'league_id':r['league_id'],'source_league':r['source_league'],'home':r['home'],'away':r['away'],'kickoff_beijing':r['kickoff_source_local'],'year':int(r['season_year']),'path':[path[i] for i in indexes],'score_rates':score_rates.get(fid)}
  group,side,hits,shape,seq=assign(r0)
  for g in hits:group_raw_hits[g]+=1
  if group: assigned_rule_hits[group]+=1
  if len(hits)>1:trigger_overlap['multi_trigger_fid']+=1;trigger_overlap['|'.join(hits)]+=1
  if not group or not side:
   if group and not side: direction_unavailable[group]+=1
   no_rule.append({'fid':fid,'status':'no_exact_rule_match' if not group else 'direction_unavailable','trigger_groups':hits,'path_shape':shape,'G_score_rates_available':bool(r0['score_rates'])});continue
  line,ho,ao=path[indexes[-1]][1:]
  price=ho if side=='home' else ao
  state0,pnl=cashflow(line,side,int(r['home_goals']),int(r['away_goals']),price)
  member=frozen_ids.__contains__(fid)
  if member: frozen_overlap.append(fid)
  times_iso=[q[0].isoformat() for q in path]
  order={'fid':fid,'group':group,'trigger_groups':hits,'priority_assigned_group':group,'home':r['home'],'away':r['away'],'league_id':r['league_id'],'league':r['source_league'],'kickoff_beijing':r['kickoff_source_local'],'year':int(r['season_year']),'iso_week':f"{dt.date.fromisoformat(r['kickoff_source_local'][:10]).isocalendar().year}-W{dt.date.fromisoformat(r['kickoff_source_local'][:10]).isocalendar().week:02d}",'decision_horizon':'T1','T6_source_quote_utc':path[indexes[0]][0].isoformat(),'T3_source_quote_utc':path[indexes[1]][0].isoformat(),'T1_source_quote_utc':path[indexes[2]][0].isoformat(),'AH_line_home':line,'AH_home_odds':ho,'AH_away_odds':ao,'side':side,'selected_odds':price,'FT_home':int(r['home_goals']),'FT_away':int(r['away_goals']),'settlement':state0,'net_u':round(pnl,10),'roi_per_order_pct':round(100*pnl,8),'frozen_10294_overlap':member,'source_type':'historical Crown raw response, retrospective retrieval; not an HTTP pregame receipt','capture_mode':'historical','pregame_http_receipt_verified':False,'t1_source_event_after_http_receipt':path[indexes[-1]][0]>parse_dt(z['capture']['response_received_at_utc']),'response_received_at_utc':z['capture']['response_received_at_utc'],'quote_source_at_utc':path[indexes[-1]][0].isoformat(),'response_sha256':z['sha256'],'source_file':z['source_file'],'model_rates':r0['score_rates'] if group=='G' else None}
  orders.append(order)
 assert len({x['fid'] for x in orders})==len(orders)
 assert not frozen_overlap
 # Group priority de-duplication report; one FID gets exactly one ordered record.
 groups={g:[x for x in orders if x['group']==g] for g in GROUPS}
 union=orders
 years=sorted({int(x['season_year']) for x in all_schedule})
 summary={'study':'M8_EXACT_FROZEN_RULE_CROSS_LEAGUE_REPLAY','execution_utc':dt.datetime.now(UTC).isoformat(),'history_type':'retrospective Crown source-event path replay; not actual pregame receipt or Telegram/formal ledger','frozen_rules':{'groups':list(GROUPS),'priority':list(GROUPS),'frozen_membership_path':str(FOUNDATION),'frozen_membership_sha256':sha_file(FOUNDATION),'frozen_membership_n':len(frozen_ids),'baseline_net_U':236.015,'baseline_ROI_pct':2.293,'old49_provider_league_ids':sorted(OLD49),'old49_count':len(OLD49),'rule_source':'Exact path triggers from research/m8/m8_frozen_eight_boundary_expansion_20261119.py and original 6/3/1 direction logic from research/m8/m8_frozen_eight_earlier_window_replay_20261116.py plus m8_raw_capture_unindexed_frozen_replay_20261115.py. The later helper group_side E endpoint-only formula conflicts with original E path-sign direction; original direction is retained because it exactly reproduces 267/267 frozen E member settlements on historical feature+FT rows.'},'sources':{'schedule_path':str(SCHEDULE),'schedule_sha256':sha_file(SCHEDULE),'schedule_rows':len(all_schedule),'outside49_rows':len(outside),'outside49_unique_fids':len({r['match_id'] for r in outside}),'outside49_provider_league_ids':sorted({r['league_id'] for r in outside}),'crown_sqlite_path':str(DB),'crown_sqlite_sha256':sha_file(DB),'capture_rows_for_outside49':sum(len(v) for v in capmap.values()),'outside49_fids_with_movement_capture':len(capmap),'frozen_membership_sha256':sha_file(FOUNDATION)},'coverage':{'status_counts':dict(collections.Counter(x['status'] for x in coverage_rows)),'per_league':{k:dict(v) for k,v in status_by_league.items()},'per_year':{k:dict(v) for k,v in status_by_year.items()},'complete_path_n':sum(x['status']=='complete_T6_T3_T1_path' for x in coverage_rows),'no_order_reason_counts':dict(collections.Counter(x['status'] for x in no_rule)),'exact_assigned_orders_n':len(orders),'frozen_overlap_n':len(frozen_overlap),'movement_capture_status_counts':dict(collections.Counter(c['status'] for caps in capmap.values() for c in caps)),'movement_capture_fids_with_quote_rows':sum(1 for caps in capmap.values() if any(int(c['quote_count'])>0 for c in caps)),'source_event_pregame_quote_fids':sum(x['status']=='complete_T6_T3_T1_path' or x['status']=='no_quote_at_or_before_T6' for x in coverage_rows),'reference_pre_kickoff_fids_prior_audit':7106},'groups':{g:{'exact_rule_matches_before_direction':assigned_rule_hits[g],'direction_unavailable':direction_unavailable[g],'assigned':stat(groups[g]),'settlement_classes':dict(collections.Counter(x['settlement'] for x in groups[g])),'per_year':{str(y):stat([x for x in groups[g] if x['year']==y]) for y in sorted({x['year'] for x in groups[g]})},'per_league':{l:stat([x for x in groups[g] if x['league_id']==l]) for l in sorted({x['league_id'] for x in groups[g]})}} for g in GROUPS},'deduplicated_union':{'all':stat(union),'settlement_classes':dict(collections.Counter(x['settlement'] for x in union)),'per_year':{str(y):stat([x for x in union if x['year']==y]) for y in sorted({x['year'] for x in union})},'per_league':{l:stat([x for x in union if x['league_id']==l]) for l in sorted({x['league_id'] for x in union})}},'overlap':{'priority_rule_multi_trigger_fids':dict(trigger_overlap),'raw_trigger_counts':dict(group_raw_hits),'raw_trigger_sum':sum(group_raw_hits.values()),'exact_priority_assigned_hits':dict(assigned_rule_hits),'direction_unavailable_by_group':dict(direction_unavailable),'unique_orders_by_group':{g:len(groups[g]) for g in GROUPS},'unique_fids':len({x['fid'] for x in orders})},'G_score_model_method':'Original independent dynamic attack/defence and league-baseline algorithm from m8_raw_capture_unindexed_frozen_replay (same predict/update equations), applied to added-league completed FT history using exact league-scoped schedule team names; each target team name is checked against its SHA-verified Crown raw fixture. Target and same/next Beijing-date results are excluded; only completed matches at least two calendar days earlier update rates. No future identity crosswalk, M9 input or target result enters prediction.','results':{'annual_incremental_orders':{str(y):{'n':sum(x['year']==y for x in union),'avg_per_calendar_week':stat([x for x in union if x['year']==y])['avg_orders_per_calendar_week'],'net_U':stat([x for x in union if x['year']==y])['net_U'],'ROI_pct':stat([x for x in union if x['year']==y])['ROI_pct']} for y in sorted({x['year'] for x in union})},'combined_original8_plus_new':None}}
 # Compute merged reporting arithmetic, while no FID overlap means base frozen set plus new union.
 newnet=sum(x['net_u'] for x in union); newn=len(union); base_n=len(frozen_ids); base_u=236.015
 full_dates=[dt.date.fromisoformat(str(x['kickoff_source_local'])[:10]) for x in outside]
 full_period_weeks=(max(full_dates)-min(full_dates)).days//7+1
 summary['period']={'schedule_first_date':min(full_dates).isoformat(),'schedule_last_date':max(full_dates).isoformat(),'observed_schedule_weeks':full_period_weeks}
 summary['results']['new_incremental']={**stat(union),'net_U':round(newnet,6),'avg_orders_per_full_observed_schedule_week':round(len(union)/full_period_weeks,6)}
 for g in GROUPS: summary['groups'][g]['avg_orders_per_full_observed_schedule_week']=round(len(groups[g])/full_period_weeks,6)
 # Year-level rates use the full observed schedule span in that year, not only active bet weeks.
 observed_year_weeks={}
 for y in sorted({int(x['season_year']) for x in outside}):
  dates=[dt.date.fromisoformat(str(x['kickoff_source_local'])[:10]) for x in outside if int(x['season_year'])==y]
  observed_year_weeks[str(y)]=(max(dates)-min(dates)).days//7+1 if dates else 0
 # Keep the order-only date span as a separate diagnostic, while making the
 # requested annual weekly rate consistent with the full schedule denominator
 # used by the report and merged annual table.
 for y,metric in summary['results']['annual_incremental_orders'].items():
  metric['avg_per_order_date_span_week']=metric.pop('avg_per_calendar_week')
  metric['observed_schedule_weeks']=observed_year_weeks.get(y,0)
  metric['avg_per_observed_schedule_week']=(round(metric['n']/metric['observed_schedule_weeks'],6)
      if metric['observed_schedule_weeks'] else 0.0)
 annual_union={}
 for y in sorted({x['year'] for x in orders}):
  yy=[x for x in orders if x['year']==y]; st=stat(yy)
  annual_union[str(y)]={**st,'observed_schedule_weeks':observed_year_weeks.get(str(y),0),'avg_orders_per_observed_schedule_week':round(len(yy)/observed_year_weeks[str(y)],6) if observed_year_weeks.get(str(y)) else 0.0}
 summary['results']['new_incremental_by_year']=annual_union
 frozen_by_year=collections.defaultdict(list)
 for m in frozen:
  frozen_by_year[int(m['year'])].append({'fid':str(m['fid']),'year':int(m['year']),'kickoff_beijing':str(m.get('date') or m.get('kickoff_beijing') or '')[:10],'net_u':float(m['pnl'])})
 merged_annual={}
 for y in sorted(set(frozen_by_year)|{x['year'] for x in orders}):
  old=frozen_by_year.get(y,[]); new=[x for x in orders if x['year']==y]
  oldn=len(old); oldu=sum(x['net_u'] for x in old); newn=len(new); newu=sum(x['net_u'] for x in new)
  merged_annual[str(y)]={'frozen_n':oldn,'frozen_net_U':round(oldu,6),'new_n':newn,'new_net_U':round(newu,6),'merged_n':oldn+newn,'merged_net_U':round(oldu+newu,6),'merged_ROI_pct':round(100*(oldu+newu)/(oldn+newn),6) if oldn+newn else None,'new_avg_orders_per_observed_schedule_week':round(newn/observed_year_weeks[str(y)],6) if observed_year_weeks.get(str(y)) else 0.0,'observed_schedule_weeks':observed_year_weeks.get(str(y),0)}
 summary['results']['merged_by_year']=merged_annual
 merged_all=[r for yy in frozen_by_year.values() for r in yy]+orders
 summary['results']['combined_portfolio_metrics']=stat(merged_all)
 # Combined chronological weekly ledger for original frozen members plus unique new FIDs.
 old_week=collections.defaultdict(lambda:[0,0.])
 for m in frozen:
  day=dt.date.fromisoformat(str(m['date'])[:10]); iso=day.isocalendar(); key=f'{iso.year}-W{iso.week:02d}';old_week[key][0]+=1;old_week[key][1]+=float(m['pnl'])
 merged_week={k:[v[0],v[1]] for k,v in old_week.items()}
 for x in orders:
  key=x['iso_week'];merged_week.setdefault(key,[0,0.]);merged_week[key][0]+=1;merged_week[key][1]+=x['net_u']
 summary['results']['merged_weekly']={k:{'n':v[0],'net_U':round(v[1],6)} for k,v in sorted(merged_week.items())}
 summary['results']['actual_receipt_candidate_fids']=0
 summary['results']['actual_receipt_note']='No live-mode captures exist for any of the 18,374 outside-49 FIDs in the Crown SQLite at audit time; all orders below are historical-response source-event replays.'
 combined_n=len(frozen_ids)+len(union)
 summary['results']['combined_original8_plus_new']={'n':combined_n,'net_U':round(base_u+newnet,6),'ROI_pct':round(100*(base_u+newnet)/combined_n,6),'max_drawdown_U':summary['results']['combined_portfolio_metrics']['max_drawdown_U'],'avg_weekly_added_orders':round(len(union)/full_period_weeks,6),'observed_schedule_weeks':full_period_weeks}
 # Persist.
 with gzip.open(OUT/'exact_rule_cross_league_orders.jsonl.gz','wt',encoding='utf-8',newline='') as f:
  for x in sorted(orders,key=lambda x:(x['kickoff_beijing'],x['fid'])): f.write(json.dumps(x,ensure_ascii=False)+'\n')
 with (OUT/'exact_rule_cross_league_coverage.jsonl').open('w',encoding='utf-8') as f:
  for x in coverage_rows: f.write(json.dumps(x,ensure_ascii=False)+'\n')
 with (OUT/'exact_rule_cross_league_no_rule.jsonl').open('w',encoding='utf-8') as f:
  for x in no_rule: f.write(json.dumps(x,ensure_ascii=False)+'\n')
 (OUT/'exact_rule_cross_league_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'coverage':summary['coverage']['status_counts'],'groups':{g:summary['groups'][g]['assigned'] for g in GROUPS},'union':summary['results']['new_incremental'],'combined':summary['results']['combined_original8_plus_new'],'G_model':summary['G_score_model_method']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
