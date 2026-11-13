import json,collections,statistics
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
hist={r['fid']:r for r in map(json.loads,(P/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').open()) if r['month'] in ('2026-10','2026-11')}
live={r['fid']:r for r in map(json.loads,(P/'m8_MR1_true_HTTP_T6_T1_AH_profit_20261113.jsonl').open()) if r['kickoff_utc'][:7] in ('2026-10','2026-11')}
both=set(hist)&set(live)
comp=collections.Counter()
details=[]
for fid in both:
 a=hist[fid];b=live[fid]
 comp['all_overlap']+=1
 comp['historic_deepen']+=a['direction']=='deepen'
 comp['actual_deepen']+=b['state']=='deepen'
 if a['direction']==b['state']:comp['same_state']+=1
 else:comp['different_state']+=1
 if a['direction']=='deepen' and b['state']=='deepen':
  comp['both_deepen']+=1
  if b['FT_verified_from_existing_frozen_dataset'] is not None:
   comp['both_deepen_FT']+=1
   comp['both_deepen_historical_pnl']+=a['dog_U']
   comp['both_deepen_real_received_pnl']+=b['dog_pnl']
 if a['direction']=='deepen' and b['state']!='deepen':comp['historical_only_signal']+=1
 if a['direction']!='deepen' and b['state']=='deepen':comp['actual_only_signal']+=1
 if a['score_goals']!=b['FT_verified_from_existing_frozen_dataset'] and b['FT_verified_from_existing_frozen_dataset']:
  comp['score_conflict']+=1
 details.append({'fid':fid,'h_direction':a['direction'],'live_direction':b['state'],'h_dog_U':a['dog_U'],'live_dog_U':b['dog_pnl'],'h_price_dog':a['AH_t1_odds_home'] if a['dog_side']=='home' else a['AH_t1_odds_away'],'live_price_dog':b['dog_odd_T1'],'h_line':a['AH_t1_line'],'live_line':b['line_T1'],'month':a['month']})
comp['both_deepen_historical_pnl']=round(comp['both_deepen_historical_pnl'],3);comp['both_deepen_real_received_pnl']=round(comp['both_deepen_real_received_pnl'],3)
p=comp['both_deepen_FT']
summary={'historical_available_for_2026_oct_nov':len(hist),'actual_HTTP_t6t1_available':len(live),'overlap':len(both),'comparison':dict(comp),'both_deepen_FT_n':p,'both_deepen_historical_ROI_pct':round(comp['both_deepen_historical_pnl']*100/p,3) if p else None,'both_deepen_real_receipt_ROI_pct':round(comp['both_deepen_real_received_pnl']*100/p,3) if p else None,'notes':'No new filters. Historical Crown source-event reconstruction vs genuine HTTP receipt as-of T6/T1 may differ due unavailable quotes or changed kickoff. Historical files later downloaded 2026-11 and not actual received.'}
for mon in ('2026-10','2026-11'):
 z=[x for x in details if x['month']==mon]
 cnt=collections.Counter((x['h_direction'],x['live_direction']) for x in z)
 summary[mon]={'overlap':len(z),'states':{str(k):v for k,v in cnt.items()}}
print('SUMMARY',json.dumps(summary,ensure_ascii=False),flush=True)
(P/'m8_M5_vs_MR1_2026_OctNov_same_fixture_signal_agreement_20261113.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
