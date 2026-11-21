#!/usr/bin/env python3
"""Independent Crown raw-response and FT/AH settlement verification."""
import collections,datetime as dt,gzip,hashlib,json,math,pathlib,sqlite3,glob
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).resolve().parent
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work');DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
SCHEDULE=WORK/'crown-drop-expanded-62/schedule_universe.jsonl';ORDERS=OUT/'exact_rule_cross_league_orders.jsonl.gz';TZ=dt.timezone(dt.timedelta(hours=8));UTC=dt.timezone.utc
PAGES=pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
DAILY=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m7/m7_future_schedule_refresh_daily_20261111')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def ts(s):
 v=dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return (v.replace(tzinfo=TZ) if v.tzinfo is None else v).astimezone(UTC)
def settle(line,side,hg,ag,odds):
 if abs(float(line)*4-round(float(line)*4))>1e-7:raise ValueError('non-quarter AH line')
 legs=[float(line)] if abs(float(line)*2-round(float(line)*2))<1e-8 else [math.floor(float(line)*2)/2,math.ceil(float(line)*2)/2]
 vals=[]
 for leg in legs:
  margin=hg-ag+leg if side=='home' else ag-hg-leg
  vals.append(float(odds)-1 if margin>1e-9 else -1. if margin<-1e-9 else 0.)
 pnl=sum(vals)/len(vals)
 label='full_win' if all(x>0 for x in vals) else 'half_win' if any(x>0 for x in vals) else 'push' if all(x==0 for x in vals) else 'half_loss' if any(x==0 for x in vals) else 'full_loss'
 return pnl,label
def main():
 fixtures={}
 summary=json.loads((OUT/'exact_rule_cross_league_summary.json').read_text())
 target_leagues={str(x) for x in summary['target_league_ids']}
 for line in open(SCHEDULE):
  r=json.loads(line);fid=str(r['match_id'])
  if r.get('home_goals') is not None and r.get('away_goals') is not None:
   fixtures[fid]={'fid':fid,'league':str(r['league_id']),'home':r.get('home'),'away':r.get('away'),
    'hg':int(r['home_goals']),'ag':int(r['away_goals']),'kickoff':ts(r['kickoff_source_local'])}
 # Include the exact cached TotalCorner schedule pages that supplied the 2,722
 # fixtures absent from the older expanded inventory. This remains an
 # independent FT/identity source from the candidate/order ledger.
 page_files=[]
 patterns=[str(PAGES/'*'/'page-*.raw.json'),str(DAILY/'2026-*'/'raw'/'*.json')]
 for pattern in patterns:
  for name in sorted(glob.glob(pattern)):
   path=pathlib.Path(name)
   league_hint=path.parent.name if 'page-*.raw.json' in pattern else path.name.split('-',1)[0]
   if league_hint not in target_leagues:continue
   page_files.append(name)
   try:doc=json.loads(path.read_text())
   except Exception:continue
   for r in (doc.get('data') or {}).get('matches',[]):
    if r.get('status')!='full' or str(r.get('l_id')) not in target_leagues:continue
    try:
     ko=ts(r['start']);y=ko.astimezone(TZ).year
     if y<2019 or y>2026:continue
     fid=str(r['id']);v={'fid':fid,'league':str(r['l_id']),'home':r.get('h'),'away':r.get('a'),
      'hg':int(r['hg']),'ag':int(r['ag']),'kickoff':ko}
    except Exception:continue
    old=fixtures.get(fid)
    if old and (old['league'],old['home'],old['away'],old['hg'],old['ag'],old['kickoff']) != \
       (v['league'],v['home'],v['away'],v['hg'],v['ag'],v['kickoff']):
     raise ValueError(f'independent schedule identity/FT conflict for {fid}: {old} vs {v}')
    fixtures[fid]=v
 orders=[json.loads(x) for x in gzip.open(ORDERS,'rt',encoding='utf-8')]
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True);cx.row_factory=sqlite3.Row
 checks=[];errs=collections.Counter();labels=collections.Counter();sum_u=0.
 for o in orders:
  fid=o['fid'];r=fixtures.get(fid)
  if not r:errs['missing_independent_FT_source']+=1;continue
  if (r['hg'],r['ag'],r['league'],r['home'],r['away']) != (int(o['hg']),int(o['ag']),str(o['league']),o['home'],o['away']):errs['FT_or_league_mismatch']+=1;continue
  ko=r['kickoff'];t1=ko-dt.timedelta(hours=1)
  rows=cx.execute('''SELECT q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc,c.response_sha256,c.source_file
    FROM asian_quote q JOIN capture c USING(capture_key)
    WHERE q.fixture_id=? AND q.quote_kind='movement' AND c.data_layer='movement' AND c.status='QUOTES_SAVED'
      AND q.quote_source_at_utc<=? ORDER BY q.quote_source_at_utc DESC,q.response_received_at_utc DESC,c.response_sha256 DESC LIMIT 1''',(fid,t1.isoformat().replace('+00:00','Z'))).fetchone()
  if not rows:errs['independent_T1_quote_missing']+=1;continue
  p=pathlib.Path(rows['source_file'])
  if not p.exists():errs['raw_response_missing']+=1;continue
  raw=p.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=rows['response_sha256']:errs['raw_SHA_mismatch']+=1;continue
  try:
   d=json.loads(raw);match=next(x for x in d.get('data',[]) if str(x.get('id'))==fid);book=next(x for x in match.get('bookmakers',[]) if x.get('slug')=='crown')
   candidates=[]
   for q in book.get('asian_list') or []:
    try:
     qt=ts(q[4]);line=float(q[1]);ho=float(q[2]);ao=float(q[3])
     if qt<=t1 and ho>1 and ao>1 and abs(line*4-round(line*4))<1e-7:candidates.append((qt,line,ho,ao))
    except Exception:continue
   if not candidates:errs['raw_has_no_T1_quote']+=1;continue
   quote=max(candidates,key=lambda x:x[0]);side=o['side'];price=quote[2] if side=='home' else quote[3]
   if abs(quote[1]-o['end_line'])>1e-7 or abs(price-o['price'])>1e-7:errs['selected_T1_contract_mismatch']+=1;continue
   pnl,label=settle(quote[1],side,r['hg'],r['ag'],price)
   good=abs(pnl-o['net_u'])<1e-8 and label==o['settlement']
   if not good:errs['payout_mismatch']+=1
   labels[label]+=1;sum_u+=pnl
   checks.append({'fid':fid,'group':o['group'],'line':quote[1],'side':side,'price':price,'ft':f"{r['hg']}-{r['ag']}",'settlement':label,'net_u':round(pnl,10),'raw_sha256':rows['response_sha256'],'raw_file':str(p),'verified':good})
  except Exception:errs['raw_parse_or_identity_error']+=1
 cx.close()
 out={'independently_checked_orders':len(checks),'expected_orders':len(orders),'verified':sum(x['verified'] for x in checks),'errors':dict(errs),'settlement_counts':dict(labels),'net_u_recomputed':round(sum_u,6),'source_schedule_sha256':sha(SCHEDULE),'source_schedule_page_count':len(set(page_files)),'source_schedule_pages_sha256':{str(pathlib.Path(x)):sha(x) for x in sorted(set(page_files))},'source_order_ledger_sha256':sha(ORDERS),'sqlite_sha256':sha(DB)}
 (OUT/'independent_settlement_verification_20261121.json').write_text(json.dumps(out,indent=2))
 with gzip.open(OUT/'independent_settlement_verification_20261121.jsonl.gz','wt',encoding='utf-8') as f:
  for x in checks:f.write(json.dumps(x,ensure_ascii=False)+'\n')
 print(json.dumps({k:out[k] for k in ('independently_checked_orders','expected_orders','verified','errors','settlement_counts','net_u_recomputed','source_schedule_page_count','source_order_ledger_sha256','sqlite_sha256')},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
