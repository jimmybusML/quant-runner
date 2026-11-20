#!/usr/bin/env python3
"""Render the M8 referee-history research report from saved result artifacts."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
RESULT = json.loads((OUT / 'm8_referee_history_results_20261120.json').read_text())
VERIFY = json.loads((OUT / 'referee_history_independent_verification_20261120.json').read_text())


def fmt(v, digits=3):
    return f'{v:+.{digits}f}' if isinstance(v, (int, float)) else str(v)


def main():
    methods = ('CROWN_ONLY', 'REF_ONLY', 'CROWN_PLUS_REF', 'LOWER_PRICE')
    titles = {
        'CROWN_ONLY': 'Crown-only market control',
        'REF_ONLY': 'Referee history only',
        'CROWN_PLUS_REF': 'Crown + referee history',
        'LOWER_PRICE': 'Same-fixture lower-price side',
    }
    lines = [
        '# M8 referee-history and Crown AH study (2026-11-20)', '',
        '## Conclusion', '',
        '**No independent profitable source was identified.** On the same 5,467 FIDs outside the frozen original eight, the referee-only model lost 170.705U (-3.122%), and Crown+referee lost 79.745U (-1.459%). Crown-only on the same eligible sample lost 27.770U (-0.508%); the referee feature therefore worsened the combined 2024–2026 net by 51.975U. The referee assignment in the source is retrospective and has no publication/receipt timestamp, so none of these results establishes a usable pre-match information advantage.', '',
        'This is a historical Crown source-event replay, not an HTTP-receipt replay, a formal trade, or a Telegram result. Original eight membership, M9/M1/MR1, production and ledger were not changed.', '',
        '## Scope and data', '',
        f"- The already audited paired Crown T24/T12 historical inventory supplied {RESULT['source_audit']['crown_t12_unique_fids']:,} unique FIDs; the full paired market file contains {VERIFY['raw_crown_t12_rows']:,} T12 rows before the paired-path restriction. The experiment only used T12 rows in that paired inventory. Prices and FT came from the Crown historical event-time inventory; historical retrieval is not proof of receipt time.",
        f"- A strict league/team crosswalk, ordered home/away identity, date within ±1 day, exact FT and referee-name join matched {RESULT['source_audit']['matched_referee_fids']:,} of 38,846 paired FIDs ({RESULT['source_audit']['unique_normalized_referees_within_league']} normalized league-scoped referee identities). Coverage loss: {json.dumps(RESULT['source_audit']['coverage_reasons'], ensure_ascii=False)}.",
        f"- Of those matched cases, {RESULT['source_audit']['test_rows_with_prior_referee_history']:,} target fixtures in 2024–2026 had a prior referee history and entered the common model sample: 2024 {RESULT['source_audit']['test_year_fids']['2024']:,}; 2025 {RESULT['source_audit']['test_year_fids']['2025']:,}; 2026 {RESULT['source_audit']['test_year_fids']['2026']:,}. Test dates run {RESULT['source_audit']['test_date_range'][0]} through {RESULT['source_audit']['test_date_range'][1]} China-time date labels.",
        f"- The common test contains {RESULT['source_audit']['test_frozen_overlap_fids']:,} frozen-eight overlaps and {RESULT['source_audit']['incremental_unique_candidate_fids']:,} unique incremental FIDs. Every model has one direction per FID; models overlap completely and must not be summed.",
        '- The source match uses retrospective referee identity in Transfermarkt games.csv.gz. It contains no referee appointment publication or receipt time; the games source ends 2026-07-06. The saved actual Crown receipt archive has 12,550 rows / 1,607 FIDs dated 2026-10-08 through 2026-11-14, zero FID overlap with model targets, and zero referee-assignment timestamp evidence.', '',
        '## Method', '',
        '- Target is the difference between one-unit net AH payouts for home and away at the Crown T12 line and both Crown prices. Quarter-handicap contracts are split into equal half-line legs and settled separately.',
        '- Historical referee feature is within-league prior mean (home goals − away goals + Crown home AH line), minus that league’s prior mean, shrunk by n/(n+20); a log(1+n) history count is also included. Prior matches are embargoed through target date minus three calendar days because the source has date but no finish time.',
        '- Models are fixed Ridge alpha 100: Crown prices/line only; referee features only; Crown+referee; and a same-FID low-price-side control. 2024/2025/2026 are expanding-year test folds trained only on earlier calendar years (5,173 / 7,333 / 10,572 eligible training rows respectively). No threshold or league search was used.',
        '- Frozen membership is used only after prediction for unique incremental attribution; it is not a feature. AH only; no OU.', '',
        '## Eight-group-excluded performance', '',
        '| Method | Incremental unique FIDs | Net U | ROI | MDD U | ISO weeks in span | Average orders / week | Active weeks |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for method in methods:
        x = RESULT['models'][method]['incremental_outside_frozen_eight']
        lines.append(f"| {titles[method]} | {x['orders']:,} | {fmt(x['net_u'])} | {fmt(x['roi_pct'])}% | {fmt(x['mdd_u'])} | {x['observation_iso_weeks']} | {x['weekly_avg_orders']:.2f} | {x['active_iso_weeks']} |")
    lines += ['', '## Year-by-year results', '', '| Method | 2024 orders / net U / ROI | 2025 orders / net U / ROI | 2026 orders / net U / ROI |', '|---|---:|---:|---:|']
    for method in methods:
        cells = []
        for year in ('2024', '2025', '2026'):
            x = RESULT['models'][method]['incremental_by_year'][year]
            cells.append(f"{x['orders']:,} / {fmt(x['net_u'])} / {fmt(x['roi_pct'])}%")
        lines.append(f"| {titles[method]} | " + ' | '.join(cells) + ' |')
    lines += ['', '## Frozen-eight same-horizon combination', '',
              'The frozen group baseline for the same 2024–2026 dates is 6,873 FIDs, +197.765U, ROI 2.877%. Each row below adds that model’s unique outside-eight candidates once. The original eight is not changed.', '',
              '| Method | Combined unique FIDs | Combined net U | Combined ROI | Change vs frozen baseline |', '|---|---:|---:|---:|---:|']
    baseline = RESULT['frozen_baseline']['2024_2026']
    for method in ('CROWN_ONLY', 'REF_ONLY', 'CROWN_PLUS_REF'):
        x = RESULT['combined_same_horizon'][method]['2024_2026']
        change = x['net_u'] - baseline['net_u']
        lines.append(f"| {titles[method]} | {x['orders']:,} | {fmt(x['net_u'])} | {fmt(x['roi_pct'])}% | {fmt(change)}U |")
    lines += ['', '## Weekly uncertainty and dispersion', '',
              'A descriptive ISO-week block bootstrap resampled active weeks with replacement within each test year (20,000 repetitions, seed 20261120). It does not correct for the fact that these years have been examined in prior M8 research.', '',
              '| Method | 95% interval net U | 95% interval ROI | Bootstrap share net-positive |', '|---|---:|---:|---:|']
    for method in methods:
        b = VERIFY['weekly_block_bootstrap'][method]
        lines.append(f"| {titles[method]} | [{fmt(b['unit_ci_95'][0])}, {fmt(b['unit_ci_95'][1])}] | [{fmt(b['roi_pct_ci_95'][0])}%, {fmt(b['roi_pct_ci_95'][1])}%] | {100*b['bootstrap_probability_net_positive']:.2f}% |")
    lines += ['', 'Candidate ISO-week count and net U for every method are preserved in `m8_referee_history_results_20261120.json` and `referee_history_independent_verification_20261120.json`.', '',
              '## League distribution', '',
              'The central Crown+referee candidate was positive in 8 of 25 leagues and negative in 17; league IDs are the Crown IDs. Positive groups were 1, 12, 25, 29, 48, 52, 70, 75; all 25 counts, net U and ROI are in the result JSON. The largest positive entries include ID 1 (459 orders, +25.165U), ID 48 (351, +15.345U), ID 52 (142, +11.450U), ID 70 (109, +8.245U), and ID 75 (41, +7.275U). The largest negative entries include ID 14 (601, −29.845U), ID 262 (257, −21.730U), ID 26540 (246, −13.270U), ID 61 (160, −11.410U), and ID 319 (101, −10.360U). These are descriptive, not a basis for league filtering; no league-specific rule was fit or selected.', '',
              '## Independent verification', '',
              f"- Independent verifier reopened the paired Crown T12 market inventory, frozen membership and gzip ledger. It checked exact FID/date/league/home/away, Crown AH line, both Crown prices and FT, then independently settled all bets, including split quarters: {VERIFY['raw_crown_quote_ft_identity_checks']:,}/{VERIFY['ledger_rows']:,} quote/FT checks passed; {VERIFY['independent_ah_settlement_checks']:,}/{VERIFY['ledger_rows']:,} settlement checks passed; direction/price selection checks {VERIFY['side_rule_checks']:,}/{VERIFY['ledger_rows']:,} passed.",
              f"- Duplicate FIDs within each model: {VERIFY['duplicate_method_fids']}; frozen overlap: {VERIFY['frozen_overlap_method_fids']:,}; incremental unique FIDs per model: {VERIFY['unique_incremental_fids_per_method']:,}. Annual ledger sums independently match the result JSON.",
              '- The verifier validates archived source-event prices and stored FT, not raw HTTP receipt bodies. There are no valid same-target referee-information receipts, so true receipt performance is not computable (zero eligible fixtures), not zero-profit live trading.', '',
              '## Answer and limits', '',
              'Retrospective referee identity alone has no independent profitable AH value in this design. Adding it to Crown prices improved one narrow test slice in 2024 by only +0.675U, then lost 47.915U in 2025 and 32.505U in 2026; total incremental loss was 79.745U. This does not support a stable signal or an actionable edge. The reason the hypothesis cannot be conclusively tested as a real pre-match information source is not just limited statistical power: the dataset lacks appointment publication/receipt timestamps, and the later genuine Crown receipt archive has no joinable target with a referee snapshot. The retrospective upper-bound is negative despite that optimistic availability assumption.', '',
              '## Reproduction and artifacts', '',
              '- Main research: `m8_referee_history_ah_20261120.py`',
              '- Independent source/settlement validator: `verify_referee_history_ah_20261120.py`',
              '- Report renderer: `build_referee_history_report_20261120.py`',
              '- Per-fixture ledger (four method rows per eligible FID): `referee_history_per_fixture_20261120.jsonl.gz`',
              '- Complete year/week/league results and coefficients: `m8_referee_history_results_20261120.json`',
              '- Independent verifier and block bootstrap: `referee_history_independent_verification_20261120.json`',
              '- Re-run: `python3 research/m8/referee_history_ah_20261120/m8_referee_history_ah_20261120.py`, then run the verifier, then this renderer.', '',
              'Historical experiment only. No production, original-eight, Telegram, formal ledger, collector or schedule changes.' ]
    (OUT / 'M8_REFEREE_HISTORY_AH_RESEARCH_20261120.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
