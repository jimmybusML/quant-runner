import json,datetime,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_league_residual_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
A0=np.concatenate([A[oldmask],NA]);C0=(A0+p)/2;ar=AR[rmask];cr=(ar+rp)/2
# Pure research descriptions; no candidate selection, no trading gates.
def values(q,mu,market):
 w,l=g['ou_wl'](mu,vec(q,'ol'));mw,ml=g['ou_wl'](market,vec(q,'ol'))
 oo,ou=vec(q,'oo'),vec(q,'ou')
 eo=w*(oo-1)-l;eu=l*(ou-1)-w;side=eo>=eu
 assert np.array_equal(side,g['make_pred'](q,mu)[1])
 me=np.where(side,mw*(oo-1)-ml,ml*(ou-1)-mw);ev=np.where(side,eo,eu)
 pnl=np.where(side,vec(q,'over_U'),vec(q,'under_U'))
 price=np.where(side,oo,ou)
 return ev,me,ev-me,pnl,price,side
def metrics(q,v,mask):
 if not mask.any():return {'n':0}
 ev,me,edge,pnl,price,side=v
 a=g['stat'](pnl[mask]);a.update(expected_roi=round(float(ev[mask].mean()*100),3),market_cost=round(float(-me[mask].mean()*100),3),estimated_edge=round(float(edge[mask].mean()*100),3),mean_price=round(float(price[mask].mean()),4))
 d=collections.defaultdict(float);n=collections.Counter()
 for r,u,b in zip(q,pnl,mask):
  if b:
   d[r['date']]+=float(u);n[datetime.date.fromisoformat(r['date']).strftime('%G-W%V')]+=1
 c=peak=dd=0.
 for _,u in sorted(d.items()):c+=u;peak=max(peak,c);dd=max(dd,peak-c)
 a.update(daily_mdd=round(dd,3),active_weeks=len(n),per_active_week=round(int(mask.sum())/len(n),3),weekly_counts=dict(sorted(n.items())))
 return a
def bybins(q,v,x,edges,labels):
 return {label:metrics(q,v,(x>=a)&(x<b)) for a,b,label in zip(edges[:-1],edges[1:],labels)}
def suite(q,mu,market):
 v=values(q,mu,market);ev,me,edge,pnl,price,side=v
 base=np.ones(len(q),bool)
 bins=bybins(q,v,ev,[-np.inf,0,.02,.05,.10,np.inf],['negative','0_2','2_5','5_10','10_plus'])
 costs=bybins(q,v,-me,[-np.inf,.025,.035,.045,np.inf],['under_2.5','2.5_3.5','3.5_4.5','4.5_plus'])
 edges=bybins(q,v,edge,[-np.inf,.02,.04,.06,.10,np.inf],['under_2','2_4','4_6','6_10','10_plus'])
 for a in (bins,costs,edges):assert sum(x['n'] for x in a.values())==len(q)
 years={}
 for yr in sorted({r['year'] for r in q}):
  year=np.array([r['year']==yr for r in q]);years[str(yr)]={'all':metrics(q,v,year),'nonnegative':metrics(q,v,year&(ev>=0)),'negative':metrics(q,v,year&(ev<0)),'bands':{label:metrics(q,v,year&(ev>=a)&(ev<b)) for a,b,label in zip([-np.inf,0,.02,.05,.10],[0,.02,.05,.10,np.inf],['negative','0_2','2_5','5_10','10_plus'])}}
 league={}
 for l in sorted({r['league'] for r in q}):
  k=np.array([r['league']==l for r in q]);league[l]={s:metrics(q,v,k&mask) for s,mask in [('all',base),('negative',ev<0),('nonnegative',ev>=0)]}
 return {'all':metrics(q,v,base),'ev_bands':bins,'cost_bands':costs,'edge_bands':edges,'year':years,'league':league,'over':metrics(q,v,side),'under':metrics(q,v,~side),'nonnegative':metrics(q,v,ev>=0)}
out={'method':'R19 fixed A/B/C prediction directions, historical 4059 and real pregame receipt replay 240, all outside original eight. Descriptive EV intervals 0/2/5/10 percentage points, price-cost bands and estimated relative advantage bands. All bands retained; no proposed rule implemented. Nonnegative is a diagnostic split not a gate. Historical/receipt overlap possible, no summing. Expected edge is model estimate, not proven edge.','models':{}}
for name,h,r in [('A',A0,ar),('B',p,rp),('C',C0,cr)]:
 a=suite(t,h,m);b=suite(rt,r,rm);out['models'][name]={'history':a,'receipt':b}
 def small(d):return {k:[x.get(j) for j in ('n','U','ROI','expected_roi','market_cost','daily_mdd')] for k,x in d.items()}
 print(name,'history bands',small(a['ev_bands']),'receipt bands',small(b['ev_bands']),flush=True)
 print(name,'historical cost',small(a['cost_bands']),'edge',small(a['edge_bands']),flush=True)
 print(name,'year nonnegative',small({k:x['nonnegative'] for k,x in a['year'].items()}),'negative',small({k:x['negative'] for k,x in a['year'].items()}),'receipt nonnegative',small({'v':b['nonnegative']}),flush=True)
 print(name,'leagues nonnegative',small({k:x['nonnegative'] for k,x in a['league'].items()}),flush=True)
assert out['models']['B']['history']['all']['U']==4.465 and out['models']['B']['receipt']['all']['U']==-8.745
assert out['models']['A']['history']['all']['U']==-76.005 and out['models']['C']['history']['all']['U']==-59.315
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());d=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':d(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(d(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(d(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_value_volume_research_20261116.json').write_text(json.dumps(out,indent=2))
