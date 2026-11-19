#!/usr/bin/env python3
"""Read-only audit of independent pre-match information and recent live Crown captures.

This script deliberately does not fit models or mutate production/collection data.
"""
from __future__ import annotations
import csv, gzip, hashlib, json, pathlib, sqlite3, time
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/m8/prematch_information_audit_20261119'
OUT.mkdir(parents=True, exist_ok=True)
DB = pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
SRC = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_pregame_info_source_20261117')
RECEIPT_AUDIT = ROOT / 'research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl'
FROZEN_FT = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m8_new_receipt_frozen_eight_FT_20261115.jsonl')


def sha(path: pathlib.Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def dt(s):
    if not s: return None
    return datetime.fromisoformat(s.replace('Z','+00:00'))

# Inventory available local pre-game data sources; timestamps here refer to source fields,
# not filesystem modification times.
source_specs = {
 'appearances.csv.gz': {'prior_research':'R63 player-minute weighting', 'timestamp_fields':[], 'limitation':'Past performance rows have no first-published/received timestamps.'},
 'game_lineups.csv.gz': {'prior_research':'R50 lineup stability/transfer review', 'timestamp_fields':[], 'limitation':'Lineup records lack first-public and system-received timestamps; target lineups are not proven pregame.'},
 'games.csv.gz': {'prior_research':'R44-R46 standings/calendar/context; team residual studies', 'timestamp_fields':['date'], 'limitation':'No collection/first-available timestamp; target-row results/positions are post-event.'},
 'transfers.csv.gz': {'prior_research':'R50 transfer history; R61-R65 news/absence work', 'timestamp_fields':['transfer_date'], 'limitation':'Event dates do not establish announcement/receipt time; future-dated rows and source cutoff exist.'},
 'player_valuations.csv.gz': {'prior_research':'R50 attempted, unusable', 'timestamp_fields':['date'], 'limitation':'Compressed file is truncated/corrupt; cannot establish usable historical snapshots.'},
 'competitions.csv.gz': {'prior_research':'ID mapping only', 'timestamp_fields':[], 'limitation':'Static competition metadata, not match-time information.'},
 'future_eng_20261121.json': {'prior_research':'Not in settled historical analyses', 'timestamp_fields':['news[].published_at'], 'limitation':'No proven HTTP received time, future fixture, and no matching Crown live capture/settled outcome.'},
 'future_nor_20261120.json': {'prior_research':'Not in settled historical analyses', 'timestamp_fields':['news[].published_at'], 'limitation':'No proven HTTP received time, future fixture, and no matching Crown live capture/settled outcome.'},
 'past_eng_candidate.json': {'prior_research':'Historical event context', 'timestamp_fields':[], 'limitation':'One historical event; post-event availability cannot be ruled out.'},
}
source_inventory=[]
for name,meta in source_specs.items():
 p=SRC/name
 row={'path':str(p),'exists':p.exists(),**meta}
 if p.exists():
  row.update({'bytes':p.stat().st_size,'sha256':sha(p)})
  if name.endswith('.csv.gz'):
   try:
    with gzip.open(p,'rt',newline='',encoding='utf-8-sig') as f:
     reader=csv.reader(f); row['columns']=next(reader); row['rows']=sum(1 for _ in reader)
   except Exception as e: row['read_error']=f'{type(e).__name__}: {e}'
  elif name.endswith('.json'):
   try:
    obj=json.loads(p.read_text()); row['top_level_type']=type(obj).__name__; row['top_level_keys']=list(obj)[:30] if isinstance(obj,dict) else None
    row['fixture_count']=len(obj) if isinstance(obj,list) else None
   except Exception as e: row['read_error']=f'{type(e).__name__}: {e}'
 source_inventory.append(row)

# Read-only Crown capture and quote audit.
con=sqlite3.connect(f'file:{DB}?mode=ro',uri=True)
con.row_factory=sqlite3.Row
q="""SELECT c.fixture_id,c.capture_key,c.response_received_at_utc,c.processed_at_utc,c.source_file,
 c.response_sha256,c.kickoff_at_utc,c.prospective_observation,c.status,c.quote_count,
 COUNT(q.sequence_index) AS quote_rows,
 MIN(q.quote_source_at_utc) AS first_quote_source_at_utc,
 MAX(q.quote_source_at_utc) AS last_quote_source_at_utc,
 MIN(q.quote_before_kickoff) AS all_quotes_before_kickoff,
 SUM(CASE WHEN q.quote_source_at_utc > q.response_received_at_utc THEN 1 ELSE 0 END) AS source_after_receipt
 FROM capture c LEFT JOIN asian_quote q ON q.capture_key=c.capture_key
 WHERE c.capture_mode='live' AND c.data_layer='summary'
 AND c.status='QUOTES_SAVED' AND c.prospective_observation=1
 GROUP BY c.capture_key ORDER BY c.response_received_at_utc"""
captures=[dict(x) for x in con.execute(q)]
# Hash-check exact raw response files and build per-FID chronology/coverage.
sha_counts=Counter(); file_missing=[]; file_mismatch=[]; capture_by_fid=defaultdict(list)
for r in captures:
 p=pathlib.Path(r['source_file']) if r['source_file'] else None
 if not p or not p.is_file(): file_missing.append({'fid':r['fixture_id'],'path':r['source_file']}); continue
 got=sha(p)
 if got != r['response_sha256']: file_mismatch.append({'fid':r['fixture_id'],'expected':r['response_sha256'],'actual':got})
 else: sha_counts['match']+=1
 capture_by_fid[str(r['fixture_id'])].append(r)

old_receipts={}
for line in RECEIPT_AUDIT.open():
 d=json.loads(line); old_receipts.setdefault(str(d.get('fid')),[]).append(d)
frozen={}
for line in FROZEN_FT.open():
 d=json.loads(line); frozen[str(d.get('fid'))]=d

fid_rows=[]
for fid,rs in sorted(capture_by_fid.items()):
 fid_rows.append({'fid':fid,'prospective_capture_count':len(rs),
  'receipt_first_utc':min(x['response_received_at_utc'] for x in rs),
  'receipt_last_utc':max(x['response_received_at_utc'] for x in rs),
  'kickoff_utc':rs[0]['kickoff_at_utc'],
  'old_actual_receipt_archive_overlap':fid in old_receipts,
  'prior_m8_receipt_ft_inventory_overlap':fid in frozen,
  'prior_ft_inventory_score':frozen.get(fid,{}).get('score'),
  'old_archive_receipt_rows':len(old_receipts.get(fid,[])),
  'raw_response_sha256_verified':all(pathlib.Path(x['source_file']).is_file() and sha(pathlib.Path(x['source_file']))==x['response_sha256'] for x in rs),
  'quotes_all_before_kickoff':all(x['all_quotes_before_kickoff']==1 for x in rs),
  'quote_event_after_http_receipt_count':sum(x['source_after_receipt'] or 0 for x in rs),
 })

# Additional response and failure counts.
summary=con.execute("""SELECT status,prospective_observation,COUNT(*) captures,COUNT(DISTINCT fixture_id) fids,
 MIN(response_received_at_utc) first_received,MAX(response_received_at_utc) last_received
 FROM capture WHERE capture_mode='live' AND data_layer='summary'
 GROUP BY status,prospective_observation ORDER BY status,prospective_observation""").fetchall()
failed=con.execute("SELECT error_code,COUNT(*) n,MIN(attempted_at_utc) first_attempt,MAX(attempted_at_utc) last_attempt FROM failed_attempt GROUP BY error_code ORDER BY n DESC").fetchall()
quote_by_layer=con.execute("""SELECT c.status,c.prospective_observation,q.quote_kind,COUNT(*) quote_rows,
 COUNT(DISTINCT c.fixture_id) fids FROM capture c JOIN asian_quote q ON c.capture_key=q.capture_key
 WHERE c.capture_mode='live' GROUP BY 1,2,3 ORDER BY 1,2,3""").fetchall()
con.close()

# The two later future fixture snapshots cannot be considered settled new samples.
new_fids=[r['fid'] for r in fid_rows if not r['prior_m8_receipt_ft_inventory_overlap']]
weekly=defaultdict(lambda:{'captures':0,'fids':set()})
for c in captures:
 iso=dt(c['response_received_at_utc']).isocalendar()
 key=f'{iso[0]}-W{iso[1]:02d}'
 weekly[key]['captures']+=1
 weekly[key]['fids'].add(str(c['fixture_id']))
receipt_weekly=[{'iso_week':k,'captures':v['captures'],'unique_fids':len(v['fids'])} for k,v in sorted(weekly.items())]
result={
 'generated_at_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Read-only source/temporal provenance audit; no new model or strategy run because no novel independent source with reliable pregame timing can be aligned to an unseen settled FID.',
 'input_files':{str(p):{'exists':p.exists(),'sha256':sha(p) if p.exists() else None} for p in [pathlib.Path(__file__),RECEIPT_AUDIT,FROZEN_FT]},
 'source_inventory':source_inventory,
 'crown_live_summary_capture_groups':[dict(r) for r in summary],
 'crown_live_quote_groups':[dict(r) for r in quote_by_layer],
 'crown_live_failed_attempt_groups':[dict(r) for r in failed],
 'prospective_quote_captures':len(captures),
 'prospective_fids':len(fid_rows),
 'prospective_quote_rows':sum(r['quote_rows'] for r in captures),
 'prospective_receipt_observation_weekly':receipt_weekly,
 'raw_source_files_verified_sha256':sha_counts['match'],
 'raw_source_files_missing':file_missing,
 'raw_source_files_hash_mismatch':file_mismatch,
 'capture_timestamp_bounds':{'first_http_received_utc':min(x['response_received_at_utc'] for x in captures),'last_http_received_utc':max(x['response_received_at_utc'] for x in captures),'first_quote_source_utc':min(x['first_quote_source_at_utc'] for x in captures),'last_quote_source_utc':max(x['last_quote_source_at_utc'] for x in captures)},
 'quote_time_quality':{'all_quotes_pre_kickoff':all(x['all_quotes_before_kickoff']==1 for x in captures),'source_event_after_receipt_quote_rows':sum(x['source_after_receipt'] or 0 for x in captures)},
 'overlap':{'fid_overlap_old_actual_receipt_audit':sum(x['old_actual_receipt_archive_overlap'] for x in fid_rows),'not_in_old_actual_receipt_audit':[x['fid'] for x in fid_rows if not x['old_actual_receipt_archive_overlap']],'fid_overlap_prior_m8_ft_inventory':sum(x['prior_m8_receipt_ft_inventory_overlap'] for x in fid_rows),'truly_unseen_fids':new_fids,'newly_settled_sample_count':0},
 'candidate_evaluation':{'new_mechanisms_executed':0,'reason':'Available independent team-information sources either lack match-time source/receipt timestamps, were already tested in R1-R65/A-L/M1-M8, are corrupt/incomplete, or cannot be joined to a truly unseen FID with a verified FT. The newer live rows contain Crown quotes only; every FID is already in prior M8 inventory.'},
 'fid_audit':fid_rows,
}
(OUT/'M8_PREMATCH_INFORMATION_LIVE_RECEIPT_AUDIT_20261119.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
with (OUT/'crown_live_fid_provenance_20261119.jsonl').open('w') as f:
 for x in fid_rows: f.write(json.dumps(x,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('source_inventory','fid_audit')},ensure_ascii=False,indent=2,default=str))
