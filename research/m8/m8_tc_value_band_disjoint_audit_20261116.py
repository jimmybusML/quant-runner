import json,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_value_volume_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
v=values(t,p,m);r=values(rt,rp,rm);e=(v[0]>=.05)&(v[0]<.10);er=(r[0]>=.05)&(r[0]<.10);ind=np.array([x['fid'] not in receiptids for x in t])
out={'method':'Post-discovery diagnostic of B EV 5–10% historical band. Remove all 1393 archived receipt fixture IDs; descriptive only, not prospective validation or a gate. Weekly counts over 45 recorded calendar weeks in 2026.', 'history_all':metrics(t,v,e),'history_disjoint':metrics(t,v,e&ind),'receipt':metrics(rt,r,er),'overlap_all_receipt':int((e&~ind).sum()),'year':{},'league':{}}
for y0 in (2024,2025,2026):
 k=np.array([x['year']==y0 for x in t]);out['year'][str(y0)]={'all':metrics(t,v,e&k),'disjoint':metrics(t,v,e&k&ind)}
for l0 in sorted(leagues):
 k=np.array([x['league']==l0 for x in t]);out['league'][l0]=metrics(t,v,e&k)
for k in ('history_all','history_disjoint','receipt','overlap_all_receipt'):
 a=out[k];print(k,{j:a[j] for j in a if j!='weekly_counts'} if isinstance(a,dict) else a,flush=True)
print('years',[(y0,{k:(a['n'],a.get('U'),a.get('ROI')) for k,a in b.items()}) for y0,b in out['year'].items()],flush=True)
print('leagues',[(l0,a['n'],a.get('U'),a.get('ROI')) for l0,a in out['league'].items()],flush=True)
(P/'m8_tc_value_band_disjoint_audit_20261116.json').write_text(json.dumps(out,indent=2))
