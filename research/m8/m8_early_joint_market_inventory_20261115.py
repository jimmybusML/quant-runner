from pathlib import Path
import json,math,datetime,bisect,hashlib,collections
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_early_exact_cross_market_consistency_20261115.py').read_text().split('C=collections.Counter();rows=[]')[0])
C=collections.Counter();rows=[]
for fid,(file,sha,lid) in jobs.items():
 try:
  raw=file.read_bytes()
  if sha and hashlib.sha256(raw).hexdigest()!=sha:C['sha_failure']+=1;continue
  x=next(q for q in json.loads(raw)['data'] if str(q['id'])==fid)
  if str(x['l_id'])!=str(lid) or x['status']!='full':C['identity_or_FT']+=1;continue
  ko=dt(x['start']);hg,ag=int(x['hg']),int(x['ag']);b=next(q for q in x['bookmakers'] if q.get('slug')=='crown')
  markets={}
  for name,field,sides in [('AH','asian',('home','away')),('OU','goal',('over','under'))]:
   paths=[]
   for q in b.get(field+'_list') or []:
    try:
     t=dt(q[4]);l,a,c=map(float,q[1:4])
     if t<ko and a>1 and c>1 and all(math.isfinite(z) for z in (l,a,c)) and abs(l*4-round(l*4))<1e-7:paths.append((t,l,a,c,'list'))
    except:pass
   # timestamped historical open/close snapshots; distinct from complete path.
   for tag in ('open','close'):
    q=(b.get(field) or {}).get(tag)
    if not isinstance(q,dict):continue
    try:
     t=dt(q['time']);l,a,c=float(q['line']),float(q[sides[0]]),float(q[sides[1]])
     if t<ko and a>1 and c>1 and all(math.isfinite(z) for z in (l,a,c)) and abs(l*4-round(l*4))<1e-7:paths.append((t,l,a,c,tag))
    except:pass
   paths.sort(key=lambda q:(q[0],q[4]=='list'));markets[name]=paths
  x12=[]
  for tag in ('open','close'):
   q=(b.get('odds') or {}).get(tag)
   if not isinstance(q,dict):continue
   try:
    t=dt(q['time']);o=[float(q[s]) for s in ('home','draw','away')]
    if t<ko and all(math.isfinite(v) and v>1 for v in o):
     p=[1/v for v in o];x12.append((t,[v/sum(p) for v in p]))
   except:pass
  for T in (24,12,6):
   cut=ko-datetime.timedelta(hours=T);chosen={}
   for market,path in markets.items():
    j=bisect.bisect_right([q[0] for q in path],cut)-1
    if j>=0:
     chosen[market]=path[j];C[f'{ko.year}|T{T}|{market}']+=1
   if len(chosen)!=2:continue
   ah,ou=chosen['AH'],chosen['OU'];r={'fid':fid,'year':ko.year,'date':ko.date().isoformat(),'league':str(lid),'T':T,'home_id':str(x.get('h_id') or ''),'away_id':str(x.get('a_id') or ''),'hg':hg,'ag':ag,'al':ah[1],'ol':ou[1],'ah':ah[2],'aa':ah[3],'oo':ou[2],'ou':ou[3],'age_ah':(cut-ah[0]).total_seconds()/3600,'age_ou':(cut-ou[0]).total_seconds()/3600,'ah_kind':ah[4],'ou_kind':ou[4]}
   v=[q for q in x12 if q[0]<=cut]
   if v:
    q=max(v,key=lambda x:x[0]);r['p1x2']=q[1];r['age_1x2']=(cut-q[0]).total_seconds()/3600
   for m,l,ss,od in [('AH',ah[1],('home','away'),ah[2:4]),('OU',ou[1],('over','under'),ou[2:4])]:
    for s,p in zip(ss,od):r[s+'_U']=settle_score(m,l,s,hg,ag,p)[1]
   rows.append(r);C[f'{ko.year}|T{T}|joint']+=1
  C['read_ok']+=1
 except Exception as e:C['error_'+type(e).__name__]+=1
out={'counts':dict(C),'joint_unique':len({r['fid'] for r in rows}),'joint_rows':len(rows),'horizons':{}}
for T in (24,12,6):
 z=[r for r in rows if r['T']==T];out['horizons'][str(T)]={'n':len(z),'year':dict(collections.Counter(r['year'] for r in z)),'both_list':sum(r['ah_kind']=='list' and r['ou_kind']=='list' for r in z),'both_age_3h':sum(max(r['age_ah'],r['age_ou'])<=3 for r in z),'1x2_also':sum('p1x2'in r for r in z),'all_three_age_3h':sum('p1x2'in r and max(r['age_ah'],r['age_ou'],r['age_1x2'])<=3 for r in z)}
(R/'m8_early_joint_market_inventory_20261115.json').write_text(json.dumps(out,indent=2))
(R/'m8_early_joint_market_inventory_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
print('COVERAGE',json.dumps(out['horizons']),'unique',out['joint_unique'],'read',C['read_ok'],flush=True)
