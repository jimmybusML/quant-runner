import json,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_crossyear_round8_replay_20261116.py').read_text()
exec(s[:s.index('prior=calc(old,prevF)')])
fix=old
assert len(fix)==308
base={**orig,**{r['fid']:r for r in bridge}}
stages=[r1,r2,r3,r4,r5,r6,r7,r8]
vintages=[];pred=[];counts=[];effective=[];gap=[]
for j,batch in enumerate(stages,1):
 base.update({r['fid']:r for r in batch})
 ii=histindex(base);ff={};nn=[];ee=[]
 for r in fix:
  v,n,e,_=feature(r,ii);ff[r['fid']]=v;nn.append(min(n));ee.append(min(e))
 assert min(nn)>0
 p=predict_annual(fix,ff);pred.append(p)
 counts.append(nn);effective.append(ee)
 w,l=g['ou_wl'](p[0],vec(fix,'ol'))
 ev_over=w*(vec(fix,'oo')-1)-l;ev_under=l*(vec(fix,'ou')-1)-w
 gap.append(abs(ev_over-ev_under))
 vintages.append({'round':j,'history_n':len(base),**g['stat'](p[2]),'median_min_history_n':float(np.median(nn)),'median_min_effective':round(float(np.median(ee)),4),'line_brier':g['probstats'](fix,p[0])['line_brier'],'switch_vs_first':int((p[1]!=pred[0][1]).sum()),'switch_vs_prior':int((p[1]!=pred[-2][1]).sum()) if len(pred)>1 else 0})
assert vintages[0]['U']==19.755 and vintages[-1]['U']==-5.46
sides=np.stack([p[1] for p in pred]);freq=np.sum(sides[1:]!=sides[:-1],axis=0);tot=np.stack([p[0] for p in pred]);last=pred[-1];first=pred[0]
def grp(mask):
 return {'n':int(mask.sum()),'first':g['stat'](first[2][mask]),'last':g['stat'](last[2][mask]),'median_first_EV_gap':round(float(np.median(gap[0][mask])),6) if mask.any() else None,'median_forecast_range_goals':round(float(np.median((tot.max(0)-tot.min(0))[mask])),6) if mask.any() else None}
out={'method':'Fixed 308 receipts, identical model/parameters, chronological archive versions R1–R8; no new selection or adjustment. Groupings describe observed sensitivity only, not prospective filters.','vintages':vintages,'ever_stable':grp(freq==0),'ever_changed':grp(freq>0),'one_switch':grp(freq==1),'multiple_switch':grp(freq>1),'final_vs_first_changed':grp(first[1]!=last[1]),'switch_events':int(freq.sum()),'forecast_range_median':round(float(np.median(tot.max(0)-tot.min(0))),6),'market':g['stat'](g['make_pred'](fix,vec(fix,'mh')+vec(fix,'ma'))[2])}
(P/'m8_tc_history_vintage_sensitivity_20261116.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,ensure_ascii=False),flush=True)
