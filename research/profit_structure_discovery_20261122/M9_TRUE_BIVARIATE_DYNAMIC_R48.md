# R48 | Original M9 bivariate model vs recent-weighted bivariate model, same fixtures (research pilot)

## Actual implementation

- Imported exact M9 production model class `penaltyblog.models.BivariatePoissonGoalModel` (as used by `ops/m9_formal_ah.py`).
- Four historical M1-cache league IDs 1, 10, 12, 61; calendar-year 2024, 2025, 2026. Each year trains on all matches before January 1, forecasts held-out matches in that year; only teams in training history have predictions.
- Original class with no weights vs same class with per-match `exp(-days_before_Jan1/365)` weights. The 365-day decay is an **exploratory research parameter only**, not user rule or deployed setting.
- Compare exact-score negative log likelihood and 1X2 negative log likelihood on identical matches. A synthetic neutral AH0 @2.0 direction is also computed but is not Crown and not tradable ROI.

## Results by league (1X2 log loss; smaller means better)

| League ID | 2024–26 fixtures | Original | Recent weighted | Interpretation |
|---|---:|---:|---:|---|
| 1 | 994 | 1.009596 | 0.999783 | Improved |
| 10 | 720 | 1.032451 | 1.161562 | Worsened |
| 12 | 1020 | 0.989163 | 0.989580 | Worsened |
| 61 | 652 | 1.052360 | 1.056495 | Worsened |

## Results by calendar year

| Year | Fixtures | Original 1X2 LL | Recent weighted 1X2 LL | Original exact-score LL | Recent weighted exact-score LL |
|---|---:|---:|---:|---:|---:|
| 2024 | 1144 | 1.024248 | 1.039324 | 3.017464 | 3.062040 |
| 2025 | 1128 | 1.013565 | 1.025373 | 2.977150 | 3.023353 |
| 2026 | 1114 | 1.011622 | 1.061677 | 3.053289 | 3.159800 |

**Total: 3386 same-fixture forecasts; 1X2 LL 1.016535 original vs 1.042030 weighted; exact-score LL 3.015821 vs 3.081315.**

## Interpretation

- Recency weighting helps league 1 but materially harms league 10; do not deploy global time-decay based on this pilot.
- This is not the R47 two-season residual correction; that mechanism is separate and has not yet been refitted to M9 goal-score grids.
- A model can improve score likelihood without improving handicap return; and synthetic AH0 cannot be reported as Crown ROI.

## Provenance / limitations
- Pilot subset leagues and calendar-year frozen training, not exact M9 per-run training time or full M9 scope.
- 365-day exponential half-life parameter is an exploratory comparison, not a user-approved production setting.
- Neutral AH0 @2.0 is a synthetic directional diagnostic; NOT Crown quote/ROI or real M9 AH line.
- M1 cached historical rows are latest snapshots; historical availability and corrections at the old forecast date are not proven.
- No model rule, gate, Telegram or official ledger changed.

## Next research options (not new production rules)

- Test strength-residual shrinkage inside the actual bivariate goal intensities, rather than simply overweighting all recent matches.
- Extend all league coverage and training cutoffs; pair only Crown odds with genuine prior-to-kickoff receipt timestamps when claiming tradable results.
- Compare original vs enhanced score-grid five-class settlement probabilities on identical actual Crown lines, then report ROI and changes in orders.
