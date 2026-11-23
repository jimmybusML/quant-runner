# R44 | Is M5 the right research direction? Audit before EV selection

## Conclusion

M5 is a mathematically coherent independent Poisson score-distribution baseline, not yet a demonstrated Crown Asian handicap mispricing model. EV is downstream of probability forecasts and quote prices; high theoretical EV cannot validate the forecast itself. No strategy change or new hard filter.

## Verified implementation

- Source: research/m5/m5_goal_model_oos.py; SHA256 39ada0911fba86dbe15496e5ef24fbe2424a435539296df0b35a5e8e4ff13fff
- Per-league attack/defence plus home/away baseline, ridge regularization, annual prior-year validation and calendar-year walk-forward.
- Independent Poisson home and away goals, 15x15 score matrix; no explicit correlation.
- Annual predictions are frozen at Jan 1; promoted/unseen teams receive neutral effects.
- The existing M5/Crown paired AH historical records are not real-time received quotes.

## Existing goal-score calibration results

| Year | Fixtures | Raw exact-score mean NLL | Calibrated mean NLL | Improvement |
|---|---:|---:|---:|---:|
| 2025 | 11967 | 2.94616099 | 2.94530921 | 0.00085178 |
| 2026 | 10235 | 2.99609417 | 2.99492682 | 0.00116734 |

Existing calibration uses prior settled goal rates, not Crown ROI. Improvements are small; this does not establish a tradable edge.

## Why R42/R43 EV does not decide M5 model validity

- M5 raw probabilities imply +14% average historical theoretical EV on a restricted M7 AH price-paired cohort but realized net return was negative.
- 2025-settled-label fit selected AH Crown-adjusted weight 1.0. The 100% odds-anchored distribution yields negative quoted-price EV by algebra, so zero positive-EV orders is a construction consequence.
- Need separate evaluation of score/goal distribution, goal-correlation assumption, temporal model freshness, market-independent information, and full AH settlement price calibration on properly timestamped quotes.

## Evidence boundaries

- R44 reviews existing M5 and prior audits; no new forward model training, no new quote acquisition and no proof of profitability.
- Do not confuse M5/M7 with R7 27 or all494 or formal Telegram models.
- No new gating, selection thresholds or production rules.
