"""Generate the synthetic incident suite into data/incidents.jsonl (deterministic).

    python scripts/build_incidents.py          # write
    python scripts/build_incidents.py --check  # fail if the committed file differs from a fresh build (CI)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiops.simulate import incident_ids, make_incident  # noqa: E402

OUT = ROOT / "data" / "incidents.jsonl"


def build() -> str:
    return "".join(json.dumps(make_incident(i), separators=(",", ":")) + "\n" for i in incident_ids())


def main() -> int:
    text = build()
    if "--check" in sys.argv:
        same = OUT.read_text() == text
        print("incidents", "match a fresh build" if same else "DIFFER from a fresh build")
        return 0 if same else 1
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {len(text.splitlines())} incidents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
