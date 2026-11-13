import json,collections,datetime,statistics
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
study=json.load((P/'m8_2026_Jan_Nov_original210_method_volume_capacity_20261113.json').open())
scope={str(z['league_id']) for z in map(json.loads,(P/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl').open())}
discovery=json.load(open('/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23/fixtures.json'))
sched=collections.Counter();months=collections.Counter()
for fid,r in discovery.items():
 if str(r.get('league_id')) not in scope:continue
 x=datetime.datetime.fromisoformat(r['kickoff_at'].replace('Z','+00:00')).isocalendar()
 w=f'{x.year}-W{x.week:02}'
 sched[w]+=1;months[r['kickoff_at'][:7]]+=1
complete={}
for wk in ('2026-W41','2026-W42','2026-W43','2026-W44','2026-W45'):
 row=study['live_actual_Crown_receipt_by_ISO_week'][wk];n=sched[wk];captured=row['unique_49league_real_receipt_fixtures'];c=row['deepen_candidates'];missing=n-captured
 complete[wk]={'discovered_49_fixture_universe':n,'unique_with_genuine_Crown_receipt':captured,'missing_actual_receipt':missing,'actual_210_method_candidates':c,'actual_210_method_settled':row['deepen_settled'],'actual_210_method_ROI_pct':row['deepen_ROI_pct'],'absolute_max_candidates_if_ALL_missing_reception_matches_trigger':c+missing,'share_of_universe_trigger_pct':round(100*c/n,2)}
 print('WEEK',wk,complete[wk],flush=True)
avg={k:round(statistics.mean(r[k] for r in complete.values()),2) for k in ('discovered_49_fixture_universe','unique_with_genuine_Crown_receipt','actual_210_method_candidates','absolute_max_candidates_if_ALL_missing_reception_matches_trigger')}
print('AVG',avg)
out={'caption':'Upper bound is only over MR1 already discovered original49 fixture universe, not all real-world league fixtures. Even if every discovered fixture missing a valid Crown receipt were a signal, total weekly max would stay under 120 in observed weeks. Not a forecast or production cap.','weeks':complete,'five_week_average':avg,'required_wk_fixture_eligible_if_current_signal_rate':study['theoretical_volume_capacity_if_same_signal_rate']['target_120_per_week_required_qualified_AH_asof_matches_at_observed_signal_rate'],'other_target_150':study['theoretical_volume_capacity_if_same_signal_rate']['target_150_per_week_required_qualified_AH_asof_matches_at_observed_signal_rate'],'no_new_rules':True}
(P/'m8_2026_49league_observed_weekly_signal_capacity_bound_20261113.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
