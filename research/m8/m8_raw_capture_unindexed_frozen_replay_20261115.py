import json,collections,datetime,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
known={r['fid'] for f in ('m8_late_full_path_water_features_20261114.jsonl','m8_extra_inventory_frozen_eight_20261115.jsonl') for r in map(json.loads,(R/f).open())}
sources={k:(v[0],v[1],Path(v[2]),v[3],v[4]) for k,v in json.load((R/'m8_raw_capture_unindexed_sources_20261115.json').open()).items()}
inventory_counts={'raw_capture_new':len(sources)}
# Reuse previous exact feature-extraction logic; source year gating only removed for extra cohort.
base=(R/'m8_late_6to1_dynamic_path_recovery_20261114.py').read_text().split('def stat(a,key):')[0]
a=base.index('def inputs():');b=base.index('def dt(s):',a)
base=base[:a]+"def inputs():\n yield from sources.values()\n"+base[b:]
# All inputs are distinct unknown IDs; use their actual kickoff year as before.
full=(R/'m8_late_full_path_water_features_20261114.py').read_text().split("add = '''",1)[1].split("'''",1)[0]
same=(R/'m8_same_line_probability_path_20261114.py').read_text().split("add = '''",1)[1].split("'''",1)[0]
same=same.replace('  if steps:continue\n','')
same='\n  if not steps:\n'+'\n'.join(' '+l for l in same.splitlines() if l.strip())+'\n'
extra="""
  r['score_row']={'fid':fid,'year':ko.year,'month':ko.strftime('%Y-%m'),'date':ko.date().isoformat(),'ko':ko.isoformat(),'league':lid,'home':str(x.get('h_id') or ''),'away':str(x.get('a_id') or ''),'hg':h,'ag':a}
  r['source_file']=str(p)
"""
base=base.replace('  rows.append(r)',full+same+extra+'  rows.append(r)')
base=base.replace("if not (2019<=ko.year<=2026) or (source=='2026' and ko.year!=2026) or (source=='old' and ko.year>=2026):continue","if not (2019<=ko.year<=2026) or (source=='2026' and ko.year!=2026) or (source=='old' and ko.year>=2026):C['outside_year']+=1;continue")
base=base.replace("if (C['input_old']+C['input_2026'])%10000==0:","if C['input_extra']%10000==0:")
exec(compile(base,'previous_path_extraction','exec'))
print('NEW_VALID',len(rows),dict(C),dict(collections.Counter(r['year'] for r in rows)),flush=True)
assert len({r['fid'] for r in rows})==len(rows) and not ({r['fid'] for r in rows}&known)
# For G reproduce original score-only rates from earlier original score history, not new sample outcomes.
import math
import numpy as np
scorelist=list(map(json.loads,(R/'m8_independent_score_strength_20261114.jsonl').open()))
scoremap={r['fid']:r for r in scorelist}
attack=collections.defaultdict(float);defense=collections.defaultdict(float);baseline=collections.defaultdict(lambda:[math.log(1.45),math.log(1.15)])
def predict(r):
 h=(r['league'],r['home']);a=(r['league'],r['away']);b=baseline[r['league']]
 return float(np.exp(np.clip(b[0]+attack[h]+defense[a],-2.5,2.3))),float(np.exp(np.clip(b[1]+attack[a]+defense[h],-2.5,2.3)))
def update(r):
 h=(r['league'],r['home']);a=(r['league'],r['away']);b=baseline[r['league']];x,y=predict(r);e1=r['hg']-x;e2=r['ag']-y
 for k,e in [(h,e1),(a,e2)]:attack[k]=.997*attack[k]+.025*float(np.clip(e,-4,4))
 for k,e in [(a,e1),(h,e2)]:defense[k]=.997*defense[k]+.025*float(np.clip(e,-4,4))
 b[0]+=.003*float(np.clip(e1,-4,4));b[1]+=.003*float(np.clip(e2,-4,4))
q=0
for r in sorted(rows,key=lambda r:(r['date'],r['fid'])):
 z=r['score_row'];day=datetime.date.fromisoformat(z['date'])
 while q<len(scorelist) and (day-datetime.date.fromisoformat(scorelist[q]['date'])).days>=2:
  update(scorelist[q]);q+=1
 if z['home'] and z['away']:
  h,a=predict(z)
  if z['fid'] in scoremap:
   sc=scoremap[z['fid']]
   # compare exact frozen rates where available
   h,a=sc['lambda_home_0.025'],sc['lambda_away_0.025']
  r['score_rates']=[h,a]
# same quarter-handicap expected return from the prior study (for G only)
K=40
def pmf(lam):
 a=[math.exp(-lam)]
 for j in range(1,K):a.append(a[-1]*lam/j)
 return a
def expect(r):
 h,a=map(pmf,r['score_rates']);line=r['end_line'];wh=wl=0
 for cut in (math.floor(line*2+1e-8)/2,math.ceil(line*2-1e-8)/2):
  for i,p in enumerate(h):
   for j,q in enumerate(a):
    v=i-j+cut
    if v>0:wh+=p*q/2
    elif v<0:wl+=p*q/2
 return wh*(r['home_price']-1)-wl,wl*(r['away_price']-1)-wh
def sg(v):return 1 if v>1e-9 else -1 if v<-1e-9 else 0
selected=[]
for r in rows:
 g=side=None
 if r['base']:g='base';side='home' if r['end_line']>0 else 'away'
 elif r.get('path_6_3_1')=='deepen_weaken':g='A';side='home' if r['end_line']>0 else 'away'
 elif r.get('path_6_3_1')=='weaken_same':g='B';side='home' if r['end_line']>0 else 'away'
 elif not r['end_zero'] and r['path_shape']=='oscillating':g='C';side='away' if r['end_line']>0 else 'home'
 elif r['end_zero'] and r['path_shape']=='reverted' and r['home_price_vs_timeavg'] is not None and r['home_price_vs_timeavg']-r['away_price_vs_timeavg']<-1e-9:g='D';side='away'
 elif r['end_zero'] and r['path_shape']=='never_changed':
  a,b=sg(r['p3']-r['p0']),sg(r['p1']-r['p3']);net=sg(r['p1']-r['p0']);s=net or a or b or sg(r['last_move'])
  if s and r['n_price_moves']:
   if r['up_moves'] and r['down_moves'] and not net:g='E';side='away' if s>0 else 'home'
   elif (not r['up_moves'] or not r['down_moves']) and a==0 and b*s==1:g='F';side='home' if s>0 else 'away'
 if g is None and r['path_shape']=='reverted' and 'score_rates' in r:
  market=sg(r['away_price']/(r['home_price']+r['away_price'])-r['start_away_price']/(r['start_home_price']+r['start_away_price']))
  eh,ea=expect(r);model=sg(eh-ea) or 1
  if market and market==model:g='G';side='away' if model>0 else 'home'
 if g:r['cohort']=g;r['side']=side;r['pnl']=r['end_'+side+'_U'];selected.append(r)
def stat(z):
 n=len(z);u=sum(r['pnl'] for r in z)
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
out={'inventory_counts':inventory_counts,'new_source_candidates':len(sources),'new_valid':len(rows),'quality':dict(C),'new_by_year':dict(collections.Counter(r['year'] for r in rows)),'selected_all':stat(selected),'groups':{},'selected_by_year':{},'selected_2026':stat([r for r in selected if r['year']==2026]),'G_score_unavailable':sum(r['path_shape']=='reverted' and 'score_rates' not in r for r in rows)}
for g in ['base','A','B','C','D','E','F','G']:
 z=[r for r in selected if r['cohort']==g];out['groups'][g]={'all':stat(z),'2026':stat([r for r in z if r['year']==2026])}
for y in sorted({r['year'] for r in rows}):out['selected_by_year'][str(y)]=stat([r for r in selected if r['year']==y])
n=out['selected_2026']['n'];u=out['selected_2026']['U'];out['combined_2026_research']={'n':2218+n,'U':round(99.82+u,3),'ROI':round(100*(99.82+u)/(2218+n),3)}
print('RESULT',json.dumps(out,ensure_ascii=False),flush=True)
(R/'m8_raw_capture_unindexed_frozen_replay_20261115.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
(R/'m8_raw_capture_unindexed_frozen_replay_20261115.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
