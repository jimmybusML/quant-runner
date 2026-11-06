#!/usr/bin/env python3
"""Create a sanitized receipt for a refreshed forward Crown quote batch."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def instant(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def read_unique(path: Path, key_fields: tuple[str, ...]) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    rows = {}
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = tuple(str(row[field]) for field in key_fields)
        if key in rows:
            raise ValueError("duplicate private row key")
        rows[key] = row
    return raw, rows


def build_receipt(forecast_path: Path, target_path: Path, capture_path: Path,
                  old_pair_path: Path, old_pair_meta_path: Path,
                  new_pair_path: Path, new_pair_meta_path: Path) -> dict:
    forecast_raw, forecasts = read_unique(forecast_path, ("match_id",))
    target_raw, targets = read_unique(target_path, ("match_id",))
    old_pair_raw, old_pairs = read_unique(old_pair_path, ("match_id", "market"))
    new_pair_raw, new_pairs = read_unique(new_pair_path, ("match_id", "market"))
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    old_meta = json.loads(old_pair_meta_path.read_text(encoding="utf-8"))
    new_meta = json.loads(new_pair_meta_path.read_text(encoding="utf-8"))

    forecast_sha = hashlib.sha256(forecast_raw).hexdigest()
    if old_meta.get("pair_sha256") != hashlib.sha256(old_pair_raw).hexdigest():
        raise ValueError("old pair digest mismatch")
    if new_meta.get("pair_sha256") != hashlib.sha256(new_pair_raw).hexdigest():
        raise ValueError("new pair digest mismatch")
    if new_meta.get("forecast_sha256") != forecast_sha:
        raise ValueError("new pair does not reference frozen forecast batch")
    if capture.get("forecast_sha256") != hashlib.sha256(target_raw).hexdigest():
        raise ValueError("capture does not reference target subset")

    target_asof_match = 0
    for key, target in targets.items():
        original = forecasts.get(key)
        if not original or any(target.get(field) != original.get(field) for field in
                               ("prediction_asof_utc", "train_end_utc", "kickoff_utc", "home", "away", "league")):
            raise ValueError("refresh target does not match frozen forecast identity/time")
        target_asof_match += 1
    capture_time = instant(capture.get("generated_utc"))
    if not capture_time:
        raise ValueError("invalid capture time")
    future_targets = sum(instant(row.get("kickoff_utc")) > capture_time for row in targets.values())
    if capture.get("attempted_fixtures") != future_targets:
        raise ValueError("attempted capture count differs from future target count")

    source_counts = {m: Counter() for m in ("AH", "OU")}
    kickoff = {m: [] for m in ("AH", "OU")}
    for key, row in new_pairs.items():
        market = row.get("market")
        if market not in source_counts or row.get("source") not in ("Crown", "TotalCorner_default"):
            raise ValueError("invalid pair market/source")
        train_end, asof = instant(row.get("train_end_utc")), instant(row.get("prediction_asof_utc"))
        event, received, ko = (instant(row.get(name)) for name in
                               ("quote_event_utc", "quote_received_utc", "kickoff_utc"))
        if not (train_end and asof and event and received and ko and train_end < asof <= event <= received < ko):
            raise ValueError("invalid pair chronology")
        source_counts[market][row["source"]] += 1
        kickoff[market].append(ko)

    common = set(old_pairs) & set(new_pairs)
    changed = Counter()
    field_labels = {"quote_event_utc": "quote_event_time_changed",
                    "quote_received_utc": "receipt_time_changed",
                    "line": "line_changed", "prices": "odds_pair_changed",
                    "source": "source_changed"}
    for key in common:
        old, new = old_pairs[key], new_pairs[key]
        for field in ("quote_event_utc", "quote_received_utc", "line", "prices", "source"):
            if old.get(field) != new.get(field):
                changed[field_labels[field]] += 1

    paired_by_market = {m: sum(1 for row in new_pairs.values() if row["market"] == m)
                        for m in ("AH", "OU")}
    if {m: n for m, n in paired_by_market.items() if n} != new_meta.get("paired_fixture_markets"):
        raise ValueError("new pair count receipt mismatch")
    if len(new_pairs) != new_meta.get("paired_rows"):
        raise ValueError("new pair row receipt mismatch")

    return {
        "protocol": "M5_FORWARD_SHADOW_REFRESH_COMPARISON_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "capture_generated_utc": capture["generated_utc"],
        "forecast_sha256": forecast_sha,
        "refresh_target_sha256": hashlib.sha256(target_raw).hexdigest(),
        "refresh_target_fixtures": len(targets),
        "refresh_targets_matching_frozen_forecast": target_asof_match,
        "capture_receipt_sha256": digest(capture_path),
        "capture_attempted_fixtures": capture["attempted_fixtures"],
        "capture_aggregate_counts": capture.get("aggregate_counts", {}),
        "old_pair_sha256": hashlib.sha256(old_pair_raw).hexdigest(),
        "new_pair_sha256": hashlib.sha256(new_pair_raw).hexdigest(),
        "new_unique_fixture_markets": len(new_pairs),
        "new_fixture_markets_by_market": paired_by_market,
        "new_source_fixture_markets": {m: dict(sorted(source_counts[m].items())) for m in ("AH", "OU")},
        "compared_fixture_markets": len(common),
        "added_fixture_markets": len(set(new_pairs) - set(old_pairs)),
        "removed_fixture_markets": len(set(old_pairs) - set(new_pairs)),
        "changed_quote_fields_on_common_fixture_markets": dict(sorted(changed.items())),
        "kickoff_coverage_utc": {
            m: [min(kickoff[m]).isoformat().replace("+00:00", "Z"),
                max(kickoff[m]).isoformat().replace("+00:00", "Z")] if kickoff[m] else [None, None]
            for m in ("AH", "OU")},
        "timing": "Every paired quote event and actual response receipt preceded kickoff; all targets match the frozen M5 forecast times.",
        "roi_pct": None,
        "privacy": "Aggregate counts and hashes only; fixture identities, team names, lines, prices, score grids and raw responses remain private.",
    }


def main():
    p = argparse.ArgumentParser()
    for arg in ("forecast", "targets", "capture", "old-pairs", "old-pair-meta",
                "new-pairs", "new-pair-meta", "output"):
        p.add_argument(f"--{arg}", type=Path, required=True)
    a = p.parse_args()
    report = build_receipt(a.forecast, a.targets, a.capture, a.old_pairs,
                           a.old_pair_meta, a.new_pairs, a.new_pair_meta)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("generated_utc", "capture_attempted_fixtures",
        "capture_aggregate_counts", "new_fixture_markets_by_market", "added_fixture_markets",
        "changed_quote_fields_on_common_fixture_markets")}, sort_keys=True))


if __name__ == "__main__":
    main()
