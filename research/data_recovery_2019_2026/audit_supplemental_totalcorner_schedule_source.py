#!/usr/bin/env python3
"""Audit a previously unmerged TotalCorner schedule source; no Crown/API calls."""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
SOURCE_DEFAULT = Path(
    "/Users/mac/QuantAsiaDesk/repos/runner/research/shared_history/totalcorner/league-15.jsonl"
)
INVENTORY_DEFAULT = Path(
    "/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/fixture_inventory_2019_2026.jsonl.gz"
)
OUT_DEFAULT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_kickoff(raw: str | None) -> tuple[str | None, str | None, int | None]:
    if not raw:
        return None, None, None
    try:
        value = dt.datetime.fromisoformat(raw.replace("Z", "+00:00").replace(" ", "T"))
        if value.tzinfo is None:
            # Matches the existing TotalCorner schedule normalization convention.
            value = value.replace(tzinfo=SHANGHAI)
        utc = value.astimezone(dt.timezone.utc)
        return utc.isoformat().replace("+00:00", "Z"), utc.date().isoformat(), utc.year
    except (TypeError, ValueError):
        return None, None, None


def parse_score(value: object) -> int | None:
    try:
        n = int(str(value))
        return n if n >= 0 and str(value).strip() == str(n) else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    ap.add_argument("--inventory", type=Path, default=INVENTORY_DEFAULT)
    ap.add_argument("--out-dir", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    known_fids: set[str] = set()
    with gzip.open(args.inventory, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                if row.get("fid"):
                    known_fids.add(str(row["fid"]))

    source_rows: dict[str, dict] = {}
    duplicate_fids: list[str] = []
    bad_rows: list[dict] = []
    with args.source.open("rb") as f:
        for line_no, raw_line in enumerate(f, 1):
            if not raw_line.strip():
                continue
            try:
                source = json.loads(raw_line)
                fid = str(source["id"])
                league_id = str(source["league_id"])
                match = source.get("match") or {}
                if league_id != "15":
                    raise ValueError(f"unexpected provider league id {league_id}")
                ko_utc, ko_date_utc, year_utc = parse_kickoff(match.get("start"))
                hg, ag = parse_score(match.get("hg")), parse_score(match.get("ag"))
                status = match.get("status")
                record = {
                    "fid": fid,
                    "provider_match_id": fid,
                    "provider_league_id": league_id,
                    "league_name": source.get("league_name"),
                    "season": None,
                    "season_status": "not_provided_by_source",
                    "kickoff_source_raw": match.get("start"),
                    "kickoff_source_timezone": "unspecified_in_record; normalized with existing project Asia/Shanghai convention",
                    "kickoff_utc": ko_utc,
                    "kickoff_utc_date": ko_date_utc,
                    "calendar_year_utc": year_utc,
                    "home_name": match.get("h"),
                    "home_id": str(match.get("h_id") or ""),
                    "away_name": match.get("a"),
                    "away_id": str(match.get("a_id") or ""),
                    "status_raw": status,
                    "home_goals_raw": match.get("hg"),
                    "away_goals_raw": match.get("ag"),
                    "verified_full_time_score": bool(status == "full" and hg is not None and ag is not None),
                    "home_goals_normalized": hg,
                    "away_goals_normalized": ag,
                    "source": source.get("source"),
                    "observed_at_utc": source.get("observed_at_utc"),
                    "source_response_sha256": source.get("source_sha256"),
                    "source_line_sha256": hashlib.sha256(raw_line.rstrip(b"\r\n")).hexdigest(),
                    "source_record_file": str(args.source),
                    "crown_market_status": "not_joined_in_this_schedule_only_audit",
                }
                if not fid or not ko_utc:
                    raise ValueError("missing FID or unparseable kickoff")
                if fid in source_rows:
                    if source_rows[fid] != record:
                        raise ValueError(f"conflicting duplicate FID {fid}")
                    duplicate_fids.append(fid)
                else:
                    source_rows[fid] = record
            except Exception as exc:
                bad_rows.append({"line_no": line_no, "error": f"{type(exc).__name__}: {exc}"})

    fids = set(source_rows)
    overlap = sorted(fids & known_fids)
    new = sorted(fids - known_fids, key=lambda x: (source_rows[x]["kickoff_utc"] or "", x))
    rows_path = args.out_dir / "supplemental_totalcorner_league15_schedule_20261121.jsonl.gz"
    with rows_path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as gz:
            for fid in new:
                payload = json.dumps(source_rows[fid], ensure_ascii=False, separators=(",", ":")).encode()
                gz.write(payload + b"\n")

    years: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    full_ft = 0
    for fid in new:
        r = source_rows[fid]
        y = str(r["calendar_year_utc"] or "unknown")
        years[y] = years.get(y, 0) + 1
        s = str(r["status_raw"] or "missing")
        status_counts[s] = status_counts.get(s, 0) + 1
        full_ft += int(r["verified_full_time_score"])

    summary = {
        "audit": "supplemental TotalCorner schedule source only; no strategy/model/backtest and no Crown request",
        "source_file": str(args.source),
        "source_file_sha256": sha256(args.source),
        "existing_inventory_file": str(args.inventory),
        "existing_inventory_file_sha256": sha256(args.inventory),
        "existing_inventory_unique_fids": len(known_fids),
        "source_unique_fids": len(fids),
        "source_rows_duplicate_exact": len(duplicate_fids),
        "source_rows_bad_or_conflicting": bad_rows,
        "overlap_with_existing_inventory": len(overlap),
        "new_unique_fids": len(new),
        "new_unique_fids_by_utc_calendar_year": dict(sorted(years.items())),
        "new_unique_fids_by_source_status": dict(sorted(status_counts.items())),
        "verified_full_time_scores": full_ft,
        "score_fields_with_unverified_or_missing_status": sum(
            int(source_rows[f]["home_goals_raw"] is not None and source_rows[f]["away_goals_raw"] is not None and not source_rows[f]["verified_full_time_score"])
            for f in new
        ),
        "new_fids_in_existing_inventory": False,
        "crown_quote_join_performed": False,
        "page_history_limitations": "The source collection summary records an unsuccessful request for league 15 page 5; these stored 120 rows are not asserted to be a complete league-season schedule.",
        "unresolved_other_schedule_candidates": "The same source summary records 14 additional competition IDs whose first requested page returned an unsuccessful response; see unresolved_schedule_competition_candidates_20261121.json.",
        "normalized_rows_file": rows_path.name,
        "normalized_rows_sha256": sha256(rows_path),
        "normalized_new_rows": len(new),
    }
    summary_path = args.out_dir / "supplemental_totalcorner_league15_schedule_summary_20261121.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if bad_rows or overlap:
        raise SystemExit(f"source audit requires review: bad={len(bad_rows)} overlap={len(overlap)}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
