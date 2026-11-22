#!/usr/bin/env python3
"""Classify the remaining FT queue without interpreting provider status codes."""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz"
OUT_JSONL = ROOT / "unverified_ft_readiness_203962_inventory_20261122.jsonl"
OUT_CSV = ROOT / "unverified_ft_readiness_203962_inventory_by_league_year_20261122.csv"
SUMMARY = ROOT / "unverified_ft_readiness_203962_inventory_20261122.json"
UTC = dt.timezone.utc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_utc(value):
    if not value:
        return None
    try:
        x = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return x.astimezone(UTC) if x.tzinfo else None
    except (TypeError, ValueError):
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--as-of-utc", default=None)
    args = p.parse_args()
    asof = parse_utc(args.as_of_utc) if args.as_of_utc else dt.datetime.now(UTC)
    if asof is None:
        raise SystemExit("invalid --as-of-utc")
    groups = collections.defaultdict(lambda: collections.Counter())
    totals = collections.Counter()
    rows = []
    seen = set()
    with gzip.open(INPUT, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            fid = str(row["fid"])
            if fid in seen:
                raise SystemExit(f"duplicate FID: {fid}")
            seen.add(fid)
            kickoff = parse_utc(row.get("kickoff_utc"))
            statuses = sorted({str(x.get("status")) for x in row.get("evidence_records", []) if x.get("status") not in (None, "")})
            scores = sorted({f"{x.get('home_goals')}:{x.get('away_goals')}" for x in row.get("evidence_records", []) if x.get("home_goals") is not None and x.get("away_goals") is not None})
            if kickoff is None:
                reason = "kickoff_missing"
            elif kickoff > asof:
                reason = "future_fixture_not_due"
            elif any(x.casefold() == "full" for x in statuses):
                reason = "full_status_score_invalid_or_conflicting"
            elif statuses:
                reason = "provider_reports_non_full_status_uninterpreted"
            elif row.get("evidence_records"):
                reason = "past_kickoff_status_missing_or_unknown"
            else:
                reason = "past_kickoff_no_schedule_or_score_source_record"
            placeholder = "0:0" in scores
            year = row.get("utc_year")
            key = (str(row.get("provider_league_id") or ""), str(year) if year is not None else "UNKNOWN_KICKOFF_YEAR")
            groups[key][reason] += 1
            groups[key]["unverified_fids"] += 1
            groups[key]["placeholder_0_0_fids"] += int(placeholder)
            groups[key]["no_source_record_fids"] += int(not row.get("evidence_records"))
            totals[reason] += 1
            totals["placeholder_0_0_fids"] += int(placeholder)
            rows.append({
                "fid": fid,
                "provider_league_id": row.get("provider_league_id"),
                "utc_year": year,
                "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z") if kickoff else None,
                "readiness": reason,
                "source_statuses": statuses,
                "observed_scores": scores,
                "placeholder_0_0_present": placeholder,
                "source_record_count": len(row.get("evidence_records", [])),
            })
    rows.sort(key=lambda x: (str(x["provider_league_id"]), str(x["utc_year"]), x["fid"]))
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    reason_fields = (
        "future_fixture_not_due",
        "kickoff_missing",
        "full_status_score_invalid_or_conflicting",
        "provider_reports_non_full_status_uninterpreted",
        "past_kickoff_status_missing_or_unknown",
        "past_kickoff_no_schedule_or_score_source_record",
    )
    matrix = []
    for (lid, year), counter in sorted(groups.items()):
        matrix.append({"provider_league_id": lid, "utc_year": year,
                       **{field: counter.get(field, 0) for field in reason_fields},
                       "unverified_fids": counter.get("unverified_fids", 0),
                       "placeholder_0_0_fids": counter.get("placeholder_0_0_fids", 0),
                       "no_source_record_fids": counter.get("no_source_record_fids", 0)})
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(matrix[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(matrix)
    summary = {
        "generated_at_utc": dt.datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "as_of_utc": asof.isoformat().replace("+00:00", "Z"),
        "input_sha256": sha256(INPUT),
        "candidate_unique_fids": len(rows),
        "classifications": dict(sorted(totals.items())),
        "league_year_rows": len(matrix),
        "network_requests": 0,
        "interpretation": "Provider status values are preserved literally; non-full codes are not interpreted as cancellation, postponement, or abandonment. 0:0 is marked as an observed value only and is never accepted as a verified result.",
        "outputs": {
            OUT_JSONL.name: {"sha256": sha256(OUT_JSONL), "rows": len(rows)},
            OUT_CSV.name: {"sha256": sha256(OUT_CSV), "rows": len(matrix)},
        },
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
