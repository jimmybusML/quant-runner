#!/usr/bin/env python3
"""Walk-forward M8 AH test of prior tactical formation mix vs Crown pricing.

Research only. Target-match formations are never used. Formation archive is
retrospective and has no verified first-publication/receipt timestamp.
"""
from __future__ import annotations
import collections,datetime as dt,gzip,hashlib,json,math,pathlib,sys
import numpy as np

OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[2]))
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
FOUNDATION=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RECEIPTS=WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
MANAGER=WORK/'m8_prior_manager_turnover_20261117.py'
MARKET=WORK/'m8_early_market_response_calibration_20261116.py'
GAMES=WORK/'m8_pregame_info_source_20261117/games.csv.gz'
ALPHA=100.0

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def parse_utc(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00'))
 if x.tzinfo is None:raise ValueError('timestamp lacks timezone')
 return x.astimezone(dt.timezone.utc)
def rows_jsonl(p):
 with open(p,encoding='utf8') as f:
  for s in f:
   if s.strip():yield json.loads(s)
def exec_prefix(path,marker,name):
 src=path.read_text(encoding='utf8'); ns={'__file__':str(path),'__name__':name}
 i=src.rindex(marker) if marker.startswith("out={'method'") else src.index(marker)
 exec(compile(src[:i],str(path)+'[replay-prefix]','exec'),ns)
 return ns
def normalize_formation(v):
 s=str(v or '').strip()
 if not s or s.lower() in ('nan','none','-'):return None
 try:n=int(s.split('-',1)[0])
 except (ValueError,TypeError):return None
 if n<2 or n>6:return None
 return min(n,5) # five or six defenders retained as a single 5+ category
def feat_team(events,day):
 cutoff=day-3; lo=cutoff-365; short_lo=cutoff-90
 z=[x for x in events if lo<x[0]<=cutoff]
 if not z:return None
 nums=[x[1] for x in z]
 n=len(nums); p3=sum(v==3 for v in nums)/n;p4=sum(v==4 for v in nums)/n;p5=sum(v>=5 for v in nums)/n
 ent=-sum(p*math.log(p) for p in (p3,p4,p5) if p>0)
 q=[x[1] for x in z if x[0]>short_lo]
 if q:
  q3=sum(v==3 for v in q)/len(q);q5=sum(v>=5 for v in q)/len(q)
 else:q3=p3;q5=p5
 return {'n':n,'p3':p3,'p4':p4,'p5':p5,'entropy':ent,'p3_90':q3,'p5_90':q5,'last_history_date':dt.date.fromordinal(max(x[0] for x in z)).isoformat()}
def paired_features(h,a):
 # For each formation statistic: level (sum), role asymmetry (home-away),
 # followed by the recent-vs-year change sum and difference for 3/5-back use.
 vals=[]
 for k in ('p3','p4','p5','entropy'):
  vals.extend((h[k]+a[k],h[k]-a[k]))
 vals.extend(((h['p3_90']-h['p3'])+(a['p3_90']-a['p3']),
              (h['p3_90']-h['p3'])-(a['p3_90']-a['p3']),
              (h['p5_90']-h['p5'])+(a['p5_90']-a['p5']),
              (h['p5_90']-h['p5'])-(a['p5_90']-a['p5'])))
 return vals
def settle(line,side,gd,odds):
 signed=float(line) if side=='home' else -float(line)
 margin=int(gd) if side=='home' else -int(gd)
 if abs(signed*4-round(signed*4))>1e-8:raise ValueError('AH line outside quarter grid')
 legs=(signed,) if abs(signed*2-round(signed*2))<1e-8 else (math.floor(signed*2)/2,math.ceil(signed*2)/2)
 pnl=[];lab=[]
 for leg in legs:
  d=margin+leg;lab.append('W' if d>1e-9 else 'L' if d< -1e-9 else 'P')
  pnl.append(float(odds)-1 if d>1e-9 else -1. if d< -1e-9 else 0.)
 net=sum(pnl)/len(pnl)
 state=('full_win' if all(x=='W' for x in lab) else 'full_loss' if all(x=='L' for x in lab) else
        'push' if all(x=='P' for x in lab) else 'half_win' if net>0 else 'half_loss' if net<0 else 'push')
 return state,net
def cdf(x):return .5*(1.+math.erf(x/math.sqrt(2.)))
def margin_dist(mu,sigma):
 sig=max(float(sigma),.35);lo=-12;hi=12
 ps=[max(0.,cdf((k+.5-mu)/sig)-cdf((k-.5-mu)/sig)) for k in range(lo,hi+1)]
 sm=sum(ps);return [(lo+i,p/sm) for i,p in enumerate(ps)]
def choose(line,ho,ao,mu,sigma):
 dist=margin_dist(mu,sigma)
 eh=sum(p*settle(line,'home',gd,ho)[1] for gd,p in dist)
 ea=sum(p*settle(line,'away',gd,ao)[1] for gd,p in dist)
 side=None if abs(eh-ea)<1e-12 else ('home' if eh>ea else 'away')
 return side,eh,ea
def ridge_fit(X,y):
 X=np.asarray(X,float);y=np.asarray(y,float);m=X.mean(0);s=X.std(0);s=np.where(s<1e-10,1.,s)
 z=(X-m)/s;d=np.column_stack([np.ones(len(z)),z]);pen=np.eye(d.shape[1])*ALPHA;pen[0,0]=0.
 b=np.linalg.solve(d.T@d+pen,d.T@y);res=y-d@b
 return m,s,b,max(.35,float(np.sqrt(np.mean(res*res))))
def predict(fit,x):
 m,s,b,_=fit
 return float(np.r_[1.,(np.asarray(x,float)-m)/s]@b)
def mdd(rows):
 daily=collections.defaultdict(float)
 for r in rows:daily[r['date']]+=float(r['net_u'])
 c=pk=dd=0.
 for day in sorted(daily):c+=daily[day];pk=max(pk,c);dd=max(dd,pk-c)
 return round(dd,6)
def stats(rows,week_den=None):
 n=len(rows);u=sum(float(x['net_u']) for x in rows)
 if not n:return {'n':0,'net_U':0.,'ROI_pct':None,'MDD_U':0.,'orders_per_week':0.,'five_state':{}}
 dates=[dt.date.fromisoformat(x['date']) for x in rows]
 span=week_den or ((max(dates)-min(dates)).days//7+1)
 return {'n':n,'net_U':round(u,6),'ROI_pct':round(100*u/n,6),'MDD_U':mdd(rows),
  'orders_per_week':round(n/span,6),'five_state':dict(collections.Counter(x.get('settlement','not_recorded') for x in rows))}
def group_stats(rs,key):
 d=collections.defaultdict(list)
 for r in rs:d[r[key]].append(r)
 return {str(k):stats(v) for k,v in sorted(d.items(),key=lambda x:str(x[0]))}
def main():
 for p in (FOUNDATION,RECEIPTS,GAMES):
  if not p.exists():raise FileNotFoundError(p)
 # The prior-market prefix restores the exact Crown T12 paired AH/score cohort.
 mn=exec_prefix(MARKET,"out={'method'",'m8_formation_market_data')
 H=mn['H'];history_ind=mn['history_ind'];HY=mn['HY'];
 # Reuse the established conservative Crown↔Transfermarkt competition/team bridge.
 bridge=exec_prefix(MANAGER,'# Build historical coach timeline','m8_formation_identity_bridge')
 teammap=bridge['teammap'];cm=bridge['cm'];allft=bridge['allft'];tm=bridge['tm']
 invcomp={v:k for k,v in cm.items()};invteam=collections.defaultdict(dict)
 for (lid,crown_tid),club in teammap.items():invteam[lid][str(club)]=str(crown_tid)
 hist=collections.defaultdict(list);audit=collections.Counter();dup_games=set()
 for z in tm:
  try:
   lid=invcomp.get(str(z['competition_id']));day=dt.date.fromisoformat(z['date']).toordinal()
   if not lid:continue
   for side in ('home','away'):
    club=str(z[side+'_club_id']);tid=invteam[lid].get(club);f=normalize_formation(z.get(side+'_club_formation'))
    if not tid or f is None:audit['unmapped_or_missing_formation_side']+=1;continue
    hist[(lid,tid)].append((day,f,str(z['game_id'])));audit['mapped_formation_sides']+=1
  except Exception:audit['invalid_historical_row']+=1
 for k in hist:
  hist[k].sort()
  seen=set();unique=[]
  for x in hist[k]:
   if x[2] not in seen:seen.add(x[2]);unique.append(x)
  hist[k]=unique
 frozen={str(r['fid']):r for r in rows_jsonl(FOUNDATION)}
 receipts={str(r['fixture_id']) for r in rows_jsonl(RECEIPTS)}
 cohort=[];miss=collections.Counter();coverage_year=collections.Counter();raw_data=[]
 for r in H:
  fid=str(r['fid']);ft=allft.get(fid)
  if ft is None:miss['missing_cached_Crown_FT_identity']+=1;continue
  lid=str(r['league']);day=dt.date.fromisoformat(str(r['date'])).toordinal()
  if (str(ft[0]),str(ft[1]),str(ft[2]),str(ft[5]),str(ft[6]),str(ft[7]))!=(lid,str(r['home_id']),str(r['away_id']),str(r['hg']),str(r['ag']),str(r['date'])):
   miss['Crown_identity_or_FT_conflict']+=1;continue
  hm=teammap.get((lid,str(r['home_id'])));am=teammap.get((lid,str(r['away_id'])));comp=cm.get(lid)
  if not hm or not am or not comp:miss['unmapped_target_team_or_league']+=1;continue
  fh=feat_team(hist.get((lid,str(r['home_id'])),[]),day);fa=feat_team(hist.get((lid,str(r['away_id'])),[]),day)
  if fh is None or fa is None:miss['no_prior_365d_formation_for_both_teams']+=1;continue
  if fh['n']<3 or fa['n']<3:audit['valid_cohort_with_any_team_prior_n_lt3']+=1
  line=float(r['al']);ho=float(r['ah']);ao=float(r['aa'])
  if min(ho,ao)<=1 or abs(line*4-round(line*4))>1e-8:miss['invalid_Crown_AH_contract']+=1;continue
  skew=.25*math.log(ao/ho)
  market=[-line+skew,line,skew]
  f=paired_features(fh,fa)
  rec={'fid':fid,'year':int(r['year']),'date':str(r['date'])[:10],
       'iso_week':f"{dt.date.fromisoformat(str(r['date'])).isocalendar().year}-W{dt.date.fromisoformat(str(r['date'])).isocalendar().week:02d}",
       'kickoff_beijing':r.get('kickoff_beijing'),'league':lid,'home_id':str(r['home_id']),'away_id':str(r['away_id']),
       'home_tm_club_id':str(hm),'away_tm_club_id':str(am),'hg':int(r['hg']),'ag':int(r['ag']),'gd':int(r['hg'])-int(r['ag']),
       'T12_AH_home_line':line,'T12_home_odds':ho,'T12_away_odds':ao,'market_features':market,'formation_features':f,
       'formation_history_home_n_365':fh['n'],'formation_history_away_n_365':fa['n'],
       'formation_history_home_max_date':fh['last_history_date'],'formation_history_away_max_date':fa['last_history_date'],
       'formation_history_home':fh,'formation_history_away':fa,'formation_cutoff':str(dt.date.fromordinal(day-3)),
       'formation_source':'retrospective Transfermarkt games.csv.gz formation fields; event-date lag only, no first-publication receipt timestamp',
       'frozen_overlap':fid in frozen,'actual_receipt_fid_overlap':fid in receipts}
  cohort.append(rec);coverage_year[rec['year']]+=1
 # Fixed common cohort and three forward-trained model specifications.
 methods=('market_only','formation_only','market_plus_formation')
 pred={m:[] for m in methods};folds={};year_cov={};fit_params={}
 for year in (2024,2025,2026):
  train=[r for r in cohort if 2019<=r['year']<year and r['fid'] not in receipts]
  test=[r for r in cohort if r['year']==year]
  if not train or not test:continue
  y=np.asarray([r['gd'] for r in train],float)
  folds[str(year)]={'train_n':len(train),'train_years':sorted({r['year'] for r in train}),'train_max_year':max(r['year'] for r in train),
                    'test_n':len(test),'ridge_alpha':ALPHA,'receipt_fids_excluded_from_training':True}
  year_cov[str(year)]={'test_n':len(test),'outside_frozen_n':sum(not r['frozen_overlap'] for r in test),'test_actual_receipt_overlap':sum(r['actual_receipt_fid_overlap'] for r in test)}
  for m in methods:
   def xof(r):
    if m=='market_only':return r['market_features']
    if m=='formation_only':return r['formation_features']
    return r['market_features']+r['formation_features']
   fit=ridge_fit([xof(r) for r in train],y);folds[str(year)].setdefault('models',{})[m]={'n_features':len(xof(train[0])),'sigma':round(fit[3],8)}
   if year==2026:fit_params[m]={'mean':fit[0].tolist(),'scale':fit[1].tolist(),'coef':fit[2].tolist(),'sigma':fit[3]}
   for r in test:
    mu=predict(fit,xof(r));side,eh,ea=choose(r['T12_AH_home_line'],r['T12_home_odds'],r['T12_away_odds'],mu,fit[3])
    if side is None:state='push';net=0.;price=None
    else:price=r['T12_home_odds'] if side=='home' else r['T12_away_odds'];state,net=settle(r['T12_AH_home_line'],side,r['gd'],price)
    pred[m].append({**r,'method':m,'predicted_home_goal_difference':round(mu,8),'predicted_sigma':round(fit[3],8),
     'home_EV_U':round(eh,8),'away_EV_U':round(ea,8),'chosen_side':side,'chosen_odds':price,
     'settlement':state,'net_u':round(net,8),'training_year_cutoff_exclusive':year})
 # Common-date weekly denominator covers the full 2024-2026 test range only.
 test_cohort=[r for r in cohort if r['year'] in (2024,2025,2026)]
 test_dates=[dt.date.fromisoformat(r['date']) for r in test_cohort];week_den=(max(test_dates)-min(test_dates)).days//7+1
 all_frozen=[]
 for z in frozen.values():
  try:all_frozen.append({'fid':str(z['fid']),'date':str(z['date'])[:10],'net_u':float(z['pnl']),'settlement':'frozen'})
  except Exception:continue
 same_frozen=[r for r in all_frozen if int(r['date'][:4]) in (2024,2025,2026) and r['date']<=max(x['date'] for x in cohort)]
 summaries={};annual={};weekly={};league={};merged_same={};merged_full={}
 for m,arr in pred.items():
  inc=[r for r in arr if not r['frozen_overlap']]
  summaries[m]={'all_test':stats(arr),'incremental_outside_frozen':stats(inc,week_den)}
  annual[m]={str(y):stats([r for r in inc if r['year']==y]) for y in (2024,2025,2026)}
  weekly[m]=group_stats(inc,'iso_week');league[m]=group_stats(inc,'league')
  same=same_frozen+inc;full=all_frozen+inc
  merged_same[m]={'n':len(same),'net_U':round(sum(r['net_u'] for r in same),6),'ROI_pct':round(100*sum(r['net_u'] for r in same)/len(same),6),
   'MDD_U':mdd(same),'candidate_incremental_n':len(inc),'candidate_incremental_net_U':round(sum(r['net_u'] for r in inc),6)}
  merged_full[m]={'n':len(full),'net_U':round(sum(r['net_u'] for r in full),6),'ROI_pct':round(100*sum(r['net_u'] for r in full)/len(full),6),
   'MDD_U':mdd(full),'candidate_incremental_n':len(inc),'candidate_incremental_net_U':round(sum(r['net_u'] for r in inc),6)}
 # Preserve a single readable JSONL and primary model's plain decision ledger.
 def write_gz(path,rs):
  with open(path,'wb') as raw:
   with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
    for r in rs:gz.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 write_gz(OUT/'formation_market_per_fixture_20261121.jsonl.gz',[r for m in methods for r in sorted(pred[m],key=lambda x:(x['date'],x['fid']))])
 write_gz(OUT/'formation_market_interaction_ledger_20261121.jsonl.gz',sorted(pred['market_plus_formation'],key=lambda x:(x['date'],x['fid'])))
 # Separate actual HTTP Crown-price replay. Select the latest archived verified
 # pre-kickoff receipt per FID; keep the formation source timing limitation explicit.
 receipt_rows=collections.defaultdict(list)
 for rr in rows_jsonl(RECEIPTS):
  fid=str(rr['fixture_id'])
  if fid not in {r['fid'] for r in pred['market_only'] if r['year']==2026}:continue
  if not rr.get('markets',{}).get('AH'):continue
  receipt_rows[fid].append(rr)
 receipt_quotes={};receipt_audit=collections.Counter()
 target2026={r['fid']:r for r in cohort if r['year']==2026}
 for fid,rrs in receipt_rows.items():
  eligible=[]
  for q in rrs:
   try:
    ko=parse_utc(q['kickoff_utc']);received=parse_utc(q['received_utc']);source=parse_utc(q['markets']['AH']['source_event_utc'])
    if received>=ko:receipt_audit['received_not_pregame']+=1;continue
    if source>received:receipt_audit['source_after_receipt']+=1;continue
    rawpath=pathlib.Path(q['source_file']);raw_file=rawpath.read_bytes();envelope=json.loads(raw_file)
    raw=str(envelope.get('raw_response') or '').encode('utf8')
    snap=rawpath.parents[1]/'snapshot.json';snapb=snap.read_bytes()
    if sha_bytes(raw)!=q['raw_sha256'] or not envelope.get('raw_saved') or int(envelope.get('http_status') or 0)!=200:
     receipt_audit['raw_sha_or_http_mismatch']+=1;continue
    if sha_bytes(snapb)!=q['snapshot_sha256']:receipt_audit['snapshot_sha_mismatch']+=1;continue
    sj=json.loads(snapb);body=json.loads(raw)
    if str(sj.get('match_id'))!=fid or not sj.get('source_bookmaker_verified') or not sj.get('prematch_valid'):
     receipt_audit['snapshot_identity_or_crown_not_verified']+=1;continue
    if (parse_utc(sj['received_at'])!=received or parse_utc(sj['kickoff_at'])!=ko):receipt_audit['snapshot_time_mismatch']+=1;continue
    ah=sj.get('AH') or {};a=q['markets']['AH'];prices=a['odds']
    if (abs(float(ah.get('line'))-float(a['line']))>1e-8 or abs(float(ah.get('home_price'))-float(prices['home']))>1e-8 or abs(float(ah.get('away_price'))-float(prices['away']))>1e-8):
     receipt_audit['snapshot_contract_mismatch']+=1;continue
    data=body.get('data');data=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
    match=next((x for x in data if str(x.get('id'))==fid),None)
    if not match or str(match.get('l_id'))!=str(target2026[fid]['league']) or str(match.get('h_id'))!=str(target2026[fid]['home_id']) or str(match.get('a_id'))!=str(target2026[fid]['away_id']):
     receipt_audit['raw_fixture_identity_mismatch']+=1;continue
    eligible.append((received,q,source,ko))
   except Exception:receipt_audit['receipt_evidence_error']+=1
  if not eligible:continue
  eligible.sort(key=lambda x:x[0]);received,q,source,ko=eligible[-1]
  r=target2026[fid]
  if ko.date().isoformat()[:10]!=r['date'] and abs((ko.date()-dt.date.fromisoformat(r['date'])).days)>1:
   receipt_audit['receipt_vs_cached_date_mismatch']+=1;continue
  a=q['markets']['AH'];line=float(a['line']);ho=float(a['odds']['home']);ao=float(a['odds']['away'])
  if min(ho,ao)<=1 or abs(line*4-round(line*4))>1e-8:receipt_audit['invalid_receipt_contract']+=1;continue
  receipt_quotes[fid]={'line':line,'home_odds':ho,'away_odds':ao,'received_utc':received.isoformat(),
    'source_event_utc':source.isoformat(),'kickoff_utc':ko.isoformat(),'snapshot_horizon':q['snapshot_horizon'],
    'raw_sha256':q['raw_sha256'],'snapshot_sha256':q['snapshot_sha256'],
    'receipt_age_minutes':round((ko-received).total_seconds()/60,6),'quote_source_age_minutes':round((received-source).total_seconds()/60,6)}
  receipt_audit['latest_pregame_receipt_verified']+=1
 receipt_pred={m:[] for m in methods}
 for method in methods:
  params=fit_params[method]
  fit=(np.asarray(params['mean']),np.asarray(params['scale']),np.asarray(params['coef']),float(params['sigma']))
  for fid,q in receipt_quotes.items():
   r=target2026[fid];skew=.25*math.log(q['away_odds']/q['home_odds']);market=[-q['line']+skew,q['line'],skew]
   x=market if method=='market_only' else r['formation_features'] if method=='formation_only' else market+r['formation_features']
   mu=predict(fit,x);side,eh,ea=choose(q['line'],q['home_odds'],q['away_odds'],mu,fit[3])
   if side is None:state='push';net=0.;price=None
   else:price=q['home_odds'] if side=='home' else q['away_odds'];state,net=settle(q['line'],side,r['gd'],price)
   receipt_pred[method].append({**r,'method':method,'receipt_quote':q,'predicted_home_goal_difference':round(mu,8),
    'predicted_sigma':round(fit[3],8),'home_EV_U':round(eh,8),'away_EV_U':round(ea,8),'chosen_side':side,
    'chosen_odds':price,'settlement':state,'net_u':round(net,8),'source_type':'verified actual pre-kickoff Crown HTTP receipt; feature archive historical event-date proxy'})
 receipt_all={};receipt_incremental={};receipt_weekly={}
 for method,arr in receipt_pred.items():
  inc=[r for r in arr if not r['frozen_overlap']]
  receipt_all[method]=stats(arr);receipt_incremental[method]=stats(inc)
  receipt_weekly[method]=group_stats(inc,'iso_week')
 write_gz(OUT/'formation_market_actual_receipt_replay_20261121.jsonl.gz',[r for m in methods for r in receipt_pred[m]])
 summary={'study':'M8 pregame prior formation mix × Crown AH pricing; historical event-time replay',
  'execution_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
  'input_sha256':{str(p):sha(p) for p in (FOUNDATION,RECEIPTS,GAMES)},
  'formation_archive_sha256':sha(GAMES),'crown_path_and_T12_data_source':'R25 M8 historical Crown T12 AH source-event cohort; event prices are historical replays, not actual HTTP receipt quotes',
  'coverage':{'formation_valid_train_and_test_rows':len(cohort),'formation_valid_by_year':dict(coverage_year),
   'formation_valid_test_rows_2024_2026':len(test_cohort),'outside_frozen_unique_test_FIDs':len({r['fid'] for r in test_cohort if not r['frozen_overlap']}),
   'frozen_overlap_test_FIDs':len({r['fid'] for r in test_cohort if r['frozen_overlap']}),'actual_receipt_overlap':len({r['fid'] for r in test_cohort if r['actual_receipt_fid_overlap']}),
   'missing_reasons':dict(miss),'source_data_max_date':max(z['date'] for z in tm),'mapped_formation_history_sides':audit['mapped_formation_sides'],
   'formation_history_365d_both_sides_n_ge_3':sum(r['formation_history_home_n_365']>=3 and r['formation_history_away_n_365']>=3 for r in cohort),
   'formation_history_365d_both_sides_n_ge_1':sum(r['formation_history_home_n_365']>=1 and r['formation_history_away_n_365']>=1 for r in cohort),
   'target_history_overlap_with_actual_receipts':sum(r['actual_receipt_fid_overlap'] for r in test_cohort)},
  'methodology':{'target':'home goals minus away goals','formation_input':'Past completed matches in source games.csv.gz; for each team within prior 365 days, three-back/four-back/five-plus formation shares and normalized Shannon entropy; prior-90-day shifts in three-back and five-plus shares; date-only cutoff target date minus 3 days. Target fixture formation never used.',
   'features':'market_only: Crown market-implied margin, AH line, two-price skew; formation_only: fixed symmetric home-away sum/difference and recent-shift features; market_plus_formation: their concatenation.',
   'time_forward':'2024 train 2019-2023; 2025 train 2019-2024; 2026 train 2019-2025; train only common-feature rows earlier than target year and exclude actual receipt FIDs.',
   'model':'Fixed Ridge alpha=100, fold-local standardization, Gaussian integer goal-difference approximation using training RMSE; choose the AH side with higher expected Crown net return. No EV no-bet filter or parameter search.',
   'settlement':'Crown AH original T12 line and both decimal odds; quarter-lines split into two adjacent half-goal legs and settled separately at half stake.'},
  'training_folds':folds,'test_coverage_by_year':year_cov,'model_results':summaries,'annual_incremental':annual,
  'weekly_incremental':weekly,'league_incremental':league,'frozen_plus_candidate_same_period':merged_same,'frozen_plus_candidate_full_frozen_union':merged_full,
  'actual_receipt_replay':{'selected_latest_pregame_quote_per_FID':len(receipt_quotes),'quote_audit':dict(receipt_audit),
   'outside_frozen_unique_fids':len({r['fid'] for r in receipt_pred['market_plus_formation'] if not r['frozen_overlap']}),
   'models_all_receipt_fids':receipt_all,'models_incremental_outside_frozen':receipt_incremental,'weekly_incremental':receipt_weekly,
   'formation_feature_time_status':'Retrospective Formation dataset rows precede each target by date, but first-publication/receipt timestamps are absent; these rows are receipt-price replay with non-verified contemporaneous feature acquisition.'},
  'pairwise_candidate_fid_overlap':{a:{b:len({r['fid'] for r in pred[a] if not r['frozen_overlap']}&{r['fid'] for r in pred[b] if not r['frozen_overlap']}) for b in methods} for a in methods},
  'formal_orders':0,'formal_ledger_writes':0,'production_changes':False}
 (OUT/'formation_market_summary_20261121.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'coverage':summary['coverage'],'models':{m:v['incremental_outside_frozen'] for m,v in summaries.items()},'annual':annual,'merged_full':merged_full},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
