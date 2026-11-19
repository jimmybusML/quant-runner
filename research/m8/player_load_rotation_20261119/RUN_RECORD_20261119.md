# M8 Player Load / Rotation Run Record

All timestamps UTC. Research only; no production process or network collector was invoked.

| Time | Command | Exit | Result |
|---|---|---:|---|
| 2026-11-19 10:13 | `python3 research/m8/m8_player_load_rotation_crown_20261119.py` | 0 | 6,986 complete feature rows; 3,520 test FIDs; 49,280 model-market predictions; 2,805 unique FIDs outside frozen eight. |
| 2026-11-19 10:28 | `python3 research/m8/verify_m8_player_load_rotation_settlement_20261119.py` | 0 | 3,421 FIDs independently reconciled from original Crown body/FT; 99 lack a locatable raw body; 12,550 receipt body SHA and 12,550 snapshot SHA checks passed; no settlement or quote mismatch. |

The run reused local M8/Crown and TotalCorner-derived files. It made no HTTP requests. Exact source and output hashes are recorded in `EXECUTION_MANIFEST_20261119.json`; detailed result and limitations are in `M8_PLAYER_LOAD_ROTATION_RESEARCH_20261119.md`.
