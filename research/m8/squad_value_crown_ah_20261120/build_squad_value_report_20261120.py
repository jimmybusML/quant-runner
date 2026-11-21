#!/usr/bin/env python3
"""Render squad-value AH report from saved study and independent audit JSON."""
import datetime as dt
import json
import pathlib

OUT=pathlib.Path(__file__).resolve().parent
D=json.loads((OUT/'m8_squad_value_results_20261120.json').read_text())
V=json.loads((OUT/'squad_value_independent_verification_20261120.json').read_text())

def f(x,n=3):return f'{x:+.{n}f}' if isinstance(x,(int,float)) else str(x)

def main():
 names={'CROWN_ONLY':'Crown-only','VALUE_ONLY':'Squad-value only','CROWN_PLUS_VALUE':'Crown + squad value','LOWER_PRICE':'Lower-price side'}
 lines=['# M8 squad market value × Crown AH study (2026-11-20)','',
 '## Conclusion','',
 '**No independent profitable expansion was found.** All 4,275 out-of-eight unique candidate FIDs lost under each fixed model. Crown+value lost 179.985U (−4.210%), worse than Crown-only on the same fixtures (−42.370U, −0.991%). The value-only model lost 166.610U (−3.897%). This is a retrospective historical Crown event-time replay. The available player-value archive is truncated and ends in 2024, while appearance history ends in June 2026; it does not prove when valuations or reconstructed rosters were published or received. Actual receipt profitability is therefore unavailable.', '',
 'The frozen original eight remained unchanged. No M8/M9/M1/MR1 production, Telegram, formal ledger, collector or schedule changes were made.', '',
 '## Hypothesis and data', '',
 '- New mechanism: a prior-appearance-based squad proxy measured from player market values may identify strength or depth information not fully reflected in Crown AH prices. This differs from the previous score/Elo, shots/possession, lineup repetition/load and transfer-activity studies by measuring accumulated player valuation rather than match outcomes or workload.',
 f"- Historical training/test source: {D['coverage']['crown_paired_fids']:,} paired Crown T24/T12 FIDs across 48 Crown leagues. The reused, audited crosswalk covers {D['source_audit']['other']['mapped_competitions']} Transfermarkt competitions and {D['source_audit']['other']['teams_crosswalked']} Crown clubs. Only cases with both teams mapped and a usable estimated squad-value feature were modeled.",
 f"- The original cross-league expansion’s 15 league IDs were checked directly: paired Crown T24/T12 inventory overlap {D['coverage']['expanded15_paired_crown_fids']} FIDs; mapped Transfermarkt club crosswalk overlap {len(D['coverage']['expanded15_ids_with_team_crosswalk'])} leagues. Therefore this mechanism was not evaluated in any of the new 15 leagues; no result below should be extrapolated to them.",
 f"- Feature rows: {D['coverage']['features_two_sides']:,}; missing/omitted coverage: {json.dumps(D['coverage']['feature_missing_reasons'],ensure_ascii=False)}. Test feature IDs: {D['coverage']['test_feature_fids']:,}, including {D['coverage']['frozen_overlap']:,} frozen-eight overlaps and {D['coverage']['incremental_unique_fids']:,} unique new candidates.",
 f"- Test rows by year: {json.dumps(D['coverage']['test_fids_by_year'],ensure_ascii=False)}; target date range {D['coverage']['test_date_range'][0]} to {D['coverage']['test_date_range'][1]}. The mapped-team appearances source ends 2026-05-24; later targets are excluded when the fixed three-day pre-match feature cutoff would exceed that source coverage.",
 f"- The locally saved `player_valuations.csv.gz` fails gzip EOF/CRC. The script salvages {D['source_audit']['valuation']['complete_csv_data_rows']:,} newline-terminated complete records, excludes the incomplete final record, and uses only dated values at least 30 days before each target. Newest complete value date: {D['source_audit']['valuation']['complete_last_date']}; no valuation publication/receipt timestamps are present.",
 '- A squad proxy includes players with a mapped-team appearance in the prior 365 days whose latest pre-cutoff appearance across mapped clubs remains with that team. It is not the target lineup, a verified roster, or a contemporaneous roster snapshot. Valuation age is retained as a feature and reported rather than filtered to improve ROI.',
 f"- Mean value ages (both teams) were 116.5 days in 2024, 227.5 days in 2025, and 471.7 days in the 2026 partial sample (maximum 627 days in 2026). The old valuation file makes later-year results a stale-value stress test, not a fresh current squad-value test.", '',
 '## Fixed model design', '',
 '- Target: home one-unit net AH payout minus away one-unit net AH payout at the paired Crown T12 AH contract. Quarter-handicap bets are independently split into equal half-line legs.',
 '- Crown baseline uses Crown AH line, both decimal prices and price-derived variables. Squad-value features include top-11 and active-squad aggregate value, median/mean value, valued-player count, appearance-roster count, coverage, concentration and value age; model includes both home-away differences and sums.',
 '- Fixed Ridge alpha=100, expanding-year folds. Test year Y uses only earlier calendar years; no target-year fitting, subgroup threshold search, league filter or ROI gate. Fold sample sizes:',
 '', '| Test year | Prior-year training rows | Feature-eligible test rows |', '|---|---:|---:|']
 for y,z in D['training_folds'].items():lines.append(f"| {y} | {z['train_n']:,} | {z['test_n']:,} |")
 lines += ['', 'All model variants use the same FIDs. The lower-price side is a same-fixture descriptive benchmark; it is not a candidate rule.', '', '## Unique out-of-eight performance','',
 '| Method | New unique FIDs | Net U | ROI | MDD U | ISO-week span | Mean orders/week | Active weeks |', '|---|---:|---:|---:|---:|---:|---:|---:|']
 for m in names:
  x=D['models'][m]['incremental'];lines.append(f"| {names[m]} | {x['orders']:,} | {f(x['net_u'])} | {f(x['roi_pct'])}% | {f(x['mdd_u'])} | {x['observation_iso_weeks']} | {x['weekly_avg_orders']:.2f} | {x['active_iso_weeks']} |")
 lines += ['', '## Year-by-year','', '| Method | 2024 orders / net U / ROI | 2025 orders / net U / ROI | 2026 partial orders / net U / ROI |','|---|---:|---:|---:|']
 for m in names:
  cells=[]
  for y in ('2024','2025','2026'):
   x=D['models'][m]['incremental_by_year'][y];cells.append(f"{x['orders']:,} / {f(x['net_u'])} / {f(x['roi_pct'])}%")
  lines.append(f"| {names[m]} | "+' | '.join(cells)+' |')
 lines += ['', '## Frozen-eight same-horizon combination','',
 f"Frozen baseline over the 2024–2026 test period: {D['frozen_eight_same_horizon']['orders']:,} FIDs, {f(D['frozen_eight_same_horizon']['net_u'])}U, ROI {f(D['frozen_eight_same_horizon']['roi_pct'])}%. Each model adds only its unique out-of-eight FIDs.", '',
 '| Method | Combined unique FIDs | Combined net U | Combined ROI | Change vs frozen baseline |', '|---|---:|---:|---:|---:|']
 for m in ('CROWN_ONLY','VALUE_ONLY','CROWN_PLUS_VALUE'):
  x=D['merged_frozen_eight_by_model'][m]
  lines.append(f"| {names[m]} | {x['orders']:,} | {f(x['net_u'])} | {f(x['roi_pct'])}% | {f(x['net_u']-D['frozen_eight_same_horizon']['net_u'])}U |")
 lines += ['', '## Annual estimate freshness and receipt audit','',
 f"The genuine Crown receipt archive has {D['coverage']['true_receipt_archive_rows']:,} rows / {D['coverage']['true_receipt_unique_fids']:,} unique FIDs, but overlap with the corrected feature-test set is {D['coverage']['receipt_fid_overlap_with_feature_test']}. It has {D['coverage']['receipt_value_snapshot_timestamp_rows']} timestamped player-value snapshots. No true-receipt model result can be computed; the model's latest target is May 24, 2026, before the later archived receipt window.", '',
 '## Independent verification','',
 f"The independent verifier re-opened the Crown T12 market inventory, FT, frozen membership and per-fixture ledger. It passed {V['quote_ft_identity_checks']:,} Crown quote/FT identity checks, {V['independent_ah_settlement_checks']:,} independently recomputed AH settlements, {V['side_rule_checks']:,} model direction checks, and {V['cutoff_and_frozen_overlap_checks']:,} date-cutoff/membership checks. Every model uses the same {V['unique_common_test_fids']:,} FIDs; no duplicate FID within a model; all four variants have {D['coverage']['incremental_unique_fids']:,} out-of-eight candidates. Full per-week and per-league tables are in `m8_squad_value_results_20261120.json`.", '',
 '## Preserved superseded attempt','',
 'The first complete run included matches later than the appearance-source end date, applying a stale frozen roster history to later fixtures. That run is preserved as `SUPERSEDED_UNGUARDED_APPEARANCE_CUTOFF_RESULTS_20261120.json` and `SUPERSEDED_UNGUARDED_APPEARANCE_CUTOFF_LEDGER_20261120.jsonl.gz`, with the reason documented in `SUPERSEDED_ATTEMPT_NOTE_20261120.md`. It is not part of the primary results above. The corrected run excludes those fixtures solely because the required pre-match appearance-history cutoff lies beyond source coverage.', '',
 '## Reproduction','',
 '- Main research: `m8_squad_value_crown_ah_20261120.py`',
 '- Independent verifier: `verify_squad_value_crown_ah_20261120.py`',
 '- Report renderer: `build_squad_value_report_20261120.py`',
 '- Full per-fixture ledger: `squad_value_per_fixture_20261120.jsonl.gz`',
 '- Complete summary, annual, ISO-week and league tables: `m8_squad_value_results_20261120.json`',
 '- Independent audit: `squad_value_independent_verification_20261120.json`',
 '- Re-run main script, verifier, then report renderer. SHA256 manifest records inputs/outputs.', '',
 'Historical research only; no formal strategy, production, Telegram or ledger behavior changed.']
 (OUT/'M8_SQUAD_VALUE_CROWN_AH_RESEARCH_20261120.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
