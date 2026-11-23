#!/usr/bin/env python3
"""Read-only inventory and per-market coverage audit for the fixed 64 leagues.

The audit's fixture universe is the approved 64 Provider League IDs and
season_year 2023-2026. It distinguishes leagues with no fixtures in the target
years from missing Crown market data. No network calls or database writes are
performed; only a TEMP SQLite table is created for the selected FIDs.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path

IDS = {
    1, 10, 12, 14, 16, 25, 29, 31, 33, 35, 37, 40, 43, 45, 46, 47, 48,
    51, 52, 55, 60, 61, 62, 66, 68, 70, 73, 75, 85, 88, 109, 116, 129,
    141, 145, 152, 177, 262, 290, 297, 298, 299, 303, 314, 319, 328, 330,
    332, 345, 378, 670, 779, 979, 1439, 8172, 8293, 10480, 10714, 11498,
    19290, 26540, 27388, 27389, 27390,
}
DEFAULT_SCHEDULE = Path(
    "/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/"
    "schedule_universe.jsonl"
)
DEFAULT_DATABASE = Path(
    "/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", type=Path, default=DEFAULT_SCHEDULE)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    selected: list[tuple[str, int, int, int | None, int | None]] = []
    all_league_years: dict[int, collections.Counter[int]] = collections.defaultdict(
        collections.Counter
    )
    all_scope_leagues: set[int] = set()
    per_year = collections.Counter()
    for line in args.schedule.open():
        row = json.loads(line)
        league = int(row["league_id"])
        if league not in IDS:
            continue
        all_scope_leagues.add(league)
        year = int(row.get("season_year") or 0)
        all_league_years[league][year] += 1
        if not 2023 <= year <= 2026:
            continue
        selected.append((
            str(row["match_id"]), league, year,
            row.get("home_goals"), row.get("away_goals"),
        ))
        per_year[year] += 1

    if all_scope_leagues != IDS:
        raise RuntimeError(
            f"fixed league inventory mismatch: missing={sorted(IDS-all_scope_leagues)} "
            f"extra={sorted(all_scope_leagues-IDS)}"
        )
    fids = [row[0] for row in selected]
    if len(fids) != len(set(fids)):
        raise RuntimeError("duplicate FID in selected fixture universe")

    con = sqlite3.connect(args.database)
    try:
        con.execute(
            "CREATE TEMP TABLE target_fixture "
            "(fid TEXT PRIMARY KEY, league_id INTEGER, season_year INTEGER, "
            "home_goals INTEGER, away_goals INTEGER)"
        )
        con.executemany("INSERT INTO target_fixture VALUES(?,?,?,?,?)", selected)

        def count_fids(sql: str) -> int:
            return int(con.execute(sql).fetchone()[0])

        market_coverage = {
            "ah_open_close": count_fids(
                "SELECT COUNT(DISTINCT q.fixture_id) FROM asian_quote q "
                "JOIN target_fixture t ON t.fid=q.fixture_id "
                "WHERE q.quote_kind IN ('open','close')"
            ),
            "ah_movement": count_fids(
                "SELECT COUNT(DISTINCT q.fixture_id) FROM asian_quote q "
                "JOIN target_fixture t ON t.fid=q.fixture_id "
                "WHERE q.quote_kind='movement'"
            ),
            "ou_open_close": count_fids(
                "SELECT COUNT(DISTINCT q.fixture_id) FROM crown_ou_quote q "
                "JOIN target_fixture t ON t.fid=q.fixture_id "
                "WHERE q.quote_kind IN ('open','close')"
            ),
            "ou_movement": count_fids(
                "SELECT COUNT(DISTINCT q.fixture_id) FROM crown_ou_quote q "
                "JOIN target_fixture t ON t.fid=q.fixture_id "
                "WHERE q.quote_kind='movement'"
            ),
        }
        missing = {
            key: len(fids) - value for key, value in market_coverage.items()
        }
        ah_kinds = con.execute(
            "SELECT q.quote_kind,COUNT(*),COUNT(DISTINCT q.fixture_id) "
            "FROM asian_quote q JOIN target_fixture t ON t.fid=q.fixture_id "
            "GROUP BY q.quote_kind ORDER BY q.quote_kind"
        ).fetchall()
        ou_kinds = con.execute(
            "SELECT q.quote_kind,COUNT(*),COUNT(DISTINCT q.fixture_id) "
            "FROM crown_ou_quote q JOIN target_fixture t ON t.fid=q.fixture_id "
            "GROUP BY q.quote_kind ORDER BY q.quote_kind"
        ).fetchall()
    finally:
        con.close()

    league_314_years = all_league_years.get(314, collections.Counter())
    completed = sum(
        home is not None and away is not None
        for _, _, _, home, away in selected
    )
    db_stat = args.database.stat()
    result = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "capture_mode": "historical inventory audit; no requests made",
        "scope": {
            "fixed_provider_league_ids": sorted(IDS),
            "fixed_league_count": len(IDS),
            "target_years": [2023, 2024, 2025, 2026],
            "schedule_league_ids_present_any_year": sorted(all_scope_leagues),
            "league_ids_with_target_year_fixtures": sorted(
                {league for _, league, *_ in selected}
            ),
            "league_ids_without_target_year_fixtures": sorted(
                IDS - {league for _, league, *_ in selected}
            ),
            "league_314_schedule_fixtures_by_year": {
                str(year): count for year, count in sorted(league_314_years.items())
            },
        },
        "schedule": {
            "path": str(args.schedule),
            "sha256": sha256(args.schedule),
            "unique_fids": len(fids),
            "fixtures_by_year": {
                str(year): per_year[year] for year in range(2023, 2027)
            },
            "completed_scores_present": completed,
            "scores_missing": len(selected) - completed,
        },
        "database": {
            "path": str(args.database),
            "size_bytes": db_stat.st_size,
            "mtime_utc": dt.datetime.fromtimestamp(
                db_stat.st_mtime, dt.timezone.utc
            ).isoformat(),
            "market_quote_kind_rows_and_fids": {
                "ah": [
                    {"quote_kind": kind, "rows": rows, "fids": fids_count}
                    for kind, rows, fids_count in ah_kinds
                ],
                "ou": [
                    {"quote_kind": kind, "rows": rows, "fids": fids_count}
                    for kind, rows, fids_count in ou_kinds
                ],
            },
        },
        "market_coverage_unique_fids": market_coverage,
        "market_missing_unique_fids": missing,
        "interpretation": (
            "Missing counts are market-specific and overlap. Fixture universe is "
            "restricted by the fixed 64 IDs and target years. League 314 remains "
            "in the fixed scope but has no scheduled fixtures in 2023-2026."
        ),
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
