#!/usr/bin/env python3
"""Replay saved M1 Crown scan forecasts against the private M5 result archive.

The script never calls a provider or production entrypoint. Output is aggregate
only; fixture IDs, prices, teams, and archived scan payloads are not emitted.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, re, unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def instant(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def settle(market, side, line, price, home, away):
    q = float(line) * 4
    if not math.isfinite(q) or abs(q - round(q)) > 1e-8:
        raise ValueError("line is not a quarter-goal contract")
    q = int(round(q))
    legs = (q,) if q % 2 == 0 else (q - 1, q + 1)
    values = []
    for leg in legs:
        if market == "AH":
            margin = home - away if side == "HOME" else away - home
            signed = 4 * margin + leg
        elif side == "OVER":
            signed = 4 * (home + away) - leg
        elif side == "UNDER":
            signed = leg - 4 * (home + away)
        else:
            raise ValueError("invalid side")
        values.append(1.0 if signed > 0 else -1.0 if signed < 0 else 0.0)
    unit_return = sum(values) / len(values)
    return (price - 1.0) * unit_return if unit_return > 0 else unit_return


def summarize(rows):
    pnl = sum(r["pnl"] for r in rows)
    state = Counter("win" if r["pnl"] > 0 else "push" if r["pnl"] == 0 else "loss" for r in rows)
    equity = peak = max_dd = 0.0
    for row in sorted(rows, key=lambda r: r["decision_utc"]):
        equity += row["pnl"]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    n = len(rows)
    return {"fixtures": n, "net_units": round(pnl, 6), "roi_pct": round(100 * pnl / n, 6) if n else None,
            "max_drawdown_units_by_decision_time": round(max_dd, 6) if n else None,
            "settlement_counts": {k: state[k] for k in ("win", "push", "loss")}}


def run(args):
    manifest_raw = (args.private_dir / "candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    fixtures = {str(row.get("match_id")): row for row in manifest.get("rows", [])
                if row.get("home_goals") is not None and row.get("away_goals") is not None}
    all_rows = defaultdict(list)
    counters = Counter()
    manifest_hashes = []
    scan_manifests = sorted(args.m1_replay_root.glob("*/manifest.json"))
    for manifest_path in scan_manifests:
        manifest_bytes = manifest_path.read_bytes()
        manifest_hashes.append(hashlib.sha256(manifest_bytes).hexdigest())
        scan = json.loads(manifest_bytes)
        scan_root = manifest_path.parent
        for record in scan.get("records", []):
            object_path = (record.get("object_ref") or {}).get("path")
            if not object_path:
                continue
            try:
                payload = json.loads(gzip.open(scan_root / object_path, "rt", encoding="utf-8").read())
            except (OSError, EOFError, ValueError, TypeError):
                counters["invalid_archived_record"] += 1
                continue
            fixture_id = str(payload.get("fixture_id") or "")
            fixture = fixtures.get(fixture_id)
            if not fixture:
                counters["not_in_expanded_fixture_archive"] += 1
                continue
            forecast = payload.get("forecast") or {}
            identity = forecast.get("fixture") or {}
            decision = instant((payload.get("decision_time") or {}).get("__m1_datetime__"))
            kickoff = instant(identity.get("kickoff"))
            fixture_kickoff = instant(fixture.get("kickoff_utc"))
            archived_at = instant(payload.get("captured_at"))
            if (not decision or not kickoff or not archived_at or kickoff != fixture_kickoff
                    or decision >= kickoff or archived_at >= kickoff):
                counters["decision_or_kickoff_mismatch"] += 1
                continue
            if (norm(identity.get("home_name")) != norm(fixture.get("home"))
                    or norm(identity.get("away_name")) != norm(fixture.get("away"))):
                counters["team_identity_mismatch"] += 1
                continue
            home_goals, away_goals = int(fixture["home_goals"]), int(fixture["away_goals"])
            for evaluation in payload.get("market_evaluations", []):
                result = evaluation.get("result") or {}
                market = {"全场让球": "AH", "全场大小球": "OU"}.get(evaluation.get("market"))
                if not market or result.get("source_bookmaker") != "crown" or result.get("source_bookmaker_verified") is not True:
                    continue
                side, direction = result.get("side"), result.get("direction")
                if not side or not direction or result.get("line") is None or result.get("price") is None:
                    counters[f"{market}_no_model_side"] += 1
                    continue
                quote_time = instant(result.get("observed_at"))
                if not quote_time or quote_time > decision or quote_time >= kickoff:
                    counters[f"{market}_quote_time_failure"] += 1
                    continue
                try:
                    price, line = float(result["price"]), float(result["line"])
                    pnl = settle(market, side, line, price, home_goals, away_goals)
                except (ValueError, TypeError, ZeroDivisionError):
                    counters[f"{market}_invalid_contract"] += 1
                    continue
                key = (fixture_id, market)
                all_rows[key].append({"market": market, "decision_utc": decision.isoformat(), "pnl": pnl,
                                      "formal": bool(result.get("formal")), "status": str(result.get("status") or "unknown")})
                counters[f"valid_model_output_{market}"] += 1
    markets = {}
    for market in ("AH", "OU"):
        latest = [max(rows, key=lambda row: row["decision_utc"])
                  for (fixture_id, row_market), rows in all_rows.items() if row_market == market]
        markets[market] = {
            "latest_saved_model_output_per_fixture": summarize(latest),
            "existing_M1_formal_candidate_subset": summarize([row for row in latest if row["formal"]]),
            "scan_status_counts_latest_output": dict(Counter(row["status"] for row in latest)),
        }
    report = {
        "protocol": "M5_M1_SAVED_CROWN_FORECAST_EXPANDED_RESULT_REPLAY_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "m1_replay_manifest_set_sha256": hashlib.sha256("\n".join(sorted(manifest_hashes)).encode()).hexdigest(),
        "archived_scan_count": len(scan_manifests),
        "markets": markets,
        "audit_counts": dict(counters),
        "method": "Exact TotalCorner fixture ID, teams, and UTC kickoff join; latest archived M1 model output per fixture-market; verified Crown price event at/before the recorded M1 decision, with saved scan archive completion also before kickoff; one unit per output; exact Asian quarter-line settlement. Formal subset retains the archived M1 formal flag without introducing any new gate.",
        "limitations": ["This scores saved M1 scans only; it does not retrain or predict all expanded fixtures.",
                        "All-output results include archived forecasts even when M1's own status was outside its formal decision window; statuses are reported separately.",
                        "M1 archives do not separately record Crown response receipt time; pre-kickoff scan archive completion is used as a conservative upper bound on receipt. The expanded result archive itself was collected retrospectively.",
                        "No fixture identifiers, team names, quotes, or scan payloads are included in output."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"generated_utc": report["generated_utc"], "markets": report["markets"],
                      "audit_counts": report["audit_counts"]}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--m1-replay-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
