import json
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_target_coverage_expansion_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
oldmask=np.array([r['fid'] not in ids for r in zz])
t=[r for r,b in zip(zz,oldmask) if b]+new
p=np.concatenate([B[oldmask],NB])
assert len(t)==4059 and len({r['fid'] for r in t})==4059
pnl=g['make_pred'](t,p)[2]
out={'method':'Descriptive league/year diagnostics on B fixed candidate, 4059 outside original eight. No exclusions or trading-rule changes. Distinct historical target cohort excluding previously verified receipt archive only for the new 1731.','leagues':{}}
for l in sorted(leagues):
 mask=np.array([r['league']==l for r in t])
 a={'all':g['stat'](pnl[mask]),'years':{str(y):g['stat'](pnl[mask&np.array([r['year']==y for r in t])]) for y in (2024,2025,2026)}}
 out['leagues'][l]=a
 print(l,a,flush=True)
print('all',g['stat'](pnl),flush=True)
(P/'m8_tc_expanded_league_audit_20261116.json').write_text(json.dumps(out,indent=2))
