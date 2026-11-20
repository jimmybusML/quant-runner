#!/usr/bin/env python3
"""Write input/output hashes for the M8 referee residual experiment."""
import hashlib
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SUMMARY = OUT / "referee_market_residual_summary.json"
VERIFY = OUT / "independent_verification.json"


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
verification = json.loads(VERIFY.read_text(encoding="utf-8"))
inputs = {}
for path in summary["inputs"]:
    inputs[pathlib.Path(path)] = "research input"
for path in verification["input_sha256"]:
    p = pathlib.Path(path)
    if p.exists() and p.resolve() != VERIFY.resolve():
        inputs[p] = "independent verification input"

lines = ["M8 referee market-residual study SHA256 manifest", ""]
for path, label in sorted(inputs.items(), key=lambda x: str(x[0])):
    if not path.is_file():
        raise FileNotFoundError(path)
    lines.append(f"INPUT {sha(path)}  {label}  {path}")
lines.append("")
for path in sorted(OUT.rglob("*")):
    if not path.is_file() or path.name == "SHA256SUMS.txt" or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    lines.append(f"OUTPUT {sha(path)}  {path.relative_to(ROOT)}")
(OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {len(inputs)} input and {len(lines) - len(inputs) - 3} output hashes")
