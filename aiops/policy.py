"""Action policy: the agent only proposes. Nothing it says is executed without this check, and
nothing high-risk is executed without a person approving it."""

from __future__ import annotations

from .runbook import FORBIDDEN, HIGH_RISK, LOW_RISK
from .topology import SERVICES


def review(action: str | None, target: str | None) -> dict:
    """Decide what happens to a proposed remediation."""
    if not action:
        return {"status": "no_action", "executed": False}
    if action in FORBIDDEN:
        return {"status": "blocked", "executed": False, "reason": f"{action} is never allowed"}
    if target not in SERVICES:
        return {"status": "rejected", "executed": False, "reason": f"unknown target {target!r}"}
    if action in HIGH_RISK:
        return {"status": "pending_approval", "executed": False, "reason": "high-risk change needs on-call approval"}
    if action in LOW_RISK:
        return {"status": "approved_low_risk", "executed": True}
    return {"status": "rejected", "executed": False, "reason": f"unknown action {action!r}"}


def mentions_forbidden(text: str) -> bool:
    return any(a in text for a in FORBIDDEN)
