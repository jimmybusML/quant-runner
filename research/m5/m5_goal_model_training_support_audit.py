#!/usr/bin/env python3
"""Aggregate M5 OOS scores by prior training support, without row identifiers."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


SUPPORT_BINS = ((0, 19), (20, 49), (50, 99), (100, 249), (250, 10**12))


def run(forecasts: Path, output: Path) -> dict:
    raw = forecasts.read_bytes()
    groups = defaultdict(lambda: defaultdict(float))
    seen = set()
    min_training = None
    max_training = 0
    for line in raw.decode("utf-8").splitlines():
        row = json.loads(line)
        match_id = str(row["match_id"])
        if match_id in seen:
            raise ValueError("duplicate fixture ID in OOS forecast file")
        seen.add(match_id)
        count = int(row["training_fixtures"])
        lo, hi = next((a, b) for a, b in SUPPORT_BINS if a <= count <= b)
        name = f"{lo}-{hi}" if hi < 10**12 else f"{lo}+"
        pred = row["prediction"]
        hg, ag = int(row["home_goals"]), int(row["away_goals"])
        outcome = 0 if hg > ag else 1 if hg == ag else 2
        probs = [float(pred[k]) for k in ("p_home", "p_draw", "p_away")]
        over_p = min(max(float(pred["p_over_2_5"]), 1e-12), 1 - 1e-12)
        over = int(hg + ag > 2.5)
        score_p = max(float(pred["grid"][hg][ag]), 1e-12) if max(hg, ag) < len(pred["grid"]) else 1e-12
        acc = groups[name]
        acc["fixtures"] += 1
        acc["ah_log_loss"] += -math.log(max(probs[outcome], 1e-12))
        acc["ah_brier"] += sum((p - int(i == outcome)) ** 2 for i, p in enumerate(probs))
        acc["ou_log_loss"] += -(over * math.log(over_p) + (1 - over) * math.log(1 - over_p))
        acc["ou_brier"] += (over_p - over) ** 2
        acc["exact_score_log_loss"] += -math.log(score_p)
        min_training = count if min_training is None else min(min_training, count)
        max_training = max(max_training, count)
    results = {}
    for name, acc in groups.items():
        n = int(acc.pop("fixtures"))
        results[name] = {"fixtures": n, **{k: round(v / n, 8) for k, v in acc.items()}}
    report = {
        "protocol": "M5_OOS_TRAINING_SUPPORT_SCORE_AUDIT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_sha256": hashlib.sha256(raw).hexdigest(),
        "unique_forecast_fixtures": len(seen),
        "minimum_training_fixtures": min_training,
        "maximum_training_fixtures": max_training,
        "support_bins": results,
        "interpretation": "Post-hoc descriptive score audit only. Bins are not betting filters, model selection criteria, or independent ROI evidence.",
        "ah_definition": "Three-way 1X2 probability proxy; not Asian handicap contract settlement.",
        "crown_prices_used": False,
        "ROI": None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "unique_forecast_fixtures": len(seen), "support_bins": results}, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.forecasts, args.output)


if __name__ == "__main__":
    main()
