from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_late_6to1_dynamic_path_recovery_20261114.py').read_text().split('def stat(a,key):')[0]
add = '''
  if steps:continue
  # All within-window odds, on one identical handicap. Margin-normalized implied price share, not an outcome probability.
  seq=[start]+seen
  vals=[(q[0],q[3]/(q[2]+q[3]),q[2],q[3]) for q in seq]
  p0=vals[0][1];p1=vals[-1][1]
  t3=ko-datetime.timedelta(hours=3)
  p3=next(q[1] for q in reversed(vals) if q[0]<=t3)
  w=[];z=[]
  for k,q in enumerate(vals):
   lo=max(q[0],t6);hi=vals[k+1][0] if k+1<len(vals) else t1
   dur=max(0.,(hi-lo).total_seconds())
   w.append(dur);z.append(q[1])
  mean=sum(a*b for a,b in zip(w,z))/18000
  var=sum(a*(b-mean)**2 for a,b in zip(w,z))/18000
  moves=[b[1]-a[1] for a,b in zip(vals,vals[1:]) if abs(b[1]-a[1])>1e-10]
  r.update({'p0':p0,'p3':p3,'p1':p1,'pmean':mean,'pmin':min(z),'pmax':max(z),'pstd':var**.5,'n_price_moves':len(moves),'up_moves':sum(v>0 for v in moves),'down_moves':sum(v<0 for v in moves),'variation':sum(abs(v) for v in moves),'last_move':moves[-1] if moves else 0.,'home_price':end[2],'away_price':end[3],'home_team':str(x.get('h_id') or ''),'away_team':str(x.get('a_id') or ''),'kickoff_utc':ko.isoformat()})
'''
s=s.replace('  rows.append(r)',add+'  rows.append(r)')
exec(compile(s,'same_line_features','exec'))
assert len({(r['year'],r['fid']) for r in rows})==len(rows)
assert sum(r['year']==2026 and not r['end_zero'] for r in rows)==4917
(R/'m8_same_line_probability_path_20261114.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
print('DONE',len(rows),dict(collections.Counter((r['year'],r['end_zero']) for r in rows)),flush=True)
