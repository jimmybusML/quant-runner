#!/usr/bin/env python3
"""Independent raw Crown FID, quote-time, F-side, and AH cashflow verification."""
import collections,datetime as dt,gzip,hashlib,json,math,pathlib
HERE=pathlib.Path(__file__).resolve().parent;ROOT=pathlib.Path(__file__).resolve().parents[4]
LEDGER=ROOT/'research/m8_m9_group_independent_20261120/exact_rule_cross_league/exact_rule_cross_league_orders.jsonl.gz'
FROZEN=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
SUMMARY=HERE/'f_group_market_mechanism_summary.json'
def parse(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 return x.astimezone(dt.timezone.utc) if x.tzinfo else x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc)
def settle(line,side,hg,ag,odds):
 line=float(line)*(1 if side=='home' else -1);margin=int(hg)-int(ag) if side=='home' else int(ag)-int(hg)
 legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 x=[float(odds)-1 if margin+z>1e-9 else -1. if margin+z< -1e-9 else 0. for z in legs]
 return sum(x)/len(x),('full_win' if all(v>0 for v in x) else 'half_win' if any(v>0 for v in x) else 'push' if all(v==0 for v in x) else 'half_loss' if any(v==0 for v in x) else 'full_loss')
def main():
 summary=json.loads(SUMMARY.read_text());base=[json.loads(s) for s in gzip.open(LEDGER,'rt') if s.strip()];rows=[r for r in base if r['group']=='F'];frozen={str(json.loads(s).get('fid') or json.loads(s).get('match_id')) for s in FROZEN.open() if s.strip()};seen=set();issues=collections.Counter();selected_u=0.;fav_u=0.;opp_u=0.;byyear=collections.defaultdict(lambda:[0,0.,0.,0.]);
 if hashlib.sha256(LEDGER.read_bytes()).hexdigest()!=summary['inputs']['source_orders_sha256']:issues['ledger_sha_mismatch']+=1
 for r in rows:
  fid=str(r['fid'])
  if fid in seen:issues['duplicate_fid']+=1
  seen.add(fid)
  if fid in frozen:issues['frozen_overlap']+=1
  try:
   raw=pathlib.Path(r['source_file']).read_bytes()
   if hashlib.sha256(raw).hexdigest()!=r['response_sha256']:issues['raw_sha_mismatch']+=1;continue
   fix=next(x for x in json.loads(raw)['data'] if str(x['id'])==fid)
   if (str(fix.get('h'))!=r['home'] or str(fix.get('a'))!=r['away'] or str(fix.get('l_id'))!=str(r['league_id']) or [int(fix['hg']),int(fix['ag'])]!=[int(r['FT_home']),int(r['FT_away'])]):issues['identity_or_ft_mismatch']+=1;continue
   ko=parse(fix['start']);crown=next(x for x in fix['bookmakers'] if x.get('slug')=='crown');q=[]
   for ix,z in enumerate(crown.get('asian_list') or []):
    try:
     t=parse(z[4]);line,ho,ao=map(float,z[1:4])
     if t<ko and ho>1 and ao>1 and abs(line*4-round(line*4))<1e-8:q.append((t,ix,line,ho,ao))
    except Exception:continue
   q.sort(key=lambda x:(x[0],x[1]));horizon=[]
   for h,field in ((6,'T6_source_quote_utc'),(3,'T3_source_quote_utc'),(1,'T1_source_quote_utc')):
    cut=ko-dt.timedelta(hours=h);eligible=[z for z in q if z[0]<=cut]
    if not eligible:raise ValueError('missing horizon')
    z=eligible[-1]
    if abs((z[0]-parse(r[field])).total_seconds())>1:issues[f'T{h}_time_mismatch']+=1
    horizon.append(z)
   h6,h3,h1=horizon
   if any(abs(z[2]-float(r['AH_line_home']))>1e-8 for z in horizon):issues['horizon_line_mismatch']+=1
   if abs(h1[3]-r['AH_home_odds'])>1e-8 or abs(h1[4]-r['AH_away_odds'])>1e-8:issues['T1_odds_mismatch']+=1
   share=lambda z:z[4]/(z[3]+z[4])
   a=share(h3)-share(h6);b=share(h1)-share(h3);net=share(h1)-share(h6)
   net_sign=1 if net>1e-9 else -1 if net< -1e-9 else 0
   a_sign=1 if a>1e-9 else -1 if a< -1e-9 else 0
   b_sign=1 if b>1e-9 else -1 if b< -1e-9 else 0
   side='home' if (net_sign or a_sign or b_sign)>0 else 'away'
   if side!=r['side']:issues['direction_mismatch']+=1
   if a_sign!=0 or b_sign==0 or (net_sign or a_sign or b_sign)!=b_sign:issues['frozen_F_sample_trigger_mismatch']+=1
   hu,hc=settle(r['AH_line_home'],'home',r['FT_home'],r['FT_away'],r['AH_home_odds']);au,ac=settle(r['AH_line_home'],'away',r['FT_home'],r['FT_away'],r['AH_away_odds'])
   chosen,other=(hu,au) if side=='home' else (au,hu);fav='home' if h1[3]<h1[4] else 'away';fv=hu if fav=='home' else au
   expected_class=hc if side=='home' else ac
   if abs(chosen-r['net_u'])>1e-8 or expected_class!=r['settlement']:issues['AH_settlement_mismatch']+=1
   selected_u+=chosen;fav_u+=fv;opp_u+=other
   v=byyear[str(r['year'])];v[0]+=1;v[1]+=chosen;v[2]+=fv;v[3]+=other
  except Exception as e:issues['raw_error_'+type(e).__name__]+=1
 expected=summary['cohort']
 if len(rows)!=expected['n'] or abs(selected_u-expected['net_U'])>1e-6:issues['summary_candidate_mismatch']+=1
 comp=summary['fixed_cohort_comparators']
 if abs(fav_u-comp['T1_market_favorite_same_fids']['net_U'])>1e-6:issues['summary_favorite_mismatch']+=1
 if abs(opp_u-comp['opposite_of_frozen_F_side_same_fids']['net_U'])>1e-6:issues['summary_reverse_mismatch']+=1
 for y,vals in byyear.items():
  if len(vals)!=4:continue
  ex=summary['annual_comparators'][y]
  for i,k in ((1,'F_selected'),(2,'T1_favorite'),(3,'opposite_F')):
   if abs(vals[i]-ex[k]['net_U'])>1e-6:issues[f'year_{y}_{k}_mismatch']+=1
 result={'study':'M8 F-group independent raw quote and payout check','pass':not issues,'issues':dict(issues),'F_rows':len(rows),'unique_FIDs':len(seen),'raw_SHA_FT_identity_and_T6_T3_T1_contract_checked':len(rows)-issues['raw_sha_mismatch']-issues['identity_or_ft_mismatch'],'frozen_FID_intersection':len(seen&frozen),'candidate_net_U':round(selected_u,6),'T1_favorite_control_net_U':round(fav_u,6),'reverse_control_net_U':round(opp_u,6),'input_SHA256':{'ledger':hashlib.sha256(LEDGER.read_bytes()).hexdigest(),'summary':hashlib.sha256(SUMMARY.read_bytes()).hexdigest()}}
 (HERE/'f_group_market_mechanism_independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 if issues:raise SystemExit(1)
if __name__=='__main__':main()
