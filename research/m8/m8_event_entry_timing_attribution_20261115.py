import json,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
data=[json.loads(l) for l in (P/'m8_event_driven_late_quote_replay_20261115.jsonl').open()]
old={r['fid']:r for r in map(json.loads,(P/'m8_late_full_path_water_features_20261114.jsonl').open()) if r['year']==2026}
old.update({r['fid']:r for r in map(json.loads,(P/'m8_extra_inventory_frozen_eight_20261115.jsonl').open()) if r['year']==2026})
control=[r for r in data if r['population']=='control_2026']
assert len(control)==len(old)==9242
def st(v):
 n=len(v);u=sum(v);return {'n':n,'U':round(u,3),'ROI':round(u*100/n,3) if n else None}
def comp(z,ev):
 a=[r for r in z if ev in r['events']]
 e=[r['events'][ev]['U'] for r in a]
 t=[old[r['fid']]['end_'+r['events'][ev]['side']+'_U'] for r in a]
 return {'event_entry':st(e),'same_side_T1':st(t),'T1_minus_event_U':round(sum(t)-sum(e),3)}
out={}
for ev in ('first_anchor_deepen_dog','first_change_reverse','first_return_reverse_excursion','first_change_fav'):
 out[ev]={'all':comp(control,ev),'T1_base_members_retrospective':comp([r for r in control if 'T1_net_deepen_dog' in r['events']],ev),'not_T1_base_members_retrospective':comp([r for r in control if 'T1_net_deepen_dog' not in r['events']],ev),'H1':comp([r for r in control if r['month']<='2026-06'],ev),'H2':comp([r for r in control if r['month']>='2026-07'],ev)}
 print(ev,out[ev],flush=True)
(P/'m8_event_entry_timing_attribution_20261115.json').write_text(json.dumps(out,indent=2))
