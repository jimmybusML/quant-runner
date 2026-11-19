#!/usr/bin/env python3
"""Independent verify of receipt-time Crown AH repricing ledger."""
import collections,datetime as dt,gzip,hashlib,json,math,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'research/m8/cross_competition_team_pricing_20261119'
LEDGER=OUT/'verified_actual_receipt_reprice_ledger_20261119.jsonl.gz'
def utc(v):
 x=dt.datetime.fromisoformat(str(v).replace('Z','+00:00').replace(' ','T'))
 return x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc) if x.tzinfo is None else x.astimezone(dt.timezone.utc)
def settle(line,side,hg,ag,odds):
 line=float(line);odds=float(odds)
 if abs(line*4-round(line*4))>1e-8:raise ValueError('bad quarter AH line')
 legs=[line] if abs(round(line*2)/2-line)<1e-8 else [math.floor(line*2)/2,math.ceil(line*2)/2]
 ret=[]
 for x in legs:
  m=int(hg)-int(ag)+x if side=='home' else int(ag)-int(hg)-x
  ret.append(odds-1 if m>1e-9 else -1. if m < -1e-9 else 0.)
 return sum(ret)/len(ret)
fails=collections.Counter();audited=[];settlements=0;ledger_n=0;snapshot_n=0
for line in gzip.open(LEDGER,'rt',encoding='utf-8'):
 r=json.loads(line);ledger_n+=1
 try:
  attempt=json.loads(pathlib.Path(r['raw_file']).read_bytes());body=attempt['raw_response']
  digest=hashlib.sha256(body.encode()).hexdigest()
  if digest!=r['raw_body_sha256'] or digest!=attempt['raw_sha256']:raise ValueError('body_sha_mismatch')
  snapshot=pathlib.Path(r['raw_file']).parents[1]/'snapshot.json'
  if not snapshot.is_file() or hashlib.sha256(snapshot.read_bytes()).hexdigest()!=r['snapshot_sha256']:raise ValueError('snapshot_sha_mismatch')
  snapshot_n+=1
  if utc(attempt['received_at'])!=utc(r['received_utc']):raise ValueError('HTTP_received_at_mismatch')
  rec=utc(r['received_utc']);ko=utc(r['kickoff_utc']);qt=utc(r['quote_source_utc'])
  if not rec<ko or not qt<=rec:raise ValueError('receipt_quote_time_order')
  doc=json.loads(body);data=doc.get('data',[]);data=data if isinstance(data,list) else [data]
  m=[x for x in data if str(x.get('id'))==str(r['fid'])]
  if len(m)!=1:raise ValueError('raw_fid_cardinality')
  m=m[0]
  if str(m.get('h_id'))!=str(r['home_team_id']) or str(m.get('a_id'))!=str(r['away_team_id']):raise ValueError('team_identity_mismatch')
  crown=[x for x in m.get('bookmakers',[]) if str(x.get('slug','')).lower()=='crown']
  if len(crown)!=1:raise ValueError('Crown_cardinality')
  found=False
  for q in crown[0].get('asian_list') or []:
   try:
    qtime=utc(q[4]);line0,ho,ao=map(float,q[1:4])
    if abs((qtime-qt).total_seconds())<1 and all(abs(a-b)<1e-8 for a,b in ((line0,r['line']),(ho,r['home_odds']),(ao,r['away_odds']))):found=True;break
   except Exception:continue
  if not found:raise ValueError('quote_not_found_in_raw_body')
  if str(m.get('status','')).lower()=='full' and (int(m.get('hg',-99)),int(m.get('ag',-99)))==(int(r['FT_home']),int(r['FT_away'])):raise ValueError('receipt_body_contains_target_FT')
  for name,p in r['methods'].items():
   side=p['selected_side'];odds=r['home_odds'] if side=='home' else r['away_odds']
   val=settle(r['line'],side,r['FT_home'],r['FT_away'],odds)
   if abs(val-float(p['pnl']))>1e-7:raise ValueError('settlement_mismatch:'+name)
   settlements+=1
  audited.append({'fid':r['fid'],'received_utc':r['received_utc'],'quote_source_utc':r['quote_source_utc'],'kickoff_utc':r['kickoff_utc'],'snapshot_horizon':r.get('snapshot_horizon'),'raw_body_sha256':digest,'verified_methods':len(r['methods']),'receipt_pre_kickoff':True,'quote_pre_or_at_receipt':True})
 except Exception as e:fails[str(e)]+=1
summary={'study':'M8_CROSS_COMPETITION_ACTUAL_RECEIPT_RAW_CROWN_INDEPENDENT_AUDIT_20261119','receipt_ledger_unique_fids':ledger_n,'audited_unique_fids':len(audited),'raw_body_sha_verified':len(audited),'snapshot_sha_verified':snapshot_n,'settlement_comparisons':settlements,'failures':dict(fails),'all_verified_settlements_match':settlements==len(audited)*5,'method':'Re-read raw HTTP attempt files; verify raw body SHA and T-horizon snapshot SHA, attempt received_at, receipt < kickoff, Crown quote event <= receipt and exact AH line/two prices in raw asian_list; confirm target FT is absent from receipt body; independently settle every selected side including quarter AH split legs against trusted FT.'}
(OUT/'INDEPENDENT_ACTUAL_RECEIPT_AUDIT_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with gzip.open(OUT/'independent_actual_receipt_audit_20261119.jsonl.gz','wt',encoding='utf-8') as f:
 for x in audited:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
