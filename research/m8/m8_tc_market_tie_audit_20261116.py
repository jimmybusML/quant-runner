import json
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_crossyear_round10_replay_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
z,H=historical([r for r in history.values() if r['fid'] in audit['target'] and r['year']>=2023],idx)
def detail(z):
 total=vec(z,'mh')+vec(z,'ma');w,l=g['ou_wl'](total,vec(z,'ol'))
 eo=w*(vec(z,'oo')-1)-l;eu=l*(vec(z,'ou')-1)-w
 gap=abs(eo-eu);p=g['make_pred'](z,total)
 return {'n':len(z),'gap_median':float(np.median(gap)),'gap_max':float(gap.max()),'gap_lt_1e-5_n':int((gap<1e-5).sum()),'choice':g['stat'](p[2]),'all_over':g['stat'](vec(z,'over_U')),'all_under':g['stat'](vec(z,'under_U')),'equal_weight_both':g['stat']((vec(z,'over_U')+vec(z,'under_U'))/2)}
out={'historical':detail(z),'receipt':detail(ex),'historical_by_year':{str(y):detail([r for r in z if r['year']==y]) for y in sorted({r['year'] for r in z})}}
(P/'m8_tc_market_tie_audit_20261116.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out),flush=True)
