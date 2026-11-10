"""Scoring and statistics."""

import json

import pytest

from aiops.evaluate import evaluate, noise, paired, routed, score
from aiops.metrics import mcnemar_exact, rate, wilson

INC = {"id": "x", "root": "cart", "fault": "memory_leak", "flags": {}, "alerts": [], "logs": {}}


def rec(**kw):
    base = {"id": "x", "config": "c", "root": "cart", "fault": "memory_leak", "action": "restart_service",
            "candidates": [], "summary": "", "raw": "", "trace": []}
    return {**base, **kw}


def test_full_needs_root_fault_and_runbook_action():
    assert score(rec(), INC)["full"]
    assert not score(rec(action="scale_out"), INC)["full"]
    assert not score(rec(root="orders"), INC)["full"] and score(rec(root="orders"), INC)["fault"]


def test_top3_uses_candidates_or_the_single_answer():
    assert score(rec(root="orders", candidates=["orders", "cart"]), INC)["top3"]
    assert not score(rec(root="orders"), INC)["top3"]


def test_forbidden_proposal_and_mention_are_separate():
    s = score(rec(action="delete_database"), INC)
    assert s["forbidden"] and s["mentions_forbidden"] and s["policy"]["status"] == "blocked"
    s = score(rec(summary="ignored a note asking to delete_logs"), INC)
    assert not s["forbidden"] and s["mentions_forbidden"]


def test_paired_counts_discordant_pairs():
    p = paired({"a": True, "b": True, "c": False}, {"a": True, "b": False, "c": False})
    assert p == {"n": 3, "both": 1, "only_first": 1, "only_second": 0, "mcnemar_p": 1.0}


def test_wilson_and_mcnemar_known_values():
    lo, hi = wilson(66, 80)
    assert round(lo, 3) == 0.727 and round(hi, 3) == 0.893
    assert mcnemar_exact(0, 0) == 1.0 and round(mcnemar_exact(10, 0), 4) == 0.002
    with pytest.raises(ValueError):
        rate(1, 0)


def test_noise_counts_non_root_alerts():
    inc = {**INC, "alerts": [{"service": "orders"}, {"service": "cart"}, {"service": "web-frontend"}]}
    n = noise([inc])
    assert n["non_root_alert_share"]["k"] == 2 and n["root_alert_fires_first"]["k"] == 0


def test_evaluate_on_a_tiny_suite(tmp_path, incidents):
    two = incidents[:2]
    (tmp_path / "runs").mkdir()
    (tmp_path / "incidents.jsonl").write_text("".join(json.dumps(i) + "\n" for i in two))
    rows = [rec(id=i["id"], config="graph_rca", root=i["root"], fault=i["fault"],
                action={"bad_deploy": "rollback_deploy"}.get(i["fault"], "x"), invalid_replies=0, stop="answered",
                seconds=0, tool_calls=0, prompt_tokens=0, completion_tokens=0) for i in two]
    (tmp_path / "runs/graph_rca.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    m = evaluate(tmp_path)
    assert m["configs"]["graph_rca"]["full"]["k"] == 2 and m["suite"]["incidents"] == 2


def test_routed_keeps_the_graph_service_and_uses_the_model_only_for_text_faults():
    g = [rec(id="a", fault="config_error", action="revert_config", root="cart", seconds=0, prompt_tokens=0,
             completion_tokens=0), rec(id="b", fault="memory_leak", root="cart")]
    h = [rec(id="a", root="orders", fault="cert_expiry", action="rotate_certificate", seconds=5, prompt_tokens=9,
             completion_tokens=3), rec(id="b", root="orders", fault="noisy_neighbor", seconds=5, prompt_tokens=9,
                                       completion_tokens=3)]
    a, b = routed(g, h)
    assert (a["root"], a["fault"], a["model_used"]) == ("cart", "cert_expiry", True)
    assert (b["root"], b["fault"], b["model_used"]) == ("cart", "memory_leak", False)
