import json,os,hashlib,glob,datetime,collections
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
cache=P/'m8_r62_full_season_guardian_source_20261118'
disc=json.loads((P/'m8_r62_full_season_guardian_discovery_20261118.json').read_text())
code=(P/'m8_r61_dated_team_news_audit_20261118.py').read_text()
exec(code[:code.index('sources=[]')])
SOURCE=cache
# Reuse exact normalizations and source parsing contract of R61.
normcode=(P/'m8_r61_prior_year_news_stress_20261118.py').read_text()
exec(normcode[normcode.index('def normal(s):'):normcode.index('sources=[]',normcode.index('def normal(s):'))])
# Frozen previous R61 data are studied on SAME sample separately for audit,
# and not counted twice with the full season.
old=json.loads((P/'m8_r61_prior_year_news_stress_20261118.json').read_text())
original={x['fid']:x for x in old['fixtures']}
members={x['fid'] for x in map(json.loads,(P/'m8_foundation_20261115/historical_membership.jsonl').open())}
sources=[]
for entry in disc['pages']:
 if 'url' not in entry:continue
 day=entry['day']
 r=extract(entry['url'],day)
 assert hashlib.sha256((cache/(day+'.html')).read_bytes()).hexdigest()==entry['sha256']
 assert r['modified_utc']==entry['modified_utc'] and r['published_utc']==entry['published_utc']
 sources.append(r)
print('ARTICLES_PARSED',len(sources),'total_fixture_sections',sum(len(s['matches']) for s in sources),flush=True)
# Indexed verified historical Crown EPL source.
CROWN={}
for file in glob.glob(os.path.expanduser('~/QuantAsiaDesk/data/m5-crown-authorized/schedules/1/page-*.raw.json')):
 j=json.load(open(file))
 assert j['data']['league']['league_id']=='1'
 for g in j['data']['matches']:
  fid=str(g['id'])
  if g.get('status')!='full':continue
  if fid in CROWN:
   other=CROWN[fid][0]
   assert (g['h'],g['a'],g['hg'],g['ag'])==(other['h'],other['a'],other['hg'],other['ag'])
  CROWN[fid]=(g,file)
q={}
for s in (P/'m8_early_joint_market_inventory_20261115.jsonl').open():
 row=json.loads(s)
 if row['T']!=12 or row['year'] not in (2024,2025) or str(row['league'])!='1':continue
 assert row['fid'] not in q
 q[row['fid']]=row
from research.m3.probabilities import settle_score
byteams=collections.defaultdict(list)
for fid,(m,file) in CROWN.items():
 kick=datetime.datetime.fromisoformat(m['start']+'+08:00').astimezone(datetime.timezone.utc)
 if kick.year not in (2024,2025):continue
 byteams[(normal(m['h']),normal(m['a']))].append((fid,m,kick,file))
rejections=collections.Counter()
out={'study':'M8_R62_FULL_SEASON_FRI_NEWS_ABSENCES_CROWN_AH',
 'method':'Expand 15 issues of Guardian pregame injuries/suspensions to all discoverable 2024 & 2025 Fri issues in non-summer months. Each full raw editorial HTML hashed locally, source article last edited before kickoff-minus-12h. Match unique home and away names/UTC day, exact Crown league1 FULL schedule, exact Crown T12 odds/line, original FT. Historic Crown odds post-retrieved source events; no contemporaneous receipt, never marketed as observed live or forward. The more-injured-than-opponent idea is R61 post-hoc and its sample-year extension is retrospective, not post-lock true prospective. Preserve zero reports and missing matches. Do not use future T1 original8 identity to select, only retrospective attribution. Compare favorites, underdogs, all-home and away on identical events. No other bookmaker prices, no TG, no new Gates or production modifications.',
 'discovery':{'fridays_attempted':disc['fridays_attempted'],
  'source_pages_found':len(sources),'by_year':disc['by_year'],
  'news_fixture_sections':sum(len(s['matches']) for s in sources)},
 'coverage':{},'sources':[{'date':r['source_date'],'url':r['url'],
   'published':r['published_utc'],'modified':r['modified_utc'],
   'sha256':r['saved_html_sha256'],'matches':len(r['matches'])} for r in sources],
 'rejections':{},'fixtures':[],'totals':{},'by_year':{},'by_calendar_quarter':{},
 'original_R61_reconciliation':{},'foundation':{}}
for source in sources:
 modified=dt(source['modified_utc'])
 for pair in source['matches']:
  hp=normal(pair['home_label']);ap=normal(pair['away_label'])
  matches=[]
  for fid,m,kick,file in byteams.get((hp,ap),[]):
   if 12<=(kick-modified).total_seconds()/3600<=6*24:
    matches.append((fid,m,kick,file))
  if len(matches)!=1:
   rejections['no_unique_Crown_full_fixture_pre_T12_news']+=1
   continue
  fid,g,kick,file=matches[0]
  q0=q.get(fid)
  if q0 is None:
   rejections['no_Crown_historic_T12_quote']+=1;continue
  if q0['date']!=kick.date().isoformat() or (int(q0['hg']),int(q0['ag']))!=(int(g['hg']),int(g['ag'])):
   rejections['Crown_schedule_quote_UTC_or_FT_mismatch']+=1
   continue
  if len(pair['teams'])!=2 or normal(pair['teams'][0]['name'])!=hp or normal(pair['teams'][1]['name'])!=ap:
   rejections['article_team_section_not_match']+=1;continue
  hb=pair['teams'][0];ab=pair['teams'][1]
  hi=len(hb['injured'])+len(hb['suspended'])
  ai=len(ab['injured'])+len(ab['suspended'])
  more='home' if hi>ai else 'away' if hi<ai else None
  fav='home' if q0['al']<0 else 'away' if q0['al']>0 else ('home' if q0['ah']<q0['aa'] else 'away')
  hpnl=float(q0['home_U']);apnl=float(q0['away_U'])
  assert abs(settle_score('AH',float(q0['al']),'home',int(g['hg']),int(g['ag']),float(q0['ah']))[1]-hpnl)<1e-8
  assert abs(settle_score('AH',float(q0['al']),'away',int(g['hg']),int(g['ag']),float(q0['aa']))[1]-apnl)<1e-8
  result={'fid':fid,'UTC_kickoff':kick.isoformat(),'UTC_date':kick.date().isoformat(),
   'year':kick.year,'source_news_day':source['source_date'],
   'source_news_url':source['url'],'news_last_modified_utc':source['modified_utc'],
   'article_modified_to_T12_cutoff_hours':round((kick-datetime.timedelta(hours=12)-modified).total_seconds()/3600,3),
   'home':g['h'],'away':g['a'],'FT_home':int(g['hg']),'FT_away':int(g['ag']),
   'reported_home_injured_count':len(hb['injured']),'reported_home_suspended_count':len(hb['suspended']),
   'reported_home_doubtful_count':len(hb['doubtful']),
   'reported_away_injured_count':len(ab['injured']),'reported_away_suspended_count':len(ab['suspended']),
   'reported_away_doubtful_count':len(ab['doubtful']),
   'reported_home_unavailable_count':hi,'reported_away_unavailable_count':ai,
   'research_more_absent_side':more,'Crown_T12_AH_line':q0['al'],
   'Crown_T12_home_odds':q0['ah'],'Crown_T12_away_odds':q0['aa'],
   'Crown_T12_AH_age_hours':q0['age_ah'],
   'Crown_T12_AH_source_event_is_before_news_mod':bool(q0['age_ah']>(kick-datetime.timedelta(hours=12)-modified).total_seconds()/3600),
   'Crown_home_PnL':hpnl,'Crown_away_PnL':apnl,
   'Crown_market_favorite':fav,
   'future_T1_frozen_eight_POSTHOC':fid in members,
   'Crown_schedule_page_sha256':hashlib.sha256(Path(file).read_bytes()).hexdigest()}
  if more is not None:
   result['more_PnL']=hpnl if more=='home' else apnl
   result['less_PnL']=apnl if more=='home' else hpnl
   result['favorite_PnL']=hpnl if fav=='home' else apnl
   result['underdog_PnL']=apnl if fav=='home' else hpnl
  out['fixtures'].append(result)
out['rejections']=dict(rejections)
assert len(set(z['fid'] for z in out['fixtures']))==len(out['fixtures'])
def calc(z):
 a=np.array(z,float)
 return {'n':len(a),'U':round(float(a.sum()),3),
  'ROI':round(100*float(a.mean()),3) if len(a) else None,
  'wins':int((a>1e-8).sum()),'losses':int((a<-1e-8).sum()),'push':int((abs(a)<=1e-8).sum())}
def group(z):
 s=[r for r in z if r['research_more_absent_side'] is not None]
 return {'all_news_matches':len(z),'unequal_reported_absence_count_games':len(s),
  'more_absent_side_AH':calc([r['more_PnL'] for r in s]),
  'less_absent_side_AH':calc([r['less_PnL'] for r in s]),
  'same_games_unconditional_underdog':calc([r['underdog_PnL'] for r in s]),
  'same_games_unconditional_favorite':calc([r['favorite_PnL'] for r in s]),
  'same_games_unconditional_home':calc([r['Crown_home_PnL'] for r in s]),
  'same_games_unconditional_away':calc([r['Crown_away_PnL'] for r in s]),
  'more_absent_minus_underdog':calc([r['more_PnL']-r['underdog_PnL'] for r in s]),
  'T1_original_eight_members_posthoc':sum(r['future_T1_frozen_eight_POSTHOC'] for r in s),
  'outside_T1_original_eight_POSTHOC':calc([r['more_PnL'] for r in s if not r['future_T1_frozen_eight_POSTHOC']]),
  'Crown_early_quote_event_preceded_article_last_modified_n':sum(r['Crown_T12_AH_source_event_is_before_news_mod'] for r in z)}
out['totals']=group(out['fixtures'])
for yr in (2024,2025):
 matches=[x for x in out['fixtures'] if x['year']==yr]
 out['by_year'][str(yr)]=group(matches)
 for k in sorted(set(x['UTC_date'][:7] for x in matches)):
  out['by_calendar_quarter'][k]=group([x for x in matches if x['UTC_date'][:7]==k])
 # prior R61 five issues must reproduce SAME strict original R61 samples if
 # archive shared the same article issue dates; list differences explicitly.
 earlier={k:v for k,v in original.items() if v['year']==yr}
 current={r['fid']:r for r in matches if r['source_news_day'] in {z['source_date'] for z in old['sources']}}
 oldf=set(earlier)
 newf=set(current)
 out['original_R61_reconciliation'][str(yr)]={'R61_source_fids':len(oldf),
  'R62_current_matching_same_issues':len(oldf&newf),
  'R61_not_in_R62':sorted(oldf-newf),
  'R62_same_issue_not_in_R61':sorted(newf-oldf)}
print('EXPANDED',out['discovery'],out['rejections'],flush=True)
for year,grouped in out['by_year'].items():
 print('YEAR',year,grouped,flush=True)
print('R61_COMPARE',out['original_R61_reconciliation'],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
digest=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={
 'membership':digest(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(digest(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(digest(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_r62_full_season_absence_ah_replay_20261118.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
