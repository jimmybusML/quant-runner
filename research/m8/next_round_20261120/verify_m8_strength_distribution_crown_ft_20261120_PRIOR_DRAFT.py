#!/usr/bin/env python3
"""Independent Crown raw-response, event-time quote and FT identity audit."""
import collections,datetime as dt,hashlib,json,math
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[3];DATA=Path('/Users/mac/QuantAsiaDesk/research-work');OUT=ROOT/'research/m8/next_round_20261120'
FEATURE=DATA/'m8_late_full_path_water_features_20261114.jsonl';SCORES=DATA/'m8_independent_score_strength_20261114.jsonl';FROZEN=DATA/'m8_foundation_20261115/historical_membership.jsonl'
RAW=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses');IDX=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-response-index.jsonl')
def sha(b):return hashlib.sha256(b).hexdigest()
def parse(x):
 z=dt.datetime.fromisoformat(str(x).replace('Z','+00:00').replace(' ','T'))
 return z if z.tzinfo else z.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(dt.timezone.utc)
def read(p):return [json.loads(l) for l in p.open() if l.strip()]
features={str(x['fid']):x for x in read(FEATURE) if 2024<=int(x['year'])<=2026};scores={str(x['fid']):x for x in read(SCORES)};frozen={str(x['fid']) for x in read(FROZEN)}
target=set(features)-frozen;src={}
for p in [DATA/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1733Z.jsonl',DATA/'m7/m7_original49_historical_Crown_T30_2h_movement_inventory_20261114.jsonl',DATA/'m8_extra_inventory_frozen_eight_20261115.jsonl',DATA/'m8_raw_capture_unindexed_frozen_replay_20261115.jsonl']:
 if not p.exists():continue
 for x in read(p):
  fid=str(x.get('fixture_id',x.get('fid','')))
  if fid in target and x.get('source_file'):
   path=Path(x['source_file']);src.setdefault(fid,{'path':path,'sha':x.get('raw_sha256')})
idx={str(x['match_id']):x for x in read(IDX)}
for fid in target:
 f=features[fid]
 if int(f['year'])==2026 and (RAW/f'{fid}.json').is_file():src[fid]={'path':RAW/f'{fid}.json','sha':idx.get(fid,{}).get('response_sha256')}
counts=collections.Counter();examples=[];verified=[]
for fid in sorted(target):
 f=features[fid];sc=scores.get(fid);s=src.get(fid)
 if not sc:counts['missing_score_row']+=1;continue
 if not s or not s['path'].is_file():counts['raw_response_missing']+=1;continue
 body=s['path'].read_bytes();bh=sha(body)
 if s.get('sha') and s['sha']!=bh:counts['body_sha_mismatch']+=1;continue
 try:doc=json.loads(body)
 except Exception:counts['invalid_json']+=1;continue
 matches=doc.get('data') or [];matches=matches if isinstance(matches,list) else [matches] if isinstance(matches,dict) else []
 ms=[m for m in matches if str(m.get('id'))==fid]
 if len(ms)!=1:counts['fid_cardinality']+=1;continue
 m=ms[0]
 if str(m.get('l_id'))!=str(f['league']) or str(m.get('h_id'))!=str(sc['home']) or str(m.get('a_id'))!=str(sc['away']):counts['identity_mismatch']+=1;continue
 try:ko=parse(m['start']);scoreok=(int(m['hg'])==int(sc['hg']) and int(m['ag'])==int(sc['ag']))
 except Exception:counts['kickoff_or_score_invalid']+=1;continue
 if ko.date().isoformat()!=str(f['date'])[:10] or not scoreok:counts['kickoff_or_ft_mismatch']+=1;continue
 cb=[b for b in m.get('bookmakers',[]) if str(b.get('slug','')).lower()=='crown']
 if len(cb)!=1:counts['crown_missing_or_ambiguous']+=1;continue
 qs=[]
 for q in cb[0].get('asian_list') or []:
  try:
   t=parse(q[4]);ln,ho,ao=map(float,q[1:4])
   if t<=ko-dt.timedelta(hours=1) and ho>1 and ao>1 and abs(ln*4-round(ln*4))<1e-8:qs.append((t,ln,ho,ao))
  except Exception:continue
 if not qs:counts['no_quote_by_tminus1h']+=1;continue
 q=max(qs,key=lambda z:z[0]); expected=(float(f['end_line']),float(f['home_price']),float(f['away_price']))
 if any(abs(a-b)>1e-8 for a,b in zip(q[1:],expected)):
  counts['quote_mismatch']+=1
  if len(examples)<20:examples.append({'fid':fid,'raw_quote':q[1:],'feature_quote':expected,'source_event_utc':q[0].isoformat()})
  continue
 verified.append({'fid':fid,'year':int(f['year']),'date':f['date'],'league':str(f['league']),'kickoff_utc':ko.isoformat(),'source_event_utc':q[0].isoformat(),'line':q[1],'home_odds':q[2],'away_odds':q[3],'FT_home':int(m['hg']),'FT_away':int(m['ag']),'body_sha256':bh,'raw_path':str(s['path'])})
 counts['verified']+=1
with (OUT/'crown_ft_independent_audit_20261120.jsonl.gz').open('wb') as raw:
 import gzip
 with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
  for x in verified:gz.write((json.dumps(x,sort_keys=True)+'\n').encode())
result={'target_unique_fids':len(target),'raw_source_paths_available':len(src),'verified_raw_crown_ft_quotes':len(verified),'coverage_pct':round(100*len(verified)/len(target),4),'checks':'body SHA when indexed; FID, Crown league/team IDs, kickoff Beijing-date, FT, Crown latest AH quote at/before T-1h matches stored T1 features; quarter lines valid','failures':dict(counts),'mismatch_examples':examples,'feature_sha256':sha(FEATURE.read_bytes()),'score_sha256':sha(SCORES.read_bytes()),'frozen_sha256':sha(FROZEN.read_bytes())}
(OUT/'crown_ft_independent_audit_summary_20261120.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
