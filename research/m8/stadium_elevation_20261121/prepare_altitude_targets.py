#!/usr/bin/env python3
"""Build strict-prior team-ground proxies for the stadium-elevation × Crown AH study."""
from __future__ import annotations
import collections,csv,datetime as dt,gzip,hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parents[3]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=WORK/'m8_pregame_info_source_20261117'
VENUE=ROOT/'research/m8/venue_environment_20261120/venue_identity_cohort_20261120.jsonl.gz'
OUT=pathlib.Path(__file__).resolve().parent
COMP={'1':'GB1','12':'IT1','14':'ES1','16':'L1','25':'FR1','29':'A1','31':'BE1','35':'TS1','37':'NL1','48':'PL1','51':'PO1','52':'RO1','61':'C1','62':'TR1','66':'SE1','70':'DK1','73':'JAP1','75':'RSK1','88':'NO1','141':'GR1','262':'SC1','290':'SA1','303':'SER1','319':'UKR1','26540':'KR1'}
TZ=dt.timezone(dt.timedelta(hours=8))
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 games_path=DATA/'games.csv.gz'; comps_path=DATA/'competitions.csv.gz'
 competitions={}
 with gzip.open(comps_path,'rt',encoding='utf8') as f:
  for r in csv.DictReader(f): competitions[r['competition_id']]=r.get('country_name','')
 games=[]; target_comp={};byclub=collections.defaultdict(list)
 with gzip.open(games_path,'rt',encoding='utf8') as f:
  for r in csv.DictReader(f):
   try: day=dt.date.fromisoformat(r['date']);club=str(r['home_club_id']);stadium=(r.get('stadium') or '').strip()
   except Exception: continue
   if not club or not stadium:continue
   row=(day,stadium,str(r['competition_id']),str(r.get('game_id') or ''))
   games.append((club,*row));byclub[club].append(row)
   target_comp[str(r.get('game_id') or '')]=str(r['competition_id'])
 for arr in byclub.values():arr.sort()
 candidates=[];missing=collections.Counter();queries={}
 with gzip.open(VENUE,'rt',encoding='utf8') as f:
  for line in f:
   r=json.loads(line)
   if int(r.get('year') or 0) not in (2019,2020,2021,2022,2023,2024,2025,2026):continue
   day=dt.date.fromisoformat(r['tm_date']);cutoff=day-dt.timedelta(days=3)
   def prior_modes(club):
    prior=[x for x in byclub[str(club)] if x[0]<cutoff and x[0]>=cutoff-dt.timedelta(days=365)]
    if not prior:return [],0,0
    cnt=collections.Counter(x[1] for x in prior);top=max(cnt.values())
    return sorted(x for x,n in cnt.items() if n==top),top,len(prior)
   hmodes,hcount,hn=prior_modes(r['tm_home_club_id']);amodes,acount,an=prior_modes(r['tm_away_club_id'])
   comp=target_comp.get(str(r['tm_game_id']),'');country=competitions.get(comp,'')
   if not country:missing['target_competition_country_missing']+=1
   hselected=hmodes[0] if len(hmodes)==1 else None;aselected=amodes[0] if len(amodes)==1 else None
   if not hmodes:missing['home_no_prior_ground_365d']+=1
   if not amodes:missing['away_no_prior_ground_365d']+=1
   if len(hmodes)>1:missing['home_prior_ground_tie']+=1
   if len(amodes)>1:missing['away_prior_ground_tie']+=1
   entry={
    'fid':str(r['fid']),'year':int(r['year']),'date':r['date'],'kickoff_utc':r['ko_utc'],
    'league':str(r['league']),'home':r['home'],'away':r['away'],'home_club_id':str(r['tm_home_club_id']),
    'crown_line_home':float(r['line']),'crown_home_decimal':float(r['home_odds']),'crown_away_decimal':float(r['away_odds']),
    'ft_home':int(r['hg']),'ft_away':int(r['ag']),'frozen_original_eight':bool(r.get('frozen')),
    'stadium_actual_postmatch_diagnostic':r.get('stadium'),
    'strictly_prior_team_history':r.get('team_history') or {},
    'prior_cutoff_exclusive':cutoff.isoformat(),'prior_window_days':365,
    'prior_home_team_home_games':hn,'prior_away_team_home_games':an,
    'home_prior_venue_modes':hmodes,'home_prior_venue_mode_count':hcount,'home_prior_venue_tie':len(hmodes)>1,
    'away_prior_venue_modes':amodes,'away_prior_venue_mode_count':acount,'away_prior_venue_tie':len(amodes)>1,
    'pregame_home_venue_proxy':hselected,'pregame_away_home_venue_proxy':aselected,
    'competition_country':country,'venue_proxy_is_target_stadium':False,
    'quote_source':'historical Crown T1 event-time; not actual HTTP receipt'
   }
   candidates.append(entry)
   for role,selected in [('host_expected_ground',hselected),('away_usual_home_ground',aselected)]:
    if selected and country:
     key=f'{selected}\t{country}'
     q=queries.setdefault(key,{'venue':selected,'country':country,'query':f'{selected}, {country}','candidate_fids':0,'years':collections.Counter(),'roles':collections.Counter()})
     q['candidate_fids']+=1;q['years'][str(r['year'])]+=1;q['roles'][role]+=1
 OUT.mkdir(parents=True,exist_ok=True)
 with gzip.open(OUT/'altitude_target_inventory_20261121.jsonl.gz','wt',encoding='utf8') as f:
  for r in sorted(candidates,key=lambda x:(x['date'],x['fid'])):f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 with (OUT/'venue_geocode_queries_base_20261121.jsonl').open('w',encoding='utf8') as f:
  for key,q in sorted(queries.items()):
   q['years']=dict(q['years']);f.write(json.dumps(q,ensure_ascii=False,sort_keys=True)+'\n')
 inputs={str(p):sha(p) for p in (VENUE,games_path,comps_path)}
 counts=collections.Counter(x['year'] for x in candidates);extra=collections.Counter(x['year'] for x in candidates if not x['frozen_original_eight'])
 dates=[x[1] for x in games]
 summary={'study':'Strict-prior stadium elevation mismatch × Crown AH inventory','fixture_rows_all_groups':len(candidates),'candidate_fids_outside_frozen_eight':sum(not x['frozen_original_eight'] for x in candidates),'candidate_outside_eight_by_year':dict(sorted(extra.items())),'by_year_all_groups':dict(sorted(counts.items())),'unique_geocode_queries':len(queries),'targets_with_both_unique_prior_venues':sum(1 for x in candidates if x['pregame_home_venue_proxy'] and x['pregame_away_home_venue_proxy']),'targets_with_home_venue_tie':missing['home_prior_ground_tie'],'targets_with_away_venue_tie':missing['away_prior_ground_tie'],'targets_without_home_prior_venue':missing['home_no_prior_ground_365d'],'targets_without_away_prior_venue':missing['away_no_prior_ground_365d'],'source_games_date_range':[min(dates).isoformat(),max(dates).isoformat()] if dates else None,'source_inputs_sha256':inputs}
 (OUT/'altitude_target_inventory_summary_20261121.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
