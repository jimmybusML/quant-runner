# Execution record — M8 discipline × referee interaction

## Scope and controls

- Study directory only: `research/m8/referee_discipline_interaction_20261121/`.
- Read-only inputs from QuantAsiaDesk cached M8/Crown research; no collection or production workflow invoked.
- Frozen eight-group membership remains 10,294 FIDs, input SHA256 `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`.
- No changes to M8 frozen rules, M1/MR1/M9, production models, Telegram, official ledger, collection chain or schedule.

## Commands actually run

1. `python3 -m py_compile research/m8/referee_discipline_interaction_20261121/run_referee_discipline_interaction.py`
2. `python3 research/m8/referee_discipline_interaction_20261121/run_referee_discipline_interaction.py`
3. `python3 research/m8/referee_discipline_interaction_20261121/verify_referee_discipline_interaction.py`
4. `python3 research/m8/referee_market_residual_20261120/verify_referee_research.py`
5. Final manifest generation and file/hash validation (recorded in SHA256 manifest).

The first attempt used a fixed 2019–2023 training window for every test fold. Inspection caught the mismatch with the requested time-forward design. That output was discarded. The script was corrected to train 2019 through the year before each test fold, and the complete run and independent settlement verification were repeated. The final folds are 2019–2023 for 2024, 2019–2024 for 2025, and 2019–2025 for 2026. The corrected run also makes the published PR #69 referee residual equality a hard assertion.

## Final observed execution

- Mapped retrospective referee + FT panel: 10,908; common referee/discipline feature cohort: 10,602.
- Prediction rows: 6,847 unique FIDs × six fixed model variants = 41,082 detailed results.
- 2024–2026 outside-frozen candidate pool: 5,316 unique FIDs; overlap with frozen membership: 0.
- Independent validator: 41,082 AH settlement rows recomputed; summary comparisons, same-period and full-frozen-union reconciliation, FID/FT/quote bridge, freeze membership, uniqueness and history cutoff assertions passed.
- Existing PR #69 raw-response audit rerun: 7,081/7,081 original Crown raw response SHA, FID, FT and T1 contract rows passed; all 6,847 FIDs in this study align with that audited panel.
- Actual pre-kickoff Crown-receipt overlap: 0. Verified pregame referee appointment timestamps: 0.
- Formal orders: 0; official ledger writes: 0; production changes: none.

## Result

The interaction candidate produced −179.315U/−3.373% ROI over 5,316 outside-frozen FIDs, MDD 185.440U, 40.273 orders/week over the 132-week calendar span (123 active ISO weeks), and negative net U in 2024, 2025 and 2026 through May 24. No new profitable mechanism was demonstrated. The full report explains same-period and full-frozen-union accounting and all comparison variants.

## Input SHA256

The full input set is recorded in `referee_discipline_interaction_summary_20261121.json`. Key identity and pricing inputs:

- Crown T1 path: `f21d4d49621df503efdb607b72b08882c1f1365c3178cce13e696d9aad4b697e`
- score/FT bridge: `e8cf152c821725139b5492746faa32fe46889886c3971878ee9cb6473e3662f8`
- frozen membership: `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`
- Crown SQLite: `7401078708d56a122987fde6231ae4b8cf296020d7fae54048437e73462c8a3f`
- published PR #69 referee ledger: recorded in summary JSON.

## Execution boundary

This was historical event-time research. No live quote was replaced by a source-event quote and no research output was represented as a Telegram/live order or official ledger entry.

## Publication

- Public repository: `jimmybusML/quant-runner`.
- Research branch: `research/m8-referee-residual-20261120`.
- Commit: `fa0307b0aba545b243eb9363124ba4a6603f683a`.
- PR #69: https://github.com/jimmybusML/quant-runner/pull/69, confirmed OPEN and not merged; remote branch SHA checked against the commit above.
