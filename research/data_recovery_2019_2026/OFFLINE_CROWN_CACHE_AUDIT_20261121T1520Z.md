# Offline Crown raw-cache coverage audit — 2026-11-21T15:20:05Z

This was a read-only audit. No Crown or TotalCorner API request and no SQLite write was performed. The existing TotalCorner schedule collector remained a separate live process (PID 10634).

## Results

- Current reconciled target-period inventory: 133,549 unique FIDs, source inventory SHA256 `793133ccbc3f3cd24a4e91ac433cec1ba746803cfefeec64c439758337d7c0e6`.
- Existing raw Crown response files checked: 104,365; valid exact-FID/Crown identity response records: 103,293; all raw file SHA values matched an existing SQLite source SHA anchor (104,365/104,365); parse/identity issues: 0; unanchored raw files: 0.
- Historical movement: 52,999 FIDs / 4,429,709 quote rows; all matching raw response hashes were already indexed in the movement layer.
- Historical summary: 49,054 unique FIDs / 99,242 quote rows; all matching raw response hashes were already indexed in the summary layer.
- The 19,429 FIDs in the normalized supplemental schedule snapshot had 0 valid Crown raw-cache matches. The existing local archive therefore supplied no additional Crown prices for these newly recovered schedules.

This only proves local-cache availability at this snapshot. The collector can still request historical Crown movement through the confirmed local cache tool once the active TotalCorner pagination is idle. Empty responses remain explicit no-quote observations; no other bookmaker or synthesized price is used.

Machine record: `OFFLINE_CROWN_CACHE_AUDIT_20261121T1520Z.json`. Raw source bodies and SQLite remain in the authorized local data store.
