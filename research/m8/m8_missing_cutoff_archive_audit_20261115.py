from pathlib import Path
import json,collections,datetime,hashlib,math
from zoneinfo import ZoneInfo
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_extra_inventory_frozen_eight_20261115.py').read_text()
exec(s.split("print('INVENTORIES'")[0])
prior_valid={r['fid'] for r in map(json.loads,(R/'m8_extra_inventory_frozen_eight_20261115.jsonl').open())}
def dt(v):return datetime.datetime.fromisoformat(str(v).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def inspect(p,fid,lid):
 try:
  x=next(q for q in json.loads(p.read_bytes())['data'] if str(q['id'])==fid)
  if str(x['l_id'])!=lid or x.get('status')!='full':return 'invalid_fixture'
  ko=dt(x['start'])
  if not 2019<=ko.year<=2026:return 'outside_year'
  b=next((q for q in x['bookmakers'] if q.get('slug')=='crown'),None)
  if b is None:return 'no_crown'
  n=0;earliest=None
  for q in b.get('asian_list') or []:
   try:
    t=dt(q[4]);l,h,a=map(float,q[1:4])
    if t<ko and h>1 and a>1 and all(math.isfinite(x) for x in (l,h,a)) and abs(l*4-round(l*4))<1e-7:
     n+=1
     if earliest is None or t<earliest:earliest=t
   except:continue
  if earliest is None:return 'no_pregame_path'
  hr=(ko-earliest).total_seconds()/3600
  if hr>=6:return 'valid'
  if hr>=1:return 'first_quote_T6_to_T1'
  return 'first_quote_after_T1'
 except Exception:return 'unreadable'
idx_lookup={str(r['match_id']):r.get('response_sha256') for r in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
counts=collections.Counter();alts=collections.Counter();recovered={};details=[]
raw=P/'data/crown_quote_store/raw/historical'
for fid,lid,p,sha,src in sources.values():
 if fid in prior_valid:continue
 reason=inspect(p,fid,lid);counts[reason]+=1
 if reason=='outside_year':continue
 paths=sorted((raw/fid).glob('*.json'))
 mp=P/f'data/m5-crown-authorized/crown-responses/{fid}.json'
 if mp.exists() and mp!=p:paths.append(mp)
 # Use only explicitly Crown raw archive or M5 validated file; no need to inspect other bookmaker paths.
 paths=[q for q in paths if q!=p]
 altlist=[]
 for candidate in paths:
  if candidate==mp:
   q=idx_lookup.get(fid) if 'idx_lookup' in globals() else None
   if not q:continue
   if hashlib.sha256(candidate.read_bytes()).hexdigest()!=q:continue
  state=inspect(candidate,fid,lid);alts[state]+=1;altlist.append(state)
  if state=='valid' and fid not in recovered:
   recovered[fid]=(fid,lid,candidate,None,'extra')
 details.append({'fid':fid,'league':lid,'reason':reason,'alternative_count':len(paths),'alternative_states':altlist,'recovered':fid in recovered})
out={'counts':dict(counts),'alternative_files':dict(alts),'recovered':len(recovered),'missing_with_alternative':sum(x['alternative_count']>0 for x in details)}
print('GAPS',out,flush=True)
(R/'m8_missing_cutoff_archive_audit_20261115.json').write_text(json.dumps(out,indent=2))
(R/'m8_missing_cutoff_archive_audit_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in details))
(R/'m8_missing_cutoff_recovered_sources_20261115.json').write_text(json.dumps({k:[v[0],v[1],str(v[2]),v[3],v[4]] for k,v in recovered.items()},indent=2))
