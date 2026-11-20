# Execution record — M8 referee card tendency

- Research date: 2026-11-20.
- Public baseline: current `origin/main` at branch base `36cedce` (`Persist M3 immutable event segment(s)`).
- Scope: Crown AH only; historical replay. No Crown API request, production workflow, Telegram dispatch, formal ledger write, or M8/M1/MR1/M9/collector change.
- Hypothesis differs from R48 team-card features by estimating historical referee×competition home-away card imbalance. Target referee identity comes from a retrospective Transfermarkt archive without verified pregame assignment time.

## Commands actually completed

```text
python3 -m py_compile research/m8/referee_card_tendency_20261120/run_referee_card_tendency.py
python3 research/m8/referee_card_tendency_20261120/run_referee_card_tendency.py
python3 -m py_compile research/m8/referee_card_tendency_20261120/verify_referee_card_tendency.py
python3 research/m8/referee_card_tendency_20261120/verify_referee_card_tendency.py
python3 research/m8/referee_card_tendency_20261120/write_sha256_manifest.py
```

The read-only verifier was rerun during continuation on 2026-11-20; it returned `pass=true`, 14,289/14,289 historical card source hashes verified, 6,685 unique target FIDs, 40,110 independently recomputed model settlements, and zero discrepancies. The verifier's inherited identity-bridge prefix also printed diagnostics for 172 auxiliary records (157 without two time windows and 15 assertion mismatches); those diagnostics are outside the card source index and test ledger. The card study's own final audit recorded no errors.

## Observed results

- Read-only inventory: 91,816 Crown raw historical response files; 14,289 unique records mapped one-to-one to competition/team/FT/referee and complete nonnegative home/away yellow/red counts; 675 referee-competition pairs. There were no duplicate or conflicting mapped FIDs.
- Existing Crown T1 paths: 39,101 FIDs. Existing score archive: 40,277 rows. Mapped target referee rows: 10,908; 2024–2026 pregame-path/FT target rows: 7,081. At least one observed same-referee prior card record covered 6,685 test FIDs, including 5,200 outside frozen membership. MR1 receipt intersection: zero.
- Six methods used the same 5,200 incremental FIDs. Candidate net U: low-price −148.970; market Ridge −229.290; market+yellow −210.940; market+red −225.005; market+yellow+red −222.290; card-tendency-only −29.045. All candidate ROIs were negative. Cross-year results are retained in the report/JSON.
- The independently computed original eight-group target-period baseline was 6,873 FIDs/+197.765U. After de-duplication, merged unique FIDs numbered 12,073; merge results do not convert losing candidates into profitable sources.
- Independent verifier: 14,289/14,289 Crown card source-body SHA and identity/FT/card rows matched; 6,685 × 6 = 40,110 AH settlement rows and feature leakage checks passed with zero errors. The 6,685 targets are a subset of 7,081 fixtures already independently raw-verified for Crown T1, paired odds, identity, and FT in the separate referee-residual audit.

## Limitations and publication

The target official's pregame assignment timestamp is missing and no MR1 real-receipt FID overlaps this feature/model cohort. Quotes are historical Crown source-event prices retrieved later, not proof of contemporaneous receipt or execution. This remains a failed research mechanism, not production behavior. Publication is recorded in `PROJECT_HANDOFF.md`.
