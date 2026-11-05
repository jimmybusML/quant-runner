"""Persist M3 append-only events in immutable segments, never a >100MiB Git blob."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from research.m3.m3_shadow_orders import order_identity
from research.m3.segmented_ledger import LEDGER, SEGMENTS, split_lines


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", *args], text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError("git " + " ".join(args[:2]) + ": " + p.stderr[-1600:])
    return p


def events(text: str) -> dict:
    records = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        eid = event["event_id"]
        if eid in records and records[eid] != event:
            raise ValueError("conflicting payload for event_id: " + eid)
        records[eid] = event
    return records


def remote_events() -> dict:
    """Union of frozen original ledger and all committed segment files."""
    original = git("show", "origin/main:" + LEDGER).stdout
    saved = events(original)
    paths = git("ls-tree", "-r", "--name-only", "origin/main", "--", SEGMENTS).stdout
    for path in sorted(p for p in paths.splitlines() if p.endswith(".jsonl")):
        extra = events(git("show", "origin/main:" + path).stdout)
        for eid, event in extra.items():
            if eid in saved and saved[eid] != event:
                raise ValueError("existing event_id mismatch across segments: " + eid)
            saved[eid] = event
    return saved


def persist(candidate_path: str | Path, max_attempts: int = 8):
    candidate = events(Path(candidate_path).read_text(encoding="utf-8"))
    for attempt in range(max_attempts):
        git("fetch", "origin", "main")
        existing = remote_events()
        # A repeat FT observation may have a new observation timestamp while
        # referring to exactly the same immutable settlement. Preserve the
        # original event; reject every other difference, including the result.
        def same_immutable_event(a, b):
            if a == b:
                return True
            if a.get('protocol') != 'M3_TOTALCORNER_FORWARD_SETTLEMENT_V1' or b.get('protocol') != a.get('protocol'):
                return False
            return {k: v for k, v in a.items() if k != 'observed_utc'} == {k: v for k, v in b.items() if k != 'observed_utc'}
        conflicts = [eid for eid, e in candidate.items() if eid in existing and not same_immutable_event(existing[eid], e)]
        if conflicts:
            raise ValueError("immutable existing event mismatch: " + str(len(conflicts)))
        already = {order_identity(e) for e in existing.values() if e.get("protocol") == "M3_SHADOW_ORDER_V1"}
        addition, suppressed = [], 0
        for eid, e in candidate.items():
            if eid in existing:
                continue
            key = order_identity(e) if e.get("protocol") == "M3_SHADOW_ORDER_V1" else None
            if key is not None and key in already:
                suppressed += 1
                continue
            addition.append(e)
            if key is not None:
                already.add(key)
        if suppressed:
            print(json.dumps({"duplicate_shadow_orders_suppressed": suppressed}), flush=True)
        if not addition:
            print(json.dumps({"status": "NO_NEW_EVENTS", "added": 0, "attempt": attempt + 1}), flush=True)
            return
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp) / "writer"
            git("worktree", "add", "--detach", str(w), "origin/main")
            try:
                git("-C", str(w), "config", "user.name", "github-actions[bot]")
                git("-C", str(w), "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
                shards = []
                for chunk in split_lines(addition):
                    data = "".join(chunk)
                    digest = hashlib.sha256(data.encode("utf-8")).hexdigest()[:20]
                    path = w / SEGMENTS / ("events-" + digest + ".jsonl")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(data, encoding="utf-8")
                    shards.append(str(path.relative_to(w)))
                git("-C", str(w), "add", "--", *shards)
                git("-C", str(w), "commit", "-m", "Persist M3 immutable event segment(s)")
                push = git("-C", str(w), "push", "origin", "HEAD:main", check=False)
                if push.returncode == 0:
                    print(json.dumps({"status": "PERSISTED", "added": len(addition), "segments": len(shards), "attempt": attempt + 1}), flush=True)
                    return
                # Surface actual push cause; suppress URLs to avoid credential leakage.
                message = push.stderr[-600:].replace("https://github.com/", "github.com/")
                print(json.dumps({"status": "RETRY_PUSH", "attempt": attempt + 1, "error": message}), flush=True)
            finally:
                git("worktree", "remove", "--force", str(w))
    raise RuntimeError("M3 segment persistence failed after retries; see prior push error lines")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()
    persist(args.candidate)
