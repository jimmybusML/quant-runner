# M3 independent OOS run report — 2026-11-06

This report summarizes GitHub Actions run [42132022252](https://github.com/ljm198964-alt/quant-runner/actions/runs/42132022252), executed from source commit `abe3324b00dc3738206b53d23fcf78692ad5f484`. The workflow completed successfully and wrote immutable per-run reports, split definitions, predictions, and parameter snapshots under `research/m3/results/history/42132022252-1/`. The workflow-generated result commit is `6320cf03f990421562cf127585e55ca8dc9f8cdb`.

## Data and time separation

The upstream Football Predictor V4 run read 60 Football-Data.co.uk CSV files covering six leagues: Belgium B1 (2,655 usable matches), Germany D1 (2,826), England E0 (3,510), France F1 (3,178), Italy I1 (3,520), and Spain SP1 (3,529). They contain 19,218 usable results across seasons 2017/18–2026/27. The input changed versus the previous snapshot (`data_changed_vs_previous_snapshot=true`); this run therefore added new source observations.

The penaltyblog run tested 17,152 season-forward matches and produced 14,807 scored predictions per model (86.33% coverage). It fit 162 fold models across Poisson, Dixon–Coles, and bivariate Poisson. For each league/season fold, training rows came from earlier season files and had UTC match dates strictly earlier than the first test-season match date. Since the source provides date-only values, each date is represented at UTC midnight and the entire first test date is excluded from training. The public report records exact split ranges, row counts, input hashes, test-set hash, and prediction hash. No bookmaker columns were read in the penaltyblog process.

The prior saved run had one fewer test fixture and a different test-set fingerprint. The comparison artifact therefore records the difference but leaves metric deltas null; this update is not presented as a same-sample model improvement.

## AH results

The tested AH diagnostic is home AH 0.0 / DNB as a three-state win/push/lose probability forecast. It has no Crown line or Crown price linkage, so ROI, profit, and drawdown are not applicable.

| Penaltyblog model | OOS predictions | Log loss | Brier |
|---|---:|---:|---:|
| Poisson | 14,807 | 1.003886 | 0.599398 |
| Dixon–Coles | 14,807 | 1.003791 | 0.599230 |
| Bivariate Poisson | 14,807 | 1.003779 | 0.599253 |

Across nine scored test seasons per model, season-level AH log loss ranged 0.956459–1.017919 and Brier ranged 0.565952–0.608272, depending on model. The latest partial 2026/27 slice had 478 predictions per model; AH log loss/Brier were 0.956459/0.565952 (Poisson), 0.958164/0.567286 (Dixon–Coles), and 0.956675/0.566131 (bivariate Poisson). These are probabilistic DNB diagnostics, not Crown ROI.

## OU results

Penaltyblog OU is fixed O2.5. It also has no Crown line or price linkage, so Crown ROI remains null.

| Penaltyblog model | OOS predictions | Log loss | Brier |
|---|---:|---:|---:|
| Poisson | 14,807 | 0.686555 | 0.246554 |
| Dixon–Coles | 14,807 | 0.686577 | 0.246564 |
| Bivariate Poisson | 14,807 | 0.686578 | 0.246577 |

Across nine scored test seasons per model, season-level OU log loss ranged 0.678845–0.698381 and Brier ranged 0.242975–0.251906. On the latest partial 2026/27 slice (478 predictions per model), OU log loss/Brier were 0.680384/0.243894 (Poisson), 0.680398/0.243899 (Dixon–Coles), and 0.681268/0.244329 (bivariate Poisson). Model differences are small and no model was promoted.

## Original Football Predictor V4 OU comparison

The workflow also reran the upstream V4 walk-forward implementation, preserving its original feature engineering and market-based variants. The table below aggregates its six test-season folds (2021/22–2026/27, including a partial current season); log loss and Brier are weighted by test rows. “Pooled author ROI” is reconstructed only from the upstream's own simulated bets and thresholds in the source dataset. It is not Crown ROI and none of these thresholds was copied into M3.

| V4 OU model | Test rows | Log loss | Brier | Upstream simulated bets | Pooled author ROI | Folds with bets / positive ROI |
|---|---:|---:|---:|---:|---:|---:|
| Logistic | 10,813 | 0.682737 | 0.244849 | 923 | -4.37% | 4 / 0 |
| LightGBM | 10,813 | 0.682621 | 0.244821 | 1,114 | -6.30% | 4 / 1 |
| Market-anchored Logistic | 10,812 | 0.681246 | 0.244130 | 2,584 | -7.07% | 5 / 0 |
| Market-residual Logistic | 10,812 | 0.672180 | 0.239744 | 909 | -12.47% | 2 / 0 |
| Market-blend Logistic | 10,812 | 0.672309 | 0.239790 | 563 | -7.31% | 2 / 0 |

The author-threshold backtests are season-sensitive: only LightGBM had a positive bet-producing fold, while all five pooled author ROIs were negative. Several folds produced no bets. This report keeps those simulations separate from Crown results and does not turn the upstream threshold into a new M3 gate.

## Crown coverage and limits

The M3 penaltyblog report explicitly records `crown_roi: null`; it used no bookmaker prices. The latest successful M3 Crown Forward Pairing run found on this audit is [42109348334](https://github.com/ljm198964-alt/quant-runner/actions/runs/42109348334), generated UTC `2026-11-05T21:07:44.614642Z`. Its public value-free receipt is `results/crown/latest_forward_capture_report.json`; it reports 30 cumulative commitments (15 AH, 15 OU), 0 added in that run because the forecast input fingerprint (`8c981e167261b2f6ae9d3ae424d131ee6987e091a2ab5a45f05af895283ca9d5`) had not changed, 43 schedule identities missing or ambiguous, and no persisted quote values/raw response. EV and ROI remain null, and the run records no new learning information. Separately, the M5 direct Crown-only probe on its frozen cohort had 355 identity-verified responses, but all 626 valid AH and 529 valid OU event rows predated the frozen forecast as-of; it yielded zero qualifying M5 Crown fixture-markets. These data are not mixed across models.

No model promotion, M1/M2/MR1 production change, formal order, Telegram message, Crown ROI claim, or new trading gate occurred. The M3 OOS model evaluation and automation are working, but a forward Crown quote/forecast/settlement cohort large enough for price-based validation remains outstanding.

Verification after the Actions run: all 75 existing M3 unit tests passed locally with penaltyblog 1.13.1; the two new M5 Crown collector/pairing unit tests passed; an independent UTC check of all 44,421 scored M3 prediction rows found 0 cases where `train_end_utc >= match_date_utc`; and `git diff --check` passed.

## Artifacts

- Full penaltyblog report and dataset hashes: `results/history/42132022252-1/penaltyblog_oos_report.json`
- Exact chronological split manifest: `results/history/42132022252-1/penaltyblog_oos_splits.json`
- Upstream V4 per-season metrics: `results/history/42132022252-1/original_v4_metrics.csv`
- V4, penaltyblog, and prior-run comparison: `results/history/42132022252-1/penaltyblog_comparison.json`
- Hash-addressed prediction and parameter artifacts are named in `results/history/42132022252-1/receipt.json`.
