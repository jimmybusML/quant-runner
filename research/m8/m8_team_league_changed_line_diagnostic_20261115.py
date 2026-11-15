from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Reuse exactly the same as-of history and estimator, do not re-select features based on annual performance.
s=(P/'m8_team_league_market_residual_20261115.py').read_text().split("out={'source':")[0]
exec(s)
results={}
def add(m):
 return {'n':m[0],'U':round(m[1],3),'ROI':round(100*m[1]/m[0],3) if m[0] else None}
for y in (2024,2025,2026):
 tr=[r for r in remaining if r['year']<y];te=[r for r in remaining if r['year']==y]
 a,p,e=fit(tr,te,'team_league_history');b,bp,be=fit(tr,te,'price_score')
 results[str(y)]={}
 for typ in ('never_changed','one_way','oscillating','reverted','net_changed'):
  def yes(r):return r['path_shape'] in ('one_way','oscillating') if typ=='net_changed' else r['path_shape']==typ
  mask=np.array([yes(r) for r in te])
  z=[r for r in te if yes(r)]
  vals=p[mask];vals0=bp[mask]
  rec={'team_league':metrics(vals),'market_strength':metrics(vals0)}
  if typ=='net_changed':
   t=[r for r in tr if yes(r)]
   for kind in ('price_score','team_league_history'):
    q,profit,est=fit(t,z,kind);rec['subpopulation_train_'+kind]=q
   for k,flag in [('H1',True),('H2',False)]:
    mask2=np.array([(r['month']<=f'{y}-06')==flag for r in z])
    rec[k]=metrics(vals[mask2])
  results[str(y)][typ]=rec
 print('ALL_PATHS',y,results[str(y)],flush=True)
(P/'m8_team_league_changed_line_diagnostic_20261115.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
