"""Correlation engine and the naive baseline."""

import numpy as np

from aiops.agent import public_view
from aiops.rca import classify, first_alert, graph_rca, onset, profile
from aiops.runbook import FAULTS


def test_onset_finds_a_sustained_step_and_ignores_flat_noise():
    rng = np.random.default_rng(0)
    flat = list(10 + rng.normal(0, 0.5, 60))
    step = flat[:30] + [x + 20 for x in flat[30:]]
    assert onset(flat)[0] is None and onset(step)[0] == 30


def test_onset_ignores_a_single_minute_spike():
    x = [10.0] * 60
    x[40] = 99.0
    assert onset(x)[0] is None


def test_onset_handles_falling_metrics():
    x = [95.0] * 30 + [40.0] * 30
    assert onset(x, decreasing=True)[0] == 30 and onset(x)[0] is None


def test_graph_rca_needs_no_ground_truth(incidents):
    for i in incidents[:20]:
        assert graph_rca(i) == graph_rca(public_view(i))


def test_root_is_always_in_the_graph_shortlist(incidents):
    assert all(i["root"] in graph_rca(public_view(i))["candidates"] for i in incidents)


def test_graph_rca_beats_first_alert_on_root(incidents):
    g = sum(graph_rca(public_view(i))["root"] == i["root"] for i in incidents)
    f = sum(first_alert(public_view(i))["root"] == i["root"] for i in incidents)
    assert g > f + 20


def test_classify_returns_a_known_fault_and_dns_is_recognised(incidents):
    for i in incidents[:30]:
        p = profile(i)
        assert classify(i, i["root"], p) in FAULTS
    assert classify({"changes": [], "t0": 30}, "dns", {}) == "dns_failure"


def test_first_alert_blames_the_first_alerting_service():
    inc = {"alerts": [{"minute": 3, "service": "cart", "rule": "cpu_pct > 85", "severity": "warning"},
                      {"minute": 5, "service": "orders", "rule": "error_pct > 5", "severity": "critical"}]}
    r = first_alert(inc)
    assert r["root"] == "cart" and r["fault"] == "noisy_neighbor" and r["candidates"] == ["cart", "orders"]


def test_empty_incident_gives_no_answer():
    assert first_alert({"alerts": []})["root"] is None
    assert graph_rca({"metrics": {"x": {"cpu_pct": [5.0] * 60}}, "changes": []})["root"] is None
