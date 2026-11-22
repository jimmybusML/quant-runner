# M8 Stadium Elevation Research

Research-only study of a pregame prior-home-ground elevation differential versus Crown AH pricing. The original eight groups and all production paths remain frozen.

## Reproduction

From the repository root, with the existing local research data files and Crown SQLite available:

1. `python3 research/m8/stadium_elevation_20261121/prepare_altitude_targets.py`
2. `python3 research/m8/stadium_elevation_20261121/audit_new15_venue_linkage.py`
3. `python3 research/m8/stadium_elevation_20261121/merge_expanded15_geocode_queries.py`
4. `python3 research/m8/stadium_elevation_20261121/geocode_prior_venues_nominatim.py` (uses cached results; uncached requests run sequentially at no more than one per second)
5. `python3 research/m8/stadium_elevation_20261121/build_venue_coordinate_catalog.py`
6. `python3 research/m8/stadium_elevation_20261121/fetch_srtm90_elevation.py` (uses cached batches; requests at most 100 coordinates per call)
7. `python3 research/m8/stadium_elevation_20261121/audit_new15_venue_linkage.py`
8. `python3 research/m8/stadium_elevation_20261121/run_stadium_elevation_ah.py`
9. `python3 research/m8/stadium_elevation_20261121/verify_stadium_elevation_crown_ft_20261121.py`
10. `python3 research/m8/stadium_elevation_20261121/build_sha256_manifest.py`

The first venue-linkage audit can be run before geocoding to inventory the additional venue queries. Nominatim requests are single-machine, single-thread, cached, and throttled; consult its linked current usage policy before repeating any uncached request. The SRTM API response bodies and hashes are retained under `srtm90m_raw/` and in the manifest.

Main report: [M8_STADIUM_ELEVATION_AH_RESEARCH_20261121.md](M8_STADIUM_ELEVATION_AH_RESEARCH_20261121.md). Full per-year, ISO-week, month, league, and settlement detail: `altitude_crown_ah_summary_20261121.json`.
