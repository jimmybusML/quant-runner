#!/usr/bin/env python3
"""Create private, independent M5 score-grid forecasts for upcoming fixtures.

The script reads cached TotalCorner schedule pages and the frozen M5-scope
historical manifest. It never consumes M1/MR1 predictions, prices, orders or
ledgers, and it writes fixture-level forecasts only outside this repository.
It performs no network requests; a separate quote collector can pair later
Crown snapshots only when received after prediction and before kickoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m3.reference.m1_runtime_policy import scope_status
from research.m5.crown_historical_capture import atomic_write, ensure_private_destination, local_to_utc
from research.m5.m5_goal_model_oos import choose_regularization, fit_rates, normalize_identity, predict, read_manifest


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_upcoming(private_dir: Path, zone: ZoneInfo, asof: datetime):
    fixtures = {}
    conflicts = set()
    identity_owner = {}
    for path in (private_dir / "schedules").glob("*/*.json"):
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            payload = envelope.get("payload") or {}
            rows = ((payload.get("data") or {}).get("matches") or [])
            if payload.get("success") != 1:
                continue
        except Exception:
            continue
        for row in rows:
            if not isinstance(row, dict) or scope_status(str(row.get("l") or "")).get("status") != "IN":
                continue
            kickoff = local_to_utc(row.get("start"), zone)
            mid = str(row.get("id") or "")
            home, away = str(row.get("h") or ""), str(row.get("a") or "")
            league = str(row.get("l") or "")
            if not mid or not home or not away or not league or not kickoff or kickoff <= asof:
                continue
            # Only future scheduled fixtures without a recorded final score.
            # TotalCorner schedule pages use literal "0" placeholders for
            # both score cells while a fixture is still in the future.
            if row.get("hg") not in (None, "", 0, "0") or row.get("ag") not in (None, "", 0, "0"):
                continue
            item = {"match_id": mid, "league": league, "home": home, "away": away,
                    "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z")}
            prior = fixtures.get(mid)
            if prior and prior != item:
                conflicts.add(mid)
            else:
                fixtures[mid] = item
            identity = (normalize_identity(league), kickoff.date().isoformat(),
                        normalize_identity(home), normalize_identity(away))
            owner = identity_owner.get(identity)
            if owner is not None and owner != mid:
                conflicts.update((owner, mid))
            else:
                identity_owner[identity] = mid
    for mid in conflicts:
        fixtures.pop(mid, None)
    return sorted(fixtures.values(), key=lambda x: (x["kickoff_utc"], x["match_id"])), len(conflicts)


def run(private_dir: Path, output: Path, source_timezone: str = "Asia/Shanghai"):
    root = ensure_private_destination(private_dir)
    zone = ZoneInfo(source_timezone)
    asof = utc_now()
    manifest_path = root / "candidate-manifest.json"
    manifest_raw, historical = read_manifest(manifest_path)
    historical = [row for row in historical if row["kickoff"] < asof]
    future, identity_conflicts = load_upcoming(root, zone, asof)
    by_league = defaultdict(list)
    for row in historical:
        by_league[row["league"]].append(row)

    grouped_future = defaultdict(list)
    for fixture in future:
        grouped_future[fixture["league"]].append(fixture)
    forecasts, fit_receipts, excluded = [], [], {}
    for league, targets in sorted(grouped_future.items()):
        train = by_league.get(league, [])
        if not train:
            excluded[league] = "no_historical_training_rows"
            continue
        years = sorted({row["year"] for row in train})
        validation_year = max(years)
        penalty, tuning = choose_regularization(train, validation_year)
        model = fit_rates(train, penalty)
        if model["training_end_utc"] >= min(datetime.fromisoformat(x["kickoff_utc"].replace("Z", "+00:00")) for x in targets):
            raise ValueError("training cutoff is not before upcoming target")
        fit_receipts.append({"league": league, "training_fixtures": len(train),
                             "training_end_utc": model["training_end_utc"].isoformat().replace("+00:00", "Z"),
                             "regularization": penalty, "regularization_validation": tuning})
        for fixture in targets:
            prediction = predict(model, fixture["home"], fixture["away"])
            forecasts.append({**fixture, "prediction_asof_utc": asof.isoformat().replace("+00:00", "Z"),
                              "train_end_utc": model["training_end_utc"].isoformat().replace("+00:00", "Z"),
                              "training_fixtures": len(train), "regularization": penalty,
                              "prediction": prediction})

    output_path = output.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if output_path == repo or repo in output_path.parents:
        raise ValueError("fixture-level forecast output must remain outside the public repository")
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_path.parent, 0o700)
    raw = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                  for row in forecasts).encode()
    atomic_write(output_path, raw)
    receipt = {"protocol": "M5_FORWARD_SHADOW_FORECASTS_V1",
               "generated_utc": asof.isoformat().replace("+00:00", "Z"),
               "historical_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
               "forecast_sha256": hashlib.sha256(raw).hexdigest(),
               "forecast_rows": len(forecasts), "future_schedule_rows": len(future),
               "identity_conflicts_excluded": identity_conflicts,
               "leagues_without_training": excluded, "model_fits": fit_receipts,
               "forecast_path": str(output_path),
               "scope_note": "M5-only model fit on prior completed fixtures; upcoming fixture identities/kickoffs only; no M1/MR1 forecasts, odds, orders or ledgers used. Private fixture forecasts must not be committed."}
    receipt_path = output_path.with_suffix(output_path.suffix + ".receipt.json")
    atomic_write(receipt_path, (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"generated_utc": receipt["generated_utc"], "future_schedule_rows": len(future),
                      "forecast_rows": len(forecasts), "identity_conflicts_excluded": identity_conflicts,
                      "leagues_without_training": len(excluded), "forecast_sha256": receipt["forecast_sha256"]},
                     sort_keys=True))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    run(args.private_dir, args.output, args.source_timezone)


if __name__ == "__main__":
    main()
