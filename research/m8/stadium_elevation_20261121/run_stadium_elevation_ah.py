#!/usr/bin/env python3
"""Time-forward test of pre-match modal-ground elevation mismatch vs Crown AH."""
from __future__ import annotations
import collections,datetime as dt,gzip,hashlib,json,math,pathlib
import numpy as np

OUT=pathlib.Path(__file__).resolve().parent
INV=OUT/'altitude_target_inventory_20261121.jsonl.gz'
COORDS=OUT/'venue_coordinates_20261121.jsonl'
ELEV=OUT/'srtm90m_manifest_20261121.jsonl'
FROZEN=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
ALPHA=20.0
def readj(path):
 opener=gzip.open if str(path).endswith('.gz') else open
 with opener(path,'rt',encoding='utf8') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def norm(s):
 import re,unicodedata
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]','',s)
def phi(z):return .5*(1+math.erf(z/math.sqrt(2)))
def margin_dist(mu,sigma):
 gs=list(range(-15,16));ps=[]
 for g in gs:
  if g==-15:p=phi((-14.5-mu)/sigma)
  elif g==15:p=1-phi((14.5-mu)/sigma)
  else:p=phi((g+.5-mu)/sigma)-phi((g-.5-mu)/sigma)
  ps.append(max(0.,p))
 z=sum(ps);return gs,[p/z for p in ps]
def settle(line,side,odds,gd):
 handicap=float(line) if side=='home' else -float(line)
 team_gd=int(gd) if side=='home' else -int(gd)
 lo=math.floor(handicap*2+1e-9)/2;hi=math.ceil(handicap*2-1e-9)/2
 legs=[handicap] if abs(handicap*2-round(handicap*2))<1e-8 else [lo,hi]
 vals=[float(odds)-1 if team_gd+h>1e-9 else -1. if team_gd+h<-1e-9 else 0. for h in legs]
 label='full_win' if all(x>0 for x in vals) else 'half_win' if any(x>0 for x in vals) else 'push' if all(x==0 for x in vals) else 'half_loss' if any(x==0 for x in vals) else 'full_loss'
 return sum(vals)/len(vals),label
def ev(line,side,odds,gd,prob):return sum(p*settle(line,side,odds,g)[0] for g,p in zip(gd,prob))
def xvec(r,kind):
 line=float(r['crown_line_home']);h=float(r['crown_home_decimal']);a=float(r['crown_away_decimal'])
 market=[1.,-line,abs(line),math.log(a/h)]
 t=r['strictly_prior_team_history']
 def v(name):return 0. if t.get(name) is None else float(t[name])
 team=[v('home_market_adjusted_prior365'),v('away_market_adjusted_prior365'),
  v('home_market_adjusted_last5'),v('away_market_adjusted_last5'),
  math.log1p(max(0.,v('home_market_prior365_n'))),math.log1p(max(0.,v('away_market_prior365_n')))]
 if kind=='market_only':return np.asarray(market,dtype=float)
 if kind=='market_team':return np.asarray(market+team,dtype=float)
 if kind=='market_team_elevation':
  home=float(r['home_ground_elevation_m']);away=float(r['away_ground_elevation_m'])
  return np.asarray(market+team+[(home-away)/1000.,home/1000.],dtype=float)
 raise KeyError(kind)
def fit(X,y):
 mu=X.mean(0);sd=X.std(0);sd[sd<1e-10]=1.;Z=(X-mu)/sd;ym=float(y.mean())
 b=np.linalg.solve(Z.T@Z+ALPHA*np.eye(Z.shape[1]),Z.T@(y-ym));return mu,sd,ym,b
def pred(x,m):mu,sd,ym,b=m;return float(((x-mu)/sd)@b+ym)
def stats(rows,observation_iso_weeks=None):
 rows=list(rows);n=len(rows);u=sum(float(r['net_u']) for r in rows);st=collections.Counter(r.get('settlement','frozen_member_pnl') for r in rows)
 days=collections.defaultdict(float);weeks=collections.defaultdict(lambda:[0,0.]);months=collections.defaultdict(lambda:[0,0.]);leagues=collections.defaultdict(lambda:[0,0.]);years=collections.defaultdict(lambda:[0,0.])
 for r in rows:
  d=dt.date.fromisoformat(r['date']);days[d]+=float(r['net_u']);iso=d.isocalendar();wk=f'{iso.year}-W{iso.week:02d}';mo=d.strftime('%Y-%m');y=str(d.year)
  weeks[wk][0]+=1;weeks[wk][1]+=float(r['net_u']);months[mo][0]+=1;months[mo][1]+=float(r['net_u']);leagues[str(r['league'])][0]+=1;leagues[str(r['league'])][1]+=float(r['net_u']);years[y][0]+=1;years[y][1]+=float(r['net_u'])
 eq=peak=mdd=0.
 for d,v in sorted(days.items()):eq+=v;peak=max(peak,eq);mdd=max(mdd,peak-eq)
 if observation_iso_weeks is not None:nweeks=int(observation_iso_weeks)
 elif rows:
  lo=min(dt.date.fromisoformat(r['date']) for r in rows);hi=max(dt.date.fromisoformat(r['date']) for r in rows)
  codes=set();day=lo
  while day<=hi:
   iso=day.isocalendar();codes.add((iso.year,iso.week));day+=dt.timedelta(days=1)
  nweeks=len(codes)
 else:nweeks=0
 fmt=lambda z:{k:{'orders':v[0],'net_u':round(v[1],6),'roi_pct':round(100*v[1]/v[0],6) if v[0] else None} for k,v in sorted(z.items())}
 return {'orders':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,'mdd_u':round(mdd,6),
   'settlements':dict(st),'avg_decimal_odds':round(sum(float(r['price']) for r in rows if r.get('price') is not None)/sum(r.get('price') is not None for r in rows),6) if n and any(r.get('price') is not None for r in rows) and all(r.get('price') is not None for r in rows) else None,
   'observation_iso_weeks':nweeks,'weekly_avg_orders':round(n/nweeks,6) if nweeks else None,
   'active_iso_weeks':len(weeks),'active_week_avg_orders':round(n/len(weeks),6) if weeks else None,
   'by_year':fmt(years),'by_month':fmt(months),'by_league':fmt(leagues),
   'weekly':{k:{'orders':v[0],'net_u':round(v[1],6)} for k,v in sorted(weeks.items())}}
def main():
 inv=list(readj(INV));assert len({r['fid'] for r in inv})==len(inv),'duplicate inventory FID'
 coord_by_key={}
 for r in readj(COORDS):coord_by_key[(r['venue'],r['country_query'])]=f"{float(r['latitude']):.6f},{float(r['longitude']):.6f}"
 elev_by_id={}
 for line in ELEV.open(encoding='utf8'):
  r=json.loads(line)
  if r.get('status')!='success':continue
  for x in r['results']:elev_by_id[x['coordinate_id']]=x.get('elevation_m')
 for r in inv:
  hk=(r.get('pregame_home_venue_proxy'),r.get('competition_country'));ak=(r.get('pregame_away_home_venue_proxy'),r.get('competition_country'))
  hi=coord_by_key.get(hk);ai=coord_by_key.get(ak);he=elev_by_id.get(hi) if hi else None;ae=elev_by_id.get(ai) if ai else None
  r['home_venue_coordinate_id']=hi;r['away_home_venue_coordinate_id']=ai
  r['home_ground_elevation_m']=he;r['away_ground_elevation_m']=ae
  r['elevation_delta_home_minus_away_m']=round(he-ae,4) if he is not None and ae is not None else None
  r['home_venue_proxy_exactly_matches_target_site_diagnostic']=bool(r.get('pregame_home_venue_proxy') and norm(r['pregame_home_venue_proxy'])==norm(r.get('stadium_actual_postmatch_diagnostic')))
  r['feature_complete']=all(x is not None for x in (he,ae,*[r['strictly_prior_team_history'].get(k) for k in ('home_market_adjusted_prior365','away_market_adjusted_prior365','home_market_adjusted_last5','away_market_adjusted_last5')]))
 rows=[r for r in inv if r['feature_complete']]
 rows.sort(key=lambda x:(x['year'],x['date'],x['fid']))
 frozen={str(json.loads(x)['fid']):json.loads(x) for x in FROZEN.open(encoding='utf8') if x.strip()}
 predictions=[];folds={};method_rows=collections.defaultdict(list)
 for year in (2024,2025,2026):
  train=[r for r in rows if int(r['year'])<year]
  test=[r for r in rows if int(r['year'])==year]
  folds[str(year)]={'train_n':len(train),'train_years':sorted({int(r['year']) for r in train}),'test_feature_complete_n':len(test),'alpha':ALPHA,'strict_expanding_years':True}
  if not train or not test:folds[str(year)]['status']='insufficient';continue
  y=np.asarray([int(r['ft_home'])-int(r['ft_away']) for r in train],dtype=float);specs={}
  for name in ('market_only','market_team','market_team_elevation'):
   X=np.vstack([xvec(r,name) for r in train]);m=fit(X,y);resid=y-np.asarray([pred(xvec(r,name),m) for r in train]);sigma=max(.75,float(np.std(resid,ddof=1)));specs[name]=(m,sigma)
  folds[str(year)].update({'status':'fit','training_rows_same_common_coverage':True,'model_names':list(specs)})
  for r in test:
   out={k:r[k] for k in ('fid','year','date','league','home','away','frozen_original_eight','crown_line_home','crown_home_decimal','crown_away_decimal','ft_home','ft_away','pregame_home_venue_proxy','pregame_away_home_venue_proxy','home_ground_elevation_m','away_ground_elevation_m','elevation_delta_home_minus_away_m','home_venue_proxy_exactly_matches_target_site_diagnostic','stadium_actual_postmatch_diagnostic')}
   out['kickoff_utc']=r['kickoff_utc'];out['quote_source']='historical Crown T1 source-event; not receipt';out['models']={}
   for name,(m,sigma) in specs.items():
    mu=pred(xvec(r,name),m);gd,prob=margin_dist(mu,sigma);line=float(r['crown_line_home'])
    eh=ev(line,'home',float(r['crown_home_decimal']),gd,prob);ea=ev(line,'away',float(r['crown_away_decimal']),gd,prob)
    side='home' if eh>=ea else 'away';best=max(eh,ea);price=float(r['crown_home_decimal'] if side=='home' else r['crown_away_decimal'])
    pnl,state=settle(line,side,price,int(r['ft_home'])-int(r['ft_away']))
    mrow={'predicted_home_margin':round(mu,8),'residual_sigma':round(sigma,8),'home_EV_U':round(eh,8),'away_EV_U':round(ea,8),'direction':side,'price':price,'settlement':state,'net_u':round(pnl,8),'max_predicted_EV_U':round(best,8)}
    out['models'][name]=mrow
    if not r['frozen_original_eight']:
     method_rows[name+'_always_bet'].append({**out,**mrow,'method':name+'_always_bet'})
     if best>0:
      method_rows[name+'_EV_positive_no_bet_diagnostic'].append({**out,**mrow,'method':name+'_EV_positive_no_bet_diagnostic'})
   predictions.append(out)
 # Write one prediction row per fixture; candidate orders are separate fixed-direction ledgers.
 with gzip.open(OUT/'altitude_per_fixture_predictions_20261121.jsonl.gz','wt',encoding='utf8') as f:
  for r in predictions:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 summary={'study':'Pregame prior-home-ground elevation differential added to Crown AH forecast; historical research only','sample':{'inventory_rows':len(inv),'feature_complete':len(rows),'candidate_outside_eight_feature_complete':sum(not r['frozen_original_eight'] for r in rows),'candidate_outside_eight_test_feature_complete':sum(not r['frozen_original_eight'] and r['year'] in (2024,2025,2026) for r in rows),'strict_prior_venue_matches_actual_postmatch_diagnostic':sum(r['home_venue_proxy_exactly_matches_target_site_diagnostic'] for r in rows),'strict_prior_venue_proxy_rows':len(rows)},'training_folds':folds,'methods':{}}
 for name,ledger in method_rows.items():summary['methods'][name]={'all':stats(ledger),'2024':stats(r for r in ledger if r['year']==2024),'2025':stats(r for r in ledger if r['year']==2025),'2026':stats(r for r in ledger if r['year']==2026)}
 candidates=[r for r in rows if not r['frozen_original_eight'] and int(r['year']) in (2024,2025,2026)]
 overlap={r['fid'] for r in candidates}&set(frozen)
 assert not overlap,f'new candidates overlap frozen FIDs: {len(overlap)}'
 def iso_weeks(group):
  ds=[dt.date.fromisoformat(r['date']) for r in group]
  if not ds:return 0
  codes=set();day=min(ds);last=max(ds)
  while day<=last:
   iso=day.isocalendar();codes.add((iso.year,iso.week));day+=dt.timedelta(days=1)
  return len(codes)
 observations={'all_2024_2026':iso_weeks(candidates),**{str(y):iso_weeks([r for r in candidates if int(r['year'])==y]) for y in (2024,2025,2026)}}
 summary['new_candidate_observation_weeks']=observations
 summary['new_candidate_frozen_fid_overlap']=len(overlap)
 frozen_rows=[{'fid':fid,'date':r['date'],'league':str(r['league']),'net_u':float(r['pnl']),'settlement':'frozen_member_pnl'} for fid,r in frozen.items() if 2024<=int(r['year'])<=2026 and (int(r['year'])<2026 or str(r['date'])<='2026-07-06')]
 summary['frozen_base_same_calendar_windows']=stats(frozen_rows)
 summary['combined_same_calendar_windows']={}
 for name,ledger in method_rows.items():
  summary['methods'][name]['all']['weekly_avg_orders']=round(summary['methods'][name]['all']['orders']/observations['all_2024_2026'],6) if observations['all_2024_2026'] else None
  for y in (2024,2025,2026):summary['methods'][name][str(y)]['weekly_avg_orders']=round(summary['methods'][name][str(y)]['orders']/observations[str(y)],6) if observations[str(y)] else None
  summary['combined_same_calendar_windows'][name]=stats(frozen_rows+ledger,observations['all_2024_2026'])
 summary['frozen_membership_sha256']=sha(FROZEN);summary['input_sha256']={str(INV):sha(INV),str(COORDS):sha(COORDS),str(ELEV):sha(ELEV),str(FROZEN):sha(FROZEN)}
 (OUT/'altitude_crown_ah_summary_20261121.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 for name,ledger in method_rows.items():
  with gzip.open(OUT/f'altitude_orders_{name}_20261121.jsonl.gz','wt',encoding='utf8') as f:
   for r in ledger:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 print(json.dumps({'sample':summary['sample'],'folds':folds,'methods':{k:v['all'] for k,v in summary['methods'].items()}},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
