import json,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_crossyear_round9_replay_20261116.py').read_text()
exec(s[:s.rindex('out={\'method\'')])
# Validate on different fixtures, excluding the entire verified receipt archive.
# Training recipes, historical feature lag, and all trade parameters stay unchanged.
recs=[r for r in history.values() if r['fid'] in audit['target'] and r['year']>=2023]
allz,allF=historical(recs,idx)
receipt_ids={r['fid'] for r in rows}
z=[r for r in allz if r['fid'] not in receipt_ids]
assert len({r['fid'] for r in z})==len(z) and not ({r['fid'] for r in z}&receipt_ids)
base={**orig,**{r['fid']:r for r in bridge}}
stages=[r1,r2,r3,r4,r5,r6,r7,r8,r9]
pred=[];coverage=[]
for i,batch in enumerate(stages,1):
 base.update({r['fid']:r for r in batch})
 f,n=features_for(z,histindex(base))
 mask=np.array([min(n[r['fid']])>0 for r in z])
 zz=[r for r,b in zip(z,mask) if b]
 pp=predict_annual(zz,f)
 side=np.full(len(z),-1,dtype=int); side[mask]=pp[1].astype(int)
 pnl=np.full(len(z),np.nan);pnl[mask]=pp[2]
 pred.append((side,pnl));coverage.append({'round':i,'n':int(mask.sum()),'history_n':len(base)})
side=np.stack([p[0] for p in pred]);pnl=np.stack([p[1] for p in pred])
has=side>=0
assert np.all(has[-1]) and np.all(~has[:-1]|has[1:])
first=has.argmax(axis=0);first_side=side[first,np.arange(len(z))]
first_pnl=pnl[first,np.arange(len(z))]
last_pnl=pnl[-1]
stable=np.all(~has|(side==first_side),axis=0)
multiple=has.sum(axis=0)>1
common=has[0]
market=g['make_pred'](z,vec(z,'mh')+vec(z,'ma'))[2]
def group(mask):
 return {'n':int(mask.sum()),'first':g['stat'](first_pnl[mask]),'last':g['stat'](last_pnl[mask]),'market':g['stat'](market[mask])}
def breakdown(mask):
 return {'all':group(mask),'stable':group(mask&stable&multiple),'changed':group(mask&~stable&multiple),'one_available_version':group(mask&~multiple)}
years=sorted({r['year'] for r in z})
out={'method':'Retrospective replication on distinct historical quote fixtures outside ALL 1393 verified receipt test fixtures, compared on available chronological archive vintages R1-R9. Earliest covered version differs by fixture outside common cohort. Stable grouping uses later archive vintages and is NOT a prospective signal, rule, or unseen-results test. Same annual models.','receipt_excluded':len(receipt_ids),'eligible_historical_all':len(allz),'distinct_historical_n':len(z),'coverage':coverage,'common_R1_R9':breakdown(common),'all_with_coverage':breakdown(np.ones(len(z),bool)),'common_by_year':{str(y):breakdown(common&np.array([r['year']==y for r in z])) for y in years},'all_by_year':{str(y):breakdown(np.array([r['year']==y for r in z])) for y in years},'by_first_covered_round':{str(i+1):breakdown(first==i) for i in range(len(stages))},'outside_frozen_eight':breakdown(np.array([r['fid'] not in ids for r in z]))}
(P/'m8_tc_historical_vintage_replication_20261116.json').write_text(json.dumps(out,indent=2))
for k in ('receipt_excluded','eligible_historical_all','distinct_historical_n','coverage','common_R1_R9','all_with_coverage','all_by_year','outside_frozen_eight','by_first_covered_round'):print(k,json.dumps(out[k]),flush=True)
