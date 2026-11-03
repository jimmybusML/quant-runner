#!/usr/bin/env python3
"""Replay the user's existing, confirmed M1 AH EV >=10% exclusion locally.

The public GitHub Runner already applies ops/m1_ah_ev_cap.py before every scan.
This wrapper is idempotent and does not introduce an additional decision gate.
"""
from pathlib import Path
import runpy
import sys
repo = Path(sys.argv[1]).resolve()
source = repo / "m1_live_scan.py"
text = source.read_text(encoding="utf-8")
if 'REJECT_M1_AH_EV_GE_10_PERCENT' in text:
    print("CONFIRMED_M1_EV_POLICY_ALREADY_APPLIED")
else:
    policy = Path(sys.argv[2]).resolve()
    old = Path.cwd()
    import os
    os.chdir(repo)
    try:
        runpy.run_path(str(policy), run_name="__main__")
    finally:
        os.chdir(old)
    after = source.read_text(encoding="utf-8")
    if after.count("REJECT_M1_AH_EV_GE_10_PERCENT") != 1:
        raise RuntimeError("M1 known policy patch could not be verified")
    print("CONFIRMED_M1_EV_POLICY_APPLIED")
