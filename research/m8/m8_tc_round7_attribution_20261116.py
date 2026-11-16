import json,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_crossyear_round7_replay_20261116.py').read_text()
exec(s[:s.index('prior=calc(old,prevF)')])
sets={'before':before,'2025_only':{**before,**{r['fid']:r for r in r7 if r['year']==2025}},'2026_only':{**before,**{r['fid']:r for r in r7 if r['year']==2026}},'both':history}
pred={k:predict_annual(old,features_for(old,histindex(v))[0]) for k,v in sets.items()}
b=pred['before'];p=pred['both'];changed=b[1]!=p[1]
assert changed.sum()==33 and g['stat'](b[2])['U']==15.44 and g['stat'](p[2])['U']==1.44
out={'method':'Same 308 target fixtures and fixed model; only add prior performance history from each round-7 acquisition year, no changes to trade logic. Shapley decomposition is descriptive.','scenarios':{},'changed':{},'league':{},'direction':{}}
for k,v in pred.items():
 out['scenarios'][k]={**g['stat'](v[2]),'switches':int((b[1]!=v[1]).sum()),'line_brier':g['probstats'](old,v[0])['line_brier'],'changed_group_U':round(float(v[2][changed].sum()),3)}
u={k:v['U'] for k,v in out['scenarios'].items()}
out['attribution']={'2025_U':round((u['2025_only']-u['before']+u['both']-u['2026_only'])/2,3),'2026_U':round((u['2026_only']-u['before']+u['both']-u['2025_only'])/2,3)}
def stats(mask):
 return {'n':int(mask.sum()),'before_U':round(float(b[2][mask].sum()),3),'after_U':round(float(p[2][mask].sum()),3),'delta_U':round(float((p[2]-b[2])[mask].sum()),3)}
out['changed']=stats(changed);out['unchanged']=stats(~changed)
for l in sorted({r['league'] for r in old}):
 out['league'][l]=stats(changed&np.array([r['league']==l for r in old]))
for name,mask in [('over_to_under',changed&b[1]),('under_to_over',changed&~b[1])]:out['direction'][name]=stats(mask)
(P/'m8_tc_round7_attribution_20261116.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,ensure_ascii=False),flush=True)
