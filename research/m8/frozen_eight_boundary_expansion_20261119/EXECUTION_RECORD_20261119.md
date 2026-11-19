# Execution record — M8 frozen-eight boundary expansion

- Started/finished: 2026-11-19 local run; research data archive as of source coverage cutoff (2026-11-04 for core).
- Repository input commit: `eb61fbe428ce9f341c1aea07a447be7c1ad523f4` (workspace/origin main at start).
- Frozen membership FIDs: 10294; manifest SHA: `6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665`.
- Feature inventory: 39,101 core + 5,842 previously audited expansion rows; 44,943 unique FIDs.
- Commands: `python3 -m py_compile research/m8/m8_frozen_eight_boundary_expansion_20261119.py`; `python3 research/m8/m8_frozen_eight_boundary_expansion_20261119.py`; `python3 research/m8/verify_m8_frozen_eight_boundary_20261119.py`; `python3 research/m8/build_m8_frozen_eight_boundary_report_20261119.py`.
- Reproduction outcome: 68,060 candidate selection rows across 11,357 unique FIDs; independent raw Crown response audit verified all 11,357 FIDs and 68,060 selections with no quote, identity, FT or settlement mismatch.
- Actual-receipt candidate replay: 0 rows because the existing HTTP receipt archive does not provide the compatible T1 path feature horizon. The 50 settled original-eight receipt signals are separately retained as retrospective archive replay.
- Feature join limitation: 76 frozen members lacked the extracted row’s FT/unique-side detail. The independent raw-body audit recovered Crown T1 quote/FT and reproduced frozen PnL for all 10294/10294 members; 591 have side ambiguity because both side cashflows match the frozen outcome. No side was guessed.
- Historical source-event replay is not actual placement, Telegram dispatch, nor independent prospective validation.
- Production models, M9, Telegram, ledger, settlement, collection workflows and rules were not modified by this study.
