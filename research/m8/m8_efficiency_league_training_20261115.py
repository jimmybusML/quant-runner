import hashlib,json
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_possession_efficiency_20261115.py').read_text()
exec(s[:s.index("out={'method'")])
z=[r for r in esvalid if r['league'] in ('1','14')]
ids={r['fid'] for r in map(json.loads,(P/'m8_foundation_20261115/historical_membership.jsonl').open())}
kind='full_shot_efficiency'
def fit(tr,te,variant):
 X=np.array([base(r,esfeat,kind) for r in tr]);Xt=np.array([base(r,esfeat,kind) for r in te])
 mu=X.mean(0);sd=X.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 X=(X-mu)/sd;Xt=(Xt-mu)/sd
 pen=np.full(X.shape[1],100.);pen[0]=0
 if variant!='shared':
  n=1 if variant=='intercept' else X.shape[1]
  a=np.array([1 if r['league']=='1' else -1 for r in tr]);b=np.array([1 if r['league']=='1' else -1 for r in te])
  X=np.column_stack([X,X[:,:n]*a[:,None]]);Xt=np.column_stack([Xt,Xt[:,:n]*b[:,None]])
  pen=np.r_[pen,np.full(n,100. if variant=='intercept' else float(variant.split('_')[1]))]
 y=vec(tr,'hg')+vec(tr,'ag');offset=np.log(vec(tr,'mh')+vec(tr,'ma'));ot=np.log(vec(te,'mh')+vec(te,'ma'))
 B=np.zeros(X.shape[1]);D=np.diag(pen)
 for _ in range(30):
  w=np.exp(np.clip(offset+X@B,-7,5));step=np.linalg.solve(X.T@(w[:,None]*X)+D,X.T@(y-w)-D@B);B+=step
  if np.max(np.abs(step))<1e-7:break
 total=np.exp(np.clip(ot+Xt@B,-7,3));w,l=ou_wl(total,vec(te,'ol'));eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
 side=eo>=eu;return total,side,np.where(side,vec(te,'over_U'),vec(te,'under_U'))
def splitfit(tr,te,foreign=False):
 x=np.zeros(len(te));s=np.zeros(len(te),bool);p=np.zeros(len(te))
 for li in ('1','14'):
  m=np.array([r['league']==li for r in te]);a=[r for r in tr if (r['league']!=li if foreign else r['league']==li)];b=[r for r in te if r['league']==li]
  x[m],s[m],p[m]=fit(a,b,'shared')
 return x,s,p
def score(te,p):
 x=p[0];y=vec(te,'hg')+vec(te,'ag');return float(np.mean(x-y*np.log(x)))
def groupstats(te,p):
 groups={'all':np.ones(len(te),bool),'outside':np.array([r['fid'] not in ids for r in te]),'H2':np.array([r['date'][5:7]>'06' for r in te]),'EPL':np.array([r['league']=='1' for r in te]),'LaLiga':np.array([r['league']=='14' for r in te])}
 return {g:metrics(te,p,m) for g,m in groups.items() if m.any()}
vs=['shared','intercept','partial_100','partial_500','partial_2000','local']
def get(tr,te,v):return splitfit(tr,te) if v=='local' else fit(tr,te,v)
out={'method':'T12 fixed shot possession efficiency features, annual prior training. Shared/local/foreign and league intercept/partial coefficient models. Research-only penalty variants reused from prior partial pooling. Prior year NLL selects structure, not test ROI. Equal sample control by year with deterministic 10 replicates, average not summed orders. Previously explored historical outcomes.','years':{}}
for y in (2024,2025,2026):
 tr=[r for r in z if r['year']<y];te=[r for r in z if r['year']==y]
 dev=[r for r in tr if r['year']<y-1];val=[r for r in tr if r['year']==y-1]
 scores={v:score(val,get(dev,val,v)) for v in vs}
 pick=min(scores,key=scores.get)
 ps={v:get(tr,te,v) for v in vs};ps['foreign']=splitfit(tr,te,True);ps['prior_NLL_selected']=ps[pick]
 rec={'n':len(te),'train_n':len(tr),'prior_year_NLL':scores,'prior_NLL_choice':pick,'models':{k:groupstats(te,v) for k,v in ps.items()},'equal_size':{}}
 # per-year equal sample count for local/foreign/pooled, common annual composition; deterministic outcome-blind selection.
 for rep in range(10):
  rng=np.random.default_rng(20261115+rep)
  local={li:[] for li in ('1','14')};mixed=[]
  for year in sorted({r['year'] for r in tr}):
   aa={li:sorted([r for r in tr if r['year']==year and r['league']==li],key=lambda r:r['fid']) for li in ('1','14')}
   n=min(map(len,aa.values()));n-=n%2
   if not n:continue
   for li in aa:
    sel=rng.choice(len(aa[li]),n,replace=False);local[li].extend(aa[li][i] for i in sel)
    mixed.extend(aa[li][i] for i in sel[:n//2])
  for v in ('local','foreign','mixed'):
   p=np.zeros(len(te));tot=np.zeros(len(te))
   for li in ('1','14'):
    m=np.array([r['league']==li for r in te]);a=mixed if v=='mixed' else local[li if v=='local' else ('14' if li=='1' else '1')]
    x,_,u=fit(a,[r for r in te if r['league']==li],'shared');p[m]=u;tot[m]=x
   rec['equal_size'].setdefault(v,[]).append({'U':float(p.sum()),'NLL':score(te,(tot,None,p)),'train_per_model':len(mixed)})
 out['years'][str(y)]=rec
 print('YEAR',y,'NLL_CHOICE',pick,'MODELS',{k:(v['all']['U'],v['all']['ROI'],v['all']['NLL'],v['outside']['U']) for k,v in rec['models'].items()},'EQUAL',{k:(round(float(np.mean([a['U'] for a in v])),3),round(float(np.min([a['U'] for a in v])),3),round(float(np.max([a['U'] for a in v])),3),v[0]['train_per_model']) for k,v in rec['equal_size'].items()},flush=True)
assert [out['years'][str(y)]['models']['shared']['all']['U'] for y in (2024,2025,2026)]==[19.115,9.89,31.555]
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_efficiency_league_training_20261115.json').write_text(json.dumps(out,indent=2))
print('FOUNDATION',out['foundation'],flush=True)
