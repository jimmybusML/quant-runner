# Execution record — M8 formation matchup Crown AH study

- Execution date: 2026-11-20 UTC.
- Publication branch: `research/m8-formation-matchup-publish`, based on `origin/main` at `132dc64f726e939ba2cf18049f2fd0048a860fc7`.
- The original research worktree `research/m8-formation-matchup-20261120` was preserved. Its pre-existing modified venue audit gzip was not staged or changed by this publication copy.
- This is a historical research replay. No Crown API request, production change, formal order, Telegram message, or ledger write occurred.

## Inputs and provenance

SHA256 values for all inputs and outputs are in `SHA256SUMS.txt`. Inputs include the Transfermarkt games archive, saved Crown historical path and score records, frozen 10,294-FID membership, expanded schedule inventory, and the current read-only Crown SQLite file. The Crown SQLite hash records the exact database state used in independent quote verification; it can change when other local work adds captures.

Transfermarkt formation fields have no verified first-publication or actual-receipt timestamps. The target match's own formation and lineup are ignored. Features use only prior completed matches before the conservative target-date-minus-three-days cutoff.

## Commands executed

```text
python3 research/m8/formation_matchup_20261120/run_formation_matchup.py
python3 research/m8/formation_matchup_20261120/verify_formation_matchup.py
python3 research/m8/formation_matchup_20261120/build_deliverables.py
```

The research runner produced 8,675 2024–2026 rows including 1,715 frozen-member rows and 6,960 unique outside-frozen FIDs. The independent verifier re-read Crown T−1 movement prices and checked schedule identity, FT, FID uniqueness, frozen overlap and independently reimplemented AH settlement.

## Result

- Crown market-only forced-side outside-frozen: 6,960 bets, −299.435U, ROI −4.302%, MDD 308.175U.
- Crown plus prior formation-profile model: same 6,960 FIDs, −197.220U, ROI −2.834%, MDD 207.420U. The paired PnL difference is +102.215U, but the candidate remains loss-making.
- Neither margin MAE nor RMSE improved over the complete 2024–2026 outside-frozen sample. The chosen side changed on 2,094/6,960 matches (30.09%). The reduced loss is an empirical paired replay effect, not evidence of a profitable signal.
- The research-only model-EV-positive policy also lost: market-only 1,291 bets/−21.140U; market plus formation 2,823 bets/−122.060U.
- All forced-side and EV-positive candidates were negative in 2024, 2025 and 2026. The frozen eight-group 2024–2026 baseline was 6,873 bets/+197.765U; combining the formation forced-side pool yields 13,833 bets/+0.545U, so the candidate reduced the baseline by 197.220U.
- Independent audit: 8,675/8,675 Crown T−1 price matches; 0 identity/FT mismatches; 0 settlement differences; 0 duplicate FIDs; 0 frozen-member overlap; 0 live-capture FIDs.

This experiment does not establish an independent profitable order source. Historical formation data availability at decision time is unproven, so it is not a real-time or prospective validation.
