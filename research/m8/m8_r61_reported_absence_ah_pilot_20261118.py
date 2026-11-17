import json,collections,datetime,math,hashlib,glob,os
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
aud=json.loads((P/'m8_r61_dated_team_news_source_20261118/R61_dated_news_audit.json').read_text())
src=(P/'m8_early_joint_path_incremental_20261116.py').read_text()
exec(src[:src.rindex("out={'method'")])
assert len(pairs)==1230
R22={b['fid']:(a,b) for a,b in pairs}
# Crown league-1 published schedule captured 2026-11-05; strict final status
# gives original Crown full-time scores for October games missing R22 paired FT.
schedule_files=glob.glob(os.path.expanduser('~/QuantAsiaDesk/data/m5-crown-authorized/schedules/1/page-*.raw.json'))
scores={}
for file in schedule_files:
 raw=json.load(open(file));assert raw.get('success')==1
 assert str(raw['data']['league']['league_id'])=='1'
 for fixture in raw['data'].get('matches',[]):
  fid=str(fixture['id'])
  if fid not in {r['fid'] for r in aud['fixtures']}:continue
  if fixture.get('status')!='full':continue
  if fid in scores:
   other=scores[fid][0]
   assert (other['hg'],other['ag'],other['h'],other['a'])==(fixture['hg'],fixture['ag'],fixture['h'],fixture['a'])
  scores[fid]=(fixture,file)
print('CROWN_FT_SCHEDULE',len(scores),'R22',len(R22),flush=True)
news=aud['fixtures']
print('DATA',len(news),'r22matches',sum(r['fid'] in R22 for r in news),flush=True)
def dt(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def report_name(s):
 import unicodedata
 x=s.split('(')[0].strip()
 x=unicodedata.normalize('NFKD',x)
 return ''.join(y for y in x.casefold() if y.isalnum() and not unicodedata.combining(y))
def winloss(side,line,hg,ag):
 from research.m3.probabilities import settle_score
 q=settle_score('AH',float(line),side,int(hg),int(ag),2.0)[1]
 w=settle_score('AH',float(line),side,int(hg),int(ag),3.0)[1]-q
 l=w-q
 return float(w),float(l)
def stat(x):
 z=np.array(x,float);return {'n':len(z),'U':round(float(z.sum()),3),
 'ROI':round(100*float(z.mean()),3) if len(z) else None,
 'wins':int((z>1e-9).sum()),'losses':int((z<-1e-9).sum()),
 'pushes':int((abs(z)<=1e-9).sum())}
def ci(x,days,n=6000):
 assert len(x)==len(days)
 if not x:return None
 d=collections.defaultdict(list)
 for v,day in zip(x,days):d[day].append(float(v))
 V=np.array([(sum(v),len(v)) for v in d.values()])
 rng=np.random.default_rng(61);ix=rng.integers(len(V),size=(n,len(V)))
 o=100*V[ix,0].sum(1)/V[ix,1].sum(1)
 return [round(float(z),3) for z in np.quantile(o,[.025,.975])],len(V)
R61={'study':'M8_R61_PREMATCH_DATED_AVAILABILITY_VS_CROWN_AH',
 'research_scope':'Pilot only: five 2026-10/11 dated Guardian pre-match weekly lists, news last modified before actual Crown T12 received on SAME fixtures. Data are weekly reported injured/suspended/doubtful; not official confirmation for every player and NOT first public discovery. News obtained after matches, so article revision transparency metadata does not prove saved contemporaneous snapshot. No claimed new AH edge. Only Crown AH quote and precise R22 FT results. No OU research membership filter or final T1 original-eight exclusion in early decision. Historical original8 remains unchanged. Hypothetical fewer reported absent player count rule is a research DIAGNOSTIC with no squad-strength weights or EV and must not become a production Gate. Unknown/doubtful separate. No official TG, bet fills or trading action.',
 'news_source_audit':aud['matching'],
 'source_pages':aud['sources'],
 'reconciled_fixtures':[],
 'coverage':{},
 'research_diagnostics':{},
 'foundation':{}}
daily=collections.defaultdict(list)
fail=collections.Counter()
def missing(record):
 return len(record['injured'])+len(record['suspended'])
baseline={}
for r in news:
 fid=r['fid']
 given_R22=R22.get(fid)
 original_score=scores.get(fid)
 if not given_R22 and not original_score:
  fail['FT_missing_from_R22_and_Crown_schedule_full']+=1
  continue
 source_kind='R22_original_receipt_FT' if given_R22 else 'Crown_league1_schedule_FT'
 if original_score:
  game,scorefile=original_score
  assert game['h']==r['home'] and game['a']==r['away']
  sh=datetime.datetime.fromisoformat(game['start']+'+08:00').astimezone(datetime.timezone.utc)
  assert abs((sh-dt(r['kickoff_utc'])).total_seconds())<121,(fid,sh,r['kickoff_utc'])
  hg=int(game['hg']);ag=int(game['ag'])
  if given_R22:
   assert (int(given_R22[1]['hg']),int(given_R22[1]['ag']))==(hg,ag)
 else:
  hg=int(given_R22[1]['hg']);ag=int(given_R22[1]['ag'])
 from research.m3.probabilities import settle_score
 b={'fid':fid,'al':float(r['T12_AH_line']),
    'ah':float(r['T12_home_odds']),'aa':float(r['T12_away_odds']),
    'hg':hg,'ag':ag,
    'home_U':settle_score('AH',float(r['T12_AH_line']),'home',hg,ag,float(r['T12_home_odds']))[1],
    'away_U':settle_score('AH',float(r['T12_AH_line']),'away',hg,ag,float(r['T12_away_odds']))[1]}
 if given_R22:
  older,exact=given_R22
  assert (b['al'],b['ah'],b['aa'])==(exact['al'],exact['ah'],exact['aa'])
  assert abs(float(exact['home_U'])-b['home_U'])<1e-8
  assert abs(float(exact['away_U'])-b['away_U'])<1e-8
 arch=[a for a in map(json.loads,(P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl').open()) if str(a['fixture_id'])==fid and a['snapshot_horizon']=='T24']
 if arch:
  older_market=arch[-1]['markets']['AH']
  earlier={'al':float(older_market['line']),
   'ah':float(older_market['odds']['home']),
   'aa':float(older_market['odds']['away'])}
  # R22 previous-window quote can be a later T18 receipt, not the raw T24.
  # Do not require different legitimate receipt moments to carry same price.
 else:
  earlier=None
 teamhome,teamaway=r['players']
 home_n=missing(teamhome);away_n=missing(teamaway)
 d=away_n-home_n
 # Fewer reported absences picked as research-only side.
 side='home' if d>0 else 'away' if d<0 else None
 prev_home=float(earlier['ah']) if earlier else float('nan');prev_away=float(earlier['aa']) if earlier else float('nan')
 h=float(b['home_U']);a=float(b['away_U'])
 q={'fid':r['fid'],'home':r['home'],'away':r['away'],
  'source_date':r['source_date'],'news_published_utc':r['source_published_utc'],
  'news_modified_utc':r['source_modified_utc'],'Crown_T12_received_utc':r['T12_received_utc'],
  'kickoff_utc':r['kickoff_utc'],
  'news_modified_to_Crown_receipt_hours':r['source_was_modified_hours_before_T12'],
  'Crown_T12_AH_source_event_utc':r['T12_AH_source_event_utc'],
  'reported_home_injured':r['home_reported_injured_n'],
  'reported_home_suspended':r['home_reported_suspended_n'],
  'reported_home_doubtful':r['home_reported_doubtful_n'],
  'reported_away_injured':r['away_reported_injured_n'],
  'reported_away_suspended':r['away_reported_suspended_n'],
  'reported_away_doubtful':r['away_reported_doubtful_n'],
  'home_reported_unavailable':home_n,'away_reported_unavailable':away_n,
  'reported_unavailable_home_minus_away':home_n-away_n,
  'research_diagnostic_side':side,
  'T12_Crown_AH_line':b['al'],
  'T12_Crown_AH_home_decimal':b['ah'],'T12_Crown_AH_away_decimal':b['aa'],
  'Crown_T24_home_decimal':earlier['ah'] if earlier else None,
  'Crown_T24_away_decimal':earlier['aa'] if earlier else None,
  'Crown_T24_AH_line':earlier['al'] if earlier else None,
  'Crown_FT_source':source_kind,
  'Crown_schedule_file_sha256':hashlib.sha256(Path(original_score[1]).read_bytes()).hexdigest() if original_score else None,
  'FT_home_goals':b['hg'],'FT_away_goals':b['ag'],
  'Crown_T12_home_AH_profit':h,'Crown_T12_away_AH_profit':a,
  'research_diagnostic_PnL':h if side=='home' else a if side=='away' else None,
  'early_News_publication_vs_Crown_T12_UTC':True,
  'source_url':r['source_url'],'source_page_sha256':r['source_html_sha256']}
 if side:
  was_line_same=earlier is not None and earlier['al']==b['al']
  q['T24_T12_AH_line_same']=bool(was_line_same)
  q['T24_T12_on_selected_side_odds_shortening']=round(float((prev_home-b['ah']) if side=='home' else (prev_away-b['aa'])),4) if was_line_same else None
  w,l=winloss(side,b['al'],b['hg'],b['ag'])
  odd=float(b['ah'] if side=='home' else b['aa'])
  assert abs(q['research_diagnostic_PnL']-(w*(odd-1)-l))<1e-8
  q['research_diagnostic_won_stake_fraction']=w
  q['research_diagnostic_lost_stake_fraction']=l
 R61['reconciled_fixtures'].append(q)
 daily[r['source_date']].append(q)
assert len({q['fid'] for q in R61['reconciled_fixtures']})==len(R61['reconciled_fixtures'])
R61['coverage']={'dated_news_Crown_T12_matched':len(news),
 'R22_T24_T12_verified_FT_AH_reconciled':len(R61['reconciled_fixtures']),
 'not_reconciled':dict(fail),
 'research_diagnostic_side_defined':sum(q['research_diagnostic_side'] is not None for q in R61['reconciled_fixtures']),
 'reported_injured_total':sum(q['reported_home_injured']+q['reported_away_injured'] for q in R61['reconciled_fixtures']),
 'reported_suspended_total':sum(q['reported_home_suspended']+q['reported_away_suspended'] for q in R61['reconciled_fixtures']),
 'reported_doubtful_total':sum(q['reported_home_doubtful']+q['reported_away_doubtful'] for q in R61['reconciled_fixtures']),
 'verified_source_times_all_before_actual_Crown_received':all(dt(q['news_modified_utc'])<dt(q['Crown_T12_received_utc']) for q in R61['reconciled_fixtures'])}
used=[q for q in R61['reconciled_fixtures'] if q['research_diagnostic_side'] is not None]
R61['research_diagnostics']['equal_reported_unavailable_n']=len(R61['reconciled_fixtures'])-len(used)
R61['research_diagnostics']['less_reported_unavailable_AH_side_hypothesis']=stat([q['research_diagnostic_PnL'] for q in used])
R61['research_diagnostics']['opposite_of_hypothesis']=stat([q['Crown_T12_away_AH_profit'] if q['research_diagnostic_side']=='home' else q['Crown_T12_home_AH_profit'] for q in used])
bss=ci([q['research_diagnostic_PnL'] for q in used],[q['kickoff_utc'][:10] for q in used])
R61['research_diagnostics']['clustered_UTC_date_bootstrap_95pct_ROI']=bss[0] if bss else None
R61['research_diagnostics']['unique_UTC_kickoff_dates']=bss[1] if bss else 0
byweek={}
for date,groups in sorted(daily.items()):
 v=[q for q in groups if q['research_diagnostic_side'] is not None]
 byweek[date]={'all_matched_n':len(groups),'with_clear_unequal_reported_absences_n':len(v),
  'research_side':stat([q['research_diagnostic_PnL'] for q in v]),
  'average_reported_absence_home_minus_away':round(float(np.mean([q['reported_unavailable_home_minus_away'] for q in groups])),3),
  'Crown_T24_T12_line_changed_n':sum(q['Crown_T24_AH_line'] is not None and q['Crown_T24_AH_line']!=q['T12_Crown_AH_line'] for q in groups),
  'Crown_T24_missing_n':sum(q['Crown_T24_AH_line'] is None for q in groups)}
R61['research_diagnostics']['week_by_week']=byweek
# Compare news 'known at snapshot' to market-source event to make clear
# that news publication does not prove a new unpriced shock.
before=0;after=0
for q in R61['reconciled_fixtures']:
 if dt(q['Crown_T12_AH_source_event_utc']) < dt(q['news_modified_utc']):before+=1
 else:after+=1
R61['research_diagnostics']['Crown_last_AH_source_event_BEFORE_article_last_modified']=before
R61['research_diagnostics']['Crown_last_AH_source_event_AFTER_or_equal_article_last_modified']=after
# Archive source list per team for repeated absences, but do NOT treat missing
# items in a later weekly post as confirmed player medically cleared.
history=collections.defaultdict(list)
for q in sorted(R61['reconciled_fixtures'],key=lambda a:a['source_date']):
 original=next(a for a in news if a['fid']==q['fid'])
 for team in original['players']:
  teamname=team['name']
  names={report_name(v) for v in team['injured']+team['suspended']}
  history[teamname].append((q['source_date'],names))
episode={'team_weeks':0,'first_coverage_baseline_n':0,'new_to_this_week_report_after_prior_week_n':0,
 'repeated_from_prior_report_n':0,'disappeared_from_next_report_n':0}
for team,h in history.items():
 prev=None
 for day,values in h:
  episode['team_weeks']+=1
  if prev is None:episode['first_coverage_baseline_n']+=len(values)
  else:
   episode['new_to_this_week_report_after_prior_week_n']+=len(values-prev)
   episode['repeated_from_prior_report_n']+=len(values&prev)
   episode['disappeared_from_next_report_n']+=len(prev-values)
  prev=values
R61['research_diagnostics']['weekly_player_report_continuity']=episode
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
R61['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(R61['foundation'].values())
(P/'m8_r61_reported_absence_ah_pilot_20261118.json').write_text(json.dumps(R61,ensure_ascii=False,indent=2))
print('COVERAGE',R61['coverage'],flush=True)
print('RESULT',R61['research_diagnostics']['less_reported_unavailable_AH_side_hypothesis'],
 'REVERSE',R61['research_diagnostics']['opposite_of_hypothesis'],
 'CI',R61['research_diagnostics']['clustered_UTC_date_bootstrap_95pct_ROI'],flush=True)
print('WEEKS',byweek,flush=True)
print('NEWS_TIMES',before,after,'PERSONNEL',episode,flush=True)
