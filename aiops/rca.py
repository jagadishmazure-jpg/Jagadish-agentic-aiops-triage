"""Non-LLM triage: a naive first-alert rule and a topology-aware correlation engine."""

from __future__ import annotations

import numpy as np

from .runbook import action_for
from .topology import APP, CALLS, SERVICES, upstream

BASE = 15  # minutes of normal behaviour at the start of every window
Z = 4.0


def onset(series: list[float], decreasing: bool = False) -> tuple[int | None, float]:
    x = np.asarray(series, dtype=float)
    b = x[:BASE]
    sd = max(float(b.std()), 0.02 * abs(float(b.mean())) + 1e-6, 0.3)
    z = (b.mean() - x) / sd if decreasing else (x - b.mean()) / sd
    for t in range(BASE + 1, len(x)):
        if z[t] > Z and z[t - 1] > Z:
            return t - 1, float(z.max())
    return None, float(z.max())


def profile(incident: dict) -> dict[str, dict[str, tuple[int, float]]]:
    """Anomalous metrics per service: {service: {metric: (onset minute, peak z)}}."""
    out = {}
    for svc, metrics in incident["metrics"].items():
        found = {}
        for name, series in metrics.items():
            t, z = onset(series, decreasing=name == "hit_rate_pct")
            if t is not None:
                found[name] = (t, round(z, 1))
        if found:
            out[svc] = found
    return out


def first_onset(p: dict, svc: str) -> int:
    return min(t for t, _ in p[svc].values())


def classify(incident: dict, root: str, p: dict) -> str:
    """Fault type from the root's metrics and change records only (no log reading)."""
    if root == "dns":
        return "dns_failure"
    m = p.get(root, {})
    if "hit_rate_pct" in m:
        return "cache_stampede"
    if "connections_pct" in m:
        return "db_pool_exhaustion"
    if "disk_pct" in m:
        return "disk_full"
    if "mem_pct" in m:
        return "memory_leak"
    if "cpu_pct" in m and "latency_ms" in m:
        return "noisy_neighbor"
    lat, err = m.get("latency_ms", (0, 0))[1], m.get("error_pct", (0, 0))[1]
    if lat > err:
        return "slow_dependency"
    t = first_onset(p, root) if m else incident["t0"]
    for c in incident["changes"]:
        if c["service"] == root and 0 <= t - c["minute"] <= 10:
            return "bad_deploy" if c["kind"] == "deploy" else "config_error"
    return "cert_expiry"


def graph_rca(incident: dict, k: int = 3) -> dict:
    """Rank root-cause candidates: anomalous services not explained by an earlier anomalous callee."""
    p = profile(incident)
    if not p:
        return {"candidates": [], "root": None, "fault": None, "action": None}
    unexplained = []
    for s in p:
        t = first_onset(p, s)
        if not any(c in p and first_onset(p, c) <= t for c in CALLS[s]):
            unexplained.append(s)
    # Many services failing in the same minute with no anomalous callee: look for a shared dependency.
    if len(unexplained) >= 4:
        common = set.intersection(*(set(CALLS[s]) for s in unexplained))
        if common:
            unexplained = sorted(common) + unexplained

    def key(s):
        if s not in p:
            return (-1, 0, 0)
        blast = sum(1 for u in upstream(s) if u in p)
        return (first_onset(p, s), -blast, -max(z for _, z in p[s].values()))

    ranked = sorted(dict.fromkeys(unexplained), key=key)
    rest = sorted((s for s in p if s not in ranked), key=key)
    cands = (ranked + rest)[:k]
    root = cands[0]
    fault = classify(incident, root, p)
    return {"candidates": cands, "root": root, "fault": fault, "action": action_for(fault)}


RULE_FAULT = {"error_pct": "bad_deploy", "latency_ms": "slow_dependency", "cpu_pct": "noisy_neighbor",
              "mem_pct": "memory_leak", "connections_pct": "db_pool_exhaustion", "disk_pct": "disk_full",
              "hit_rate_pct": "cache_stampede"}


def first_alert(incident: dict) -> dict:
    """What a pager rule does: blame the first alerting service; fault from the alert's metric."""
    if not incident["alerts"]:
        return {"candidates": [], "root": None, "fault": None, "action": None}
    a = incident["alerts"][0]
    fault = RULE_FAULT[a["rule"].split()[0]]
    seen = list(dict.fromkeys(x["service"] for x in incident["alerts"]))
    return {"candidates": seen[:3], "root": a["service"], "fault": fault, "action": action_for(fault)}


__all__ = ["APP", "SERVICES", "classify", "first_alert", "graph_rca", "onset", "profile"]
