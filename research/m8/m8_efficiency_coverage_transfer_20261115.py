import json,datetime,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_possession_efficiency_20261115.py').read_text()
exec(s[:s.index("out={'method'")])
# Same archived fixtures, common histories, no test-year fitting.
E=ep
Tids=set(T)
matched=set(E)&Tids
assert len(matched)==51
esparse={f:E[f] for f in matched}
tsparse={f:T[f] for f in matched}
def features_for(hist):
 # Same previous 180-day decay and 8-match shrinkage; return effective prior match counts.
 hist=sorted(hist.values(),key=lambda r:(r['date'],r['fid']))
 st={}; counts={}; ff={}; j=0
 def day(r):return datetime.date.fromisoformat(r['date']).toordinal()
 def get(k,t):
  a,b,last=st.get(k,(0.,0.,t));w=2**(-(t-last)/180);return a*w,b*w
 def add(k,x,t):
  a,b=get(k,t);st[k]=(a+x,b+1,t)
 for r in hist:
  t=day(r)
  while j<len(hist) and day(hist[j])<=t-3:
   q=hist[j];tt=day(q);j+=1
   for role,opp in [('h','a'),('a','h')]:
    team=(q['league'],q['home'] if role=='h' else q['away'])
    for metric,field in [('shots','shots'),('sot','sot'),('poss','poss'),('goals','g')]:
     add((team,'for',metric),q[role+field],tt);add((team,'against',metric),q[opp+field],tt)
  v=[];c=[]
  for team in ((r['league'],r['home']),(r['league'],r['away'])):
   c.append(get((team,'for','shots'),t)[1])
   for direction in ('for','against'):
    x=[]
    for metric,prior in [('shots',12.),('sot',4.),('poss',50.),('goals',1.4)]:
     a,b=get((team,direction,metric),t);x.append((a+8*prior)/(b+8))
    v+=x+[x[3]/max(x[1],.01)]
  ff[r['fid']]=v;counts[r['fid']]=min(c)
 return ff,counts
dense,dc=features_for(E);sparse,sc=features_for(esparse);tmatch,mc=features_for(tsparse);tdense,tcnt=features_for(T)
assert all(np.allclose(esfeat[f],dense[f]) for f in dense)
assert all(np.allclose(tcfeat[f],tdense[f]) for f in tdense)
cores=[r for r in esvalid if r['league'] in ('1','14')]
def run(tr,te,F,counts):
 mask=np.ones(len(te),bool);fs={k:forecast(tr,te,F,k) for k in variants}
 return {'n':len(te),'train_n':len(tr),'median_min_effective_prior':round(float(np.median([counts[r['fid']] for r in te])),3),'zero_prior_either_team':sum(counts[r['fid']]==0 for r in te),'models':{k:metrics(te,p,mask) for k,p in fs.items()}}
out={'method':'Same T12 market, annual prior-year training. Fixed models. Matched 51 ESPN/TC identical fixtures and identical restricted historical coverage. Effective counts are diagnostics, no filter/gate. Same-source cross-league transfer, no outcome-driven model choice. Historical explored samples.','matched':{},'other_ESPN':{},'leave_league_out':{},'coverage':{}}
tr=[r for r in cores if r['year']<2026]
te=[r for r in cores if r['fid'] in matched]
assert len(te)==51
for label,ff,cc in [('ESPN_dense',dense,dc),('ESPN_matched_only',sparse,sc),('TC_matched_only',tmatch,mc),('TC_full_archive',tdense,tcnt)]:out['matched'][label]=run(tr,te,ff,cc)
other=[r for r in esvalid if r['league'] not in ('1','14') and r['year']==2026]
out['other_ESPN']=run(tr,other,dense,dc)
for y in (2024,2025,2026):
 out['leave_league_out'][str(y)]={}
 for li in ('1','14'):
  a=[r for r in cores if r['year']<y and r['league']!=li];b=[r for r in cores if r['year']==y and r['league']==li]
  out['leave_league_out'][str(y)][li]=run(a,b,dense,dc)
for y in (2023,2025,2026):
 a=[r for r in cores if r['year']<y];b=[r for r in tcvalid if r['year']==y and r['league'] not in ('1','14')]
 out['coverage'][str(y)]=run(a,b,tdense,tcnt)
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_efficiency_coverage_transfer_20261115.json').write_text(json.dumps(out,indent=2))
def summary(r):
 return {k:r[k] for k in ('n','train_n','median_min_effective_prior','zero_prior_either_team')}|{k:(v['U'],v['ROI'],v['NLL']) for k,v in r['models'].items()}
for k,r in out['matched'].items():print('MATCH',k,summary(r),flush=True)
print('OTHER_ESPN',summary(out['other_ESPN']),flush=True)
for y,d in out['leave_league_out'].items():
 for li,r in d.items():print('LEAGUE',y,li,summary(r),flush=True)
for y,r in out['coverage'].items():print('TC',y,summary(r),flush=True)
print('FOUNDATION',out['foundation'],flush=True)
