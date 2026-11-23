# R61-R63 | Matched real model challenger research

## Implementations
- Real fitted original M9-class bivariate Poisson and Dixon-Coles, annual frozen baseline.
- An independent, reusable Poisson attack/defence diagonal-covariance assumed-density EKF with per-team attack/defense, league scoring rates, process variance, and post-result online updating.
- BP and Dixon-Coles expanding monthly re-fits with available-result proxy, a cadence-control research comparison. It cannot isolate all advantages from differing update cadence.
- Dixon-Coles rho projected only when mathematically necessary for nonnegative low-score probabilities; count reported.
- Research forecast CLI permits explicit as-of date, fixture and synthetic home handicap; state checkpoint serialization tested.

## Historical coverage
26,044 2024-26 fixtures, 43 leagues, 121 league-year pairs. 32 newly finalized fixtures since R57. Annual DC projection 10 and rolling DC projection 9 predictions. Monthly fit periods 1126. No missing predictions.

## Probability metrics (lower is better)
| Model | 1X2 LL | RPS | Exact-score LL | 7-bin margin LL | 7-bin margin Brier |
|---|---|---|---|---|---|
| M9-class annual BP | 1.016401 | 0.208374 | 2.952488 | 1.766424 | 0.809387 |
| Annual Dixon-Coles | 1.014580 | 0.208171 | 2.950483 | 1.762908 | 0.809061 |
| Online Poisson EKF | 1.001990 | 0.204452 | 2.945086 | 1.749409 | 0.807257 |
| Monthly BP refit | 1.007666 | 0.205872 | 2.935566 | 1.753626 | 0.806417 |
| Monthly Dixon-Coles refit | 1.005889 | 0.205736 | 2.932764 | 1.750712 | 0.806219 |

## 1X2 Log Loss by year
| Year | N | M9-class annual BP | Annual Dixon-Coles | Online Poisson EKF | Monthly BP refit | Monthly Dixon-Coles refit |
|---|---|---|---|---|---|---|
| 2024 | 8878 | 1.018661 | 1.015588 | 0.997282 | 1.006734 | 1.004130 |
| 2025 | 9038 | 1.021094 | 1.019631 | 1.011181 | 1.015199 | 1.013205 |
| 2026 | 8128 | 1.008714 | 1.007862 | 0.996913 | 1.000308 | 0.999674 |

## Descriptive league-cluster bootstrap of 1X2 LL gain
Positive gain means the challenger reduces loss. 5,000 seeded resamples of 43 league clusters; ignores higher-order dependence and repeated research selection. Not a production promotion test.
| Comparison | Gain | Improved leagues | Bootstrap 95% |
|---|---|---|---|
| annual_dc_vs_annual_bp | +0.001821 | 34/43 | [+0.000542, +0.003663] |
| dynamic_vs_annual_bp | +0.014411 | 32/43 | [+0.007710, +0.022474] |
| dynamic_vs_annual_dc | +0.012590 | 32/43 | [+0.006235, +0.020212] |
| dynamic_vs_monthly_bp | +0.005676 | 28/43 | [+0.000547, +0.011220] |
| dynamic_vs_monthly_dc | +0.003899 | 28/43 | [-0.000795, +0.008761] |

## Synthetic home Asian handicap five-state Brier
Score states full-win, half-win, push, half-loss, full-loss. These are neutral synthetic lines, not actual Crown quotes.
| Home AH | M9-class annual BP | Annual Dixon-Coles | Online Poisson EKF | Monthly BP refit | Monthly Dixon-Coles refit |
|---|---|---|---|---|---|
| -1.5 | 0.315939 | 0.315759 | 0.314373 | 0.312605 | 0.312511 |
| -1.25 | 0.544257 | 0.544075 | 0.539467 | 0.539707 | 0.539575 |
| -1 | 0.544257 | 0.544075 | 0.539467 | 0.539707 | 0.539575 |
| -0.75 | 0.544257 | 0.544075 | 0.539467 | 0.539707 | 0.539575 |
| -0.5 | 0.442795 | 0.442380 | 0.435197 | 0.437506 | 0.437169 |
| -0.25 | 0.606088 | 0.605483 | 0.598113 | 0.600687 | 0.600270 |
| +0 | 0.606088 | 0.605483 | 0.598113 | 0.600687 | 0.600270 |
| +0.25 | 0.606088 | 0.605483 | 0.598113 | 0.600687 | 0.600270 |
| +0.5 | 0.390701 | 0.390305 | 0.382612 | 0.385982 | 0.385774 |
| +0.75 | 0.447577 | 0.447375 | 0.441873 | 0.443577 | 0.443515 |
| +1 | 0.447577 | 0.447375 | 0.441873 | 0.443577 | 0.443515 |
| +1.25 | 0.447577 | 0.447375 | 0.441873 | 0.443577 | 0.443515 |
| +1.5 | 0.226159 | 0.226143 | 0.223969 | 0.223523 | 0.223606 |

## Interpretation and limitations
- Training and scoring are code-based using latest historical cache; there is no archived truly point-in-time as-of fixture fact source.
- The R62 EKF result becomes eligible for state update only after assumed kickoff+3h, not a verified final-score receipt. This assumed lag is research code, NOT a user-approved rule.
- Annual model versus online model is update cadence confounded; rolling-month models improve comparability but still do not update after each match.
- All EKF variances, process noise, fit cadence, and DC safe-rho projection are exploratory research choices, not formal M9 changes.
- Some individual metrics/years may worsen. The model is a candidate, not yet proven with Crown-market EV or profit.
- 2026 is partial. League-cluster bootstrap is descriptive, not conclusive under complex calendar, within-team, and selection dependencies.
- No official model, TG orders, Crown evidence, formal ledger, or settlement changed.

## Files
Model: dynamic_poisson_ekf_r62.py
Predict CLI: m9_dynamic_forecast_r62.py
Annual model experiment: m9_model_challenger_r61.py
Online model experiment: m9_dynamic_model_r62.py
Rolling control experiment: m9_rolling_baselines_r63.py
Compare/report: m9_challenger_compare_r63.py


## Dynamic EKF mathematical specification

For each fixture, model scoring intensities are:

- home lambda = exp(league home log rate + home attack log strength - away defence log strength)
- away lambda = exp(league away log rate + away attack log strength - home defence log strength)

The 15x15 exact-score grid is the outer product of two conditional Poisson goal distributions, renormalized to the represented 0..14-goal scores. Each team's attack and defence and the league home/away intercept are Gaussian random-walk latent states. The assumed-density EKF update applies the joint two-goal Poisson innovation with observation variance approximated by the predicted scoring intensities. The filter retains diagonal covariance (an approximation), not full cross-team correlation or exact Bayesian posterior inference. This is a new research implementation; **not** a reproduction of the SportsQuant engine.

Research hyperparameters used here: team initial variance 0.20, league-rate initial variance 0.035, team random-walk variance 0.00035/day, league-rate variance 0.000005/day. League scoring-rate priors are empirical averages from games before the first evaluated year, and these earlier games are then assimilated again to produce the starting state (empirical-Bayes-style initialization; not an independent prior dataset). No hyperparameter scan or market-based optimization was performed in this round. These are experimental values, **not user-approved production defaults**. Result updates occur no sooner than a hypothesized 3 hours after kickoff; this is not a verified as-of data receipt time.

## Reproduce and make a research-only forecast

The CLI needs an explicit league ID, home ID, away ID, fixture kickoff, as-of timestamp, and home handicap. Input time strings must share the historical-cache local clock convention; timezone cannot be inferred from the cache. Example retrospective invocation (not a market quote):

    /Users/mac/QuantAsiaDesk/venv/bin/python research/profit_structure_discovery_20261122/m9_dynamic_forecast_r62.py --league 1 --home 6 --away 27 --kickoff 2026-10-10T19:30:00 --as-of 2026-10-07T19:30:00 --home-handicap -0.25

The output includes independent-score 15x15 probabilities, home/draw/away probabilities, expected goals and five possible AH settlement outcomes at the specified synthetic line. It has no odds, EV or order execution. State weights can be saved/restored using to_state_dict/from_state_dict. Checkpoint round-trip, normalized score grid and expected directional goals update were sanity checked.

Compressed anonymized per-fixture scoring evidence is preserved in M9_MODEL_CHALLENGER_R61_EVIDENCE.json.gz, M9_DYNAMIC_MODEL_R62_EVIDENCE.json.gz and M9_ROLLING_BASELINES_R63_EVIDENCE.json.gz. To regenerate this report from saved evidence without live historical-cache access, use M9_COMPARE_EVIDENCE_ONLY=1 when running m9_challenger_compare_r63.py.

## Specific caution on claimed model advantage

The dynamic EKF versus monthly Dixon-Coles 1X2 Log Loss gain is only +0.003899, with exploratory league-cluster bootstrap 95% range [-0.000795,+0.008761], crossing zero. Monthly Dixon-Coles outperforms dynamic EKF on exact-score Log Loss (2.932764 vs 2.945086) and seven-bin margin Brier (0.806219 vs 0.807257). The evidence supports a useful challenge model, **not** a verified overall superior engine or Crown profitability.

## Optional next investigation
Replay actual recorded result-receipt timestamps and paired pre-kickoff Crown quotes for both candidate grids. Then examine AH five-state EV, placed-side differences and settlement ROI as research shadow. No new production gates are assumed.
