import json
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_league_residual_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Descriptive P&L decomposition, not an optimization or new selection rule.
def attrib(q,rate,market):
 line=vec(q,'ol');oo=vec(q,'oo');ou=vec(q,'ou')
 w,l=g['ou_wl'](rate,line);mw,ml=g['ou_wl'](market,line)
 side=g['make_pred'](q,rate)[1]
 yh=vec(q,'hg')+vec(q,'ag')
 aw=np.zeros(len(q));al=np.zeros(len(q))
 for a in g['probstats'].__globals__['halves'](line):
  aw+=(yh>a)/2;al+=(yh<a)/2
 ev=np.where(side,w*(oo-1)-l,l*(ou-1)-w)
 me=np.where(side,mw*(oo-1)-ml,ml*(ou-1)-mw)
 actual=np.where(side,vec(q,'over_U'),vec(q,'under_U'))
 expected_real=np.where(side,aw*(oo-1)-al,al*(ou-1)-aw)
 assert np.allclose(actual,expected_real)
 def a(mask):
  if not mask.any():return {'n':0}
  mk=lambda v:round(float(np.mean(v[mask])*100),3)
  return {**g['stat'](actual[mask]),'market_expected_roi':mk(me),'estimated_edge_over_market':mk(ev-me),'model_expected_roi':mk(ev),'realized_minus_model_roi':mk(actual-ev),'model_win_fraction':mk(np.where(side,w,l)),'actual_win_fraction':mk(np.where(side,aw,al)),'model_loss_fraction':mk(np.where(side,l,w)),'actual_loss_fraction':mk(np.where(side,al,aw))}
 return {'all':a(np.ones(len(q),bool)),'over':a(side),'under':a(~side)}
out={'method':'Fixed B directions, actual Asian split settlement; expected return decomposition into market-implied pricing cost, estimated model advantage and estimation error. Market expected ROI uses the already selected side, no arbitrary tie-based market directions. Descriptive, no new gate.','history':{},'receipt':{}}
for label,q,a,b in [('history',t,p,m),('receipt',rt,rp,rm)]:
 for l in sorted(leagues):
  k=np.array([r['league']==l for r in q]);qq=[r for r,b0 in zip(q,k) if b0]
  item=attrib(qq,a[k],b[k]);item['under_by_year']={}
  for yr in sorted({r['year'] for r in qq}):
   j=k&np.array([r['year']==yr for r in q]);item['under_by_year'][str(yr)]=attrib([r for r,v in zip(q,j) if v],a[j],b[j])['under']
  out[label][l]=item
  if l in negative:print(label,l,'under',item['under'],'years',[(y,x.get('n'),x.get('ROI'),x.get('model_expected_roi'),x.get('realized_minus_model_roi')) for y,x in item['under_by_year'].items()],flush=True)
(P/'m8_tc_under_price_attribution_20261116.json').write_text(json.dumps(out,indent=2))
