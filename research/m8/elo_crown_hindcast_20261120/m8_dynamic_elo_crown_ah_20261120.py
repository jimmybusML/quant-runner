#!/usr/bin/env python3
"""Time-forward dynamic Elo information test against Crown AH pricing.

Research-only. Uses cached M8 score/Crown features and archived true Crown
receipts; does not collect data or touch production.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, sys
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax

ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=pathlib.Path(__file__).resolve().parent
SCORES=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl')
MARKETS=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl')
FROZEN=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
RECEIPTS=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
VERIFIED_FT=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m7/m7_actual_received_Crown_verified_FT_index_20261110_v3.jsonl')
MODEL_LEDGER=OUT/'m8_dynamic_elo_crown_ah_predictions_20261120.jsonl.gz'
RECEIPT_LEDGER=OUT/'m8_dynamic_elo_crown_ah_true_receipt_replay_20261120.jsonl.gz'
SUMMARY=OUT/'m8_dynamic_elo_crown_ah_summary_20261120.json'
METHODS=('CROWN_ONLY','ELO_CONTRACT','CROWN_PLUS_ELO')
STATES=('full_loss','half_loss','push','half_win','full_win')
STATE_INDEX={s:i for i,s in enumerate(STATES)}
TARGET_YEARS=(2024,2025,2026)
ELO_K=20.0; ELO_HOME_ADVANTAGE=65.0; ELO_BASE=1500.0
TRAIN_L2=1.0
CHINA_TZ=dt.timezone(dt.timedelta(hours=8))
BOOT_REPS=20000; BOOT_SEED=20261120

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read_jsonl(p):return [json.loads(x) for x in open(p,encoding='utf-8') if x.strip()]
def parse_utc(x):
 s=str(x).replace('Z','+00:00')
 t=dt.datetime.fromisoformat(s)
 if t.tzinfo is None:t=t.replace(tzinfo=dt.timezone.utc)
 return t.astimezone(dt.timezone.utc)
def settle(line,side,hg,ag,odds):
 line=float(line);odds=float(odds)
 if abs(line*4-round(line*4))>1e-7:raise ValueError(f'unsupported AH line {line}')
 legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 pn=[]
 for leg in legs:
  margin=hg-ag+leg if side=='home' else ag-hg-leg
  pn.append(odds-1 if margin>1e-9 else -1.0 if margin<-1e-9 else 0.0)
 state=('full_win' if all(x>0 for x in pn) else 'half_win' if any(x>0 for x in pn) else 'push' if all(x==0 for x in pn) else 'half_loss' if any(x==0 for x in pn) else 'full_loss')
 return sum(pn)/len(pn),state
def home_state(line,hg,ag):
 _,s=settle(line,'home',hg,ag,2.0)
 return s
def payout_vector(odds,side):
 base={'full_loss':-1.0,'half_loss':-0.5,'push':0.0,'half_win':(odds-1.0)/2.0,'full_win':odds-1.0}
 if side=='home':return np.array([base[s] for s in STATES],dtype=float)
 mirror={'full_loss':'full_win','half_loss':'half_win','push':'push','half_win':'half_loss','full_win':'full_loss'}
 return np.array([base[mirror[s]] for s in STATES],dtype=float)

def elo_features(score_rows, asof_by_fid=None):
 """League-team Elo; use only matches at least two UTC calendar days old."""
 matches=[]
 for r in score_rows:
  try:
   ko=parse_utc(r['ko']); hg=int(r['hg']);ag=int(r['ag']);lid=str(r['league']);h=str(r['home']);a=str(r['away'])
   if not lid or not h or not a or h==a:continue
   matches.append((ko.date(),ko,str(r['fid']),lid,h,a,hg,ag))
  except (KeyError,TypeError,ValueError):continue
 matches.sort(key=lambda z:(z[0],z[1],z[2]))
 targets=defaultdict_list()
 target_rows=collections.defaultdict(list)
 score_by_fid={str(r.get('fid')):r for r in score_rows}
 if asof_by_fid is None:
  for r in score_rows:
   try:
    day=parse_utc(r['ko']).date(); targets[day].append(str(r['fid'])); target_rows[day].append(r)
   except Exception:pass
 else:
  for fid,t in asof_by_fid.items():
   day=parse_utc(t).date();targets[day].append(str(fid))
   if str(fid) in score_by_fid:target_rows[day].append(score_by_fid[str(fid)])
 target_dates=sorted(targets)
 ratings=collections.defaultdict(lambda:ELO_BASE);out={};j=0
 for day in target_dates:
  cutoff=day-dt.timedelta(days=2)
  while j<len(matches) and matches[j][0]<=cutoff:
   # Batch all same-day results so no fixture on that day uses another same-day FT.
   match_day=matches[j][0];batch=[]
   while j<len(matches) and matches[j][0]==match_day:batch.append(matches[j]);j+=1
   deltas=collections.defaultdict(float)
   for _,ko,fid,lid,h,a,hg,ag in batch:
    hk=(lid,h);ak=(lid,a);rh=ratings[hk];ra=ratings[ak]
    exp=1.0/(1.0+10.0**(-((rh+ELO_HOME_ADVANTAGE-ra)/400.0)))
    act=1.0 if hg>ag else 0.5 if hg==ag else 0.0
    delta=ELO_K*(act-exp);deltas[hk]+=delta;deltas[ak]-=delta
   for k,v in deltas.items():ratings[k]+=v
  # Store neutral Elo difference for every fixture whose selected as-of date is this day.
  for r in target_rows[day]:
   fid=str(r.get('fid'))
   try:out[fid]=(ratings[(str(r['league']),str(r['home']))]-ratings[(str(r['league']),str(r['away']))])/400.0
   except Exception:continue
 return out

def defaultdict_list():return collections.defaultdict(list)

def softmax_fit(x,y,nclass=len(STATES),l2=TRAIN_L2):
 x=np.asarray(x,float);y=np.asarray(y,int)
 mean=x.mean(axis=0);scale=x.std(axis=0);scale=np.where(scale<1e-8,1.0,scale)
 z=np.column_stack([np.ones(len(x)),(x-mean)/scale])
 p=z.shape[1]
 counts=np.bincount(y,minlength=nclass)
 if np.any(counts==0):raise ValueError(f'training class missing {counts.tolist()}')
 def fg(flat):
  w=flat.reshape(nclass,p);logits=z@w.T
  loss=(logsumexp(logits,axis=1)-logits[np.arange(len(y)),y]).mean()+0.5*l2*np.square(w[:,1:]).sum()
  prob=softmax(logits,axis=1);prob[np.arange(len(y)),y]-=1.0
  grad=(prob.T@z)/len(y);grad[:,1:]+=l2*w[:,1:]
  return loss,grad.ravel()
 res=minimize(fg,np.zeros(nclass*p),jac=True,method='L-BFGS-B',options={'maxiter':500,'ftol':1e-10,'gtol':1e-6})
 if not res.success and res.fun>1e5:raise RuntimeError(res.message)
 return {'w':res.x.reshape(nclass,p),'mean':mean,'scale':scale,'success':bool(res.success),'message':str(res.message),'iterations':int(res.nit),'loss':float(res.fun),'train_class_counts':counts.tolist()}
def softmax_predict(model,x):
 z=np.column_stack([np.ones(len(x)),(np.asarray(x,float)-model['mean'])/model['scale']])
 return softmax(z@model['w'].T,axis=1)

def features_for_row(r,elo):
 line=float(r['end_line']);ho=float(r['home_price']);ao=float(r['away_price'])
 if not(ho>1 and ao>1 and math.isfinite(line+ho+ao)):raise ValueError('invalid odds')
 qh=(1/ho)/(1/ho+1/ao);over=(1/ho+1/ao)-1.0
 return {'CROWN_ONLY':np.array([line,qh,over]),'ELO_CONTRACT':np.array([line,elo]),'CROWN_PLUS_ELO':np.array([line,qh,over,elo])}

def predict_sides(probs,ho,ao):
 evh=probs@payout_vector(ho,'home');eva=probs@payout_vector(ao,'away')
 side='home' if evh>eva else 'away'
 return side,float(evh),float(eva)
def iso(d):
 x=dt.date.fromisoformat(d).isocalendar();return f'{x.year}-W{x.week:02d}'
def metrics(rows):
 n=len(rows);pnl=sum(float(x['net_u']) for x in rows);dates=collections.defaultdict(float);weeks=collections.Counter();league=collections.defaultdict(lambda:[0,0.]);sett=collections.Counter()
 for x in rows:
  dates[x['date']]+=float(x['net_u']);weeks[x['iso_week']]+=1;league[str(x['league'])][0]+=1;league[str(x['league'])][1]+=float(x['net_u']);sett[x['settlement']]+=1
 run=peak=mdd=0.0
 for day,v in sorted(dates.items()):run+=v;peak=max(peak,run);mdd=max(mdd,peak-run)
 calendar_weeks=0;by_week={}
 for wk,nwk in sorted(weeks.items()):
  wr=[x for x in rows if x['iso_week']==wk]
  by_week[wk]={'orders':nwk,'net_u':round(sum(float(x['net_u']) for x in wr),6),'roi_pct':round(100*sum(float(x['net_u']) for x in wr)/nwk,6) if nwk else None}
 if rows:
  first=dt.date.fromisoformat(min(x['date'] for x in rows));last=dt.date.fromisoformat(max(x['date'] for x in rows))
  monday=first-dt.timedelta(days=first.weekday());end=last-dt.timedelta(days=last.weekday())
  calendar_weeks=(end-monday).days//7+1
 return {'orders':n,'net_u':round(pnl,6),'roi_pct':round(pnl/n*100,6) if n else None,'mdd_u':round(mdd,6),'active_iso_weeks':len(weeks),'calendar_iso_weeks':calendar_weeks,'orders_per_calendar_week':round(n/calendar_weeks,6) if calendar_weeks else 0,'settlements':dict(sett),'by_iso_week':by_week,'by_league':{k:{'orders':v[0],'net_u':round(v[1],6),'roi_pct':round(100*v[1]/v[0],6) if v[0] else None} for k,v in league.items()}}
def bootstrap(rows,reps=BOOT_REPS,seed=BOOT_SEED):
 byyear=collections.defaultdict(lambda:collections.defaultdict(list))
 for x in rows:byyear[int(x['year'])][x['iso_week']].append(float(x['net_u']))
 rng=np.random.default_rng(seed);pn=[];ro=[]
 for _ in range(reps):
  s=n=0
  for y,ww in byyear.items():
   keys=list(ww)
   for i in range(len(keys)):
    b=ww[keys[rng.integers(len(keys))]];s+=sum(b);n+=len(b)
  pn.append(s);ro.append(100*s/n if n else 0)
 def pct(a,p):return float(np.quantile(a,p))
 return {'method':'ISO-week cluster resampling within calendar year; descriptive, exploratory; not adjusted for prior M8 model search','replicates':reps,'seed':seed,'net_u_95pct':[round(pct(pn,.025),6),round(pct(pn,.975),6)],'roi_pct_95pct':[round(pct(ro,.025),6),round(pct(ro,.975),6)],'bootstrap_fraction_net_positive':round(float(np.mean(np.asarray(pn)>0)),6)}

def main():
 score_rows=read_jsonl(SCORES);market_rows=read_jsonl(MARKETS);frozen_rows=read_jsonl(FROZEN)
 frozen={str(x['fid']):x for x in frozen_rows};scores={str(x['fid']):x for x in score_rows}
 assert len(scores)==len(score_rows)==40277 and len(frozen)==10294
 assert sha(FROZEN)=='6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665'
 assert all(str(x['fid']) in scores for x in market_rows)
 # Elo snapshots at each target match date, using results whose UTC match date is >=2 days earlier.
 elo=elo_features(score_rows)
 rows=[];model_fits={};common=[];outgroup=[]
 by_year_market=collections.defaultdict(list)
 for r in market_rows:
  fid=str(r['fid']);s=scores[fid]
  assert str(r['league'])==str(s['league']) and str(r['date'])==str(s['date']) and int(r['year'])==int(s['year'])
  assert int(s['hg'])>=0 and int(s['ag'])>=0
  uh,sh=settle(float(r['end_line']),'home',int(s['hg']),int(s['ag']),float(r['home_price']))
  if abs(uh-float(r['end_home_U']))>1e-7:raise AssertionError(f'T1 home settlement mismatch FID {fid}')
  if fid not in elo:raise AssertionError(f'missing Elo {fid}')
  ko_utc=parse_utc(s['ko']);ko_cn=ko_utc.astimezone(CHINA_TZ)
  row={**r,'source_date':r['date'],'date':ko_cn.date().isoformat(),'year':ko_cn.year,'ko_utc':ko_utc.isoformat(),'ko_china':ko_cn.isoformat(),'hg':int(s['hg']),'ag':int(s['ag']),'ko':s['ko'],'elo_diff':elo[fid],'market_state':home_state(float(r['end_line']),int(s['hg']),int(s['ag']))}
  row['feature_sets']=features_for_row(row,elo[fid]);by_year_market[int(row['year'])].append(row)
 for y in TARGET_YEARS:
  train=[x for yy,rr in by_year_market.items() if yy<y for x in rr]
  test=by_year_market.get(y,[])
  if not test:continue
  training_years=[min(z['year'] for z in train),max(z['year'] for z in train)]
  train_y=np.array([STATE_INDEX[x['market_state']] for x in train],int)
  test_y=np.array([STATE_INDEX[x['market_state']] for x in test],int)
  for method in METHODS:
   fit=softmax_fit(np.vstack([x['feature_sets'][method] for x in train]),train_y)
   prob=softmax_predict(fit,np.vstack([x['feature_sets'][method] for x in test]))
   model_fits[(y,method)]=fit
   for x,p in zip(test,prob):
    fid=str(x['fid'])
    side,evh,eva=predict_sides(p,float(x['home_price']),float(x['away_price']))
    pnl,state=settle(float(x['end_line']),side,x['hg'],x['ag'],float(x[f'{side}_price']))
    ev_side=side if max(evh,eva)>0.0 else None
    ev_pnl,ev_state=(settle(float(x['end_line']),ev_side,x['hg'],x['ag'],float(x[f'{ev_side}_price'])) if ev_side else (0.0,'no_bet'))
    q={k:v for k,v in x.items() if k!='feature_sets'}
    q.update({'method':method,'training_years':training_years,'predicted_probs':{s:float(p[i]) for i,s in enumerate(STATES)},'predicted_ev_home_u':evh,'predicted_ev_away_u':eva,'selected_side':side,'selected_price':float(x[f'{side}_price']),'settlement':state,'net_u':pnl,'ev_positive_selected':bool(ev_side),'ev_positive_side':ev_side,'ev_positive_expected_u':max(evh,eva),'ev_positive_settlement':ev_state,'ev_positive_net_u':ev_pnl,'source_class':'historical Crown source-event T1 replay','true_receipt':False,'original_eight_overlap':fid in frozen,'unique_incremental':fid not in frozen,'iso_week':iso(q['date'])})
    # Market low-price reference for every method, kept as a reference not a candidate method.
    fav='home' if float(x['home_price'])<=float(x['away_price']) else 'away'
    fu,fs=settle(float(x['end_line']),fav,x['hg'],x['ag'],float(x[f'{fav}_price']))
    q['lower_price_side']=fav;q['lower_price_side_net_u']=fu;q['lower_price_side_settlement']=fs
    rows.append(q)
 # Add equal-stake original-eight members on the exact same FID sample to form comparable unions.
 modelsummary={}; all_predictions={}
 for method in METHODS:
  mr=[x for x in rows if x['method']==method]
  incr=[x for x in mr if x['unique_incremental']]
  common_fids={x['fid'] for x in mr}
  test_by_fid={x['fid']:x for x in mr}
  base=[{'fid':fid,'date':test_by_fid[fid]['date'],'year':int(test_by_fid[fid]['year']),'iso_week':iso(test_by_fid[fid]['date']),'league':frozen[fid]['league'],'net_u':float(frozen[fid]['pnl']),'settlement':'frozen_group'} for fid in common_fids if fid in frozen]
  combined=base+[{k:x[k] for k in ('fid','date','year','iso_week','league','net_u','settlement')} for x in incr]
  r_recent=[x for x in mr if int(x['year'])>=2024]
  i_recent=[x for x in incr if int(x['year'])>=2024]
  b_recent=[x for x in base if int(x['year'])>=2024]
  c_recent=b_recent+[{k:x[k] for k in ('fid','date','year','iso_week','league','net_u','settlement')} for x in i_recent]
  # Paired calibration scores: all five categories, identical years and FIDs.
  actual=np.array([STATE_INDEX[x['market_state']] for x in mr]);P=np.array([[x['predicted_probs'][s] for s in STATES] for x in mr])
  nll=float(-np.log(np.clip(P[np.arange(len(actual)),actual],1e-12,1)).mean());brier=float(np.square(P-np.eye(len(STATES))[actual]).sum(axis=1).mean())
  byyear={str(y):metrics([x for x in incr if int(x['year'])==y]) for y in TARGET_YEARS}
  bymonth={m:metrics([x for x in incr if x['date'][:7]==m]) for m in sorted({x['date'][:7] for x in incr})}
  market_baseline=[{**x,'net_u':x['lower_price_side_net_u'],'settlement':x['lower_price_side_settlement']} for x in incr]
  ev_incr=[{**x,'selected_side':x['ev_positive_side'],'net_u':x['ev_positive_net_u'],'settlement':x['ev_positive_settlement']} for x in incr if x['ev_positive_selected']]
  ev_recent=[x for x in ev_incr if int(x['year'])>=2024]
  ev_base=[x for x in base if int(x['year'])>=2024]
  ev_combined=ev_base+[{k:x[k] for k in ('fid','date','year','iso_week','league','net_u','settlement')} for x in ev_recent]
  frozen_all=[]
  for fid,v in frozen.items():
   if fid in scores:
    d_cn=parse_utc(scores[fid]['ko']).astimezone(CHINA_TZ).date().isoformat();yr_cn=int(d_cn[:4])
   else:d_cn=v['date'];yr_cn=int(v['year'])
   frozen_all.append({'fid':fid,'date':d_cn,'year':yr_cn,'iso_week':iso(d_cn),'league':v['league'],'net_u':float(v['pnl']),'settlement':'frozen_group'})
  full_historical_combined=frozen_all+[{k:x[k] for k in ('fid','date','year','iso_week','league','net_u','settlement')} for x in incr]
  modelsummary[method]={'all_scored_fids':metrics(mr),'out_of_eight_incremental':metrics(incr),'out_of_eight_by_year':byyear,'out_of_eight_by_month':bymonth,'out_of_eight_2024_2026':metrics(i_recent),'paired_lower_price_side_out_of_eight':metrics(market_baseline),'increment_net_u_vs_lower_price':round(sum(x['net_u'] for x in incr)-sum(x['lower_price_side_net_u'] for x in incr),6),'ev_positive_out_of_eight':metrics(ev_incr),'ev_positive_out_of_eight_by_year':{str(y):metrics([x for x in ev_incr if int(x['year'])==y]) for y in TARGET_YEARS},'ev_positive_2024_2026':metrics(ev_recent),'ev_positive_no_bet_fids':len(incr)-len(ev_incr),'ev_positive_combined_2024_2026':metrics(ev_combined),'frozen_eight_same_scored_fids':metrics(base),'combined_same_scored_fids':metrics(combined),'combined_2024_2026':metrics(c_recent),'original_eight_full_history':metrics(frozen_all),'full_original_eight_plus_candidate_history':metrics(full_historical_combined),'state_nll':round(nll,8),'state_brier_sum':round(brier,8),'out_of_eight_week_bootstrap_2024_2026':bootstrap(i_recent)}
  all_predictions[method]=mr
 # Measure how often adding Elo changes a side on the exact same out-of-eight FIDs.
 by_method={m:{x['fid']:x for x in rows if x['method']==m and x['unique_incremental']} for m in METHODS}
 direction_comparison={}
 for method in ('ELO_CONTRACT','CROWN_PLUS_ELO'):
  a=by_method['CROWN_ONLY'];b=by_method[method];dis=[fid for fid in sorted(a) if a[fid]['selected_side']!=b[fid]['selected_side']]
  direction_comparison[f'CROWN_ONLY_vs_{method}']={'same_fid_count':len(set(a)&set(b)),'different_direction_fids':len(dis),'different_direction_fraction':round(len(dis)/len(a),8) if a else None,'crown_only_net_u_on_disagreements':round(sum(a[fid]['net_u'] for fid in dis),6),'elo_variant_net_u_on_disagreements':round(sum(b[fid]['net_u'] for fid in dis),6),'net_u_delta_on_disagreements':round(sum(b[fid]['net_u']-a[fid]['net_u'] for fid in dis),6)}
 # Actual received Crown receipts: latest true pre-kick AH observation per FID, independently FT-verified.
 actual_receipts=read_jsonl(RECEIPTS);ftrows=read_jsonl(VERIFIED_FT);ft={str(x.get('match_id')):x for x in ftrows if x.get('status')=='verified_ft'}
 rec_by={}
 raw_sha_checks=0;raw_mismatches=[];receipt_identity_mismatches=[]
 for rec in actual_receipts:
  fid=str(rec['fixture_id']);m=rec.get('markets',{}).get('AH')
  if not m:continue
  try:
   ko=parse_utc(rec['kickoff_utc']);received=parse_utc(rec['received_utc']);src=parse_utc(m['source_event_utc']);line=float(m['line']);ho=float(m['odds']['home']);ao=float(m['odds']['away'])
  except Exception:continue
  if not(received<ko and src<=received and ho>1 and ao>1):continue
  try:
   rawdoc=json.load(open(rec['source_file'],encoding='utf-8'));raw=json.loads(rawdoc['raw_response']);
   got=hashlib.sha256(rawdoc['raw_response'].encode()).hexdigest();raw_sha_checks+=1
   if got!=rec['raw_sha256']:raw_mismatches.append(fid);continue
   match=next((z for z in raw.get('data',[]) if str(z.get('id'))==fid),None)
   crown=next((b for b in (match or {}).get('bookmakers',[]) if b.get('slug')=='crown'),None)
   qfound=False
   for q in (crown or {}).get('asian_list',[]):
    if len(q)>=5 and abs(float(q[1])-line)<1e-9 and abs(float(q[2])-ho)<1e-9 and abs(float(q[3])-ao)<1e-9:
     qfound=True;break
   if not qfound:raw_mismatches.append(fid);continue
   if fid in scores:
    s=scores[fid]
    if str(s['league'])!=str(rec['league_id']) or parse_utc(s['ko'])!=ko:receipt_identity_mismatches.append(fid);continue
   old=rec_by.get(fid)
   if old is None or received>old['received_dt']:
    rec_by[fid]={'fid':fid,'league':str(rec['league_id']),'league_name':rec['league'],'kickoff_utc':ko.isoformat(),'received_utc':received.isoformat(),'received_dt':received,'source_event_utc':src.isoformat(),'snapshot_horizon':rec['snapshot_horizon'],'snapshot_split':rec['snapshot_split'],'raw_sha256':rec['raw_sha256'],'snapshot_sha256':rec['snapshot_sha256'],'line':line,'home_price':ho,'away_price':ao,'elo_diff':None,'source_file':rec['source_file'],'score_fixture':scores.get(fid)}
  except Exception as exc:
   raw_mismatches.append(fid)
 # Assign Elo as-of each chosen quote's actual receive date; elo_features applies the 2-day embargo.
 rec_asof={fid:(dt.datetime.fromisoformat(x['received_utc'])-dt.timedelta(days=0)) for fid,x in rec_by.items()}
 rec_elo=elo_features(score_rows,rec_asof)
 rec_rows=[]
 for fid,r in rec_by.items():
  if fid not in ft:continue
  f=ft[fid]
  if (str(f.get('home')) and str(f.get('away'))) and fid in scores:
   sc=scores[fid]
   if int(f['home_goals'])!=int(sc['hg']) or int(f['away_goals'])!=int(sc['ag']):receipt_identity_mismatches.append(fid);continue
  hg=int(f['home_goals']);ag=int(f['away_goals']);r['elo_diff']=rec_elo.get(fid)
  feats={'CROWN_ONLY':np.array([r['line'],(1/r['home_price'])/(1/r['home_price']+1/r['away_price']),(1/r['home_price']+1/r['away_price'])-1])}
  if fid in rec_elo:
   feats['ELO_CONTRACT']=np.array([r['line'],r['elo_diff']])
   feats['CROWN_PLUS_ELO']=np.array([r['line'],(1/r['home_price'])/(1/r['home_price']+1/r['away_price']),(1/r['home_price']+1/r['away_price'])-1,r['elo_diff']])
  for method in METHODS:
   if method not in feats:continue
   fit=model_fits[(2026,method)];p=softmax_predict(fit,feats[method][None,:])[0]
   side,evh,eva=predict_sides(p,r['home_price'],r['away_price']);u,state=settle(r['line'],side,hg,ag,r[f'{side}_price'])
   receipt_ko=parse_utc(r['kickoff_utc']).astimezone(CHINA_TZ);receipt_date=receipt_ko.date().isoformat()
   rr={k:v for k,v in r.items() if k not in ('received_dt','source_file','score_fixture')};rr.update({'date':receipt_date,'year':receipt_ko.year,'iso_week':iso(receipt_date),'method':method,'home':scores[fid]['home'] if fid in scores else None,'away':scores[fid]['away'] if fid in scores else None,'hg':hg,'ag':ag,'predicted_probs':{s:float(p[i]) for i,s in enumerate(STATES)},'predicted_ev_home_u':evh,'predicted_ev_away_u':eva,'selected_side':side,'selected_price':r[f'{side}_price'],'settlement':state,'net_u':u,'true_crown_http_receipt':True,'source_class':'archived actual pre-kick HTTP Crown receipt replay; retrospective evaluation','FT_source':f.get('result_provider') or f.get('source')})
   rec_rows.append(rr)
 receipt_summary={}
 for method in METHODS:
  z=[x for x in rec_rows if x['method']==method]
  rz=[{**x,'ev_positive_selected':max(x['predicted_ev_home_u'],x['predicted_ev_away_u'])>0} for x in z if max(x['predicted_ev_home_u'],x['predicted_ev_away_u'])>0]
  receipt_summary[method]={'settled_true_receipt_fids':len({x['fid'] for x in z}),'metrics':metrics(z),'ev_positive_metrics':metrics(rz),'ev_positive_no_bet':len(z)-len(rz),'by_year':{'2026':metrics(z)},'receipt_horizons':dict(collections.Counter(x['snapshot_horizon'] for x in z))}
 # Write reproducible fixture-level rows and summary.
 with gzip.open(MODEL_LEDGER,'wt',encoding='utf-8') as f:
  for x in rows:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
 with gzip.open(RECEIPT_LEDGER,'wt',encoding='utf-8') as f:
  for x in rec_rows:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
 result={'study':'M8 dynamic Elo as independent pre-match information for Crown AH contract outcome prediction; research only','scope':{'crown_T1_path_rows':len(market_rows),'score_history_rows':len(score_rows),'unique_joined_fids':len(rows)//len(METHODS),'historical_test_years':{str(y):len(by_year_market.get(y,[])) for y in TARGET_YEARS},'original_eight_frozen_fids':len(frozen),'historical_true_receipt_replay':'separate from event-time replay'},'inputs':{'scores_sha256':sha(SCORES),'crown_features_sha256':sha(MARKETS),'frozen_sha256':sha(FROZEN),'actual_receipt_archive_sha256':sha(RECEIPTS),'verified_ft_index_sha256':sha(VERIFIED_FT)},'method':{'elo_system':'league-specific Elo; initial 1500; K=20; 65-point home advantage in updates; win/draw/loss outcome update; no margin multiplier','elo_asof':'only prior matches at least 2 UTC calendar days before target/receipt date; all same-day results are updated as a batch after features are assigned','reporting_timezone':'Asia/Shanghai UTC+08:00; Elo information cutoff remains UTC with a two-calendar-day embargo','targets':'five-state home AH contract settlement (full/half loss, push, half/full win)','models':'CROWN_ONLY=line, no-vig home share, overround; ELO_CONTRACT=line, Elo rating difference/400; CROWN_PLUS_ELO=both feature sets','estimator':'multinomial softmax with train-year-only standardization and fixed L2=1.0; no test-year parameter selection','walk_forward':'for test year Y, model trained only on earlier years; one direction selected per match by higher predicted net U at actual Crown line and actual two-sided quote, with no EV threshold/no abstention','ev_selection':'a separate non-production diagnostic abstains when both predicted sides have expected net payoff <= 0U; zero is the economic break-even point, not a deployed Gate','stake':'1U per selected match; quarter AH split into two half-stakes','historical_quote':'Crown source-event T1 replay; not actual HTTP receipt or execution','actual_receipt_quote':'latest valid actual pre-kick MR1 Crown receipt per FID, raw SHA and exact Crown asian_list line/odds rechecked; only verified FT rows evaluated'},'models':modelsummary,'direction_comparison':direction_comparison,'actual_receipt_audit':{'archive_valid_latest_unique_fids':len(rec_by),'raw_response_and_asian_list_checks':raw_sha_checks,'raw_or_quote_mismatches':len(raw_mismatches),'identity_mismatches':len(set(receipt_identity_mismatches)),'m7_verified_ft_intersection':len(set(rec_by)&set(ft)),'elo_feature_join_fids':len(set(rec_by)&set(rec_elo)),'elo_feature_and_verified_ft_intersection':len(set(rec_by)&set(rec_elo)&set(ft)),'evaluated_settled_unique_fids':len({x['fid'] for x in rec_rows if x['method']=='CROWN_ONLY'}),'per_model':receipt_summary,'note':'Archive results were observed before this research; this is retrospective receipt-price replay, not a blind or production-forward trial.'},'model_fit_diagnostics':{str(y):{m:{k:v for k,v in model_fits[(y,m)].items() if k not in ('w','mean','scale')} for m in METHODS} for y in TARGET_YEARS},'limitations':['M8 input score source has no exact first-received timestamp; two-day event-time embargo reduces same-week information leakage but cannot prove historical score data were received at decision time.','Crown T1 paths were retrieved historically; their HTTP response was received in 2026, not at the historical event time.','The true receipt subset has only the matches with a separately verified FT index; this is retrospective and already appeared in prior M8 research.','Current-year 2026 T1 inventory is partial and source-file coverage definition differs from other user-provided 2026 inventory totals.','This is a single predefined Elo parameterization, but the broader M8 program has prior model-selection history; no independent blind validation is claimed.'],'production_changes':False,'formal_telegram_orders':0,'formal_ledger_writes':0}
 SUMMARY.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'summary':str(SUMMARY),'test_rows':len(rows)//len(METHODS),'outgroup_by_model':{m:v['out_of_eight_incremental'] for m,v in modelsummary.items()},'recent_by_model':{m:v['out_of_eight_2024_2026'] for m,v in modelsummary.items()},'receipts':result['actual_receipt_audit']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
