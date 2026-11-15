import json,collections,datetime,math,re,unicodedata,hashlib
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_joint_distribution_calibration_20261115.py').read_text()
exec(s[:s.index("out={'method'")])
# Index only already archived ESPN and Crown records; no external network or non-Crown prices.
D=P.parent/'data/epl_laliga_crown_5seasons'
m=json.load((D/'espn_identity_review.json').open())
manifest=json.load((P.parent/'data/m5-crown-authorized/candidate-manifest.json').open())['rows']
def dt1(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(datetime.timezone.utc)
def norm(x):
 x=unicodedata.normalize('NFKD',str(x).lower()).encode('ascii','ignore').decode()
 return re.sub('[^a-z0-9]','',x)
L={'eng_1':'England Premier League','esp_1':'Spain La Liga'}
target={r['fid']:r for r in rows if r['T']==12}
C=collections.Counter()
idx=collections.defaultdict(list)
for r in manifest:
 if r['league'] not in L.values():continue
 try:
  fid=str(r['match_id']);k=dt1(r['kickoff_utc']);h,a=int(r['home_goals']),int(r['away_goals'])
  idx[(r['league'],k,h,a)].append((fid,r['home'],r['away']))
 except:continue
# Exact Crown source match identity checked separately when joining odds.
ep={}
for p in sorted((D/'espn_source').glob('*.json')):
 l=L.get(p.stem.rsplit('_',1)[0])
 if not l:continue
 for e in json.load(p.open()).get('events',[]):
  C['event_rows']+=1
  try:
   c=e['competitions'][0];assert c['status']['type']['name']=='STATUS_FULL_TIME'
   k=dt1(e['date']);y=k.year if k.month>=7 else k.year-1
   team={x['homeAway']:x for x in c['competitors']};h,a=team['home'],team['away'];hg,ag=int(h['score']),int(a['score'])
   mp=m.get(f'{l}|{y}',{}).get('team_map',{})
   hn=h['team']['displayName'];an=a['team']['displayName'];hh=mp.get(hn,hn);aa=mp.get(an,an)
   candidates=[x for x in idx.get((l,k,hg,ag),[]) if norm(x[1])==norm(hh) and norm(x[2])==norm(aa)]
   if len({x[0] for x in candidates})!=1:C['unmatched_identity']+=1;continue
   fid=candidates[0][0];v=target.get(fid)
   if not v:C['outside_T12']+=1;continue
   if (hg,ag)!=(v['hg'],v['ag']) or k.date().isoformat()!=v['date']:C['target_disagreement']+=1;continue
   def parse(team,score):
    z={a['name']:float(a['displayValue']) for a in team['statistics'] if a['name'] in ('totalShots','shotsOnTarget','possessionPct','totalGoals')}
    assert z['totalGoals']==score and 0<=z['shotsOnTarget']<=z['totalShots'] and 0<=z['possessionPct']<=100
    return z
   hs,as_=parse(h,hg),parse(a,ag)
   assert abs(hs['possessionPct']+as_['possessionPct']-100)<.2
   record={'fid':fid,'league':v['league'],'date':v['date'],'year':v['year'],'ko':k.isoformat(),'home':v['home_id'],'away':v['away_id'],'hg':hg,'ag':ag,'hshots':hs['totalShots'],'ashots':as_['totalShots'],'hsot':hs['shotsOnTarget'],'asot':as_['shotsOnTarget'],'hposs':hs['possessionPct'],'aposs':as_['possessionPct'],'espn_id':str(e['id'])}
   if fid in ep and ep[fid]!=record:C['conflicting_duplicates']+=1;continue
   if fid in ep:C['duplicate_events']+=1
   ep[fid]=record
  except (AssertionError,ValueError,KeyError,IndexError,TypeError):C['not_full_or_bad_stats']+=1
# Confirm exact UTC match against original Crown source for each matched match.
rs=P/'m8_early_exact_cross_market_consistency_20261115.py';exec(rs.read_text().split('C=collections.Counter();rows=[]')[0])
# prefix redefines P/R and jobs; retain target, C from ESPN.
verified={}
for fid,r in ep.items():
 try:
  f,sha,lid=jobs[fid];b=f.read_bytes();assert not sha or hashlib.sha256(b).hexdigest()==sha
  x=next(v for v in json.loads(b)['data'] if str(v['id'])==fid)
  assert str(x['l_id'])==r['league']==str(lid) and dt(x['start']).isoformat()==r['ko'] and str(x['h_id'])==r['home'] and str(x['a_id'])==r['away'] and (int(x['hg']),int(x['ag']))==(r['hg'],r['ag']) and x['status']=='full'
  verified[fid]=r
 except Exception:C['raw_disagreement']+=1
ep=verified;P=R
print('MATCHED',len(ep),dict(collections.Counter(r['year'] for r in ep.values())),dict(C),flush=True)
(P/'m8_espn_cached_performance_verified_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in ep.values()))
# Prior match performance data only. Decayed averages of attack and opposition shot activity, plus goal-to-shot residual.
hist=sorted(ep.values(),key=lambda r:(r['date'],r['fid']));state={};j=0;feat={}
def day(r):return datetime.date.fromisoformat(r['date']).toordinal()
def get(key,t):
 a,b,last=state.get(key,(0.,0.,t));w=2**(-(t-last)/180);return a*w,b*w
def add(key,v,t):
 a,b=get(key,t);state[key]=(a+v,b+1,t)
def avg(key,t,p):
 a,b=get(key,t);return (a+8*p)/(b+8)
metrics=('shots','sot','poss','goals')
prior=(12.,4.,50.,1.4)
for r in hist:
 t=day(r)
 while j<len(hist) and day(hist[j])<=t-3:
  q=hist[j];tt=day(q);j+=1
  for role,opp in [('h','a'),('a','h')]:
   team=(q['league'],q['home'] if role=='h' else q['away'])
   vals=[q[role+'shots'],q[role+'sot'],q[role+'poss'],q[role+'g']]
   vals_opp=[q[opp+'shots'],q[opp+'sot'],q[opp+'poss'],q[opp+'g']]
   for k,a,b in zip(metrics,vals,vals_opp):
    add((team,'for',k),a,tt);add((team,'against',k),b,tt)
 h=(r['league'],r['home']);a=(r['league'],r['away'])
 vals=[]
 for team in (h,a):
  for direction in ('for','against'):
   x=[avg((team,direction,k),t,p) for k,p in zip(metrics,prior)]
   vals+=x+[x[3]/max(x[1],.01)]
 feat[r['fid']]=vals
z=[target[f] for f in ep];valid=[]
for st in range(0,len(z),4000):
 v=z[st:st+4000];ol,al=vec(v,'ol'),vec(v,'al');op=vec(v,'ou')/(vec(v,'oo')+vec(v,'ou'));ap=vec(v,'aa')/(vec(v,'ah')+vec(v,'aa'))
 total,ok1,e1=solve(op,.0001,20.,lambda x:ou_share(x,ol));frac,ok2,e2=solve(ap,.00001,.99999,lambda x:ah_share(total,x,al))
 for i,r in enumerate(v):
  if ok1[i] and ok2[i] and e1[i]<1e-5 and e2[i]<1e-5:r['mh']=float(total[i]*frac[i]);r['ma']=float(total[i]*(1-frac[i]));valid.append(r)
def features(r,kind):
 h,a=r['mh'],r['ma'];x=[1,np.log(h),np.log(a),np.log(h+a),np.log1p(r['age_ah']),np.log1p(r['age_ou']),r['al'],r['ol']]
 if kind=='market_performance':x+=feat[r['fid']]
 return x
out={'raw_verified':len(ep),'counts':dict(C),'years_coverage':dict(collections.Counter(r['year'] for r in ep.values())),'league_coverage':dict(collections.Counter(r['league'] for r in ep.values())),'tests':{},'availability':'prior >=3 UTC dates historical proxy; archive retrieved 2026, not original receipt'}
for y in (2024,2025,2026):
 tr=[r for r in valid if r['year']<y];te=[r for r in valid if r['year']==y]
 if not tr or not te:continue
 res={'train_n':len(tr),'test_n':len(te)}
 for kind in ('market','market_performance'):
  X=np.array([features(r,kind) for r in tr]);Xt=np.array([features(r,kind) for r in te])
  h=goals_predict(X,vec(tr,'hg'),np.log(vec(tr,'mh')),Xt,np.log(vec(te,'mh')))
  a=goals_predict(X,vec(tr,'ag'),np.log(vec(tr,'ma')),Xt,np.log(vec(te,'ma')))
  res[kind]=evaluate(te,h,a)
 out['tests'][str(y)]=res;print('TEST',y,json.dumps(res),flush=True)
(P/'m8_espn_cached_performance_verified_20261115.json').write_text(json.dumps(out,indent=2))
