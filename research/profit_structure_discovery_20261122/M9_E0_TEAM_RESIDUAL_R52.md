# R52 | E0 team-level attribution of true historical forecast-residual correction

## Scope

Independent M3 penaltyblog bivariate OOS 1X2 historical predictions. The true residual is observed points minus model-predicted expected points, computed only from two prior seasons. Not a formal M9 replay, not a full score-grid adjustment, not Crown AH ROI.

## Held-out season results

| Season | N | Mean 1X2 log-loss improvement | Exploratory match bootstrap 95% interval | Fixtures with team unseen in two-year calibration |
|---|---:|---:|---:|---:|
| 2324 | 342 | +0.006692 | [-0.002661, +0.016494] | 70 |
| 2425 | 342 | +0.033869 | [+0.020947, +0.046645] | 0 |
| 2526 | 342 | +0.017872 | [+0.006056, +0.030368] | 36 |
| 2627 | 81 | +0.026349 | [+0.000031, +0.052626] | 17 |

Overall E0: 1107 matches, log-loss improvement +0.019980; match-level bootstrap 95% interval [+0.013574, +0.026339].

## Team attribution

Each fixture improvement is allocated 50/50 to both participating teams. This is descriptive attribution, not team causal effect or a trading signal.

| Team | Fixtures | Attributed sum improvement | Seasons improved / observed |
|---|---:|---:|---:|
| Tottenham | 117 | +2.937 | 4/4 |
| Arsenal | 116 | +2.416 | 4/4 |
| Leicester | 36 | +2.366 | 1/1 |
| Newcastle | 116 | +1.922 | 4/4 |
| Wolves | 108 | +1.577 | 3/3 |
| Aston Villa | 117 | +1.550 | 4/4 |
| Brighton | 117 | +1.490 | 4/4 |
| Fulham | 116 | +1.455 | 3/4 |
| Nott'm Forest | 117 | +1.431 | 4/4 |
| Burnley | 72 | +1.154 | 2/2 |
| Man City | 117 | +1.065 | 3/4 |
| Southampton | 36 | +1.064 | 1/1 |
| West Ham | 108 | +0.690 | 2/3 |
| Bournemouth | 118 | +0.662 | 2/4 |
| Leeds | 46 | +0.322 | 2/2 |
| Sheffield United | 36 | +0.205 | 1/1 |
| Chelsea | 117 | +0.201 | 2/4 |
| Man United | 117 | +0.162 | 3/4 |
| Crystal Palace | 118 | +0.149 | 2/4 |
| Sunderland | 9 | +0.119 | 1/1 |
| Ipswich | 9 | -0.055 | 0/1 |
| Brentford | 117 | -0.087 | 2/4 |
| Liverpool | 118 | -0.115 | 2/4 |
| Everton | 116 | -0.562 | 1/4 |

## Interpretation

E0 improvement is not confined to a single season or a single team. Some clubs contribute negatively. Unseen/promoted teams have no previous-team residual and therefore receive zero direct correction, while their opponent may still be adjusted.

## Caveats
- R50 independent M3 season-forward model, not M9 production; score-grid and Crown AH unavailable.
- Per-team gains allocate shared match gains 50/50, not an independent team effect.
- Team residuals are observed from prior two seasons, with promoted teams potentially absent.
- This analysis reuses R50 data, not an independent replication.
- Match-level IID bootstrap 4000 replicates is exploratory and ignores fixture/team/time dependence; not a formal proof of persistent edge.

## Proposed next research (not new rules)

- Check per-team forecast residual persistence across consecutive prior seasons, with team promotions and name continuity explicit.
- Fit M9 actual bivariate score grids using strictly earlier model forecast-error residuals and evaluate held-out AH lines and five-state settlement with timestamp-valid Crown odds.
- Preserve production M9, Telegram, and ledgers unchanged.
