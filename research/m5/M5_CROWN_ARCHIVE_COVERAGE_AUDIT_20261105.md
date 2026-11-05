# M5 Crown Archive Coverage Audit — 2026-11-05

> **Goal update:** The user restarted M5 on 2026-11-05: keep AH and OU independent, retain at least 10,000 unique real fixtures per market, and consider the return target met if either market reaches sample-out ROI ≥3%. Crown remains preferred; where a market has no Crown quote, TotalCorner (TOTAL) may be reported as its own source. Earlier sections mentioning the retired dual-market >5% objective are historical context only.

This is an aggregate-only audit of an additional local MR1 research archive discovered during M5 coverage review. The source checkout remains read-only. No raw quote, fixture ID, team, token, or private ledger row is copied into the public repository.

## Findings

The archive `mr1-ai-browser-forward/crown-market-benchmark-v26/forward/observations.jsonl` contains 382 browser research records. Only 47 records have the explicit `source_bookmaker=crown` label and both a source quote event timestamp and a local receipt timestamp. All 47 have an AH line and both AH prices, with event time <= receipt time < kickoff. They span four UTC kickoff dates from 2026-10-09 through 2026-10-13. The remaining 335 records have no verified Crown bookmaker label and are excluded.

The schema is AH-only: none of the verified Crown records contains an OU line or paired over/under prices. The archive has 47 unique match IDs. Its saved scope is a browser-capture benchmark and is not a complete historical Crown market archive.

An exact M3 strict-OOS join was attempted using the registered UTC kickoff day and normalized exact home/away names, requiring all three M3 penaltyblog model rows and quote-event <= received < kickoff. It produced zero pairs. The M3 OOS prediction artifact has no matching supported-league predictions on those four dates. This archive therefore adds no valid M3 Crown ROI observations and no OU coverage.

## Existing M5 evidence remains unchanged

The largest usable local Crown historical source remains the verified MR1 V23 snapshot archive. Re-running `m3_crown_exact_line_replay.py` at 2026-11-04T16:36:31Z yielded 121 exact M3 OOS fixtures, Crown AH0 coverage n=24 and OU2.5 coverage n=36. The unchanged small-sample outcomes are AH +5.910U / +24.625% (95% descriptive fixture-bootstrap interval -6.46% to +54.46% in this rerun) and OU -1.660U / -4.611% (-36.06% to +26.83%). These are not evidence for the 10,000-fixture goal or stable positive ROI.

The latest M3 input report describes 13,234 unique season-forward test fixtures across historical periods, but its archived prediction outputs have no Crown price mapping except the small 2026/27 archive overlap above. The 24,347 historical TotalCorner schedule/result IDs previously found in local MR1 batches contain no verified Crown bookmaker identity or timestamped quote snapshots. Ambiguous schedule fields such as `p_asian` and `p_goal` are not treated as Crown prices.

## Collection and authorization boundary

The user confirmed that existing Crown authorization should be reused and instructed us not to seek new authorization. Existing public Actions configuration shows a TotalCorner credential name, but its value was not read. No API request was made in this audit. We also found no public authorization-scope record that independently documents bulk historical extraction permissions. This audit therefore does not establish permission for high-volume historical backfill. Existing saved data has been exhausted for the M3 OOS join attempted here.

For ongoing M3 pairing, the current research capture archive should be treated as a limited prospective AH browser-capture study. To produce independent M3 prospective evidence, a future collector must capture both Crown AH and OU quotes with quote event time, received time, UTC kickoff, exact fixture identity, and an M3 forecast timestamp, and preserve append-only sanitized receipts. No collector is enabled by this report; M1/M2/MR1 production, Telegram, credentials, and trading rules are untouched.

## Status

- Additional verified Crown archive audited: 47 AH fixtures; zero exact M3 strict-OOS joins; zero OU quotes.
- Largest usable existing M3/Crown replay remains AH0 n=24 and OU2.5 n=36.
- Crown historical coverage target of 10,000 fixtures: not met.
- M5 independent AH and OU ROI target: not met.
- API requests, production writes, Telegram writes, and credential reads: zero.

## Existing authorization and forward-capture paths rechecked (2026-11-05)

The public `quant-runner` repository's GitHub Actions secret metadata lists `TOTALCORNER_TOKEN` and `PRIVATE_REPO_TOKEN`; values were not read. The connected GitHub identity can inspect the private `totalcorner-research-bridge`, whose current root has M1/MR1 material but no M5 historical-capture directory or M5 quote archive. This confirms an existing credential path in Actions, but not that the private-repository token grants the needed checkout from a runner, nor does it provide M5's private per-fixture forecast file to that runner.

The public repository already has an M3-specific Crown prospective pairing workflow on a four-hour schedule. Its latest checked run, [41968378899](https://github.com/ljm198964-alt/quant-runner/actions/runs/41968378899), completed successfully at `2026-11-05T04:31:57Z`. The sanitized report generated at `2026-11-05T02:47:28.510865Z` records 18 M3 quote commitments (9 AH, 9 OU), no raw quote values, no EV or ROI, and `formal_order=false` / `telegram_sent=false`. This is M3's prospective archive only; it is not M5 history or an M5 forecast cohort and must not be added to M5 backtest sample counts.

The private M5 TotalCorner capture remains at 300 of 23,812 unique candidate fixtures processed; 298 exact Crown responses yielded 212 fixtures with valid pre-kickoff AH and 212 with valid pre-kickoff OU, with 2 transport errors. The separate 51-league schedule manifest is incomplete: 4,660 of 4,789 known pages saved, 129 missing, 133,140 completed candidates, and `complete_historical_universe=false`. These are local/private progress records, not public quotes or M5 results.

No M5 request was made in this recheck: the machine has no `TOTALCORNER_TOKEN` environment value, and the extant M3 workflow consumes its token only for M3 data. M5's capture/replay requires its private forecast inputs alongside private raw quote responses; the accessible bridge currently does not contain those M5 inputs. Do not treat M3's successful run as M5 automation acceptance, and do not claim the current auth metadata alone makes M5 historical replay runnable in Actions.

## Replay reproducibility confirmation (2026-11-05)

Re-ran the existing private Crown replay against the unchanged local capture and the 127,674-row M5 UTC walk-forward forecast (`research/m5/crown_historical_capture.py replay`). The sanitized output exactly matches the saved [`m5_goal_model_totalcorner_crown_partial.json`](results/m5_goal_model_totalcorner_crown_partial.json) after excluding `generated_utc`; forecast SHA, quote-response hash set, schedule-manifest SHA, fixture counts, settlements, returns, proper scores and drawdowns are identical. The new run generated at `2026-11-05T04:52:46.880043Z`; there was no new source data and therefore no new learning information.

| Market | Unique Crown event-time fixtures | Bets / settled | W / HW / P / HL / L | Net U | ROI | Max DD U |
|---|---:|---:|---|---:|---:|---:|
| AH | 212 | 212 / 212 | 91 / 10 / 22 / 9 / 80 | +5.865 | +2.766509% | 9.620 |
| OU | 212 | 212 / 212 | 88 / 15 / 9 / 19 / 81 | -0.600 | -0.283019% | 16.060 |

These are event-time historical movement backtests: the Crown movement source timestamps precede kickoff, but the API responses and FT data were received after the matches. Keep this cohort separate from contemporaneously received MR1 Crown snapshots. Each market remains below 10,000 unique fixtures, and neither ROI exceeds +5%.

## M5 restart: verified Keychain path and resumed capture (2026-11-05)

The previous credential audit checked environment variables and an incorrect Keychain service name. The existing local maintenance code identifies the credential service as `QuantAsiaDesk.TOTALCORNER_TOKEN`; its Keychain item is present for the current user. The M5 capture was launched by a small in-memory wrapper that passes the credential to the existing TotalCorner client; the value was not printed, written to disk, or committed. No new authorization was requested.

Resumed `crown_historical_capture.py schedules` with the existing private scope file. Its 51 cached page-1 envelopes each reported one current page, so it made zero schedule-page requests and did not repair the older historical page gaps. The separate frozen partial manifest still has 4,660/4,789 known schedule pages and 129 missing; do not treat the 51-page recheck as a complete historical schedule refresh.

The Crown collector then rebuilt its candidate manifest by exact identity against the full M5 UTC annual walk-forward forecast. It found 127,674 common OOS fixture rows, whereas the old checkpoint had been built against a narrower 23,812-row forecast subset. This expands the eligible collection universe; it does not add forecast fixtures or outcomes. The existing capture runs with a 3.1-second minimum interval, Crown-specific `/match/bookmaker_odds` endpoint, 10,000 valid-fixture target separately for AH and OU, and private raw response storage.

At the latest checkpoint (`2026-11-05T05:56:46.930327Z`), the active candidate-set progress was 500 processed (499 exact Crown responses and 1 transport error), with 394 fixtures containing source-time-valid AH and 394 containing source-time-valid OU. The append-only response index has additional older rows outside the expanded candidate set; do not count those as newly processed fixtures. This is collection progress only, not M5 ROI. The progress file updates every 100 processed candidates. The capture handle remained active at this check; wait for its terminal summary before freezing/replaying newly accumulated data.

The existing M3 forward-Crown collector is not reused for M5, and its forecasts/quote commitments are excluded from M5. A separate M5 TotalCorner default `/match/odds` fallback collector has now been added as `research/m5/m5_totalcorner_default_fallback_capture.py` (syntax compilation passed, no requests yet). It waits for the Crown capture's final checkpoint, then queries only already processed and identity-verified Crown response candidates where a market is absent, labels the provider/source as `TotalCorner default` (not Crown), and keeps raw replies private. Its replay still needs implementation after capture results are available. Never merge prices under a Crown label or count a fixture-market twice.

## Follow-up: V26 archive versus M5 historical forecasts (2026-11-05)

A second, local-only audit inspected the existing `market-resolution/latest` rows for the 47 locked Crown observations and the private M5 forecast file. The public V26 `observations.jsonl` is schema-minimal (status, match ID, signal key and first-seen/freeze timestamps); raw resolved quote/fixture payloads remain outside the public repository. The V26 aggregate `summary.json` has 39 settled scoring rows and aggregate Crown observation P&L, but the scored rows contain no quote prices or market lines.

The private quote payloads verified the Crown bookmaker marker and exact fixture identity. All 47 locked observations pass the event / request / receipt sequence with `quote event <= received < kickoff`. Thirty-nine fixtures join by exact match ID and fixture identity to the M5 annual UTC walk-forward forecast and independent post-kickoff FT receipt. On review, the lack of a contemporaneous M5 forecast-generation receipt does not disqualify a historical hindcast: the M5 training cutoff and `prediction_asof_utc` are before the Crown quote and kickoff, and the probabilities can be deterministically reconstructed without the target result. The 39 are valid retrospective M5/Crown AH hindcast observations, but are not archived live M5 signals.

The exact-line replay produced these aggregate results (one 1U bet per unique fixture, no EV gate): M5 on the V26 first-locked Crown quotes, n=39, 8 full wins / 5 half wins / 6 pushes / 3 half losses / 17 losses, -8.985U, ROI -23.038462%, maximum quote-event drawdown 12.695U, settlement log loss 1.16726241 and Brier 0.73294132. The browser AI direction replayed on those same 39 M5-join fixtures and Crown contracts was +9.815U / +25.166667%; this is a small descriptive direction baseline, not an M5 result or formal MR1 model comparison. The V23 later Crown quote for the same 39 fixtures produced M5 -9.475U / -24.294872%. All 39 overlapping V23 quote events are later than their V26 quote events. Consequently V26 adds no new distinct fixture-market to the deduplicated V23 cohort; the union remains AH n=317 (ROI -4.088328%). OU remains V23-only at n=317 and V26 has no OU prices. Do not add the two AH source samples together or treat their different quote times as distinct matches.

The parallel MR1 V6 forward archive has records for 39 of those fixture IDs, but contains only market-fit statuses and selected-side summaries rather than an auditable full score distribution; it is not a substitute M5 forecast. The V26 scored summary omits contract prices/lines, so it cannot independently reproduce the M5 P&L; the private source-verified quote payloads were required for the replay.

Replay code and aggregate receipt: `research/m5/m5_v26_crown_oos_replay.py` and `research/m5/results/m5_v26_crown_oos_replay.json`. Audit source SHA-256 values (local archive only): observations `5d2b236e500c90447274ea0c78123832f6debc6dbb6b3ace136c695da5468db6`, V26 summary `24ad11aad9668aef6c1e425ceb3f0dde71ef7c2d3b40b67e0775dff5db7c5e32`, protocol `a31d541d9ad024530a913ba5de3d985d4fe5fda04386f6109b6f8162ac4dec0b`. No raw quote values, match IDs, teams or credentials were copied into this report. This follow-up made no provider requests or production writes.


## Partial Crown-first event-time replay (2026-11-05)

The aggregate-only replay utility `research/m5/m5_source_union_replay.py` was rerun against the private archive while the Crown backfill continued. At `2026-11-05T06:36:32.097163Z`, 821 unique fixture-markets per market were readable and all selected quotes were Crown (no TOTAL requests had run). UTC kickoff coverage is 2026-10-10 through 2026-11-04. AH was `+18.475U / +2.250305%`; OU was `-63.280U / -7.707674%`. Settled W/HW/P/HL/L: AH 362/35/60/57/307; OU 329/34/44/59/355. Settlement log-loss/Brier: AH 1.00909567/0.63154766; OU 1.00648324/0.63829580. Event-time max drawdown was 23.56U AH and 73.59U OU; descriptive 95% fixture-bootstrap intervals were AH -3.766748% to +8.417783%, OU -13.740560% to -1.699147%. These remain partial retrospective event-time outputs, not final ROI estimates. All 821 provider responses were received after kickoff; source event timestamps alone do not prove pre-kickoff receipt or execution. Source-time event chronology was constrained to M5 prediction as-of <= quote event < kickoff, with forecast train_end < as-of and exact fixture identity/score.

This partial replay does not meet the 10,000 unique fixture target and neither market reaches +3%. The aggregate receipt is published at `results/m5_source_union_replay_partial_20261105.json`; it also includes descriptive-only ROI/profit splits by 49 leagues, UTC kickoff hour, forecast/quote lead-time bins, and line, plus settlement-category probability bins. These are unfiltered diagnostics, not validated gates; most groups are small and only one UTC kickoff year is represented. No per-fixture values are in the public receipt. Re-run after Crown capture has a terminal checkpoint and any TOTAL fallback run is complete, then publish the final aggregate result with source-stratified counts.


## 2026-11-05T18:18Z checkpoint refresh

The append-only private capture checkpoint advanced to 9,500 of 127,674 candidate fixtures processed at `2026-11-05T18:18:35.319520Z`; 9,444 exact responses, 56 transport errors, 8,532 AH and 8,532 OU fixtures with valid Crown quotes, and zero schedule identity/time mismatches. The collector remained active and no terminal `finished_utc` was present.

The aggregate event-time replay generated at `2026-11-05T18:19:34.971591Z` contains 8,542 unique fixtures per market. AH: -139.660U, -1.634980% ROI, 172.935U max drawdown, settlement LL/Brier 1.03356792/0.64981503. OU: -348.350U, -4.078085%, 351.850U, LL/Brier 0.98967251/0.62473892. Quote events precede kickoff but all 8,542 API receipts per market followed kickoff. Thus these prices are not receipt-verified pregame quotes and these figures are retrospective simulations only. Report [`replay receipt`](results/m5_source_union_replay_partial_20261105T181934Z.json).

The temporal holdout receipt generated `2026-11-05T18:21:53.154620Z` uses 6,266 train and 2,295 holdout fixtures per market with disjoint identities and a `2026-09-01T00:00:00Z` cutoff. It fits independent global home/away rate offsets from prior goals (1.035343 / 1.031832) without ROI optimization. Calibration improves proper scores, but holdout ROI is AH -0.204793% and OU -3.901961%; raw controls are +0.244009% and -4.723965%. All quote API receipts are post-kickoff. This is a temporal model diagnostic, not a pregame executable backtest. Report [`temporal holdout receipt`](results/m5_crown_goal_rate_temporal_holdout_20261105T182153Z.json).


### Append-only response index replay refresh (2026-11-05T18:28Z)

While the collector remained active, a read-only replay observed newer response files than the last `quote-progress.json` checkpoint. The generated aggregate at `2026-11-05T18:25:36.570072Z` covered 8,596 Crown fixtures per market: AH -139.980U/-1.628432%, LL/Brier 1.03297664/0.64940953; OU -348.570U/-4.055026%, LL/Brier 0.98905515/0.62437528. Six records lacked valid receipt timestamps. All included responses arrived after kickoff. See [`replay receipt`](results/m5_source_union_replay_partial_20261105T182536Z.json).

The refreshed `2026-09-01 UTC` temporal holdout generated at `2026-11-05T18:28:06.718136Z` has 6,318 training and 2,295 holdout fixture-markets per market with disjoint IDs. Calibrated ROI is AH -0.162092%, OU -3.810022%; all API receipts remain post-kickoff. This snapshot remains below the 10,000 target and is not executable ROI evidence. See [`holdout receipt`](results/m5_crown_goal_rate_temporal_holdout_20261105T182806Z.json).


### 9,700-candidate checkpoint refresh

At `2026-11-05T18:33:56Z`, the private progress record shows 9,700/127,674 candidates, 9,643 exact responses, 57 transport errors, 8,724 eligible quotes per market and no fixture identity/time mismatch. Collector remains active. The append-only index replay has 8,733/market; AH -1.717795%, OU -4.065556%. Two bad receipt rows were omitted and all included API receipts were post-kickoff. The updated fixed-cutoff calibration uses 6,454 train / 2,295 holdout per market (disjoint), with AH +0.001743% and OU -3.813508% calibrated ROI, still all post-kickoff receipts. Aggregate receipts: [replay](results/m5_source_union_replay_partial_20261105T183456Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T183708Z.json).


### 9,800-candidate Crown checkpoint

At `2026-11-05T18:43:58Z`, 9,800/127,674 candidates were processed, 9,742 exact responses, 58 transport errors, 8,818 eligible AH and OU quotes, and zero identity/time mismatch. Collector remained active, with no terminal receipt. The latest append-only replay (`2026-11-05T18:44:47Z`) has 8,825 fixture-markets per side: AH -1.749348%, OU -3.968159%; 14 invalid receipt-time rows omitted; every remaining response receipt followed kickoff. The refreshed temporal holdout (`2026-11-05T18:46:59Z`) has 6,562 train / 2,295 disjoint holdout per market; calibrated AH +0.220044%, OU -3.894118%, with every receipt post-kickoff. Aggregate receipts: [replay](results/m5_source_union_replay_partial_20261105T184447Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T184659Z.json).


### 9,900-candidate Crown checkpoint

At `2026-11-05T18:51:05Z`: 9,900/127,674 candidates processed, 9,841 exact responses, 59 transport errors, 8,914 eligible AH/OU quotes and no identity/time mismatches. Active collector had no terminal receipt. Response-index replay at `2026-11-05T18:52:23Z` yielded 8,919 fixtures/market; AH -1.754008%, OU -3.779852%; eight invalid receipt timestamps excluded, all remaining API receipts post-kickoff. The temporal holdout generated `2026-11-05T18:54:37Z` uses 6,640/2,295 disjoint train/holdout per market; calibrated AH +0.220479%, OU -3.893246%, with post-kickoff receipts. Receipts: [replay](results/m5_source_union_replay_partial_20261105T185223Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T185437Z.json).


### 10,000-candidate checkpoint (candidate count is not quote count)

The Crown progress record at `2026-11-05T18:59:55Z` processed 10,000/127,674 candidates and had 9,008 valid AH/OU quotes. The fresh response-index replay at `2026-11-05T19:00:47Z` has 9,015 settled fixture-markets per side after 14 invalid receipt-time exclusions: AH -1.795286%, OU -3.768164%. All API receipts remain post-kickoff. Fixed-cutoff calibration at `2026-11-05T19:03:05Z`: 6,746 train / 2,295 disjoint holdout per market; calibrated AH +0.220044%, OU -3.977778%, also with post-kickoff receipts. No 10,000 sample milestone or ROI target achieved. Receipts: [replay](results/m5_source_union_replay_partial_20261105T190047Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T190305Z.json).


### 10,100-candidate Crown checkpoint

At `2026-11-05T19:08:34Z`: 10,100 processed, 10,040 exact responses, 60 transport errors, 9,105 valid quotes per market, zero identity/time mismatches. Response replay at `2026-11-05T19:09:26Z`: 9,108 fixture-markets per side; AH -1.847003%, OU -3.629941%; six receipt-time-invalid rows excluded, all remaining responses after kickoff. Fixed temporal holdout at `2026-11-05T19:11:40Z`: 6,827 train / 2,295 disjoint holdout per market; calibrated AH +0.057952%, OU -3.975599%; all holdout receipts post-kickoff. Receipts: [replay](results/m5_source_union_replay_partial_20261105T190926Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T191140Z.json).


### 10,200-candidate Crown checkpoint

At `2026-11-05T19:15:50Z`: 10,200 candidates, 10,140 exact responses, 60 transport errors, 9,204 valid quote fixtures per market, zero identity/time mismatches. Response-index replay at `2026-11-05T19:17:42Z` includes 9,217 per market; AH -1.784800%, OU -3.286427%; two invalid receipt-time records excluded and all other receipts post-kickoff. Temporal holdout at `2026-11-05T19:19:58Z`: 6,931 train / 2,295 disjoint test per market; calibrated AH +0.220479%, OU -4.142484%; all receipts post-kickoff. Receipts: [replay](results/m5_source_union_replay_partial_20261105T191742Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T191958Z.json).


### 10,300-candidate Crown checkpoint

At `2026-11-05T19:26:36Z`, 10,300 candidates, 10,239 exact responses, 61 transport errors, 9,302 valid quotes per market and zero fixture identity/time mismatch. Replay `2026-11-05T19:27:19Z` includes 9,293 per market (33 from 2025, 9,260 from 2026). AH -1.775369%, OU -3.398902%; 14 bad receipt-time rows excluded, all other API receipts post-kickoff. Temporal holdout `2026-11-05T19:29:35Z`: 7,032 train / 2,295 disjoint holdout per side, calibrated AH +0.263399%, OU -4.061874%, all receipts post-kickoff. Receipts: [replay](results/m5_source_union_replay_partial_20261105T192719Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T192935Z.json).


### 10,400-candidate Crown checkpoint

At `2026-11-05T19:32:57Z`: 10,400 candidates processed; 10,339 exact responses; 61 transport errors; 9,393 valid quotes per market; zero identity/time mismatches. Replay at `2026-11-05T19:34:16Z` includes 9,387 per side (127 UTC-2025 and 9,260 UTC-2026), AH -1.881485%, OU -3.341217%; two invalid receipt timestamps omitted and all included responses post-kickoff. Time holdout at `2026-11-05T19:36:32Z` has 7,103 AH / 7,102 OU train and 2,295 holdout per market, disjoint; calibrated AH +0.218083%, OU -4.025708%; all holdout receipts post-kickoff. Receipts: [replay](results/m5_source_union_replay_partial_20261105T193416Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T193632Z.json).


### 10,500-candidate Crown checkpoint

At `2026-11-05T19:41:57Z`: 10,500 processed, 10,439 exact responses, 61 transport errors, 9,477 valid quotes per market, no identity/time mismatches. Event-time replay `2026-11-05T19:43:24Z` has AH 9,470 / OU 9,469 (one invalid/missing OU receipt), so not yet 10,000. AH -1.806072%, OU -3.269089%; every included API receipt is post-kickoff. Holdout `2026-11-05T19:45:41Z`: 7,188 AH / 7,187 OU train and 2,295 disjoint holdout each; calibrated AH +0.117865%, OU -3.931373%; receipts after kickoff. See [replay](results/m5_source_union_replay_partial_20261105T194324Z.json) and [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T194541Z.json).


### 10,600-candidate Crown checkpoint

At `2026-11-05T19:54:27Z`: 10,600 candidates; 10,538 exact responses; 62 transport errors; 9,555 valid quotes per market; identity/time mismatches 0. Replay `2026-11-05T19:56:01Z`: AH 9,551 / OU 9,550; AH -1.964559%, OU -3.217120%. Fourteen invalid timestamps excluded; all selected API receipts post-kickoff. Holdout `2026-11-05T19:58:17Z`: train 7,281 AH / 7,280 OU, holdout 2,295 each; calibrated AH +0.052941%, OU -3.843355%, with all receipts after kickoff. Receipts [replay](results/m5_source_union_replay_partial_20261105T195601Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T195817Z.json).


### 10,700-candidate Crown checkpoint

At `2026-11-05T20:00:12Z`: 10,700 candidates, 10,638 exact responses, 62 transport errors, 9,635 valid quotes per market, identity/time mismatch 0. Replay `2026-11-05T20:01:49Z` has AH n=9,636 / OU n=9,635, AH -1.942767%, OU -3.384587%; eight invalid response timestamps omitted, all remaining receipt times after kickoff. Holdout `2026-11-05T20:04:11Z`: 7,359/7,358 train and 2,295 disjoint holdout per side; calibrated AH +0.077996%, OU -3.930501%; all API receipts post-kickoff. Receipts [replay](results/m5_source_union_replay_partial_20261105T200149Z.json), [holdout](results/m5_crown_goal_rate_temporal_holdout_20261105T200411Z.json).
