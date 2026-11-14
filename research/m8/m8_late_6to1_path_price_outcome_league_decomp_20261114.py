import json,collections,statistics
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rs=[json.loads(l) for l in (P/'m8_late_6to1_dynamic_path_recovery_20261114.jsonl').open()]
rmap={(r['year'],r['fid']):r for r in rs if r['base'] or r.get('path_6_3_1') in ('deepen_weaken','weaken_same')}
G=collections.defaultdict(list)
for r in map(json.loads,(P/'m8_early_AH_same_line_water_movement_2019to2026_20261114.jsonl').open()):
 if r['window']!='6->1':continue
 key=(r['year'],r['fid']);t=rmap.get(key)
 if t is None or r['end_zero']:continue
 side='home' if r['end_line']>0 else 'away'
 odd=r['end_home_odds'] if side=='home' else r['end_away_odds']
 pnl=t['base_U'] if t['base'] else t['end_dog_U']
 if abs(pnl-r['underdog_U'])>1e-7:raise ValueError(str(key))
 # Counterfactual 1.95 decomposes payout vs outcome; never claim it was a historical executable quote.
 f=pnl/(odd-1) if pnl>0 else 0.;lost=-pnl if pnl<0 else 0.
 assert -.0001<=f<=1.0001 and -.0001<=lost<=1.0001
 row={'id':r['fid'],'year':r['year'],'league':r['league'],'price':odd,'real_U':pnl,'ref_U':f*.95-lost,'won_fraction':f,'lost_fraction':lost}
 g='base' if t['base'] else 'A' if t['path_6_3_1']=='deepen_weaken' else 'B'
 G[g].append(row)
def st(z):
 n=len(z)
 if not n:return {'n':0}
 mean=lambda f:sum(r[f] for r in z)/n
 return {'n':n,'mean_decimal':round(mean('price'),4),'observed_ROI':round(100*mean('real_U'),3),'reference_1.95_ROI':round(100*mean('ref_U'),3),'win_stake_fraction_pct':round(100*mean('won_fraction'),3),'loss_stake_fraction_pct':round(100*mean('lost_fraction'),3),'price_contribution_pct':round(100*(mean('real_U')-mean('ref_U')),3)}
out={'description':'1.95 price is a counterfactual normalization for outcome-vs-price attribution only, no selection and not a real market quote or new strategy rule. Groups remain fully included. League composition comparison is descriptive and does not establish causality.','groups':{}}
for g,z in G.items():
 era={'2019-2023':[r for r in z if r['year']<=2023],'2024-2025':[r for r in z if 2024<=r['year']<=2025],'2026':[r for r in z if r['year']==2026]}
 out['groups'][g]={k:st(v) for k,v in era.items()}
 out['groups'][g]['matched_count']=len(z)
 print('PRICE_OUTCOME',g,out['groups'][g],flush=True)
# Descriptive B common-league decomposition comparing 2019-23 and 2024-26.
early=collections.defaultdict(list);late=collections.defaultdict(list)
for r in G['B']:(early if r['year']<=2023 else late)[r['league']].append(r)
common=set(early)&set(late)
E=[r for k in common for r in early[k]];L=[r for k in common for r in late[k]]
old_rates={k:sum(r['real_U'] for r in early[k])/len(early[k]) for k in common}
new_rates={k:sum(r['real_U'] for r in late[k])/len(late[k]) for k in common}
old=100*sum(r['real_U'] for r in E)/len(E);new=100*sum(r['real_U'] for r in L)/len(L)
counter=100*sum(old_rates[k]*len(late[k]) for k in common)/len(L)
out['B_common_league_mix']={'common_leagues':len(common),'early_n':len(E),'later_n':len(L),'early_roi':round(old,3),'later_ROI':round(new,3),'early_ROI_reweighted_to_late_league_mix':round(counter,3),'composition_only_change_pp':round(counter-old,3),'within_league_residual_pp':round(new-counter,3),'excluded_from_overlap_comparison_but_retained':{'early':len(G['B'])-len(E)-len([r for r in G['B'] if r['year']>=2024]),'later':len([r for r in G['B'] if r['year']>=2024])-len(L)}}
print('COMMON_LEAGUES',out['B_common_league_mix'],flush=True)
(P/'m8_late_6to1_path_price_outcome_league_decomp_20261114.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
