#!/usr/bin/env python3
"""Independent reconstruction of red-card-adjusted Crown AH results.

Re-reads the source schedule pages, Crown red-card bodies, frozen membership,
market paths and output ledger. Does not import the research runner's helpers.
"""
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, sqlite3
from zoneinfo import ZoneInfo
import numpy as np

HERE=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path(__file__).resolve().parents[3]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=pathlib.Path('/Users/mac/QuantAsiaDesk/data')
P49=WORK/'m8_late_full_path_water_features_20261114.jsonl'
P15=HERE/'expanded15_t1_path_input.jsonl.gz'
FROZEN=WORK/'m8_foundation_20261115/historical_membership.jsonl'
PAGE_MANIFEST=HERE/'schedule_page_sha256_manifest.json'
CARD_INDEX=HERE/'red_card_history_source_index.jsonl.gz'
LEDGER=HERE/'red_card_adjusted_form_per_fixture.jsonl.gz'
SUMMARY=HERE/'red_card_adjusted_form_summary.json'
DB=DATA/'crown_quote_store/crown_quotes.sqlite3'
TZ=ZoneInfo('Asia/Shanghai'); UTC=dt.timezone.utc
METHODS=('market','market_plus_raw_form','market_plus_red_adjusted_form','market_plus_raw_and_red_context','low_price')
issues=collections.Counter(); checks=collections.Counter()

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def parse(s):
 x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return x.astimezone(UTC) if x.tzinfo else x.replace(tzinfo=TZ).astimezone(UTC)
def settle(line,side,gd,odds):
 h=float(line) if side=='home' else -float(line); margin=int(gd) if side=='home' else -int(gd)
 if abs(h*4-round(h*4))>1e-8: raise ValueError('bad AH quarter grid')
 legs=[h] if int(round(h*4))%2==0 else [math.floor(h*2)/2,math.ceil(h*2)/2]
 pnl=[]; states=[]
 for leg in legs:
  z=margin+leg; states.append('W' if z>1e-9 else 'L' if z<-1e-9 else 'P')
  pnl.append(float(odds)-1 if z>1e-9 else -1. if z<-1e-9 else 0.)
 label=('full_win' if all(x=='W' for x in states) else 'full_loss' if all(x=='L' for x in states) else 'push' if all(x=='P' for x in states) else 'half_win' if 'W' in states else 'half_loss')
 return label,sum(pnl)/len(pnl)
def read(path):
 if str(path).endswith('.gz'):
  with gzip.open(path,'rt',encoding='utf-8') as f:
   for line in f:
    if line.strip():yield json.loads(line)
 else:
  with open(path,encoding='utf-8') as f:
   for line in f:
    if line.strip():yield json.loads(line)
def eq(a,b,tol=1e-9):
 try:return abs(float(a)-float(b))<=tol
 except:return a==b

# Target market inventory from frozen historical Crown path derivatives.
targets={}
for r in read(P49):
 fid=str(r['fid']); targets[fid]={'fid':fid,'league':str(r['league']),'line':float(r['end_line']),'home_odds':float(r['home_price']),'away_odds':float(r['away_price']),'source_group':'original49_T1'}
for r in read(P15):
 fid=str(r['fid'])
 if fid in targets:issues['target_duplicate_fid']+=1
 targets[fid]={'fid':fid,'league':str(r['league']),'line':float(r['end_line']),'home_odds':float(r['home_price']),'away_odds':float(r['away_price']),'source_group':'expanded15_T1'}
checks['target_paths']=len(targets)

# Verify every cached schedule source body hash and rebuild the completed-game corpus.
page_map=json.loads(PAGE_MANIFEST.read_text())
target_ids=set(targets); target_leagues={v['league'] for v in targets.values()}; found=collections.defaultdict(list); history=collections.defaultdict(list)
for ptxt,expected in page_map.items():
 p=pathlib.Path(ptxt)
 if not p.is_file() or sha(p)!=expected: issues['schedule_page_sha_mismatch']+=1;continue
 try: matches=(json.loads(p.read_bytes()).get('data') or {}).get('matches') or []
 except: issues['schedule_page_parse_error']+=1;continue
 for m in matches:
  fid=str(m.get('id') or '')
  if not fid or m.get('status')!='full':continue
  league=str(m.get('l_id') or '')
  if league not in target_leagues:continue
  try:
   ko=parse(m['start']); rec={'fid':fid,'league':league,'home_id':str(m['h_id']),'away_id':str(m['a_id']),'home':str(m.get('h') or ''),'away':str(m.get('a') or ''),'hg':int(m['hg']),'ag':int(m['ag']),'kickoff_utc':ko.isoformat(),'date':ko.astimezone(TZ).date().isoformat()}
   if not rec['home_id'] or not rec['away_id'] or rec['home_id']==rec['away_id'] or min(rec['hg'],rec['ag'])<0:continue
  except:continue
  history[fid].append(rec)
  if fid in target_ids:found[fid].append(rec)
checks['schedule_pages']=len(page_map)
identity={};
for fid,vals in found.items():
 sig={(x['league'],x['home_id'],x['away_id'],x['hg'],x['ag'],x['kickoff_utc']) for x in vals}
 if len(sig)!=1:issues['target_identity_conflict']+=1
 else:identity[fid]=vals[0]
cleanhist={}
for fid,vals in history.items():
 sig={(x['league'],x['home_id'],x['away_id'],x['hg'],x['ag'],x['kickoff_utc']) for x in vals}
 if len(sig)==1:cleanhist[fid]=vals[0]
 else:issues['history_identity_conflict']+=1
checks['target_identity']=len(identity);checks['full_score_history']=len(cleanhist)

# Re-read indexed raw Crown responses and verify SHA plus identities, FT and card counts.
card={}
for r in read(CARD_INDEX):
 path=pathlib.Path(r['source_file'])
 if not path.is_file() or sha(path)!=r['source_sha256']:
  issues['card_raw_sha_mismatch']+=1;continue
 try:
  b=json.loads(path.read_bytes()); d=b.get('data');d=d[0] if isinstance(d,list) and d else d
  values={'fid':str(d.get('id')),'league':str(d.get('l_id')),'home_id':str(d.get('h_id')),'away_id':str(d.get('a_id')),'hg':int(d['hg']),'ag':int(d['ag']),'red_home':int(d['hrc']),'red_away':int(d['arc'])}
  if d.get('status')!='full' or any(str(values[k])!=str(r[k]) for k in values):issues['card_raw_identity_or_value_mismatch']+=1;continue
  if r['fid'] in card:issues['card_index_duplicate_fid']+=1;continue
  card[r['fid']]=r
 except Exception:issues['card_raw_parse_error']+=1
checks['card_index_rows']=sum(1 for _ in read(CARD_INDEX));checks['card_raw_verified']=len(card)

# Build full prior-score history and card-conditioned history.
score_games={fid:r for fid,r in cleanhist.items()}
for fid,c in card.items():
 old=score_games.get(fid)
 if old and (old['league'],old['home_id'],old['away_id'],old['hg'],old['ag'])!=(c['league'],c['home_id'],c['away_id'],c['hg'],c['ag']):
  issues['card_schedule_conflict']+=1;continue
 if not old:
  k=parse(c['kickoff_utc']);score_games[fid]={'fid':fid,'league':c['league'],'home_id':c['home_id'],'away_id':c['away_id'],'hg':int(c['hg']),'ag':int(c['ag']),'date':k.astimezone(TZ).date().isoformat(),'kickoff_utc':k.isoformat()}
score_hist=collections.defaultdict(list); card_hist=collections.defaultdict(list)
for r in score_games.values():
 day=dt.date.fromisoformat(r['date']).toordinal()
 score_hist[(r['league'],r['home_id'])].append((day,r['hg']-r['ag'],r['fid']))
 score_hist[(r['league'],r['away_id'])].append((day,r['ag']-r['hg'],r['fid']))
for r in card.values():
 day=dt.date.fromisoformat(r['date']).toordinal()
 card_hist[(r['league'],r['home_id'])].append((day,int(r['hg'])-int(r['ag']),int(r['red_away'])-int(r['red_home']),r['fid'],r['source_sha256']))
 card_hist[(r['league'],r['away_id'])].append((day,int(r['ag'])-int(r['hg']),int(r['red_home'])-int(r['red_away']),r['fid'],r['source_sha256']))
for key in score_hist:score_hist[key].sort()
for key in card_hist:card_hist[key].sort()

def prior_form(hist,key,target_date):
 cutoff=dt.date.fromisoformat(target_date).toordinal()-3; start=cutoff-365
 seq=[x for x in hist.get(key,[]) if start<=x[0]<cutoff]
 if not seq:return {'n':0,'gd_avg':None,'last_gd':None,'last_date':None}
 return {'n':len(seq),'gd_avg':sum(x[1] for x in seq)/len(seq),'last_gd':seq[-1][1],'last_date':dt.date.fromordinal(seq[-1][0]).isoformat()}
def prior_card(key,target_date):
 cutoff=dt.date.fromisoformat(target_date).toordinal()-3;start=cutoff-365
 seq=[x for x in card_hist.get(key,[]) if start<=x[0]<cutoff]
 if not seq:return {'n':0,'gd_avg':None,'red_adv_avg':None,'last_gd':None,'last_red_adv':None,'last_date':None,'source_sha256':None}
 src=hashlib.sha256('\n'.join(f'{x[3]}:{x[4]}' for x in seq).encode()).hexdigest()
 return {'n':len(seq),'gd_avg':sum(x[1] for x in seq)/len(seq),'red_adv_avg':sum(x[2] for x in seq)/len(seq),'last_gd':seq[-1][1],'last_red_adv':seq[-1][2],'last_date':dt.date.fromordinal(seq[-1][0]).isoformat(),'source_sha256':src}

frozen={str(json.loads(x)['fid']) for x in open(FROZEN,encoding='utf-8') if x.strip()}
checks['frozen_members']=len(frozen)
score_archive={}
for srow in read(WORK/'m8_independent_score_strength_20261114.jsonl'):
 fid=str(srow['fid'])
 if fid in score_archive:issues['score_archive_duplicate_fid']+=1
 score_archive[fid]=srow
rows=[]
for fid,p in targets.items():
 ident=identity.get(fid)
 if not ident or ident['league']!=p['league']:continue
 sr=score_archive.get(fid)
 if sr and (str(sr['league']),str(sr['home']),str(sr['away']),int(sr['hg']),int(sr['ag']))!=(ident['league'],ident['home_id'],ident['away_id'],ident['hg'],ident['ag']):
  issues['independent_score_identity_mismatch']+=1;continue
 if fid in card and (card[fid]['league'],card[fid]['home_id'],card[fid]['away_id'],int(card[fid]['hg']),int(card[fid]['ag']))!=(ident['league'],ident['home_id'],ident['away_id'],ident['hg'],ident['ag']):
  issues['target_card_ft_conflict']+=1;continue
 line=p['line'];ho=p['home_odds'];ao=p['away_odds'];gd=ident['hg']-ident['ag']
 hs,hu=settle(line,'home',gd,ho);as_,au=settle(line,'away',gd,ao)
 day=dt.date.fromisoformat(ident['date']);iso=day.isocalendar()
 hraw=prior_form(score_hist,(ident['league'],ident['home_id']),ident['date']); araw=prior_form(score_hist,(ident['league'],ident['away_id']),ident['date'])
 if hraw['n']<=0 or araw['n']<=0:continue
 hc=prior_card((ident['league'],ident['home_id']),ident['date']);ac=prior_card((ident['league'],ident['away_id']),ident['date'])
 rows.append({**ident,**p,'date':ident['date'],'year':day.year,'iso_week':f'{iso.year}-W{iso.week:02d}','gd':gd,'home_settlement':hs,'home_net_u':hu,'away_settlement':as_,'away_net_u':au,'market_margin':-line+.25*math.log(ao/ho),'raw_form':{'home':hraw,'away':araw},'card_form':{'home':hc,'away':ac},'frozen_eight_overlap':fid in frozen})
checks['feature_rows_reconstructed']=len(rows)

# Annual expanding training and exact model predictions, rebuilt without importing runner helpers.
def feat(r,kind,beta):
 hr,ar=r['raw_form']['home'],r['raw_form']['away'];hc,ac=r['card_form']['home'],r['card_form']['away']
 rh,ra=float(hr['gd_avg']),float(ar['gd_avg'])
 dh=-beta*float(hc['red_adv_avg']) if hc['red_adv_avg'] is not None else 0.
 da=-beta*float(ac['red_adv_avg']) if ac['red_adv_avg'] is not None else 0.
 nh,na=int(hc['n']),int(ac['n']); gap=(float(hc['red_adv_avg'] or 0.)-float(ac['red_adv_avg'] or 0.))
 base=[r['market_margin'],r['line'],.25*math.log(r['away_odds']/r['home_odds'])]
 raw=[rh,ra,rh-ra,rh+ra,hr['last_gd'],ar['last_gd'],math.log1p(hr['n']),math.log1p(ar['n'])]
 adjusted=[rh+dh,ra+da,(rh+dh)-(ra+da),(rh+dh)+(ra+da),dh,da]
 ctx=[gap,math.log1p(nh),math.log1p(na),int(nh==0),int(na==0),nh/max(hr['n'],1),na/max(ar['n'],1)]
 return base if kind=='market' else base+raw if kind=='market_plus_raw_form' else base+adjusted+ctx if kind=='market_plus_red_adjusted_form' else base+raw+adjusted+ctx

def ridge(x,y,xt):
 x=np.asarray(x,float);y=np.asarray(y,float);xt=np.asarray(xt,float);mu=x.mean(0);sd=x.std(0);sd[sd<1e-10]=1
 z=(x-mu)/sd;zt=(xt-mu)/sd;d=np.column_stack([np.ones(len(z)),z]);dtst=np.column_stack([np.ones(len(zt)),zt]);pen=np.eye(d.shape[1])*100.;pen[0,0]=0
 return dtst@np.linalg.solve(d.T@d+pen,d.T@y)

byyear=collections.defaultdict(list)
for r in rows:byyear[r['year']].append(r)
models={m:{} for m in METHODS}
for year in (2024,2025,2026):
 train=[r for r in rows if 2019<=r['year']<year];test=byyear[year]
 prior=[r for r in card.values() if 2019<=int(r['date'][:4])<year]
 red=np.array([int(r['red_away'])-int(r['red_home']) for r in prior]+[int(r['red_home'])-int(r['red_away']) for r in prior],float)
 gd=np.array([int(r['hg'])-int(r['ag']) for r in prior]+[int(r['ag'])-int(r['hg']) for r in prior],float)
 beta=float(red@gd/(red@red)) if red@red else 0.
 for method in METHODS:
  if method=='low_price':
   for r in test:models[method][r['fid']]='home' if r['home_odds']<=r['away_odds'] else 'away'
  else:
   preds=ridge([feat(r,method,beta) for r in train],[r['home_net_u']-r['away_net_u'] for r in train],[feat(r,method,beta) for r in test])
   for r,pred in zip(test,preds):models[method][r['fid']]='home' if pred>0 else 'away'
 checks[f'fold_{year}_train']=len(train);checks[f'fold_{year}_test']=len(test)
 checks[f'fold_{year}_beta']=beta

# Reconcile output, every selection, AH settlement, time boundary and portfolios.
ledger_rows=list(read(LEDGER));ledger={r['fid']:r for r in ledger_rows}
if len(ledger)!=len(ledger_rows):issues['ledger_duplicate_fid']+=1
checks['ledger_rows']=len(ledger)
scored_rows=[r for r in rows if r['year'] in (2024,2025,2026)]
for r in scored_rows:
 fid=r['fid']; out=ledger.get(fid)
 if not out:issues['reconstructed_fid_missing_from_ledger']+=1;continue
 for team in ('home','away'):
  for k in ('n','last_date'):
   if r['raw_form'][team][k]!=out['raw_form'][team][k]:issues['raw_form_mismatch']+=1
  if not eq(r['raw_form'][team]['gd_avg'],out['raw_form'][team]['gd_avg']):issues['raw_form_mismatch']+=1
  c1=r['card_form'][team];c2=out['card_form'][team]
  for k in ('n','last_date','source_sha256'):
   if c1[k]!=c2[k]:issues['card_form_mismatch']+=1
  for k in ('gd_avg','red_adv_avg'):
   if not eq(c1[k],c2[k]):issues['card_form_mismatch']+=1
 if fid in frozen and not out['frozen_eight_overlap']:issues['frozen_overlap_flag_mismatch']+=1
 for m in METHODS:
  side=models[m].get(fid)
  mo=out.get('methods',{}).get(m,{})
  if mo.get('side')!=side:issues['model_side_mismatch_'+m]+=1
  if not side:continue
  state,pnl=settle(r['line'],side,r['gd'],r[f'{side}_odds'])
  if mo.get('settlement')!=state or not eq(mo.get('net_u'),pnl):issues['AH_pnl_mismatch_'+m]+=1
  if not eq(mo.get('odds'),r[f'{side}_odds']):issues['selected_odds_mismatch_'+m]+=1
  if any(dt.date.fromisoformat(out['raw_form'][team]['last_date'])>=dt.date.fromisoformat(r['date'])-dt.timedelta(days=3) for team in ('home','away')):issues['future_score_feature']+=1
  if any(out['card_form'][team]['last_date'] and dt.date.fromisoformat(out['card_form'][team]['last_date'])>=dt.date.fromisoformat(r['date'])-dt.timedelta(days=3) for team in ('home','away')):issues['future_card_feature']+=1

# Current SQLite T1 provenance check, keeping source-event time distinct from receive time.
cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True);cx.row_factory=sqlite3.Row
ids=list(ledger); qmap=collections.defaultdict(list)
for i in range(0,len(ids),700):
 chunk=ids[i:i+700];marks=','.join('?' for _ in chunk)
 q=f'''SELECT q.fixture_id,q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc,q.response_received_at_utc,c.capture_mode,c.prospective_observation,c.response_sha256
 FROM asian_quote q JOIN capture c USING(capture_key) WHERE q.fixture_id IN ({marks}) AND c.data_layer='movement' AND q.quote_kind='movement' ORDER BY q.fixture_id,q.quote_source_at_utc,q.response_received_at_utc'''
 for x in cx.execute(q,chunk):qmap[str(x['fixture_id'])].append(dict(x))
cx.close()
quote_count=collections.Counter();receipt_fids=set()
for fid,out in ledger.items():
 ko=parse(out['kickoff_utc']);cut=ko-dt.timedelta(hours=1);opts=[]
 for q in qmap.get(fid,[]):
  ts=parse(q['quote_source_at_utc'])
  try:
   if ts<=cut and abs(float(q['handicap_home'])*4-round(float(q['handicap_home'])*4))<1e-8:opts.append((ts,q))
  except (TypeError,ValueError):continue
 if not opts:quote_count['no_sqlite_quote_at_or_before_T1']+=1;continue
 ts,q=opts[-1]
 match=abs(float(q['handicap_home'])-out['line'])<1e-8 and abs(float(q['home_decimal'])-out['home_odds'])<1e-8 and abs(float(q['away_decimal'])-out['away_odds'])<1e-8
 quote_count['exact_price_match' if match else 'price_mismatch']+=1
 if q['response_sha256']!=out.get('t1_source_response_sha256'):issues['quote_response_sha_mismatch']+=1
 if q['response_received_at_utc']!=out.get('t1_response_received_at_utc'):issues['quote_receive_time_mismatch']+=1
 if bool(q['prospective_observation']):receipt_fids.add(fid)
checks['sqlite_t1_quote_audit']=dict(quote_count);checks['receipt_fids_in_test_ledger']=len(receipt_fids)
checks['outside_frozen_candidate_fids']=sum(not r['frozen_eight_overlap'] for r in ledger.values())
checks['outside_frozen_duplicate_fids']=len([r for r in ledger.values() if not r['frozen_eight_overlap']])-len({r['fid'] for r in ledger.values() if not r['frozen_eight_overlap']})

# Independently aggregate candidate outcomes and compare summary totals.
s=json.loads(SUMMARY.read_text());candidate=[r for r in ledger.values() if not r['frozen_eight_overlap']]
aggregates={}
for m in METHODS:
 bets=[r for r in candidate if r['methods'][m]['side']]
 u=sum(r['methods'][m]['net_u'] for r in bets); n=len(bets)
 daily=collections.defaultdict(float);weekly=collections.defaultdict(lambda:[0,0.])
 byleague=collections.defaultdict(float);byyear=collections.defaultdict(float)
 for r in bets:
  daily[r['date']]+=r['methods'][m]['net_u'];weekly[r['iso_week']][0]+=1;weekly[r['iso_week']][1]+=r['methods'][m]['net_u'];byleague[r['league_name']]+=r['methods'][m]['net_u'];byyear[str(r['year'])]+=r['methods'][m]['net_u']
 cum=peak=mdd=0.
 for _,v in sorted(daily.items()):cum+=v;peak=max(peak,cum);mdd=max(mdd,peak-cum)
 exp=s['outside_frozen_eight'][m]
 if n!=exp['orders'] or not eq(u,exp['net_u'],1e-7) or not eq(mdd,exp['mdd_u'],1e-6):issues['aggregate_mismatch_'+m]+=1
 if len(weekly)!=exp['active_iso_weeks']:issues['weekly_count_mismatch_'+m]+=1
 aggregates[m]={'orders':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6),'mdd_u':round(mdd,6),'active_iso_weeks':len(weekly),'active_week_avg':round(n/len(weekly),6),'year_net_u':dict(sorted(byyear.items())),'league_net_u':dict(sorted(byleague.items()))}
checks['aggregate_methods']=aggregates
checks['overlap_frozen']=len({r['fid'] for r in candidate}&frozen)
checks['methods_all_2024_2026_rows']=len(ledger)
result={'study':'M8_RED_CARD_ADJUSTED_FORM_INDEPENDENT_VERIFICATION','pass':not bool(issues),'issues':dict(issues),'checks':dict(checks),'scope_note':'Historical event-time replay only; red-card publication/receipt time is not proven; no formal orders or ledger writes.'}
(HERE/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pass':result['pass'],'issues':dict(issues),'checks':{k:v for k,v in checks.items() if not k.startswith('aggregate_methods')},'aggregates':aggregates},ensure_ascii=False,indent=2))
