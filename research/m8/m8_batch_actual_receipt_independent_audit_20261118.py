#!/usr/bin/env python3
"""Independent AH settlement and receipt-time audit for the batch replay."""
import collections, datetime as dt, hashlib, json, math
from pathlib import Path

BASE = Path("/Users/mac/QuantAsiaDesk/research-work")
HERE = Path(__file__).resolve().parent
COVERAGE = BASE / "m8_independent_receipt_coverage_20261115.jsonl"
ARCHIVE = BASE / "m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl"
FOUNDATION = BASE / "m8_foundation_20261115/historical_membership.jsonl"
INPUTS = [
    HERE / "m8_batch_E_discrete_AH_contract_calibration_actual_receipt_orders_20261118.jsonl",
    HERE / "m8_batch_F_async_Crown_market_updates_actual_receipt_orders_20261118.jsonl",
    HERE / "m8_batch_H_team_contract_position_residual_actual_receipt_orders_20261118.jsonl",
]
OUT_ROWS = HERE / "m8_batch_actual_receipt_independently_audited_20261118.jsonl"
OUT = HERE / "m8_batch_actual_receipt_independent_audit_20261118.json"


def read(path):
    return [json.loads(s) for s in path.open() if s.strip()]


def settle(line_home, odds, side, home_goals, away_goals):
    # Recompute AH settlement independently from stored pnl fields. A quarter
    # line is an equal 0.5U split between its neighboring half-goal lines.
    ticks = round(line_home * 4)
    if abs(line_home * 4 - ticks) > 1e-7:
        raise ValueError(f"unsupported AH line: {line_home}")
    if ticks % 2:
        legs = [math.floor(line_home * 2) / 2, math.floor(line_home * 2) / 2 + 0.5]
    else:
        legs = [line_home, line_home]
    profit = 0.0
    for home_line in legs:
        margin = home_goals - away_goals + home_line
        if side == "away":
            margin = -margin
        if margin > 1e-9:
            profit += 0.5 * (odds - 1)
        elif margin < -1e-9:
            profit -= 0.5
    return round(profit, 6)


def summarize(rows):
    if not rows:
        return {"orders": 0, "net_u": 0.0, "roi_pct": None, "weekly_orders_avg": None,
                "weeks_elapsed": 0, "max_drawdown_daily_close_u": 0.0,
                "wins": 0, "half_wins": 0, "pushes": 0, "half_losses": 0, "losses": 0}
    day = collections.defaultdict(float)
    week = collections.Counter()
    total = 0.0
    outcome = collections.Counter()
    for r in rows:
        d = dt.date.fromisoformat(r["date"])
        total += r["audit_pnl_u"]
        day[r["date"]] += r["audit_pnl_u"]
        y, w, _ = d.isocalendar()
        week[(y, w)] += 1
        p = r["audit_pnl_u"]
        if abs(p) < 1e-9: outcome["pushes"] += 1
        elif p >= 0.99: outcome["wins"] += 1
        elif p > 0: outcome["half_wins"] += 1
        elif p <= -0.99: outcome["losses"] += 1
        else: outcome["half_losses"] += 1
    dates = sorted(day)
    bal = peak = mdd = 0.0
    for d in dates:
        bal += day[d]
        peak = max(peak, bal)
        mdd = max(mdd, peak - bal)
    first = dt.date.fromisoformat(dates[0])
    last = dt.date.fromisoformat(dates[-1])
    weeks_elapsed = ((last - dt.timedelta(days=last.weekday())) -
                     (first - dt.timedelta(days=first.weekday()))).days // 7 + 1
    return {"orders": len(rows), "net_u": round(total, 6),
            "roi_pct": round(total / len(rows) * 100, 6),
            "weekly_orders_avg": round(len(rows) / weeks_elapsed, 6),
            "weeks_elapsed": weeks_elapsed, "active_weeks": len(week),
            "max_drawdown_daily_close_u": round(mdd, 6), **outcome,
            "weekly": [{"iso_year": y, "iso_week": w, "orders": week[(y, w)]}
                       for y, w in sorted(week)]}


coverage = {str(r["fid"]): r for r in read(COVERAGE)
            if r.get("verified_receipt") and r.get("FT") is not None and
            not r.get("FT_error") and r.get("kickoff_utc")}
archive = {}
for r in read(ARCHIVE):
    archive[(str(r["fixture_id"]), r["received_utc"])] = r
foundation = {str(r["fid"]): r for r in read(FOUNDATION)}

audited = []
errors = collections.Counter()
snapshot_checks = 0
used_receipt_fids = set()
for path in INPUTS:
    for row in read(path):
        fid = str(row["fid"])
        cov = coverage.get(fid)
        if not cov:
            errors["missing_verified_FT"] += 1
            continue
        # Match the exact stored HTTP receipt; it may be T12, T18, or another
        # verified pre-kickoff horizon. Do not relabel it as a T12 snapshot.
        rec = archive.get((fid, row.get("received_utc") or cov["receipt_utc"]))
        if not rec:
            errors["missing_exact_archive_receipt"] += 1
            continue
        ah = rec.get("markets", {}).get("AH") or {}
        price = (ah.get("odds") or {})
        if (abs(float(ah.get("line")) - float(row["line_home"])) > 1e-9 or
                abs(float(price.get("home")) - float(row["odds_home"])) > 1e-9 or
                abs(float(price.get("away")) - float(row["odds_away"])) > 1e-9):
            errors["Crown_line_or_odds_mismatch"] += 1
            continue
        kickoff = dt.datetime.fromisoformat(rec["kickoff_utc"].replace("Z", "+00:00"))
        received = dt.datetime.fromisoformat(rec["received_utc"].replace("Z", "+00:00"))
        if received >= kickoff:
            errors["receipt_not_before_kickoff"] += 1
            continue
        horizon = str(rec.get("snapshot_horizon") or row.get("nominal_horizon") or "")
        snap = BASE.parent / "repos/mr1/data/prospective-market/shadow-v23/snapshots" / fid / horizon / "snapshot.json"
        if snap.exists():
            snapshot_checks += 1
            if hashlib.sha256(snap.read_bytes()).hexdigest() != rec["snapshot_sha256"]:
                errors["snapshot_sha256_mismatch"] += 1
                continue
        else:
            errors["missing_snapshot_file"] += 1
            continue
        side = row["side"]
        bet_price = float(price[side])
        hg, ag = map(int, cov["FT"])
        pnl = settle(float(ah["line"]), bet_price, side, hg, ag)
        enriched = dict(row)
        enriched.update({"signal_time_utc": rec["received_utc"],
                         "verified_receipt_horizon": horizon,
                         "cutoff_time_utc": row.get("signal_time_utc"),
                         "source_event_utc": ah.get("source_event_utc"),
                         "raw_sha256": rec["raw_sha256"],
                         "snapshot_sha256": rec["snapshot_sha256"],
                         "ft": f"{hg}-{ag}", "ft_source": cov["FT_source"],
                         "audit_pnl_u": pnl,
                         "original_pnl_u": float(row["pnl_u"]),
                         "foundation_overlap": fid in foundation})
        if abs(pnl - float(row["pnl_u"])) > 1e-6:
            errors["settlement_mismatch_vs_batch"] += 1
        audited.append(enriched)
        used_receipt_fids.add(fid)

by_method = collections.defaultdict(list)
for r in audited:
    by_method[r["method"]].append(r)
method_results = {}
for method, rows in sorted(by_method.items()):
    distinct = {r["fid"]: r for r in rows}
    unique_rows = list(distinct.values())
    incremental = [r for r in unique_rows if not r["foundation_overlap"]]
    method_results[method] = {
        "actual_verified_receipt_sample": summarize(unique_rows),
        "actual_verified_receipt_increment_outside_frozen_eight": summarize(incremental),
        "unique_fids": len(distinct),
        "foundation_overlap_fids": len(distinct) - len({r["fid"] for r in incremental}),
    }

# Foundation plus each actual-receipt method is reported separately; these are
# not pooled across methods, because their candidate sides can conflict.
foundation_by_year = collections.defaultdict(list)
for fid, r in foundation.items():
    if int(r["year"]) == 2026:
        foundation_by_year["2026"].append({"fid": fid, "date": r["date"], "audit_pnl_u": float(r["pnl"])})
combined_by_method = {}
for method, rows in by_method.items():
    unique = {r["fid"]: r for r in rows}
    add = [r for fid, r in unique.items() if fid not in foundation]
    combined = foundation_by_year["2026"] + add
    combined_by_method[method] = summarize(combined)

with OUT_ROWS.open("w") as f:
    for r in audited:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
result = {
    "study": "M8 batch independent actual receipt Crown AH settlement audit",
    "method": "independent manual quarter-line settlement, exact pre-kickoff HTTP receipt match at its actual horizon, SHA256 of stored snapshot.json, verified FT from receipt coverage index",
    "coverage": {"verified_receipt_FT_fids": len(coverage), "verified_archive_receipts_all_horizons": len(archive),
                 "candidate_actual_rows": sum(len(read(p)) for p in INPUTS),
                 "audited_rows": len(audited), "unique_receipt_fids": len(used_receipt_fids),
                 "snapshot_sha256_checks": snapshot_checks,
                 "unresolved_or_failed_checks": dict(errors)},
    "per_method": method_results,
    "2026_frozen_eight_plus_each_research_method": combined_by_method,
    "output_per_fixture": OUT_ROWS.name,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False, indent=2))
