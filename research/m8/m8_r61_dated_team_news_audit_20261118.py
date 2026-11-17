import json,requests,bs4,re,hashlib,datetime,unicodedata,collections,sys
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
SOURCE=P/'m8_r61_dated_team_news_source_20261118'
SOURCE.mkdir(exist_ok=True)
URLS={
 '2026-10-09':'https://www.theguardian.com/football/2026/oct/09/premier-league-team-news-predicted-lineups-for-the-weekend-action',
 '2026-10-16':'https://www.theguardian.com/football/2026/oct/16/premier-league-team-news-predicted-lineups-for-the-weekend-action',
 '2026-10-23':'https://www.theguardian.com/football/2026/oct/23/premier-league-team-news-predicted-lineups',
 '2026-10-30':'https://www.theguardian.com/football/2026/oct/30/premier-league-team-news-predicted-lineups-for-the-weekend-action',
 '2026-11-06':'https://www.theguardian.com/football/2026/nov/06/premier-league-team-news-predicted-lineups-for-the-weekend-action'
}
def dt(s):
 return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def norm(s):
 s=unicodedata.normalize('NFKD',s)
 s=''.join(x for x in s if not unicodedata.combining(x))
 s=s.casefold().replace('utd','united').replace('nottm','nottingham').replace('spurs','tottenham')
 s=s.replace('city','city').replace('brighton and hove albion','brighton').replace('afc ','')
 s=s.replace('hull city','hull').replace('ipswich town','ipswich').replace('manchester','man')
 return ''.join(c for c in s if c.isalnum())
def names(raw):
 raw=raw.strip()
 if raw.lower().strip() in ('none','nil','n/a','no','-',''):return []
 # CSV commas can occur inside parenthetical descriptions, but not player
 # separator. Count top-level comma-delimited entries with source raw preserved.
 items=[];cur='';depth=0
 for ch in raw:
  if ch=='(':depth+=1
  if ch==')':depth=max(0,depth-1)
  if ch==',' and depth==0:
   if cur.strip():items.append(cur.strip())
   cur=''
  else:cur+=ch
 if cur.strip():items.append(cur.strip())
 return items
def extract(url,date):
 path=SOURCE/f'{date}.html'
 if not path.exists():
  rr=requests.get(url,timeout=30,headers={'User-Agent':'Mozilla/5.0'})
  rr.raise_for_status()
  path.write_bytes(rr.content)
 rawbytes=path.read_bytes();soup=bs4.BeautifulSoup(rawbytes,'html.parser')
 def met(k):
  v=soup.find('meta',attrs={'property':k});return v.get('content') if v else None
 modified=met('article:modified_time');published=met('article:published_time')
 assert published and modified and dt(modified)>=dt(published)
 body=soup.select_one('.article-body-commercial-selector')
 if body is None:raise ValueError('Missing article body')
 current=None;team=None; matches={}
 for item in body.children:
  if not getattr(item,'name',None):continue
  if item.name=='h2':
   title=item.get_text(' ',strip=True)
   if re.search(r'\s+v\s+',title) and title.replace(' v ','').upper()==title.replace(' v ',''):
    a,b=re.split(r'\s+v\s+',title,1,flags=re.I)
    current={'home_label':a,'away_label':b,'teams':[]}
    matches[title]=current;team=None
   elif current is not None:
    if len(current['teams'])<2:
     team={'name':title,'injured':[],'suspended':[],'doubtful':[], 'source_text':{}}
     current['teams'].append(team)
    else:team=None
  elif item.name=='p' and team is not None:
   v=item.get_text(' ',strip=True)
   for label in ('Injured','Suspended','Doubtful'):
    if v.startswith(label+' '):
     team[label.lower()]=names(v[len(label):].strip())
     team['source_text'][label.lower()]=v
 assert matches,(date,url)
 return {'source_date':date,'url':url,'published_utc':published,'modified_utc':modified,
  'saved_html_sha256':hashlib.sha256(rawbytes).hexdigest(),'matches':list(matches.values())}
sources=[]
for day,url in URLS.items():
 x=extract(url,day)
 sources.append(x)
 print('SOURCE',day,'times',x['published_utc'],x['modified_utc'],'fixtures',len(x['matches']),'labels',[(m['home_label'],m['away_label']) for m in x['matches']],flush=True)
# Actual received T12 Crown archive, not a retrospective source event.
archive=[json.loads(s) for s in (P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl').open()]
eng=collections.defaultdict(list)
for r in archive:
 if r['league']=='England Premier League' and r['snapshot_horizon'] in ('T12','T18','T24'):
  eng[str(r['fixture_id'])].append(r)
real={}
for fid,rs in eng.items():
 rs=sorted(rs,key=lambda r:r['received_utc'])
 mraw=json.loads(json.loads(Path(rs[0]['source_file']).read_text())['raw_response'])
 match=next(x for x in mraw['data'] if str(x['id'])==fid)
 real[fid]={'fid':fid,'home':match['h'],'away':match['a'],
  'kickoff_utc':rs[0]['kickoff_utc'],'snapshots':rs}
eligible=[];rejected=[];all_art=[]
for s in sources:
 for m in s['matches']:
  a=norm(m['home_label']);b=norm(m['away_label'])
  found=[x for x in real.values() if (norm(x['home']),norm(x['away']))==(a,b)]
  if len(found)!=1:
   rejected.append({'source_date':s['source_date'],'fixture':(m['home_label'],m['away_label']),
    'reason':'not exactly one Crown EPL fixture mapped','candidate_n':len(found)})
   continue
  q=found[0]
  # choose T12 if present, else no substitution silently
  t12=[r for r in q['snapshots'] if r['snapshot_horizon']=='T12']
  if not t12:
   rejected.append({'source_date':s['source_date'],'fixture':(m['home_label'],m['away_label']),
    'reason':'no real T12 receipt','fid':q['fid']})
   continue
  rr=t12[-1]
  pub=dt(s['published_utc']);mod=dt(s['modified_utc']);recv=dt(rr['received_utc']);kick=dt(q['kickoff_utc'])
  if not (mod<=recv<kick):
   rejected.append({'source_date':s['source_date'],'fixture':(m['home_label'],m['away_label']),
    'reason':'news modified AFTER T12 actual receipt OR not pregame','fid':q['fid'],
    'news_modified_utc':s['modified_utc'],'received_utc':rr['received_utc']})
   continue
  a=Path(rr['source_file']);record=json.loads(a.read_bytes())
  raw=record['raw_response'].encode()
  assert hashlib.sha256(raw).hexdigest()==record['raw_sha256']==rr['raw_sha256']
  snap_path=a.parent.parent/'snapshot.json'
  assert hashlib.sha256(snap_path.read_bytes()).hexdigest()==rr['snapshot_sha256']
  assert record['classification']=='SNAPSHOT_OK' and record['http_status']==200
  assert rr['markets']['AH']['source_event_utc']
  # Avoid a team header typo from article being silently mapped:
  if len(m['teams'])!=2 or norm(m['teams'][0]['name'])!=norm(q['home']) or norm(m['teams'][1]['name'])!=norm(q['away']):
   rejected.append({'source_date':s['source_date'],'fixture':(m['home_label'],m['away_label']),
    'reason':'article team section headings mismatch Crown fixture','fid':q['fid'],
    'teams':[t['name'] for t in m['teams']]});continue
  ah=rr['markets']['AH']
  eligible.append({'fid':q['fid'],'source_url':s['url'],'source_date':s['source_date'],
   'source_published_utc':s['published_utc'],'source_modified_utc':s['modified_utc'],
   'source_html_sha256':s['saved_html_sha256'],'home':q['home'],'away':q['away'],
   'kickoff_utc':q['kickoff_utc'],'T12_received_utc':rr['received_utc'],
   'T12_AH_source_event_utc':ah['source_event_utc'],
   'T12_AH_line':ah['line'],'T12_home_odds':ah['odds']['home'],'T12_away_odds':ah['odds']['away'],
   'source_was_modified_hours_before_T12':round((recv-mod).total_seconds()/3600,4),
   'players':m['teams'],
   'home_reported_injured_n':len(m['teams'][0]['injured']),
   'home_reported_suspended_n':len(m['teams'][0]['suspended']),
   'home_reported_doubtful_n':len(m['teams'][0]['doubtful']),
   'away_reported_injured_n':len(m['teams'][1]['injured']),
   'away_reported_suspended_n':len(m['teams'][1]['suspended']),
   'away_reported_doubtful_n':len(m['teams'][1]['doubtful'])})
out={'research_id':'M8_R61_DATED_TEAM_NEWS_SOURCE_AUDIT',
 'method':'News source is single dated editorial public snapshot (Guardian pre-match injury/suspension/doubtful player lists), not initial official club confirmation. Source html saved as raw bytes SHA256. Both publish and last-modified UTC must predate actual T12 Crown HTTP receipt; otherwise reject. Match by explicit name and exact Crown fixture ID from raw HTTP, league and kickoff. Retrospective scrape on 2026 Nov18 is not contemporaneous captured news. Reported injured/suspended treated as quoted on published snapshot, doubt separate, not certainty of an actual game-day absence; no claim first-ever disclosure. Counting unavailable players equally is descriptive only, not weighted football edge or user production gate. Do not classify risk as realized without posted lineup. Only Crown AH lines and prices. No future T1 membership as early feature. No TG sends or book fills.',
 'sources':[{k:v for k,v in x.items() if k!='matches'}|{'matches_listed':len(x['matches']),
  'team_sections_total':sum(len(y['teams']) for y in x['matches'])} for x in sources],
 'matching':{'Crown_EPL_receipt_matches':len(real),'news_matches_total':sum(len(x['matches']) for x in sources),
  'eligible_news_T12_exact_pairs':len(eligible),'rejected_n':len(rejected),'rejected':rejected},
 'fixtures':eligible}
assert len({f['fid'] for f in eligible})==len(eligible)
(SOURCE/'R61_dated_news_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('COVERAGE',out['matching']['Crown_EPL_receipt_matches'],out['matching']['news_matches_total'],out['matching']['eligible_news_T12_exact_pairs'], 'rejected',len(rejected))
print('REJECTION_CODES',dict(collections.Counter(x['reason'] for x in rejected)),flush=True)
for row in eligible:
 print('FIX',row['source_date'],row['fid'],row['home'],'-',row['away'],
  row['home_reported_injured_n'],row['home_reported_suspended_n'],
  row['away_reported_injured_n'],row['away_reported_suspended_n'],
  'lag',row['source_was_modified_hours_before_T12'],flush=True)
