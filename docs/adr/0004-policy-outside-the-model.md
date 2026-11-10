# ADR 0004: The action policy lives outside the model

**Status:** accepted

**Context.** Logs are attacker-reachable text. Any instruction the model reads can end up in its
answer, and a prompt that says "never do X" is not a control.

**Decision.** The assistant only proposes. `aiops/policy.py` reviews every proposal: forbidden actions
(deleting data, disabling alerting) are blocked, unknown actions and targets rejected, high-risk runbook
actions wait for on-call approval, and only two low-risk actions (scale out, warm cache) may run. The CI
gate fails if any measured answer proposed a forbidden action or a high-risk action was executed.

**Consequences.** A fooled model cannot cause harm through this path. The cost is that most fixes still
need a person, which is the right default for production changes.
