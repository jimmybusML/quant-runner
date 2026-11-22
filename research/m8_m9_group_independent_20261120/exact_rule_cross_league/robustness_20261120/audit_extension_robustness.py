#!/usr/bin/env python3
"""Fixed robustness diagnostics for the exact-rule cross-league replay.
No thresholds or rules are fit or selected here.
"""
import collections, datetime as dt, gzip, hashlib, json, random
from pathlib import Path

HERE=Path(__file__).resolve().parent
LEDGER=HERE.parent/'exact_rule_cross_league_orders.jsonl.gz'
EXPANSION_SUMMARY=HERE.parent/'exact_rule_cross_league_summary.json'
SCHEDULE=Path('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl')
RECEIPTS=Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
OUT=HERE/'robustness_results.json'
SEED=4862026
REPLICATES=20000
BLOCK_WEEKS=4

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 rows=[json.loads(line) for line in gzip.open(LEDGER,'rt')]
 assert len(rows)==1160 and len({r['fid'] for r in rows})==1160
 total_u=sum(float(r['net_u']) for r in rows)
 by_league=collections.defaultdict(lambda:[0,0.])
 by_year=collections.defaultdict(lambda:[0,0.])
 weekly=collections.defaultdict(lambda:[0,0.])
 for r in rows:
  n,u=1,float(r['net_u'])
  by_league[r['league']][0]+=1;by_league[r['league']][1]+=u
  by_year[str(r['year'])][0]+=1;by_year[str(r['year'])][1]+=u
  weekly[r['iso_week']][0]+=1;weekly[r['iso_week']][1]+=u
 loo_league=[]
 for league,(n,u) in sorted(by_league.items()):
  loo_league.append({'omitted_league':league,'orders_omitted':int(n),'net_u_omitted':round(u,6),'remaining_orders':len(rows)-int(n),'remaining_net_u':round(total_u-u,6),'remaining_roi_pct':round(100*(total_u-u)/(len(rows)-int(n)),6)})
 loo_year=[]
 for year,(n,u) in sorted(by_year.items()):
  loo_year.append({'omitted_year':year,'orders_omitted':int(n),'net_u_omitted':round(u,6),'remaining_orders':len(rows)-int(n),'remaining_net_u':round(total_u-u,6),'remaining_roi_pct':round(100*(total_u-u)/(len(rows)-int(n)),6)})
 first=dt.date.fromisocalendar(int(min(weekly)[:4]),int(min(weekly)[-2:]),1)
 last=dt.date.fromisocalendar(int(max(weekly)[:4]),int(max(weekly)[-2:]),1)
 allweeks=[];day=first
 while day<=last:
  iso=day.isocalendar(); key=f'{iso.year}-W{iso.week:02d}'
  allweeks.append(weekly.get(key,[0,0.]));day+=dt.timedelta(days=7)
 rng=random.Random(SEED);boot=[];nweeks=len(allweeks)
 for _ in range(REPLICATES):
  sample=[]
  while len(sample)<nweeks:
   start=rng.randrange(nweeks)
   sample.extend(allweeks[(start+i)%nweeks] for i in range(BLOCK_WEEKS))
  sample=sample[:nweeks];n=sum(x[0] for x in sample);u=sum(x[1] for x in sample)
  if n:boot.append((u,100*u/n))
 def quant(col,p):
  vals=sorted(x[col] for x in boot)
  return vals[round((len(vals)-1)*p)]
 expansion=json.loads(EXPANSION_SUMMARY.read_text())
 new_ids=set(expansion['sources']['outside49_provider_league_ids'])
 schedule_rows=[json.loads(line) for line in SCHEDULE.open() if line.strip()]
 new_2026=[r for r in schedule_rows if str(r['league_id']) in new_ids and str(r['kickoff_source_local']).startswith('2026')]
 live_receipt_ids={str(json.loads(line)['fixture_id']) for line in RECEIPTS.open() if line.strip()}
 new_2026_receipt_ids=live_receipt_ids.intersection({str(r['match_id']) for r in new_2026})
 path_2026=int(expansion['coverage']['per_year']['2026'].get('complete_T6_T3_T1_path',0))
 result={
  'study':'Robustness diagnostics for unchanged frozen exact M8 base/A-G rules applied outside original49; retrospective only.',
  'input':str(LEDGER),'input_sha256':sha(LEDGER),'coverage_input_sha256':{str(p):sha(p) for p in (EXPANSION_SUMMARY,SCHEDULE,RECEIPTS)},'n_orders':len(rows),'n_unique_fids':len({r['fid'] for r in rows}),'net_u':round(total_u,6),'roi_pct':round(100*total_u/len(rows),6),
  'league_count_with_orders':len(by_league),'positive_leagues':sum(u>0 for n,u in by_league.values()),'negative_leagues':sum(u<0 for n,u in by_league.values()),
  'leave_one_league_out':loo_league,'leave_one_year_out':loo_year,
  'week_block_bootstrap':{'method':'circular resampling of consecutive 4-ISO-week blocks; zero-order weeks retained; percentile interval; diagnostics do not correct for prior research selection or multiple comparisons.','seed':SEED,'replicates':len(boot),'block_weeks':BLOCK_WEEKS,'span_weeks':nweeks,'weeks_with_orders':len(weekly),'net_u_ci95':[round(quant(0,.025),6),round(quant(0,.975),6)],'roi_pct_ci95':[round(quant(1,.025),6),round(quant(1,.975),6)],'bootstrap_fraction_net_positive':round(sum(u>0 for u,roi in boot)/len(boot),6)},
  'by_league':{k:{'orders':int(v[0]),'net_u':round(v[1],6),'roi_pct':round(100*v[1]/v[0],6)} for k,v in sorted(by_league.items())},
  'by_year':{k:{'orders':int(v[0]),'net_u':round(v[1],6),'roi_pct':round(100*v[1]/v[0],6)} for k,v in sorted(by_year.items())},
  'weekly':{k:{'orders':int(v[0]),'net_u':round(v[1],6)} for k,v in sorted(weekly.items())},
  'additional_15_league_2026_data_availability':{'provider_league_ids':sorted(new_ids),'schedule_fixtures':len(new_2026),'latest_kickoff_local':max((r['kickoff_source_local'] for r in new_2026),default=None),'schedule_leagues_present':sorted({str(r['league_id']) for r in new_2026}),'complete_T6_T3_T1_historical_paths_from_expansion_audit':path_2026,'unique_fids_in_MR1_HTTP_receipt_archive':len(new_2026_receipt_ids),'receipt_claim':'none; archive overlap only and no full score features/quotes are implied'},
  'rule_changes':False,'production_changes':False,'formal_orders':0,'ledger_writes':0,
 }
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'n_orders':len(rows),'net_u':round(total_u,6),'roi_pct':round(100*total_u/len(rows),6),'league_count':len(by_league),'leave_one_league_out_min_u':min(x['remaining_net_u'] for x in loo_league),'leave_one_league_out_max_u':max(x['remaining_net_u'] for x in loo_league),'positive_leave_one_league_out':sum(x['remaining_net_u']>0 for x in loo_league),'leave_out_international_match_u':next(x['remaining_net_u'] for x in loo_league if x['omitted_league']=='International Match'),'block_bootstrap':result['week_block_bootstrap']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
