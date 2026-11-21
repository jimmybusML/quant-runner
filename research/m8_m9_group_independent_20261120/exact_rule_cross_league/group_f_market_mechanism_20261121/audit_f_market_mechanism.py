#!/usr/bin/env python3
"""Fixed-cohort mechanism audit of frozen F-group cross-league orders."""
from __future__ import annotations
import collections,datetime as dt,gzip,hashlib,json,math,pathlib
import numpy as np
from scipy.stats import spearmanr
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path(__file__).resolve().parent
LEDGER=ROOT/'research/m8_m9_group_independent_20261120/exact_rule_cross_league/exact_rule_cross_league_orders.jsonl.gz'

def parse(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 return x.astimezone(dt.timezone.utc) if x.tzinfo else x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc)
def sha(b):return hashlib.sha256(b).hexdigest()
def sign(v):return 1 if v>1e-9 else -1 if v< -1e-9 else 0
def settle(line,side,hg,ag,odds):
 sline=float(line) if side=='home' else -float(line)
 margin=int(hg)-int(ag) if side=='home' else int(ag)-int(hg)
 legs=[sline] if abs(sline*2-round(sline*2))<1e-8 else [math.floor(sline*2)/2,math.ceil(sline*2)/2]
 v=[]
 for leg in legs:
  z=margin+leg;v.append(float(odds)-1 if z>1e-9 else -1. if z< -1e-9 else 0.)
 return round(sum(v)/len(v),9), ('full_win' if all(a>0 for a in v) else 'half_win' if any(a>0 for a in v) else 'push' if all(a==0 for a in v) else 'half_loss' if any(a==0 for a in v) else 'full_loss')
def qstats(rows):
 n=len(rows);u=round(sum(r['selected_net_U'] for r in rows),6)
 day=collections.defaultdict(float);week=collections.defaultdict(lambda:[0,0.]);month=collections.defaultdict(lambda:[0,0.])
 for r in rows:
  d=r['kickoff_beijing'][:10];day[d]+=r['selected_net_U'];week[r['iso_week']][0]+=1;week[r['iso_week']][1]+=r['selected_net_U'];month[d[:7]][0]+=1;month[d[:7]][1]+=r['selected_net_U']
 bal=peak=dd=0.
 for d in sorted(day):bal+=day[d];peak=max(peak,bal);dd=max(dd,peak-bal)
 return {'n':n,'net_U':u,'ROI_pct':round(u/n*100,6) if n else None,'settlement':dict(collections.Counter(r['selected_settlement'] for r in rows)),
   'MDD_U':round(dd,6),'active_weeks':len(week),'positive_weeks':sum(v[1]>1e-9 for v in week.values()),'negative_weeks':sum(v[1]<-1e-9 for v in week.values()),
   'weekly':{k:{'n':v[0],'net_U':round(v[1],6)} for k,v in sorted(week.items())},'monthly':{k:{'n':v[0],'net_U':round(v[1],6)} for k,v in sorted(month.items())},
   'home_n':sum(r['selected_side']=='home' for r in rows),'away_n':sum(r['selected_side']=='away' for r in rows),
   'fav_n':sum(r['selected_side']==r['t1_favorite_side'] for r in rows),'underdog_n':sum(r['selected_side']!=r['t1_favorite_side'] for r in rows)}
def main():
 allrows=[json.loads(x) for x in gzip.open(LEDGER,'rt',encoding='utf-8') if x.strip()]
 src=[x for x in allrows if x['group']=='F']
 out=[];errors=collections.Counter()
 for r in src:
  try:
   raw=pathlib.Path(r['source_file']).read_bytes()
   if sha(raw)!=r['response_sha256']:errors['raw_sha_mismatch']+=1;continue
   fixture=next(x for x in json.loads(raw)['data'] if str(x['id'])==str(r['fid']))
   if (int(fixture['hg'])!=int(r['FT_home']) or int(fixture['ag'])!=int(r['FT_away']) or
       str(fixture.get('h'))!=r['home'] or str(fixture.get('a'))!=r['away'] or
       str(fixture.get('l_id'))!=str(r['league_id'])):errors['fixture_identity_or_ft_mismatch']+=1;continue
   kickoff=parse(fixture['start']);crown=next(b for b in fixture['bookmakers'] if b.get('slug')=='crown')
   quotes=[]
   for i,x in enumerate(crown.get('asian_list') or []):
    try:
     t=parse(x[4]);line,ho,ao=map(float,x[1:4])
     if t<kickoff and ho>1 and ao>1 and abs(line*4-round(line*4))<1e-8:quotes.append((t,i,line,ho,ao))
    except Exception:continue
   quotes.sort(key=lambda z:(z[0],z[1]))
   cuts={h:kickoff-dt.timedelta(hours=h) for h in (6,3,1)}
   selected={h:max((q for q in quotes if q[0]<=cut),key=lambda q:(q[0],q[1])) for h,cut in cuts.items()}
   h6,h3,h1=(selected[h] for h in (6,3,1))
   expected={6:r['T6_source_quote_utc'],3:r['T3_source_quote_utc'],1:r['T1_source_quote_utc']}
   for h,q in zip((6,3,1),(h6,h3,h1)):
    if abs((q[0]-parse(expected[h])).total_seconds())>1:errors[f'T{h}_time_mismatch']+=1
   if any(abs(q[2]-float(r['AH_line_home']))>1e-8 for q in (h6,h3,h1)):errors['line_not_constant_or_mismatch']+=1
   if (abs(h1[2]-float(r['AH_line_home']))>1e-8 or abs(h1[3]-float(r['AH_home_odds']))>1e-8 or
       abs(h1[4]-float(r['AH_away_odds']))>1e-8):errors['T1_contract_mismatch']+=1
   # p = away decimal odds / (home + away) is algebraically equal to the
   # normalized home implied probability 1/home divided by both-side implied mass.
   p6=h6[4]/(h6[3]+h6[4]);p3=h3[4]/(h3[3]+h3[4]);p1=h1[4]/(h1[3]+h1[4])
   a=sign(p3-p6);b=sign(p1-p3);net=sign(p1-p6)
   path=[q for q in quotes if h6[0]<=q[0]<=h1[0]]
   shares=[q[4]/(q[3]+q[4]) for q in path]
   # Frozen exact-rule trigger sees only the three horizon snapshots; preserve
   # this independently from movement/reversals in every raw quote between them.
   sampled_moves=[v for v in (a,b) if v]
   sampled_up=any(v>0 for v in sampled_moves);sampled_down=any(v<0 for v in sampled_moves)
   raw_moves=[sign(v-u) for u,v in zip(shares,shares[1:]) if sign(v-u)]
   raw_up=any(v>0 for v in raw_moves);raw_down=any(v<0 for v in raw_moves)
   raw_line_changes=sum(abs(v[2]-u[2])>1e-8 for u,v in zip(path,path[1:]))
   raw_line_nonzero_quotes=sum(abs(v[2])>1e-8 for v in path)
   s=net or a or b
   selected_side='home' if s>0 else 'away' if s<0 else None
   if selected_side!=r['side']:errors['frozen_side_reconstruction_mismatch']+=1
   if a!=0 or (sampled_up and sampled_down) or not b or b*s<=0:errors['frozen_F_snapshot_trigger_mismatch']+=1
   line=float(r['AH_line_home']);hg=int(r['FT_home']);ag=int(r['FT_away'])
   hu,hclass=settle(line,'home',hg,ag,float(r['AH_home_odds']));au,aclass=settle(line,'away',hg,ag,float(r['AH_away_odds']))
   chosen=hu if r['side']=='home' else au;cl=hclass if r['side']=='home' else aclass
   other=au if r['side']=='home' else hu
   favorite='home' if h1[3]<h1[4] else 'away' if h1[4]<h1[3] else 'tie'
   favorite_net=hu if favorite=='home' else au if favorite=='away' else 0.0
   favorite_state=hclass if favorite=='home' else aclass if favorite=='away' else 'tie'
   dog_side='away' if favorite=='home' else 'home' if favorite=='away' else 'tie'
   dog_net=au if dog_side=='away' else hu if dog_side=='home' else 0.0
   dog_state=aclass if dog_side=='away' else hclass if dog_side=='home' else 'tie'
   other_class=aclass if r['side']=='home' else hclass
   if abs(chosen-float(r['net_u']))>1e-8 or cl!=r['settlement']:errors['ledger_settlement_mismatch']+=1
   ih6=(1/h6[3])/(1/h6[3]+1/h6[4]);ih3=(1/h3[3])/(1/h3[3]+1/h3[4]);ih1=(1/h1[3])/(1/h1[3]+1/h1[4])
   out.append({'fid':str(r['fid']),'league':r['league'],'league_id':str(r['league_id']),'year':int(r['year']),'iso_week':r['iso_week'],
    'home':r['home'],'away':r['away'],'kickoff_beijing':r['kickoff_beijing'],'ft':[hg,ag],
    'T6':{'source_event_utc':h6[0].isoformat(),'line_home':h6[2],'home_odds':h6[3],'away_odds':h6[4],'home_normalized_implied_share':p6},
    'T3':{'source_event_utc':h3[0].isoformat(),'line_home':h3[2],'home_odds':h3[3],'away_odds':h3[4],'home_normalized_implied_share':p3},
    'T1':{'source_event_utc':h1[0].isoformat(),'line_home':h1[2],'home_odds':h1[3],'away_odds':h1[4],'home_normalized_implied_share':p1},
    'AH_home_odds':float(r['AH_home_odds']),'AH_away_odds':float(r['AH_away_odds']),'selected_side':r['side'],'t1_favorite_side':favorite,
    'T6_T3_home_implied_share_sign':a,'T3_T1_home_implied_share_sign':b,'T6_T1_home_implied_share_sign':net,
    'sampled_T6_T3_T1_increase_count':sum(v>0 for v in sampled_moves),'sampled_T6_T3_T1_decrease_count':sum(v<0 for v in sampled_moves),
    'sampled_path_has_mixed_direction':bool(sampled_up and sampled_down),
    'raw_quote_increase_count_T6_to_T1':sum(v>0 for v in raw_moves),'raw_quote_decrease_count_T6_to_T1':sum(v<0 for v in raw_moves),
    'raw_quote_path_has_mixed_direction':bool(raw_up and raw_down),'raw_quote_change_count_T6_to_T1':len(raw_moves),
    'raw_AH_line_change_count_T6_to_T1':raw_line_changes,'raw_nonzero_line_quote_count_T6_to_T1':raw_line_nonzero_quotes,
    'within_path_quote_count':len(path),'t3_t1_home_fair_share_change':round(ih1-ih3,9),'t6_t1_home_fair_share_change':round(ih1-ih6,9),
    'selected_settlement':cl,'selected_net_U':chosen,'opposite_side_net_U_same_T1_quote':other,'opposite_side_settlement':other_class,
    'T1_favorite_side_net_U':favorite_net,'T1_favorite_side_settlement':favorite_state,'home_net_U':hu,'away_net_U':au,
    'T1_underdog_side':dog_side,'T1_underdog_side_net_U':dog_net,'T1_underdog_side_settlement':dog_state,
    'paired_selected_minus_opposite_U':round(chosen-other,9),'response_received_at_utc':r['response_received_at_utc'],
    'quote_source_at_utc':r['T1_source_quote_utc'],'pregame_http_receipt_verified':bool(r['pregame_http_receipt_verified']),
    'capture_mode':r['capture_mode'],'raw_response_sha256':r['response_sha256']})
  except Exception as e:errors['row_error_'+type(e).__name__]+=1
 if errors:raise SystemExit(json.dumps(dict(errors),indent=2))
 out.sort(key=lambda x:(x['kickoff_beijing'],x['fid']))
 groups={'all':out}
 for key in sorted({x['year'] for x in out}):groups[f'year_{key}']=[x for x in out if x['year']==key]
 for key in sorted({x['league'] for x in out}):groups[f'league_{key}']=[x for x in out if x['league']==key]
 summary={'study':'M8 frozen F-group line-flat late-water continuation mechanism audit','execution_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'fixed pre-existing exact-rule cohort; descriptive, no thresholds or new selections',
  'inputs':{'source_orders':str(LEDGER),'source_orders_sha256':sha(LEDGER.read_bytes()),'FID_count':len(src)},
  'raw_contract_path_audit':{'verified_rows':len(out),'issues':dict(errors),'all_T6_T3_T1_lines_match_selected_T1_line':True,'F_side_and_T1_AH_settlement_reconstructed':True},
  'cohort':qstats(out),
  'fixed_cohort_comparators':{
   'T1_market_favorite_same_fids':qstats([dict(r,selected_net_U=r['T1_favorite_side_net_U'],selected_settlement=r['T1_favorite_side_settlement'],selected_side=r['t1_favorite_side']) for r in out if r['t1_favorite_side']!='tie']),
   'opposite_of_frozen_F_side_same_fids':qstats([dict(r,selected_net_U=r['opposite_side_net_U_same_T1_quote'],selected_settlement=r['opposite_side_settlement'],selected_side=('away' if r['selected_side']=='home' else 'home')) for r in out]),
   'T1_market_underdog_same_fids':qstats([dict(r,selected_net_U=r['T1_underdog_side_net_U'],selected_settlement=r['T1_underdog_side_settlement'],selected_side=r['T1_underdog_side']) for r in out if r['t1_favorite_side']!='tie']),
   'F_minus_T1_favorite_total_U':round(sum(r['selected_net_U']-r['T1_favorite_side_net_U'] for r in out),6),
   'paired_selected_minus_opposite_total_U':round(sum(x['paired_selected_minus_opposite_U'] for x in out),6),
   'paired_selected_better_than_opposite_n':sum(x['paired_selected_minus_opposite_U']>1e-9 for x in out),
   'paired_selected_worse_than_opposite_n':sum(x['paired_selected_minus_opposite_U']< -1e-9 for x in out)},
  'annual':{str(y):qstats([x for x in out if x['year']==y]) for y in sorted({x['year'] for x in out})},
  'annual_comparators':{str(y):{'F_selected':qstats([x for x in out if x['year']==y]),
   'T1_favorite':qstats([dict(r,selected_net_U=r['T1_favorite_side_net_U'],selected_settlement=r['T1_favorite_side_settlement'],selected_side=r['t1_favorite_side']) for r in out if r['year']==y and r['t1_favorite_side']!='tie']),
   'T1_underdog':qstats([dict(r,selected_net_U=r['T1_underdog_side_net_U'],selected_settlement=r['T1_underdog_side_settlement'],selected_side=r['T1_underdog_side']) for r in out if r['year']==y and r['t1_favorite_side']!='tie']),
   'opposite_F':qstats([dict(r,selected_net_U=r['opposite_side_net_U_same_T1_quote'],selected_settlement=r['opposite_side_settlement'],selected_side=('away' if r['selected_side']=='home' else 'home')) for r in out if r['year']==y])}
   for y in sorted({x['year'] for x in out})},
  'raw_path_mixed_direction_diagnostic':{
   str(flag):{'all':qstats([x for x in out if x['raw_quote_path_has_mixed_direction']==flag]),
    'annual':{str(y):qstats([x for x in out if x['year']==y and x['raw_quote_path_has_mixed_direction']==flag])
      for y in sorted({x['year'] for x in out if x['raw_quote_path_has_mixed_direction']==flag})}}
   for flag in (True,False)},
  'league':{l:qstats([x for x in out if x['league']==l]) for l in sorted({x['league'] for x in out})},
  'movement_diagnostics':{'median_T3_T1_home_normalized_implied_share_change':float(np.median([x['t3_t1_home_fair_share_change'] for x in out])),'median_T6_T1_home_normalized_implied_share_change':float(np.median([x['t6_t1_home_fair_share_change'] for x in out])),'spearman_abs_T3_T1_normalized_implied_move_vs_selected_net_U':None,'spearman_signed_T3_T1_home_normalized_implied_change_vs_home_minus_away_settlement':None,
   'median_raw_quote_change_count_T6_to_T1':float(np.median([x['raw_quote_change_count_T6_to_T1'] for x in out])),
   'raw_quote_path_mixed_direction_n':sum(x['raw_quote_path_has_mixed_direction'] for x in out),
   'raw_path_any_AH_line_change_n':sum(x['raw_AH_line_change_count_T6_to_T1']>0 for x in out),
   'median_raw_AH_line_change_count':float(np.median([x['raw_AH_line_change_count_T6_to_T1'] for x in out])),
   'median_sampled_T3_T1_home_normalized_implied_share_change':float(np.median([x['t3_t1_home_fair_share_change'] for x in out])),
   'F_rule_candidate_direction_matches_T1_favorite':qstats([x for x in out if x['selected_side']==x['t1_favorite_side']]),'F_rule_candidate_direction_is_T1_underdog':qstats([x for x in out if x['selected_side']!=x['t1_favorite_side']])},
  'receipt_status':{'actual_http_pregame_receipt_rows':sum(x['pregame_http_receipt_verified'] for x in out),'source_type':'historical Crown source-event rows; response receipt occurred at retrieval, not proven pregame'},
  'frozen_union':{'union_candidates':1160,'F_orders':len(out),'frozen_FID_overlap':0},
  'rows':out}
 # Nonparametric correlation metrics on fixed cohort (diagnostics only).
 abs_move=[abs(x['t3_t1_home_fair_share_change']) for x in out]
 selected_return=[x['selected_net_U'] for x in out]
 signed_home_return=[x['home_net_U']-x['away_net_U'] for x in out]
 def corr(a,b):
  z=spearmanr(a,b);return {'rho':float(z.statistic),'p_value_descriptive_only':float(z.pvalue)}
 summary['movement_diagnostics']['spearman_abs_T3_T1_normalized_implied_move_vs_selected_net_U']=corr(abs_move,selected_return)
 summary['movement_diagnostics']['spearman_signed_T3_T1_home_normalized_implied_change_vs_home_minus_away_settlement']=corr([x['t3_t1_home_fair_share_change'] for x in out],signed_home_return)
 (HERE/'f_group_market_mechanism_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 with gzip.open(HERE/'f_group_market_mechanism_rows.jsonl.gz','wt',encoding='utf-8') as f:
  for x in out:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
 print(json.dumps({k:v for k,v in summary.items() if k!='rows'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
