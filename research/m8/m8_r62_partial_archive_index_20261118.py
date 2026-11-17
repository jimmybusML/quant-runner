import json,collections,hashlib,datetime,bs4,shutil
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
folder=P/'m8_r62_full_season_guardian_source_20261118'
oldfolder=P/'m8_r61_dated_team_news_source_20261118'
old=json.loads((P/'m8_r61_prior_year_news_stress_20261118.json').read_text())
for q in old['sources']:
 day=q['source_date']
 f=oldfolder/(day+'.html')
 assert f.exists()
 out=folder/(day+'.html')
 if not out.exists():shutil.copyfile(f,out)
res=[]
for f in sorted(folder.glob('202*.html')):
 soup=bs4.BeautifulSoup(f.read_bytes(),'html.parser')
 meta=lambda k:soup.find('meta',attrs={'property':k})
 published=meta('article:published_time')
 modified=meta('article:modified_time')
 url=soup.find('link',attrs={'rel':'canonical'})
 assert published and modified and url,(f,published,modified,url)
 pub=published.get('content')
 assert pub[:10]==f.stem,(f,pub)
 body=soup.select_one('.article-body-commercial-selector')
 assert body is not None
 n=sum(' v ' in h.get_text(' ',strip=True) for h in body.select('h2'))
 assert n>=3,(f,n)
 res.append({'day':f.stem,'url':url.get('href'),'published_utc':pub,
  'modified_utc':modified.get('content'),
  'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),
  'H2_fixtures':n,'bytes':f.stat().st_size})
# The original online discovery was interrupted by host proxy timeout. This
# ledger is a partial cached corpus, NOT a full season.
out={'method':'Source inventory from already saved local 2024/25 Friday Guardian pregame news. Exact published and last modified UTC, canonical url, raw SHA. Network discovery incomplete due localhost proxy outage during batch scan, so not full-season coverage, and no fabricated missing source claims.',
 'fridays_attempted':len(res),'found':len(res),
 'by_year':{str(y):{'attempted':sum(r['day'][:4]==str(y) for r in res),
  'found':sum(r['day'][:4]==str(y) for r in res)} for y in (2024,2025)},
 'pages':res,
 'discovery_incomplete':True,'blocker':'Host HTTP proxy 127.0.0.1:1082 stopped responding while requesting historical Guardian pages. Full-year coverage not established; these are all already downloaded pages.'}
(P/'m8_r62_full_season_guardian_discovery_20261118.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('RECONSTRUCTED_SOURCE',out['by_year'],'pages',len(res),'fixture_sections',sum(z['H2_fixtures'] for z in res))
