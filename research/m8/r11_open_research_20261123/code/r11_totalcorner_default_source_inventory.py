#!/usr/bin/env python3
"""R11-D: independent READ-ONLY historical source-coverage audit of separately
archived TotalCorner default Asian AH/OU backup. This is NOT Crown, and not
part of R11 Crown performance or current Nov23 production completeness.
Raw book prices and fixture IDs not exported to public report.
"""
from pathlib import Path
from collections import Counter
import json,hashlib
ROOT=Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized')
P=ROOT/'totalcorner-default-progress.json'
I=ROOT/'totalcorner-default-index.jsonl'
OUT=Path('/Users/mac/QuantAsiaDesk/research-work/r11_open_method_research_20261123/r11_independent_totalcorner_default_snapshot_coverage.json')
p=json.loads(P.read_text())
rows=[json.loads(line) for line in I.open()]
ids=[str(x['match_id']) for x in rows]
s=Counter(x['status'] for x in rows)
good=[x for x in rows if x['status']=='verified_fixture_response']
bad=[x for x in rows if x['status']!='verified_fixture_response']
out={'study':'R11_HISTORICAL_DEFAULT_ASIAN_ODDS_INVENTORY_READ_ONLY',
 'snapshot_generated_utc':p.get('finished_utc'),
 'index_capture_first_utc':min(x['captured_at_utc'] for x in rows),
 'index_capture_last_utc':max(x['captured_at_utc'] for x in rows),
 'source_identity':'TotalCorner /match/odds default bookmaker NOT Crown; provider-specific quote lines and odds may differ',
 'index_sha256':hashlib.sha256(I.read_bytes()).hexdigest(),
 'progress_SHA256':hashlib.sha256(P.read_bytes()).hexdigest(),
 'source_priority_counts_for_historical_11652_candidate_subset':p.get('source_priority_market_counts'),
 'manifest_candidate_total':p.get('processed_crown_candidates'),
 'index_rows':len(rows),'unique_match_IDs':len(set(ids)),
 'verified_response_count':len(good),'error_response_count':len(bad),
 'index_rows_with_both_pregame_AH_and_OU':sum(x['ah_valid_prematch_rows']>0 and x['ou_valid_prematch_rows']>0 for x in good),
 'index_rows_with_AH_pregame':sum(x['ah_valid_prematch_rows']>0 for x in good),
 'index_rows_with_OU_pregame':sum(x['ou_valid_prematch_rows']>0 for x in good),
 'total_AH_valid_pregame_quote_rows':sum(x['ah_valid_prematch_rows'] for x in good),
 'total_OU_valid_pregame_quote_rows':sum(x['ou_valid_prematch_rows'] for x in good),
 'index_errors_by_status':dict(s),
 'limitations':['Data capture snapshot in early Nov 2026, NOT an up-to-date November 23 production ledger nor a continuously updated job health check.',
  '1150 distinct match ID count and 1156 request rows include transport errors; record counts are quote event rows not independent matches or official orders.',
  'Historical match quotes are collected long after original kickoff; source_event timestamp does NOT prove actual received price back then.',
  'The stored old progress counts 11652 historical Crown-candidate fixtures; cannot extrapolate this to all historical games or R11 9908 Crown matched cohort.',
  'TotalCorner default AH and OU are NOT Crown odds; original source priority Crown before fallback must be maintained; never mix performance without source labels.',
  'This audit does not enable any new data source or production rule and does not alter running collection process or data.']}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k in ('snapshot_generated_utc','index_rows','unique_match_IDs','verified_response_count','error_response_count','index_rows_with_both_pregame_AH_and_OU','total_AH_valid_pregame_quote_rows','total_OU_valid_pregame_quote_rows','source_priority_counts_for_historical_11652_candidate_subset')},ensure_ascii=False))
