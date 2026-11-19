#!/usr/bin/env python3
"""Audit whether source-event freshness predicts AH side returns on true Crown receipts.

Research-only and deliberately descriptive: no bet-selection rule is created.
Only real pregame HTTP receipt rows from the independently audited M8 archive
are used. Source-event time is kept distinct from HTTP receipt and kickoff.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl"
OUT = Path(__file__).resolve().parent


def timestamp(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def settle(line: float, odds: float, gd: int) -> tuple[float, str]:
    q = round(line * 4) / 4
    if abs(q * 2 - round(q * 2)) < 1e-9:
        legs = [q]
    else:
        legs = [math.floor(q * 2) / 2, math.ceil(q * 2) / 2]
    returns = []
    for leg in legs:
        m = gd + leg
        returns.append(odds - 1 if m > 0 else (-1.0 if m < 0 else 0.0))
    pnl = sum(returns) / len(returns)
    state = "full_loss" if pnl <= -0.999999 else (
        "half_loss" if pnl < -1e-9 else ("push" if abs(pnl) < 1e-9 else (
            "half_win" if pnl < odds - 1 - 1e-8 else "full_win")))
    return pnl, state


def stats(rows, key):
    vals = [float(x[key]) for x in rows]
    days = collections.defaultdict(float)
    weeks = collections.defaultdict(lambda: [0, 0.0])
    for x in rows:
        d = dt.date.fromisoformat(x["date"])
        days[d.isoformat()] += float(x[key])
        y, w, _ = d.isocalendar()
        a = weeks[f"{y}-W{w:02d}"]
        a[0] += 1
        a[1] += float(x[key])
    eq = high = dd = 0.0
    for day in sorted(days):
        eq += days[day]
        high = max(high, eq)
        dd = max(dd, high-eq)
    return {
        "n": len(rows),
        "net_u": round(sum(vals), 6),
        "roi_pct": round(100*sum(vals)/len(vals), 6) if rows else None,
        "max_drawdown_u": round(dd, 6),
        "weeks": {w: {"n": v[0], "net_u": round(v[1], 6)} for w,v in sorted(weeks.items())},
    }


def main():
    by_fid = {}
    for line in INPUT.open():
        r = json.loads(line)
        # E is used only as a stable row carrier; all methods share the exact
        # same actual receipt quote and FT. The direction is reconstructed here.
        if r["method"] != "E_discrete_AH_contract_calibration":
            continue
        assert r["source_type"] == "actual_http_receipt"
        assert r.get("raw_sha256") and r.get("snapshot_sha256")
        by_fid[r["fid"]] = r
    rows = []
    for fid, r in sorted(by_fid.items()):
        received = timestamp(r["received_utc"])
        source = timestamp(r["AH_source_event_utc"])
        kickoff = timestamp(r["kickoff_utc"])
        hg, ag = map(int, r["ft"].split("-"))
        age_min = (received-source).total_seconds()/60
        assert received < kickoff, fid
        assert age_min >= 0, fid
        line = float(r["line_home"])
        # The favorite is defined from the Crown signed AH line; at pk, the
        # lower decimal price is used as a descriptive priced-favorite proxy.
        if line < 0:
            fav = "home"
        elif line > 0:
            fav = "away"
        else:
            fav = "home" if float(r["odds_home"]) <= float(r["odds_away"]) else "away"
        dog = "away" if fav == "home" else "home"
        sides = {}
        for side in ("home", "away"):
            odds = float(r[f"odds_{side}"])
            gd = hg-ag if side == "home" else ag-hg
            p, state = settle(line if side == "home" else -line, odds, gd)
            sides[side] = {"pnl_u": round(p, 6), "state": state}
        if r.get("audit_pnl_u") is not None:
            assert abs(sides[r["side"]]["pnl_u"]-float(r["audit_pnl_u"])) < 1e-6, fid
        age_bin = "00_15m" if age_min < 15 else ("15_60m" if age_min < 60 else ("1_6h" if age_min < 360 else "6h_plus"))
        horizon_min = (kickoff-received).total_seconds()/60
        horizon_bin = "00_15m" if horizon_min < 15 else ("15_60m" if horizon_min < 60 else ("1_6h" if horizon_min < 360 else "6h_plus"))
        rows.append({
            "fid": fid, "date": r["date"], "kickoff_utc": r["kickoff_utc"],
            "received_utc": r["received_utc"], "source_event_utc": r["AH_source_event_utc"],
            "source_age_minutes": round(age_min, 6), "received_minutes_to_kickoff": round(horizon_min, 6),
            "source_age_bin": age_bin, "receipt_horizon_bin": horizon_bin,
            "line_home": line, "odds_home": r["odds_home"], "odds_away": r["odds_away"],
            "favorite_side_by_handicap": fav, "home_pnl_u": sides["home"]["pnl_u"],
            "away_pnl_u": sides["away"]["pnl_u"], "favorite_pnl_u": sides[fav]["pnl_u"],
            "underdog_pnl_u": sides[dog]["pnl_u"], "favorite_state": sides[fav]["state"],
            "underdog_state": sides[dog]["state"], "ft": r["ft"],
            "source_type": r["source_type"], "raw_sha256": r["raw_sha256"],
            "snapshot_sha256": r["snapshot_sha256"], "FT_source": r["FT_source"],
            "foundation_overlap": bool(r["foundation_overlap"]),
        })
    assert len(rows) == 1230, len(rows)
    # Fixed source-age intervals describe freshness. They are not a candidate
    # betting filter. Receipt-horizon intervals are included as a confound check.
    summary = {
        "scope": "unique actual pregame Crown HTTP receipts among the audited 1,230-FID archive",
        "research_only": True,
        "not_a_trade_gate": True,
        "receipt_rows": len(rows),
        "unique_fids": len({x["fid"] for x in rows}),
        "date_range": [min(x["date"] for x in rows), max(x["date"] for x in rows)],
        "source_age_min_median_max_minutes": [
            round(min(x["source_age_minutes"] for x in rows), 3),
            round(sorted(x["source_age_minutes"] for x in rows)[len(rows)//2], 3),
            round(max(x["source_age_minutes"] for x in rows), 3),
        ],
        "source_age_freshness_bins": {},
        "all_receipt_side_benchmarks": {},
        "posthoc_outside_frozen_eight": {},
        "receipt_horizon_sensitivity_bins": {},
        "method": "Crown AH actual received quote and verified FT; both sides independently settled with quarter-lines; side summaries are diagnostics, not selected trades",
        "input_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        "limits": [
            "One 2026 six-week receipt cohort; no multi-year real-receipt validation.",
            "Receipt-time snapshots are not proof of actual execution or fill.",
            "Source event age is common to both sides and does not itself identify which side is mispriced.",
            "Age-bin outcomes are descriptive and were examined after the results were known; no threshold is promoted.",
        ],
    }
    for b in ("00_15m", "15_60m", "1_6h", "6h_plus"):
        subset = [x for x in rows if x["source_age_bin"] == b]
        summary["source_age_freshness_bins"][b] = {
            "fids": len(subset),
            "favorite_side": stats(subset, "favorite_pnl_u"),
            "underdog_side": stats(subset, "underdog_pnl_u"),
        }
        outside = [x for x in subset if not x["foundation_overlap"]]
        summary["posthoc_outside_frozen_eight"][b] = {
            "fids": len(outside),
            "favorite_side": stats(outside, "favorite_pnl_u"),
            "underdog_side": stats(outside, "underdog_pnl_u"),
            "membership_note": "retrospective FID attribution only; T12 did not know future frozen-eight membership",
        }
    summary["all_receipt_side_benchmarks"] = {
        "favorite_side": stats(rows, "favorite_pnl_u"),
        "underdog_side": stats(rows, "underdog_pnl_u"),
    }
    outside_all = [x for x in rows if not x["foundation_overlap"]]
    summary["posthoc_outside_frozen_eight_all"] = {
        "fids": len(outside_all),
        "favorite_side": stats(outside_all, "favorite_pnl_u"),
        "underdog_side": stats(outside_all, "underdog_pnl_u"),
        "membership_note": "retrospective FID attribution only; T12 did not know future frozen-eight membership",
    }
    for b in ("00_15m", "15_60m", "1_6h", "6h_plus"):
        subset = [x for x in rows if x["receipt_horizon_bin"] == b]
        summary["receipt_horizon_sensitivity_bins"][b] = {
            "fids": len(subset),
            "favorite_side": stats(subset, "favorite_pnl_u"),
            "underdog_side": stats(subset, "underdog_pnl_u"),
        }
    with (OUT/"receipt_quote_freshness_fixtures.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":"))+"\n")
    (OUT/"receipt_quote_freshness_results.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("source_age_freshness_bins","receipt_horizon_sensitivity_bins")}, indent=2))
    print("source_age_freshness_bins:")
    print(json.dumps(summary["source_age_freshness_bins"], indent=2))
    print("posthoc_outside_frozen_eight:")
    print(json.dumps(summary["posthoc_outside_frozen_eight"], indent=2))
    print("receipt_horizon_sensitivity_bins:")
    print(json.dumps(summary["receipt_horizon_sensitivity_bins"], indent=2))


if __name__ == "__main__":
    main()
