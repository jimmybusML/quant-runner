# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Independent raw Crown, as-of-feature, overlap and AH settlement audit."""
from __future__ import annotations
import bisect, collections, csv, datetime as dt, gzip, hashlib, json, math, pathlib, re, unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).resolve().parent
FEATURES=OUT/'referee_market_bias_fixture_features.jsonl.gz'
PRED=OUT/'referee_market_bias_predictions.jsonl.gz'
SUMMARY=OUT/'referee_market_bias_summary.json'
FOUNDATION=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
def parse(x):
 t=dt.datetime.fromisoformat(str(x).replace('Z','+00:00').replace(' ','T'))
 if t.tzinfo is None:t=t.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
 return t.astimezone(dt.timezone.utc)
def norm_ref(s):
 x=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode('ascii').lower()
 x=re.sub(r'\b(fc|cf|sc|afc|ac|club|football|soccer|fk|as)\b',' ',x)
 return re.sub(r'[^a-z0-9]','',x)
def settle(line,side,hg,ag,odds):
 line=float(line);odds=float(odds)
 legs=[line] if abs(line*2-round(line*2))<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 vals=[]
 for leg in legs:
  z=(hg-ag+leg) if side=='home' else (ag-hg-leg)
  vals.append(odds-1 if z>1e-9 else -1.0 if z< -1e-9 else 0.0)
 pnl=round(sum(vals)/len(vals),10)
 if all(x>0 for x in vals):state='full_win'
 elif any(x>0 for x in vals):state='half_win'
 elif all(x==0 for x in vals):state='push'
 elif any(x==0 for x in vals):state='half_loss'
 else:state='full_loss'
 return pnl,state
def read_gz(path):
 with gzip.open(path,'rt',encoding='utf8') as f:return [json.loads(x) for x in f if x.strip()]
def main():
 features=read_gz(FEATURES);pred=read_gz(PRED);summary=json.loads(SUMMARY.read_text())
 ids=[r['fid'] for r in features];errs=collections.Counter()
 if len(ids)!=len(set(ids)):errs['duplicate_feature_fid']+=len(ids)-len(set(ids))
 frozen={str(json.loads(x)['fid']) for x in FOUNDATION.open() if x.strip()}
 rawcache={};feature_by_id={r['fid']:r for r in features}
 for r in features:
  p=pathlib.Path(r['source_file']);b=rawcache.get(str(p))
  if b is None:b=p.read_bytes();rawcache[str(p)]=b
  if hashlib.sha256(b).hexdigest()!=r['response_sha256']:errs['raw_sha_mismatch']+=1;continue
  fx=next((q for q in json.loads(b).get('data',[]) if str(q.get('id'))==r['fid']),None)
  if fx is None:errs['raw_fid_missing']+=1;continue
  if int(fx.get('hg'))!=int(r['FT'][0]) or int(fx.get('ag'))!=int(r['FT'][1]):errs['raw_ft_mismatch']+=1
  if str(fx.get('l_id'))!=r['league_id']:errs['raw_league_mismatch']+=1
  if parse(fx['start']).isoformat()!=r['kickoff_utc']:errs['kickoff_mismatch']+=1
  kick=parse(fx['start']);cut=kick-dt.timedelta(hours=12);crown=next(q for q in fx.get('bookmakers',[]) if q.get('slug')=='crown');qs=[]
  for i,q in enumerate(crown.get('asian_list') or []):
   try:
    when=parse(q[4]);line,ho,ao=map(float,q[1:4])
    if when<kick and when<=cut and ho>1 and ao>1 and abs(line*4-round(line*4))<1e-7:qs.append((when,1,i,line,ho,ao))
   except Exception:pass
  for k in ('open','close'):
   q=(crown.get('asian') or {}).get(k)
   if isinstance(q,dict):
    try:
     when=parse(q['time']);line=float(q['line']);ho=float(q['home']);ao=float(q['away'])
     if when<kick and when<=cut and ho>1 and ao>1 and abs(line*4-round(line*4))<1e-7:qs.append((when,0,-1,line,ho,ao))
    except Exception:pass
  if not qs:errs['T12_quote_missing']+=1;continue
  q=max(qs,key=lambda v:(v[0],v[1],v[2]))
  if abs(q[3]-r['line_home'])>1e-8 or abs(q[4]-r['home_odds'])>1e-8 or abs(q[5]-r['away_odds'])>1e-8:errs['T12_contract_mismatch']+=1
  if abs((q[0]-parse(r['source_event_utc'])).total_seconds())>1:errs['T12_source_event_mismatch']+=1
  hu,hc=settle(q[3],'home',r['FT'][0],r['FT'][1],q[4]);au,ac=settle(q[3],'away',r['FT'][0],r['FT'][1],q[5])
  if abs(hu-r['home_return'])>1e-8 or hc!=r['home_settlement'] or abs(au-r['away_return'])>1e-8 or ac!=r['away_settlement']:errs['feature_settlement_mismatch']+=1
  if bool(r['frozen_eight_overlap'])!=(r['fid'] in frozen):errs['frozen_membership_mismatch']+=1
 # Independently rebuild ref history features using only records strictly earlier than the 3-day embargo.
 sorted_rows=sorted(features,key=lambda x:(x['date'],x['fid']))
 byref=collections.defaultdict(list);bycomp=collections.defaultdict(list)
 for r in sorted_rows:
  day=dt.date.fromisoformat(r['date']).toordinal();cut=day-3;lo=cut-730
  rh=[x for d,x in byref[(r['tm_competition'],norm_ref(r['referee']))] if lo<=d<cut]
  lh=[x for d,x in bycomp[r['tm_competition']] if lo<=d<cut]
  n=len(rh);compmean=sum(x['market_margin_residual'] for x in lh)/len(lh) if lh else 0.0
  refmean=sum(x['market_margin_residual'] for x in rh)/n if n else compmean
  bias=(n/(n+10.0))*(refmean-compmean) if n else 0.0
  if n!=r['ref_n_730']:errs['ref_history_n_mismatch']+=1
  if abs(refmean-r['ref_resid_raw_730'])>1e-8:errs['ref_history_mean_mismatch']+=1
  if abs(bias-r['ref_bias_730'])>1e-8:errs['ref_history_bias_mismatch']+=1
  implied=(1/r['home_odds'])/(1/r['home_odds']+1/r['away_odds'])
  if abs(implied-r['home_normalized_implied'])>1e-8:errs['home_probability_mismatch']+=1
  byref[(r['tm_competition'],norm_ref(r['referee']))].append((day,r));bycomp[r['tm_competition']].append((day,r))
 # Recompute method/annual/overlap payouts solely from the independently settled prediction rows.
 method_rows=collections.defaultdict(list);seen=collections.Counter()
 for r in pred:
  if r['fid'] not in feature_by_id:errs['prediction_without_feature_row']+=1;continue
  src=feature_by_id[r['fid']];seen[(r['method'],r['fid'])]+=1
  if r['selected_side'] not in ('home','away'):errs['invalid_side']+=1;continue
  contract=settle(src['line_home'],r['selected_side'],src['FT'][0],src['FT'][1],src['home_odds'] if r['selected_side']=='home' else src['away_odds'])
  if abs(contract[0]-r['net_u'])>1e-8 or contract[1]!=r['settlement']:errs['prediction_payout_mismatch']+=1
  method_rows[r['method']].append(r)
 if any(n!=1 for n in seen.values()):errs['duplicate_method_fid']+=sum(n-1 for n in seen.values() if n>1)
 if len({r['fid'] for r in pred if r['year'] in (2024,2025,2026)})!=7524:errs['test_unique_fid_count']+=1
 frozen_overlap={r['fid'] for r in pred if r['fid'] in frozen}; outside={r['fid'] for r in pred if r['fid'] not in frozen}
 if len(frozen_overlap)!=1650:errs['test_frozen_overlap_count']+=1
 if len(outside)!=5874:errs['test_outside_unique_count']+=1
 result={}
 for m,rr in method_rows.items():
  for scope,subset in [('outside_frozen_eight',[x for x in rr if not x['frozen_eight_overlap']]),('all_matched_test',rr)]:
   u=round(sum(x['net_u'] for x in subset),6);k=f'{m}|{scope}'
   result[k]={'n':len(subset),'net_U':u,'ROI_pct':round(100*u/len(subset),6) if subset else None}
   expect=summary['models'][m][scope]
   if len(subset)!=expect['n'] or abs(u-expect['net_U'])>1e-6:errs['summary_total_mismatch']+=1
   for year in (2024,2025,2026):
    q=[x for x in subset if x['year']==year];e=(summary['models'][m]['outside_annual' if scope=='outside_frozen_eight' else 'annual'][str(year)])
    yu=round(sum(x['net_u'] for x in q),6)
    if len(q)!=e['n'] or abs(yu-e['net_U'])>1e-6:errs['summary_year_mismatch']+=1
 # Check the published annual, league and ISO-week exports independently against settled rows.
 league_export=list(csv.DictReader((OUT/'referee_market_bias_by_league.csv').open(encoding='utf8')))
 league_export_map={(r['method'],r['league']):r for r in league_export}
 for m in method_rows:
  outside_rows=[r for r in method_rows[m] if not r['frozen_eight_overlap']]
  for league in {r['league'] for r in outside_rows}:
   subset=[r for r in outside_rows if r['league']==league];e=league_export_map.get((m,league))
   if not e or int(e['n'])!=len(subset) or abs(float(e['net_U'])-sum(r['net_u'] for r in subset))>1e-6:errs['league_export_mismatch']+=1
   q=summary['models'][m]['outside_by_league'].get(league,{})
   if q.get('n')!=len(subset) or abs(q.get('net_U',0)-sum(r['net_u'] for r in subset))>1e-6:errs['league_json_mismatch']+=1
 weekly_export=list(csv.DictReader((OUT/'referee_market_bias_by_week.csv').open(encoding='utf8')))
 weekly_map={(r['method'],r['iso_week']):r for r in weekly_export}
 for m,rr in method_rows.items():
  weeks={r['iso_week'] for r in rr}
  for week in weeks:
   q=[r for r in rr if r['iso_week']==week];qi=[r for r in q if not r['frozen_eight_overlap']];e=weekly_map.get((m,week))
   if not e or int(e['n'])!=len(q) or abs(float(e['net_U'])-sum(r['net_u'] for r in q))>1e-6 or int(e['outside_frozen_eight_n'])!=len(qi) or abs(float(e['outside_net_U'])-sum(r['net_u'] for r in qi))>1e-6:errs['weekly_export_mismatch']+=1
 verification={'study':'Independent verifier for referee-history M8 Crown AH research','pass':not errs,'issues':dict(errs),'feature_rows':len(features),'unique_feature_fids':len(set(ids)),'raw_response_hash_ft_identity_T12_and_AH_settlement_checked':len(features),'unique_raw_files':len(rawcache),'prediction_rows':len(pred),'methods':sorted(method_rows),'test_unique_fids':len({r['fid'] for r in pred}),'frozen_eight_overlap_fids':len(frozen_overlap),'outside_frozen_eight_unique_fids':len(outside),'referee_lookback_features_rebuilt_rows':len(features),'method_totals':result,'live_receipt_feature_rows':0}
 (OUT/'referee_market_bias_independent_verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(verification,ensure_ascii=False,indent=2))
 if errs:raise SystemExit(1)
if __name__=='__main__':main()
