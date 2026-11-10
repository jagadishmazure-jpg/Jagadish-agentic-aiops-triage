# ADR 0001: Measure once on CPU, replay the scoring in CI

**Status:** accepted

**Context.** Running a small model over 80 incidents in four configurations takes about three hours on a
shared 8-core CPU (most of it the free agent). CI cannot do that on every push and should not need model weights.

**Decision.** Triage runs are measured once with `scripts/run_triage.py` and committed as JSONL. CI
rebuilds the incident suite from the simulator and compares it with the committed file, checks the hash
manifest, re-scores every committed answer against ground truth, and fails if any number differs from
`results/` or from the numbers quoted in the docs.

**Consequences.** Scoring is reproducible and cheap. The model's behaviour itself is not re-measured in
CI; that needs `scripts/fetch_models.sh` and a few hours of CPU.
