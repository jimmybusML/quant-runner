import json,collections,math,datetime,statistics
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_score_market_divergence_full_AH_20261114.py').read_text().split('out={}\n')[0])
grows=G[('shape_relation','reverted','agree')]
gids={(r['year'],r['fid']) for r in grows}
assert len(gids)==1213
oldrows=[{**r,'pnl':prior[(r['year'],r['fid'])][1],'cohort':prior[(r['year'],r['fid'])][0]} for r in A if (r['year'],r['fid']) in prior]
gnew=[{**r,'pnl':r['contra_U'],'cohort':'G'} for r in grows]
assert len(oldrows)+len(gnew)==8956
assert sum(r['year']==2026 for r in oldrows+gnew)==2070
reverted=[r for r in G[('remaining_all',)] if r['path_shape']=='reverted']
rest=[r for r in reverted if (r['year'],r['fid']) not in gids]
def sections(z,key):
 ans=summary(z,key)
 ans['annual']={str(y):st([r for r in z if r['year']==y],key) for y in range(2019,2027)}
 return ans
D=collections.defaultdict(list)
for i,r in enumerate(reverted):
 # final line equals original, so price changes can be compared directly.
 side='home' if direction(r['away_price']/(r['home_price']+r['away_price'])-r['start_away_price']/(r['start_home_price']+r['start_away_price']))=='home' else 'away'
 market=direction(r['away_price']/(r['home_price']+r['away_price'])-r['start_away_price']/(r['start_home_price']+r['start_away_price']))
 r['market_side']=market
 r['home_delta']=r['home_price']-r['start_home_price']
 r['away_delta']=r['away_price']-r['start_away_price']
 if market!='flat':
  opp='away' if market=='home' else 'home'
  r['market_U']=r['end_'+market+'_U'];r['market_opp_U']=r['end_'+opp+'_U']
  r['opp_price']=r[opp+'_price']
  r['opp_vs_mean']=r[opp+'_price_vs_timeavg']
 else:r['market_U']=r['market_opp_U']=None
 # these are descriptive bins, not any production filter.
 age=r['last_line_change_age_min'];duration=r['final_line_minutes']
 assert age is not None
 r['last_return_bin']='0-60m' if age<=60 else '60-120m' if age<=120 else '120-300m'
 r['at_start_line_duration_bin']='0-100m' if duration<=100 else '100-200m' if duration<=200 else '200-300m'
 r['excursion_bin']='0.25' if r['line_range']<=.25000001 else '0.5+' 
 r['change_count_bin']='two' if r['n_line_changes']==2 else 'three_or_more'
 r['market_disagree_bin']=r['relation']
 r['payout_vs_avg_bin']='above' if r.get('opp_vs_mean') is not None and r['opp_vs_mean']>1e-9 else 'below' if r.get('opp_vs_mean') is not None and r['opp_vs_mean']<-1e-9 else 'equal_or_na'
 cohort='G' if (r['year'],r['fid']) in gids else 'other'
 for field in ('last_return_bin','at_start_line_duration_bin','excursion_bin','change_count_bin','payout_vs_avg_bin','market_disagree_bin'):
  D[(cohort,field,r[field])].append(r)
 if cohort=='other':
  D[(cohort,'relation_x_return',r['relation']+'|'+r['last_return_bin'])].append(r)
  D[(cohort,'relation_x_count',r['relation']+'|'+r['change_count_bin'])].append(r)
  D[(cohort,'relation_x_range',r['relation']+'|'+r['excursion_bin'])].append(r)
out={'scope':'Crown 2019–2026 T6-T1 full path; previous eight research cohorts preserved; descriptive bins are not a production selection rule. G membership exactly reconstructed.','coverage':{'all_reverted_outside_previous7':len(reverted),'G':len(grows),'other_reverted':len(rest)},'G_diagnostics':{},'other_diagnostics':{}}
for (c,k,v),z in sorted(D.items()):
 vals={key:sections(z,key) for key in ('contra_U','ind_U')}
 if c=='G':out['G_diagnostics'][k+'|'+v]=vals
 else:out['other_diagnostics'][k+'|'+v]=vals
 if c=='G':print('G',k,v,{h:vals['contra_U'][h] for h in ('2019-23','2024-25','2026')},flush=True)
 elif all(vals['contra_U'][h]['ROI'] is not None and vals['contra_U'][h]['ROI']>0 for h in ('2019-23','2024-25','2026')) or all(vals['ind_U'][h]['ROI'] is not None and vals['ind_U'][h]['ROI']>0 for h in ('2019-23','2024-25','2026')):
  print('OTHER_POSITIVE',k,v,{f:{h:vals[f][h] for h in ('2019-23','2024-25','2026')} for f in vals},flush=True)
print('COVERAGE',out['coverage'],'REST',sections(rest,'ind_U'),sections(rest,'contra_U'),flush=True)
# payout decomposition all G, by era; reference payout only diagnosis
for r in grows:
 p=r['opp_price'];u=r['contra_U'];r['reference_U']=u/(p-1)*.95 if u>0 else u
out['G_payout']={}
for k,z in [('2019-23',[r for r in grows if era(r)=='2019-23']),('2024-25',[r for r in grows if era(r)=='2024-25']),('2026',[r for r in grows if era(r)=='2026'])]:
 out['G_payout'][k]={'market_odds_mean':round(statistics.mean(r['opp_price'] for r in z),4),'real':st(z,'contra_U'),'reference_1.95':st(z,'reference_U')}
print('PAYOUT',out['G_payout'],flush=True)
# Learn side in a fixed partition on 2019–23, keep frozen across 2024–25 and 2026.
# Every group with earlier data predicts one side, including negative training means.
out['chronological']={}
for groupfields in [('relation',),('relation','last_return_bin'),('relation','excursion_bin'),('relation','change_count_bin')]:
 buckets=collections.defaultdict(list)
 for r in rest:buckets[tuple(r[k] for k in groupfields)].append(r)
 chosen=[];unseen=[]
 for k,z in buckets.items():
  tr=[r for r in z if r['year']<=2023]
  if not tr:unseen.extend(z);continue
  side=max(('ind_U','contra_U'),key=lambda key:sum(r[key] for r in tr))
  learned=statistics.mean(r[side] for r in tr)
  chosen.extend({**r,'pnl':r[side],'train_mean':learned} for r in z)
 name='|'.join(groupfields)
 out['chronological'][name]={'all':sections(chosen,'pnl'),'training_positive_research':sections([r for r in chosen if r['train_mean']>0],'pnl'),'unseen':dict(collections.Counter(era(r) for r in unseen))}
 print('CHRONO',name,out['chronological'][name]['all'],out['chronological'][name]['training_positive_research'],flush=True)
# retain exact rows for candidate reproduction; no source raw prices posted.
(P/'m8_reversion_duration_explore_20261115.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
(P/'m8_reversion_duration_explore_20261115.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in reverted))
