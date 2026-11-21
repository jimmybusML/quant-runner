#!/usr/bin/env python3
"""Collect the three exact-mapped TotalCorner competitions omitted from the first 35-target run.

Reuses the existing resumable collector, its pacing, private raw archive, append-only request
log, fixture ledger, and scheduled-job safety checks.
"""
from __future__ import annotations
import pathlib, sys
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import collect_supplemental_totalcorner_schedules as collector
collector.CANDIDATES=HERE/'m7_named_competition_schedule_supplemental3_20261122.json'
if __name__=='__main__':
    raise SystemExit(collector.main())
