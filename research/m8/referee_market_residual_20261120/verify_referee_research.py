#!/usr/bin/env python3
"""Independent referee-study AH settlement, identity, time and raw Crown audit."""
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, sys, csv
from zoneinfo import ZoneInfo
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'research/m8/referee_market_residual_20261120'
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=pathlib.Path('/Users/mac/QuantAsiaDesk/data')
LEDGER=OUT/'referee_market_residual_per_fixture.jsonl.gz'
SUMMARY=OUT/'referee_market_residual_summary.json'
PATH=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=WORK/'m8_independent_score_strength_20261114.jsonl'
FOUNDATION=WORK/'m8_foundation_20261115/historical_membership.jsonl'
OLD=WORK/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
INDEX=DATA/'m5-crown-authorized/crown-response-index.jsonl'
GAMES=WORK/'m8_pregame_info_source_20261117/games.csv.gz'
MANAGER=ROOT/'research/m8/m8_prior_manager_turnover_20261117.py'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(p):
 with p.open(encoding='utf-8') as f:
  for l in f:
   if l.strip():yield json.loads(l)
def parse_dt(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 if x.tzinfo is None:x=x.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
 return x.astimezone(dt.timezone.utc)
def settle(line,side,gd,odds):
 # Independent expression: convert the selected side to its own goal margin,
 # then apply the AH handicap and split quarter lines into equal half-stakes.
 handicap=float(line) if side=='home' else -float(line)
 margin=int(gd) if side=='home' else -int(gd)
 q=round(handicap*4)
 if abs(handicap*4-q)>1e-8:raise ValueError('bad AH grid')
 legs=[handicap] if q%2==0 else [math.floor(handicap*2)/2,math.floor(handicap*2)/2+.5]
 pnl=[];labels=[]
 for leg in legs:
  z=margin+leg
  labels.append('W' if z>1e-9 else 'L' if z< -1e-9 else 'P')
  pnl.append(float(odds)-1 if z>1e-9 else -1. if z< -1e-9 else 0.)
 net=sum(pnl)/len(pnl)
 state=('full_'+('win' if net>0 else 'loss') if 'P' not in labels else 'push' if net==0 else 'half_'+('win' if net>0 else 'loss'))
 return state,net
def metric(rows,method):
 bets=[r for r in rows if r['methods'][method]['side'] is not None]
 n=len(bets);u=sum(float(r['methods'][method]['net_u']) for r in bets)
 daily=collections.defaultdict(float)
 for r in bets:daily[r['date']]+=float(r['methods'][method]['net_u'])
 cum=peak=mdd=0.
 for d in sorted(daily):cum+=daily[d];peak=max(peak,cum);mdd=max(mdd,peak-cum)
 return {'orders':n,'no_bet':len(rows)-n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(mdd,6)}
def main():
 rows=[json.loads(l) for l in gzip.open(LEDGER,'rt',encoding='utf-8')]
 summary=json.loads(SUMMARY.read_text())
 assert len(rows)==7081 and len({r['fid'] for r in rows})==len(rows)
 methods=list(summary['results']['outside_frozen_eight'])
 errors=collections.Counter(); examples=[]
 frozen={str(r['fid']) for r in read(FOUNDATION)}
 incr=[r for r in rows if r['year']>=2024 and not r['frozen_eight_overlap']]
 outside_overlap=sum(r['fid'] in frozen for r in incr)
 for r in rows:
  target=dt.date.fromisoformat(r['date'])-dt.timedelta(days=3)
  for key in ('ref_prior_max_date_365','comp_prior_max_date_365'):
   v=r.get(key)
   if v and dt.date.fromisoformat(v)>=target:errors['feature_lag_violation']+=1
  if r.get('ref_prior_n_365',0)==0 and r.get('ref_centered_residual_365_shrunk')!=0:errors['unseen_ref_not_zero']+=1
  for method in methods:
   m=r['methods'][method];side=m['side']
   if side is None:
    if m['settlement']!='no_bet' or abs(float(m['net_u']))>1e-10:errors['no_bet_ledger_mismatch']+=1
    continue
   odds=float(r['home_odds'] if side=='home' else r['away_odds'])
   state,u=settle(float(r['line']),side,int(r['gd']),odds)
   if state!=m['settlement'] or abs(u-float(m['net_u']))>1e-8:
    errors['settlement_mismatch']+=1
    if len(examples)<8:examples.append({'fid':r['fid'],'method':method,'expected':[state,u],'saved':[m['settlement'],m['net_u']]})
 # Confirm frozen disjointness and recalc outcome metrics from line ledger.
 frozen_baseline={str(x['fid']):x for x in read(FOUNDATION) if int(x['year']) in (2024,2025,2026)}
 for method in methods:
  got=metric(incr,method);exp=summary['results']['outside_frozen_eight'][method]
  for k in ('orders','no_bet','net_u','roi_pct','mdd_u'):
   if got[k]!=exp[k]:errors['summary_metric_'+method+'_'+k]+=1
  picked=[r for r in incr if r['methods'][method]['side'] is not None]
  picked_ids={r['fid'] for r in picked}
  if picked_ids&set(frozen_baseline):errors['candidate_frozen_overlap_'+method]+=1
  merged={f:{'date':str(x['date'])[:10],'net_u':float(x['pnl'])} for f,x in frozen_baseline.items()}
  merged.update({r['fid']:{'date':r['date'],'net_u':r['methods'][method]['net_u']} for r in picked})
  # Verify merged unique order count and net against published summary.
  m=sum(x['net_u'] for x in merged.values());n=len(merged);exp_m=summary['merged_with_frozen_eight_2024_2026'][method]['merged_unique_fid']
  if n!=exp_m['orders'] or abs(m-exp_m['net_u'])>1e-6:errors['merged_summary_'+method]+=1
 # Recreate the frozen Crown/TM identity bridge in read-only mode and confirm
 # target referee ID, game, score, date and competition against source games.csv.gz.
 src=MANAGER.read_text();marker='# Build historical coach timeline';ns={'__file__':str(MANAGER),'__name__':'m8_referee_independent_bridge'}
 exec(compile(src[:src.index(marker)],str(MANAGER)+'[independent bridge prefix]','exec'),ns)
 teammap=ns['teammap'];cm=ns['cm']
 game_rows={}
 with gzip.open(GAMES,'rt',encoding='utf-8') as f:
  for x in csv.DictReader(f):game_rows[str(x['game_id'])]=x
 for r in rows:
  g=game_rows.get(str(r['tm_game_id']))
  if not g:errors['tm_game_missing']+=1;continue
  if (str(g['home_club_id']),str(g['away_club_id']))!=(r['home_tm_id'],r['away_tm_id']):errors['tm_club_id_mismatch']+=1
  if (int(g['home_club_goals']),int(g['away_club_goals']))!=(int(r['hg']),int(r['ag'])):errors['tm_ft_mismatch']+=1
  if str(g['referee'])!=str(r['referee']):errors['tm_referee_name_mismatch']+=1
  if str(g['competition_id'])!=str(cm.get(str(r['league']))):errors['tm_competition_mismatch']+=1
  local=dt.date.fromisoformat(r['date']);tmdate=dt.date.fromisoformat(g['date'])
  if abs((local-tmdate).days)>1:errors['tm_date_mismatch']+=1
  if teammap.get((str(r['league']),str(r['home'])))!=r['home_tm_id'] or teammap.get((str(r['league']),str(r['away'])))!=r['away_tm_id']:errors['team_crosswalk_mismatch']+=1
 # Independently read original Crown HTTP/source response files and recalc latest T-1 quote.
 oldidx={str(x['fixture_id']):x for x in read(OLD)}; response_idx={str(x['match_id']):x for x in read(INDEX)}
 raw_counts=collections.Counter();quote_mismatch=[]
 for r in rows:
  fid=str(r['fid'])
  if fid in oldidx:
   meta=oldidx[fid];raw_path=pathlib.Path(meta['source_file']);expected=meta.get('raw_sha256')
  else:
   raw_path=DATA/'m5-crown-authorized/crown-responses'/f'{fid}.json';expected=response_idx.get(fid,{}).get('response_sha256')
  if not raw_path.is_file():raw_counts['raw_file_missing']+=1;continue
  b=raw_path.read_bytes();actual=hashlib.sha256(b).hexdigest()
  if expected and actual!=expected:raw_counts['raw_sha_mismatch']+=1;continue
  try:body=json.loads(b)
  except Exception:raw_counts['raw_json_error']+=1;continue
  matches=body.get('data');matches=matches if isinstance(matches,list) else [matches] if isinstance(matches,dict) else []
  m=next((x for x in matches if str(x.get('id'))==fid),None)
  if not m:raw_counts['fixture_missing']+=1;continue
  if (str(m.get('l_id')),str(m.get('h_id')),str(m.get('a_id'))) != (str(r['league']),str(r['home']),str(r['away'])):raw_counts['raw_fixture_identity_mismatch']+=1;continue
  if (int(m.get('hg',-999)),int(m.get('ag',-999)))!=(int(r['hg']),int(r['ag'])):raw_counts['raw_ft_mismatch']+=1;continue
  ko=parse_dt(m['start']);cutoff=ko-dt.timedelta(hours=1);bk=next((x for x in m.get('bookmakers',[]) if str(x.get('slug','')).lower()=='crown'),None)
  if not bk:raw_counts['crown_missing']+=1;continue
  qlist=[]
  for q in bk.get('asian_list') or []:
   try:
    t=parse_dt(q[4]);line,ho,ao=map(float,q[1:4])
    if t<=cutoff and ho>1 and ao>1:qlist.append((t,line,ho,ao))
   except (ValueError,TypeError,IndexError):continue
  if not qlist:raw_counts['t1_quote_missing']+=1;continue
  q=max(qlist,key=lambda z:z[0]);raw_counts['raw_quote_verified']+=1
  if any(abs(a-b)>1e-8 for a,b in zip(q[1:],(float(r['line']),float(r['home_odds']),float(r['away_odds'])))):
   raw_counts['t1_quote_mismatch']+=1
   if len(quote_mismatch)<10:quote_mismatch.append({'fid':fid,'ledger':[r['line'],r['home_odds'],r['away_odds']],'raw':[q[1],q[2],q[3]]})
 # Do not fail on absent archive source files silently: all candidate rows need verification.
 if outside_overlap:errors['outside_frozen_overlap']+=outside_overlap
 if raw_counts['raw_quote_verified']!=len(rows):errors['raw_quote_coverage']+=1
 result={'ledger_rows':len(rows),'unique_fids':len({r['fid'] for r in rows}),'incremental_fids_2024_2026':len({r['fid'] for r in incr}),'candidate_frozen_overlap':outside_overlap,'method_settlement_rows':sum(len(r['methods']) for r in rows),'settlement_and_summary_errors':dict(errors),'raw_crown_t1_audit':dict(raw_counts),'raw_quote_mismatch_examples':quote_mismatch,'input_sha256':{str(p):sha(p) for p in (LEDGER,SUMMARY,PATH,SCORES,FOUNDATION,OLD,INDEX,GAMES,MANAGER) if p.exists()},'pass':not errors and raw_counts['raw_quote_verified']==len(rows)}
 (OUT/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('input_sha256','raw_quote_mismatch_examples')},ensure_ascii=False,indent=2))
 if errors:raise SystemExit('Independent verification found errors.')
if __name__=='__main__':main()
