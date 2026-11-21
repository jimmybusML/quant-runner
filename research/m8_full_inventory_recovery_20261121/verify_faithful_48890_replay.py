"""Independent FID, Crown raw SHA, original event quote, correct away line,
date ordering and 5-state cashflow verification for full-path expanded 15 hits.
The original 49 freeze is verified against historic authoritative membership.
No production writes.
"""
from pathlib import Path
import gzip,json,math,collections,hashlib,datetime
P=Path(__file__).resolve().parent
def dt(s):
 x=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return x.astimezone(datetime.timezone.utc) if x.tzinfo else x.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8))).astimezone(datetime.timezone.utc)
def settle_independent(line,side,hg,ag,home_odd,away_odd):
 l=float(line)*(1 if side=='home' else -1)
 gd=int(hg)-int(ag)
 if side=='away':gd=-gd
 odds=float(home_odd if side=='home' else away_odd)
 legs=[l] if int(round(l*4))%2==0 else [math.floor(l*2)/2,math.ceil(l*2)/2]
 returns=[]
 for z in legs:
  t=gd+z
  returns.append(odds-1 if t>1e-9 else -1 if t < -1e-9 else 0)
 return sum(returns)/len(returns)
rows=[json.loads(s) for s in gzip.open(P/'faithful_frozen_full_path_48890_ledger.jsonl.gz','rt')]
new=[r for r in rows if r['source']=='expanded15']
old=[r for r in rows if r['source']=='original49']
assert len(new)==1271 and len(old)==9482
source={}
ep=P/'source69/research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
if not ep.exists():ep=Path('/Users/mac/QuantAsiaDesk/research-work/recovered_factors_20261121/source69/research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz')
for s in gzip.open(ep,'rt'):
 r=json.loads(s);source[r['fid']]=r
frozen={r['fid']:r for s in open(Path('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl')) if (r:=json.loads(s))}
assert len(frozen)==10294
fail=collections.Counter()
assert len({r['fid'] for r in rows})==len(rows)
for r in new:
 fid=r['fid']
 if fid in frozen:fail['frozen_overlap']+=1
 s=source.get(fid)
 if s is None:fail['missing_source']+=1;continue
 fp=Path(s['source_files'][0])
 try:
  buf=fp.read_bytes()
  if hashlib.sha256(buf).hexdigest()!=r['raw_sha256']:fail['sha_mismatch']+=1;continue
  f=next(x for x in json.loads(buf)['data'] if str(x['id'])==fid)
  if str(f['l_id'])!=r['league']:fail['league_mismatch']+=1
  if (str(f['h']),str(f['a']))!=(s['home'],s['away']):fail['team_mismatch']+=1
  hg,ag=int(f['hg']),int(f['ag'])
  if (hg,ag)!=(s['hg'],s['ag']):fail['ft_mismatch']+=1
  ko=dt(f['start'])
  if ko!=dt(s['kickoff_utc']):fail['ko_mismatch']+=1
  bookmaker=next(b for b in f['bookmakers'] if b['slug']=='crown')
  quotes=[]
  for item in bookmaker['asian_list']:
   try:
    t=dt(item[4]);l,ho,ao=map(float,item[1:4])
    if t<ko and ho>1 and ao>1 and all(math.isfinite(z) for z in (l,ho,ao)) and abs(l*4-round(l*4))<1e-9:
     quotes.append((t,l,ho,ao))
   except Exception:pass
  quotes.sort()
  target=ko-datetime.timedelta(hours=1)
  latest=max((q for q in quotes if q[0]<=target),default=None)
  if latest is None:fail['missing_T1']+=1;continue
  if latest[0].isoformat()!=r['T1_utc'] or (latest[1],latest[2],latest[3])!=(r['T1_home_line'],r['T1_home_odds'],r['T1_away_odds']):
   fail['T1_quote_mismatch']+=1;continue
  if not (dt(r['T6_utc'])<=dt(r['T3_utc'])<=dt(r['T1_utc'])<ko):fail['cutoff_order']+=1
  if s['capture_modes'][0]!='historical':fail['incorrect_historical_type']+=1
  pnl=settle_independent(latest[1],r['side'],hg,ag,latest[2],latest[3])
  if abs(pnl-r['net_u_T1'])>1e-9:fail['pnl_mismatch']+=1
 except Exception as e:
  fail['exception_'+type(e).__name__]+=1
for r in old:
 mem=frozen.get(r['fid'])
 if mem is None:fail['extra_original49_not_frozen']+=1
 else:
  if r['group']!=mem['cohort']:fail['old_group_mismatch']+=1
  if abs(r['net_u_T1']-mem['pnl'])>1e-9:fail['old_cash_mismatch']+=1
actual={
 'study':'full M8 eight-group full quote path 48,890 priced historical fixtures',
 'input_prices_n':48890,
 'verified_original49_frozen_n':len(old),
 'verified_expanded15_new_n':len(new),
 'extra15_raw_quote_SHA_FT_independent_rechecks':len(new),
 'outstanding_original49_frozen_without_T6_or_G_score':len(frozen)-len(old),
 'issues':dict(fail),'pass':not fail,
 'note':'Independent contract and settlement check; G rates use existing source-as-of training provenance, not retrospectively re-trained here. Raw quote is historical, not actual pregame receipt.'}
(P/'faithful_frozen_full_path_48890_independent_verification.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2))
print(json.dumps(actual,ensure_ascii=False,indent=2))
if fail:raise SystemExit(1)
