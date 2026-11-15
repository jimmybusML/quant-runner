import json,hashlib,datetime,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_receipt_performance_replay_20261115.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Recover seven previously fetched match/view performance samples omitted from the league-page history.
meta=json.loads((P/'m8_performance_probe_20261115.json').read_text())
history=dict(T);added=[];issues=collections.Counter()
for a in meta['results']:
 if not a.get('identity_and_FT'):issues['prior_response_not_verified']+=1;continue
 f=a['fid'];b=(P/'m8_performance_probe_20261115'/f"{f}-{a['sha256']}.json").read_bytes()
 assert digest(b)==a['sha256']
 x=next(q for q in json.loads(b)['data'] if str(q['id'])==f)
 t=audit['target'][f]
 assert str(x['l_id'])==t['league'] and str(x['h_id'])==t['home_id'] and str(x['a_id'])==t['away_id'] and x['status']=='full' and (int(x['hg']),int(x['ag']))==(t['hg'],t['ag'])
 ko=audit['local'](x['start'])
 assert ko.date().isoformat()==t['date']
 # Verify exact kickoff against original indexed Crown raw if available, otherwise historical file.
 z=audit['inv'].get(f)
 if f in audit['m5']:
  m=audit['m5'][f];raw=(P.parent/'data/m5-crown-authorized/crown-responses'/f'{f}.json').read_bytes();assert digest(raw)==m['response_sha256']
 elif z:
  raw=Path(z['source_file']).read_bytes();assert digest(raw)==z['raw_sha256']
 else:issues['no_indexed_Crown_raw']+=1;continue
 q=next(q for q in json.loads(raw)['data'] if str(q['id'])==f)
 assert audit['local'](q['start'])==ko and q['status']=='full' and all(str(q[k])==str(x[k]) for k in ('id','l_id','h_id','a_id','hg','ag'))
 so,sf,po=[[float(v) for v in x[k]] for k in ('shot_on','shot_off','possess')]
 if any(v<0 for v in so+sf+po) or abs(sum(po)-100)>1:issues['incomplete_stats']+=1;continue
 if f in history:issues['already_in_history']+=1;continue
 r={'fid':f,'league':t['league'],'date':t['date'],'year':t['year'],'home':t['home_id'],'away':t['away_id'],'hg':t['hg'],'ag':t['ag'],'hshots':so[0]+sf[0],'ashots':so[1]+sf[1],'hsot':so[0],'asot':so[1],'hposs':po[0],'aposs':po[1],'raw_sha256':a['sha256'],'received_utc':a['retrieved_utc']}
 history[f]=r;added.append(r)
idx=histindex(history);features={};covered=set()
for r in rows:
 v,n,_,_=feature(r,idx);features[r['fid']]=v
 if min(n)>0:covered.add(r['fid'])
orig=[r for r in rows if r['fid'] in both['TC']]
old=g['forecast'](tr,orig,featuremaps['TC'],'full_shot_efficiency')
new=g['forecast'](tr,orig,features,'full_shot_efficiency')
assert g['stat'](old[2])['U']==22.435
extra=[r for r in rows if r['fid'] in covered-both['TC']]
result={'method':'Separate historical feature coverage sensitivity from already stored individual TC probe raw; original candidate retained. Prior performance receipt timing unverified. No newly acquired data or new formal rule.','added':added,'issues':dict(issues),'before':len(T),'after':len(history),'matched_existing':g['stat'](new[2]),'original_existing':g['stat'](old[2]),'changed_sides':int((old[1]!=new[1]).sum()),'newly_covered':len(extra),'new_coverage_leagues':dict(collections.Counter(r['league'] for r in extra))}
if extra:
 p=g['forecast'](tr,extra,features,'full_shot_efficiency');result['newly_covered_diagnostic']=g['stat'](p[2])
(P/'m8_tc_local_probe_bridge_20261115.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps({**result,'added':[(r['fid'],r['league'],r['date']) for r in added]},ensure_ascii=False),flush=True)
