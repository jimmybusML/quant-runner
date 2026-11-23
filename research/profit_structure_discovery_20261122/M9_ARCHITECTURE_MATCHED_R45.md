# R45 | M9 enhancement research: first matched-archive inspection and identity warning

## Recovered actual M9 source

- Public production executor: ops/m9_formal_ah.py. It invokes research.m3.openfootball_shadow.MODELS["bivariate_poisson"] using league history and selects AH side from neutral-odds score-grid calculation.
- Existing research: research/m3/penaltyblog_walkforward.py implements independently fitted Poisson, Dixon-Coles and Bivariate Poisson models.
- M9 production model identity, fixture universe, time windows and Crown formal receipt ledger must remain distinct from M3 historical shadow and M5 historical archives.

## Existing archive matched comparison

| Year | Same fixture IDs | M5 1X2 logloss | Bivariate-named archive 1X2 logloss | Recency-named archive 1X2 logloss |
|---|---:|---:|---:|---:|
| 2025 | 11187 | 1.0173152 | 1.0173152 | 1.0173152 |
| 2026 | 9409 | 1.0132839 | 1.0132839 | 1.0132839 |

## Critical interpretation

All 2025 and 2026 matched model scores, including exact-score NLL and 1X2 Brier, are identical to displayed precision across all three files. These are archive files labeled baseline-matched; they are not demonstrated independent challenger forecast outputs. Therefore **do not claim M9 bivariate or recency model has zero incremental benefit**. This run is a data-source identity/coverage diagnostic, NOT a completed M9 enhancement comparison.

## Follow-on research implementation (recommendations only)

- Generate actual original M9-equivalent bivariate score matrices and separate candidate matrices for low-score adjustment and dynamic team-strength, on identical fixtures with training data available before kickoff.
- Compare full score NLL, 1X2 and five-class AH probability calibration, not only EV or retrospective ROI.
- Pair only independently timestamped Crown quotes to claim executable market pricing edge; retrospective Crown records remain non-executable research evidence.
- Keep original M9 direction and coverage unchanged for baseline, with all alternative decisions reported as research counterfactuals; no new filters or production changes.

## Source coverage

Source rows: {'m5_annual': 22202, 'bivariate_archive': 20596, 'recency_archive': 22202}; common matched fixture IDs: 20596; parse errors: {}.

## Caveats
- Bivariate archived forecasts and recency archived forecasts are pre-existing M5 comparison artifacts, NOT the M9 production runner trained with M3 history. Therefore no M9 production improvement can be inferred.
- This scores predictive accuracy on common fixture IDs only; not Crown line/price or Asian settlement ROI.
- 2025/26 historical results can have been examined during earlier research, so this is retrospective matched scoring, not pristine untouched prospective confirmation.
- Archived forecast training as-of provenance must be checked separately before claiming executable point-in-time forecast equivalence.
- No selection thresholds, gates, strategy, M9 production code, Telegram or formal ledgers changed.
