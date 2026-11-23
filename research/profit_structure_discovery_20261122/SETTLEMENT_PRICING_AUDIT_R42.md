# R42 | Five-state AH settlement probability and Crown price calibration audit

User approved checking exact Asian settlement outcome probabilities, prediction calibration, and Crown market pricing. This report uses existing M5 annual score-grid and its pre-existing market-adjusted blend on historical M7 AH records. It does NOT evaluate R7 27, all494, or formal Telegram production orders.

## Recalculation and coverage

- AH records: 9400; independently verified full five-state AH settlement and exact M5 theoretical EV: 9400; mismatches: 0.
- Five-state array order: FULL_LOSS, HALF_LOSS, PUSH, HALF_WIN, FULL_WIN.
- EV = (P(FULL_WIN) + 0.5 P(HALF_WIN))*(decimal odds - 1) - P(FULL_LOSS) - 0.5 P(HALF_LOSS).
- Correct settlement classification uses actual final score, handicap line, direction, and decimal price.

## Year-by-year scoring and expected-return calibration

| Year | n | M5 Brier | Blend Brier | M5 log loss | Blend log loss | M5 predicted EV | Blend predicted EV | Realized net per order |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 | 1075 | 0.661117 | 0.622424 | 1.045945 | 0.997964 | +14.4301% | -4.0902% | -7.4433% |
| 2026 | 8325 | 0.643681 | 0.618731 | 1.023066 | 0.989443 | +13.8638% | -4.0218% | -3.6712% |

## Five settlement states by year

| Year | State | Actual frequency | M5 forecast frequency | Blend forecast frequency |
|---|---|---:|---:|---:|
| 2025 | FULL_LOSS | 41.77% | 31.69% | 40.56% |
| 2025 | HALF_LOSS | 6.33% | 5.36% | 6.80% |
| 2025 | PUSH | 6.88% | 5.70% | 5.70% |
| 2025 | HALF_WIN | 7.91% | 7.22% | 6.18% |
| 2025 | FULL_WIN | 37.12% | 50.04% | 40.76% |
| 2026 | FULL_LOSS | 39.82% | 31.62% | 40.07% |
| 2026 | HALF_LOSS | 6.81% | 6.05% | 7.56% |
| 2026 | PUSH | 6.58% | 5.86% | 5.86% |
| 2026 | HALF_WIN | 6.92% | 6.48% | 5.57% |
| 2026 | FULL_WIN | 39.87% | 49.99% | 40.94% |

## Interpretation

- Both cohorts have M5 mean theoretical EV around +14% despite negative realized mean net returns. The pre-existing market-adjusted blend predicts negative EV near -4% and produces lower five-class Brier and log loss than raw M5 on the same records.
- The blend is not an independently observed Crown five-state distribution. Crown two-sided prices alone do not identify the full settlement probability vector for quarter lines; independent market pricing advantage remains unproven.
- Existing research rows are classified as historical Crown responses retrieved after kickoff; quote event time before kickoff is not proof that quotes were accessible at that historical time.
- No additional betting conditions or model deployment were introduced.

## Caveats
- Verified class order by independently recomputing theoretical EV and AH settlement from raw line, side, score and odds.
- Market-adjusted blend is not an independent bookmaker probability distribution: it incorporates model information; no pure Crown five-state market distribution is identified from a single two-sided AH quote.
- Five-state multiclass Brier and logloss compare M5 and pre-existing blend on same outcome target, but market-independent superiority cannot be inferred.
- M5 forecasts and blend may have different information provenance or hindsight model-selection; not a prospectively registered experiment.
- All price-paired historical Crown records were retrieved after kickoff, not proof of real-time executable odds.
- 2025 and 2026 are existing M5/M7 historical research cohorts, not original R7 or official Telegram wagers.
- No new strategy, thresholds, portfolio changes or production writes.
