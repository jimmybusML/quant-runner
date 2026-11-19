#!/usr/bin/env python3
"""M8 research: transfer of a Crown team pricing residual across competitions.

Research only. Uses historical Crown event-time AH T1 prices and results; it
does not establish contemporaneous receipt or executable performance.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, statistics, csv, re, unicodedata, difflib
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[2]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
OUT=ROOT/'research/m8/cross_competition_team_pricing_20261119'
OUT.mkdir(parents=True,exist_ok=True)
PATH=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=WORK/'m8_independent_score_strength_20261114.jsonl'
MEM=ROOT/'research/m8/frozen_eight_boundary_expansion_20261119/frozen_eight_full_authoritative_membership_ledger_20261119.jsonl.gz'
FOUNDATION=WORK/'m8_foundation_20261115/historical_membership.jsonl'
GROUPS=('base','A','B','C','D','E','F','G')

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def read(path):
 with open(path,encoding='utf-8') as f:
  for line in f:
   if line.strip(): yield json.loads(line)
def ah_settle(line,side,hg,ag,odds):
 line=float(line);odds=float(odds)
 if abs(line*4-round(line*4))>1e-8: raise ValueError(f'bad quarter line {line}')
 legs=[line] if abs(round(line*2)/2-line)<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 out=[]
 for l in legs:
  margin=int(hg)-int(ag)+l if side=='home' else int(ag)-int(hg)-l
  out.append(odds-1 if margin>1e-9 else -1.0 if margin < -1e-9 else 0.0)
 return sum(out)/len(out)
def week(r):
 d=dt.date.fromisoformat(r['date']); y,w,_=d.isocalendar();return f'{y}-W{w:02d}'
def metrics(rows):
 if not rows:return {'n':0,'net_u':0.0,'roi_pct':None,'max_drawdown_u':0.0,'weekly':{},'weekly_mean':None}
 ordered=sorted(rows,key=lambda r:(r['date'],r['fid']))
 net=sum(float(r['pnl']) for r in ordered); n=len(ordered);cum=peak=dd=0.
 daily=collections.defaultdict(float);wk=collections.defaultdict(lambda:[0,0.])
 for r in ordered:
  daily[r['date']]+=float(r['pnl']); z=week(r);wk[z][0]+=1;wk[z][1]+=float(r['pnl'])
 for d in sorted(daily):cum+=daily[d];peak=max(peak,cum);dd=max(dd,peak-cum)
 weeks={k:{'n':v[0],'net_u':round(v[1],6)} for k,v in sorted(wk.items())}
 span=max(1,len(wk));return {'n':n,'net_u':round(net,6),'roi_pct':round(100*net/n,6),'max_drawdown_u':round(dd,6),'weekly':weeks,'weekly_mean':round(n/span,6),'weeks':span}
def q(v):
 try:
  x=float(v);return x if math.isfinite(x) else None
 except:return None
def as_utc(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 return x.replace(tzinfo=dt.timezone.utc) if x.tzinfo is None else x.astimezone(dt.timezone.utc)
CHINA=dt.timezone(dt.timedelta(hours=8))

# Current target FID must exist in both independent Crown market path and
# Crown score/identity archive. Payout histories are materialized only after
# each prior fixture is at least 72 hours old.
paths={str(x['fid']):x for x in read(PATH)}
scores={str(x['fid']):x for x in read(SCORES)}
members=collections.defaultdict(list)
with gzip.open(MEM,'rt',encoding='utf-8') as f:
 for line in f:
  x=json.loads(line);members[str(x['fid'])].append(x)
foundation_rows=list(read(FOUNDATION));foundation_by_fid=collections.defaultdict(list)
for x in foundation_rows:foundation_by_fid[str(x['fid'])].append(x)
if set(foundation_by_fid)!=set(members):raise ValueError('frozen-eight FID membership differs from original frozen foundation')
for fid,rr in foundation_by_fid.items():
 if {(x['cohort'],float(x['pnl'])) for x in rr}!={(x['cohort'],float(x['pnl'])) for x in members[fid]}:raise ValueError('frozen-eight group/PnL differs from foundation for '+fid)
rows=[];issues=collections.Counter()
for fid,p in paths.items():
 s=scores.get(fid)
 if not s: issues['missing_score_identity']+=1;continue
 try:
  if str(p['league'])!=str(s['league']):raise ValueError('league mismatch')
  if str(p['date'])[:10]!=str(s['date'])[:10]:raise ValueError('date mismatch')
  line=q(p.get('end_line'));ho=q(p.get('home_price'));ao=q(p.get('away_price'))
  if line is None or ho is None or ao is None or min(ho,ao)<=1:raise ValueError('quote missing')
  if abs(line*4-round(line*4))>1e-8:raise ValueError('line not quarter-grid')
  ko_utc=as_utc(s['ko']);ko_china=ko_utc.astimezone(CHINA)
  x={'fid':fid,'year':ko_china.year,'date':ko_china.date().isoformat(),'ko_utc':ko_utc.isoformat(),'kickoff_china':ko_china.isoformat(),
     'source_date_utc':str(s['date'])[:10],'source_year_utc':int(s['year']),'league':str(s['league']),
     'home_team_id':str(s['home']),'away_team_id':str(s['away']),'hg':int(s['hg']),'ag':int(s['ag']),
     'line':line,'home_odds':ho,'away_odds':ao,'home_pnl':q(p.get('end_home_U')),'away_pnl':q(p.get('end_away_U')),
     'path_fid':fid,'membership':members.get(fid,[])}
  if x['home_pnl'] is None or x['away_pnl'] is None:raise ValueError('payout missing')
  # Cross-check payout columns against AH arithmetic before modeling.
  if abs(ah_settle(line,'home',x['hg'],x['ag'],ho)-x['home_pnl'])>1e-6 or abs(ah_settle(line,'away',x['hg'],x['ag'],ao)-x['away_pnl'])>1e-6:raise ValueError('path_payout_arithmetic_mismatch')
  rows.append(x)
 except Exception as e: issues[type(e).__name__+':'+str(e)]+=1
rows.sort(key=lambda r:(r['date'],r['fid']))
frozen_fids=set(members)
frozen_member_rows=[];baseline_time_fallback=0
for fid,group_rows in members.items():
 for v in group_rows:
  s=scores.get(str(fid))
  if s:
   local=as_utc(s['ko']).astimezone(CHINA);date_cn=local.date().isoformat();year_cn=local.year
  else:
   date_cn=str(v['date'])[:10];year_cn=int(v['year']);baseline_time_fallback+=1
  frozen_member_rows.append({'fid':str(fid),'date':date_cn,'year':year_cn,'pnl':float(v['pnl'])})
# Conservative Crown team -> external club identity bridge, rebuilt from
# exact-score and team-name anchors. External match outcomes are not used as
# predictive features. A bridge key is usable only after its first anchor.
TM=WORK/'m8_pregame_info_source_20261117/games.csv.gz'
COMP={'1':'GB1','12':'IT1','14':'ES1','16':'L1','25':'FR1','29':'A1','31':'BE1','35':'TS1','37':'NL1','48':'PL1','51':'PO1','52':'RO1','61':'C1','62':'TR1','66':'SE1','70':'DK1','73':'JAP1','75':'RSK1','88':'NO1','141':'GR1','262':'SC1','290':'SA1','303':'SER1','319':'UKR1','26540':'KR1'}
def norm_name(s):
 x=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode('ascii').lower()
 x=re.sub(r'\b(fc|cf|sc|afc|ac|club|football|soccer|fk|as)\b',' ',x)
 return re.sub(r'[^a-z0-9]','',x)
def sim_name(a,b):
 a,b=norm_name(a),norm_name(b)
 if not a or not b:return 0.
 if a==b:return 1.
 if min(len(a),len(b))>=6 and (a in b or b in a):return .91
 return difflib.SequenceMatcher(None,a,b).ratio()
tm_sha=sha(TM);tm_matches=collections.defaultdict(list)
for z in csv.DictReader(gzip.open(TM,'rt',encoding='utf-8')):
 try:
  comp=z['competition_id'];day=dt.date.fromisoformat(z['date'])
  if comp not in set(COMP.values()):continue
  tm_matches[(comp,day.toordinal())].append((str(z['home_club_id']),str(z['away_club_id']),int(z['home_club_goals']),int(z['away_club_goals']),z['home_club_name'],z['away_club_name']))
 except Exception:continue
crown_matches={}
for page in sorted(pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules').glob('*/page-*.raw.json')):
 league=page.parent.name
 if league not in COMP:continue
 try:
  for z in json.loads(page.read_bytes())['data']['matches']:
   if z.get('status')!='full' or str(z.get('l_id'))!=league:continue
   fid=str(z.get('id'));day=dt.datetime.fromisoformat(str(z.get('start')).replace(' ','T')).replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).date()
   crown_matches[fid]=(league,str(z['h_id']),str(z['a_id']),day,int(z['hg']),int(z['ag']),str(z.get('h','')),str(z.get('a','')))
 except Exception:continue
anchors=collections.defaultdict(list);bridge_stats=collections.Counter()
for fid,r in scores.items():
 z=crown_matches.get(fid)
 if not z:continue
 league,hid,aid,day,hg,ag,hn,an=z
 for ordinal in (day.toordinal()-1,day.toordinal(),day.toordinal()+1):
  cand=[]
  for tm in tm_matches.get((COMP[league],ordinal),[]):
   if (hg,ag)!=(tm[2],tm[3]):continue
   a,b=sim_name(hn,tm[4]),sim_name(an,tm[5])
   if min(a,b)>=.85:cand.append((min(a,b),tm))
  cand.sort(key=lambda a:(-a[0],a[1][0],a[1][1]))
  if cand and (len(cand)==1 or cand[0][0]>cand[1][0]+.05):
   t=cand[0][1];anchors[(league,hid)].append((t[0],day));anchors[(league,aid)].append((t[1],day));bridge_stats['named_anchors']+=1
  elif cand:bridge_stats['ambiguous_anchors']+=1
candidate_map={};reverse=collections.defaultdict(set)
for key,vals in anchors.items():
 ids={v[0] for v in vals}
 if len(ids)!=1:bridge_stats['conflict_team_mapping']+=1;continue
 club=next(iter(ids));candidate_map[key]=club;reverse[(key[0],club)].add(key[1])
candidate_map={k:v for k,v in candidate_map.items() if len(reverse[(k[0],v)])==1}
anchor_first={k:min(day for club,day in vals) for k,vals in anchors.items() if k in candidate_map}
bridge_stats['accepted_league_team_keys']=len(candidate_map);bridge_stats['unique_tm_clubs']=len(set(candidate_map.values()))
hist_same=collections.defaultdict(list);hist_tm=collections.defaultdict(list)
def hist_stats(teamkey,tmclub,league,target_day):
 cutoff=target_day-dt.timedelta(days=3)
 same=[x for x in hist_same.get(teamkey,[]) if x['date']<cutoff]
 cross=[]
 if tmclub and anchor_first.get(teamkey,dt.date.max)<cutoff:
  cross=[x for x in hist_tm.get(tmclub,[]) if x['league']!=league and x['date']<cutoff and anchor_first.get(x['teamkey'],dt.date.max)<=x['date']]
 def stats(z):
  recent=[x for x in z if x['date']>=target_day-dt.timedelta(days=365)]
  last=z[-5:]
  # fixed shrinkage keeps tiny samples near zero and avoids hard history-count gates
  return [sum(x['pnl'] for x in recent)/(len(recent)+5),sum(x['pnl'] for x in last)/(len(last)+5),math.log1p(len(recent)),math.log1p(len(z))]
 return stats(same)+stats(cross)
def features(r,side):
 day=dt.date.fromisoformat(r['date']);home=side=='home'
 own=r['home_team_id'] if home else r['away_team_id'];opp=r['away_team_id'] if home else r['home_team_id']
 ownkey=(r['league'],own);oppkey=(r['league'],opp)
 ownclub=candidate_map.get(ownkey) if anchor_first.get(ownkey,dt.date.max)<day-dt.timedelta(days=3) else None
 oppclub=candidate_map.get(oppkey) if anchor_first.get(oppkey,dt.date.max)<day-dt.timedelta(days=3) else None
 ownst=hist_stats(ownkey,ownclub,r['league'],day);oppst=hist_stats(oppkey,oppclub,r['league'],day)
 line=r['line'] if home else -r['line'];odds=r['home_odds'] if home else r['away_odds']
 other=r['away_odds'] if home else r['home_odds']
 return [line,abs(line),odds,other,1/odds,1/other,(1/odds+1/other),*ownst,*oppst]
FEAT_NAMES=['signed_line','abs_line','selected_odds','other_odds','selected_implied','other_implied','pair_implied_sum',
 'own_same365_shrunk_mean','own_same_last5_shrunk_mean','own_same365_log_n','own_same_all_log_n',
 'own_cross365_shrunk_mean','own_cross_last5_shrunk_mean','own_cross365_log_n','own_cross_all_log_n',
 'opp_same365_shrunk_mean','opp_same_last5_shrunk_mean','opp_same365_log_n','opp_same_all_log_n',
 'opp_cross365_shrunk_mean','opp_cross_last5_shrunk_mean','opp_cross365_log_n','opp_cross_all_log_n']
variants={'market_only':[0,1,2,3,4,5,6],
 'market_plus_same_competition':[0,1,2,3,4,5,6,7,8,9,10,15,16,17,18],
 'market_plus_verified_club_cross_competition':[0,1,2,3,4,5,6,11,12,13,14,19,20,21,22],
 'market_plus_both_competition_histories':list(range(23))}
all_features={};both=[]
for i,r in enumerate(rows):
 day=dt.date.fromisoformat(r['date'])
 if r['year']>=2024 and r['fid'] not in frozen_fids:
  # Only create a comparable pair of possible decisions for outsiders.
  both.append(r)
 # Features are recorded before updating the historical event buffer.
 all_features[r['fid']]={'home':features(r,'home'),'away':features(r,'away')}
 # Historical Crown payout as a prior observation. Historical history is
 # strictly pre-target by the 72-hour query above. No target outcome is used
 # until the target is 72h in the past for later rows.
 for side,team in [('home',r['home_team_id']),('away',r['away_team_id'])]:
  key=(r['league'],team);rec={'date':day,'league':r['league'],'pnl':r[side+'_pnl'],'fid':r['fid'],'teamkey':key}
  hist_same[key].append(rec)
  club=candidate_map.get(key)
  if club and anchor_first.get(key,dt.date.max)<=day:hist_tm[club].append(rec)

# Train each calendar test year only on earlier years, and compare models on
# the identical outsiders. Ridge/scaling fixed ex ante; no target-year tuning.
preds=[]; yearly_model={};fit_specs={}
for year in (2024,2025,2026):
 train=[r for r in rows if r['year']<year]
 test=[r for r in both if r['year']==year]
 trainx=[];trainy=[]
 for r in train:
  fs=all_features[r['fid']]
  for side in ('home','away'):
   trainx.append(fs[side]);trainy.append(r[side+'_pnl'])
 yearly_model[str(year)]={'training_unique_fids':len(train),'test_outside_eight_fids':len(test),'training_years':sorted({r['year'] for r in train})}
 if not train or not test:continue
 model_preds={name:{} for name in variants}
 for name,cols in variants.items():
  raw=np.asarray(trainx,dtype=float)[:,cols]; y=np.asarray(trainy,dtype=float)
  mean=raw.mean(axis=0);scale=raw.std(axis=0);scale[scale<1e-12]=1.0
  X=(raw-mean)/scale;ym=float(y.mean());yc=y-ym
  beta=np.linalg.solve(X.T@X+100.0*np.eye(X.shape[1]),X.T@yc)
  fit_specs[(year,name)]={'cols':cols,'mean':mean.tolist(),'scale':scale.tolist(),'beta':beta.tolist(),'y_mean':ym,'training_years':yearly_model[str(year)]['training_years'],'training_unique_fids':len(train)}
  for r in test:
   fh=np.asarray(all_features[r['fid']]['home'])[cols].reshape(1,-1);fa=np.asarray(all_features[r['fid']]['away'])[cols].reshape(1,-1)
   ph=float((((fh-mean)/scale)@beta+ym).item());pa=float((((fa-mean)/scale)@beta+ym).item())
   model_preds[name][r['fid']]={'home_ev':ph,'away_ev':pa,'selected_side':'home' if ph>=pa else 'away'}
 for r in test:
  rec={'fid':r['fid'],'year':year,'date':r['date'],'ko_utc':r['ko_utc'],'kickoff_china':r['kickoff_china'],'league':r['league'],'home_team_id':r['home_team_id'],'away_team_id':r['away_team_id'],
   'AH_home_line':r['line'],'AH_home_odds':r['home_odds'],'AH_away_odds':r['away_odds'],'FT_home':r['hg'],'FT_away':r['ag'],
   'home_Crown_pnl':r['home_pnl'],'away_Crown_pnl':r['away_pnl'],'frozen_eight_overlap':False,
   'research_feature_inputs':{'names':FEAT_NAMES,'home_side':all_features[r['fid']]['home'],'away_side':all_features[r['fid']]['away']},
   'home_team_same_league_prior365_n':int(round(math.expm1(all_features[r['fid']]['home'][9]))),
   'home_team_cross_league_prior365_n':int(round(math.expm1(all_features[r['fid']]['home'][13]))),
   'away_team_same_league_prior365_n':int(round(math.expm1(all_features[r['fid']]['away'][9]))),
   'away_team_cross_league_prior365_n':int(round(math.expm1(all_features[r['fid']]['away'][13])))}
  rec['methods']={}
  for name in variants:
   z=model_preds[name][r['fid']];side=z['selected_side']; rec['methods'][name]={**z,'pnl':r[side+'_pnl'],'settlement':None}
  rec['methods']['crown_lower_odds_side']={'selected_side':'home' if r['home_odds']<=r['away_odds'] else 'away','pnl':r['home_pnl'] if r['home_odds']<=r['away_odds'] else r['away_pnl']}
  preds.append(rec)

# Same-FID profitability and merge audit. Union is used only for report math;
# a candidate FID overlapping any frozen group is never an incremental order.
model_summaries={}
for name in [*variants,'crown_lower_odds_side']:
 sel=[]
 for r in preds:
  m=r['methods'][name];sel.append({'fid':r['fid'],'date':r['date'],'year':r['year'],'league':r['league'],'side':m['selected_side'],'line':r['AH_home_line'],'odds':r['AH_home_odds'] if m['selected_side']=='home' else r['AH_away_odds'],'FT_home':r['FT_home'],'FT_away':r['FT_away'],'pnl':m['pnl'],'frozen_eight_overlap':False})
 model_summaries[name]={}
 for yr in (2024,2025,2026,'all'):
  group=sel if yr=='all' else [x for x in sel if x['year']==yr]
  model_summaries[name][str(yr)]=metrics(group)
  frozen=[v for v in frozen_member_rows if (yr=='all' and int(v['year']) in (2024,2025,2026)) or (yr!='all' and int(v['year'])==yr)]
  # Candidate set is outside frozen eight by construction; union includes each
  # frozen unique FID once, without adding a duplicate FID.
  dedup={x['fid']:x for x in frozen};dedup.update({x['fid']:x for x in group})
  merged=metrics(list(dedup.values()))
  model_summaries[name][str(yr)]['merged_with_frozen_eight']=merged
  model_summaries[name][str(yr)]['incremental_net_u_vs_frozen']=round(sum(x['pnl'] for x in group),6)

# Separate true HTTP receipt repricing on the same 2026 outside-eight FIDs.
# One earliest verifiable, pre-kickoff HTTP receipt per FID; use its Crown AH
# prices, but the team history features remain retrospective event-time inputs
# (their contemporaneous availability is not proven).
def parse_utc(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 return x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc) if x.tzinfo is None else x.astimezone(dt.timezone.utc)
archive=WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
receipt_rows=list(read(archive));test2026={r['fid']:r for r in both if r['year']==2026}
receipt_candidates=collections.defaultdict(list);receipt_fail=collections.Counter()
for rr in receipt_rows:
 fid=str(rr.get('fixture_id'))
 if fid not in test2026:continue
 try:
  recut=parse_utc(rr['received_utc']);kick=parse_utc(rr['kickoff_utc'])
  if not recut<kick:raise ValueError('receipt_not_pregame')
  attempt=json.loads(pathlib.Path(rr['source_file']).read_bytes())
  body=attempt['raw_response'];body_sha=hashlib.sha256(body.encode('utf-8')).hexdigest()
  if body_sha!=rr['raw_sha256']:raise ValueError('receipt_raw_sha_mismatch')
  response=json.loads(body);data=response.get('data',[]);matches=data if isinstance(data,list) else [data]
  matches=[m for m in matches if str(m.get('id'))==fid]
  if len(matches)!=1:raise ValueError('receipt_fid_cardinality')
  m=matches[0];crown=[b for b in m.get('bookmakers',[]) if str(b.get('slug','')).lower()=='crown']
  if len(crown)!=1:raise ValueError('receipt_crown_cardinality')
  ah=rr['markets']['AH'];source_time=parse_utc(ah['source_event_utc']);line=float(ah['line']);ho=float(ah['odds']['home']);ao=float(ah['odds']['away'])
  if source_time>recut:raise ValueError('quote_after_receipt')
  found=False
  for qrow in crown[0].get('asian_list') or []:
   try:
    qt=parse_utc(qrow[4]);ln,qh,qa=map(float,qrow[1:4])
    if abs((qt-source_time).total_seconds())<1 and all(abs(a-b)<1e-8 for a,b in ((ln,line),(qh,ho),(qa,ao))):found=True;break
   except Exception:continue
  if not found:raise ValueError('receipt_quote_not_in_raw_Crown_body')
  receipt_candidates[fid].append({'fid':fid,'received_utc':recut.isoformat(),'kickoff_utc':kick.isoformat(),'quote_source_utc':source_time.isoformat(),
   'line':line,'home_odds':ho,'away_odds':ao,'snapshot_horizon':rr.get('snapshot_horizon'),'raw_body_sha256':body_sha,'snapshot_sha256':rr.get('snapshot_sha256'),'raw_file':rr['source_file']})
 except Exception as e:receipt_fail[str(e)]+=1
receipt_orders=[]
for fid,opts in receipt_candidates.items():
 rr=sorted(opts,key=lambda x:x['received_utc'])[0];target=test2026[fid]
 rr.update({'year':2026,'date':target['date'],'league':target['league'],'home_team_id':target['home_team_id'],'away_team_id':target['away_team_id'],
  'FT_home':target['hg'],'FT_away':target['ag'],'kickoff_china':target['kickoff_china']})
 for name,cols in variants.items():
  spec=fit_specs[(2026,name)];mean=np.asarray(spec['mean']);scale=np.asarray(spec['scale']);beta=np.asarray(spec['beta']);ym=float(spec['y_mean'])
  sides={}
  for side in ('home','away'):
   f=np.asarray(all_features[fid][side],dtype=float).copy()
   ishome=side=='home';f[0]=rr['line'] if ishome else -rr['line'];f[1]=abs(f[0]);f[2]=rr['home_odds'] if ishome else rr['away_odds'];f[3]=rr['away_odds'] if ishome else rr['home_odds']
   f[4]=1/f[2];f[5]=1/f[3];f[6]=f[4]+f[5]
   sides[side]=float((((f[cols]-mean)/scale)@beta+ym).item())
  side='home' if sides['home']>=sides['away'] else 'away';odds=rr['home_odds'] if side=='home' else rr['away_odds']
  rr.setdefault('methods',{})[name]={'selected_side':side,'home_ev':sides['home'],'away_ev':sides['away'],'pnl':ah_settle(rr['line'],side,rr['FT_home'],rr['FT_away'],odds)}
 side='home' if rr['home_odds']<=rr['away_odds'] else 'away';odds=rr['home_odds'] if side=='home' else rr['away_odds']
 rr['methods']['crown_lower_odds_side']={'selected_side':side,'pnl':ah_settle(rr['line'],side,rr['FT_home'],rr['FT_away'],odds)}
 receipt_orders.append(rr)
receipt_summaries={}
for name in [*variants,'crown_lower_odds_side']:
 receipt_summaries[name]=metrics([{'fid':r['fid'],'date':r['date'],'year':2026,'league':r['league'],'pnl':r['methods'][name]['pnl']} for r in receipt_orders])
receipt_ids={x['fid'] for x in receipt_orders}
receipt_event_time_summaries={}
for name in [*variants,'crown_lower_odds_side']:
 rr=[r for r in preds if r['fid'] in receipt_ids]
 receipt_event_time_summaries[name]=metrics([{'fid':r['fid'],'date':r['date'],'year':2026,'league':r['league'],'pnl':r['methods'][name]['pnl']} for r in rr])
direction_overlap={}
method_names=[*variants,'crown_lower_odds_side']
for i,a in enumerate(method_names):
 for b in method_names[i+1:]:
  amap={r['fid']:r['methods'][a]['selected_side'] for r in preds};bmap={r['fid']:r['methods'][b]['selected_side'] for r in preds};common=set(amap)&set(bmap)
  direction_overlap[a+'__vs__'+b]={'common_unique_fids':len(common),'same_side':sum(amap[f]==bmap[f] for f in common),'opposite_side':sum(amap[f]!=bmap[f] for f in common),'same_side_pct':round(100*sum(amap[f]==bmap[f] for f in common)/len(common),6) if common else None}
with gzip.open(OUT/'verified_actual_receipt_reprice_ledger_20261119.jsonl.gz','wt',encoding='utf-8') as f:
 for x in receipt_orders:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')

# Missing cross-league history availability diagnostics on test outsiders.
coverage={}
for year in (2024,2025,2026):
 subset=[r for r in preds if r['year']==year]
 coverage[str(year)]={'test_unique_fids':len(subset),
  'home_has_cross_league_history':sum(r['home_team_cross_league_prior365_n']>0 for r in subset),
  'away_has_cross_league_history':sum(r['away_team_cross_league_prior365_n']>0 for r in subset),
  'both_sides_have_cross_league_history':sum(r['home_team_cross_league_prior365_n']>0 and r['away_team_cross_league_prior365_n']>0 for r in subset)}

# Per-week summaries for every model and year remain accessible in the summary;
# the JSONL retains all side choices, features, outcomes, and methods.
with gzip.open(OUT/'cross_competition_team_pricing_predictions_20261119.jsonl.gz','wt',encoding='utf-8') as f:
 for x in preds:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
summary={'study':'M8_CROSS_COMPETITION_TEAM_CROWN_AH_RESIDUAL_TRANSFER_20261119','research_only':True,
 'hypothesis':'A Crown team ID may carry prior market-relative AH payout information across competition IDs when the team changes competitive environment. This differs from earlier league+team-key residual models and generic external-stat cross-league migration.',
 'novelty_audit':['The only potentially distinct mechanism is transferring a lagged Crown AH settlement residual across competition IDs for a verified same club. Direct Crown team IDs yielded zero cross-league history; the one-to-one external identity bridge also yielded zero such historical observations in the 2024-26 target pool, so this mechanism was not estimable.','Same-competition team payout features are a control and overlap with earlier team residual / team-contract payout work (R26/R30 and A-L H); they are not presented as a newly discovered source.','Earlier cross-league sports-stat transfer studies moved training rows/metrics across competitions, not lagged same-club Crown AH payout residuals.','R1-R65, A-L and M1-M8 market-only, team residual, familiarity, schedule, player load, motivation, price-state and boundary studies reviewed; no exact positive mechanism was rebranded.'],
 'input_sha256':{str(p):sha(p) for p in (PATH,SCORES,MEM,FOUNDATION)},
 'frozen_eight_validation':{'original_foundation_fid_count':len(foundation_by_fid),'full_authoritative_ledger_fid_count':len(members),'same_unique_fids':True,'group_and_pnl_rows_match':True,'original_foundation_sha256':sha(FOUNDATION)},
 'coverage':{'crown_path_rows':len(paths),'score_identity_rows':len(scores),'common_valid_rows':len(rows),'year_counts_china_time':dict(collections.Counter(r['year'] for r in rows)),
   'frozen_eight_unique_fids':len(frozen_fids),'frozen_member_beijing_time_fallback_rows':baseline_time_fallback,'frozen_eight_2024_2026_china_time_baseline':metrics([r for r in frozen_member_rows if r['year'] in (2024,2025,2026)]),'candidate_test_years_china_time':{str(y):sum(x['year']==y and x['fid'] not in frozen_fids for x in rows) for y in (2024,2025,2026)},
   'quarantine_or_missing':dict(issues),'feature_available_fields':FEAT_NAMES,'target_market_field':'historical Crown end T1 AH line + paired prices; target event-time, not confirmed HTTP received'},
 'time_forward':{'calendar':'Beijing time (UTC+08:00) defines report year, date, ISO week and forward split','training':'all Crown score/path fixtures strictly earlier China-time calendar years than each target year','feature_lag':'only prior team matches on China dates earlier than target local date minus 3 days; same-day order excluded conservatively','models':'Ridge alpha=100, scaler fit on prior years only; model variants and columns fixed before test-year scoring','action':'one side selected per unique candidate FID by larger predicted Crown unit payout; no abstention threshold and no future T1 group identity/outcome used'},
 'models':{'market_features':['signed current AH line for selected side','absolute line','selected-side and opposing odds','paired implied probabilities and total'],
   'market_plus_same_competition':'market features plus lagged same-team Crown payout summaries within current competition',
   'market_plus_verified_club_cross_competition':'market features plus lagged same-club Crown payout summaries outside current competition via the anchored identity bridge',
   'market_plus_both_competition_histories':'market plus both histories','crown_lower_odds_side':'descriptive favorite-side benchmark'},
 'walkforward_training_by_test_year_china_time':yearly_model,'method_results':model_summaries,'cross_competition_history_coverage':coverage,'candidate_overlap_and_direction_agreement':direction_overlap,
 'identity_bridge':{'source':str(TM),'source_sha256':tm_sha,'method':'one-to-one Crown league/team to Transfermarkt club identity from unique exact-score + normalized team-name anchors; mapping only used after its first anchor date; external outcome values are not predictive features','anchor_and_mapping_counts':dict(bridge_stats),'mapped_league_team_keys':len(candidate_map),'mapped_unique_clubs':len(set(candidate_map.values()))},
 'important_limitations':['Historical event-time quotes and payout histories are not contemporaneous received information.','No claim of live fill or formal Telegram orders.','History coverage is restricted to saved Crown path and score inventories.','A fixed ridge action is an experimental estimator, not a trading Gate.','Study design was authored after review of historical reports and is not a preregistered blind discovery.'],
 'receipt_validation':{'crown_receipt_reprice_replay':True,'source_archive':str(archive),'source_archive_sha256':sha(archive),'candidate_fids_with_at_least_one_valid_receipt':len(receipt_candidates),'unique_outside_eight_fids_repriced':len(receipt_orders),'verified_receipt_horizon_distribution':dict(collections.Counter(r.get('snapshot_horizon') for r in receipt_orders)),
  'receipt_raw_sha_and_quote_crosschecks':{'candidate_receipt_attempt_rows_examined':len(receipt_candidates)+sum(receipt_fail.values()),'invalid_or_unmatched_attempts':dict(receipt_fail),'selection':'earliest valid pre-kickoff Crown AH receipt per candidate FID','raw_Crown_quote_and_receipt_SHA_checked':True},
  'results_at_receipt_quote':receipt_summaries,'same_fid_event_time_results':receipt_event_time_summaries,
  'limitation':'The 2026 model is trained on historical event-time T1 market features and retrospective Crown team-history summaries. This reprice applies receipt-time AH price to the frozen model on the same FIDs; historical team features are not proven contemporaneously available, and target receipt horizons vary. It is not a blinded prospective replay or formal order evidence.'},
 'production_models_telegram_ledger_collection_changed':False}
(OUT/'CROSS_COMPETITION_TEAM_PRICING_RESULTS_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'coverage':summary['coverage'],'cross_competition_history_coverage':coverage,'results':{k:{y:{z:v for z,v in x[y].items() if z in ('n','net_u','roi_pct','max_drawdown_u','weekly_mean','weeks','incremental_net_u_vs_frozen')} for y in ('2024','2025','2026','all')} for k,x in model_summaries.items()}},ensure_ascii=False,indent=2))
