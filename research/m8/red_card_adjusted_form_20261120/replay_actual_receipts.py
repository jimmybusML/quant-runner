#!/usr/bin/env python3
"""Reprice the fixed 2026 red-card/form model at actual Crown HTTP T1 receipts.

This is a receipt-price diagnostic only: historical card features do not have
verified contemporaneous snapshots, and the outcomes were already observed.
"""
import collections,datetime as dt,gzip,hashlib,json,math,pathlib
from zoneinfo import ZoneInfo
HERE=pathlib.Path(__file__).resolve().parent
RECEIPTS=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')
LEDGER=HERE/'red_card_adjusted_form_per_fixture.jsonl.gz'; SUMMARY=HERE/'red_card_adjusted_form_summary.json'
TZ=ZoneInfo('Asia/Shanghai');UTC=dt.timezone.utc
METHODS=('market','market_plus_raw_form','market_plus_red_adjusted_form','market_plus_raw_and_red_context','low_price')
def ts(x):
 d=dt.datetime.fromisoformat(str(x).replace('Z','+00:00'))
 return d.astimezone(UTC) if d.tzinfo else d.replace(tzinfo=TZ).astimezone(UTC)
def settle(line,side,gd,odds):
 h=float(line) if side=='home' else -float(line);m=int(gd) if side=='home' else -int(gd)
 if abs(h*4-round(h*4))>1e-8:raise ValueError(f'bad AH line {line}')
 legs=[h] if int(round(h*4))%2==0 else [math.floor(h*2)/2,math.ceil(h*2)/2]
 vals=[]
 for leg in legs:
  z=m+leg;vals.append((float(odds)-1) if z>1e-9 else (-1. if z<-1e-9 else 0.))
 state=('full_win' if all(x>0 for x in vals) else 'full_loss' if all(x<0 for x in vals) else 'push' if all(x==0 for x in vals) else 'half_win' if any(x>0 for x in vals) else 'half_loss')
 return state,sum(vals)/len(vals)
def vector(r,method,beta,line,ho,ao):
 hr,ar=r['raw_form']['home'],r['raw_form']['away'];hc,ac=r['card_form']['home'],r['card_form']['away']
 rh,ra=float(hr['gd_avg']),float(ar['gd_avg'])
 dh=-beta*float(hc['red_adv_avg']) if hc['red_adv_avg'] is not None else 0.
 da=-beta*float(ac['red_adv_avg']) if ac['red_adv_avg'] is not None else 0.
 nh,na=int(hc['n']),int(ac['n']);gap=float(hc['red_adv_avg'] or 0.)-float(ac['red_adv_avg'] or 0.)
 base=[-float(line)+.25*math.log(float(ao)/float(ho)),float(line),.25*math.log(float(ao)/float(ho))]
 raw=[rh,ra,rh-ra,rh+ra,hr['last_gd'],ar['last_gd'],math.log1p(hr['n']),math.log1p(ar['n'])]
 adjusted=[rh+dh,ra+da,(rh+dh)-(ra+da),(rh+dh)+(ra+da),dh,da]
 ctx=[gap,math.log1p(nh),math.log1p(na),int(nh==0),int(na==0),nh/max(hr['n'],1),na/max(ar['n'],1)]
 return base if method=='market' else base+raw if method=='market_plus_raw_form' else base+adjusted+ctx if method=='market_plus_red_adjusted_form' else base+raw+adjusted+ctx

def main():
 ledger={r['fid']:r for r in (json.loads(x) for x in gzip.open(LEDGER,'rt',encoding='utf-8'))}
 summary=json.loads(SUMMARY.read_text());fold=summary['folds']['2026'];beta=float(fold['beta_red_adv_to_goal_diff'])
 t1=[];archive_rows=0;hash_bad=identity_bad=not_pregame_bad=kickoff_metadata_diff=market_bad=0;candidate_any=set();candidate_t1=set();exact_path=set();rows_by_fid={}
 for line in RECEIPTS.open(encoding='utf-8'):
  x=json.loads(line);archive_rows+=1
  fid=str(x.get('fixture_id') or '')
  if fid not in ledger or ledger[fid]['frozen_eight_overlap'] or 'AH' not in (x.get('markets') or {}):continue
  candidate_any.add(fid)
  if x.get('snapshot_horizon')!='T1':continue
  q=x['markets']['AH'];row=ledger[fid]
  d=json.loads(pathlib.Path(x['source_file']).read_bytes());raw=str(d.get('raw_response') or '')
  rawsha=hashlib.sha256(raw.encode()).hexdigest()
  if rawsha!=x.get('raw_sha256') or d.get('raw_sha256')!=x.get('raw_sha256'):hash_bad+=1;continue
  body=json.loads(raw);items=body.get('data') or []
  if not items or str(items[0].get('id'))!=fid or str(items[0].get('l_id'))!=row['league'] or str(items[0].get('h_id'))!=row['home_id'] or str(items[0].get('a_id'))!=row['away_id']:
   identity_bad+=1;continue
  if d.get('received_at')!=x.get('received_utc') or ts(x['received_utc'])>=ts(row['kickoff_utc']):
   not_pregame_bad+=1
   print('RECEIPT_NOT_PREKICKOFF',fid,'receipt_kickoff',x.get('kickoff_utc'),'target_kickoff',row.get('kickoff_utc'),'received',x.get('received_utc'),'raw_received',d.get('received_at'))
   continue
  crown=next((b for b in items[0].get('bookmakers',[]) if b.get('slug')=='crown'),None)
  close=(crown or {}).get('asian',{}).get('close') or {}
  source=ts(q['source_event_utc'])
  if (close.get('line') is None or abs(float(close['line'])-float(q['line']))>1e-8 or abs(float(close['home'])-float(q['odds']['home']))>1e-8 or abs(float(close['away'])-float(q['odds']['away']))>1e-8 or source!=ts(close.get('time'))):market_bad+=1;continue
  candidate_t1.add(fid);rows_by_fid[fid]=(row,x,q)
  if ts(x['kickoff_utc'])!=ts(row['kickoff_utc']):kickoff_metadata_diff+=1
  if abs(float(q['line'])-row['line'])<1e-8 and abs(float(q['odds']['home'])-row['home_odds'])<1e-8 and abs(float(q['odds']['away'])-row['away_odds'])<1e-8:exact_path.add(fid)
 if hash_bad or identity_bad or not_pregame_bad or market_bad:raise SystemExit(f'receipt evidence mismatch: {hash_bad=} {identity_bad=} {not_pregame_bad=} {market_bad=}')
 orders=[];changes=collections.Counter()
 for fid,(r,x,q) in sorted(rows_by_fid.items(),key=lambda kv:(kv[1][0]['kickoff_beijing'],kv[0])):
  line=float(q['line']);ho=float(q['odds']['home']);ao=float(q['odds']['away']); gd=int(r['gd'])
  for m in METHODS:
   if m=='low_price':predside='home' if ho<=ao else 'away'
   else:
    fit=fold['models'][m];z=vector(r,m,beta,line,ho,ao);mu=fit['mean'];sd=fit['scale'];coef=fit['coef_intercept_first']
    pred=float(coef[0]+sum((z[i]-mu[i])/sd[i]*coef[i+1] for i in range(len(z))))
    predside='home' if pred>0 else 'away'
   state,pnl=settle(line,predside,gd,ho if predside=='home' else ao)
   oldside=r['methods'][m]['side'];changes[m]+=int(oldside!=predside)
   orders.append({'fid':fid,'method':m,'league_id':r['league'],'league':r['league_name'],'kickoff_beijing':r['kickoff_beijing'],'snapshot_horizon':'T1','actual_received_utc':x['received_utc'],'received_minutes_to_kickoff':x['received_minutes_to_kickoff'],'source_event_utc':q['source_event_utc'],'raw_sha256':x['raw_sha256'],'snapshot_sha256':x['snapshot_sha256'],'source_snapshot_file':x['source_file'],'AH_line':line,'AH_home_odds':ho,'AH_away_odds':ao,'history_path_price_exact':fid in exact_path,'historical_path_side':oldside,'receipt_repriced_side':predside,'side_changed_at_actual_price':oldside!=predside,'FT_home':r['hg'],'FT_away':r['ag'],'settlement':state,'net_u':round(pnl,10),'red_feature_snapshot_verified':False})
 stats={}
 for m in METHODS:
  rs=[r for r in orders if r['method']==m];u=sum(r['net_u'] for r in rs);daily=collections.defaultdict(float);wk=collections.defaultdict(lambda:[0,0.]);month=collections.defaultdict(lambda:[0,0.]);league=collections.defaultdict(lambda:[0,0.])
  for r in rs:
   day=r['kickoff_beijing'][:10];daily[day]+=r['net_u'];w=dt.date.fromisoformat(day).isocalendar();wk[f'{w.year}-W{w.week:02d}'][0]+=1;wk[f'{w.year}-W{w.week:02d}'][1]+=r['net_u'];month[day[:7]][0]+=1;month[day[:7]][1]+=r['net_u'];league[r['league']][0]+=1;league[r['league']][1]+=r['net_u']
  cum=peak=mdd=0.
  for _,v in sorted(daily.items()):cum+=v;peak=max(peak,cum);mdd=max(mdd,peak-cum)
  stats[m]={'orders':len(rs),'net_u':round(u,6),'roi_pct':round(100*u/len(rs),6) if rs else None,'mdd_u':round(mdd,6),'active_weeks':len(wk),'active_week_avg':round(len(rs)/len(wk),6) if wk else 0,'side_changes_vs_event_path':changes[m],'settlements':dict(collections.Counter(r['settlement'] for r in rs)),'monthly':{k:{'n':v[0],'net_u':round(v[1],6)} for k,v in sorted(month.items())},'weekly':{k:{'n':v[0],'net_u':round(v[1],6)} for k,v in sorted(wk.items())},'league':{k:{'n':v[0],'net_u':round(v[1],6)} for k,v in sorted(league.items())}}
 result={'study':'M8_RED_CARD_FORM_ACTUAL_CROWN_T1_RECEIPT_PRICE_REPLAY','receipt_archive_rows':archive_rows,'candidate_fids_with_any_actual_pregame_Crown_receipt':len(candidate_any),'candidate_T1_receipt_fids':len(candidate_t1),'candidate_T1_receipt_exact_match_to_event_path_price_fids':len(exact_path),'candidate_T1_receipt_price_mismatch_fids':len(candidate_t1-exact_path),'verified_raw_http_receipt_rows':len(candidate_t1),'raw_sha_identity_timing_market_issues':{'raw_sha':hash_bad,'identity':identity_bad,'not_pregame':not_pregame_bad,'Crown_market':market_bad},'receipt_vs_current_schedule_kickoff_metadata_differences':kickoff_metadata_diff,'date_range':{'start':min(r['kickoff_beijing'] for r in orders)[:10] if orders else None,'end':max(r['kickoff_beijing'] for r in orders)[:10] if orders else None},'metrics_by_method':stats,'scope_note':'Actual Crown T1 HTTP prices and receipt times were verified. Red-card and score-history features have no contemporaneous receipt snapshots; the FT outcomes were already known when this analysis was designed. This is not a valid prospective strategy test, nor a formal Telegram/ledger result.'}
 (HERE/'actual_receipt_reprice_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 with gzip.open(HERE/'actual_receipt_reprice_orders.jsonl.gz','wt',encoding='utf-8') as f:
  for r in orders:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('metrics_by_method',)},ensure_ascii=False,indent=2))
 for m,v in stats.items():print(m,v['orders'],v['net_u'],v['roi_pct'],v['mdd_u'],v['active_week_avg'],v['side_changes_vs_event_path'])
if __name__=='__main__':main()
