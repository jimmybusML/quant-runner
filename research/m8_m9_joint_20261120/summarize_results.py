#!/usr/bin/env python3
import collections,datetime as dt,json
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path(__file__).parent; ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=[json.loads(x) for x in (P/'m9_reconstruction_m8_universe.jsonl').open()]
coverage=json.loads((P/'coverage_audit.json').read_text())
mem=[json.loads(x) for x in (ROOT/'m8_foundation_20261115/historical_membership.jsonl').open()]
feat={json.loads(x)['fid']:json.loads(x) for x in (ROOT/'m8_independent_score_strength_20261114.jsonl').open()}
path={json.loads(x)['fid']:json.loads(x) for x in (ROOT/'m8_late_full_path_water_features_20261114.jsonl').open()}
for name in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
 p=ROOT/name
 if p.exists():
  for line in p.open():
   r=json.loads(line);r={**r,**(r.get('score_row') or {})};fid=str(r.get('fid',''))
   if fid:path[fid]={**path.get(fid,{}),**r}
ST=['FULL_WIN','HALF_WIN','PUSH','HALF_LOSS','FULL_LOSS']
def stats(a,key='pnl'):
 if not a:return {'n':0,'unique_fids':0,'win':0,'half_win':0,'push':0,'half_loss':0,'loss':0,'net_U':0,'ROI_pct':None,'max_drawdown_U':0}
 pnl=lambda r:float(r[key]) if key in r else float(r.get('m9_pnl',0))
 n=len(a); u=sum(pnl(r) for r in a); counts=collections.Counter(r.get('state',r.get('m9_state')) for r in a)
 equity=peak=dd=0
 for r in sorted(a,key=lambda r:(r['kickoff_utc'],r['fid'])):
  equity+=pnl(r);peak=max(peak,equity);dd=max(dd,peak-equity)
 return {'n':n,'unique_fids':len({r['fid'] for r in a}),'win':counts['FULL_WIN'],'half_win':counts['HALF_WIN'],'push':counts['PUSH'],'half_loss':counts['HALF_LOSS'],'loss':counts['FULL_LOSS'],'net_U':round(u,6),'ROI_pct':round(100*u/n,6),'max_drawdown_U':round(dd,6)}
def recalc_m8():
 out=[];amb=0
 for m in mem:
  f={**path.get(m['fid'],{}),**feat.get(m['fid'],{})}
  side=f.get('side') or ('home' if abs(float(m['pnl'])-float(f['end_home_U']))<1e-7 else 'away' if abs(float(m['pnl'])-float(f['end_away_U']))<1e-7 else None)
  if side is None:amb+=1;continue
  try:state,pnl=settle_score('AH',float(f['end_line']),side,int(f['hg']),int(f['ag']),float(f['home_price'] if side=='home' else f['away_price']))
  except Exception:amb+=1;continue
  out.append({'fid':m['fid'],'kickoff_utc':f['ko'],'season_year':int(m['year']),'cohort':m['cohort'],'pnl':float(m['pnl']),'state':state,'side':side})
 return out,amb
m8,amb=recalc_m8();allm9=rows;inside=[r for r in rows if r['is_m8_member']];outside=[r for r in rows if not r['is_m8_member']]
m8common=[r for r in inside if r['m8_side']]
same=[r for r in m8common if r['m8_side']==r['m9_side']];opposite=[r for r in m8common if r['m8_side']!=r['m9_side']]
# Category evidence uses common line, odds and FT for both predictions.
m8hit_m9miss=[r for r in m8common if r['m8_pnl_repriced_same_Crown_contract']>0 and r['m9_pnl']<0]
m9hit_m8miss=[r for r in m8common if r['m9_pnl']>0 and r['m8_pnl_repriced_same_Crown_contract']<0]
def custom(entries):
 if not entries:return {'orders':0,'unique_fids':0,'win':0,'half_win':0,'push':0,'half_loss':0,'loss':0,'net_U':0,'ROI_pct':None,'max_drawdown_U':0}
 equity=peak=dd=0
 for _,date,fid,pnl,state in sorted(entries,key=lambda x:(x[1],x[2],x[0])):
  equity+=pnl;peak=max(peak,equity);dd=max(dd,peak-equity)
 c=collections.Counter(x[4] for x in entries);u=sum(x[3] for x in entries)
 return {'orders':len(entries),'unique_fids':len({x[2] for x in entries}),'win':c['FULL_WIN'],'half_win':c['HALF_WIN'],'push':c['PUSH'],'half_loss':c['HALF_LOSS'],'loss':c['FULL_LOSS'],'net_U':round(u,6),'ROI_pct':round(100*u/len(entries),6),'max_drawdown_U':round(dd,6)}
# Simple merge means both signals are placed on overlapping FIDs; protected union retains M8 on every original FID.
simple_entries=[('m8',r['kickoff_utc'],r['fid'],r['pnl'],r['state']) for r in m8]+[('m9',r['kickoff_utc'],r['fid'],r['m9_pnl'],r['m9_state']) for r in allm9]
member_map={r['fid']:r for r in m8}
protect_entries=[('m8',r['kickoff_utc'],r['fid'],r['pnl'],r['state']) for r in m8]
protect_entries += [('m9',r['kickoff_utc'],r['fid'],r['m9_pnl'],r['m9_state']) for r in outside]
annual={}; years=sorted({r['season_year'] for r in allm9}|{r['season_year'] for r in m8})
for y in years:
 a=[r for r in allm9 if r['season_year']==y];b=[r for r in outside if r['season_year']==y];c=[r for r in m8 if r['season_year']==y]
 annual[str(y)]={'m8_frozen':stats(c),'m9_independent':stats(a),'m9_outside_m8_increment':stats(b),'simple_merged_orders':custom([e for e in simple_entries if dt.date.fromisoformat(e[1][:10]).year==y]),'unique_fid_protected_union':custom([e for e in protect_entries if dt.date.fromisoformat(e[1][:10]).year==y])}
weekly=collections.defaultdict(lambda:{'m8':[],'m9':[],'m9_increment':[]})
for kind,arr in [('m8',m8),('m9',allm9),('m9_increment',outside)]:
 for r in arr:
  d=dt.date.fromisoformat(r['kickoff_utc'][:10]);y,w,_=d.isocalendar();weekly[f'{y}-W{w:02d}'][kind].append(r)
weekly={k:{kind:stats(v) for kind,v in groups.items()} for k,groups in sorted(weekly.items())}
for kind,entries in [('simple_merged_orders',simple_entries),('unique_fid_protected_union',protect_entries)]:
 weekly_entries=collections.defaultdict(list)
 for e in entries:
  d=dt.date.fromisoformat(e[1][:10]);y,w,_=d.isocalendar();key=f'{y}-W{w:02d}';weekly_entries[key].append(e)
 for key,entries_for_week in weekly_entries.items():weekly.setdefault(key,{})[kind]=custom(entries_for_week)
cohorts={}
for g in ('base','A','B','C','D','E','F','G'):
 z=[r for r in inside if r.get('m8_cohort')==g]; agree=[r for r in z if r['m8_side']==r['m9_side']];disagree=[r for r in z if r['m8_side']!=r['m9_side']]
 cohorts[g]={'n_m8_members_total':sum(r['cohort']==g for r in mem),'m9_overlap_n':len(z),'m9_overlap':stats(z),'m8_common_contract_net_U':round(sum(r['m8_pnl_repriced_same_Crown_contract'] for r in z),6),'same_direction_n':len(agree),'same_direction_m9_net_U':round(sum(r['m9_pnl'] for r in agree),6),'opposite_direction_n':len(disagree),'opposite_direction_m9_net_U':round(sum(r['m9_pnl'] for r in disagree),6)}
summary={'m8_frozen_independent':stats(m8),'m8_direction_unresolved_n':amb,'m8_frozen_membership_n':len(mem),'m9_independent':stats(allm9),'m9_on_m8_overlap':stats(inside),'m9_outside_m8_increment':stats(outside),'m8_overlap_same_Crown_contract_repriced':{'n':len(m8common),'m8':round(sum(r['m8_pnl_repriced_same_Crown_contract'] for r in m8common),6),'m9':round(sum(r['m9_pnl'] for r in m8common),6)},'same_direction':{'n':len(same),'m9':stats(same),'m8_net_U':round(sum(r['m8_pnl_repriced_same_Crown_contract'] for r in same),6)},'opposite_direction':{'n':len(opposite),'m9':stats(opposite),'m8_net_U':round(sum(r['m8_pnl_repriced_same_Crown_contract'] for r in opposite),6)},'m8_hit_m9_miss':{'n':len(m8hit_m9miss),'m9_net_U':round(sum(r['m9_pnl'] for r in m8hit_m9miss),6)},'m9_hit_m8_miss':{'n':len(m9hit_m8miss),'m9_net_U':round(sum(r['m9_pnl'] for r in m9hit_m8miss),6)},'m8_cohort_attribution':cohorts,'simple_merged_orders_allow_overlap':custom(simple_entries),'unique_fid_union_keep_m8_order_on_overlap':custom(protect_entries),'unique_m9_fids_outside_m8':len({r['fid'] for r in outside}),'true_pregame_http_receipts_in_historical_reconstruction':sum(bool(r['crown_prospective_observation']) for r in allm9),'annual':annual,'weekly':weekly,'formal_M9_TG_sent_events':coverage.get('formal_m9_event_counts_at_completion',{}).get('M9_TG_SENT',0),'formal_M9_formal_event_counts':coverage.get('formal_m9_event_counts_at_completion',{}),'training_protocol':'Per-league UTC monthly model vintage; fit at the earliest target kickoff in each month using all complete results before that cutoff. Same-month later results are not used.','max_drawdown_method':'Cumulative 1U PnL drawdown in kickoff order, FID tie-break within kickoff timestamp.'}
(P/'results_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(P/'annual_weekly.json').write_text(json.dumps({'annual':annual,'weekly':weekly},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('annual','weekly')},ensure_ascii=False,indent=2))
