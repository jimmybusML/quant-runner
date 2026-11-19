#!/usr/bin/env python3
"""Bridge new A/B ledgers to the separately re-read raw Crown AH audit."""
import collections,datetime as dt,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
D=ROOT/'research/m8/next_round_20261120'
RAW=ROOT/'research/m8/cross_competition_team_pricing_20261119/independent_raw_crown_audit_20261119.jsonl.gz'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def settle(line,side,odds,hg,ag):
 z=float(line)*(1 if side=='home' else -1);g=(int(hg)-int(ag))*(1 if side=='home' else -1)
 legs=[z] if abs(z*2-round(z*2))<1e-9 else [math.floor(z*2)/2,math.ceil(z*2)/2]
 return sum(float(odds)-1 if g+x>1e-9 else -1. if g+x< -1e-9 else 0. for x in legs)/len(legs)
raw={}
with gzip.open(RAW,'rt') as f:
 for ln in f:
  x=json.loads(ln);raw[str(x['fid'])]=x
checks=[];fails=collections.Counter();modelfids=collections.defaultdict(set)
def check(name,x,fid,year,date,line,ho,ao,hg,ag,side,pnl):
 q=raw.get(str(fid))
 if not q:fails[name+':raw_fid_missing']+=1;return
 if int(q['year'])!=int(year):fails[name+':year_mismatch']+=1
 if q['kickoff_china'][:10]!=str(date)[:10]:fails[name+':beijing_date_mismatch']+=1
 for a,b,n in ((q['AH_home_line'],line,'line'),(q['AH_home_odds'],ho,'home_odds'),(q['AH_away_odds'],ao,'away_odds'),(q['FT_home'],hg,'FT_home'),(q['FT_away'],ag,'FT_away')):
  if abs(float(a)-float(b))>1e-8:fails[name+':'+n+'_mismatch']+=1
 odds=ho if side=='home' else ao;actual=settle(line,side,odds,hg,ag)
 if abs(actual-float(pnl))>1e-8:fails[name+':settlement_mismatch']+=1
 elif name.startswith('A:') or name.startswith('B:'):pass
 checks.append((name,fid,actual))
# A: prequential Crown-surprise strength shock and research-only positive EV subset.
with gzip.open(D/'strength_shock_per_fixture_20261120.jsonl.gz','rt') as f:
 for ln in f:
  x=json.loads(ln);m=x['model'];name='A:'+m;fid=str(x['fid']);modelfids[name].add(fid)
  check(name,x,fid,x['year_beijing'],x['kickoff_beijing'],x['Crown_home_AH_line'],x['Crown_home_odds'],x['Crown_away_odds'],x['FT_home'],x['FT_away'],x['direction'],x['net_u'])
# B: nonlinear Crown-contract strength distribution, three same-FID models.
with gzip.open(D/'per_fixture_walkforward_20261120.jsonl.gz','rt') as f:
 for ln in f:
  x=json.loads(ln);m=x['model'];name='B:'+m;fid=str(x['fid']);modelfids[name].add(fid)
  check(name,x,fid,x['year'],x['date'],x['crown_ah_line_home'],x['crown_home_odds'],x['crown_away_odds'],x['FT_home'],x['FT_away'],x['direction'],x['net_u'])
ref=set(raw)
checks_summary={'study':'M8 breakthrough A/B ledgers raw Crown source bridge','raw_audit_source':str(RAW.relative_to(ROOT)),'raw_audit_sha256':sha(RAW),'raw_audit_unique_fids':len(ref),'verified_quote_ft_and_ah_settlements':len(checks),'model_rows':{k:len(v) for k,v in modelfids.items()},'model_unique_fids':{k:len(set(fid for n,fid,p in checks if n==k)) for k in modelfids},'all_method_fids_match_raw_audit':all(v<=ref for v in modelfids.values()),'failures':dict(fails),'all_checks_pass':not fails,'scope_note':'Raw Crown bodies were independently re-read in the immediately preceding verifier run; this bridge proves every A/B selection used the identical audited FID, China kickoff date, quote, FT and Crown AH contract. Event time is not HTTP receipt time.'}
(D/'raw_quote_bridge_audit_20261120.json').write_text(json.dumps(checks_summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks_summary,ensure_ascii=False,indent=2))
