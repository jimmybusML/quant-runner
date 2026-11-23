# R70 | Why model EV overstates four-year historical Crown AH returns

## Executive finding
**The main observed mismatch is conditional on which side the model selects, rather than an equally large average bias when the same model is evaluated on fixed home or fixed away positions.** The models are on average close to the actual fixed-side payout at archived odds, but choosing the side with the model's highest estimated EV creates a large optimistic gap. This suggests a lack of exploitable information relative to the Crown market and potential winner's-curse selection effects, not a proven single causal mechanism.

## Data scope / counting
- Uses Codex recovered **2023–2026** completed fixtures and audited historical Crown movement/open source quotations at or before kickoff T−6h and T−12h.
- The R70 computation rechecked **165,390** model-price calculations: 27,826 matches × 3 models at T−6h and 27,304 × 3 at T−12h. In each scenario a fixture occurs once. The same fixture can occur once in each scenario; do not sum 6h and 12h counts as distinct games.
- **None** of the 275 M9 formal Telegram sends appears here. Every 1U result is simulated retrospectively, not an actual filled bet. Original Crown raw response SHA256 and identity were audited by R68.
- No EV or sample-size selection requirement was imposed: the model chooses the higher of the two estimated side EVs even if both are negative. Grouping labels are analytical descriptions only, not betting rules.

## 1. Three-model EV prediction vs historical settled returns

### lead6h

| Model | Matches | Predicted EV | Simulated ROI | Overstatement (pp) | Five-state Brier | Five-state log loss |
|---|---|---|---|---|---|---|
| Annual bivariate Poisson | 27,826 | +14.95% | -3.17% | +18.12 | 0.64790 | 1.04849 |
| Annual Dixon-Coles | 27,826 | +14.53% | -3.16% | +17.70 | 0.64665 | 1.04029 |
| Sequential dynamic Poisson EKF | 27,826 | +11.77% | -3.84% | +15.61 | 0.63950 | 1.01825 |

### lead12h

| Model | Matches | Predicted EV | Simulated ROI | Overstatement (pp) | Five-state Brier | Five-state log loss |
|---|---|---|---|---|---|---|
| Annual bivariate Poisson | 27,304 | +14.35% | -3.55% | +17.91 | 0.64715 | 1.04642 |
| Annual Dixon-Coles | 27,304 | +13.94% | -3.56% | +17.49 | 0.64596 | 1.03814 |
| Sequential dynamic Poisson EKF | 27,304 | +11.29% | -3.65% | +14.94 | 0.63862 | 1.01644 |

The winning-side forecast is not a market edge simply because its estimated EV is positive. All three models overstate the chosen-side EV relative to historically settled unit returns.

## 2. Fixing the side reveals an important distinction
A five-state wager has exactly reversed outcomes if backed on the opposite side. R70B independently reconstructs the opposite-side five-state distribution from the stored model-selected side, using genuine archived home/away odds. Thus we can compare model-selected EV with **always-home**, **always-away**, and **the unselected side**, on exactly the same matches and prices.

### lead6h: dynamic EKF — selection versus fixed direction

| Selection | N | Predicted EV | Historical ROI | Gap pp | Predicted full win | Actual full win |
|---|---|---|---|---|---|---|
| Model picks larger EV | 27,826 | +11.77% | -3.84% | +15.61 | 48.15% | 39.10% |
| Opposite of model pick | 27,826 | -17.93% | -2.27% | -15.65 | 33.03% | 39.91% |
| Always home | 27,826 | -3.47% | -3.43% | -0.04 | 40.58% | 39.54% |
| Always away | 27,826 | -2.69% | -2.68% | -0.01 | 40.60% | 39.47% |

### lead12h: dynamic EKF — selection versus fixed direction

| Selection | N | Predicted EV | Historical ROI | Gap pp | Predicted full win | Actual full win |
|---|---|---|---|---|---|---|
| Model picks larger EV | 27,304 | +11.29% | -3.65% | +14.94 | 48.09% | 39.32% |
| Opposite of model pick | 27,304 | -17.87% | -2.81% | -15.06 | 33.15% | 39.75% |
| Always home | 27,304 | -3.64% | -3.62% | -0.02 | 40.63% | 39.52% |
| Always away | 27,304 | -2.94% | -2.84% | -0.10 | 40.61% | 39.56% |

Always-home/away are **diagnostic comparators**, not recommended strategies. The opposite side also loses on average; the data do not prove that automatically reversing model picks would be profitable.

## 3. Five-state probability errors are conditional on selection
For each matched quote the selected direction's distribution sums to 1 and its EV and full/half/push settlement were independently recalculated. Below are dynamic EKF class-average probabilities and historical observed outcomes on the model-selected direction:

### lead6h

| State | Mean predicted | Observed frequency | Forecast−observed pp |
|---|---|---|---|
| FULL_WIN | 48.15% | 39.10% | +9.05 |
| HALF_WIN | 6.48% | 6.92% | -0.44 |
| PUSH | 6.05% | 6.89% | -0.84 |
| HALF_LOSS | 6.28% | 7.18% | -0.90 |
| FULL_LOSS | 33.03% | 39.91% | -6.88 |

### lead12h

| State | Mean predicted | Observed frequency | Forecast−observed pp |
|---|---|---|---|
| FULL_WIN | 48.09% | 39.32% | +8.76 |
| HALF_WIN | 6.44% | 6.97% | -0.54 |
| PUSH | 6.07% | 6.78% | -0.71 |
| HALF_LOSS | 6.25% | 7.17% | -0.92 |
| FULL_LOSS | 33.15% | 39.75% | -6.60 |

## 4. Four calendar years: is the gap repeated?
The following four-year figures refer to **identical-model, identical-Crown-time scenario**, not contemporaneously dispatched bets.

### lead6h dynamic EKF

| Year | N | Predicted EV | Historical ROI | Overstatement pp |
|---|---|---|---|---|
| 2023 | 4,618 | +11.59% | -3.87% | +15.45 |
| 2024 | 7,925 | +11.70% | -3.79% | +15.49 |
| 2025 | 8,115 | +11.80% | -4.18% | +15.97 |
| 2026 | 7,168 | +11.93% | -3.48% | +15.41 |

### lead12h dynamic EKF

| Year | N | Predicted EV | Historical ROI | Overstatement pp |
|---|---|---|---|---|
| 2023 | 4,545 | +11.30% | -3.30% | +14.60 |
| 2024 | 7,766 | +11.34% | -3.98% | +15.31 |
| 2025 | 7,936 | +11.29% | -3.43% | +14.71 |
| 2026 | 7,057 | +11.23% | -3.76% | +14.99 |

Both timing scenarios show positive EV overstatement in every year. The positive bias of a very broad selected-direction group is not evidence that a *profitable subgroup* persists.

## 5. Full EV distribution: does highest model EV actually pay?
The JSON contains all 2.5-percentage-point EV histogram cells and each year's matching histogram for all three models, plus 20 equal-frequency forecast-EV cells per model/lead. No combinations were hidden behind an n-based threshold. Here are the dynamic EKF quantiles from the most unfavorable to the model's highest forecast EV.

### lead6h: 20 equal-frequency EV groups

| Quantile | N | EV range | Mean forecast EV | Historical ROI | EV gap pp |
|---|---|---|---|---|---|
| 1 | 1392 | -7.6% to -1.9% | -3.02% | -6.99% | +3.97 |
| 2 | 1391 | -1.9% to -0.8% | -1.36% | -1.89% | +0.54 |
| 3 | 1391 | -0.8% to +0.4% | -0.18% | -4.57% | +4.39 |
| 4 | 1392 | +0.4% to +1.5% | +0.93% | -4.66% | +5.59 |
| 5 | 1391 | +1.5% to +2.7% | +2.09% | -2.18% | +4.26 |
| 6 | 1391 | +2.7% to +3.9% | +3.26% | -4.01% | +7.27 |
| 7 | 1392 | +3.9% to +5.1% | +4.49% | -0.17% | +4.66 |
| 8 | 1391 | +5.1% to +6.4% | +5.75% | -2.10% | +7.85 |
| 9 | 1391 | +6.4% to +7.7% | +7.05% | -4.56% | +11.61 |
| 10 | 1391 | +7.7% to +9.1% | +8.37% | -2.03% | +10.40 |
| 11 | 1392 | +9.1% to +10.6% | +9.80% | -5.93% | +15.74 |
| 12 | 1391 | +10.6% to +12.2% | +11.35% | -1.04% | +12.39 |
| 13 | 1391 | +12.2% to +13.9% | +12.99% | +0.18% | +12.81 |
| 14 | 1392 | +13.9% to +15.9% | +14.85% | -2.93% | +17.78 |
| 15 | 1391 | +15.9% to +18.0% | +16.89% | -2.91% | +19.80 |
| 16 | 1391 | +18.0% to +20.5% | +19.17% | -4.84% | +24.01 |
| 17 | 1392 | +20.5% to +23.6% | +21.95% | -8.13% | +30.07 |
| 18 | 1391 | +23.6% to +27.4% | +25.46% | -2.85% | +28.31 |
| 19 | 1391 | +27.4% to +34.4% | +30.45% | -7.07% | +37.52 |
| 20 | 1391 | +34.4% to +112.7% | +45.11% | -8.06% | +53.17 |

### lead12h: 20 equal-frequency EV groups

| Quantile | N | EV range | Mean forecast EV | Historical ROI | EV gap pp |
|---|---|---|---|---|---|
| 1 | 1366 | -8.2% to -2.1% | -3.36% | -3.70% | +0.35 |
| 2 | 1365 | -2.1% to -1.0% | -1.59% | -0.75% | -0.84 |
| 3 | 1365 | -1.0% to +0.1% | -0.47% | -4.14% | +3.67 |
| 4 | 1365 | +0.1% to +1.3% | +0.68% | -3.32% | +4.01 |
| 5 | 1365 | +1.3% to +2.4% | +1.85% | -5.75% | +7.60 |
| 6 | 1366 | +2.4% to +3.6% | +3.00% | -3.65% | +6.65 |
| 7 | 1365 | +3.6% to +4.8% | +4.18% | -2.84% | +7.02 |
| 8 | 1365 | +4.8% to +6.1% | +5.42% | +0.21% | +5.20 |
| 9 | 1365 | +6.1% to +7.3% | +6.66% | +2.15% | +4.51 |
| 10 | 1365 | +7.3% to +8.7% | +7.99% | -4.97% | +12.96 |
| 11 | 1366 | +8.7% to +10.1% | +9.38% | -0.86% | +10.24 |
| 12 | 1365 | +10.1% to +11.7% | +10.88% | -5.91% | +16.79 |
| 13 | 1365 | +11.7% to +13.3% | +12.50% | -4.73% | +17.23 |
| 14 | 1365 | +13.3% to +15.2% | +14.24% | -4.11% | +18.35 |
| 15 | 1365 | +15.2% to +17.3% | +16.23% | -3.35% | +19.58 |
| 16 | 1366 | +17.3% to +19.7% | +18.46% | -5.00% | +23.46 |
| 17 | 1365 | +19.7% to +22.7% | +21.14% | -2.49% | +23.64 |
| 18 | 1365 | +22.7% to +26.8% | +24.60% | -5.79% | +30.39 |
| 19 | 1365 | +26.8% to +33.7% | +29.83% | -8.51% | +38.35 |
| 20 | 1365 | +33.7% to +102.4% | +44.15% | -5.46% | +49.61 |

This is a descriptive ranking **over all four years**, not a time-forward selected betting rule. A positive-looking isolated cell is not independent proof of profitable trade selection.

## 6. Handicap quarter structure and odds distribution
The entire exact home-handicap line set, all quarter-point types, home-gives/home-gets, model-selected side and decimal-odds 0.1 buckets are in the JSON (not restricted to a preset handicap range).

### lead6h: handicap fractional portion

| Fraction | N | Forecast EV | ROI | Gap pp |
|---|---|---|---|---|
| half | 6,770 | +11.99% | -4.78% | +16.77 |
| integer | 6,697 | +11.95% | -2.44% | +14.39 |
| quarter | 9,618 | +11.13% | -3.93% | +15.06 |
| three-quarter | 4,741 | +12.50% | -4.28% | +16.78 |

### lead12h: handicap fractional portion

| Fraction | N | Forecast EV | ROI | Gap pp |
|---|---|---|---|---|
| half | 6,707 | +11.25% | -3.01% | +14.27 |
| integer | 6,586 | +11.39% | -2.18% | +13.57 |
| quarter | 9,346 | +10.88% | -4.37% | +15.25 |
| three-quarter | 4,665 | +12.01% | -5.19% | +17.20 |

No single handicap fraction is identified as a stable profitable category. Different year×handicap records appear in the R70 JSON and can disagree even when aggregate differences appear large.

## 7. First forward-only test of EV calibration bias
For an exploratory diagnostic only, fit a two-parameter linear payoff-versus-model-EV mapping, or simply subtract the historical average EV bias, **using only prior calendar years**. Test in 2024, 2025, 2026 without fitting either correction to the test year's outcomes. This is not a new order rule or improvement in profitability; it tests whether the optimism in a model's *reported* EV carries forward.

### lead6h dynamic EKF

| Test year | N | Prior-year bias pp | Fitted slope | Actual ROI | Raw EV | Prior-shift EV | Prior-linear EV | Raw MSE | Shift MSE | Linear MSE |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | 7925 | +15.45 | -0.138 | -3.79% | +11.70% | -3.75% | -3.88% | 0.8171 | 0.7931 | 0.7738 |
| 2025 | 8115 | +15.48 | -0.157 | -4.18% | +11.80% | -3.68% | -3.84% | 0.8171 | 0.7916 | 0.7758 |
| 2026 | 7168 | +15.67 | -0.119 | -3.48% | +11.93% | -3.74% | -3.99% | 0.8110 | 0.7873 | 0.7696 |

Pooled out-of-year one-unit payout prediction MSE (2024–26): raw 0.815250, prior-bias adjustment 0.790804, prior-linear mapping 0.773212. These changes only improve the *numerical forecast of payoff* in this retrospective experiment; they do not make the return positive or change the sign of any settled historical bet.

### lead12h dynamic EKF

| Test year | N | Prior-year bias pp | Fitted slope | Actual ROI | Raw EV | Prior-shift EV | Prior-linear EV | Raw MSE | Shift MSE | Linear MSE |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | 7766 | +14.60 | -0.135 | -3.98% | +11.34% | -3.26% | -3.30% | 0.8126 | 0.7892 | 0.7735 |
| 2025 | 7936 | +15.05 | -0.093 | -3.43% | +11.29% | -3.76% | -3.72% | 0.8110 | 0.7893 | 0.7700 |
| 2026 | 7057 | +14.92 | -0.134 | -3.76% | +11.23% | -3.69% | -3.60% | 0.8042 | 0.7817 | 0.7651 |

Pooled out-of-year one-unit payout prediction MSE (2024–26): raw 0.809432, prior-bias adjustment 0.786936, prior-linear mapping 0.769685. These changes only improve the *numerical forecast of payoff* in this retrospective experiment; they do not make the return positive or change the sign of any settled historical bet.

## 8. What is supported and what is not
- **Supported:** The selected-side optimistic EV bias is far larger than the same model's fixed-side average EV bias. Four years have similar overall positive selected-side overstatements; 2024–26 forward-only payoff-mapping tests reduce mean-squared errors.
- **Not proven:** The difference is entirely attributable to a single algorithm defect, or that R70 recalibration of profit predictions alone improves trade ROI. All tested directions remain overall negative. The fitted mapping can have a negative slope because extreme model-market disagreements are particularly unreliable.
- **Crucial historical limitation:** Most 2023–25 Crown responses were retrieved in 2026. The provider's quote event time before kickoff does NOT establish that our system received it then. Prior results entered after a 3-hour model availability proxy, not verified first-receipt timestamps.
- **Model comparability:** Annual frozen bivariate/DC versus online EKF use different update frequencies. This analysis isolates return-forecast diagnostics on matched fixtures, not a pure experimental comparison of online update algorithms.
- **Dependence:** Fixed 6h and 12h snapshots of one match are correlated, and league/team temporal dependencies remain. Bootstrap ranges by whole leagues are exploratory, not definitive financial significance tests.

## Reproducible evidence / no production changes
- Input: local user Codex archive and R66/R68 original fixture/quote evidence; R68 SHA256 Crown raw identity/source checks; R70 recomputes 165,390 state/EV/1U payout observations; R70B additionally checks exact reversal for all 165,390.
- Calculations: m9_crown_ev_calibration_r70.py, m9_crown_ev_direction_r70b.py; report: m9_crown_ev_report_r70.py.
- Aggregate outputs: M9_CROWN_EV_CALIBRATION_R70.json, M9_CROWN_EV_DIRECTION_R70B.json, M9_CROWN_EV_CALIBRATION_R70.md. Individual fixture IDs and source paths remain in private local data, not in git.
- Formal M9, Telegram dispatch, production Crown source requirements, official/settled ledger and accepted project rules were **not changed**.

## Optional next research, not confirmed rules
Investigate conditional calibration against the market using prior-year-only estimate/realization pairs, independent of whether the model's preferred side is home or away; test whether the ranking of model-market disagreement contains any robust forward edge. No EV cutoffs, restrictive categories, auto-trading conditions or model replacements are authorized by this report.
