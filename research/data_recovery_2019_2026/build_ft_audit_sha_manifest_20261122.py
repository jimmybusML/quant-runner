#!/usr/bin/env python3
"""Build the 2026-11-22 reproducibility digest list for the FT audit checkpoint."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
DATA = Path("/Users/mac/QuantAsiaDesk/data")
REPO_FILES = [
    ROOT / "audit_epl_laliga_espn_ft_archive_20261122.py",
    ROOT / "reconcile_53_league_schedule_union_20261122.py",
    ROOT / "classify_merged_unverified_ft_readiness_20261122.py",
    ROOT / "build_recovery_checkpoint_20261122.py",
    ROOT / "build_ft_audit_sha_manifest_20261122.py",
    ROOT / "EXISTING_EPL_LALIGA_ESPN_FT_AUDIT_20261122.md",
    ROOT / "epl_laliga_espn_ft_archive_reconciliation_20261122.json",
    ROOT / "epl_laliga_espn_verified_ft_overlay_20261122.jsonl",
    ROOT / "epl_laliga_espn_verified_ft_conflicts_20261122.jsonl",
    ROOT / "schedule_union_53_leagues_reconciliation_20261122.json",
    ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz",
    ROOT / "unverified_FT_candidates_pre_epl_laliga_20261122.jsonl.gz",
    ROOT / "unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz",
    ROOT / "unverified_ft_readiness_203962_inventory_20261122.json",
    ROOT / "unverified_ft_readiness_203962_inventory_20261122.jsonl",
    ROOT / "unverified_ft_readiness_203962_inventory_by_league_year_20261122.csv",
    ROOT / "COLLECTION_STATUS_20261122T0253Z.json",
    ROOT / "COLLECTION_CHECKPOINT_20261122T0253Z.md",
    REPO / "PROJECT_HANDOFF.md",
    ROOT / "README.md",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    audit = json.loads((ROOT / "epl_laliga_espn_ft_archive_reconciliation_20261122.json").read_text())
    entries = []
    for path in REPO_FILES:
        if not path.is_file():
            raise SystemExit(f"missing repo artifact: {path}")
        entries.append((sha(path), str(path.relative_to(REPO))))

    local_inputs = {
        "epl_laliga_crown_5seasons/英超_西甲_2021-22至2025-26_Crown亚洲盘.csv": audit["csv_input"]["sha256"],
        "epl_laliga_crown_5seasons/espn_verified_enrichment.json": audit["enrichment_input"]["sha256"],
        "epl_laliga_crown_5seasons/espn_identity_review.json": audit["team_identity_review_input"]["sha256"],
    }
    for rel, expected in local_inputs.items():
        path = DATA / rel
        if not path.is_file() or sha(path) != expected:
            raise SystemExit(f"local input missing or SHA mismatch: {path}")
        entries.append((expected, f"PRIVATE_INPUT:{path}"))
    for rel, expected in audit["raw_espn_season_responses"]["sha256_by_relative_path"].items():
        path = DATA / rel
        if not path.is_file() or sha(path) != expected:
            raise SystemExit(f"raw ESPN source missing or SHA mismatch: {path}")
        entries.append((expected, f"PRIVATE_INPUT:{path}"))

    out = ROOT / "CHECKPOINT_SHA256_20261122T0253Z.txt"
    lines = ["# SHA256 checkpoint 2026-11-22 02:53 UTC",
             "# Repository-relative paths unless explicitly prefixed PRIVATE_INPUT."]
    lines.extend(f"{digest}  {path}" for digest, path in sorted(entries, key=lambda x: x[1]))
    lines.append("# Raw licensed responses, private inventory, and Crown SQLite remain local.")
    lines.append("# Active SQLite writer/WAL snapshot is not represented by a stable DB file SHA.")
    out.write_text("\n".join(lines) + "\n")
    print(json.dumps({"manifest": out.name, "entries": len(entries), "sha256": sha(out)}, indent=2))


if __name__ == "__main__":
    main()
