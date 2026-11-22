#!/usr/bin/env python3
"""Strictly reconcile the saved EPL/La Liga ESPN FT archive to current FIDs.

This is an offline result-evidence audit. It does not read Crown prices as FT,
issue network requests, or modify SQLite. The compiled fixture table is used
only as the preserved FID crosswalk; accepted scores must be found in the raw
ESPN season archive with STATUS_FULL_TIME and match exact inventory kickoff and
home/away identities.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent
DATA = pathlib.Path("/Users/mac/QuantAsiaDesk/data")
PACKAGE = DATA / "epl_laliga_crown_5seasons"
ESPN_DIR = PACKAGE / "espn_source"
CSV = PACKAGE / "英超_西甲_2021-22至2025-26_Crown亚洲盘.csv"
ENRICHMENT = PACKAGE / "espn_verified_enrichment.json"
TEAM_REVIEW = PACKAGE / "espn_identity_review.json"
INVENTORY = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
BASELINE_UNVERIFIED = ROOT / "unverified_FT_candidates_pre_epl_laliga_20261122.jsonl.gz"
OVERLAY = ROOT / "epl_laliga_espn_verified_ft_overlay_20261122.jsonl"
CONFLICTS = ROOT / "epl_laliga_espn_verified_ft_conflicts_20261122.jsonl"
SUMMARY = ROOT / "epl_laliga_espn_ft_archive_reconciliation_20261122.json"
UTC = dt.timezone.utc
SHANGHAI = dt.timezone(dt.timedelta(hours=8))
LEAGUES = {
    "England Premier League": {"id": "1", "name": "England Premier League", "slug": "eng_1"},
    "Spain La Liga": {"id": "14", "name": "Spain La Liga", "slug": "esp_1"},
}


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def norm(value) -> str:
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


def parse_crown_start(value):
    if not value:
        return None
    try:
        return dt.datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S").replace(tzinfo=SHANGHAI).astimezone(UTC)
    except (TypeError, ValueError):
        return None


def read_gzip_jsonl(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def schedule_sources(fixture):
    out = []
    for key in ("totalcorner_page_records", "M1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
        out.extend((key, x) for x in fixture.get(key, []))
    return out


def raw_espn_event(event_id, events_by_id):
    found = events_by_id.get(str(event_id), [])
    if len(found) != 1:
        raise ValueError(f"ESPN event ID is not unique: {event_id} ({len(found)})")
    return found[0]


def extract_ft(event):
    comps = event.get("competitions") or []
    if len(comps) != 1:
        raise ValueError("ESPN event competition is not unique")
    comp = comps[0]
    status = (comp.get("status") or {}).get("type") or {}
    if status.get("name") != "STATUS_FULL_TIME" or not status.get("completed"):
        raise ValueError("raw ESPN event is not verified full time")
    competitors = comp.get("competitors") or []
    home = [x for x in competitors if x.get("homeAway") == "home"]
    away = [x for x in competitors if x.get("homeAway") == "away"]
    if len(home) != 1 or len(away) != 1:
        raise ValueError("raw ESPN home/away competitors are not unique")
    h, a = home[0], away[0]
    try:
        hg, ag = int(h["score"]), int(a["score"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("raw ESPN FT score is invalid")
    hn = (h.get("team") or {}).get("displayName") or (h.get("team") or {}).get("name")
    an = (a.get("team") or {}).get("displayName") or (a.get("team") or {}).get("name")
    if not hn or not an:
        raise ValueError("raw ESPN team name is missing")
    return comp, hg, ag, str(hn), str(an)


def verify_fixture_crosswalk(fid, csv_row, fixture, event, team_map, enrichment_home, enrichment_away, expected_hg, expected_ag):
    ko_csv = parse_utc(csv_row["比赛日期时间_UTC"])
    ko_event = parse_utc(event.get("date"))
    ko_inventory = parse_utc(fixture.get("totalcorner_kickoff_utc"))
    if not ko_csv or ko_csv != ko_event or not ko_inventory:
        raise ValueError("compiled CSV and raw ESPN event UTC kickoff mismatch or missing inventory kickoff")
    if norm(csv_row["主队名称"]) != norm(enrichment_home) or norm(csv_row["客队名称"]) != norm(enrichment_away):
        raise ValueError("compiled canonical names differ from saved ESPN enrichment")
    comp, hg, ag, raw_home, raw_away = extract_ft(event)
    mapped_home, mapped_away = team_map.get(raw_home), team_map.get(raw_away)
    if not mapped_home or not mapped_away:
        raise ValueError("raw ESPN team missing from saved one-to-one identity map")
    if norm(mapped_home) != norm(csv_row["主队名称"]) or norm(mapped_away) != norm(csv_row["客队名称"]):
        raise ValueError("raw ESPN home/away identity does not map to exact compiled fixture")
    if (hg, ag) != (int(csv_row["最终比分_主队进球"]), int(csv_row["最终比分_客队进球"])):
        raise ValueError("raw ESPN score differs from preserved compiled result row")
    if (hg, ag) != (int(expected_hg), int(expected_ag)):
        raise ValueError("raw ESPN score differs from saved verification row")
    if len(comp.get("competitors") or []) != 2:
        raise ValueError("raw ESPN competitor count is not two")
    if str(csv_row["比赛ID"]) != fid:
        raise ValueError("compiled row FID mismatch")
    if not str(csv_row.get("赛果来源") or "").startswith("ESPN"):
        raise ValueError("compiled result source is not an ESPN-verified row")
    identities = set()
    for _, source in schedule_sources(fixture):
        if not source.get("home_name") or not source.get("away_name"):
            continue
        ko = parse_utc(source.get("kickoff_utc"))
        if not ko:
            continue
        identities.add((str(source.get("provider_league_id") or fixture.get("provider_league_id") or ""),
                        ko.isoformat(), str(source.get("home_id") or ""), str(source.get("away_id") or ""),
                        norm(source.get("home_name")), norm(source.get("away_name"))))
    matched = [x for x in identities if x[0] == str(fixture.get("provider_league_id"))
               and x[2] and x[3] and x[4] == norm(csv_row["主队名称"]) and x[5] == norm(csv_row["客队名称"])]
    if not matched:
        raise ValueError("exact TotalCorner FID team-ID/home-away identity missing")
    if len({(x[2], x[3], x[4], x[5]) for x in matched}) != 1:
        raise ValueError("conflicting TotalCorner team-ID identities for exact FID")
    home_id, away_id = matched[0][2], matched[0][3]
    return ko_inventory, ko_event, hg, ag, raw_home, raw_away, mapped_home, mapped_away, home_id, away_id


def validate_crosswalk(fid, row, fixture, league, events_by_id, identity_review):
    meta = LEAGUES[league]
    if str(fixture.get("provider_league_id")) != meta["id"]:
        raise ValueError("FID provider league ID does not match EPL/La Liga source")
    if str(row.get("比赛ID")) != fid:
        raise ValueError("CSV exact FID does not match enrichment FID")
    season = int(str(row["赛季"]).split("/")[0])
    map_key = f"{league}|{season}"
    team_map = identity_review.get(map_key, {}).get("team_map", {})
    if not team_map:
        raise ValueError("saved ESPN-to-TotalCorner team map is missing")
    event = raw_espn_event(row["__espn_id"], events_by_id)
    return event, team_map, season, meta


def main():
    inventory = {str(r["fid"]): r for r in read_gzip_jsonl(INVENTORY)}
    gap = {str(r["fid"]): r for r in read_gzip_jsonl(BASELINE_UNVERIFIED)}
    enrichment = json.loads(ENRICHMENT.read_text(encoding="utf-8"))
    identity_review = json.loads(TEAM_REVIEW.read_text(encoding="utf-8"))

    csv_by_fid = {}
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            fid = str(row.get("比赛ID") or "")
            if not fid or fid in csv_by_fid:
                raise SystemExit(f"missing or duplicate FID in compiled 3,800-row fixture file: {fid}")
            csv_by_fid[fid] = row

    events_by_id = collections.defaultdict(list)
    raw_hashes = {}
    for league, meta in LEAGUES.items():
        for season in range(2021, 2027):
            path = ESPN_DIR / f"{meta['slug']}_{season}.json"
            raw_hashes[str(path.relative_to(DATA))] = sha(path)
            body = json.loads(path.read_text(encoding="utf-8"))
            for event in body.get("events", []):
                events_by_id[str(event.get("id"))].append((path, event))

    supplemental = {str(r["match_id"]): r for r in enrichment.get("supplemental", []) if str(r.get("match_id", "")).isdigit()}
    if len(supplemental) != enrichment.get("supplemented"):
        raise SystemExit("supplemental enrichment FIDs are not unique TotalCorner IDs")
    corrections = enrichment.get("corrections", {})
    accepted = []
    accepted_overlap = []
    conflict_rows = []
    rejects = collections.Counter()
    rejection_examples = collections.defaultdict(list)
    current_unverified = set(gap)

    def audit_item(fid, league, event_id, expected_h, expected_a, expected_hg, expected_ag, csv_row, correction=False):
        if fid not in inventory:
            raise ValueError("FID absent from reconciled inventory")
        if fid not in csv_by_fid or csv_by_fid[fid] is not csv_row:
            raise ValueError("FID is not uniquely present in preserved 3,800-row fixture CSV")
        if str(event_id) not in events_by_id or len(events_by_id[str(event_id)]) != 1:
            raise ValueError("ESPN event ID missing or ambiguous in saved season responses")
        path, event = events_by_id[str(event_id)][0]
        meta = LEAGUES[league]
        map_key = f"{league}|{int(str(csv_row['赛季']).split('/')[0])}"
        team_map = identity_review.get(map_key, {}).get("team_map", {})
        if not team_map:
            raise ValueError("saved team identity map missing")
        fixture = inventory[fid]
        (inventory_ko, source_event_ko, hg, ag, raw_home, raw_away,
         mapped_home, mapped_away, home_id, away_id) = verify_fixture_crosswalk(
            fid, csv_row, fixture, event, team_map, expected_h, expected_a, expected_hg, expected_ag
        )
        if (hg, ag) != (int(expected_hg), int(expected_ag)):
            raise ValueError("raw ESPN score mismatch")
        raw_rel = str(path.relative_to(DATA))
        raw_sha = raw_hashes[raw_rel]
        return {
            "fid": fid,
            "provider_league_id": meta["id"],
            "provider_league_name": meta["name"],
            "kickoff_utc": inventory_ko.isoformat().replace("+00:00", "Z"),
            "source_event_kickoff_utc": source_event_ko.isoformat().replace("+00:00", "Z"),
            "kickoff_difference_seconds_vs_inventory": int((source_event_ko - inventory_ko).total_seconds()),
            "home_id": home_id,
            "away_id": away_id,
            "home_name": csv_row["主队名称"],
            "away_name": csv_row["客队名称"],
            "verified_FT": f"{hg}:{ag}",
            "source": "ESPN league-season raw archive STATUS_FULL_TIME; not Crown odds",
            "source_event_id": str(event_id),
            "source_raw_sha256": raw_sha,
            "source_raw_file": raw_rel,
            "source_raw_provider_response": True,
            "response_status": "STATUS_FULL_TIME",
            "crosswalk": "exact ESPN event ID + exact UTC kickoff + saved exact TotalCorner FID and home/away IDs/names; no name-only join",
            "espn_home_name_raw": raw_home,
            "espn_away_name_raw": raw_away,
            "espn_home_mapped_name": mapped_home,
            "espn_away_mapped_name": mapped_away,
            "crosswalk_totalcorner_identity_source_keys": sorted({k for k, source in schedule_sources(fixture)
                if str(source.get("home_id")) == home_id and str(source.get("away_id")) == away_id
                and norm(source.get("home_name")) == norm(csv_row["主队名称"])
                and norm(source.get("away_name")) == norm(csv_row["客队名称"])}),
            "crosswalk_kind": "score_evidence" if not correction else "score_conflict_evidence",
        }

    for fid, row in supplemental.items():
        try:
            if fid not in csv_by_fid:
                raise ValueError("supplemental TotalCorner FID missing from compiled fixture dataset")
            csv_row = csv_by_fid[fid]
            league = "England Premier League" if row["league"] == "England Premier League" else "Spain La Liga"
            if row["league"] not in LEAGUES:
                raise ValueError("unsupported league")
            rec = audit_item(fid, league, row["espn_id"], row["home"], row["away"], row["home_goals"], row["away_goals"], csv_row)
            if fid in current_unverified:
                accepted.append(rec)
            else:
                accepted_overlap.append(rec)
        except Exception as exc:
            rejects[str(exc)] += 1
            rejection_examples[str(exc)].append(fid)

    for fid, corr in corrections.items():
        try:
            fid = str(fid)
            csv_row = csv_by_fid[fid]
            league = "England Premier League" if csv_row["联赛名称"] == "英格兰超级联赛" else "Spain La Liga"
            rec = audit_item(fid, league, corr["espn_id"], csv_row["主队名称"], csv_row["客队名称"], corr["hg"], corr["ag"], csv_row, correction=True)
            old = (int(corr["tc_hg"]), int(corr["tc_ag"]))
            fixture = inventory[fid]
            existing_scores = set()
            for key, source in schedule_sources(fixture):
                if str(source.get("status") or "").lower() == "full" and str(source.get("home_goals", "")).isdigit() and str(source.get("away_goals", "")).isdigit():
                    existing_scores.add((int(source["home_goals"]), int(source["away_goals"])))
            if old not in existing_scores:
                raise ValueError("TotalCorner correction baseline score not present in inventory sources")
            if old == tuple(map(int, rec["verified_FT"].split(":"))):
                raise ValueError("correction does not conflict with saved source score")
            rec["existing_totalcorner_scores"] = [f"{a}:{b}" for a, b in sorted(existing_scores)]
            rec["conflict_resolution"] = "both scores retained; no canonical score overwritten"
            conflict_rows.append(rec)
        except Exception as exc:
            rejects[f"correction:{exc}"] += 1
            rejection_examples[f"correction:{exc}"].append(str(fid))

    if rejects:
        raise SystemExit(json.dumps({"rejects": dict(rejects), "examples": dict(rejection_examples)}, ensure_ascii=False))
    if len(accepted) != 42 or len(accepted_overlap) != 1 or len(conflict_rows) != 12:
        raise SystemExit(f"unexpected accepted counts: new={len(accepted)} overlap={len(accepted_overlap)} conflicts={len(conflict_rows)}")
    if len({r["fid"] for r in accepted}) != len(accepted) or len({r["fid"] for r in conflict_rows}) != len(conflict_rows):
        raise SystemExit("duplicate FIDs in accepted overlays")

    for path, rows in ((OVERLAY, accepted), (CONFLICTS, conflict_rows)):
        with path.open("w", encoding="utf-8") as f:
            for row in sorted(rows, key=lambda x: x["fid"]):
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    result = {
        "generated_at_utc": dt.datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "purpose": "Existing EPL/La Liga FT evidence reconciliation only; no model, betting, or Crown price source substitution.",
        "csv_input": {"path_relative_to_data": str(CSV.relative_to(DATA)), "sha256": sha(CSV), "rows": len(csv_by_fid), "unique_fids": len(csv_by_fid)},
        "enrichment_input": {"sha256": sha(ENRICHMENT), "supplemental_rows": len(supplemental), "score_corrections": len(corrections), "identity_ambiguous": enrichment.get("identity_ambiguous")},
        "team_identity_review_input": {"sha256": sha(TEAM_REVIEW), "league_season_maps": len(identity_review)},
        "inventory_input": {"sha256": sha(INVENTORY), "unique_fids": len(inventory)},
        "baseline_unverified_queue_input": {"file": BASELINE_UNVERIFIED.name, "sha256": sha(BASELINE_UNVERIFIED), "fids": len(gap)},
        "raw_espn_season_responses": {"files": len(raw_hashes), "sha256_by_relative_path": dict(sorted(raw_hashes.items()))},
        "results": {
            "supplemental_rows_raw_verified": len(accepted) + len(accepted_overlap),
            "new_verified_ft_fids_in_current_gap": len(accepted),
            "already_verified_same_score_fids": len(accepted_overlap),
            "score_conflicts_verified_and_retained": len(conflict_rows),
            "raw_sha_fid_status_kickoff_identity_failures": dict(rejects),
            "network_requests": 0,
            "crown_prices_used_for_ft": 0,
        },
        "outputs": {
            OVERLAY.name: {"sha256": sha(OVERLAY), "rows": len(accepted)},
            CONFLICTS.name: {"sha256": sha(CONFLICTS), "rows": len(conflict_rows)},
        },
        "caveat": "Crown raw files are used only to verify exact fixture identity and FID; their partial match status/score is not used as FT. The accepted FT comes from raw ESPN STATUS_FULL_TIME responses. All historical sources remain separately attributed.",
    }
    SUMMARY.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"results": result["results"], "outputs": result["outputs"], "summary": str(SUMMARY)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
