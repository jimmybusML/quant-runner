import json,datetime,hashlib,collections,bisect
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
def read(p):return list(map(json.loads,(P/p).open()))
def dt(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def local(s):return dt(s.replace(' ','T')+'+08:00').astimezone(datetime.timezone.utc)
E={r['fid']:r for r in read('m8_espn_performance_confirmed_18leagues_20261115.jsonl')}
T={r['fid']:r for f in ('m8_performance_batch_probe_20261115.jsonl','m8_performance_cross_year_20261115/verified_new.jsonl','m8_performance_contiguous_20261115/verified_new.jsonl','m8_performance_gap_recovery_20261115/verified_new.jsonl') for r in read(f)}
test={f for f,r in E.items() if r['league'] in ('1','14') and r['year'] in (2024,2025,2026)}
assert len(test)==2017
archive=read('m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
inv={r['fixture_id']:r for r in read('m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl')}
target={r['fid']:r for r in read('m8_early_joint_market_inventory_20261115.jsonl') if r['T']==12}
by=collections.defaultdict(list)
for r in archive:
 if r['received_minutes_to_kickoff']>=720 and 'AH' in r['markets'] and 'OU' in r['markets']:by[str(r['fixture_id'])].append(r)
assert len(by)==1537 and len(set(by)&test)==67
new=set(by)-test
assert len(new)==1470
def digest(b):return hashlib.sha256(b).hexdigest()
def verify(r):
 f=str(r['fixture_id']);ko=dt(r['kickoff_utc']);recv=dt(r['received_utc'])
 assert (ko-recv).total_seconds()>=43200,'receipt_exact_cutoff'
 p=Path(r['source_file']);a=json.loads(p.read_bytes());raw=a['raw_response']
 assert digest(raw.encode())==a['raw_sha256']==r['raw_sha256'],'raw_sha'
 assert dt(a['received_at'])==recv and a['classification']=='SNAPSHOT_OK' and a['http_status']==200,'attempt_identity'
 b=(p.parent.parent/'snapshot.json').read_bytes();s=json.loads(b)
 assert digest(b)==r['snapshot_sha256'],'snapshot_sha'
 assert str(s['match_id'])==f and dt(s['kickoff_at'])==ko and dt(s['received_at'])==recv and s['source_bookmaker']=='crown' and s['source_bookmaker_verified'] is True,'snapshot_identity'
 x=json.loads(raw)['data'][0]
 assert str(x['id'])==f and str(x['l_id'])==str(r['league_id']) and local(x['start'])==ko,'raw_identity'
 bk=next(v for v in x['bookmakers'] if v['slug']=='crown')
 for market,key,sa,sb in [('AH','asian','home','away'),('OU','goal','over','under')]:
  d=bk[key]['close'];q=r['markets'][market];stamp=local(d['time'])
  assert stamp<=recv<ko and stamp==dt(q['source_event_utc']),'quote_timestamp'
  assert float(d['line'])==q['line'] and float(d[sa])==q['odds'][sa] and float(d[sb])==q['odds'][sb],'quote_values'
  assert float(d[sa])>1 and float(d[sb])>1,'quote_price'
 return x
m5={str(r['match_id']):r for r in read('../data/m5-crown-authorized/crown-response-index.jsonl')}
m7=collections.defaultdict(list)
for r in read('m7/m7_schedule_verified_FT_receipt_events_20261111.jsonl'):m7[str(r['fixture_id'])].append(r)
local_ft={p.name.split('-')[0]:p for p in (P/'m8_new_receipt_FT_raw_20261115').glob('*.json')}
ft_source={}
def final(f,x):
 errors=[]
 candidates=[]
 if f in m5:
  r=m5[f];candidates.append(('M5_indexed_raw',P/'../data/m5-crown-authorized/crown-responses'/f'{f}.json',r['response_sha256'],r['captured_at_utc'],None))
 if f in inv:
  r=inv[f];candidates.append(('historical_raw',Path(r['source_file']),r['raw_sha256'],r['historical_capture_received_at_utc'],None))
 for r in m7.get(f,[]):
  candidates.append(('M7_schedule_raw',Path(r['raw_path']),r['raw_sha256'],r['observed_at_utc'],[int(r['home_goals']),int(r['away_goals'])]))
 for tag,p,sha,observed,expected in candidates:
  try:
   b=p.read_bytes();assert digest(b)==sha,'FT_sha'
   body=json.loads(b);data=body['data'];data=data['matches'] if isinstance(data,dict) else data
   q=next(v for v in data if str(v['id'])==f)
   assert q['status']=='full','FT_status'
   assert dt(observed)>local(x['start']),'FT_observation'
   assert all(str(q[k])==str(x[k]) for k in ('id','l_id','h_id','a_id')) and local(q['start'])==local(x['start']),'FT_identity'
   g=[int(q['hg']),int(q['ag'])]
   assert min(g)>=0 and (expected is None or g==expected),'FT_score'
   ft_source[f]=tag
   return g,None
  except Exception as exc:errors.append(str(exc.args[0]) if isinstance(exc,AssertionError) and exc.args else type(exc).__name__)
 if f in local_ft:
  try:
   p=local_ft[f];b=p.read_bytes();assert digest(b)==p.stem.split('-')[-1],'FT_sha'
   q=next(v for v in json.loads(b)['data'] if str(v['id'])==f)
   assert q['status']=='full','FT_status'
   assert all(str(q[k])==str(x[k]) for k in ('id','l_id','h_id','a_id')) and local(q['start'])==local(x['start']),'FT_identity'
   g=[int(q['hg']),int(q['ag'])]
   assert min(g)>=0,'FT_score'
   # Source timestamp separately retained in prior FT attempt result.
   qmeta=next(v for v in json.loads((P/'m8_new_receipt_frozen_eight_FT_20261115.json').read_text())['score_attempts'] if v['fid']==f)
   assert qmeta['sha256']==digest(b) and dt(qmeta['observed_at_utc'])>local(x['start']),'FT_observation'
   ft_source[f]='TC_match_view_raw'
   return g,None
  except Exception as exc:errors.append(str(exc.args[0]) if isinstance(exc,AssertionError) and exc.args else type(exc).__name__)
 return None,';'.join(sorted(set(errors))) if errors else 'no_FT_inventory'
def histories(records):
 h=collections.defaultdict(list)
 for r in records.values():
  for team in (r['home'],r['away']):h[(str(r['league']),str(team))].append(datetime.date.fromisoformat(r['date']))
 return {k:sorted(v) for k,v in h.items()}
eh=histories(E);th=histories(T)
def counts(h,x):
 d=local(x['start']).date()-datetime.timedelta(days=3)
 return [bisect.bisect_right(h.get((str(x['l_id']),str(x[k])),[]),d) for k in ('h_id','a_id')]
rows=[];errors=collections.Counter()
for f in sorted(new):
 xs=sorted(by[f],key=lambda r:dt(r['received_utc']),reverse=True)
 rec={'fid':f,'league':str(xs[0]['league_id']),'league_name':xs[0]['league'],'eligible_archive_rows':len(xs),'verified_receipt':False}
 for r in xs:
  try:x=verify(r)
  except Exception as exc:
   errors[str(exc.args[0]) if isinstance(exc,AssertionError) and exc.args else type(exc).__name__]+=1;continue
  g,why=final(f,x)
  ec=counts(eh,x);tc=counts(th,x)
  rec.update({'verified_receipt':True,'kickoff_utc':r['kickoff_utc'],'receipt_utc':r['received_utc'],'horizon':r['snapshot_horizon'],'receipt_minutes':(dt(r['kickoff_utc'])-dt(r['received_utc'])).total_seconds()/60,'FT':g,'FT_error':why,'FT_source':ft_source.get(f),'ESPN_prior_counts':ec,'TC_prior_counts':tc,'current_ESPN':f in E,'current_TC':f in T,'historical_T12':f in target,'historical_T12_same_identity':f in target and all(str(target[f][k])==str(x[v]) for k,v in [('league','l_id'),('home_id','h_id'),('away_id','a_id')]) and target[f]['date']==local(x['start']).date().isoformat()})
  break
 rows.append(rec)
valid=[r for r in rows if r['verified_receipt']]
ft=[r for r in valid if r['FT'] is not None]
def group(a):
 return {'n':len(a),'current_ESPN':sum(r['current_ESPN'] for r in a),'current_TC':sum(r['current_TC'] for r in a),'historical_T12':sum(r['historical_T12_same_identity'] for r in a),'both_ESPN_prior':sum(min(r['ESPN_prior_counts'])>0 for r in a),'both_TC_prior':sum(min(r['TC_prior_counts'])>0 for r in a),'both_prior_one_source':sum(max(min(r['ESPN_prior_counts']),min(r['TC_prior_counts']))>0 for r in a),'either_team_no_prior_both_sources':sum(any(r['ESPN_prior_counts'][j]==0 and r['TC_prior_counts'][j]==0 for j in (0,1)) for r in a)}
out={'method':'Archived candidate inventory only. Latest independently verified existing receipt at least 12h before kickoff per fixture, no formal rule. Recheck raw and snapshot SHA, Crown odds, timestamp, exact fixture/league/team and FT source. Prior history counts only (3 UTC dates legacy proxy), no new filter or fitted model; real historical receipt of performance unavailable.','prior_universe':1537,'previous_test':67,'new_candidates':len(new),'verified_receipt':group(valid),'verified_receipt_and_FT':group(ft),'receipt_errors':dict(errors),'FT_sources':dict(collections.Counter(ft_source.values())),'FT_errors':dict(collections.Counter(r['FT_error'] for r in valid if r['FT'] is None)),'candidate_leagues':dict(collections.Counter(r['league_name'] for r in rows)),'verified_FT_leagues':dict(collections.Counter(r['league_name'] for r in ft)),'by_league':{},'new_confirmed_prospective_evaluation_n':0}
for league in sorted({r['league'] for r in valid}):
 a=[r for r in ft if r['league']==league]
 out['by_league'][league]={'name':next(r['league_name'] for r in valid if r['league']==league),**group(a)}
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':digest((P/m['historical_membership']['local_file']).read_bytes())==m['historical_membership']['sha256'],'inputs':all(digest((P/k).read_bytes())==v for k,v in m['input_sha256'].items()),'scripts':all(digest((P/k).read_bytes())==v for k,v in m['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_independent_receipt_coverage_20261115.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
(P/'m8_independent_receipt_coverage_20261115.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
print(json.dumps({k:v for k,v in out.items() if k not in ('by_league','candidate_leagues','verified_FT_leagues')},ensure_ascii=False),flush=True)
print('BY_LEAGUE',json.dumps(out['by_league'],ensure_ascii=False),flush=True)
