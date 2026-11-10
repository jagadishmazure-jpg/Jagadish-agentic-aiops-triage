"""One incident end to end without a model: the page, the correlation shortlist, and the policy review.

    python examples/demo.py [incident-id]

Prints what the on-call engineer would see, what the correlation engine shortlists, the measured hybrid
answer for this incident from data/runs/, and what the action policy does with it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiops.agent import public_view  # noqa: E402
from aiops.policy import review  # noqa: E402
from aiops.rca import first_alert, graph_rca  # noqa: E402


def main(iid: str = "cache_stampede-02") -> None:
    inc = next(json.loads(x) for x in (ROOT / "data/incidents.jsonl").read_text().splitlines()
               if json.loads(x)["id"] == iid)
    pub = public_view(inc)
    print(f"incident {iid}: {len(pub['alerts'])} alerts")
    for a in pub["alerts"][:6]:
        print(f"  {a['minute']:02d}m {a['severity']:8s} {a['service']}: {a['rule']}")
    fa, g = first_alert(pub), graph_rca(pub)
    print(f"first-alert rule blames: {fa['root']} ({fa['fault']})")
    print(f"correlation shortlist:  {', '.join(g['candidates'])}")
    print(f"correlation engine answer: {g['root']} ({g['fault']})")
    runs = ROOT / "data/runs/gemma4-e2b.hybrid.jsonl"
    rec = next((json.loads(x) for x in runs.read_text().splitlines() if json.loads(x)["id"] == iid), None)
    if rec:
        print(f"hybrid answer (measured): {rec['root']} / {rec['fault']} -> {rec['action']}")
        r = review(rec["action"], rec["root"])
        print(f"policy review: {r['status']} (executed: {r['executed']})")
    print(f"ground truth: {inc['root']} / {inc['fault']}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
