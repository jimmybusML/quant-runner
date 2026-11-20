#!/usr/bin/env python3
"""Verify the original E-direction formula against every frozen E member."""
import collections,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from research.m3.probabilities import settle_score
R=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work');OUT=pathlib.Path(__file__).resolve().parent
sign=lambda x:1 if x>1e-9 else -1 if x<-1e-9 else 0
members={}
for line in open(R/'m8_foundation_20261115/historical_membership.jsonl'):
 x=json.loads(line)
 if x['cohort']=='E':members[str(x['fid'])]=x
rows={}
for name in ('m8_late_full_path_water_features_20261114.jsonl','m8_same_line_probability_path_20261114.jsonl','m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl','m8_independent_score_strength_20261114.jsonl'):
 p=R/name
 if not p.exists():continue
 for line in open(p):
  x=json.loads(line);fid=str(x.get('fid',''))
  if fid in members:rows.setdefault(fid,{}).update(x)
ok=0;issues=collections.Counter();details=[]
for fid,m in members.items():
 r=rows.get(fid,{})
 if r.get('score_row'):
  r.setdefault('hg',r['score_row'].get('hg'));r.setdefault('ag',r['score_row'].get('ag'))
 try:
  p0,p3,p1=(float(r[k]) for k in ('p0','p3','p1'))
  a=sign(p3-p0);b=sign(p1-p3);net=sign(p1-p0);s=net or a or b or sign(float(r.get('last_move') or 0))
  if not s:issues['direction_unavailable']+=1;continue
  side='away' if s>0 else 'home';price=float(r['home_price' if side=='home' else 'away_price'])
  state,pnl=settle_score('AH',float(r['end_line']),side,int(r['hg']),int(r['ag']),price)
  if abs(pnl-float(m['pnl']))>1e-8:issues['pnl_mismatch']+=1;details.append({'fid':fid,'computed':pnl,'frozen':m['pnl']})
  else:ok+=1
 except Exception as e:issues['missing_or_invalid_'+type(e).__name__]+=1;details.append({'fid':fid,'error':type(e).__name__})
res={'frozen_E_members':len(members),'feature_rows':len(rows),'matched_frozen_pnl':ok,'issues':dict(issues),'pass':ok==len(members) and not issues,'direction':'s=net(p1-p0) or sign(p3-p0) or sign(p1-p3) or sign(last_move); s>0 selects away, otherwise home','input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'m8_foundation_20261115/historical_membership.jsonl']}}
(OUT/'frozen_e_direction_audit.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n');print(json.dumps(res,ensure_ascii=False,indent=2));
if not res['pass']:raise SystemExit(1)
