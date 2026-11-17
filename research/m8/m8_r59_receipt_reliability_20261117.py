import json,hashlib,collections
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_r59_early_precursor_repricing_20261117.py').read_text()
exec(src[:src.index('for name,data in X.items():')])
base=json.loads((P/'m8_r59_early_precursor_repricing_20261117.json').read_text())
assert all(base['foundation'].values())
def bootstrap(vals,ds,seed=5901,reps=5000):
 a=np.asarray(vals,float)
 dates=collections.defaultdict(list)
 for t,v in zip(ds,a):dates[t].append(float(v))
 if not dates:return None
 s=np.array([sum(v) for v in dates.values()])
 n=np.array([len(v) for v in dates.values()])
 rng=np.random.default_rng(seed)
 v=rng.integers(len(s),size=(reps,len(s)))
 roi=100*s[v].sum(axis=1)/n[v].sum(axis=1)
 return [round(float(x),3) for x in np.quantile(roi,[.025,.975])]
days=np.array([z['date'] for z in R])
ranked_days=np.sort(days)
median_day=ranked_days[len(days)//2]
events=[]
for a,b in pairs:
 events.append('line_changed' if a['al']!=b['al'] else 'same_line_odds_changed' if a['ah']!=b['ah'] or a['aa']!=b['aa'] else 'no_price_change')
events=np.array(events)
res={'study':'R59_RECEIPT_RELIABILITY_NO_NEW_RULES',
 'method':'Reproduce R59 exact prior-calendar-year model and training-score p75/p90 experiment on truly received Crown T24/T12 quotes. Audit UTC kickoff-day cluster 5000 bootstrap CI, chronology split by median RECEIPT FIXTURE DATE (not profit outcome), market repricing groups present at decision. Conditional subgroups diagnostic only, not strategies or gates. Compare future frozen T1 membership post-hoc precision to unconditional receipt baseline; no deployment rule. Do not label receipt replay as prospective locked model. No Crown calls, TG orders or settlement changes.','received_cohort':{'n':len(R),'days':len(set(days)),'dates':[min(days),max(days)],'median_day':median_day,'future_frozen_T1_membership_n_RETROSPECTIVE':int(true_R_membership.sum()),'unconditional_future_frozen_T1_rate_pct':round(100*float(true_R_membership.mean()),3)},
 'models':{},'foundation':base['foundation']}
for name,data in X.items():
 tr=np.flatnonzero((years<2026)&excluded_receipts)
 trside=np.flatnonzero((years<2026)&excluded_receipts&valid_side)
 _,predtr,mp=fit(data,membership,tr,tr)
 _,_,sp=fit(data,side,trside,trside)
 pr=np.clip((actual_X[name]-mp[0])/mp[1],-8,8)@mp[2]
 sd=np.clip((actual_X[name]-sp[0])/sp[1],-8,8)@sp[2]>=.5
 pnl=np.where(sd,actual_H,actual_A)
 z={}
 for mode,t in [('every_fixture',-float('inf')),
 ('research_training_p75',float(np.quantile(predtr,.75))),
 ('research_training_p90',float(np.quantile(predtr,.9)))]:
  chosen=pr>t
  rec=base['models'][name]['actual_received_quotes'][mode]
  assert rec['price_received_AH_simulation']['n']==int(chosen.sum())
  assert abs(rec['price_received_AH_simulation']['U']-pnl[chosen].sum())<.00051
  split={}
  for label,m in [('earlier_dates',days<median_day),('later_dates',days>=median_day),
   ('line_changed_pre_T12',events=='line_changed'),
   ('same_line_odds_changed_pre_T12',events=='same_line_odds_changed'),
   ('no_early_AH_price_change',events=='no_price_change')]:
   sub=chosen&m
   split[label]={'n':int(sub.sum()),'U':round(float(pnl[sub].sum()),3),
    'ROI':round(float(pnl[sub].mean()*100),3) if sub.any() else None}
  week=collections.defaultdict(list)
  for i in np.flatnonzero(chosen):
   week[days[i][:7]].append(float(pnl[i]))
  z[mode]={'n':int(chosen.sum()),
   'U':round(float(pnl[chosen].sum()),3),
   'ROI':round(float(pnl[chosen].mean()*100),3),
   'UTC_day_bootstrap_95percent_ROI':bootstrap(pnl[chosen],days[chosen]),
   'future_frozen_T1_precision_pct_RETROSPECTIVE':round(100*float(true_R_membership[chosen].mean()),3),
   'future_frozen_T1_count':int(true_R_membership[chosen].sum()),
   'split':split,'by_month':{k:{'n':len(v),'U':round(sum(v),3),'ROI':round(100*np.mean(v),3)} for k,v in sorted(week.items())}}
  print('RECEIPT',name,mode,z[mode],flush=True)
 res['models'][name]=z
(P/'m8_r59_receipt_reliability_20261117.json').write_text(json.dumps(res,ensure_ascii=False,indent=2))
