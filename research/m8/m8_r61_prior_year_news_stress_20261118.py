import json,hashlib,glob,datetime,collections,os,requests,bs4
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_r61_dated_team_news_audit_20261118.py').read_text()
exec(s[:s.index('sources=[]')])
SOURCE.mkdir(exist_ok=True)
HIST={
 '2024-10-04':['https://www.theguardian.com/football/2024/oct/04/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2024-10-18':['https://www.theguardian.com/football/2024/oct/18/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2024-10-25':['https://www.theguardian.com/football/2024/oct/25/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2024-11-01':['https://www.theguardian.com/football/2024/nov/01/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2024-11-08':['https://www.theguardian.com/football/2024/nov/08/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2025-10-03':['https://www.theguardian.com/sport/2025/oct/03/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2025-10-17':['https://www.theguardian.com/sport/2025/oct/17/premier-league-team-news-predicted-lineups-for-the-weekend-action',
                 'https://www.theguardian.com/football/2025/oct/17/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2025-10-24':['https://www.theguardian.com/sport/2025/oct/24/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2025-10-31':['https://www.theguardian.com/football/2025/oct/31/premier-league-team-news-predicted-lineups-for-the-weekend-action'],
 '2025-11-07':['https://www.theguardian.com/football/2025/nov/07/premier-league-team-news-predicted-lineups-for-the-weekend-action']
}
def normal(s):
 n=norm(s)
 n=n.replace('wolverhamptonwanderers','wolves').replace('wolverhampton','wolves')
 n=n.replace('newcastleunited','newcastle').replace('leicestercity','leicester')
 n=n.replace('westhamunited','westham').replace('brightonhovealbion','brighton')
 n=n.replace('tottenhamhotspur','tottenham').replace('manchesterunited','manunited')
 n=n.replace('nottinghamforest','nottinghamforest')
 n=n.replace('bournemouthafc','bournemouth').replace('burnleyfc','burnley')
 n=n.replace('sheffieldunited','sheffieldunited')
 return n
sources=[];unavailable_sources={}
for date,candidates in HIST.items():
 best=None
 for url in candidates:
  try:
   x=extract(url,date)
   best=x
   break
  except Exception as exc:
   unavailable_sources[url]=type(exc).__name__+': '+str(exc)[:150]
 if best:
  sources.append(best)
  print('NEWS',date,'fixtures',len(best['matches']),'lastModified',best['modified_utc'],flush=True)
 else:print('NEWS_MISSING',date,flush=True)
# Crown local original historical schedule league 1. Competition is the
# already approved league, no third-party Asian handicap prices.
CROWN={}
for file in glob.glob(os.path.expanduser('~/QuantAsiaDesk/data/m5-crown-authorized/schedules/1/page-*.raw.json')):
 d=json.load(open(file));assert d['data']['league']['league_id']=='1'
 for match in d['data']['matches']:
  if match.get('status')!='full':continue
  fid=str(match['id'])
  if fid in CROWN:
   assert (CROWN[fid][0]['hg'],CROWN[fid][0]['ag'])==(match['hg'],match['ag'])
  CROWN[fid]=(match,file)
quote={}
for ln in (P/'m8_early_joint_market_inventory_20261115.jsonl').open():
 q=json.loads(ln)
 if q['T']==12 and str(q['league'])=='1' and q['year'] in (2024,2025):
  assert q['fid'] not in quote
  quote[q['fid']]=q
out={'study':'M8_R61_PRIOR_YEAR_GUARDIAN_DATED_NEWS_CROWN_AH_STRESS',
 'method':'Stress-test the post-hoc R61 unweighted reported injury+suspension count direction on 2024/25 older seasons with dated Guardian weekly news and Crown post-retrieved T12 event-timestamped AH quotes. Only historical replay, not pregame received or independent forward. Must require source article last-modified before nominal kickoff minus 12h; match both home away and kickoff UTC against Crown league1 original FULL schedule and Crown T12 quote, then check FT. Doubt separate. Model is unweighted and posthoc invented after observing 2026 R61 results, so validation is NOT independent preregistered proof. Never use future lineup or scoring in features, never use other sportsbook odds. Null when equal absence counts is a research hypothesis only, not a new trading gate.',
 'coverage':{'news_source_pages_found':len(sources),'news_source_pages_missing':len(HIST)-len(sources),
 'missing_sources':unavailable_sources,'Crown_league1_all_schedule_FT':len(CROWN),
 'Crown_EPL_T12_quote_2024_25':len(quote)},
 'sources':[{k:v for k,v in s.items() if k!='matches'}|{'matches_in_article':len(s['matches'])} for s in sources],
 'rejected':{},'fixtures':[],'years':{}}
rej=collections.Counter()
for source in sources:
 modified=dt(source['modified_utc'])
 for pair in source['matches']:
  hname=normal(pair['home_label']);aname=normal(pair['away_label'])
  candidates=[]
  for fid,(g,file) in CROWN.items():
   if (normal(g['h']),normal(g['a']))!=(hname,aname):continue
   sched_kick=datetime.datetime.fromisoformat(g['start']+'+08:00').astimezone(datetime.timezone.utc)
   days=(sched_kick-modified).total_seconds()/3600
   if 12<=days<=6*24:candidates.append((fid,g,sched_kick,file))
  if len(candidates)!=1:
   rej['no_unique_competition_score_fixture_with_pre_T12_news']+=1
   continue
  fid,g,kick,scorefile=candidates[0]
  q=quote.get(fid)
  if q is None:
   rej['no_historical_Crown_T12_pair']+=1;continue
  if str(q['date'])!=kick.date().isoformat():
   rej['Crown_T12_UTC_date_mismatch']+=1;continue
  if int(q['hg'])!=int(g['hg']) or int(q['ag'])!=int(g['ag']):
   rej['Crown_T12_FT_score_mismatch']+=1;continue
  if len(pair['teams'])!=2 or normal(pair['teams'][0]['name'])!=hname or normal(pair['teams'][1]['name'])!=aname:
   rej['news_team_sections_mismatch']+=1;continue
  abs_home=len(pair['teams'][0]['injured'])+len(pair['teams'][0]['suspended'])
  abs_away=len(pair['teams'][1]['injured'])+len(pair['teams'][1]['suspended'])
  side='home' if abs_home<abs_away else 'away' if abs_away<abs_home else None
  z={'fid':fid,'home':g['h'],'away':g['a'],'year':int(kick.year),'kickoff_utc':kick.isoformat(),
   'news_source_date':source['source_date'],'news_url':source['url'],
   'news_modified_utc':source['modified_utc'],
   'news_before_nominal_T12_hours':round((kick-datetime.timedelta(hours=12)-modified).total_seconds()/3600,4),
   'bookmaker':'Crown',
   'Crown_T12_event_age_hours_before_T12':q['age_ah'],
   'Crown_quote_source_may_precede_article':bool(q['age_ah']>(kick-datetime.timedelta(hours=12)-modified).total_seconds()/3600),
   'Crown_T12_line':q['al'],'home_price':q['ah'],'away_price':q['aa'],
   'Crown_FT_home':g['hg'],'Crown_FT_away':g['ag'],
   'reported_unavailable_home':abs_home,'reported_unavailable_away':abs_away,
   'reported_doubtful_home':len(pair['teams'][0]['doubtful']),
   'reported_doubtful_away':len(pair['teams'][1]['doubtful']),
   'research_fewer_absences_side':side,
   'fewer_absences_AH_Crown_T12_PnL':float(q['home_U'] if side=='home' else q['away_U']) if side else None,
   'more_absences_AH_Crown_T12_PnL':float(q['away_U'] if side=='home' else q['home_U']) if side else None,
   'Crown_schedule_source_file_sha256':hashlib.sha256(Path(scorefile).read_bytes()).hexdigest()}
  out['fixtures'].append(z)
assert len({x['fid'] for x in out['fixtures']})==len(out['fixtures'])
out['rejected']=dict(rej)
def stat(p):
 a=np.asarray(p,float)
 return {'n':len(a),'U':round(float(a.sum()),3),
 'ROI':round(100*float(a.mean()),3) if len(a) else None,
 'wins':int((a>1e-8).sum()),'losses':int((a<-1e-8).sum()),
 'push':int((abs(a)<=1e-8).sum())}
for year in (2024,2025):
 f=[x for x in out['fixtures'] if x['year']==year]
 test=[x for x in f if x['research_fewer_absences_side']]
 out['years'][str(year)]={'fixtures_matched':len(f),'hypothesis_count':len(test),
   'fewer_absence_side':stat([x['fewer_absences_AH_Crown_T12_PnL'] for x in test]),
   'more_absence_side_posthoc_reverse':stat([x['more_absences_AH_Crown_T12_PnL'] for x in test]),
   'quote_source_event_preceded_article_n':sum(x['Crown_quote_source_may_precede_article'] for x in f),
   'by_report':{date:{'n':len([x for x in test if x['news_source_date']==date]),
     'less_absence_side':stat([x['fewer_absences_AH_Crown_T12_PnL'] for x in test if x['news_source_date']==date])}
     for date in sorted(set(x['news_source_date'] for x in f))}}
 print('PRIOR',year,out['years'][str(year)],flush=True)
print('SOURCE_COVERAGE',out['coverage'],'matched',len(out['fixtures']),'rejections',out['rejected'],flush=True)
(P/'m8_r61_prior_year_news_stress_20261118.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
