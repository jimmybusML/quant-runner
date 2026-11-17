import datetime,concurrent.futures,requests,bs4,re,json,hashlib,collections,threading
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
cache=P/'m8_r62_full_season_guardian_source_20261118'
cache.mkdir(exist_ok=True)
prev=(P/'m8_r61_dated_team_news_audit_20261118.py').read_text()
exec(prev[:prev.index('sources=[]')])
FRIDAYS=[]
d=datetime.date(2024,1,5)
while d<=datetime.date(2025,12,26):
 if d.month not in (6,7):
  FRIDAYS.append(d)
 d+=datetime.timedelta(days=7)
# Known Friday article slugs often have path football or sport.
STANDARD='premier-league-team-news-predicted-lineups-for-the-weekend-action'
ALTERNATE='premier-league-team-news-predicted-lineups'
EXTRA='premier-league-team-news-predicted-lineups-for-the-opening-weekend'
ALL={}
for y in (2024,2025):
 file=P/'m8_r61_dated_team_news_source_20261118'/f'{y}-10-09.html'
# The old R61 in-range source URL is reused via persisted JSON if Friday
# lands in current R61 dates; a modified duplicate isn't counted again.
prior=json.loads((P/'m8_r61_prior_year_news_stress_20261118.json').read_text())
existing={x['source_date']:x['url'] for x in prior['sources']}
def one(date):
 iso=date.isoformat();mm=date.strftime('%b').lower()
 base=f'https://www.theguardian.com'
 variants=[]
 if iso in existing:variants.append(existing[iso])
 for cat in ('football','sport'):
  variants.append(f'{base}/{cat}/{date.year}/{mm}/{date.day:02d}/{STANDARD}')
  variants.append(f'{base}/{cat}/{date.year}/{mm}/{date.day:02d}/{ALTERNATE}')
 if date.month==8:
  variants.extend([
    f'{base}/football/article/{date.year}/{mm}/{date.day:02d}/{EXTRA}',
    f'{base}/football/article/{date.year}/{mm}/{date.day:02d}/{STANDARD}'])
 variants=list(dict.fromkeys(variants))
 outcome=[]
 for url in variants:
  try:
   resp=requests.get(url,timeout=13,headers={'User-Agent':'Mozilla/5.0'})
   if resp.status_code!=200:continue
   s=bs4.BeautifulSoup(resp.content,'html.parser')
   meta=s.find('meta',attrs={'property':'article:published_time'})
   mod=s.find('meta',attrs={'property':'article:modified_time'})
   body=s.select_one('.article-body-commercial-selector')
   if not (meta and mod and body):continue
   if not (len([h for h in body.select('h2') if re.search(r' v ',h.get_text(' ',strip=True))])>=3):continue
   # Explicit day matches avoids a redirected unrelated article.
   publish=meta.get('content')
   if not publish.startswith(iso):
    continue
   raw=resp.content
   cache.joinpath(iso+'.html').write_bytes(raw)
   return {'day':iso,'url':url,'published_utc':publish,'modified_utc':mod.get('content'),
      'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
      'H2_fixtures':len([h for h in body.select('h2') if re.search(r' v ',h.get_text(' ',strip=True))])}
  except Exception as exc:
   outcome.append(type(exc).__name__)
 return {'day':iso,'not_found':True,'issues':dict(collections.Counter(outcome))}
result=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
 tasks={pool.submit(one,d):d for d in FRIDAYS}
 for fut in concurrent.futures.as_completed(tasks):
  result.append(fut.result())
  if len(result)%20==0:
   print('PROGRESS',len(result),'found',sum('url'in x for x in result),flush=True)
result.sort(key=lambda x:x['day'])
out={'method':'R62 evidence of available full-season dated Guardian pregame news inventory; only Fri editions in 2024/2025, skipped summer June/July, exact published date and >=3 match h2 headings; dedupe by issue date, source raw HTML SHA. This is a non-exhaustive discoverable editorial sample, NOT randomized all league games or contemporaneous 2024/25 HTTP receipt. Crown still only odds source.',
 'fridays_attempted':len(FRIDAYS),'found':sum('url'in z for z in result),
 'by_year':{str(y):{'attempted':sum(z['day'][:4]==str(y) for z in result),
  'found':sum(z['day'][:4]==str(y) and 'url' in z for z in result)} for y in (2024,2025)},
 'pages':result}
P.joinpath('m8_r62_full_season_guardian_discovery_20261118.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('FINISHED',out['fridays_attempted'],out['found'],out['by_year'])
