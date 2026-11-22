#!/usr/bin/env python3
"""Append the audited 53-league TotalCorner schedule batch to the inventory.

This is an offline, append-only reconciliation artifact. It does not modify the
baseline inventory, contact Crown/TotalCorner, or infer seasons from dates.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "fixture_inventory_2019_2026.jsonl.gz"
SUPP = ROOT / "supplemental_totalcorner_schedules_53leagues_2019_2026.jsonl.gz"
OUT = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
SUMMARY = ROOT / "schedule_union_53_leagues_reconciliation_20261122.json"
UNVERIFIED = ROOT / "unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz"
EXTERNAL_FT = ROOT / "archived_espn_verified_ft_reconciled_to_203962_inventory_20261122.jsonl"
M5_FT_OVERLAY = ROOT / "m5_verified_ft_overlay_2019_2026_20261122.jsonl"
M5_RAW_ROOT = Path("/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/forward-shadow")
CROWN_FT_OVERLAY = ROOT / "crown_capture_verified_ft_overlay_2019_2026_20261122.jsonl"
EPL_LALIGA_ESPN_FT_OVERLAY = ROOT / "epl_laliga_espn_verified_ft_overlay_20261122.jsonl"
EPL_LALIGA_ESPN_CONFLICTS = ROOT / "epl_laliga_espn_verified_ft_conflicts_20261122.jsonl"
CROWN_DATA_ROOT = Path("/Users/mac/QuantAsiaDesk/data")
UTC = dt.timezone.utc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def scope_year(row):
    value = row.get("kickoff_utc")
    if not value:
        return None
    try:
        x = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if x.tzinfo is None:
            return None
        x = x.astimezone(UTC)
        return x.year if 2019 <= x.year <= 2026 else None
    except (ValueError, TypeError):
        return None


def parse_dt(value):
    if not value:
        return None
    try:
        x = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if x.tzinfo is None:
            return None
        return x.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def normalize(row):
    y = scope_year(row)
    supplemental = {
        "source_file": str(SUPP),
        "source_record_sha256": row.get("source_record_sha256"),
        "source_response_sha256": row.get("source_page_response_sha256"),
        "provider_league_id": str(row.get("provider_league_id") or ""),
        "league_name": row.get("provider_league_name"),
        "kickoff_source": row.get("kickoff_source_raw"),
        "kickoff_utc": row.get("kickoff_utc"),
        "home_id": str(row.get("home_id") or ""),
        "away_id": str(row.get("away_id") or ""),
        "home_name": row.get("home_name"),
        "away_name": row.get("away_name"),
        "status": row.get("status_raw"),
        "home_goals": row.get("home_goals_raw"),
        "away_goals": row.get("away_goals_raw"),
        "season": row.get("season_raw"),
        "observed_at_utc": row.get("response_received_at_utc"),
        "source_page": row.get("source_page"),
        "capture_mode": row.get("capture_mode"),
    }
    return {
        "fid": str(row["fid"]),
        "provider_league_id": str(row.get("provider_league_id") or ""),
        "year": y,
        "totalcorner_kickoff_utc": row.get("kickoff_utc"),
        "totalcorner_page_records": [],
        "supplemental_schedule_records": [supplemental],
        "crown_fixture_metadata_records": [],
        "M1_history_cache_records": [],
        "m5_result_evidence_records": [],
        "expanded_universe_records": [],
        "priced_t6_records": [],
        "crown_captures": [],
        "crown_quote_groups": [],
        "external_ft_evidence": [],
        "failed_attempts": {},
        "identity_conflicts": [],
    }


def has_verified_ft(row):
    if row.get("external_ft_evidence"):
        return True
    sources = []
    # The merged inventory's actual field is case-sensitive and named
    # ``M1_history_cache_records``. The old lowercase spelling silently
    # excluded all verified M1 FT rows from the reconciled count.
    for key in ("totalcorner_page_records", "M1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
        sources.extend(row.get(key, []))
    has_schedule_ft = any(
        x.get("status") == "full"
        and str(x.get("home_goals", "")).isdigit()
        and str(x.get("away_goals", "")).isdigit()
        for x in sources
    )
    has_m5_ft = any(
        x.get("status") == "verified_ft"
        and str(x.get("home_goals", "")).isdigit()
        and str(x.get("away_goals", "")).isdigit()
        and bool(x.get("raw_response_sha256"))
        for x in row.get("m5_result_evidence_records", [])
    )
    has_crown_capture_ft = any(
        x.get("status") == "full"
        and str(x.get("home_goals", "")).isdigit()
        and str(x.get("away_goals", "")).isdigit()
        and bool(x.get("raw_response_sha256"))
        for x in row.get("crown_ft_evidence_records", [])
    )
    return has_schedule_ft or has_m5_ft or has_crown_capture_ft


def normalized_name(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return "".join(c for c in text if c.isalnum())


def verified_external_rows(path):
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({str(row.get("fid")) for row in rows}) != len(rows):
        raise SystemExit("duplicate FID in archived external FT overlay")
    for row in rows:
        if not re.fullmatch(r"\d+:\d+", str(row.get("verified_FT") or "")):
            raise SystemExit(f"invalid archived external FT for FID {row.get('fid')}")
        raw = Path(str(row.get("source_raw_file") or ""))
        if not raw.is_file() or sha256(raw) != row.get("source_raw_sha256"):
            raise SystemExit(f"raw ESPN SHA mismatch for FID {row.get('fid')}")
    return rows


def verified_epl_laliga_espn_rows(path, existing):
    """Revalidate the saved EPL/La Liga ESPN rows against raw season responses.

    The TotalCorner kickoff and ESPN event kickoff are stored separately. A
    time discrepancy does not rewrite the canonical schedule timestamp; exact
    FID, league, home/away IDs and names are required for the crosswalk.
    """
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
    if len({str(row.get("fid")) for row in rows}) != len(rows):
        raise SystemExit("duplicate FID in EPL/La Liga ESPN overlay")
    accepted = []
    for row in rows:
        fid = str(row.get("fid") or "")
        fixture = existing.get(fid)
        if fixture is None:
            raise SystemExit(f"EPL/La Liga ESPN FT FID outside merged inventory: {fid}")
        if str(row.get("provider_league_id")) != str(fixture.get("provider_league_id")):
            raise SystemExit(f"EPL/La Liga ESPN provider league mismatch: {fid}")
        if row.get("kickoff_utc") != fixture.get("totalcorner_kickoff_utc"):
            raise SystemExit(f"EPL/La Liga ESPN canonical TotalCorner kickoff mismatch: {fid}")
        raw = CROWN_DATA_ROOT / str(row.get("source_raw_file") or "")
        raw_sha = str(row.get("source_raw_sha256") or "")
        if not raw.is_file() or not raw_sha or sha256(raw) != raw_sha:
            raise SystemExit(f"EPL/La Liga ESPN raw season response missing or SHA mismatch: {fid}")
        body = json.loads(raw.read_text(encoding="utf-8"))
        events = [event for event in body.get("events", []) if str(event.get("id")) == str(row.get("source_event_id"))]
        if len(events) != 1:
            raise SystemExit(f"EPL/La Liga ESPN event ID is not unique in saved response: {fid}")
        event = events[0]
        comps = event.get("competitions") or []
        if len(comps) != 1:
            raise SystemExit(f"EPL/La Liga ESPN competition is not unique: {fid}")
        comp = comps[0]
        st = (comp.get("status") or {}).get("type") or {}
        if st.get("name") != "STATUS_FULL_TIME" or not st.get("completed"):
            raise SystemExit(f"EPL/La Liga ESPN raw event not full time: {fid}")
        sides = comp.get("competitors") or []
        home = [x for x in sides if x.get("homeAway") == "home"]
        away = [x for x in sides if x.get("homeAway") == "away"]
        if len(home) != 1 or len(away) != 1:
            raise SystemExit(f"EPL/La Liga ESPN raw home/away ambiguity: {fid}")
        h, a = home[0], away[0]
        try:
            score = f"{int(h['score'])}:{int(a['score'])}"
        except (KeyError, TypeError, ValueError):
            raise SystemExit(f"EPL/La Liga ESPN raw score invalid: {fid}")
        if score != str(row.get("verified_FT")):
            raise SystemExit(f"EPL/La Liga ESPN raw score differs from overlay: {fid}")
        event_ko = parse_dt(event.get("date"))
        if not event_ko or event_ko.isoformat().replace("+00:00", "Z") != row.get("source_event_kickoff_utc"):
            raise SystemExit(f"EPL/La Liga ESPN raw event kickoff differs from overlay: {fid}")
        hn = (h.get("team") or {}).get("displayName") or (h.get("team") or {}).get("name")
        an = (a.get("team") or {}).get("displayName") or (a.get("team") or {}).get("name")
        if normalized_name(hn) != normalized_name(row.get("espn_home_name_raw")) or normalized_name(an) != normalized_name(row.get("espn_away_name_raw")):
            raise SystemExit(f"EPL/La Liga ESPN raw team names differ from overlay: {fid}")
        if (normalized_name(row.get("espn_home_mapped_name")) != normalized_name(row.get("home_name"))
                or normalized_name(row.get("espn_away_mapped_name")) != normalized_name(row.get("away_name"))):
            raise SystemExit(f"EPL/La Liga ESPN saved team map differs from canonical fixture: {fid}")
        if not str(row.get("home_id")) or not str(row.get("away_id")):
            raise SystemExit(f"EPL/La Liga ESPN overlay missing exact TotalCorner team IDs: {fid}")
        identity_matches = []
        for key in ("totalcorner_page_records", "M1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
            for src in fixture.get(key, []):
                if (str(src.get("home_id")) == str(row.get("home_id"))
                        and str(src.get("away_id")) == str(row.get("away_id"))
                        and normalized_name(src.get("home_name")) == normalized_name(row.get("home_name"))
                        and normalized_name(src.get("away_name")) == normalized_name(row.get("away_name"))):
                    identity_matches.append(key)
        if not identity_matches:
            raise SystemExit(f"EPL/La Liga ESPN exact TotalCorner team identity not corroborated: {fid}")
        accepted.append(row)
    return rows, accepted


def verified_epl_laliga_conflicts(path, existing, accepted_ft_rows):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
    if len({str(row.get("fid")) for row in rows}) != len(rows):
        raise SystemExit("duplicate FID in EPL/La Liga ESPN conflict evidence")
    accepted_scores = {str(r["fid"]): str(r["verified_FT"]) for r in accepted_ft_rows}
    verified = []
    for row in rows:
        fid = str(row.get("fid") or "")
        if fid not in existing or fid in accepted_scores:
            raise SystemExit(f"EPL/La Liga conflict FID absent or also new overlay FID: {fid}")
        # Reuse the same raw ESPN and TotalCorner identity verification; the
        # score must conflict with, and preserve, an existing verified source.
        raw_rows, validated = verified_epl_laliga_espn_rows_from_single(row, existing)
        del raw_rows
        if len(validated) != 1:
            raise SystemExit(f"EPL/La Liga conflict evidence not uniquely verified: {fid}")
        old_scores = set()
        fixture = existing[fid]
        for key in ("totalcorner_page_records", "M1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
            for src in fixture.get(key, []):
                if str(src.get("status") or "").lower() == "full" and str(src.get("home_goals", "")).isdigit() and str(src.get("away_goals", "")).isdigit():
                    old_scores.add(f"{int(src['home_goals'])}:{int(src['away_goals'])}")
        if not old_scores or not old_scores.intersection(set(row.get("existing_totalcorner_scores") or [])):
            raise SystemExit(f"EPL/La Liga conflict lacks corroborated old FT evidence: {fid}")
        if str(row.get("verified_FT")) in old_scores:
            raise SystemExit(f"EPL/La Liga score marked conflict but matches stored FT: {fid}")
        verified.append(row)
    return rows, verified


def verified_epl_laliga_espn_rows_from_single(row, existing):
    """Validate a one-row conflict using the same raw response and identity rules."""
    # The 12 conflict rows are a strict subset of the accepted source records,
    # but the standalone overlay uses a different file. Reconstruct a tiny
    # temporary view through the same verifier without writing files.
    fid = str(row.get("fid") or "")
    fixture = existing.get(fid)
    if (not fixture
            or str(row.get("provider_league_id")) != str(fixture.get("provider_league_id"))
            or str(row.get("kickoff_utc")) != fixture.get("totalcorner_kickoff_utc")):
        raise SystemExit(f"EPL/La Liga conflict canonical identity mismatch: {fid}")
    raw = CROWN_DATA_ROOT / str(row.get("source_raw_file") or "")
    raw_sha = str(row.get("source_raw_sha256") or "")
    if not raw.is_file() or sha256(raw) != raw_sha:
        raise SystemExit(f"EPL/La Liga conflict raw SHA mismatch: {fid}")
    body = json.loads(raw.read_text(encoding="utf-8"))
    events = [e for e in body.get("events", []) if str(e.get("id")) == str(row.get("source_event_id"))]
    if len(events) != 1:
        raise SystemExit(f"EPL/La Liga conflict ESPN event ID not unique: {fid}")
    event = events[0]
    comps = event.get("competitions") or []
    if len(comps) != 1:
        raise SystemExit(f"EPL/La Liga conflict ESPN competition ambiguous: {fid}")
    comp = comps[0]
    st = (comp.get("status") or {}).get("type") or {}
    if st.get("name") != "STATUS_FULL_TIME" or not st.get("completed"):
        raise SystemExit(f"EPL/La Liga conflict ESPN event not FT: {fid}")
    sides = comp.get("competitors") or []
    home = [x for x in sides if x.get("homeAway") == "home"]
    away = [x for x in sides if x.get("homeAway") == "away"]
    if len(home) != 1 or len(away) != 1:
        raise SystemExit(f"EPL/La Liga conflict ESPN sides ambiguous: {fid}")
    actual = f"{int(home[0]['score'])}:{int(away[0]['score'])}"
    if actual != row.get("verified_FT"):
        raise SystemExit(f"EPL/La Liga conflict raw score mismatch: {fid}")
    if parse_dt(event.get("date")) is None or parse_dt(event.get("date")).isoformat().replace("+00:00", "Z") != row.get("source_event_kickoff_utc"):
        raise SystemExit(f"EPL/La Liga conflict source event kickoff mismatch: {fid}")
    hname = (home[0].get("team") or {}).get("displayName") or (home[0].get("team") or {}).get("name")
    aname = (away[0].get("team") or {}).get("displayName") or (away[0].get("team") or {}).get("name")
    if normalized_name(hname) != normalized_name(row.get("espn_home_name_raw")) or normalized_name(aname) != normalized_name(row.get("espn_away_name_raw")):
        raise SystemExit(f"EPL/La Liga conflict raw team identity mismatch: {fid}")
    if not any(str(src.get("home_id")) == str(row.get("home_id")) and str(src.get("away_id")) == str(row.get("away_id"))
               and normalized_name(src.get("home_name")) == normalized_name(row.get("home_name")) and normalized_name(src.get("away_name")) == normalized_name(row.get("away_name"))
               for key in ("totalcorner_page_records", "M1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records")
               for src in fixture.get(key, [])):
        raise SystemExit(f"EPL/La Liga conflict TotalCorner identity mismatch: {fid}")
    if normalized_name(row.get("espn_home_mapped_name")) != normalized_name(row.get("home_name")) or normalized_name(row.get("espn_away_mapped_name")) != normalized_name(row.get("away_name")):
        raise SystemExit(f"EPL/La Liga conflict saved team map mismatch: {fid}")
    return [row], [row]
def main():
    existing = {}
    for row in read_gz(BASE):
        fid = str(row.get("fid") or "")
        if fid:
            existing[fid] = row
    baseline_ids = set(existing)
    source_rows = 0
    source_by_fid = collections.defaultdict(list)
    source_identity_conflicts = []
    counts = collections.defaultdict(lambda: collections.Counter())
    for row in read_gz(SUPP):
        fid = str(row.get("fid") or "")
        if not fid:
            continue
        source_rows += 1
        lid = str(row.get("provider_league_id") or "")
        year = scope_year(row)
        key = (lid, year if year is not None else "UNKNOWN_KICKOFF_YEAR")
        d = counts[key]
        d["supplemental_source_rows"] += 1
        if row.get("status_raw") == "full" and str(row.get("home_goals_raw", "")).isdigit() and str(row.get("away_goals_raw", "")).isdigit():
            d["verified_full_time_rows"] += 1
        else:
            d["unverified_or_nonfull_rows"] += 1
        if not row.get("kickoff_utc"):
            d["missing_kickoff_timestamp_rows"] += 1
        source_by_fid[fid].append(row)

    new_ids = set(source_by_fid) - baseline_ids
    overlap_ids = set(source_by_fid) & baseline_ids
    new_status_by_year = collections.defaultdict(collections.Counter)
    new_status_by_league = collections.defaultdict(collections.Counter)
    for fid in new_ids:
        for row in source_by_fid[fid]:
            y = scope_year(row)
            year_key = str(y) if y is not None else "UNKNOWN_KICKOFF_YEAR"
            lid = str(row.get("provider_league_id") or "")
            status = row.get("status_raw") == "full" and str(row.get("home_goals_raw", "")).isdigit() and str(row.get("away_goals_raw", "")).isdigit()
            for counter in (new_status_by_year[year_key], new_status_by_league[lid]):
                counter["new_unique_source_rows"] += 1
                counter["verified_full_time"] += int(status)
                counter["unverified_or_nonfull"] += int(not status)
                counter["missing_kickoff"] += int(not row.get("kickoff_utc"))
    for fid, versions in source_by_fid.items():
        if fid in existing:
            target = existing[fid]
            target.setdefault("supplemental_schedule_records", [])
            for row in versions:
                target["supplemental_schedule_records"].append(normalize(row)["supplemental_schedule_records"][0])
            # Preserve the original canonical year/kickoff; source discrepancies
            # remain explicit in the record-version provenance.
        else:
            normalized = normalize(versions[0])
            # Preserve every source version for a FID, not only the first.
            normalized["supplemental_schedule_records"] = [normalize(v)["supplemental_schedule_records"][0] for v in versions]
            if len(versions) > 1:
                source_identity_conflicts.append({"fid": fid, "source_versions": len(versions), "resolution": "all_versions_preserved_no_overwrite"})
            existing[fid] = normalized

    external_ft_rows = verified_external_rows(EXTERNAL_FT)
    external_evidence_added = 0
    for row in external_ft_rows:
        fid = str(row["fid"])
        if fid not in existing:
            raise SystemExit(f"external FT FID outside merged schedule inventory: {fid}")
        fixture = existing[fid]
        expected_kickoff = parse_dt(fixture.get("totalcorner_kickoff_utc"))
        observed_kickoff = parse_dt(row.get("kickoff_utc"))
        identities = []
        for key in ("totalcorner_page_records", "M1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
            for src in fixture.get(key, []):
                ko = parse_dt(src.get("kickoff_utc"))
                hn, an = src.get("home_name"), src.get("away_name")
                if ko and hn and an:
                    identities.append((ko, normalized_name(hn), normalized_name(an)))
        expected = (observed_kickoff, normalized_name(row.get("Crown_home")), normalized_name(row.get("Crown_away")))
        # Different saved TotalCorner versions can carry a revised kickoff.
        # Require one exact source-version match and preserve the other
        # versions as evidence; a conflicting secondary version must not
        # silently erase a valid exact match.
        if not expected_kickoff or observed_kickoff != expected_kickoff or expected not in identities:
            raise SystemExit(f"external FT identity not corroborated by saved schedule versions for FID {fid}")
        evidence = {
            "source": "archived ESPN raw response; independently verified; not Crown odds",
            "verified_FT": row["verified_FT"],
            "source_event_id": row.get("source_event_id"),
            "source_raw_sha256": row.get("source_raw_sha256"),
            "source_raw_file": row.get("source_raw_file"),
            "kickoff_utc": row.get("kickoff_utc"),
            "home_name": row.get("Crown_home"),
            "away_name": row.get("Crown_away"),
            "crosswalk": row.get("crosswalk"),
        }
        existing_shas = {x.get("source_raw_sha256") for x in fixture.get("external_ft_evidence", [])}
        if evidence["source_raw_sha256"] not in existing_shas:
            fixture.setdefault("external_ft_evidence", []).append(evidence)
            external_evidence_added += 1

    m5_ft_rows = [json.loads(line) for line in M5_FT_OVERLAY.read_text(encoding="utf-8").splitlines() if line.strip()] if M5_FT_OVERLAY.exists() else []
    m5_evidence_added = 0
    for row in m5_ft_rows:
        fid = str(row.get("fid") or "")
        if fid not in existing:
            raise SystemExit(f"M5 FT FID outside merged schedule inventory: {fid}")
        fixture = existing[fid]
        raw_rel = str(row.get("raw_response_relative_path") or "")
        raw = M5_RAW_ROOT / raw_rel
        if not raw.is_file() or sha256(raw) != row.get("raw_response_sha256"):
            raise SystemExit(f"M5 raw response SHA mismatch for FID {fid}")
        response = json.loads(raw.read_text(encoding="utf-8"))
        raw_events = [x for x in response.get("data", []) if str(x.get("id")) == fid]
        if response.get("success") not in (1, "1", True) or len(raw_events) != 1:
            raise SystemExit(f"M5 raw response does not contain one successful exact FID: {fid}")
        event = raw_events[0]
        try:
            raw_score = (int(event["hg"]), int(event["ag"]))
            indexed_score = (int(row["home_goals"]), int(row["away_goals"]))
        except (KeyError, TypeError, ValueError):
            raise SystemExit(f"M5 raw score is invalid for FID {fid}")
        if event.get("status") != "full" or raw_score != indexed_score:
            raise SystemExit(f"M5 raw FT status or score mismatch for FID {fid}")
        if str(event.get("l_id")) != str(fixture.get("provider_league_id")) or row.get("kickoff_utc") != fixture.get("totalcorner_kickoff_utc"):
            raise SystemExit(f"M5 league or kickoff mismatch for FID {fid}")
        identity_source_rows = fixture.get("totalcorner_page_records", []) + fixture.get("M1_history_cache_records", [])
        identity_ok = any(
            str(src.get("home_id")) == str(event.get("h_id"))
            and str(src.get("away_id")) == str(event.get("a_id"))
            and normalized_name(src.get("home_name")) == normalized_name(event.get("h"))
            and normalized_name(src.get("away_name")) == normalized_name(event.get("a"))
            for src in identity_source_rows
        )
        if not identity_ok:
            raise SystemExit(f"M5 team identity mismatch for FID {fid}")
        evidence = {
            "status": "verified_ft",
            "home_goals": raw_score[0],
            "away_goals": raw_score[1],
            "kickoff_utc": row.get("kickoff_utc"),
            "home_id": row.get("home_id"),
            "away_id": row.get("away_id"),
            "home_name": row.get("home_name"),
            "away_name": row.get("away_name"),
            "source": row.get("source"),
            "response_received_at_utc": row.get("response_received_at_utc"),
            "raw_response_sha256": row.get("raw_response_sha256"),
            "raw_response_relative_path": raw_rel,
            "index_file_sha256": row.get("index_file_sha256"),
        }
        fixture.setdefault("m5_result_evidence_records", [])
        if not any(x.get("raw_response_sha256") == evidence["raw_response_sha256"] for x in fixture["m5_result_evidence_records"]):
            fixture["m5_result_evidence_records"].append(evidence)
            m5_evidence_added += 1

    crown_ft_rows = [json.loads(line) for line in CROWN_FT_OVERLAY.read_text(encoding="utf-8").splitlines() if line.strip()] if CROWN_FT_OVERLAY.exists() else []
    crown_ft_evidence_added = 0
    for row in crown_ft_rows:
        fid = str(row.get("fid") or "")
        if fid not in existing:
            raise SystemExit(f"Crown FT FID outside merged schedule inventory: {fid}")
        fixture = existing[fid]
        if row.get("capture_mode") != "historical":
            raise SystemExit(f"Crown FT overlay contains non-historical row: {fid}")
        raw_rel = str(row.get("raw_response_relative_path") or "")
        raw = CROWN_DATA_ROOT / raw_rel
        if not raw.is_file() or sha256(raw) != row.get("raw_response_sha256"):
            raise SystemExit(f"Crown raw response SHA mismatch for FID {fid}")
        response = json.loads(raw.read_text(encoding="utf-8"))
        raw_events = [x for x in response.get("data", []) if str(x.get("id")) == fid]
        if response.get("success") not in (1, "1", True) or len(raw_events) != 1:
            raise SystemExit(f"Crown raw response does not contain one successful exact FID: {fid}")
        event = raw_events[0]
        try:
            raw_score = (int(event["hg"]), int(event["ag"]))
            indexed_score = (int(row["home_goals"]), int(row["away_goals"]))
        except (KeyError, TypeError, ValueError):
            raise SystemExit(f"Crown raw score invalid for FID {fid}")
        if event.get("status") != "full" or raw_score != indexed_score:
            raise SystemExit(f"Crown raw FT status or score mismatch for FID {fid}")
        if str(event.get("l_id")) != str(fixture.get("provider_league_id")) or row.get("kickoff_utc") != fixture.get("totalcorner_kickoff_utc"):
            raise SystemExit(f"Crown FT league or kickoff mismatch for FID {fid}")
        identity_source_rows = fixture.get("totalcorner_page_records", []) + fixture.get("M1_history_cache_records", []) + fixture.get("supplemental_schedule_records", [])
        identity_ok = any(
            str(src.get("home_id")) == str(event.get("h_id"))
            and str(src.get("away_id")) == str(event.get("a_id"))
            and normalized_name(src.get("home_name")) == normalized_name(event.get("h"))
            and normalized_name(src.get("away_name")) == normalized_name(event.get("a"))
            for src in identity_source_rows
        )
        if not identity_ok:
            raise SystemExit(f"Crown FT team identity mismatch for FID {fid}")
        evidence = {
            "status": "full",
            "home_goals": raw_score[0],
            "away_goals": raw_score[1],
            "kickoff_utc": row.get("kickoff_utc"),
            "home_id": row.get("home_id"),
            "away_id": row.get("away_id"),
            "home_name": row.get("home_name"),
            "away_name": row.get("away_name"),
            "source": row.get("source"),
            "capture_key": row.get("capture_key"),
            "data_layer": row.get("data_layer"),
            "capture_status": row.get("capture_status"),
            "quote_count": row.get("quote_count"),
            "response_received_at_utc": row.get("response_received_at_utc"),
            "raw_response_sha256": row.get("raw_response_sha256"),
            "raw_response_relative_path": raw_rel,
        }
        fixture.setdefault("crown_ft_evidence_records", [])
        if not any(x.get("raw_response_sha256") == evidence["raw_response_sha256"] for x in fixture["crown_ft_evidence_records"]):
            fixture["crown_ft_evidence_records"].append(evidence)
            crown_ft_evidence_added += 1

    epl_laliga_rows, epl_laliga_verified = verified_epl_laliga_espn_rows(EPL_LALIGA_ESPN_FT_OVERLAY, existing)
    epl_laliga_conflict_rows, epl_laliga_conflicts_verified = verified_epl_laliga_conflicts(EPL_LALIGA_ESPN_CONFLICTS, existing, epl_laliga_verified)
    epl_laliga_evidence_added = 0
    for row in epl_laliga_verified:
        fixture = existing[str(row["fid"])]
        evidence = {
            "status": "verified_ft",
            "home_goals": int(str(row["verified_FT"]).split(":")[0]),
            "away_goals": int(str(row["verified_FT"]).split(":")[1]),
            "kickoff_utc": row["kickoff_utc"],
            "source_event_kickoff_utc": row["source_event_kickoff_utc"],
            "kickoff_difference_seconds_vs_inventory": row["kickoff_difference_seconds_vs_inventory"],
            "home_id": row["home_id"],
            "away_id": row["away_id"],
            "home_name": row["home_name"],
            "away_name": row["away_name"],
            "source": row["source"],
            "source_event_id": row["source_event_id"],
            "source_raw_sha256": row["source_raw_sha256"],
            "source_raw_file": row["source_raw_file"],
            "response_status": row["response_status"],
            "crosswalk": row["crosswalk"],
            "crosswalk_totalcorner_identity_source_keys": row["crosswalk_totalcorner_identity_source_keys"],
        }
        fixture.setdefault("external_ft_evidence", [])
        if not any(x.get("source_raw_sha256") == evidence["source_raw_sha256"] and str(x.get("source_event_id")) == str(evidence["source_event_id"]) for x in fixture["external_ft_evidence"]):
            fixture["external_ft_evidence"].append(evidence)
            epl_laliga_evidence_added += 1

    epl_laliga_conflict_evidence_added = 0
    for row in epl_laliga_conflicts_verified:
        fixture = existing[str(row["fid"])]
        evidence = {
            "source": row["source"],
            "source_event_id": row["source_event_id"],
            "source_event_kickoff_utc": row["source_event_kickoff_utc"],
            "source_raw_sha256": row["source_raw_sha256"],
            "source_raw_file": row["source_raw_file"],
            "status": row["response_status"],
            "external_verified_FT": row["verified_FT"],
            "existing_totalcorner_scores": row["existing_totalcorner_scores"],
            "conflict_resolution": row["conflict_resolution"],
            "crosswalk": row["crosswalk"],
        }
        fixture.setdefault("external_ft_conflicts", [])
        if not any(x.get("source_raw_sha256") == evidence["source_raw_sha256"] and str(x.get("source_event_id")) == str(evidence["source_event_id"]) for x in fixture["external_ft_conflicts"]):
            fixture["external_ft_conflicts"].append(evidence)
            epl_laliga_conflict_evidence_added += 1

    with OUT.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            for fid in sorted(existing, key=lambda z: (existing[z].get("provider_league_id", ""), existing[z].get("year") or 9999, z)):
                gz.write((json.dumps(existing[fid], ensure_ascii=False, separators=(",", ":")) + "\n").encode())

    # Uniqueness and integrity checks on the persisted output.
    seen = set()
    persisted = 0
    for row in read_gz(OUT):
        fid = str(row.get("fid") or "")
        if fid in seen:
            raise SystemExit(f"duplicate FID in output: {fid}")
        seen.add(fid)
        persisted += 1
    if persisted != len(existing) or len(seen) != len(existing):
        raise SystemExit("persisted inventory count mismatch")
    merged_verified_ft = sum(has_verified_ft(row) for row in existing.values())
    unverified_by_league_year = collections.defaultdict(collections.Counter)
    unverified_count = 0
    with UNVERIFIED.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            for fid in sorted(existing, key=lambda z: (existing[z].get("provider_league_id", ""), existing[z].get("year") or 9999, z)):
                row = existing[fid]
                if has_verified_ft(row):
                    continue
                unverified_count += 1
                sources = []
                for key in ("totalcorner_page_records", "M1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records", "m5_result_evidence_records", "crown_ft_evidence_records", "external_ft_conflicts"):
                    for x in row.get(key, []):
                        sources.append({k: x.get(k) for k in ("status", "home_goals", "away_goals", "kickoff_utc", "provider_league_id", "league_name", "home_id", "away_id", "home_name", "away_name", "source_file", "page_file", "source_response_sha256", "source_record_sha256") if k in x})
                year = row.get("year") if row.get("year") is not None else "UNKNOWN_KICKOFF_YEAR"
                key = (str(row.get("provider_league_id") or ""), str(year))
                unverified_by_league_year[key]["unverified_FT_fids"] += 1
                candidate = {"fid": fid, "provider_league_id": row.get("provider_league_id"), "utc_year": row.get("year"), "kickoff_utc": row.get("totalcorner_kickoff_utc"), "evidence_records": sources, "resolution_status": "no_verified_full_time_score_in_reconciled_sources"}
                gz.write((json.dumps(candidate, ensure_ascii=False, separators=(",", ":")) + "\n").encode())

    years = collections.defaultdict(collections.Counter)
    for fid, versions in source_by_fid.items():
        for row in versions:
            y = scope_year(row)
            years[y if y is not None else "UNKNOWN_KICKOFF_YEAR"]["unique_fids"] += int(row is versions[0])
    summary = {
        "generated_at_utc": dt.datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "method": "baseline inventory plus FID-deduplicated 53-league schedule artifact; append-only provenance; no Crown requests",
        "inputs": {
            str(BASE.name): {"sha256": sha256(BASE), "bytes": BASE.stat().st_size, "unique_fids": len(baseline_ids)},
            str(SUPP.name): {"sha256": sha256(SUPP), "bytes": SUPP.stat().st_size, "source_rows": source_rows, "unique_fids": len(source_by_fid)},
            str(EXTERNAL_FT.name): {"sha256": sha256(EXTERNAL_FT) if EXTERNAL_FT.exists() else None, "unique_fids": len(external_ft_rows), "source": "archived ESPN raw responses, strictly SHA/identity/FT verified"},
            str(M5_FT_OVERLAY.name): {"sha256": sha256(M5_FT_OVERLAY) if M5_FT_OVERLAY.exists() else None, "unique_fids": len(m5_ft_rows), "source": "authorized M5 TotalCorner result responses, strictly SHA/FID/identity/FT verified; not Crown odds"},
            str(CROWN_FT_OVERLAY.name): {"sha256": sha256(CROWN_FT_OVERLAY) if CROWN_FT_OVERLAY.exists() else None, "unique_fids": len(crown_ft_rows), "source": "existing historical Crown raw fixture responses, strictly SHA/FID/identity/FT verified; result only"},
            str(EPL_LALIGA_ESPN_FT_OVERLAY.name): {"sha256": sha256(EPL_LALIGA_ESPN_FT_OVERLAY) if EPL_LALIGA_ESPN_FT_OVERLAY.exists() else None, "unique_fids": len(epl_laliga_rows), "source": "saved raw ESPN season responses, strictly SHA/event/status/score and exact TotalCorner FID/team-ID identity verified"},
            str(EPL_LALIGA_ESPN_CONFLICTS.name): {"sha256": sha256(EPL_LALIGA_ESPN_CONFLICTS) if EPL_LALIGA_ESPN_CONFLICTS.exists() else None, "unique_fids": len(epl_laliga_conflict_rows), "source": "saved raw ESPN FT scores that conflict with preserved TotalCorner FT values; conflict evidence only, no score overwrite"},
        },
        "results": {
            "baseline_unique_fids": len(baseline_ids),
            "supplemental_source_rows": sum(len(rows) for rows in source_by_fid.values()),
            "supplemental_unique_fids": len(source_by_fid),
            "supplemental_overlap_fids": len(overlap_ids),
            "supplemental_new_unique_fids": len(new_ids),
            "merged_unique_fids": len(existing),
            "merged_verified_FT_fids": merged_verified_ft,
            "merged_unverified_FT_fids": len(existing) - merged_verified_ft,
            "strictly_reconciled_archived_external_FT_fids": len(external_ft_rows),
            "new_archived_external_FT_evidence_rows_added": external_evidence_added,
            "strictly_reconciled_M5_FT_fids": len(m5_ft_rows),
            "new_M5_FT_evidence_rows_added": m5_evidence_added,
            "strictly_reconciled_historical_Crown_FT_fids": len(crown_ft_rows),
            "new_historical_Crown_FT_evidence_rows_added": crown_ft_evidence_added,
            "strictly_reconciled_EPL_La_Liga_ESPN_FT_fids": len(epl_laliga_verified),
            "new_EPL_La_Liga_ESPN_FT_evidence_rows_added": epl_laliga_evidence_added,
            "strictly_reconciled_EPL_La_Liga_ESPN_score_conflicts": len(epl_laliga_conflicts_verified),
            "new_EPL_La_Liga_ESPN_conflict_evidence_rows_added": epl_laliga_conflict_evidence_added,
            "unverified_queue_rows": unverified_count,
            "identity_conflicts_overwritten": 0,
            "source_fids_with_multiple_versions_preserved": len(source_identity_conflicts),
            "unknown_kickoff_year_unique_fids": sum(1 for fid, rows in source_by_fid.items() if all(scope_year(r) is None for r in rows)),
            "new_unique_status_by_utc_year": {k: dict(v) for k, v in sorted(new_status_by_year.items())},
            "new_unique_status_by_provider_league": {k: dict(v) for k, v in sorted(new_status_by_league.items())},
        },
        "source_by_league_utc_year": [
            {"provider_league_id": lid, "utc_year": year, **dict(counter)}
            for (lid, year), counter in sorted(counts.items(), key=lambda x: (x[0][0], str(x[0][1])))
        ],
        "source_unique_fids_by_utc_year": {str(k): v["unique_fids"] for k, v in sorted(years.items(), key=lambda x: str(x[0]))},
        "unverified_FT_by_provider_league_utc_year": [
            {"provider_league_id": lid, "utc_year": year, **dict(counter)}
            for (lid, year), counter in sorted(unverified_by_league_year.items())
        ],
        "source_identity_conflicts": source_identity_conflicts,
        "output": {"file": OUT.name, "sha256": sha256(OUT), "bytes": OUT.stat().st_size, "unique_fids": persisted},
        "unverified_ft_queue": {"file": UNVERIFIED.name, "sha256": sha256(UNVERIFIED), "bytes": UNVERIFIED.stat().st_size, "unique_fids": unverified_count},
        "scope_caveat": "This reconciles the audited 53-league schedule batch with the committed baseline only; it does not claim all leagues, FT gaps, or Crown history are complete. Missing kickoff dates remain unassigned to a UTC year; season metadata absent at source remains absent.",
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"results": summary["results"], "output": summary["output"], "summary": str(SUMMARY)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
