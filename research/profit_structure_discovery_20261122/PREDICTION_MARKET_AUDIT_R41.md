# R41 | Pivot to predictive advantage and Crown market pricing: initial probability audit

User explicitly approved pivot away from searching retrospective profitable structures toward testing probability accuracy and market mispricing. This is an initial audit of existing M7/M5 model AH price-paired historical rows, NOT a new model, and NOT the R7 27 structure cohort.

## Scope and coverage

- Input: /Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend_all_orders.jsonl
- Coverage counters: {'AH_rows': 9400, 'complete': 9400}

## Core results

| Year | Rows | Unique fixtures | Model positive-return probability | Realized positive-return rate | Forecast bias pp | Binary Brier | Mean predicted EV | Mean realized U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 | 1075 | 1075 | 57.25% | 45.02% | +12.23 | 0.264383 | 14.43% | -7.44% |
| 2026 | 8325 | 8325 | 56.46% | 46.79% | +9.68 | 0.256683 | 13.86% | -3.67% |

## Model positive-return probability calibration bins

Bins use p cutpoints 0.4, 0.5, 0.6, 0.7, 0.8 (bin 0 is p<0.4; bin 5 p>=0.8).

| Year | Bin | n | Mean forecast p | Actual positive return | Mean EV | Mean realized U |
|---|---|---:|---:|---:|---:|
| 2025 | 0 | 55 | 37.76% | 32.73% | 0.70% | -1.67% |
| 2025 | 1 | 247 | 45.53% | 37.25% | 6.59% | -9.30% |
| 2025 | 2 | 348 | 55.21% | 45.40% | 9.66% | -7.33% |
| 2025 | 3 | 284 | 64.42% | 51.76% | 17.80% | -5.64% |
| 2025 | 4 | 116 | 74.05% | 50.86% | 34.63% | -6.91% |
| 2025 | 5 | 25 | 85.08% | 40.00% | 56.42% | -26.38% |
| 2026 | 0 | 421 | 37.70% | 32.78% | 0.97% | -5.33% |
| 2026 | 1 | 2014 | 45.43% | 38.73% | 6.04% | -4.56% |
| 2026 | 2 | 2971 | 55.28% | 47.93% | 10.83% | -2.92% |
| 2026 | 3 | 1980 | 64.42% | 52.78% | 18.02% | -4.11% |
| 2026 | 4 | 770 | 73.61% | 54.94% | 33.67% | -1.21% |
| 2026 | 5 | 169 | 84.24% | 50.30% | 53.72% | -8.21% |

## Preliminary interpretation

- Model M5 annual score-grid forecast positive-return probability is high relative to realized binary positive returns in both historical year cohorts. Predicted theoretical EV is also higher than realized mean net U. This flags probability calibration / pricing risk, not proof of one specific root cause.
- All audited AH rows have capture_classification HISTORICAL_RESPONSE_RETRIEVED_AFTER_KICKOFF. They are NOT proof of real-time executable Crown quotes.
- The two-sided normalized market no-vig price share is not a valid full/half-win/push Asian settlement probability; the diagnostic market-share binary Brier cannot be used to rank model vs market.
- Next research should inspect existing model score-grid or settlement-class probabilities and compare proper outcome-class scoring and exact Asian settlement EV against Crown prices, with as-of training provenance and no new betting rules.

## Caveats
- Market no-vig share is a normalized two-side quoted odds share; it is NOT the probability of positive net return for Asian quarter-line or push/half outcomes. Market Brier against positive return is only a deliberately labeled non-comparable diagnostic and cannot rank market vs model.
- Model positive-return probability cannot by itself determine full/half-win/half-loss/push EV. Require settlement-class probabilities or exact score matrix for fair price comparison.
- These pre-existing M7 records have their own model identity, fixture universe and entry windows, not original R7 27 or all494. Never transfer their predictive metrics to R7.
- Historical Crown responses captured after kickoff are not live executable; capture classification must be checked.
- Rows can include repeated fixtures across windows, directions or model versions; n is rows, not independent fixture count.
- These model forecasts may have been trained or selected on past data; no new strategy selection or production rule.
- 2026 rows, if present, are an audit of existing records only and do not imply prospective live validation.
