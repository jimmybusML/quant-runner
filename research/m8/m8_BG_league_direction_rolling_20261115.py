from pathlib import Path
import json,collections,statistics,math
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_BG_expanded_attribution_20261115.py').read_text().rsplit("out={}",1)[0])
def side(r):
 if r['sample']=='new':return r['side']
 if r['cohort']=='B':return 'home' if r['end_line']>0 else 'away'
 return 'away' if r['away_price']/(r['home_price']+r['away_price'])>r['start_away_price']/(r['start_home_price']+r['start_away_price']) else 'home'
# previous baseline exact rechecked against historical side and payoff
Z=[]
for r in old+extra:
 if r['cohort'] not in ('B','G'):continue
 sd=side(r);opp='home' if sd=='away' else 'away'
 assert abs(r['pnl']-r['end_'+sd+'_U'])<1e-7,(r['fid'],r['cohort'])
 Z.append({**r,'reverse':r['end_'+opp+'_U']})
def stats(v):
 n=len(v);u=sum(v);return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
out={}
for g in ('B','G'):
 rs=[r for r in Z if r['cohort']==g];out[g]={}
 for yr in (2024,2025,2026):
  tr=[r for r in rs if r['year']<yr];te=[r for r in rs if r['year']==yr]
  # Compare choosing side on all training matches, and league-adjusted difference shrunk toward the overall historical gap.
  # 20 is a numerical shrinkage experiment, not a production eligibility rule; no match excluded.
  gap=sum(r['pnl']-r['reverse'] for r in tr)/len(tr)
  by=collections.defaultdict(list)
  for r in tr:by[r['league']].append(r['pnl']-r['reverse'])
  def ev(r):
   a=by[r['league']]
   return (sum(a)+20*gap)/(len(a)+20)
  q={'baseline':stats([r['pnl'] for r in te]),'reverse_all':stats([r['reverse'] for r in te]),'global_historical_choice':stats([r['pnl'] if gap>=0 else r['reverse'] for r in te]),'league_historical_choice':stats([r['pnl'] if ev(r)>=0 else r['reverse'] for r in te]),'league_reversed_count':sum(ev(r)<0 for r in te),'historical_gap':round(gap,5)}
  for sub in ('old','new'):
   a=[r for r in te if r['sample']==sub]
   q[sub]={'baseline':stats([r['pnl'] for r in a]),'league_choice':stats([r['pnl'] if ev(r)>=0 else r['reverse'] for r in a])}
  out[g][str(yr)]=q
  print('ROLL',g,yr,q,flush=True)
(P/'m8_BG_league_direction_rolling_20261115.json').write_text(json.dumps(out,indent=2))
