import json,datetime,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_value_volume_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
v=values(t,p,m);r=values(rt,rp,rm)
band=(v[0]>=.05)&(v[0]<.10);rb=(r[0]>=.05)&(r[0]<.10)
assert band.sum()==578 and rb.sum()==32
assert abs(v[3][band].sum()-21.635)<1e-8
ind=np.array([a['fid'] not in receiptids for a in t])
ly=np.array([a['league'] for a in t]);years=np.array([a['year'] for a in t])
# R16 descriptive positive leagues already saved before R19. Test complements, not new rules.
prior_positive={'1','12','25','73'}
def static(q):return np.array([a['league'] in prior_positive for a in q])
def annual(q,rule):
 result=np.zeros(len(q),bool);log={}
 for y0 in sorted({a['year'] for a in q}):
  if y0<2025:continue
  pool=ind&~band&((years==y0-1) if rule=='previous_year' else (years<y0))
  eligible=[]
  for league in sorted(set(ly)):
   k=pool&(ly==league)
   if not k.any():continue
   st=g['stat'](v[3][k])
   if st['U']>0:eligible.append(league)
   log.setdefault(str(y0),{})[league]=st
  for i,a in enumerate(q):
   if a['year']==y0 and a['league'] in eligible:result[i]=True
 return result,log
def describe(q,val,b,chosen):
 extra=chosen&~b
 assert not (b&extra).any()
 ret={'band':metrics(q,val,b),'extra':metrics(q,val,extra),'combined':metrics(q,val,b|extra),'extra_by_year':{},'extra_by_league':{},'combined_by_year':{},'extra_disjoint':{}}
 for y0 in sorted({a['year'] for a in q}):
  ym=np.array([a['year']==y0 for a in q]);ret['extra_by_year'][str(y0)]=metrics(q,val,extra&ym);ret['combined_by_year'][str(y0)]=metrics(q,val,(b|extra)&ym)
  if q is t:
   ret['extra_disjoint'][str(y0)]=metrics(q,val,extra&ym&ind)
 for l0 in sorted({a['league'] for a in q}):
  ret['extra_by_league'][l0]=metrics(q,val,extra&np.array([a['league']==l0 for a in q]))
 return ret
out={'method':'R20 fixed B predictions and preserved R19 band. Nonoverlapping complementary league research only: R16 previously observed four positive leagues (retrospective diagnostic); previous-calendar-year and cumulative earlier-year positive net returns only on non-band fixtures, excluding all archived receipt IDs from selection. Research selection alternatives not production rules. Preserve every result. Historical and receipt sets reported separately; same model/targets, no new independent data. 2024 cannot do chronological selection for R16 cohort.', 'models':{}}
for name in ('static_R16','previous_year','all_prior_years'):
 if name=='static_R16':h=static(t);rr0=static(rt);log={}
 else:
  h,log=annual(t,name);rr0,log2=annual(rt,name)
  assert log['2026']==log2['2026']
 a=describe(t,v,band,h);b=describe(rt,r,rb,rr0)
 out['models'][name]={'history':a,'receipt':b,'selection_diagnostic':log}
 slim=lambda k:{j:k.get(j) for j in ('n','U','ROI','daily_mdd','active_weeks')}
 print(name,'H', {k:slim(a[k]) for k in ('extra','combined')},'years', {k:slim(z) for k,z in a['extra_by_year'].items()},'disjoint', {k:slim(z) for k,z in a['extra_disjoint'].items()},'receipt',{k:slim(b[k]) for k in ('extra','combined')},flush=True)
 print(name,'combined years',{k:slim(z) for k,z in a['combined_by_year'].items()},'leagues',{k:slim(z) for k,z in a['extra_by_league'].items()},flush=True)
 print(name,'select',{yr:[l for l,z in a0.items() if z['U']>0] for yr,a0 in log.items()},flush=True)
# Explicit calendar window comparison, not future weekly volume.
base26=[a for a in load('m8_foundation_20261115/historical_membership.jsonl') if a['year']==2026]
baseu=sum(a['pnl'] for a in base26)
for name,val in out['models'].items():
 row=val['history']['combined_by_year']['2026'];extra=val['history']['extra_by_year']['2026']
 n=row['n'];u=row['U']
 val['historical_2026_volume']={'extra_beyond_band_weekly':round(extra['n']/45,3),'all_new_weekly':round(n/45,3),'base_plus_all_weekly':round((len(base26)+n)/45,3),'base_plus_all_U':round(baseu+u,3),'base_plus_all_ROI':round(100*(baseu+u)/(len(base26)+n),3)}
 print(name,'volume',val['historical_2026_volume'],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());d=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':d(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(d(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(d(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_complementary_league_research_20261116.json').write_text(json.dumps(out,indent=2))
