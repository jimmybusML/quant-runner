# Bivariate-Poisson vs Crown AH timing; Codex short-window review (2026-11-21)

**Status:** research-only historical replay and read-only Codex audit. **Not** approved trading rules, not formal Telegram orders, not proof of live executable edge. This report supplements `PROJECT_HANDOFF.md` without changing any earlier user-approved rule. M8 original eight groups and all M1/MR1/M9/production/collector/scheduler/settlement paths remain unchanged.

## Data/method

- 49 approved leagues; 2024 Aug–Dec (4,749 AH FIDs), 2025 Aug–Dec (4,749), 2026 Jan–May (3,702): **13,200 unique FIDs per model**.
- Two isolated BivariatePoissonGoalModel variants, `monthly_unweighted` and `monthly_365d`; only past-calendar-month training results, same fitted model for T0/6/12/24 quote comparisons. Each bet remains 1U. Historical Crown market quotes were recovered after the event; price source-event timestamps precede kickoff but **HTTP receipt at the historical time is not established**. No formal records counted.
- From `m8_early_joint_market_inventory_20261115.jsonl`: Crown as-of checkpoints T−6h / T−12h / T−24h; 12,973 / 12,650 / 11,905 common FIDs (per model). Median actual source-event lead at T−6h = 6.804h, T−12h = 14.218h, T−24h = 36.223h.
- Side chosen from AH two directions at neutral decimal 2.00, then Crown *actual selected-side* odds used to report model EV and settle. Separately calculated counterfactual side chosen by the **two actual quoted odds**; that counterfactual did not produce positive aggregate ROI.
- T0 refit/selection/EV/settlement independently matched the three existing historical-order files **26,400/26,400, 0 mismatches**. Result per-fixture dataset: 101,456 rows across variants/checkpoints.

## Three approved research directions: findings

### 1. Market-conditioned calibration / score-state

At T−6h, on each variant's 12,973 FIDs, average predicted vs realized full-win/full-loss outcome rates:

| Variant | predicted full win | actual full win | predicted full loss | actual full loss |
|---|---:|---:|---:|---:|
| Unweighted | 48.725% | 39.921% | 31.656% | 39.490% |
| 365d weight | 48.188% | 39.821% | 32.108% | 39.590% |

Mean model EV at T−6h: +13.113% / +12.119%; realized ROI −3.266% / −3.595%. This demonstrates systematic **selected-side optimism** but cannot uniquely identify whether the cause is underlying score distribution, selection on noisy model differences, or missing pregame information. Other state probabilities and odds/line-level aggregations are preserved in the local summary.

### 2. Model-versus-market disagreement

Two-side equal-stake same-FID baseline at T−6h = −3.201% ROI. Unweighted choice −3.266% (−0.064 percentage points versus baseline), weighted −3.595% (−0.394). Neutral-price model side versus maximizing model EV at both **actual** Crown odds:

| Model | T−6h neutral-side ROI | T−6h actual-price-max-side ROI |
|---|---:|---:|
| Unweighted | −3.266% | −3.856% |
| Weighted | −3.595% | −3.359% |

Hence merely changing EV valuation of two sides does not resolve the lack of net market edge. This baseline is a 50/50 selection comparator, not a professional market forecasting model.

### 3. Time dimension / early-quote robustness

| AH cohort reselected at **each** quote checkpoint | Near-kickoff retrospective | T−6h historical replay |
|---|---:|---:|
| Unweighted, EV 45–50% | 164 FIDs, +10.817% ROI | 139 FIDs, −3.331% |
| Weighted, EV 40–45% | 232 FIDs, +11.509% ROI | 177 FIDs, −2.983% |

At T−6h, unweighted 45–50% 2024/25/26 ROI = −7.750% / +1.761% / +4.033% (78/46/15 orders). Weighted 40–45% 2024/25/26 = +3.427% / −7.490% / −20.560% (103/49/25).
Only 41/157 (26.11%) of T0 45–50% unweighted candidates with T−6h evidence remain in that bin at T−6h; weighted 54/223 (24.22%). This is conditional **signal-persistence** assessment, not an executable filter. The T0 and T−6h EV-bin cohorts differ, so their ROI must not be compared as if same orders.

All-cohort unweighted T0/6/12/24 ROI: −2.656%, −3.266%, −3.019%, −2.275%; weighted: −3.719%, −3.595%, −3.853%, −2.948%. None profitable all-cohort.

## Separate Codex short-window review

Read current **unmerged** PR [#69](https://github.com/jimmybusML/quant-runner/pull/69) source and Mac Codex worktree `research/m8-referee-residual-20261120`, plus independent cross-league PR [#67](https://github.com/jimmybusML/quant-runner/pull/67). These are **different methods and cohorts**, not to be added to any formal ledger or counted as M8-original profit.

Independent **outside-frozen-eight** historical results:

| Codex candidate | 2024 U | 2025 U | 2026 U | Overall U | Overall N |
|---|---:|---:|---:|---:|---:|
| Original49 pair-only | −23.040 | −39.750 | −28.090 | −90.880 | 4,383 |
| Expanded15 Crown + pair | no eligible rows | +7.740 | no eligible rows | +7.740 | 309 |
| Formation-only | −3.245 | +44.735 | −57.485 | −15.995 | 6,571 |
| Discipline-only | +35.170 | −13.910 | −10.505 | +10.755 | 5,316 |

Expanded15 pair has no 2024/26 feature-complete test; no true target receipt and no immutable first-publication timestamp for lineup. Formation-only actual pre-kick receipt cohort outside frozen = 218 FIDs / −21.220U (−9.734%); formation source capped 2026-07-06 whereas receipt dates 2026 Oct–Nov; do not interpret this as contemporaneous lineup data. Discipline-only outperformed its **same-FID market-only forced-side model** by +114.240/+91.005/+48.100U in 2024/25/26, despite 2025/26 standalone losses; this comparative result may contain signal, but the baseline itself loses heavily and is not a positive trading edge. Original49 pair-only three years negative.

**Weekly profit concentration (diagnostic, not a rule):** formation-only 2025 +44.735U total, five best active weeks +68.440U, remaining weeks −23.705U; discipline-only 2025 −13.910U total, five best +56.015U, remaining −69.925U. Selecting profitable weeks after seeing results is look-ahead/selection bias. The prior eight-group frozen profits must not be added to candidate performance when making an incremental-edge claim.

Cross-league exact-rule replay in PR67: 1,160 historical incremental FIDs +10.890U overall, but 2024 +7.890U, 2025 −0.390U, 2026 −5.160U, and zero true receipt coverage; no cross-year reproducible edge. PR68 has a different expanded cohort (1,271 FIDs, +7.185U over its span); do **not** silently reconcile counts or treat them as identical experiments.

## Interpretation / optional future research (NOT user-approved rules)

1. Optional: score-state calibration conditional on AH line/odds and objective model-versus-Crown residual; any calibration fit should be evaluated without using its target period outcomes.
2. Optional: investigate whether the discipline-only feature adds genuine information to a **market-matched** baseline across years and with independent price receipts; the published referee-containing cohort's pregame assignment timing is not verified.
3. Optional: study short-lived changes in information quality or market regime with forward-known predictors, not by looking up which historic weeks won.
4. Optional: compare T−6h+ historical replay with prospectively received quotes before considering any real-world executability. **No new EV gates, volume caps, release gates, or automatic Codex promotion were introduced.**

## Reproduction and evidence on authorized Mac

Research root: `/Users/mac/QuantAsiaDesk/research-work/`. Private raw Crown/FT inputs are **not** in this public GitHub report.

- `independent_bivariate_t6_market_disagreement_20261121.py` SHA256 `1fe72cad5792671444e26f182c1d4ee630cb07eb51c1e3a83a10acd98e527f85`
- `independent_bivariate_t6_market_disagreement_20261121.jsonl` SHA256 `98cebc139e55aba1b1981fe07e067061f005ac7e2e328656f023767370dc8c10`
- `independent_bivariate_t6_market_summary_20261121.json` SHA256 `2bb7a5f122722897e0eec75aedd3fea2e8c99ab47a1267ef593d3f9f658ee00b`
- `codex_short_window_audit_20261121.json` SHA256 `824eeebfdc56d455565bde91e462f5bf422e570a0913a28332a4821e33e27596`

**Actual operations:** read-only replay and Codex-source analysis, generated local research ledgers and summaries, zero code changes to production, zero workflow triggers, zero Telegram formal orders, zero formal ledger writes, zero changes to approved M8/M9/M1/MR1 strategies. Evidence does not prove future positive OOS ROI or executable trading performance.
