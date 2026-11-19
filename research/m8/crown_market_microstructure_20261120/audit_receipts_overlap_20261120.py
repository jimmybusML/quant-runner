#!/usr/bin/env python3
"""Audit verified HTTP receipt overlap with microstructure event/FT inventory."""
import collections,datetime as dt,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'research/m8/crown_market_microstructure_20261120'
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
RECEIPTS=ROOT/'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl'
FEATURES=WORK/'m8_late_full_path_water_features_20261114.jsonl'
SCORES=WORK/'m8_independent_score_strength_20261114.jsonl'
TZ=dt.timezone(dt.timedelta(hours=8))
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 rec=list(map(json.loads,RECEIPTS.open())); byfid={}
 for x in rec:byfid.setdefault(str(x['fid']),[]).append(x)
 features={str(x['fid']):x for x in map(json.loads,FEATURES.open())};scores={str(x['fid']):x for x in map(json.loads,SCORES.open())}
 exact=sorted(set(byfid)&set(features)&set(scores)); rows=[];fail=[]
 for fid in exact:
  x=max(byfid[fid],key=lambda z:z['received_utc'])
  ko=dt.datetime.fromisoformat(x['kickoff_utc'].replace('Z','+00:00')).astimezone(TZ)
  recv=dt.datetime.fromisoformat(x['received_utc'].replace('Z','+00:00'))
  quote=dt.datetime.fromisoformat(x['ah_source_utc'].replace('Z','+00:00'))
  sc=scores[fid]; ft={'FT_home':sc.get('hg'),'FT_away':sc.get('ag')}
  valid=recv<dt.datetime.fromisoformat(x['kickoff_utc'].replace('Z','+00:00')) and quote<dt.datetime.fromisoformat(x['kickoff_utc'].replace('Z','+00:00'))
  rows.append({'fid':fid,'received_utc':x['received_utc'],'quote_event_utc':x['ah_source_utc'],'kickoff_utc':x['kickoff_utc'],'kickoff_beijing':ko.isoformat(),
               'snapshot_sha256':x['snapshot_sha256'],'crown_home_line':x['crown_ah_home_line'],'home_odds':x['home_decimal'],'away_odds':x['away_decimal'],
               **ft,'historical_path_row_available':True,'score_ft_row_available':True,'receipt_before_kickoff':valid,
               'history_source_timestamps_prove_http_receipt_for_features':False,'strategy_frozen_before_receipt':False})
 summary={'verified_receipt_snapshot_rows':len(rec),'receipt_unique_fids':len(byfid),'receipt_fids_with_microstructure_and_ft':len(exact),
          'valid_pre_kickoff_receipts_with_joined_features_ft':sum(x['receipt_before_kickoff'] for x in rows),
          'receipt_snapshots_after_kickoff':sum(1 for x in rec if dt.datetime.fromisoformat(x['received_utc'].replace('Z','+00:00'))>=dt.datetime.fromisoformat(x['kickoff_utc'].replace('Z','+00:00'))),
          'receipt_coverage':{'receipt_file_sha256':sha(RECEIPTS),'features_sha256':sha(FEATURES),'scores_sha256':sha(SCORES)},
          'interpretation':'Historical full-path feature records do not include HTTP receipt arrival time. The receipt price itself is verified, but no microstructure model was frozen before these receipts; results are not prospective.'}
 (OUT/'receipt_overlap_audit_20261120.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 with gzip.open(OUT/'receipt_overlap_per_fid_20261120.jsonl.gz','wt',encoding='utf8') as f:
  for x in rows:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
