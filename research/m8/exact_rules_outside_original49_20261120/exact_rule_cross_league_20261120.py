#!/usr/bin/env python3
"""Recompute frozen M8 exact base/A-G triggers on expanded Original-49 Crown paths.

Research-only. Reads the local Crown SQLite store and schedule caches; never
changes production files. Historical source-event replay is kept separate from
the archived true HTTP receipt audit.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, glob, hashlib, json, math, pathlib, sqlite3, sys
from zoneinfo import ZoneInfo
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).resolve().parent
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
OLD=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl')
PAGES=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
DAILY=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m7/m7_future_schedule_refresh_daily_20261111')
FROZEN=WORK/'m8_foundation_20261115/historical_membership.jsonl'
FOUNDATION=WORK/'m8_foundation_20261115/manifest.json'
EXISTING=(WORK/'m8_late_full_path_water_features_20261114.jsonl',
          WORK/'m8_extra_inventory_frozen_eight_20261115.jsonl',
          WORK/'m8_raw_capture_unindexed_frozen_replay_20261115.jsonl')
GROUPS=('base','A','B','C','D','E','F','G')
ORIGINAL49={1,10480,109,116,12,14,141,1439,145,152,16,177,25,262,26540,29,290,297,298,299,303,31,319,328,330,332,345,35,37,40,43,45,46,47,48,51,52,55,60,61,62,66,68,70,73,75,8172,88,979}
EXPANDED62={int(json.loads(x)['league_id']) for x in open('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl') if x.strip()}
TARGET_LEAGUES=EXPANDED62-ORIGINAL49
TZ=ZoneInfo('Asia/Shanghai'); UTC=dt.timezone.utc

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def parse_ts(s):
 if not s:return None
 x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 if x.tzinfo is None:x=x.replace(tzinfo=TZ)
 return x.astimezone(UTC)
def sgn(x,eps=1e-9):return 1 if x>eps else -1 if x<-eps else 0
def settle(line,side,hg,ag,odds):
 legs=[float(line)] if abs(float(line)*2-round(float(line)*2))<1e-8 else [math.floor(float(line)*2)/2,math.ceil(float(line)*2)/2]
 pn=[]
 for z in legs:
  margin=hg-ag+z if side=='home' else ag-hg-z
  pn.append(float(odds)-1 if margin>1e-9 else -1. if margin<-1e-9 else 0.)
 return sum(pn)/len(pn),('full_win' if all(x>0 for x in pn) else 'half_win' if any(x>0 for x in pn) else 'push' if all(x==0 for x in pn) else 'half_loss' if any(x==0 for x in pn) else 'full_loss')
def poisson(lam,n=40):
 v=[math.exp(-lam)]
 for k in range(1,n):v.append(v[-1]*lam/k)
 return np.array(v)
def expected_ah(line,ho,ao,rates):
 hp,ap=map(poisson,rates); hi,ai=np.indices((len(hp),len(ap)));diff=hi-ai
 probs=hp[:,None]*ap[None,:]; hw=hl=aw=al=0.
 legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 for leg in legs:
  m=probs/len(legs); z=diff+leg
  hw+=float(m[z>1e-9].sum());hl+=float(m[z<-1e-9].sum())
  za=-diff-leg;aw+=float(m[za>1e-9].sum());al+=float(m[za<-1e-9].sum())
 return hw*(ho-1)-hl,aw*(ao-1)-al

def read_jsonl(p):return [json.loads(x) for x in open(p) if x.strip()]
def load_schedules():
 # Merge both historical inventory and current cached TotalCorner schedule pages
 # by unique FID. Page timestamps are Asia/Shanghai source times.
 d={}
 for r in read_jsonl(OLD):
  if int(r.get('league_id') or 0) in TARGET_LEAGUES and r.get('home_goals') is not None:
   f=str(r['match_id']); local=parse_ts(r.get('kickoff_source_local'))
   d[f]={'fid':f,'league':str(r['league_id']),'league_name':r.get('scope_item') or r.get('source_league'),'home':r['home'],'away':r['away'],'home_id':'','away_id':'','hg':int(r['home_goals']),'ag':int(r['away_goals']),'kickoff_utc':local.isoformat() if local else None,'source':'expanded62_schedule'}
 def add_files(patterns,source):
  for pat in patterns:
   for name in glob.glob(pat):
    p=pathlib.Path(name)
    try:blob=json.loads(p.read_text())
    except Exception:continue
    for r in (blob.get('data') or {}).get('matches',[]):
     if int(r.get('l_id') or 0) not in TARGET_LEAGUES or r.get('status')!='full':continue
     try:
      ko=parse_ts(r['start']);
      if ko is None or not(dt.datetime(2019,1,1,tzinfo=UTC)<=ko<=dt.datetime(2026,11,20,23,59,59,tzinfo=UTC)):continue
      f=str(r['id']);v={'fid':f,'league':str(r['l_id']),'league_name':r.get('l'),'home':r.get('h'),'home_id':str(r.get('h_id') or ''),'away':r.get('a'),'away_id':str(r.get('a_id') or ''),'hg':int(r['hg']),'ag':int(r['ag']),'kickoff_utc':ko.isoformat(),'source':source}
     except Exception:continue
     if f in d:
      old=d[f]
      if (old['league'],old['hg'],old['ag'])!=(v['league'],v['hg'],v['ag']):raise ValueError(f'schedule conflict {f}: {old} vs {v}')
      if old.get('kickoff_utc') and v.get('kickoff_utc') and abs((parse_ts(old['kickoff_utc'])-parse_ts(v['kickoff_utc'])).total_seconds())>1:raise ValueError(f'kickoff conflict {f}: {old.get("kickoff_utc")} vs {v.get("kickoff_utc")}')
      if old.get('home')!=v.get('home') or old.get('away')!=v.get('away'):raise ValueError(f'team identity conflict {f}: {old.get("home")}/{old.get("away")} vs {v.get("home")}/{v.get("away")}')
      old.setdefault('sources',[old.get('source')]);old['sources'].append(source)
      if v.get('kickoff_utc'):old['kickoff_utc']=v['kickoff_utc']
      if v.get('home'):old['home']=v['home']
      if v.get('away'):old['away']=v['away']
      if v.get('home_id'):old['home_id']=v['home_id']
      if v.get('away_id'):old['away_id']=v['away_id']
      if v.get('league_name'):old['league_name']=v['league_name']
     else:d[f]=v
 add_files(['/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules/*/page-*.raw.json'],'raw_schedule_page')
 add_files(['/Users/mac/QuantAsiaDesk/research-work/m7/m7_future_schedule_refresh_daily_20261111/2026-*/raw/*.json'],'daily_schedule_refresh')
 return d

def make_score_rates(schedules):
 # Reproduce the archived independent score-only online model at LR=.025.
 # Every target prediction is emitted before consuming matches fewer than two
 # calendar days old; no current/future score is used.
 rows=sorted((s for s in schedules.values() if s.get('home_id') and s.get('away_id')),
             key=lambda s:(s['kickoff_utc'],s['fid']))
 attack=collections.defaultdict(float);defense=collections.defaultdict(float)
 baseline=collections.defaultdict(lambda:[math.log(1.45),math.log(1.15)])
 def predict(r):
  h=(r['league'],r['home_id']);a=(r['league'],r['away_id']);b=baseline[r['league']]
  return float(np.exp(np.clip(b[0]+attack[h]+defense[a],-2.5,2.3))),float(np.exp(np.clip(b[1]+attack[a]+defense[h],-2.5,2.3)))
 def update(r):
  h=(r['league'],r['home_id']);a=(r['league'],r['away_id']);b=baseline[r['league']];x,y=predict(r);e1=r['hg']-x;e2=r['ag']-y
  for k,e in ((h,e1),(a,e2)):attack[k]=.997*attack[k]+.025*float(np.clip(e,-4,4))
  for k,e in ((a,e1),(h,e2)):defense[k]=.997*defense[k]+.025*float(np.clip(e,-4,4))
  b[0]+=.003*float(np.clip(e1,-4,4));b[1]+=.003*float(np.clip(e2,-4,4))
 rates={};q=0
 for r in rows:
  day=dt.date.fromisoformat(r['kickoff_utc'][:10])
  while q<len(rows) and (day-dt.date.fromisoformat(rows[q]['kickoff_utc'][:10])).days>=2:
   update(rows[q]);q+=1
  rates[r['fid']]=predict(r)
 return rates

def load_quotes(schedule):
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True);cx.row_factory=sqlite3.Row
 fids=list(schedule); qmap=collections.defaultdict(list);cmap=collections.defaultdict(list)
 # Chunked placeholders for SQLite limits.
 for i in range(0,len(fids),800):
  chunk=fids[i:i+800]; marks=','.join('?' for _ in chunk)
  for x in cx.execute(f"SELECT fixture_id,status,quote_count,capture_mode,response_sha256 FROM capture WHERE fixture_id IN ({marks}) AND data_layer='movement'",chunk):cmap[str(x['fixture_id'])].append(dict(x))
  sql=f'''SELECT q.fixture_id,q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc,q.response_received_at_utc,
          c.capture_mode,c.response_sha256,c.source_file,c.status,c.data_layer,q.quote_kind
          FROM asian_quote q JOIN capture c USING(capture_key)
          WHERE q.fixture_id IN ({marks}) AND q.quote_kind='movement' AND c.data_layer='movement'
          ORDER BY q.fixture_id,q.quote_source_at_utc,q.response_received_at_utc,c.response_sha256'''
  for x in cx.execute(sql,chunk):
   f=str(x['fixture_id']);qmap[f].append(dict(x))
 cx.close();return qmap,cmap

def features(fid,sched,quotes,scoremap):
 ko=parse_ts(sched.get('kickoff_utc'))
 if ko is None:return None,'kickoff_missing'
 qvalid=[]
 for q in quotes:
  try:
   t=parse_ts(q['quote_source_at_utc']);line=float(q['handicap_home']);ho=float(q['home_decimal']);ao=float(q['away_decimal'])
   if t and t<ko and ho>1 and ao>1 and all(map(math.isfinite,[line,ho,ao])) and abs(line*4-round(line*4))<1e-7:
    qvalid.append((t,line,ho,ao,q))
  except Exception:pass
 if not qvalid:return None,'no_valid_pregame_quote'
 qvalid.sort(key=lambda z:(z[0],z[4]['response_received_at_utc'] or '',z[4]['response_sha256'] or ''))
 cut=[ko-dt.timedelta(hours=h) for h in (6,3,1)]
 path=[]
 for tcut in cut:
  eligible=[x for x in qvalid if x[0]<=tcut]
  if not eligible:return None,'missing_T6' if tcut==cut[0] else 'missing_T3' if tcut==cut[1] else 'missing_T1'
  path.append(eligible[-1])
 start,mid,end=path;seq=[x for x in qvalid if start[0]<=x[0]<=end[0]]
 if not seq:return None,'empty_window'
 # Deduplicate identical source-time observations from archived repeats.
 uniq=[]
 for x in seq:
  if not uniq or (x[0],x[1],x[2],x[3])!=(uniq[-1][0],uniq[-1][1],uniq[-1][2],uniq[-1][3]):uniq.append(x)
 seq=uniq; steps=[(u,v) for u,v in zip(seq,seq[1:]) if u[1]!=v[1]]
 l0,l3,l1=start[1],mid[1],end[1]
 def state(a,b):return 'deepen' if (b-a)*l1>0 else 'weaken' if (b-a)*l1<0 else 'same'
 shape='never_changed' if not steps else 'reverted' if l0==l1 else 'one_way' if all((v[1]-u[1])*(l1-l0)>0 for u,v in steps) else 'oscillating'
 durations=collections.defaultdict(float);odds=collections.defaultdict(lambda:[0.,0.])
 for n,x in enumerate(seq):
  lo=max(cut[0],x[0]);hi=seq[n+1][0] if n+1<len(seq) else cut[2];dur=max(0.,(hi-lo).total_seconds())
  durations[x[1]]+=dur;odds[x[1]][0]+=dur*x[2];odds[x[1]][1]+=dur*x[3]
 p=lambda x:x[3]/(x[2]+x[3])
 moves=[p(v)-p(u) for u,v in zip(seq,seq[1:]) if abs(p(v)-p(u))>1e-10]
 rates=scoremap.get(fid)
 local_ko=ko.astimezone(TZ)
 r={'fid':fid,'year':local_ko.year,'date':local_ko.date().isoformat(),'league':sched['league'],'league_name':sched.get('league_name'),'home':sched.get('home'),'away':sched.get('away'),'hg':sched['hg'],'ag':sched['ag'],
    'kickoff_utc':ko.isoformat(),'kickoff_china':local_ko.isoformat(),'start_line':l0,'mid_line':l3,'end_line':l1,'start_home_price':start[2],'start_away_price':start[3],'home_price':end[2],'away_price':end[3],
    'p0':p(start),'p3':p(mid),'p1':p(end),'base':((l1-l0)*l1)>0,'end_zero':l1==0,'n_price_moves':len(moves),'up_moves':sum(z>0 for z in moves),'down_moves':sum(z<0 for z in moves),
    'last_move':moves[-1] if moves else 0.,'path_6_3_1':state(l0,l3)+'_'+state(l3,l1),'path_shape':shape,'home_price_vs_timeavg':end[2]-odds[l1][0]/durations[l1] if durations[l1] else None,
    'away_price_vs_timeavg':end[3]-odds[l1][1]/durations[l1] if durations[l1] else None,'n_events':len(seq),'n_line_changes':len(steps),'score_rates':rates,
    'source_event_times':[x[0].isoformat() for x in path], 'response_received_times':[x[4]['response_received_at_utc'] for x in path], 'source_sha256':[x[4]['response_sha256'] for x in path],
    'capture_modes':[x[4]['capture_mode'] for x in path], 'source_files':[x[4]['source_file'] for x in path]}
 if shape=='reverted' and rates:
  eh,ea=expected_ah(l1,end[2],end[3],rates);r['expected_ah_home_ev']=eh;r['expected_ah_away_ev']=ea
 return r,None

def trigger_all(r):
 l=r['end_line'];hits={}
 if r['base']:hits['base']='home' if l>0 else 'away'
 if r['path_6_3_1']=='deepen_weaken':hits['A']='home' if l>0 else 'away'
 if r['path_6_3_1']=='weaken_same':hits['B']='home' if l>0 else 'away'
 if not r['end_zero'] and r['path_shape']=='oscillating':hits['C']='away' if l>0 else 'home'
 if r['end_zero'] and r['path_shape']=='reverted' and r['home_price_vs_timeavg'] is not None and r['home_price_vs_timeavg']-r['away_price_vs_timeavg']<-1e-9:hits['D']='away'
 if r['end_zero'] and r['path_shape']=='never_changed':
  a=sgn(r['p3']-r['p0']);b=sgn(r['p1']-r['p3']);net=sgn(r['p1']-r['p0']);s=net or a or b or sgn(r['last_move'])
  if s and r['n_price_moves']:
   if r['up_moves'] and r['down_moves'] and not net:hits['E']='away' if s>0 else 'home'  # archived exact E rule, verified against 267/267 members
   if (not r['up_moves'] or not r['down_moves']) and a==0 and b*s==1:hits['F']='home' if s>0 else 'away'
 if r['path_shape']=='reverted' and r.get('score_rates'):
  market=sgn(r['away_price']/(r['home_price']+r['away_price'])-r['start_away_price']/(r['start_home_price']+r['start_away_price']))
  eh,ea=r.get('expected_ah_home_ev'),r.get('expected_ah_away_ev');model=sgn(eh-ea) or 1
  if market and market==model:hits['G']='away' if model>0 else 'home'
 return hits

def span_weeks(date_span):
 if not date_span:return 0
 lo=min(dt.date.fromisoformat(x) for x in date_span);hi=max(dt.date.fromisoformat(x) for x in date_span)
 a=lo.isocalendar();b=hi.isocalendar()
 return (b.year-a.year)*52 + (b.week-a.week)+1 if a.year==b.year else len({(d.isocalendar().year,d.isocalendar().week) for d in (lo+dt.timedelta(days=i) for i in range((hi-lo).days+1))})
def summarize(rows,date_span=None):
 pnl=sum(x['net_u'] for x in rows);n=len(rows);dates=collections.defaultdict(float)
 for x in rows:dates[x['date']]+=x['net_u']
 c=peak=mdd=0.
 for day,v in sorted(dates.items()):c+=v;peak=max(peak,c);mdd=max(mdd,peak-c)
 span=date_span if date_span is not None else list(dates);weeks=span_weeks(span)
 active=set()
 for day in dates:
  d=dt.date.fromisoformat(day).isocalendar();active.add((d.year,d.week))
 settlements=collections.Counter(x['settlement'] for x in rows)
 return {'orders':n,'net_u':round(pnl,6),'roi_pct':round(pnl/n*100,6) if n else None,'mdd_u':round(mdd,6),
  'average_decimal_odds':round(sum(float(x['price']) for x in rows)/n,6) if n else None,
  'settlements':dict(settlements),'active_iso_weeks':len(active),'active_week_avg':round(n/len(active),6) if active else 0,
  'observation_iso_weeks':weeks,'weekly_avg':round(n/weeks,6) if weeks else 0}

def main():
 schedules=load_schedules();frozen=read_jsonl(FROZEN);frozen_ids={str(x['fid']) for x in frozen}
 frozen_u=round(sum(float(x['pnl']) for x in frozen),3)
 assert len(frozen_ids)==10294 and abs(frozen_u-236.015)<1e-6,(len(frozen_ids),frozen_u)
 assert not(set(schedules)&frozen_ids),'Target cross-league schedule overlaps frozen Original49 FIDs'
 oldpaths=[json.loads(x) for p in EXISTING for x in open(p) if x.strip()];known_path={str(x['fid']) for x in oldpaths}
 qmap,cmap=load_quotes(schedules)
 # G's frozen independent score rates from the original score-strength replay; later IDs may not exist.
 scoremap=make_score_rates(schedules)
 coverage=collections.Counter();missing=collections.Counter();rows=[];coverage_rows=[]
 for i,(fid,s) in enumerate(schedules.items(),1):
  coverage['schedule_fids']+=1
  local_dt=parse_ts(s['kickoff_utc']).astimezone(TZ);coverage_time={'date':local_dt.date().isoformat(),'kickoff_china':local_dt.isoformat()}
  qs=qmap.get(fid,[])
  if not qs:
   local_year=parse_ts(s['kickoff_utc']).astimezone(TZ).year
   if cmap.get(fid):
    missing['movement_capture_no_quotes']+=1;reason='movement_capture_no_quotes'
   else:missing['no_movement_capture']+=1;reason='no_movement_capture'
   coverage_rows.append({'fid':fid,'league':s['league'],'year':local_year,**coverage_time,'status':reason,'capture_rows':len(cmap.get(fid,[]))});continue
  if not any(q['status']=='QUOTES_SAVED' for q in qs):
   missing['movement_capture_no_quotes']+=1;coverage_rows.append({'fid':fid,'league':s['league'],'year':parse_ts(s['kickoff_utc']).astimezone(TZ).year,**coverage_time,'status':'movement_capture_no_quotes','capture_rows':len(qs)});continue
  coverage['quote_saved_fids']+=1
  if any(parse_ts(q['quote_source_at_utc']) and parse_ts(q['quote_source_at_utc'])<parse_ts(s['kickoff_utc']) for q in qs):coverage['valid_pregame_quote_fids']+=1
  feat,reason=features(fid,s,qs,scoremap)
  if reason:missing[reason]+=1;coverage_rows.append({'fid':fid,'league':s['league'],'year':parse_ts(s['kickoff_utc']).astimezone(TZ).year,**coverage_time,'status':reason,'capture_rows':len(qs)});continue
  coverage['complete_T6_T3_T1']+=1
  if feat.get('score_rates') is not None:coverage['complete_paths_with_G_score_rates']+=1
  else:coverage['complete_paths_without_G_score_rates']+=1
  if fid in known_path:coverage['previously_screened_complete_path']+=1
  else:coverage['newly_restored_complete_path']+=1
  hits=trigger_all(feat);g=next((x for x in GROUPS if x in hits),None);side=hits.get(g)
  feat['raw_group_hits']=hits
  coverage_rows.append({'fid':fid,'league':s['league'],'year':feat['year'],**coverage_time,'status':'complete_path_with_signal' if g else 'complete_path_no_signal','assigned_group':g,'all_group_hits':hits})
  feat['group']=g;feat['side']=side
  if g:
   odds=feat['home_price'] if side=='home' else feat['away_price']
   val,label=settle(feat['end_line'],side,feat['hg'],feat['ag'],odds)
   feat.update({'price':odds,'settlement':label,'net_u':val,'unique_outside_frozen':fid not in frozen_ids,
                'historical_event_replay':True,'actual_receipt_claim':False})
  rows.append(feat)
  if i%10000==0:print('progress',i,dict(coverage),dict(missing),flush=True)
 # retain only truly expanded-scope candidates, but keep previous paths as calibration/status context in coverage
 new=[r for r in rows if r['fid'] not in frozen_ids and r.get('group')]
 # frozen priority is mutually exclusive base,A,B,C,D,E,F,G. Cross-group assignments retained for audit.
 byfid=collections.defaultdict(list);raw_byfid=collections.defaultdict(list)
 for r in rows:
  if r.get('group'):byfid[r['fid']].append(r)
  for g,side in r.get('raw_group_hits',{}).items():
   z=dict(r);z['group']=g;z['side']=side
   price=z['home_price'] if side=='home' else z['away_price'];net,label=settle(z['end_line'],side,z['hg'],z['ag'],price)
   z.update({'side':side,'price':price,'net_u':net,'settlement':label})
   raw_byfid[z['fid']].append(z)
 priority={g:i for i,g in enumerate(GROUPS)}
 unique=[]
 for fid,arr in byfid.items():
  r=sorted(arr,key=lambda x:priority[x['group']])[0]
  if fid not in frozen_ids:unique.append(r)
 for g in GROUPS:
  coverage['all_exact_'+g]+=sum(x.get('group')==g for x in rows)
  coverage['new_exact_'+g]+=sum(x.get('group')==g and x['fid'] not in frozen_ids for x in rows)
 orders=[]
 for r in unique:
  x=dict(r);x['group_overlap_all']=sorted({z['group'] for z in raw_byfid[x['fid']]});orders.append(x)
 spans_by_year={str(y):[x['date'] for x in rows if x['year']==y] for y in range(2019,2027)}
 all_span=[x['date'] for x in rows]
 groups={}
 for g in GROUPS:
  z=[x for x in orders if x['group']==g]
  groups[g]={'all':summarize(z,all_span),'by_year':{str(y):summarize([x for x in z if x['year']==y],spans_by_year.get(str(y),[])) for y in range(2019,2027)},
   'by_league':{l:summarize([x for x in z if x['league']==l]) for l in sorted({x['league'] for x in z})},
   'weekly':weekly(z,all_span)}
 summary={'study':'M8 frozen Original49 exact base/A-G transfer to the 15 expanded-schedule league IDs outside the frozen Original49; research historical replay only',
  'inputs':{'schedule_old_sha256':sha(OLD),'frozen_sha256':sha(FROZEN),'foundation_manifest_sha256':sha(FOUNDATION),'sqlite_sha256':sha(DB),
    'existing_path_sha256':{str(p):sha(p) for p in EXISTING},'expanded_schedule_source':'crown-drop-expanded-62/schedule_universe.jsonl; raw page cache; daily refresh cache'},
  'schedule_universe':len(schedules),'original49_excluded_from_target':sorted(ORIGINAL49),'target_league_ids':sorted(TARGET_LEAGUES),'coverage':dict(coverage),'missing_reasons':dict(missing),'frozen_baseline':{'n':len(frozen_ids),'U':frozen_u,'ROI_pct':round(frozen_u/len(frozen_ids)*100,6)},
 'unique_incremental':summarize(orders),'by_group':groups,
 'raw_group_hits_before_priority':{g:summarize([x for a in raw_byfid.values() for x in a if x['group']==g and x['fid'] not in frozen_ids],all_span) for g in GROUPS},
  'overlap':{'fids_with_multiple_group_hits':sum(len(a)>1 for a in raw_byfid.values()),'overlapping_group_pairs':pair_counts(raw_byfid),
    'raw_hit_fids':len(raw_byfid),'priority_assigned_unique_fids':len(orders)},
  'incremental_by_year':{str(y):summarize([x for x in orders if x['year']==y],spans_by_year.get(str(y),[])) for y in range(2019,2027)},
  'combined_with_frozen_baseline':combined(frozen,orders,all_span),
  'weekly_incremental':weekly(orders,all_span),
  'weekly_frozen_eight':weekly([{'date':x.get('date') or x.get('kickoff_china','')[:10],'net_u':float(x['pnl'])} for x in frozen],all_span),
  'weekly_combined':weekly([{'date':x.get('date') or x.get('kickoff_china','')[:10],'net_u':float(x['pnl'])} for x in frozen]+orders,all_span),
  'combined_by_year':{str(y):combined([x for x in frozen if int(x['year'])==y],[x for x in orders if x['year']==y],spans_by_year.get(str(y),[])) for y in sorted({int(x['year']) for x in frozen}|{x['year'] for x in orders})},
  'data_classification':'SQLite historical movement source timestamps; retrieval/response receive time recorded but never represented as contemporaneous receipt. True HTTP receipts are reported separately in receipt audit.'}
 out_json=OUT/'exact_rule_cross_league_summary.json';out_json.write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 with gzip.open(OUT/'exact_rule_cross_league_orders.jsonl.gz','wt',encoding='utf-8') as f:
  for x in orders:f.write(json.dumps(x,ensure_ascii=False)+'\n')
 with gzip.open(OUT/'exact_rule_cross_league_all_complete_paths.jsonl.gz','wt',encoding='utf-8') as f:
  for x in rows:f.write(json.dumps(x,ensure_ascii=False)+'\n')
 with gzip.open(OUT/'exact_rule_cross_league_coverage_by_fid.jsonl.gz','wt',encoding='utf-8') as f:
  for x in coverage_rows:f.write(json.dumps(x,ensure_ascii=False)+'\n')
 def cov_agg(seq):
  z=collections.Counter(x['status'] for x in seq);return dict(z)
 coverage_doc={'schedule_unique_fids':len(schedules),'coverage_by_reason':dict(missing),'coverage_by_league':{},'coverage_by_year':{},
  'coverage_by_league_year':{},'fid_detail_file':'exact_rule_cross_league_coverage_by_fid.jsonl.gz'}
 for lid in sorted({x['league'] for x in coverage_rows},key=int):
  z=[x for x in coverage_rows if x['league']==lid];coverage_doc['coverage_by_league'][lid]={'n':len(z),'statuses':cov_agg(z)}
 for year in sorted({x['year'] for x in coverage_rows}):
  z=[x for x in coverage_rows if x['year']==year];coverage_doc['coverage_by_year'][str(year)]={'n':len(z),'statuses':cov_agg(z)}
 for lid,year in sorted({(x['league'],x['year']) for x in coverage_rows},key=lambda x:(int(x[0]),x[1])):
  z=[x for x in coverage_rows if x['league']==lid and x['year']==year];coverage_doc['coverage_by_league_year'][f'{lid}|{year}']={'n':len(z),'statuses':cov_agg(z)}
 (OUT/'exact_rule_cross_league_coverage.json').write_text(json.dumps(coverage_doc,ensure_ascii=False,indent=2))
 print(json.dumps({'schedule':len(schedules),'coverage':dict(coverage),'missing':dict(missing),'unique':summary['unique_incremental'],'groups':{g:v['all'] for g,v in groups.items()}},ensure_ascii=False),flush=True)

def weekly(rows,date_span=None):
 z=collections.defaultdict(list)
 for x in rows:
  iso=dt.date.fromisoformat(x['date']).isocalendar();z[f'{iso.year}-W{iso.week:02}'].append(x)
 if date_span:
  lo=min(dt.date.fromisoformat(x) for x in date_span);hi=max(dt.date.fromisoformat(x) for x in date_span)
  for i in range((hi-lo).days+1):
   x=lo+dt.timedelta(days=i);iso=x.isocalendar();z.setdefault(f'{iso.year}-W{iso.week:02}',[])
 return {k:{'n':len(v),'net_u':round(sum(x['net_u'] for x in v),6)} for k,v in sorted(z.items())}
def pair_counts(byfid):
 c=collections.Counter()
 for a in byfid.values():
  gs=sorted({x['group'] for x in a})
  for i,g in enumerate(gs):
   for h in gs[i+1:]:c[f'{g}|{h}']+=1
 return dict(c)
def combined(frozen,orders,date_span=None):
 base=[{'fid':str(x['fid']),'date':x.get('date') or x.get('kickoff_china','')[:10],'year':int(x['year']),'net_u':float(x['pnl'])} for x in frozen]
 extra=[{'fid':x['fid'],'date':x['date'],'year':x['year'],'net_u':x['net_u']} for x in orders]
 z=base+extra;n=len(z);u=sum(x['net_u'] for x in z);daily=collections.defaultdict(float)
 for x in z:daily[x['date']]+=x['net_u']
 c=peak=mdd=0.
 for d,v in sorted(daily.items()):c+=v;peak=max(peak,c);mdd=max(mdd,peak-c)
 return {'orders':n,'net_u':round(u,6),'roi_pct':round(u/n*100,6) if n else None,'mdd_u':round(mdd,6),
  'incremental_orders':len(extra),'increment_vs_frozen_u':round(sum(x['net_u'] for x in extra),6),
  'weekly_avg_incremental':summarize(orders,date_span)['weekly_avg'],'observation_iso_weeks':span_weeks(date_span or [x['date'] for x in extra])}
if __name__=='__main__':main()
