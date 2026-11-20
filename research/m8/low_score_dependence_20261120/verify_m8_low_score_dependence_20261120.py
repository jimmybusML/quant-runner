#!/usr/bin/env python3
"""Independent contract/FT/settlement/FID audit of low-score DC ledger."""
import collections,datetime as dt,gzip,hashlib,json,math
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
LEDGER=HERE/'m8_low_score_dependence_orders_20261120.jsonl.gz'
SCORE=WORK/'m8_independent_score_strength_20261114.jsonl'
MARKET=WORK/'m8_late_full_path_water_features_20261114.jsonl'
M5=WORK/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl'
FROZEN=WORK/'m8_foundation_20261115/historical_membership.jsonl'
EXTRA=Path(__file__).resolve().parents[1]/'exact_rules_outside_original49_20261120/exact_rule_cross_league_all_complete_paths.jsonl.gz'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(p):return [json.loads(x) for x in open(p,encoding='utf-8') if x.strip()]
def quarter_settle(line,side,hg,ag,odds):
 line=float(line);q=line*4
 if abs(q-round(q))>1e-7:raise AssertionError(f'not a quarter line: {line}')
 legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 leg_u=[]
 for leg in legs:
  margin=hg-ag+leg if side=='home' else ag-hg-leg
  leg_u.append(float(odds)-1 if margin>1e-9 else -1. if margin<-1e-9 else 0.)
 label='full_win' if all(x>0 for x in leg_u) else 'half_win' if any(x>0 for x in leg_u) else 'push' if all(x==0 for x in leg_u) else 'half_loss' if any(x==0 for x in leg_u) else 'full_loss'
 return sum(leg_u)/len(leg_u),label
def main():
 score={str(x['fid']):x for x in read(SCORE)};market={str(x['fid']):x for x in read(MARKET)};m5={str(x['fid']):x for x in read(M5)};frozen={str(x['fid']) for x in read(FROZEN)}
 with gzip.open(EXTRA,'rt',encoding='utf-8') as f:extra={str(x['fid']):x for x in (json.loads(y) for y in f if y.strip())}
 ledger=[json.loads(x) for x in gzip.open(LEDGER,'rt',encoding='utf-8')]
 errors=collections.Counter();by_method=collections.defaultdict(list);per_fid=collections.defaultdict(list);checked=0
 for r in ledger:
  fid=str(r['fid']);seg=r['segment']
  if seg=='additional15':
   src=extra.get(fid)
   if not src:errors['missing_crown_path_source']+=1;continue
   vals=(float(src['end_line']),float(src['home_price']),float(src['away_price']),int(src['hg']),int(src['ag']))
  elif r['year']==2026:
   src=m5.get(fid)
   if not src:errors['missing_m5_source']+=1;continue
   hg,ag=map(int,str(src['score_goals']).split('-'));vals=(float(src['AH_t1_line']),float(src['AH_t1_odds_home']),float(src['AH_t1_odds_away']),hg,ag)
  else:
   src=market.get(fid)
   if not src:errors['missing_original49_path_source']+=1;continue
   s=score.get(fid)
   if not s:errors['missing_ft_source']+=1;continue
   vals=(float(src['end_line']),float(src['home_price']),float(src['away_price']),int(s['hg']),int(s['ag']))
  if abs(vals[0]-float(r['line']))>1e-8 or abs(vals[1]-float(r['ho']))>1e-8 or abs(vals[2]-float(r['ao']))>1e-8 or vals[3]!=int(r['hg']) or vals[4]!=int(r['ag']):errors['source_contract_or_ft_mismatch']+=1
  if r['frozen']!=(fid in frozen):errors['frozen_overlap_flag_mismatch']+=1
  if (not r['frozen'])!=(fid not in frozen):errors['incremental_flag_mismatch']+=1
  u,label=quarter_settle(r['line'],r['selected_side'],int(r['hg']),int(r['ag']),float(r['selected_price']))
  if abs(u-float(r['net_u']))>1e-9 or label!=r['settlement']:errors['model_settlement_mismatch']+=1
  side=r['ev_positive_side']
  eu,el=(quarter_settle(r['line'],side,int(r['hg']),int(r['ag']),float(r['ho'] if side=='home' else r['ao'])) if side else (0.,'no_bet'))
  if abs(eu-float(r['ev_positive_net_u']))>1e-9 or el!=r['ev_positive_settlement']:errors['ev_diagnostic_settlement_mismatch']+=1
  by_method[r['method']].append(r);per_fid[(r['method'],fid)].append(r);checked+=1
 result={}
 for method,rows in by_method.items():
  ids=[str(x['fid']) for x in rows];inc=[x for x in rows if not x['frozen']]
  if len(ids)!=len(set(ids)):errors[f'{method}_duplicate_fids']+=len(ids)-len(set(ids))
  if {str(x['fid']) for x in inc}&frozen:errors[f'{method}_frozen_fid_overlap_in_incremental']+=1
  if len({x['fid'] for x in inc})!=len(inc):errors[f'{method}_duplicate_incremental_fids']+=1
  result[method]={'rows':len(rows),'unique_test_fids':len(set(ids)),'incremental_fids':len(inc),'net_u_recomputed':round(sum(float(x['net_u']) for x in inc),6),'ev_positive_incremental_fids':sum(bool(x['ev_positive_side']) for x in inc),'ev_positive_net_u_recomputed':round(sum(float(x['ev_positive_net_u']) for x in inc),6),'all_actual_receipt_flags_false':all(not x['actual_http_receipt'] for x in rows)}
 out={'independent_ledger_rows_checked':checked,'errors':dict(errors),'pass':not errors,'frozen_membership_fids':len(frozen),'frozen_sha256':sha(FROZEN),'source_sha256':{'score_history':sha(SCORE),'crown_paths_original49':sha(MARKET),'m5_2026':sha(M5),'additional15_paths':sha(EXTRA),'ledger':sha(LEDGER)},'by_method':result,'production_changes':False,'formal_telegram_orders':0,'formal_ledger_writes':0}
 (HERE/'independent_verification_20261120.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
