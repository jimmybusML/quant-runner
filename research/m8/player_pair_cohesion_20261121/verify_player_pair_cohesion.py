#!/usr/bin/env python3
"""Independent Crown/FT/quarter-line and actual-receipt audit."""
from __future__ import annotations
import collections,datetime as dt,gzip,hashlib,json,math,pathlib

OUT=pathlib.Path(__file__).resolve().parent
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=pathlib.Path('/Users/mac/QuantAsiaDesk/data')
RAW_AUDIT=pathlib.Path('/Users/mac/.codex/worktrees/m8-discipline-referee/quant-runner-m8-goalkeeper/research/m8/prior_formation_market_20261121/historical_crown_raw_fid_audit_20261121.jsonl.gz')
RECEIPT_AUDIT=pathlib.Path('/Users/mac/.codex/worktrees/m8-discipline-referee/quant-runner-m8-goalkeeper/research/m8/prior_formation_market_20261121/actual_receipt_quote_audit_20261121.jsonl.gz')
def jlines(path):
 with gzip.open(path,'rt',encoding='utf8') as f:
  for s in f:
   if s.strip():yield json.loads(s)
def jl(path):
 with open(path,encoding='utf8') as f:
  for s in f:
   if s.strip():yield json.loads(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def utc(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
 return x.astimezone(dt.timezone.utc)
def settle(line,side,gd,odds):
 signed=float(line) if side=='home' else -float(line);margin=int(gd) if side=='home' else -int(gd)
 if abs(signed*4-round(signed*4))>1e-8:raise ValueError('not quarter-grid line')
 legs=(signed,) if abs(signed*2-round(signed*2))<1e-8 else (math.floor(signed*2)/2,math.ceil(signed*2)/2)
 outcomes=[];pnl=[]
 for leg in legs:
  x=margin+leg;outcomes.append('W' if x>1e-9 else 'L' if x < -1e-9 else 'P');pnl.append(float(odds)-1 if x>1e-9 else -1. if x < -1e-9 else 0.)
 net=round(sum(pnl)/len(pnl),8)
 state='full_win' if all(x=='W' for x in outcomes) else 'full_loss' if all(x=='L' for x in outcomes) else 'push' if all(x=='P' for x in outcomes) else 'half_win' if net>0 else 'half_loss' if net<0 else 'push'
 return state,net
def load_crown_sources(fids):
 known={str(r['fid']):r for r in jl(WORK/'m8_late_full_path_water_features_20261114.jsonl')}
 jobs={}
 for r in jl(WORK/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'):
  fid=str(r['fixture_id'])
  if fid in fids and fid in known and int(known[fid]['year'])<2026:jobs[fid]=(pathlib.Path(r['source_file']),None,str(known[fid]['league']))
 index={str(r['match_id']):r.get('response_sha256') for r in jl(DATA/'m5-crown-authorized/crown-response-index.jsonl')}
 for fid in fids:
  if fid in known and int(known[fid]['year'])==2026:jobs[fid]=(DATA/'m5-crown-authorized/crown-responses'/f'{fid}.json',index.get(fid),str(known[fid]['league']))
 for name in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
  for r in jl(WORK/name):
   fid=str(r['fid'])
   if fid in fids and fid not in jobs:jobs[fid]=(pathlib.Path(r['source_file']),index.get(fid) if '/m5-crown-authorized/crown-responses/' in r['source_file'] else None,str(r['league']))
 return jobs
def main():
 summary=json.loads((OUT/'pair_cohesion_summary_20261121.json').read_text())
 rows=list(jlines(OUT/'pair_cohesion_per_fixture_20261121.jsonl.gz'))
 receipts=list(jlines(OUT/'pair_cohesion_actual_receipt_replay_20261121.jsonl.gz'))
 frozen={str(r['fid']) for r in jl(WORK/'m8_foundation_20261115/historical_membership.jsonl')}
 raw={r['fid']:r for r in jlines(RAW_AUDIT)}
 recaudit={r['fid']:r for r in jlines(RECEIPT_AUDIT)}
 issues=collections.Counter();methods=collections.defaultdict(list)
 for r in rows:
  methods[r['method']].append(r)
  if bool(r['fid'] in frozen)!=bool(r['frozen_overlap']):issues['frozen_overlap_mismatch']+=1
  if r['year']>=2024 and int(r['training_year_cutoff_exclusive'])!=r['year']:issues['training_cutoff_mismatch']+=1
  cutoff=dt.date.fromisoformat(r['cohesion_cutoff'])
  for side in ('home','away'):
   f=r[f'pair_features_{side}']
   if dt.date.fromisoformat(f['last_history_date'])>cutoff:issues['history_feature_after_cutoff']+=1
   if int(f['n_team_matches_365'])<3:issues['history_minimum_mismatch']+=1
  state,net=settle(r['T12_AH_home_line'],r['chosen_side'] or 'home',r['gd'],r['chosen_odds'] or r['T12_home_odds']) if r['chosen_side'] else ('push',0.)
  if state!=r['settlement'] or abs(net-float(r['net_u']))>1e-7:issues['historical_settlement_mismatch']+=1
 # Re-read Crown source bodies for every candidate FID, including candidates
 # outside the earlier formation-feature cohort.
 target_by_fid={str(r['fid']):r for r in jl(WORK/'m8_early_joint_market_inventory_20261115.jsonl') if int(r['T'])==12}
 jobs=load_crown_sources(set(r['fid'] for r in methods['market_only']));raw_verified=0;historical_evidence=[]
 for r in methods['market_only']:
  fid=r['fid'];job=jobs.get(fid);market=target_by_fid.get(fid)
  if not job or not job[0].is_file() or not market:issues['historical_raw_source_missing']+=1;continue
  path,expected_sha,expected_league=job
  try:
   b=path.read_bytes()
   if expected_sha and sha(b)!=expected_sha:issues['historical_raw_file_sha_mismatch']+=1;continue
   body=json.loads(b);match=next(x for x in body.get('data',[]) if str(x.get('id'))==fid)
   if str(match.get('l_id'))!=expected_league or str(match.get('status'))!='full':issues['historical_raw_identity_or_status']+=1;continue
   if (int(match['hg']),int(match['ag']))!=(int(r['hg']),int(r['ag'])):issues['historical_raw_FT_mismatch']+=1;continue
   ko=utc(match['start']);cutoff=ko-dt.timedelta(hours=12);book=next(x for x in match['bookmakers'] if x.get('slug')=='crown');quotes=[]
   for q in book.get('asian_list') or []:
    try:
     t=utc(q[4]);line,home,away=map(float,q[1:4])
     if t<ko and home>1 and away>1 and abs(line*4-round(line*4))<1e-7:quotes.append((t,1,line,home,away))
    except Exception:pass
   for q in (book.get('asian') or {}).values():
    if not isinstance(q,dict):continue
    try:
     t=utc(q['time']);line=float(q['line']);home=float(q['home']);away=float(q['away'])
     if t<ko and home>1 and away>1 and abs(line*4-round(line*4))<1e-7:quotes.append((t,0,line,home,away))
    except Exception:pass
   eligible=[x for x in quotes if x[0]<=cutoff]
   if not eligible:issues['historical_T12_quote_missing']+=1;continue
   event_time,_,line,home,away=max(eligible,key=lambda x:(x[0],x[1]))
   if (abs(line-float(market['al']))>1e-8 or abs(home-float(market['ah']))>1e-8 or abs(away-float(market['aa']))>1e-8):issues['historical_T12_raw_contract_mismatch']+=1;continue
   if (str(match.get('h_id'))!=str(r['home_id']) or str(match.get('a_id'))!=str(r['away_id'])):issues['historical_raw_team_mismatch']+=1;continue
   raw_verified+=1
   historical_evidence.append({'fid':fid,'source_file':str(path),'raw_file_sha256':sha(b),'indexed_response_sha256':expected_sha,
       'quote_source_event_utc':event_time.isoformat(),'league':str(match.get('l_id')),'home_id':str(match.get('h_id')),'away_id':str(match.get('a_id')),
       'kickoff_utc':ko.isoformat(),'T12_AH_home_line':line,'T12_home_odds':home,'T12_away_odds':away,'hg':int(match['hg']),'ag':int(match['ag'])})
  except Exception:issues['historical_raw_parse_error']+=1
 for m,arr in methods.items():
  ids=[r['fid'] for r in arr]
  if len(ids)!=len(set(ids)):issues['duplicate_method_FID']+=1
  inc=[r for r in arr if not r['frozen_overlap']]
  got={'n':len(inc),'net_U':round(sum(float(r['net_u']) for r in inc),6)}
  exp=summary['models'][m]['incremental_outside_frozen']
  if got['n']!=exp['n'] or abs(got['net_U']-exp['net_U'])>1e-6:issues['summary_reconciliation']+=1

 # Raw MR1 actual HTTP response and the exact snapshot digest used for each
 # unique FID are checked independently of the model ledger.
 receipt_archive={}
 for a in jl(WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'):
  receipt_archive[(str(a['fixture_id']),str(a.get('raw_sha256')),str(a.get('snapshot_sha256')))]=a
 receipt_ids=set();receipt_unique_rows={}
 for r in receipts:
  q=r['receipt_quote'];fid=r['fid'];receipt_ids.add(fid);receipt_unique_rows[fid]=r
  proof=recaudit.get(fid)
  if not proof:issues['receipt_source_proof_missing']+=1;continue
  key=(fid,str(q['raw_sha256']),str(q['snapshot_sha256']));a=receipt_archive.get(key)
  if not a:issues['receipt_archive_map_missing']+=1;continue
  try:
   p=pathlib.Path(a['source_file']);env=json.loads(p.read_bytes());body=str(env.get('raw_response') or '').encode()
   snap=p.parents[1]/'snapshot.json';sb=snap.read_bytes();sj=json.loads(sb);jbody=json.loads(body)
   if sha(body)!=q['raw_sha256'] or sha(sb)!=q['snapshot_sha256']:issues['receipt_raw_or_snapshot_sha_mismatch']+=1;continue
   if int(env.get('http_status') or 0)!=200 or not env.get('raw_saved'):issues['receipt_HTTP_status']+=1;continue
   if utc(q['received_utc'])>=utc(q['kickoff_utc']) or utc(q['source_event_utc'])>utc(q['received_utc']):issues['receipt_not_pregame']+=1;continue
   if utc(q['kickoff_utc']).date()!=dt.date.fromisoformat(r['date']):issues['receipt_kickoff_date_mismatch']+=1;continue
   if str(sj.get('match_id'))!=fid or not sj.get('prematch_valid') or not sj.get('source_bookmaker_verified'):issues['receipt_snapshot_identity']+=1;continue
   ah=sj.get('AH') or {}
   if abs(float(ah.get('line'))-float(q['line']))>1e-8 or abs(float(ah.get('home_price'))-float(q['home_odds']))>1e-8 or abs(float(ah.get('away_price'))-float(q['away_odds']))>1e-8:issues['receipt_snapshot_price_mismatch']+=1;continue
   data=jbody.get('data');data=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
   mm=next((x for x in data if str(x.get('id'))==fid),None)
   if not mm or str(mm.get('l_id'))!=str(r['league']) or str(mm.get('h_id'))!=str(r['home_id']) or str(mm.get('a_id'))!=str(r['away_id']):issues['receipt_raw_fixture_mismatch']+=1;continue
   state,net=settle(q['line'],r['chosen_side'] or 'home',r['gd'],r['chosen_odds'] or q['home_odds']) if r['chosen_side'] else ('push',0.)
   if state!=r['settlement'] or abs(net-float(r['net_u']))>1e-7:issues['receipt_settlement_mismatch']+=1
   receipt_unique_rows[fid]['independent_receipt_audit']='pass'
  except Exception:issues['receipt_audit_exception']+=1
 for m in summary['models']:
  got=[r for r in receipts if r['method']==m]; inc=[r for r in got if not r['frozen_overlap']]
  exp=summary['actual_receipt_replay']['models'][m]['incremental_outside_frozen']
  if len(inc)!=exp['n'] or abs(sum(float(r['net_u']) for r in inc)-exp['net_U'])>1e-6:issues['receipt_summary_reconciliation']+=1
 def write_gz(path,items):
  with open(path,'wb') as rawf:
   with gzip.GzipFile(fileobj=rawf,mode='wb',mtime=0) as gz:
    for item in items:gz.write((json.dumps(item,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 write_gz(OUT/'historical_crown_raw_audit_20261121.jsonl.gz',sorted(historical_evidence,key=lambda x:x['fid']))
 write_gz(OUT/'actual_receipt_raw_audit_20261121.jsonl.gz',[{'fid':k,'received_utc':v['receipt_quote']['received_utc'],
    'source_event_utc':v['receipt_quote']['source_event_utc'],'kickoff_utc':v['receipt_quote']['kickoff_utc'],
    'raw_sha256':v['receipt_quote']['raw_sha256'],'snapshot_sha256':v['receipt_quote']['snapshot_sha256'],
    'line':v['receipt_quote']['line'],'home_odds':v['receipt_quote']['home_odds'],'away_odds':v['receipt_quote']['away_odds'],
    'league':v['league'],'home_id':v['home_id'],'away_id':v['away_id'],'hg':v['hg'],'ag':v['ag']}
    for k,v in sorted(receipt_unique_rows.items()) if v.get('independent_receipt_audit')=='pass'])
 result={'pass':not issues,'historical_rows_verified':len(rows),'historical_unique_FIDs':len(set(r['fid'] for r in methods['market_only'])),
  'historical_raw_Crown_contracts_matched':raw_verified,'model_count':len(methods),
  'actual_receipt_model_rows':len(receipts),'actual_receipt_unique_FIDs':len(receipt_ids),
  'actual_receipt_raw_and_snapshot_audited_unique_FIDs':len({k for k,v in receipt_unique_rows.items() if v.get('independent_receipt_audit')=='pass'}),
  'issues':dict(issues),'note':'Price receipt validity does not establish contemporaneous availability of retrospective lineup history.'}
 (OUT/'independent_verification_20261121.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
