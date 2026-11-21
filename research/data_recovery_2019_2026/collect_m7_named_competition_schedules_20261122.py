#!/usr/bin/env python3
"""Run the existing resumable TotalCorner schedule collector for newly mapped IDs.

This wrapper changes only the candidate input. It reuses the existing local
collector, 5.2-second spacing, private raw archive, append-only request ledger,
resume logic, and unsafe-job checks.
"""
from __future__ import annotations
import pathlib, sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import collect_supplemental_totalcorner_schedules as collector

collector.CANDIDATES=HERE/'m7_named_competition_schedule_targets_20261122.json'

if __name__=='__main__':
    raise SystemExit(collector.main())
