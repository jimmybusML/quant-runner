#!/usr/bin/env python3
"""Verify contemporaneous Crown HTTP receipts for expanded non-Original49 FIDs."""
import collections,datetime as dt,gzip,hashlib,json,pathlib,os
from zoneinfo import ZoneInfo
from exact_rule_cross_league_20261120 import load_schedules,make_score_rates,features,trigger_all,settle,sha,OUT,WORK,GROUPS,ORIGINAL49

BASE=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/forward-shadow')
INDEX=BASE/'crown-capture-index.jsonl'
UTC=dt.timezone.utc; TZ=ZoneInfo('Asia/Shanghai')
def ts(x):
 v=dt.datetime.fromisoformat(str(x).replace('Z','+00:00').replace(' ','T'))
 if v.tzinfo is None:v=v.replace(tzinfo=TZ)
 return v.astimezone(UTC)
def main():
 schedules=load_schedules();scoremap=make_score_rates(schedules);rows=[];errors=collections.Counter();per_fid=collections.defaultdict(list)
 known=set(schedules)
 for line in open(INDEX):
  try:r=json.loads(line)
  except Exception:errors['bad_index_json']+=1;continue
  fid=str(r.get('match_id') or '')
  if fid not in known or r.get('provider')!='TotalCorner' or r.get('source_bookmaker')!='Crown' or r.get('source_endpoint')!='/match/bookmaker_odds':continue
  p=BASE/r['raw_response_relative_path']
  if not p.exists():errors['raw_missing']+=1;continue
  raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest()
  if digest!=r.get('response_sha256'):errors['sha_mismatch']+=1;continue
  try:
   doc=json.loads(raw);match=next(x for x in doc.get('data',[]) if str(x.get('id'))==fid)
   sched=schedules[fid];kick=ts(r.get('kickoff_utc') or match['start']);received=ts(r['captured_at_utc'])
   if str(match.get('l_id'))!=str(sched['league']) or int(match['hg'])!=int(sched['hg']) or int(match['ag'])!=int(sched['ag']):errors['fixture_ft_mismatch']+=1;continue
   crown=next((x for x in match.get('bookmakers',[]) if x.get('slug')=='crown'),None)
   if crown is None:errors['crown_missing']+=1;continue
   # Receipt is usable only for source events no later than the actual response receive time.
   qs=[]
   for q in crown.get('asian_list') or []:
    try:
     source=ts(q[4]);line=float(q[1]);ho=float(q[2]);ao=float(q[3])
     if source<=received and ho>1 and ao>1 and abs(line*4-round(line*4))<1e-7:qs.append((source,line,ho,ao))
    except Exception:continue
   t1=kick-dt.timedelta(hours=1);available=received<=t1
   cuts=[kick-dt.timedelta(hours=h) for h in (6,3,1)];levels=[]
   if available:
    for cut in cuts:
     vals=[x for x in qs if x[0]<=cut]
     levels.append(vals[-1] if vals else None)
   path_complete=bool(available and len(levels)==3 and all(levels))
   base={'fid':fid,'league':sched['league'],'league_name':sched.get('league_name'),'year':kick.astimezone(TZ).year,'kickoff_utc':kick.isoformat(),'kickoff_china':kick.astimezone(TZ).isoformat(),
    'received_at_utc':received.isoformat(),'response_sha256':digest,'raw_response_relative_path':r['raw_response_relative_path'],
    'quote_event_asof_utc':r.get('quote_event_asof_utc'),'valid_crown_quote_events_available_at_receipt':len(qs),
    'received_by_T1':available,'complete_T6_T3_T1_using_receipt':path_complete,
    'historical_source_events_in_receipt':[x[0].isoformat() for x in levels if x]}
   if path_complete:base['T6_T3_T1_home_lines']=[x[1] for x in levels]
   rows.append(base)
   if path_complete:
    qrows=[{'fixture_id':fid,'handicap_home':x[1],'home_decimal':x[2],'away_decimal':x[3],
      'quote_source_at_utc':x[0].isoformat(),'response_received_at_utc':received.isoformat(),
      'capture_mode':'live','response_sha256':digest,'source_file':str(p),'status':'QUOTES_SAVED'} for x in qs]
    per_fid[fid].append((received,base,qrows))
  except Exception:errors['parse_or_identity']+=1
 out=OUT/'actual_receipt_exact_rule_audit_20261122.jsonl.gz'
 with gzip.open(out,'wt',encoding='utf-8') as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 # For each FID, use only the latest actual Crown HTTP response received no later
 # than T1. No source event received after T1 can contribute to this replay.
 receipt_orders=[];receipt_complete=[]
 for fid,arr in per_fid.items():
  received,meta,qrows=max(arr,key=lambda x:x[0]);feat,reason=features(fid,schedules[fid],qrows,scoremap)
  if reason:errors['complete_receipt_missing_'+reason]+=1;continue
  receipt_complete.append(fid);hits=trigger_all(feat);group=next((x for x in GROUPS if x in hits),None)
  if not group:continue
  side=hits[group];price=feat['home_price'] if side=='home' else feat['away_price'];net,label=settle(feat['end_line'],side,feat['hg'],feat['ag'],price)
  feat.update({'group':group,'side':side,'price':price,'net_u':net,'settlement':label,'receipt_received_at_utc':received.isoformat(),
    'response_sha256':meta['response_sha256'],'raw_response_relative_path':meta['raw_response_relative_path'],
    'is_frozen_overlap':fid in ORIGINAL49,'receipt_source':'verified_true_http_Crown'})
  receipt_orders.append(feat)
 with gzip.open(OUT/'actual_receipt_exact_rule_orders_20261122.jsonl.gz','wt',encoding='utf-8') as f:
  for r in receipt_orders:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 receipt_archives=[pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'),
  pathlib.Path('/Users/mac/Documents/ChatGPT/m8-m9-group-research/research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl'),
  pathlib.Path('/Users/mac/Documents/ChatGPT/m8-m9-group-research/research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl')]
 archive_ids=collections.defaultdict(set);archive_rows=collections.Counter()
 for p0 in receipt_archives:
  if not p0.exists():continue
  for line in open(p0):
   try:x=json.loads(line)
   except Exception:continue
   fid=str(x.get('fid') or x.get('fixture_id') or x.get('match_id') or '')
   if fid in known:archive_rows[p0.name]+=1;archive_ids[p0.name].add(fid)
 # The Crown DB's explicit live mode is also checked independently of raw archive indexes.
 import sqlite3
 db=pathlib.Path(os.environ.get('M8_CROSS_LEAGUE_DB','/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3'))
 cx=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
 live_fids=set()
 fids=list(known)
 for i in range(0,len(fids),800):
  chunk=fids[i:i+800];marks=','.join('?' for _ in chunk)
  live_fids.update(str(x[0]) for x in cx.execute(f"SELECT DISTINCT fixture_id FROM capture WHERE fixture_id IN ({marks}) AND capture_mode='live'",chunk))
 cx.close()
 counts={'verified_receipt_rows':len(rows),'unique_fids':len({r['fid'] for r in rows}),
  'received_by_T1_fids':len({r['fid'] for r in rows if r['received_by_T1']}),
  'complete_T6_T3_T1_fids':len(set(receipt_complete)),
  'exact_rule_receipt_orders':len(receipt_orders),
  'other_receipt_archive_intersection_rows':dict(archive_rows),'other_receipt_archive_intersection_fids':{k:len(v) for k,v in archive_ids.items()},
  'explicit_live_capture_fids_in_crown_sqlite':len(live_fids),
  'by_year':{},'errors':dict(errors),'input_sha256':sha(INDEX),'output':out.name,'output_sha256':sha(out),
  'note':'Receipt counts are independent of historical API replay. Completeness means a verified response was actually received by T1 and contained Crown source quotes permitting all three original cutoffs; it does not itself claim positive settlement.'}
 for year in sorted({r['year'] for r in rows}):
  z=[r for r in rows if r['year']==year];counts['by_year'][str(year)]={'receipt_rows':len(z),'fids':len({r['fid'] for r in z}),'received_by_T1':len({r['fid'] for r in z if r['received_by_T1']}),'complete_T6_T3_T1':len({r['fid'] for r in z if r['complete_T6_T3_T1_using_receipt']})}
 (OUT/'actual_receipt_exact_rule_audit_20261122.json').write_text(json.dumps(counts,indent=2))
 def stat(z):
  n=len(z);u=sum(x['net_u'] for x in z);return {'n':n,'net_u':round(u,6),'roi_pct':round(u/n*100,6) if n else None}
 counts['receipt_order_results']={'all':stat(receipt_orders),'by_group':{g:stat([x for x in receipt_orders if x['group']==g]) for g in GROUPS},
  'by_year':{str(y):stat([x for x in receipt_orders if x['year']==y]) for y in sorted({x['year'] for x in receipt_orders})}}
 counts['orders_output']='actual_receipt_exact_rule_orders_20261122.jsonl.gz';counts['orders_sha256']=sha(OUT/counts['orders_output'])
 print(json.dumps(counts,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
