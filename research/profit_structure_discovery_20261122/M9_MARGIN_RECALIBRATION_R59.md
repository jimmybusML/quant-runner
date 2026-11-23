# R59 | Previous-year OOS seven-margin recalibration: negative result

## Scope and design

Same 26,012 held-out fixtures as R57/R58 across 43 leagues, 121 league-year groups, 2024–26. Prior-year OOS margin category expected counts are computed from a bivariate model fitted before that prior year. Exploratory multiplicative seven-category correction factor `(observed + 1)/(predicted expected count + 1)` is then applied to the following year model score grid and normalized. Pseudocount +1 is a **research choice**, not an approved production rule. All training and calibration use earlier kickoff dates, but latest historical cache is not point-in-time archived.

## Held-out results

| Year | N | Original margin Log Loss | Corrected margin Log Loss |
|---|---:|---:|---:|
| 2024 | 8,878 | 1.754896 | 1.763957 |
| 2025 | 9,038 | 1.764658 | 1.778522 |
| 2026 | 8,096 | 1.781613 | 1.795951 |
| **All** | **26,012** | **1.766603** | **1.778976** |

Overall seven-margin Brier original **0.809442**, recalibrated **0.813251** (worse). Synthetic neutral AH0 direction changes **1183**; no Crown prices or ROI. Three league-year groups had no eligible previous-year calibration matches and hence an identity correction.

## Calibration aggregate

| Margin | Actual | Original | Corrected |
|---|---:|---:|---:|
| 客胜≥3 | 5.720% | 5.520% | 5.525% |
| 客胜2 | 8.319% | 8.729% | 8.397% |
| 客胜1 | 17.134% | 17.345% | 16.811% |
| 平局 | 25.573% | 24.820% | 25.435% |
| 主胜1 | 21.152% | 20.863% | 21.256% |
| 主胜2 | 12.094% | 12.519% | 12.742% |
| 主胜≥3 | 10.007% | 10.204% | 9.835% |

## Asian handicap five-state probability test

Full-win, half-win, push, half-loss, full-loss states were derived from the entire score grid for synthetic **home handicap lines** from −1.5 to +1.5 in quarter-goal steps, evaluated against exact score results. These are **proper probability scoring metrics**, not betting PnL.

| Home handicap | Original five-state Brier | Corrected Brier | Original five-state LL | Corrected LL |
|---|---:|---:|---:|---:|
| -1.5 | 0.315932 | 0.316874 | 0.491726 | 0.492666 |
| -1.25 | 0.544394 | 0.546503 | 0.929654 | 0.932972 |
| -1 | 0.544394 | 0.546503 | 0.929654 | 0.932972 |
| -0.75 | 0.544394 | 0.546503 | 0.929654 | 0.932972 |
| -0.5 | 0.442989 | 0.444851 | 0.635620 | 0.637805 |
| -0.25 | 0.606279 | 0.608330 | 1.016685 | 1.020264 |
| +0 | 0.606279 | 0.608330 | 1.016685 | 1.020264 |
| +0.25 | 0.606279 | 0.608330 | 1.016685 | 1.020264 |
| +0.5 | 0.390815 | 0.392082 | 0.576940 | 0.579186 |
| +0.75 | 0.447694 | 0.449662 | 0.788359 | 0.793132 |
| +1 | 0.447694 | 0.449662 | 0.788359 | 0.793132 |
| +1.25 | 0.447694 | 0.449662 | 0.788359 | 0.793132 |
| +1.5 | 0.226186 | 0.227374 | 0.377030 | 0.379559 |

## Interpretation

- Correcting aggregate draw frequency (original 24.820%, corrected 25.435%, actual 25.573%) does **not** improve per-fixture forecasting.
- Both margin Log Loss and Brier deteriorate overall and in all three test years; five-state AH probability scoring deteriorates at every tested synthetic handicap line.
- This exploratory uniform league-year category recalibration should not be promoted to production; that is a research conclusion, not an added gate or user rule.
- The correction may need match-conditional structure, league/season context, or a different underlying model; these are **optional hypotheses**, not verified advantages.
- No verified historical Crown quote pairs for the 26,012 fixtures; no real AH ROI. No formal M9, Telegram, or ledger changes.
