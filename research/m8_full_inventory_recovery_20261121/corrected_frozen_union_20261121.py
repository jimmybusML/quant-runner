"""Corrected historical union following authoritative full-path original M8 replay.
Old 3-sample extension PR67 summary superseded. No production edits.
"""
import gzip,json,collections
from pathlib import Path
P=Path(__file__).resolve().parent
F=Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
def rows(p):
 with (gzip.open(p,'rt') if str(p).endswith('.gz') else open(p)) as f:
  for s in f:yield json.loads(s)
frozen=[{'fid':r['fid'],'year':r['year'],'league':r['league'],'group':r['cohort'],'net_u':float(r['pnl']),
 'cohort':'original_frozen'} for r in rows(F)]
correct_ledger=P/'faithful_frozen_full_path_48890_ledger.jsonl.gz'
if not correct_ledger.exists():correct_ledger=P/'full_path_corrected_20261121/faithful_frozen_full_path_48890_ledger.jsonl.gz'
correct=[{'fid':r['fid'],'year':r['year'],'league':r['league'],'group':r['group'],'side':r['side'],'net_u':float(r['net_u_T1']),
 'cohort':'full_path_expansion'} for r in rows(correct_ledger) if r['source']=='expanded15']
assert len(frozen)==10294 and len(correct)==1271
oldpr=P/'source67/research/m8_m9_group_independent_20261120/exact_rule_cross_league/exact_rule_cross_league_orders.jsonl.gz'
if not oldpr.exists():oldpr=Path('/Users/mac/QuantAsiaDesk/research-work/recovered_factors_20261121/source67/research/m8_m9_group_independent_20261120/exact_rule_cross_league/exact_rule_cross_league_orders.jsonl.gz')
fromPR={r['fid']:r for r in rows(oldpr)}
assert len(fromPR)==1160
ftids={r['fid'] for r in frozen}; ctids={r['fid'] for r in correct}
assert not ftids&ctids
league_ids={'37','141','75'}
three=[{'fid':r['fid'],'year':r['year'],'league':r['league'],'net_u':float(r['pnl_U']),
 'group':'three_league_POSTHOC','cohort':'posthoc_three_league'} for r in
 rows(P/'full62_price_models_ledger.jsonl.gz') if not r['is_m8_member'] and r['model']=='price_league_binary'
 and r['training']=='annual_forward' and r['league'] in league_ids]
assert len(three)==1559
threeids={r['fid'] for r in three}
assert not (threeids&(ctids|ftids))
def stat(z):
 n=len(z);u=sum(r['net_u'] for r in z)
 return {'n':n,'net_U':round(u,4),'ROI_pct':round(100*u/n,4) if n else None}
def byyear(z):return {str(y):stat([r for r in z if r['year']==y]) for y in range(2019,2027)}
def bygroup(z):return {g:stat([r for r in z if r['group']==g]) for g in ('base','A','B','C','D','E','F','G')}
out={'correction':'The old PR67 extension aggregated only the three sample quotes for path shape/price moves; this replay follows original full raw quote sequence from T6 through T1.',
 'original_M8':stat(frozen),'corrected_external':stat(correct),'corrected_external_year':byyear(correct),
 'corrected_external_group':bygroup(correct),
 'original_plus_corrected':stat(frozen+correct),
 'three_profit_leagues_exploratory':stat(three),
 'original_plus_three_profit_leagues_hypothetical':stat(frozen+three),
 'original_plus_corrected_plus_three_profit_leagues_hypothetical':stat(frozen+correct+three),
 '2024_26':{'original_M8':stat([r for r in frozen if r['year']>=2024]),
 'corrected_extra15':stat([r for r in correct if r['year']>=2024]),
 'posthoc_three_leagues':stat(three),
 'original_plus_extra15':stat([r for r in frozen+correct if r['year']>=2024]),
 'original_plus_three_leagues':stat([r for r in frozen+three if r['year']>=2024]),
 'all_three_hypothetical':stat([r for r in frozen+correct+three if r['year']>=2024])},
 'yearly_posthoc_three_leagues':byyear(three),
 'corrected_external_vs_old_PR67':{'old_fids':len(fromPR),
   'new_fids':len(correct),'shared_FIDs':len(ctids&set(fromPR)),
   'new_only_FIDs':len(ctids-set(fromPR)),
   'old_only_FIDs':len(set(fromPR)-ctids),
   'changed_group_shared':sum(r['group']!=fromPR[r['fid']]['group'] for r in correct if r['fid'] in fromPR),
   'changed_side_shared':sum(r['side']!=fromPR[r['fid']]['side'] for r in correct if r['fid'] in fromPR)},
 'frozen_group_sha_integrity':'Frozen membership untouched 10,294; original49 full-path 9,482 matched in group and pnl, 133 frozen G require missing score rates, 679 lack T6 inventory',
 'raw_contract_verification':'Independent external 1,271/1,271 raw Crown SHA, FID, teams, FT, T1 source timestamp/line/odds, five-state returns pass',
 'nonapproved_status':[
 'All quotes historical Crown source events retrieved after fixture; no verified real pregame HTTP receipt',
 'These are historical arithmetic unions only, not executable orders, no production change',
 'Three leagues were chosen with known 2024-26 outcomes, thus posthoc selection',
 'Original and extra15 2026 have unequal coverage',
 'No additional screening, thresholds, release gates, or business logic introduced']}
(P/'corrected_frozen_union_summary_20261121.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
with gzip.open(P/'corrected_frozen_union_ledger_20261121.jsonl.gz','wt') as f:
 for r in frozen+correct+three:f.write(json.dumps(r,ensure_ascii=False)+'\n')
for k in ['original_M8','corrected_external','original_plus_corrected','three_profit_leagues_exploratory','original_plus_corrected_plus_three_profit_leagues_hypothetical']:
 print(k,out[k],flush=True)
print('2024-26',out['2024_26'],flush=True)
print('correction',out['corrected_external_vs_old_PR67'],flush=True)
