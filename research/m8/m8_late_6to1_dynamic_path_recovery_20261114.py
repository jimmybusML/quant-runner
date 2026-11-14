import json,datetime,math,hashlib,collections,statistics,bisect
from pathlib import Path
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
old=R/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
schedule=R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl'
idx={str(r['match_id']):r for r in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
def inputs():
 for r in map(json.loads,old.open()):
  if datetime.datetime.fromisoformat(r['kickoff_utc']).year<2026:yield str(r['fixture_id']),str(r['league_id']),Path(r['source_file']),None,'old'
 for r in map(json.loads,schedule.open()):
  fid=str(r['fid']);yield fid,str(r['league_id']),P/f'data/m5-crown-authorized/crown-responses/{fid}.json',idx.get(fid,{}).get('response_sha256'),'2026'
def dt(s):return datetime.datetime.fromisoformat(str(s).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def favored(line):return 'home' if line<0 else 'away' if line>0 else None
def opp(s):return 'away' if s=='home' else 'home' if s=='away' else None
def direction(a,b):return (b-a)*b>0
C=collections.Counter();rows=[]
for fid,lid,p,sha,source in inputs():
 C['input_'+source]+=1
 try:
  if not p.exists():C['missing_file']+=1;continue
  raw=p.read_bytes()
  if source=='2026' and (not sha or hashlib.sha256(raw).hexdigest()!=sha):C['bad_sha']+=1;continue
  x=next((q for q in json.loads(raw).get('data',[]) if str(q.get('id'))==fid),None)
  if x is None or str(x.get('l_id'))!=lid or x.get('status')!='full':C['invalid_fixture']+=1;continue
  ko=dt(x['start']);h,a=int(x['hg']),int(x['ag'])
  if not (2019<=ko.year<=2026) or (source=='2026' and ko.year!=2026) or (source=='old' and ko.year>=2026):continue
  b=next((q for q in x.get('bookmakers',[]) if q.get('slug')=='crown'),None)
  if b is None:C['missing_crown']+=1;continue
  path=[]
  for q in b.get('asian_list') or []:
   try:
    t=dt(q[4]);l=float(q[1]);od1=float(q[2]);od2=float(q[3])
    if t<ko and od1>1 and od2>1 and all(math.isfinite(z) for z in (l,od1,od2)) and abs(l*4-round(l*4))<1e-7:path.append((t,l,od1,od2))
   except:continue
  path.sort(key=lambda q:q[0]);times=[q[0] for q in path];t6=ko-datetime.timedelta(hours=6);t1=ko-datetime.timedelta(hours=1)
  i=bisect.bisect_right(times,t6)-1;j=bisect.bisect_right(times,t1)-1
  if i<0 or j<0:C['missing_cutoffs']+=1;continue
  start=path[i];end=path[j];seen=path[i+1:j+1];base=direction(start[1],end[1]);fav=favored(end[1]);dog=opp(fav)
  def pnl(q,side):
   return settle_score('AH',q[1],side,h,a,q[2] if side=='home' else q[3])[1]
  # anchor trigger: observable signal ever reached within the window, including transient events.
  anchor=[q for q in seen if direction(start[1],q[1])]
  # Local-step direction: earlier quote compared with next actual event; no future information.
  steps=[(u,v) for u,v in zip([start]+seen,seen) if u[1]!=v[1]]
  deepsteps=[v for u,v in steps if direction(u[1],v[1])]
  anchorside=opp(favored(anchor[-1][1])) if anchor else None
  stepside=opp(favored(deepsteps[-1][1])) if deepsteps else None
  r={'fid':fid,'year':ko.year,'month':ko.strftime('%Y-%m'),'date':ko.date().isoformat(),'league':lid,'base':base,'n_events':len(seen),'n_line_changes':len(steps),'start_line':start[1],'end_line':end[1],'had_anchor':bool(anchor),'had_step':bool(deepsteps),'end_home_U':pnl(end,'home'),'end_away_U':pnl(end,'away'),'base_U':pnl(end,dog) if base else None,'end_zero':end[1]==0}
  if anchor:
   q=anchor[0];side=opp(favored(q[1]));r['anchor_first_U']=pnl(q,side);r['anchor_first_hours']=round((ko-q[0]).total_seconds()/3600,5);r['anchor_first_side']=side
   r['anchor_last_dog_at_T1_U']=pnl(end,anchorside);r['anchor_last_fav_at_T1_U']=pnl(end,opp(anchorside));r['anchor_last_side']=anchorside;r['anchor_last_line']=anchor[-1][1];r['anchor_end_retrace']=not base
  if deepsteps:
   q=deepsteps[0];side=opp(favored(q[1]));r['step_first_U']=pnl(q,side);r['step_first_hours']=round((ko-q[0]).total_seconds()/3600,5)
   r['step_last_dog_at_T1_U']=pnl(end,stepside);r['step_last_fav_at_T1_U']=pnl(end,opp(stepside))
  # Three-step phase classification at T1 (sign relative to the final favorite).
  i3=bisect.bisect_right(times,ko-datetime.timedelta(hours=3))-1
  if i3>=0 and fav:
   mid=path[i3]
   def state(l1,l2):return 'deepen' if (l2-l1)*end[1]>0 else 'weaken' if (l2-l1)*end[1]<0 else 'same'
   r['path_6_3_1']=state(start[1],mid[1])+'_'+state(mid[1],end[1]);r['end_dog_U']=pnl(end,dog);r['end_fav_U']=pnl(end,fav)
  rows.append(r)
 except Exception as e:
  C['error_'+type(e).__name__]+=1
  if C['error_'+type(e).__name__]<=2:print('ERROR',fid,repr(e),flush=True)
 if (C['input_old']+C['input_2026'])%10000==0:print('PROGRESS',len(rows),flush=True)
def stat(a,key):
 vals=[r[key] for r in a if r.get(key) is not None];n=len(vals);net=sum(vals)
 return {'n':n,'U':round(net,3),'ROI':round(net/n*100,3) if n else None}
def compare(a,k):
 return {v:stat([r for r in a if fn(r['year'])],k) for v,fn in [('2019-2023',lambda y:y<=2023),('2024-2025',lambda y:2024<=y<=2025),('2026',lambda y:y==2026)]}
oldbase=[r for r in rows if r['base']]
b2026=[r for r in oldbase if r['year']==2026]
assert len(b2026)==1182 and abs(sum(r['base_U'] for r in b2026)-38.955)<1e-5,(len(b2026),stat(b2026,'base_U'))
others=[r for r in rows if not r['base']]
anchor=[r for r in rows if r['had_anchor']]
step=[r for r in rows if r['had_step']]
tests={
 'baseline_T1':(oldbase,'base_U'),
 'dynamic_first_anchor_all':(anchor,'anchor_first_U'),
 'dynamic_first_local_step_all':(step,'step_first_U'),
 'nonbaseline_anchor_dog_T1':([r for r in others if r['had_anchor']],'anchor_last_dog_at_T1_U'),
 'nonbaseline_anchor_fav_T1':([r for r in others if r['had_anchor']],'anchor_last_fav_at_T1_U'),
 'nonbaseline_any_step_dog_T1':([r for r in others if r['had_step']],'step_last_dog_at_T1_U'),
 'nonbaseline_any_step_fav_T1':([r for r in others if r['had_step']],'step_last_fav_at_T1_U'),
 'nonbaseline_step_no_anchor_dog_T1':([r for r in others if r['had_step'] and not r['had_anchor']],'step_last_dog_at_T1_U'),
 'nonbaseline_step_no_anchor_fav_T1':([r for r in others if r['had_step'] and not r['had_anchor']],'step_last_fav_at_T1_U'),
}
for path in sorted({r.get('path_6_3_1') for r in rows if r.get('path_6_3_1')}):
 for side in ('dog','fav'):
  tests['nonbaseline_path_'+path+'_'+side]=([r for r in others if r.get('path_6_3_1')==path],'end_'+side+'_U')
summary={'quality':dict(C),'rows':len(rows),'research_scope':'Historical Crown source events at T6 through T1 in original49, source event pricing; all extra groups evaluated at T1 (only at T1 can know base did not trigger). No new production rules. First-event policies are separate time-causal tests, not union with future baseline.','tests':{}}
for k,(a,field) in tests.items():
 rec=compare(a,field)
 rec['2026_H1']=stat([r for r in a if r['year']==2026 and r['month']<='2026-06'],field)
 rec['2026_H2']=stat([r for r in a if r['year']==2026 and r['month']>='2026-07'],field)
 rec['2026_monthly']={m:stat([r for r in a if r['month']==m],field) for m in sorted({r['month'] for r in a if r['year']==2026})}
 if k.startswith('nonbaseline'):
  z=[r for r in a if r['year']==2026 and r.get(field) is not None];v=[r['base_U'] for r in b2026]+[r[field] for r in z]
  rec['2026_combined']={'n':len(v),'U':round(sum(v),3),'ROI':round(sum(v)*100/len(v),3)}
  weeks=collections.Counter()
  for r in b2026+z:
   iso=datetime.date.fromisoformat(r['date']).isocalendar();weeks[f'{iso.year}-W{iso.week:02}']+=1
  rec['2026_combined_weekly']={'max':max(weeks.values()),'median':statistics.median(weeks.values()),'weeks':dict(sorted(weeks.items()))}
 summary['tests'][k]=rec
 print(k, {p:rec[p] for p in ('2019-2023','2024-2025','2026','2026_H1','2026_H2')},flush=True)
(R/'m8_late_6to1_dynamic_path_recovery_20261114.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(R/'m8_late_6to1_dynamic_path_recovery_20261114.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
print('DONE',len(rows),C,flush=True)
