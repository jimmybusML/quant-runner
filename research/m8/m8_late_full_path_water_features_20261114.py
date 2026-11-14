# Build full-path features on exactly the previously audited fixture universe.
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_late_6to1_dynamic_path_recovery_20261114.py').read_text().split('def stat(a,key):')[0]
add = '''
  # Time-weighted quotes, within T-6 through T-1 only. At T-1 all features known.
  seq=[start]+seen
  duration=collections.defaultdict(float); odds_sums=collections.defaultdict(lambda:[0.,0.])
  for n,q in enumerate(seq):
   lo=max(t6,q[0]);hi=seq[n+1][0] if n+1<len(seq) else t1
   length=max(0.,(hi-lo).total_seconds())
   duration[q[1]]+=length
   odds_sums[q[1]][0]+=length*q[2];odds_sums[q[1]][1]+=length*q[3]
  r['home_price']=end[2];r['away_price']=end[3]
  r['start_home_price']=start[2];r['start_away_price']=start[3]
  r['final_line_minutes']=duration[end[1]]/60
  r['line_range']=max(q[1] for q in seq)-min(q[1] for q in seq)
  r['path_shape']='never_changed' if not steps else 'reverted' if start[1]==end[1] else 'one_way' if all((v[1]-u[1])*(end[1]-start[1])>0 for u,v in steps) else 'oscillating'
  r['late_event_age_min']=(t1-end[0]).total_seconds()/60
  r['last_line_change_age_min']=(t1-steps[-1][1][0]).total_seconds()/60 if steps else None
  if duration[end[1]]>0:
   r['home_price_vs_timeavg']=end[2]-odds_sums[end[1]][0]/duration[end[1]]
   r['away_price_vs_timeavg']=end[3]-odds_sums[end[1]][1]/duration[end[1]]
  else:
   r['home_price_vs_timeavg']=None;r['away_price_vs_timeavg']=None
  if fav:
   sign=-1 if fav=='home' else 1
   strengths=[sign*q[1] for q in seq]
   r['fav_end_vs_start']=strengths[-1]-strengths[0]
   r['fav_end_vs_max']=strengths[-1]-max(strengths)
   r['fav_end_vs_min']=strengths[-1]-min(strengths)
   r['fav_last_move']=sign*(steps[-1][1][1]-steps[-1][0][1]) if steps else 0
   r['dog_price']=end[2] if dog=='home' else end[3]
   r['dog_price_vs_timeavg']=r['home_price_vs_timeavg'] if dog=='home' else r['away_price_vs_timeavg']
   r['dog_price_change']=r['dog_price']-(start[2] if dog=='home' else start[3])
   r['fav_price_change']=(end[2]-start[2]) if fav=='home' else (end[3]-start[3])
'''
s=s.replace('  rows.append(r)',add+'  rows.append(r)')
exec(compile(s,'full_path_features','exec'))
assert len(rows)==39101,len(rows)
assert len({(r['year'],r['fid']) for r in rows})==len(rows)
(R/'m8_late_full_path_water_features_20261114.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
print('FEATURES_DONE',len(rows),dict(C),flush=True)
