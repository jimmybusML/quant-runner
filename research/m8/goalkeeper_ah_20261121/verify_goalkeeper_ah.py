#!/usr/bin/env python3
"""Independent Crown raw quote, FT, quarter-line and frozen-FID audit."""
import collections,datetime as dt,gzip,hashlib,json,math,pathlib,sqlite3
OUT=pathlib.Path(__file__).resolve().parent
DB=pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
FOUNDATION=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')
SCORES=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl')
FEATURES=pathlib.Path(__file__).resolve().parents[1]/'player_load_rotation_20261119/m8_player_load_rotation_feature_rows_20261119.jsonl.gz'
UTC=dt.timezone.utc
def sha_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def iso(s):return dt.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
def read_gz(path):return [json.loads(s) for s in gzip.open(path,'rt',encoding='utf8') if s.strip()]
def quarter_settle(line,side,hg,ag,price):
 line=float(line);price=float(price)
 if abs(line*4-round(line*4))>1e-8 or price<=1:raise ValueError('invalid AH contract')
 signed=line if side=='home' else -line
 diff=int(hg)-int(ag) if side=='home' else int(ag)-int(hg)
 if abs(signed*2-round(signed*2))<=1e-8:legs=[signed]
 else:legs=[math.floor(signed*2)/2,math.ceil(signed*2)/2]
 cash=[price-1 if diff+x>1e-9 else -1. if diff+x< -1e-9 else 0. for x in legs]
 pnl=sum(cash)/len(cash)
 state=('full_win' if all(x>0 for x in cash) else 'half_win' if any(x>0 for x in cash) else
        'push' if all(x==0 for x in cash) else 'half_loss' if any(x==0 for x in cash) else 'full_loss')
 return state,pnl
def body_fixture(body,fid):
 matches=body.get('data',[])
 if isinstance(matches,dict):matches=matches.get('matches',[])
 return next((x for x in matches if str(x.get('id'))==str(fid)),None)
def body_quotes(fixture):
 crown=next((b for b in fixture.get('bookmakers',[]) if b.get('slug')=='crown'),None)
 if not crown:return []
 out=[]
 for item in crown.get('asian_list') or []:
  try:
   t=iso(item[4]).astimezone(UTC);line,ho,ao=map(float,item[1:4])
   if ho>1 and ao>1 and abs(line*4-round(line*4))<=1e-8:out.append((t,line,ho,ao))
  except Exception:continue
 return sorted(out)
def payout_stats(rows):
 n=len(rows);u=sum(float(x['net_u']) for x in rows)
 daily=collections.defaultdict(float)
 for x in rows:daily[str(x['date'])]+=float(x['net_u'])
 total=peak=mdd=0.0
 for day in sorted(daily):
  total+=daily[day];peak=max(peak,total);mdd=max(mdd,peak-total)
 return {'n':n,'net_U':round(u,6),'ROI_pct':round(100*u/n,6) if n else None,'MDD_U':round(mdd,6),
         'settlement_classes':dict(collections.Counter(x['settlement'] for x in rows))}
def main():
 frozen={str(json.loads(s)['fid']) for s in open(FOUNDATION,encoding='utf8') if s.strip()}
 scores={str(x['fid']):x for x in (json.loads(s) for s in open(SCORES,encoding='utf8') if s.strip())}
 base={str(x['fid']):x for x in read_gz(FEATURES) if int(x['year'])>=2024}
 ledgers={}
 for p in sorted(OUT.glob('goalkeeper_ah_*_ledger_20261121.jsonl.gz')):
  method=p.name.replace('goalkeeper_ah_','').replace('_ledger_20261121.jsonl.gz','')
  ledgers[method]=read_gz(p)
 issues=collections.Counter();checks=collections.Counter();quote_audit=[];raw_cache={};quote_cache={};target_seen=collections.defaultdict(set)
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True);cx.row_factory=sqlite3.Row
 sql="""SELECT q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc,
               c.kickoff_at_utc,c.capture_mode,c.response_sha256,c.source_file,c.response_received_at_utc,
               c.prospective_observation
        FROM asian_quote q JOIN capture c USING(capture_key)
        WHERE q.fixture_id=? AND q.quote_kind='movement' AND q.quote_source_at_utc IS NOT NULL"""
 live_sql="select distinct fixture_id from capture where capture_mode='live' and fixture_id=?"
 for method,rows in ledgers.items():
  seen=set()
  for r in rows:
   fid=str(r['fid']);checks['ledger_rows']+=1
   if fid in seen:issues['duplicate_fid_within_method']+=1
   seen.add(fid);target_seen[method].add(fid)
   if fid not in base:issues['fid_missing_feature_source']+=1;continue
   if fid in frozen and not r['frozen_overlap_posthoc']:issues['frozen_flag_mismatch']+=1
   if fid not in frozen and r['frozen_overlap_posthoc']:issues['outside_frozen_flag_mismatch']+=1
   if int(r['training_year_cutoff_exclusive'])!=int(r['year']):issues['fold_cutoff_mismatch']+=1
   src=base[fid]
   if (int(src['FT_home']),int(src['FT_away']))!=(int(r['FT_home']),int(r['FT_away'])):issues['FT_source_row_mismatch']+=1
   for side in ('home','away'):
    st,pnl=quarter_settle(r['line_home'],side,r['FT_home'],r['FT_away'],r['home_odds'] if side=='home' else r['away_odds'])
    if abs(pnl-float(r[side+'_U']))>1e-8:issues['source_side_pnl_mismatch']+=1
   side=r['chosen_side'];price=r['home_odds'] if side=='home' else r['away_odds']
   st,pnl=quarter_settle(r['line_home'],side,r['FT_home'],r['FT_away'],price)
   if abs(pnl-float(r['net_u']))>1e-8:issues['candidate_net_u_mismatch']+=1
   checks['independent_ah_settlements']+=1
   if method=='market_only':
    score=scores.get(fid)
    if score:
     if (int(score['hg']),int(score['ag']))!=(int(r['FT_home']),int(r['FT_away'])):issues['independent_score_ft_mismatch']+=1
     else:checks['score_source_ft_match']+=1
    else:checks['score_source_ft_missing']+=1
    if cx.execute(live_sql,(fid,)).fetchone():checks['live_capture_fids']+=1
   if fid not in quote_cache:
    rowsq=[];kickoff=None
    for q0 in cx.execute(sql,(fid,)):
     try:
      ko0=iso(q0['kickoff_at_utc']).astimezone(UTC);event=iso(q0['quote_source_at_utc']).astimezone(UTC)
      if q0['capture_mode']!='historical' or event>ko0-dt.timedelta(hours=12):continue
      if float(q0['home_decimal'])<=1 or float(q0['away_decimal'])<=1:continue
      rowsq.append((event,q0));kickoff=ko0
     except Exception:continue
    quote_cache[fid]=(max(rowsq,key=lambda x:x[0]) if rowsq else None,kickoff)
   picked,kickoff=quote_cache[fid]
   if not picked:
    if method=='market_only':checks['no_Crown_T12_event_in_sqlite']+=1
    continue
   event,q=picked;expected=(float(r['line_home']),float(r['home_odds']),float(r['away_odds']))
   actual=(float(q['handicap_home']),float(q['home_decimal']),float(q['away_decimal']))
   if any(abs(a-b)>1e-8 for a,b in zip(actual,expected)):
    if method=='market_only':issues['Crown_T12_line_or_price_mismatch']+=1
    continue
   if method=='market_only':checks['Crown_T12_line_and_both_prices_match']+=1
   if method!='market_only':continue
   key=(str(q['response_sha256']),str(q['source_file']))
   if key not in raw_cache:
    try:
     raw=pathlib.Path(q['source_file']).read_bytes();digest=hashlib.sha256(raw).hexdigest()
     raw_cache[key]={'digest':digest,'body':json.loads(raw)}
    except Exception:raw_cache[key]={'digest':None,'body':None}
   raw=raw_cache[key]
   if raw['digest']!=q['response_sha256']:
    issues['raw_response_sha_mismatch_or_missing']+=1;continue
   fx=body_fixture(raw['body'],fid)
   if fx is None:issues['raw_response_fixture_missing']+=1;continue
   checks['raw_response_sha_and_fid_match']+=1
   try:
    if (int(fx['hg']),int(fx['ag']))!=(int(r['FT_home']),int(r['FT_away'])):issues['raw_fixture_ft_mismatch']+=1
    else:checks['raw_fixture_ft_match']+=1
    rawqs=body_quotes(fx);up=[x for x in rawqs if x[0]<=kickoff-dt.timedelta(hours=12)]
    if not up:issues['no_raw_T12_quote']+=1;continue
    rq=max(up,key=lambda x:x[0]);
    if any(abs(x-y)>1e-8 for x,y in zip(rq[1:],expected)):issues['raw_Crown_T12_mismatch']+=1;continue
    checks['raw_Crown_T12_match']+=1
    quote_audit.append({'fid':fid,'T12_source_event_utc':rq[0].isoformat(),'response_sha256':q['response_sha256'],
                        'response_received_at_utc':q['response_received_at_utc'],'capture_mode':q['capture_mode'],
                        'prospective_observation':bool(q['prospective_observation']),'line':rq[1],'home_odds':rq[2],'away_odds':rq[3]})
   except Exception:issues['raw_response_parse_or_identity_error']+=1
 # Dedup/summary consistency and same FID set across models.
 model_sets={m:{str(r['fid']) for r in v} for m,v in ledgers.items()}
 for a,sa in model_sets.items():
  for b,sb in model_sets.items():
   if sa!=sb:issues['method_candidate_fid_set_difference']+=1
   checks[f'overlap_{a}__{b}']=len(sa&sb)
 cx.close()
 audit={'study':'M8_GOALKEEPER_CONTINUITY_AND_DEFENSIVE_HISTORY_AH_INDEPENDENT_AUDIT',
        'ledger_rows':sum(len(x) for x in ledgers.values()),'methods':{m:len(v) for m,v in ledgers.items()},
        'unique_test_fids':len(base),'unique_frozen_overlap_fids':sum(fid in frozen for fid in base),
        'outside_frozen_unique_fids':sum(fid not in frozen for fid in base),
        'checks':dict(checks),'issues':dict(issues),'pass':not issues,
        'independent_settlement':'reimplemented AH payout by splitting quarter-line contracts into adjacent half-goal legs and averaging stake returns',
        'inputs_sha256':{str(p):sha_file(p) for p in (DB,FEATURES,FOUNDATION,SCORES)}}
 (OUT/'goalkeeper_ah_independent_audit_20261121.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
 with gzip.open(OUT/'goalkeeper_ah_raw_quote_link_audit_20261121.jsonl.gz','wt',encoding='utf8') as f:
  for row in sorted(quote_audit,key=lambda x:x['fid']):f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
 raw_fids={x['fid'] for x in quote_audit}
 verified={}
 for method,rows in ledgers.items():
  subset=[x for x in rows if str(x['fid']) in raw_fids and not x['frozen_overlap_posthoc']]
  verified[method]={'raw_Crown_and_FT_verified_incremental':payout_stats(subset),
                    'by_year':{str(y):payout_stats([x for x in subset if int(x['year'])==y]) for y in (2024,2025,2026)},
                    'weekly':{}}
  week_rows=collections.defaultdict(list)
  for x in subset:week_rows[str(x['iso_week'])].append(x)
  verified[method]['weekly']={w:payout_stats(v) for w,v in sorted(week_rows.items())}
 raw_subset={'raw_verified_total_fids':len(raw_fids),
             'raw_verified_frozen_overlap_fids':sum(fid in frozen for fid in raw_fids),
             'raw_verified_outside_frozen_unique_fids':len(raw_fids-set(frozen)),
             'models':verified,
             'interpretation':'Only historical-mode Crown source-event quotes whose event time is at least T-12h and whose stored line/prices match the independent raw HTTP response are included. All underlying captures are historical retrievals, not live pregame receipts.'}
 (OUT/'goalkeeper_ah_raw_verified_subset_20261121.json').write_text(json.dumps(raw_subset,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(audit,ensure_ascii=False,indent=2))
 if issues:raise SystemExit(1)
if __name__=='__main__':main()
