#!/usr/bin/env python3
"""Strictly recheck archived ESPN FT evidence against the reconciled inventory.

No requests are made. Each accepted result requires an exact FID, unique saved
schedule identity, exact UTC kickoff, full-time source status, and verified raw
response SHA. ESPN remains an external FT source, never a Crown quote source.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
QUEUE = ROOT / "unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz"
SOURCE = Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_remaining_FT_exact_id_20261110/espn/verified_external_espn_results.jsonl")
OUT = ROOT / "archived_espn_verified_ft_reconciled_to_203962_inventory_20261122.jsonl"
AUDIT = ROOT / "archived_espn_ft_reconciliation_203962_inventory_20261122.json"
UTC = dt.timezone.utc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return "".join(c for c in text if c.isalnum())


def parse_utc(value):
    if not value:
        return None
    try:
        x = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if x.tzinfo is None:
            return None
        return x.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def fixture_evidence(row):
    out = []
    for key in ("totalcorner_page_records", "m1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
        for source in row.get(key, []):
            ko = parse_utc(source.get("kickoff_utc"))
            home, away = source.get("home_name"), source.get("away_name")
            if ko and home and away:
                out.append((ko, norm(home), norm(away), str(source.get("provider_league_id") or "")))
    return set(out)


def main():
    inventory = {}
    for line in gzip.open(INVENTORY, "rt", encoding="utf-8"):
        row = json.loads(line)
        inventory[str(row["fid"])] = row
    queue = set()
    for line in gzip.open(QUEUE, "rt", encoding="utf-8"):
        row = json.loads(line)
        queue.add(str(row["fid"]))
    rejects = collections.Counter()
    rejected_fids = collections.defaultdict(list)
    accepted = {}
    verified_rows_candidate_fids = set()
    source_status = collections.Counter()
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        status = str(row.get("status") or "MISSING_STATUS")
        source_status[status] += 1
        if status != "ESPN_FT_VERIFIED":
            continue
        fid = str(row.get("fixture_id") or "")
        fixture = inventory.get(fid)
        if fixture is None:
            rejects["fid_not_in_reconciled_inventory"] += 1
            rejected_fids["fid_not_in_reconciled_inventory"].append(fid)
            continue
        if fid in queue:
            verified_rows_candidate_fids.add(fid)
        raw_path = Path(str(row.get("raw_result_file") or ""))
        raw_sha = str(row.get("raw_result_SHA256") or "")
        if not raw_path.is_file() or not raw_sha or sha256(raw_path) != raw_sha:
            reason = "raw_file_missing_or_sha_mismatch"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        if len(row.get("external_matches") or []) != 1:
            reason = "external_match_not_unique"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        match = row["external_matches"][0]
        try:
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
        except Exception:
            reason = "raw_json_invalid"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        event_id = str(match.get("eid") or row.get("provider_event_id") or "")
        events = [x for x in raw.get("events", []) if str(x.get("id")) == event_id]
        if len(events) != 1:
            reason = "raw_event_id_not_unique"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        event = events[0]
        comps = event.get("competitions") or []
        if len(comps) != 1:
            reason = "competition_not_unique"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        comp = comps[0]
        st = (comp.get("status") or {}).get("type") or {}
        if st.get("name") != "STATUS_FULL_TIME" or not st.get("completed"):
            reason = "raw_event_not_verified_full_time"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        sides = comp.get("competitors") or []
        home = [x for x in sides if x.get("homeAway") == "home"]
        away = [x for x in sides if x.get("homeAway") == "away"]
        if len(home) != 1 or len(away) != 1:
            reason = "raw_home_away_not_unique"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        hn = (home[0].get("team") or {}).get("displayName") or (home[0].get("team") or {}).get("name")
        an = (away[0].get("team") or {}).get("displayName") or (away[0].get("team") or {}).get("name")
        hg, ag = home[0].get("score"), away[0].get("score")
        ko = parse_utc(fixture.get("totalcorner_kickoff_utc") or fixture.get("kickoff_utc"))
        crown_ko = parse_utc(row.get("Crown_kickoff"))
        ext_ko = parse_utc(event.get("date"))
        expected = (ko, norm(row.get("Crown_home")), norm(row.get("Crown_away")))
        observed = (crown_ko, norm(hn), norm(an))
        if not ko or not ext_ko or ko != ext_ko or crown_ko != ko:
            reason = "exact_utc_kickoff_mismatch_or_missing"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        identities = fixture_evidence(fixture)
        matching_identity = (ko, norm(hn), norm(an))
        if not identities or any((a, b, c) != matching_identity for a, b, c, _ in identities):
            reason = "inventory_identity_not_unique_or_mismatched"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        if expected != observed:
            reason = "crown_and_external_identity_mismatch"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        if str(hg) != str(row.get("home_goals")) or str(ag) != str(row.get("away_goals")):
            reason = "raw_score_mismatch"
            rejects[reason] += 1
            rejected_fids[reason].append(fid)
            continue
        if fid in accepted:
            if accepted[fid]["verified_FT"] != f"{int(hg)}:{int(ag)}":
                reason = "conflicting_verified_scores_for_fid"
                rejects[reason] += 1
                rejected_fids[reason].append(fid)
                accepted.pop(fid, None)
                continue
            accepted[fid]["duplicate_source_rows"] += 1
            continue
        accepted[fid] = {
            "fid": fid,
            "provider_league_id": fixture.get("provider_league_id"),
            "kickoff_utc": fixture.get("totalcorner_kickoff_utc") or fixture.get("kickoff_utc"),
            "Crown_home": row.get("Crown_home"),
            "Crown_away": row.get("Crown_away"),
            "verified_FT": f"{int(hg)}:{int(ag)}",
            "source": "archived ESPN raw response, independently reverified; not Crown odds",
            "source_event_id": event_id,
            "source_raw_sha256": raw_sha,
            "source_raw_file": str(raw_path),
            "crosswalk": "exact FID in reconciled inventory plus exact UTC kickoff and normalized home/away identity",
            "response_status": "STATUS_FULL_TIME",
            "duplicate_source_rows": 0,
        }

    with OUT.open("w", encoding="utf-8") as f:
        for fid in sorted(accepted):
            f.write(json.dumps(accepted[fid], ensure_ascii=False, separators=(",", ":")) + "\n")
    summary = {
        "generated_at_utc": dt.datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "input_sha256": {INVENTORY.name: sha256(INVENTORY), QUEUE.name: sha256(QUEUE), SOURCE.name: sha256(SOURCE)},
        "source_status_counts": dict(sorted(source_status.items())),
        "verified_source_FIDs_in_current_unverified_queue": len(verified_rows_candidate_fids),
        "verified_source_FIDs_in_reconciled_inventory": len(accepted),
        "strictly_reconciled_unique_FIDs": len(accepted),
        "rejected_or_outside_candidate_counts": dict(sorted(rejects.items())),
        "rejected_FIDs_by_reason": {k: v for k, v in sorted(rejected_fids.items())},
        "network_requests": 0,
        "outputs": {OUT.name: {"sha256": sha256(OUT), "bytes": OUT.stat().st_size, "rows": len(accepted)}},
        "caveat": "This is a separately attributed archived ESPN FT overlay. It neither changes the TotalCorner source record nor represents Crown AH availability or a real-time observation.",
    }
    AUDIT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rejected_FIDs_by_reason"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
