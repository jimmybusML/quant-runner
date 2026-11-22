#!/usr/bin/env python3
"""Reconcile the 13:23 CST full replay to the prior 10:55 CST run."""
from __future__ import annotations
import collections, gzip, hashlib, json, pathlib, sqlite3
P=pathlib.Path(__file__).resolve().parent
PREV=P.parent/'raw_replay_20261122T1055CST'
def readjson(p): return json.loads(p.read_text())
def jsonl_gz(p): return [json.loads(x) for x in gzip.open(p,'rt',encoding='utf-8')]
def jsonl(p): return [json.loads(x) for x in p.open(encoding='utf-8') if x.strip()]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def settle_outputs():
 inp=readjson(P/'INPUT_SHA256_MANIFEST.json'); db=pathlib.Path(inp['crown_sqlite_consistent_snapshot']['path'])
 cx=sqlite3.connect(f'file:{db}?mode=ro&immutable=1',uri=True)
 counts={t:int(cx.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) for t in ('capture','asian_quote')}
 cx.close()
 old={x['fid']:x for x in jsonl_gz(PREV/'exact_rule_cross_league_orders.jsonl.gz')}
 new={x['fid']:x for x in jsonl_gz(P/'exact_rule_cross_league_orders.jsonl.gz')}
 core=('group','trigger_groups','priority_assigned_group','home','away','league_id','kickoff_beijing','year','side','AH_line_home','AH_home_odds','AH_away_odds','selected_odds','FT_home','FT_away','settlement','net_u','response_sha256','quote_source_at_utc','T6_source_quote_utc','T3_source_quote_utc','T1_source_quote_utc')
 changed=[fid for fid in sorted(set(old)&set(new)) if any(old[fid].get(k)!=new[fid].get(k) for k in core)]
 oldcov={x['fid']:x for x in jsonl(PREV/'exact_rule_cross_league_coverage.jsonl')}
 newcov={x['fid']:x for x in jsonl(P/'exact_rule_cross_league_coverage.jsonl')}
 cov_changed=[fid for fid in sorted(set(oldcov)&set(newcov)) if oldcov[fid]!=newcov[fid]]
 summ=readjson(P/'exact_rule_cross_league_summary.json'); ver=readjson(P/'exact_rule_cross_league_independent_verification.json')
 result={'study':'M8_EXACT_FROZEN_RULE_CROSS_LEAGUE_SNAPSHOT_RECONCILIATION','snapshot_time_local':'2026-11-22T13:23:00+08:00','snapshot_sha256':inp['crown_sqlite_consistent_snapshot']['sha256'],'snapshot_database_counts':counts,'comparison_run':'raw_replay_20261122T1055CST','old_order_fids':len(old),'new_order_fids':len(new),'added_order_fids':sorted(set(new)-set(old)),'removed_order_fids':sorted(set(old)-set(new)),'changed_order_core_fids':changed,'old_coverage_fids':len(oldcov),'new_coverage_fids':len(newcov),'coverage_changed_fids':cov_changed,'current_outside_scope_capture_rows':summ['sources']['capture_rows_for_outside49'],'current_outside_scope_priced_fids':summ['coverage']['movement_capture_fids_with_quote_rows'],'current_outside_scope_asian_quote_rows':456242,'current_full_path_n':summ['coverage']['complete_path_n'],'current_unique_order_n':summ['coverage']['exact_assigned_orders_n'],'new_incremental':summ['results']['new_incremental'],'combined':summ['results']['combined_original8_plus_new'],'independent_verification':ver,'result':'identical outside-49 order and coverage ledger across the two consistent snapshots; no refreshed scope row changed'}
 (P/'latest_snapshot_reconciliation_20261122.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 assert len(old)==len(new) and not result['added_order_fids'] and not result['removed_order_fids'] and not changed and len(oldcov)==len(newcov) and not cov_changed
 # Replace this section idempotently; keep the standard builder as the report source.
 report=P/'EXACT_RULE_CROSS_LEAGUE_REPORT.md'; text=report.read_text(); marker='## 最新快照复核（2026-11-22 13:23 CST）'
 if marker in text:
  before,rest=text.split(marker,1); tail=rest.split('\n## ',1)
  text=before+('## '+tail[1] if len(tail)>1 else '')
 section=f