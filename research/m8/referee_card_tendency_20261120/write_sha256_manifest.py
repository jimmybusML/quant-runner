#!/usr/bin/env python3
"""Write a deterministic SHA256SUMS file for this study directory."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "SHA256SUMS.txt"

entries = []
for path in sorted(p for p in ROOT.iterdir() if p.is_file() and p != MANIFEST):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    entries.append(f"{digest}  {path.name}")
MANIFEST.write_text("\n".join(entries) + "\n", encoding="utf-8")
print(f"wrote {MANIFEST} ({len(entries)} files)")
