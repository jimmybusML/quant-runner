"""Restore append-only M3 events from immutable tracked base plus Git-friendly segments.

The original 2026-11-02 large JSONL is preserved exactly in Git.  New events go
into independently committed immutable JSONL segments; no historical deletion.
Consumers continue using the same ledger filename after `materialize`.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

LEDGER = "research/m3/results/totalcorner/forward_ev_ledger.jsonl"
SEGMENTS = "research/m3/results/totalcorner/segments"
# GitHub rejects a single blob >=100MiB. Splitting only affects physical storage.
SEGMENT_BYTES = 32 * 1024 * 1024


def git(*args: str) -> str:
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError("git " + " ".join(args[:2]) + ": " + p.stderr[-1000:])
    return p.stdout


def segment_paths(ref: str = "HEAD") -> list[str]:
    out = git("ls-tree", "-r", "--name-only", ref, "--", SEGMENTS)
    return sorted(p for p in out.splitlines() if p.endswith(".jsonl"))


def lines_from_text(text: str):
    for line in text.splitlines():
        if line.strip():
            yield line, json.loads(line)


def materialize(path: str | Path = LEDGER) -> dict:
    target = Path(path)
    # Prefer immutable repository baseline, not a working copy modified by this run.
    baseline = git("show", "HEAD:" + LEDGER)
    paths = segment_paths()
    seen = set()
    count = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=target.parent, prefix=".m3-materialize-", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            for line, event in lines_from_text(baseline):
                eid = event["event_id"]
                if eid in seen:
                    raise ValueError("Duplicate immutable baseline event_id: " + eid)
                seen.add(eid)
                out.write(line + "\n")
                count += 1
            for shard in paths:
                for line, event in lines_from_text(git("show", "HEAD:" + shard)):
                    eid = event["event_id"]
                    if eid in seen:
                        raise ValueError("Duplicate segment event_id: " + eid)
                    seen.add(eid)
                    out.write(line + "\n")
                    count += 1
        os.replace(name, target)
        # Generated union stays a worktree-only view: never stage it or block
        # independent status-report commits from rebasing against latest main.
        git("update-index", "--skip-worktree", "--", LEDGER)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return {"status": "MATERIALIZED", "events": count, "segments": len(paths), "path": str(target)}


def split_lines(events: list[dict]) -> list[list[str]]:
    chunks, chunk, size = [], [], 0
    for e in events:
        line = json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n"
        size_next = len(line.encode("utf-8"))
        if size_next >= 100 * 1024 * 1024:
            raise ValueError("A single event exceeds GitHub blob limit")
        if chunk and size + size_next > SEGMENT_BYTES:
            chunks.append(chunk)
            chunk, size = [], 0
        chunk.append(line)
        size += size_next
    if chunk:
        chunks.append(chunk)
    return chunks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["materialize", "list"])
    args = p.parse_args()
    if args.command == "materialize":
        print(json.dumps(materialize(), ensure_ascii=False))
    else:
        print(json.dumps({"segments": segment_paths()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
