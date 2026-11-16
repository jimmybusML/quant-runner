import json,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_crossyear_round10_replay_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
z,H=historical([r for r in history.values() if r['fid'] in audit['target'] and r['year']>=2023],idx)
assert len(z)==3029 and len(ex)==308
def pred(z,features,kind):
 total=np.zeros(len(z));side=np.zeros(len(z),bool);pnl=np.zeros(len(z))
 for y in sorted({r['year'] for r in z}):
  mask=np.array([r['year']==y for r in z]);te=[r for r,m in zip(z,mask) if m]
  train=[r for r in g['esvalid'] if r['league'] in ('1','14') and r['year']<y]
  total[mask],side[mask],pnl[mask]=g['forecast'](train,te,features,kind)
 return total,side,pnl
def detail(z,ps):
 market=ps['market_implied'];yy=vec(z,'hg')+vec(z,'ag')
 o={}
 for name,p in ps.items():
  change=p[1]!=market[1];a=g['probstats'](z,p[0])
  o[name]={**g['stat'](p[2]),'goals_pred':round(float(p[0].mean()),5),'goals_actual':round(float(yy.mean()),5),'goal_bias':a['mean_goal_bias'],'brier':a['line_brier'],'logloss':a['line_logloss'],'over_bias':a['over_bias'],'over_n':int(p[1].sum()),'over_U':round(float(p[2][p[1]].sum()),3),'under_U':round(float(p[2][~p[1]].sum()),3),'switch_n':int(change.sum()),'switch_delta_U':round(float((p[2]-market[2])[change].sum()),3)}
 return o
def suite(z,H):
 ps={'market_implied':g['make_pred'](z,vec(z,'mh')+vec(z,'ma'))}
 for kind in ('market','full','full_shot_efficiency'):ps[kind]=pred(z,H,kind)
 def sub(m):
  a=[r for r,b in zip(z,m) if b]
  return detail(a,{k:tuple(v[m] for v in p) for k,p in ps.items()}) if a else {}
 return {'all':detail(z,ps),'year':{str(y):sub(np.array([r['year']==y for r in z])) for y in sorted({r['year'] for r in z})},'league_year':{str(y):{l:sub(np.array([r['year']==y and r['league']==l for r in z])) for l in sorted({r['league'] for r in z if r['year']==y})} for y in sorted({r['year'] for r in z})}}
hist=suite(z,H);receipt=suite(ex,F)
assert hist['all']['full_shot_efficiency']['U']==-13.82 and receipt['all']['full_shot_efficiency']['U']==-8.54
# Compare same targets first with naturally available history, then exactly the same source history fixtures.
common=set(E)&set(history);same=[]
errors=collections.Counter()
for fid in common:
 a,b=E[fid],history[fid]
 if any(str(a[k])!=str(b[k]) for k in ('league','home','away','date','hg','ag')):errors['identity']+=1;continue
 same.append(fid)
sameE={f:E[f] for f in same};sameT={f:history[f] for f in same}
def compare(z,H, label):
 EF,EN=features_for(z,histindex(E));TF,TN=features_for(z,idx)
 a=[r for r in z if min(EN[r['fid']])>0 and min(TN[r['fid']])>0]
 def evalpair(a,ef,tf):
  if not a:return {'n':0}
  pp={'market_implied':g['make_pred'](a,vec(a,'mh')+vec(a,'ma')),'ESPN':pred(a,ef,'full_shot_efficiency'),'TC':pred(a,tf,'full_shot_efficiency')}
  return {'n':len(a),'metrics':detail(a,pp),'ESPN_TC_switches':int((pp['ESPN'][1]!=pp['TC'][1]).sum()),'median_abs_goals_difference':round(float(np.median(abs(pp['ESPN'][0]-pp['TC'][0]))),6)}
 se,sn=features_for(a,histindex(sameE));st,tn=features_for(a,histindex(sameT))
 b=[r for r in a if min(sn[r['fid']])>0 and min(tn[r['fid']])>0]
 assert all(sn[r['fid']]==tn[r['fid']] for r in b)
 return {'natural':evalpair(a,EF,TF),'same_history_ESPN_TC':evalpair(b,se,st),'same_history_natural':evalpair(b,EF,TF),'natural_by_year':{str(y):evalpair([r for r in a if r['year']==y],EF,TF) for y in sorted({r['year'] for r in a})}}
# Compare provider raw metric distributions on identity-matched fixture pairs (descriptive).
diff={}
for k in ('hshots','ashots','hsot','asot','hposs','aposs'):
 v=np.array([float(history[f][k])-float(E[f][k]) for f in same])
 diff[k]={'mean_TC_minus_ESPN':round(float(v.mean()),4),'median_abs':round(float(np.median(abs(v))),4),'exact_n':int((v==0).sum())}
# Constant composition across 2024-26: compare only leagues represented each year, equal league weight.
ly=hist['league_year'];ls=set.intersection(*(set(ly[str(y)]) for y in (2024,2025,2026)))
mix={str(y):{'n':sum(ly[str(y)][l]['full_shot_efficiency']['n'] for l in ls),'equal_league_ROI':round(float(np.mean([ly[str(y)][l]['full_shot_efficiency']['ROI'] for l in ls])),4),'equal_league_market_ROI':round(float(np.mean([ly[str(y)][l]['market_implied']['ROI'] for l in ls])),4)} for y in (2024,2025,2026)}
out={'method':'Fixed R10 historical data; market-implied, market-only calibration, full features, full shot efficiency compared on identical targets. Annual training prior years ESPN; diagnostic comparisons, not model selection. Historical and actual pre-match receipt replay evidence separate. Shared history uses exact fixture identity, date and score.','history_n':len(history),'historical':hist,'receipt':receipt,'common_league_set':sorted(ls),'equal_league_descriptive':mix,'source_raw_overlap_n':len(common),'source_identity_matched_n':len(same),'source_identity_failures':dict(errors),'raw_metric_diff':diff,'historical_source':compare(z,H,'historical'),'receipt_source':compare(ex,F,'receipt')}
(P/'m8_tc_bias_diagnosis_20261116.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
for name,ss in [('historical',hist),('receipt',receipt)]:
 print(name,'ALL',json.dumps(ss['all']),flush=True)
 for y,a in ss['year'].items():print(name,y,json.dumps(a),flush=True)
print('MIX',sorted(ls),mix)
print('SOURCE',len(common),len(same),diff)
for k in ('historical_source','receipt_source'):
 for name,v in out[k].items():
  if name!='natural_by_year':print(k,name,json.dumps(v),flush=True)
