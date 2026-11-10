"""SHA-256 of every committed data file, so a changed measurement cannot slip in unnoticed.

    python scripts/manifest.py          # write data/manifest.json
    python scripts/manifest.py --check  # fail if a file differs (CI)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def files() -> list[str]:
    """The incident suite plus every measured run file (one per triage configuration)."""
    return ["incidents.jsonl", *sorted(str(p.relative_to(DATA)) for p in (DATA / "runs").glob("*.jsonl"))]


def digests() -> dict:
    return {f: hashlib.sha256((DATA / f).read_bytes()).hexdigest() for f in files()}


def main() -> int:
    path = DATA / "manifest.json"
    if "--check" in sys.argv:
        want, have = json.loads(path.read_text()), digests()
        bad = sorted(f for f in set(want) | set(have) if want.get(f) != have.get(f))
        print("manifest", "differs: " + ", ".join(bad) if bad else "matches")
        return 1 if bad else 0
    path.write_text(json.dumps(digests(), indent=1, sort_keys=True) + "\n")
    print("manifest written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
