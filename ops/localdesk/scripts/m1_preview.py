#!/usr/bin/env python3
"""M1 manual non-TG preview using the unchanged model selector.

The preview has its own durable signal identity and run output; it cannot
consume or mutate the official Telegram signal state.
"""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
preview = root / "state/m1_preview"
preview.mkdir(parents=True, exist_ok=True)
import m1_live_scan as scan

scan.RESULTS = preview
scan.STATE_PATH = preview / "m1_signal_state.json"
result = scan.main()
print(json.dumps({
    "status": result["scan_status"],
    "preview_only": True,
    "telegram_sent": False,
    "new_signals": result["new_signal_count"],
    "candidate_count": result["candidate_count"],
    "errors": result["error_count"],
    "output": str(scan.RESULTS / "latest.json")
}, ensure_ascii=False))
