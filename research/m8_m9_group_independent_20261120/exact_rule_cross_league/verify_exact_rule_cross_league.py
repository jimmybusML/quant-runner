#!/usr/bin/env python3
"""Independent raw Crown/FT and Asian settlement audit of cross-league ledger."""
import collections,datetime as dt,gzip,hashlib,json,math,pathlib,sqlite3,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
SCHEDULE=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl')
FOUNDATION=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
def sha(b):return hashlib.sha256(b).hexdigest()
def parse_dt(s):
 x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 if x.tzinfo:return x.astimezone(dt.timezone.utc)
 return x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc)
def settle_ah_independent(line,side,hg,ag,price):
 """Independent equal-leg AH settlement, intentionally separate from project helper."""
 line=float(line);price=float(price)
 if abs(line*4-round(line*4))>1e-8 or price<=1:raise ValueError('invalid AH contract')
 signed=line if side=='home' else -line
 margin=int(hg)-int(ag) if side=='home' else int(ag)-int(hg)
 if abs(signed*2-round(signed*2))<=1e-8:legs=[signed]
 else:legs=[math.floor(signed*2)/2,math.ceil(signed*2)/2]
 outcomes=[]
 for leg in legs:
  x=margin+leg
  outcomes.append(price-1 if x>1e-9 else -1.0 if x< -1e-9 else 0.0)
 pnl=sum(outcomes)/len(outcomes)
 if all(x>0 for x in outcomes):state='full_win'
 elif any(x>0 for x in outcomes):state='half_win'
 elif all(x==0 for x in outcomes):state='push'
 elif any(x==0 for x in outcomes):state='half_loss'
 else:state='full_loss'
 return state,pnl
def main():
 s=json.load(open(OUT/'exact_rule_cross_league_summary.json'))
 sched={str(x['match_id']):x for x in map(json.loads,open(SCHEDULE))}
 old=set(json.loads(x)['fid'] for x in open(FOUNDATION))
 rows=[json.loads(x) for x in gzip.open(OUT/'exact_rule_cross_league_orders.jsonl.gz','rt')]
 cov=[json.loads(x) for x in open(OUT/'exact_rule_cross_league_coverage.jsonl')]
 covj={x['fid']:x for x in cov};seen=set();issues=collections.Counter();bygroup=collections.defaultdict(list);checks=[]
 for r in rows:
  fid=str(r['fid'])
  if fid in seen:issues['duplicate_order_fid']+=1
  seen.add(fid)
  if fid in old:issues['frozen_overlap']+=1
  q=sched.get(fid)
  if not q:issues['no_schedule_FID']+=1;continue
  if str(q['league_id']) in s['frozen_rules']['old49_provider_league_ids']:issues['inside_original49']+=1
  try:
   if (str(q['home']),str(q['away']),int(q['home_goals']),int(q['away_goals']))!=(r['home'],r['away'],r['FT_home'],r['FT_away']):issues['schedule_identity_or_FT_mismatch']+=1
   if str(q['kickoff_source_local'])!=r['kickoff_beijing']:issues['kickoff_local_mismatch']+=1
   bodyb=pathlib.Path(r['source_file']).read_bytes()
   if sha(bodyb)!=r['response_sha256']:issues['raw_sha_mismatch']+=1;continue
   fixture=next(x for x in json.loads(bodyb)['data'] if str(x['id'])==fid)
   if str(fixture['l_id'])!=str(q['league_id']) or int(fixture['hg'])!=r['FT_home'] or int(fixture['ag'])!=r['FT_away'] or parse_dt(fixture['start'])!=parse_dt(q['kickoff_source_local']):issues['raw_fixture_identity_FT_mismatch']+=1
   if str(fixture.get('h'))!=r['home'] or str(fixture.get('a'))!=r['away']:issues['raw_team_name_mismatch']+=1
   crown=next(b for b in fixture['bookmakers'] if b.get('slug')=='crown')
   cutoff=parse_dt(q['kickoff_source_local'])-dt.timedelta(hours=1)
   qs=[]
   for item in crown.get('asian_list') or []:
    try:
     t=parse_dt(item[4]);line,ho,ao=map(float,item[1:4])
     if t<parse_dt(q['kickoff_source_local']) and ho>1 and ao>1 and abs(line*4-round(line*4))<1e-8:qs.append((t,line,ho,ao))
    except Exception:pass
   qs.sort(key=lambda z:z[0]);at=[x for x in qs if x[0]<=cutoff]
   if not at:issues['missing_T1_or_prior_quote']+=1;continue
   selected=at[-1]
   if (selected[0].isoformat(),selected[1],selected[2],selected[3])!=(r['quote_source_at_utc'],r['AH_line_home'],r['AH_home_odds'],r['AH_away_odds']):issues['T1_raw_quote_mismatch']+=1
   # Recompute every Asian line settlement from the raw Crown line, odds and FT.
   state,pnl=settle_ah_independent(selected[1],r['side'],r['FT_home'],r['FT_away'],selected[2] if r['side']=='home' else selected[3])
   if state!=r['settlement']:issues['settlement_state_mismatch']+=1
   if abs(pnl-r['net_u'])>1e-9:issues['settlement_pnl_mismatch']+=1
   if not (parse_dt(r['T6_source_quote_utc'])<=parse_dt(r['T3_source_quote_utc'])<=parse_dt(r['T1_source_quote_utc'])<parse_dt(q['kickoff_source_local'])):issues['horizon_order_mismatch']+=1
   if covj[fid]['status']!='complete_T6_T3_T1_path':issues['order_without_complete_path']+=1
   bygroup[r['group']].append(pnl)
  except Exception as e:issues['row_exception_'+type(e).__name__]+=1
  checks.append(fid)
 # Ledger count and U agreement with the independently recomputed raw-source cashflows.
 for g in s['frozen_rules']['groups']:
  expected=s['groups'][g]['assigned']; actual=bygroup[g]
  if len(actual)!=expected['n']:issues['summary_group_n_'+g]+=1
  if abs(sum(actual)-expected['net_U'])>1e-6:issues['summary_group_U_'+g]+=1
 if len(seen)!=s['results']['new_incremental']['n']:issues['summary_union_n']+=1
 if abs(sum(x['net_u'] for x in rows)-s['results']['new_incremental']['net_U'])>1e-6:issues['summary_union_U']+=1
 if sum(s['groups'][g]['assigned']['n'] for g in s['frozen_rules']['groups'])!=len(rows):issues['group_union_n']+=1
 if abs(sum(s['groups'][g]['assigned']['net_U'] for g in s['frozen_rules']['groups'])-sum(x['net_u'] for x in rows))>1e-6:issues['group_union_U']+=1
 combined=s['results']['combined_original8_plus_new']
 if combined['n']!=len(old)+len(rows):issues['summary_combined_n']+=1
 if abs(combined['net_U']-(236.015+sum(x['net_u'] for x in rows)))>1e-6:issues['summary_combined_U']+=1
 # There must be no live HTTP capture for any outside-49 FID; this prevents retrospective prices being called receipts.
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True);outside=[fid for fid,x in sched.items() if fid in covj and x['league_id'] not in s['frozen_rules']['old49_provider_league_ids']]
 live=[]
 for j in range(0,len(outside),700):
  chunk=outside[j:j+700];m=','.join('?' for _ in chunk)
  live.extend(x[0] for x in cx.execute(f"select distinct fixture_id from capture where capture_mode='live' and fixture_id in ({m})",chunk))
 cx.close()
 if live:issues['live_capture_outside49_note_count']+=len(live)
 result={'study':'M8_EXACT_FROZEN_RULE_CROSS_LEAGUE_RAW_SETTLEMENT_AUDIT','checked_orders':len(rows),'checked_unique_fids':len(seen),'independent_raw_quote_and_FT_rechecks':len(checks),'outside49_fids_checked_for_live_capture':len(outside),'live_capture_fids':len(live),'issues':dict(issues),'pass':not issues}
 (OUT/'exact_rule_cross_league_independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
 if issues:raise SystemExit(1)
if __name__=='__main__':main()
