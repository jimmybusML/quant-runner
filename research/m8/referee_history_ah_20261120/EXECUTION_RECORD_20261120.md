# Execution record — M8 referee-history AH study

- Execution date: 2026-11-20 (Asia/Shanghai).
- Repository branch: `research/m8-exact-cross-league-expansion`.
- Working-tree starting state: the research branch was clean except for this new study directory; no other user modifications were present.
- Main command: `python3 research/m8/referee_history_ah_20261120/m8_referee_history_ah_20261120.py` — exit 0; 38,846 paired Crown T24/T12 historical FIDs read; 12,851 referee joins; 6,967 forward-test FIDs, of which 5,467 are outside frozen M8.
- Independent verification command: `python3 research/m8/referee_history_ah_20261120/verify_referee_history_ah_20261120.py` — exit 0; 27,868 Crown/FT identity checks, independent AH settlement checks and side-selection checks passed; no duplicate FIDs within model; frozen overlap 1,500 and outside-eight unique FIDs 5,467.
- Report command: `python3 research/m8/referee_history_ah_20261120/build_referee_history_report_20261120.py` — exit 0.
- Main outcome: REF_ONLY −170.705U / −3.122%; CROWN_PLUS_REF −79.745U / −1.459%; Crown-only on same candidate FIDs −27.770U / −0.508%; same-FID lower-price side −290.930U / −5.322%. The referee assignment source has no publication/receipt timestamps, actual-receipt target FID intersection is zero, and no live referee-information result is available.
- Historical source-event replay only. No production models, original-eight membership, Telegram, formal ledger, Crown collection workflow, or scheduler changed. No formal order was placed and no ledger write occurred.
- Inputs are local authorized research files and were not copied into the public repository. The gzip ledger and outputs contain research results only; no raw private HTTP response body or credentials are included.
- Machine-readable input/output hashes: `SHA256SUMS_20261120.txt`.
