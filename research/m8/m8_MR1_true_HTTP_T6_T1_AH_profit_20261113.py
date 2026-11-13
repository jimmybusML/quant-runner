import json,collections,datetime,hashlib
from pathlib import Path
import numpy as np
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work')
Q=P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
FT=P/'m7/m7_full_scope_8_axis_combo_pending_FT_recovered_20261110.jsonl'
fts={}
for r in map(json.loads,FT.open()):
 if r.get('verified_FT_score'):fts[r['fixture_id']]=r['verified_FT_score']
by=collections.defaultdict(list)
for r in map(json.loads,Q.open()):by[r['fixture_id']].append(r)
def ts(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
out=[];quality=collections.Counter()
for fid,arr in by.items():
 arr.sort(key=lambda x:x['received_utc'])
 # use frozen fixture kickoff for old FT, source snapshot for new only if no FT, never settle unverifiable.
 kickoff=ts(arr[-1]['kickoff_utc'])
 if any(ts(z['kickoff_utc'])!=kickoff for z in arr):quality['inconsistent_snapshot_kickoff']+=1
 six=kickoff-datetime.timedelta(hours=6);one=kickoff-datetime.timedelta(hours=1)
 q6=[r for r in arr if ts(r['received_utc'])<=six]
 q1=[r for r in arr if ts(r['received_utc'])<=one]
 if not q6:quality['missing_observed_at_T6']+=1
 if not q1:quality['missing_observed_at_T1']+=1
 z6=q6[-1] if q6 else None;z1=q1[-1] if q1 else None
 if not z6 or not z1:continue
 # Store last known price as-of T-6 and as-of T-1 from real HTTP, both check bookmaker source event <= receipt and kickoff.
 m6=z6['markets']['AH'];m1=z1['markets']['AH']
 line=float(m1['line']);first=float(m6['line'])
 if line==0:
  quality['zero_asof_T1_AH']+=1;continue
 fav='home' if line<0 else 'away';dog='away' if line<0 else 'home'
 shift=line-first
 state='deepen' if shift*line>0 else 'weaken' if shift*line<0 else 'unchanged'
 q6age=(six-ts(z6['received_utc'])).total_seconds()/3600
 q1age=(one-ts(z1['received_utc'])).total_seconds()/3600
 score=fts.get(fid)
 row={'fid':fid,'observed_snapshot_count':len(arr),'kickoff_utc':arr[-1]['kickoff_utc'],'market':'AH','state':state,'line_T6':first,'line_T1':line,'received_T6':z6['received_utc'],'received_T1':z1['received_utc'],'received_delay_before_cutoff_T6_hours':round(q6age,3),'received_delay_before_cutoff_T1_hours':round(q1age,3),'bookmaker_source_age_T1_hours':m1['source_age_minutes_at_actual_receipt']/60,'dog_odd_T1':m1['odds'][dog],'fav_odd_T1':m1['odds'][fav],'FT_verified_from_existing_frozen_dataset':score,'dog_pnl':None,'fav_pnl':None,'snapshot_T1_source_SHA256':z1['raw_sha256']}
 if score:
  h,g=map(int,score.split('-'))
  row['dog_pnl']=settle_score('AH',line,dog,h,g,m1['odds'][dog])[1]
  row['fav_pnl']=settle_score('AH',line,fav,h,g,m1['odds'][fav])[1]
 else:quality['FT_not_in_frozen_verified_results']+=1
 out.append(row)
def stat(x,key):
 y=[r[key] for r in x if r[key] is not None];n=len(y)
 return {'observed':len(x),'settled':n,'net_U':round(sum(y),3),'ROI_pct':round(100*sum(y)/n,3) if n else None}
data={'source':'MR1 archived Crown actual HTTP received, earliest/latest valid as of Tminus6 and Tminus1, FT from existing frozen M7 FT lookup only','total_actual_received_unique':len(by),'with_both_asof_cutoffs_nonzero_AH':len(out),'verified_FT_all':len(fts),'quality':dict(quality),'by_state':{},'by_month':{},'not_formal_M8_TG':True,'research_cutoffs_not_production_rules':True}
for state in ('deepen','weaken','unchanged'):
 z=[r for r in out if r['state']==state]
 data['by_state'][state]={'dog':stat(z,'dog_pnl'),'favorite':stat(z,'fav_pnl')}
 print('STATE',state,data['by_state'][state],flush=True)
 for month in ('2026-10','2026-11'):
  sub=[r for r in z if r['kickoff_utc'].startswith(month)]
  data['by_month'][month+'|'+state]={'dog':stat(sub,'dog_pnl'),'favorite':stat(sub,'fav_pnl')}
  print('MONTH',month,state,data['by_month'][month+'|'+state],flush=True)
print('QUALITY',data['quality'],flush=True)
(P/'m8_MR1_true_HTTP_T6_T1_AH_profit_20261113.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
(P/'m8_MR1_true_HTTP_T6_T1_AH_profit_20261113.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out))
