import json,hashlib,datetime,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_receipt_performance_replay_20261115.py').read_text()
exec(s[:s.rindex("out={'method'")])
te=[r for r in rows if r['fid'] in both['TC']]
assert len(te)==263
p=g['forecast'](tr,te,featuremaps['TC'],'full_shot_efficiency')
ref=g['make_pred'](te,vec(te,'mh')+vec(te,'ma'))
assert g['stat'](p[2])['U']==22.435
auditrows={r['fid']:r for r in records}
items=[]
for i,r in enumerate(te):
 f=r['fid'];h=r['source_features']['TC'];dt0=datetime.date.fromisoformat(r['date'])
 items.append({'fid':f,'date':r['date'],'league':r['league'],'name':auditrows[f]['league_name'],'pnl':float(p[2][i]),'market_pnl':float(ref[2][i]),'counts':h['counts'],'effective':min(h['effective']),'oldest_last_days':max((dt0-datetime.date.fromisoformat(x)).days for x in h['last']),'outside':f not in ids,'side':'over' if p[1][i] else 'under'})
def stats(a):
 n=len(a);u=sum(r['pnl'] for r in a);return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None,'positive':sum(r['pnl']>0 for r in a),'negative':sum(r['pnl']<0 for r in a),'zero':sum(r['pnl']==0 for r in a)}
def periodic(a,key):
 d=collections.defaultdict(list)
 for r in a:d[key(r)].append(r)
 return {k:stats(v) for k,v in sorted(d.items())}
def week(r):
 d=datetime.date.fromisoformat(r['date']);y,w,_=d.isocalendar();return f'{y}-W{w:02}'
def equity(a):
 d=collections.defaultdict(float)
 for r in a:d[r['date']]+=r['pnl']
 total=peak=dd=0.;peakdate=None;start=None;end=None;series=[]
 for date,u in sorted(d.items()):
  total+=u
  if total>=peak:peak=total;peakdate=date
  if peak-total>dd:dd=peak-total;start=peakdate;end=date
  series.append({'date':date,'daily_U':round(u,3),'cumulative_U':round(total,3)})
 return {'max_daily_drawdown_U':round(dd,3),'peak_date':start,'trough_date':end,'series':series}
def group(a):
 return {'summary':stats(a),'league':periodic(a,lambda r:r['name']),'weeks':periodic(a,week),'equity':equity(a),'counts':periodic(a,lambda r:'1' if min(r['counts'])==1 else '2-3' if min(r['counts'])<=3 else '4+'),'median_min_effective':round(float(np.median([r['effective'] for r in a])),3),'median_oldest_last_days':float(np.median([r['oldest_last_days'] for r in a]))}
extra=[r for r in items if r['outside']]
assert len(extra)==206 and stats(extra)['U']==19.695
frozen=load('m8_foundation_20261115/historical_membership.jsonl');assert len(frozen)==10294
base2026=[r for r in frozen if r['year']==2026];assert stats(base2026)['U']==99.82
lo=min(r['date'] for r in items);hi=max(r['date'] for r in items)
same=[r for r in base2026 if lo<=r['date']<=hi]
# Earlier TC transfer relied on after-match retrieved market event history, not received quotes.
oldrows=[]
for y in (2023,2025,2026):
 tt=[r for r in g['tcvalid'] if r['year']==y and r['league'] not in ('1','14')]
 train=[r for r in g['esvalid'] if r['year']<y and r['league'] in ('1','14')]
 pp=g['forecast'](train,tt,g['tcfeat'],'full_shot_efficiency')
 for r,u in zip(tt,pp[2]):oldrows.append({'fid':r['fid'],'date':r['date'],'league':r['league'],'pnl':float(u),'outside':r['fid'] not in ids})
assert len(oldrows)==353 and stats(oldrows)['U']==-19.335 and not ({r['fid'] for r in oldrows}&{r['fid'] for r in items})
old26=[r for r in oldrows if r['date'].startswith('2026')]
oldextra=[r for r in oldrows if r['outside']]
# Sensitivity of sample concentration, not a proposed exclusion rule.
leave={n:stats([r for r in items if r['name']!=n]) for n in sorted({r['name'] for r in items})}
out={'method':'Fixed existing TC efficiency model, exact same 263 replay rows. Coverage count categories descriptive only. Daily settled-date equity, no intraday capital or order sequence assumed. FID non-overlap scenario combines historical original eight with actual receipt replay, not production or validated unified simulation. Earlier TC archive distinct fixtures and different quote evidence retained separately.','all':group(items),'outside_eight':group(extra),'leave_one_league':leave,'old_TC':{'all':stats(oldrows),'year':periodic(oldrows,lambda r:r['date'][:4]),'outside_eight':stats(oldextra),'outside_by_year':periodic(oldextra,lambda r:r['date'][:4])},'combination':{'full_2026':{'base':stats(base2026),'add':stats(extra),'combined':stats(base2026+extra),'base_dd':equity(base2026),'combined_dd':equity(base2026+extra)},'matched_date_window':{'start':lo,'end':hi,'base':stats(same),'add':stats(extra),'combined':stats(same+extra),'base_dd':equity(same),'combined_dd':equity(same+extra),'base_weeks':periodic(same,week),'combined_weeks':periodic(same+extra,week)}},'cross_archive_diagnostic':{'all':stats(oldrows+items),'2026':stats(old26+items),'outside_eight_all':stats(oldextra+extra)},'source_coverage':{}}
for l in sorted({r['league'] for r in items}):
 a=[r for r in items if r['league']==l];out['source_coverage'][l]={'name':a[0]['name'],'n':len(a),'TC_history_rows':sum(str(r['league'])==l for r in T.values()),'median_min_prior_count':float(np.median([min(r['counts']) for r in a])),'median_min_effective':round(float(np.median([r['effective'] for r in a])),3),'median_days_since_older_last_match':float(np.median([r['oldest_last_days'] for r in a]))}
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':digest((P/m['historical_membership']['local_file']).read_bytes())==m['historical_membership']['sha256'],'inputs':all(digest((P/k).read_bytes())==v for k,v in m['input_sha256'].items()),'scripts':all(digest((P/k).read_bytes())==v for k,v in m['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_receipt_robustness_20261115.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
for name in ('all','outside_eight'):
 a=out[name];print(name,json.dumps({k:v for k,v in a.items() if k!='equity'},ensure_ascii=False),'DD', {k:v for k,v in a['equity'].items() if k!='series'},flush=True)
print('COVERAGE',out['source_coverage']);print('OLD',out['old_TC'],'CROSS',out['cross_archive_diagnostic'])
for k,v in out['combination'].items():print('COMBO',k,{a:({q:w for q,w in b.items() if q!='series'} if a.endswith('_dd') else b) for a,b in v.items()})
print('LEAVE',out['leave_one_league'],'FOUNDATION',out['foundation'],flush=True)
