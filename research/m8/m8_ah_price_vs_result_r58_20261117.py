import json,hashlib,collections
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_received_price_chain_r57_20261117.py').read_text()
exec(s[:s.index("out={'research_id'")])
# Receipts, hashes, identity, FT were independently checked in the R57 prefix.
# No outcome / future price enters the AH choice at T12.
assert len(chosen)==1230 and np.array_equal(positive,forecast_best>0)
def stat(p):
 z=np.asarray(p,float)
 return {'n':len(z),'U':round(float(z.sum()),3),
  'ROI':round(100*float(z.mean()),3) if len(z) else None,
  'win':int((z>1e-9).sum()),'loss':int((z<-1e-9).sum()),
  'push':int((abs(z)<=1e-9).sum())}
def cluster_ci(v,dates,reps=3000,seed=58):
 a=np.asarray(v,float)
 if len(a)<2:return None
 ix=collections.defaultdict(list)
 for v0,d in zip(a,dates):ix[d].append(v0)
 U=np.array([sum(v) for v in ix.values()]);N=np.array([len(v) for v in ix.values()])
 rng=np.random.default_rng(seed)
 ss=rng.integers(len(U),size=(reps,len(U)))
 b=100*U[ss].sum(1)/N[ss].sum(1)
 return [round(float(x),3) for x in np.quantile(b,[.025,.975])]
# Fractional AH settlement is affine in decimal quote odds:
# payout = (odds-1)*won_stake_fraction - lost_stake_fraction.
# Infer win fraction from two legal decimal odds, not 1/odds binary guesses.
def winloss(side,line,hg,ag):
 home=bool(side)
 p2=settle_score('AH',line,'home' if home else 'away',int(hg),int(ag),2.0)[1]
 p3=settle_score('AH',line,'home' if home else 'away',int(hg),int(ag),3.0)[1]
 w=p3-p2
 l=w-p2
 assert min(w,l)>-1e-8 and w+l<=1.00000001,(side,line,hg,ag,w,l)
 return max(w,0.),max(l,0.)
def break_even(groups):
 if not groups:return {'n':0}
 actual,decimal,w,l=map(np.array,zip(*groups))
 assert np.max(abs(actual-((decimal-1)*w-l)))<1e-8
 win=w.sum();loss=l.sum()
 return {'n':len(groups),'payout':stat(actual),
  'avg_decimal_odds':round(float(decimal.mean()),5),
  'avg_won_stake_fraction':round(float(w.mean()),5),
  'avg_lost_stake_fraction':round(float(l.mean()),5),
  'observed_expost_break_even_decimal':round(float(1+loss/win),5) if win>0 else None,
  'required_uniform_extra_odds_to_break_even_expost':round(float(-actual.sum()/win),5) if win>0 else None}
# Historic multi-year chronological testing; do not exclude frozen8 based
# on T1 future stage. Members only shown in a separate attribution view.
hist_d=D['T12'];X=hist_d['X'];Y=hist_d['y']
yr=hist_d['year'];prev_ok=hist_d['disjoint']
months=np.array([q['date'] for q in hist_d['now']])
hp=hist_d['home_pay'];ap=hist_d['away_pay']
predh=np.zeros((len(yr),2))
for yr0 in (2024,2025,2026):
 tr=(yr<yr0)&prev_ok;te=(yr==yr0)
 val,_=regression(X[tr],Y[tr],X[te])
 predh[te]=val
side_h=predh[:,0]>=predh[:,1]
opp_h=np.where(side_h,ap,hp)
fav_h=np.where(side_h,hp,ap)
op_h=predh.max(1)>0
hsel=yr>=2024
out={'study_id':'M8_R58_AH_PRICE_VS_OUTCOME',
 'method':'R58 disentangles price shortening vs settlement by computing fractional AH settled win/loss stake and two-sided counterfactual. Most important live-like selection: previous-calendar-year fit from strictly T24/T12 AH Crown feature, same selected side for outcomes and CLV measured only on post-selection T6 real receipts; raw snapshot receipt SHA/identity/FT revalidated by R57 prefix. Hindsight T6 matching line is a DIAGNOSTIC only. New reverse-side evaluations are explored AFTER R57 was seen and therefore not independent precommitted out-of-sample even if positive. No new trading rule/gate; no future T1 membership used to define actual-time eligible cohort. Original frozen8 unmodified, OU unrelated. Book overround is a proxy, not exact fractional-handicap fee or expected EV. Ex-post break-even decimal odds use realized match results and are NOT expected true fair odds. Historic Crown quotes are post-retrieved source timestamps, no proof of actual historical receipt. No TG orders or actual fills.',
 'history':{},'receipts':{},'market_movement':{},'source':{'verified_t12':len(chosen)},'foundation':{}}
for y0 in (2024,2025,2026):
 mask=(yr==y0)
 z={}
 for k,cohort in [('all',mask),('predict_price_opportunity',mask&op_h),
  ('predict_price_not_opportunity',mask&~op_h)]:
  chosen_side=fav_h[cohort];contra=opp_h[cohort]
  tdates=months[cohort]
  z[k]={'normal':stat(chosen_side),'reverse':stat(contra),
   'normal_day_bootstrap95':cluster_ci(chosen_side,tdates),
   'reverse_day_bootstrap95':cluster_ci(contra,tdates)}
 out['history'][str(y0)]=z
 print('HISTORY',y0,{k:{m:v[m] for m in ('normal','reverse')} for k,v in z.items()},flush=True)
# Reproduce the earlier actual receipt data frame, and compute reverse
# results at SAME original received T12 AH price (not other-bookmaker prices).
dates=np.array([b['date'] for a,b,c,l in chosen])
is_frozen=np.array([b['fid'] in ids for a,b,c,l in chosen])
opp_pnl=np.array([b['away_U'] if side else b['home_U'] for (a,b,c,l),side in zip(chosen,buy_home)])
for name,mask in [('all',np.ones(len(chosen),bool)),
 ('price_opportunity',positive),('price_not_opportunity',~positive),
 ('hindsight_inside_eight',is_frozen),('hindsight_outside_eight',~is_frozen),
 ('price_opportunity_hindsight_outside_eight',positive&~is_frozen)]:
 pos=np.flatnonzero(mask)
 cohorts=[]
 for i in pos:
  _,b,c,later=chosen[i]
  side=buy_home[i]
  odd=c['home_odds'] if side else c['away_odds']
  w,l=winloss(side,c['line'],b['hg'],b['ag'])
  cohorts.append((base_pnl[i],odd,w,l))
 a=break_even(cohorts)
 out['receipts'][name]={'chosen_side':stat(base_pnl[mask]),
  'reversed_side':stat(opp_pnl[mask]),
  'reversed_side_day_bootstrap95':cluster_ci(opp_pnl[mask],dates[mask]),
  'chosen_day_bootstrap95':cluster_ci(base_pnl[mask],dates[mask]),
  'settlement_decomposition':a}
 print('RECEIPT',name,'normal',out['receipts'][name]['chosen_side'],'contra',out['receipts'][name]['reversed_side'],'BE',a,flush=True)
# The following future subsets are explanatory post-hoc only, not a
# selection in any simulated T12 strategy.
for name,mask in [('price_opportunity',positive),
 ('price_not_opportunity',~positive),
 ('all',np.ones(len(chosen),bool))]:
 sub=collections.defaultdict(list)
 for i in np.flatnonzero(mask):
  a,b,c,later=chosen[i]
  q=later.get('T6')
  if q is None:continue
  side=buy_home[i]
  now=c['home_odds'] if side else c['away_odds']
  future=q['home_odds'] if side else q['away_odds']
  othernow=c['away_odds'] if side else c['home_odds']
  otherfuture=q['away_odds'] if side else q['home_odds']
  v_now=(1/c['home_odds']+1/c['away_odds']-1)
  v_later=(1/q['home_odds']+1/q['away_odds']-1)
  same=c['line']==q['line']
  if same:
   w,l=winloss(side,c['line'],b['hg'],b['ag'])
   sub['same_line_observations'].append((i,base_pnl[i],now,w,l,now-future,othernow-otherfuture,v_now,v_later))
   if (q['source_event']-c['source_event']).total_seconds()>0:
    sub['same_line_fresh'].append((i,base_pnl[i],now,w,l,now-future,othernow-otherfuture,v_now,v_later))
   if now>future+1e-9:sub['actually_shortened'].append((i,base_pnl[i],now,w,l,now-future,othernow-otherfuture,v_now,v_later))
   elif now<future-1e-9:sub['actually_lengthened'].append((i,base_pnl[i],now,w,l,now-future,othernow-otherfuture,v_now,v_later))
   else:sub['actually_unchanged'].append((i,base_pnl[i],now,w,l,now-future,othernow-otherfuture,v_now,v_later))
  else:
   sub['changed_handicap_line'].append((i,base_pnl[i],now,None,None,None,None,v_now,v_later))
 ret={}
 for label,vs in sub.items():
  idx=[r[0] for r in vs]
  x={'n':len(vs),'T12_settlement':stat([r[1] for r in vs]),
     'same_line_only':label!='changed_handicap_line',
     'T12_book_two_sided_overround_proxy_mean':round(float(np.mean([r[7] for r in vs])),5),
     'T6_book_two_sided_overround_proxy_mean':round(float(np.mean([r[8] for r in vs])),5)}
  if label!='changed_handicap_line':
   x['T12_selected_odds_mean']=round(float(np.mean([r[2] for r in vs])),5)
   x['odds_shortening_mean']=round(float(np.mean([r[5] for r in vs])),6)
   x['other_side_odds_shortening_mean']=round(float(np.mean([r[6] for r in vs])),6)
   x['odds_change_opposite_sign_pct']=round(float(np.mean([r[5]*r[6]<-1e-9 for r in vs]))*100,3)
   x['odds_change_both_same_sign_pct']=round(float(np.mean([r[5]*r[6]>1e-9 for r in vs]))*100,3)
   x['break_even']=break_even([(r[1],r[2],r[3],r[4]) for r in vs])
  ret[label]=x
 out['market_movement'][name]=ret
 print('MARKET',name,[(k,v['n'],v['T12_settlement']['ROI'],v.get('odds_shortening_mean'),v.get('break_even',{}).get('required_uniform_extra_odds_to_break_even_expost')) for k,v in ret.items()],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_ah_price_vs_result_r58_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('SAVED',flush=True)
