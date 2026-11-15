import json,collections,statistics,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_score_market_divergence_full_AH_20261114.py').read_text().split('out={}\n')[0])
old=[{**r,'pnl':prior[(r['year'],r['fid'])][1],'cohort':prior[(r['year'],r['fid'])][0],'sample':'old'} for r in A if (r['year'],r['fid']) in prior]
old.extend({**r,'pnl':r['contra_U'],'cohort':'G','sample':'old'} for r in G[('shape_relation','reverted','agree')])
extra=[{**r,'sample':'new'} for r in map(json.loads,(P/'m8_extra_inventory_frozen_eight_20261115.jsonl').open()) if r.get('cohort')]
assert len(old)==8956 and len(extra)==1337
def stat(z):
 n=len(z);u=sum(r['pnl'] for r in z)
 if not n:return {'n':0,'U':0,'ROI':None}
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3)}
def price(r):
 if r['sample']=='new':sd=r['side']
 elif r['cohort']=='B':sd='home' if r['end_line']>0 else 'away'
 else:sd='away' if r['away_price']/(r['home_price']+r['away_price'])>r['start_away_price']/(r['start_home_price']+r['start_away_price']) else 'home'
 return r[sd+'_price']
def pay(z):
 s=stat(z)
 if not z:return s
 w=[r['pnl']/(price(r)-1) if r['pnl']>0 else 0 for r in z]
 l=[-min(r['pnl'],0) for r in z]
 assert all(-1e-7<=x<=1.000001 for x in w+l)
 return s|{'mean_price':round(statistics.mean(price(r) for r in z),4),'won_stake_pct':round(100*statistics.mean(w),3),'lost_stake_pct':round(100*statistics.mean(l),3),'reference_1_95_ROI':round(100*(.95*sum(w)-sum(l))/len(z),3)}
def era(r):return '2019-23' if r['year']<=2023 else '2024-25' if r['year']<=2025 else '2026'
out={}
for g in ('B','G'):
 a=[r for r in old if r['cohort']==g];b=[r for r in extra if r['cohort']==g];z=a+b
 r={'old':pay(a),'new':pay(b),'all':pay(z),'year':{},'league':{},'mix':{},'by_handicap':{}}
 for y in range(2019,2027):
  r['year'][str(y)]={k:pay([x for x in v if x['year']==y]) for k,v in [('old',a),('new',b),('all',z)]}
 for lid in sorted({x['league'] for x in z}):
  r['league'][lid]={k:pay([x for x in v if x['league']==lid]) for k,v in [('old',a),('new',b),('all',z)]}
 for val in sorted({abs(x['end_line']) for x in z}):
  r['by_handicap'][str(val)]={k:pay([x for x in v if abs(x['end_line'])==val]) for k,v in [('old',a),('new',b),('all',z)]}
 # Stratification by both league and calendar year; symmetric decomposition of ROI change in shared cells
 def strat(key):
  ag=collections.defaultdict(list);bg=collections.defaultdict(list)
  for x in a:ag[key(x)].append(x)
  for x in b:bg[key(x)].append(x)
  keys=set(ag)&set(bg);aa=sum(len(ag[k]) for k in keys);bb=sum(len(bg[k]) for k in keys)
  v0=v1=mix=within=0.
  for k in keys:
   p=len(ag[k])/aa;q=len(bg[k])/bb;u=sum(x['pnl'] for x in ag[k])/len(ag[k]);v=sum(x['pnl'] for x in bg[k])/len(bg[k])
   v0+=p*u;v1+=q*v;mix+=(q-p)*(v+u)/2;within+=(q+p)*(v-u)/2
  return {'shared_cells':len(keys),'old_n':aa,'new_n':bb,'old_roi':round(100*v0,3),'new_roi':round(100*v1,3),'mix_pp':round(100*mix,3),'within_pp':round(100*within,3)}
 r['mix']['league']=strat(lambda x:x['league']);r['mix']['league_year']=strat(lambda x:(x['league'],x['year']))
 r['eras']={e:{k:pay([x for x in v if era(x)==e]) for k,v in [('old',a),('new',b),('all',z)]} for e in ('2019-23','2024-25','2026')}
 out[g]=r
 print('COHORT',g,r['old'],r['new'],r['all'],'ERAS',r['eras'],'MIX',r['mix'],flush=True)
 print('NEW_WORST',g,sorted([(k,v['new']) for k,v in r['league'].items() if v['new']['n']],key=lambda x:x[1]['U'])[:6],flush=True)
 print('NEW_BEST',g,sorted([(k,v['new']) for k,v in r['league'].items() if v['new']['n']],key=lambda x:-x[1]['U'])[:6],flush=True)
print('DONE')
(P/'m8_BG_expanded_attribution_20261115.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
