"""Run one triage configuration over the incident suite; append results to data/runs/<config>.jsonl.

    python scripts/run_triage.py --config gemma4-e2b.agent [--limit N] [--threads 8]
    python scripts/run_triage.py --config graph_rca          # rule-based, no model

Resumable: incidents already in the file are skipped. LLM configs need llama-cpp-python==0.3.36 and the
GGUF from scripts/fetch_models.sh. Run long configs detached (nohup) and watch the log.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiops.agent import CONFIGS, LIMITS, RULES, run_agent, run_hybrid, run_oneshot, run_rules  # noqa: E402

RUNS = ROOT / "data" / "runs"
MODES = {"agent": run_agent, "hybrid": run_hybrid, "oneshot": run_oneshot}


def incidents() -> list[dict]:
    return [json.loads(line) for line in (ROOT / "data/incidents.jsonl").read_text().splitlines()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=[*CONFIGS, *RULES])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--only", nargs="*", default=None, help="incident ids (smoke tests)")
    ap.add_argument("--models-dir", type=Path, default=ROOT / "models")
    a = ap.parse_args()
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f"{a.config}.jsonl"
    done = {json.loads(x)["id"] for x in out.read_text().splitlines()} if out.exists() else set()
    todo = [i for i in incidents() if i["id"] not in done and (a.only is None or i["id"] in a.only)]
    todo = todo[: a.limit or None]
    llm = None
    if a.config in CONFIGS and todo:
        from llama_cpp import Llama

        spec = json.loads((ROOT / "scripts/models.json").read_text())
        f = next(m["file"] for m in spec["gguf"] if m["label"] == CONFIGS[a.config]["model"])
        llm = Llama(str(a.models_dir / f), n_ctx=LIMITS["n_ctx"], n_threads=a.threads, seed=0, verbose=False)
    with out.open("a", encoding="utf-8") as fh:
        for inc in todo:
            if llm is None:
                r = run_rules(inc, a.config)
            else:
                r = MODES[CONFIGS[a.config]["mode"]](inc, llm, a.config)
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(inc["id"], r["stop"], r["root"], r["fault"], r["seconds"], flush=True)
    print("done", a.config, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
