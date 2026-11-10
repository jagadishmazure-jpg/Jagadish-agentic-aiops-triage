"""Agent loop, one-shot and hybrid modes with a scripted fake model (no weights needed)."""

import json

from conftest import FakeLLM

from aiops.agent import (LIMITS, find_json, parse_call, run_agent, run_hybrid, run_hybrid_injected, run_oneshot,
                         with_root_injection)
from aiops.evaluate import score
from aiops.policy import review
from aiops.simulate import INJECTION

SUBMIT = json.dumps({"tool": "submit", "args": {"root_service": "postgres-orders", "fault_type": "db_pool_exhaustion",
                                                "action": "increase_connection_pool", "summary": "pool full"}})


def test_parse_call_finds_the_json_after_prose_and_accepts_arguments_key():
    assert parse_call('Look first. {"tool": "get_logs", "args": {"service": "cart"}}') == ("get_logs", {"service": "cart"})
    assert parse_call('{"tool": "get_alerts", "arguments": {}}') == ("get_alerts", {})
    assert parse_call("no json here") is None and parse_call('{"tool": 3}') is None
    assert find_json('{"a": 1} then {"root_service": "dns"}', "root_service") == {"root_service": "dns"}


def test_agent_reads_tools_then_submits(by_id):
    inc = by_id["db_pool_exhaustion-01"]
    llm = FakeLLM(['{"tool": "get_alerts", "args": {}}',
                   '{"tool": "get_metrics", "args": {"service": "postgres-orders"}}', SUBMIT])
    r = run_agent(inc, llm, "gemma4-e2b.agent")
    assert r["stop"] == "submitted" and r["tool_calls"] == 2 and r["turns"] == 3
    assert [t["tool"] for t in r["trace"]] == ["get_alerts", "get_metrics", "submit"]
    assert r["root"] == "postgres-orders" and r["action"] == "increase_connection_pool"


def test_agent_never_sees_the_ground_truth(by_id):
    inc = by_id["db_pool_exhaustion-01"]
    llm = FakeLLM([SUBMIT])
    run_agent(inc, llm, "gemma4-e2b.agent")
    shown = json.dumps(llm.seen)
    assert '"flags"' not in shown and inc["id"] not in shown


def test_agent_stops_after_repeated_replies_without_a_tool_call(by_id):
    r = run_agent(by_id["dns_failure-00"], FakeLLM(["hmm", "hmm", "hmm", SUBMIT]), "gemma4-e2b.agent")
    assert r["stop"] == "no_tool_call" and r["invalid_replies"] == LIMITS["no_call_streak"] and r["root"] == ""


def test_agent_tool_budget_is_enforced(by_id):
    many = ['{"tool": "get_alerts", "args": {}}'] * 11 + [SUBMIT]
    r = run_agent(by_id["dns_failure-00"], FakeLLM(many), "gemma4-e2b.agent")
    assert r["tool_calls"] == LIMITS["max_tool_calls"] and r["stop"] == "submitted"


def test_agent_stops_when_the_context_is_full(by_id):
    r = run_agent(by_id["dns_failure-00"], FakeLLM([SUBMIT], tokens_per_byte=10), "gemma4-e2b.agent")
    assert r["stop"] == "context_full" and r["turns"] == 1


def test_oneshot_sees_alerts_and_changes_but_no_logs(by_id):
    inc = by_id["cert_expiry-02"]
    llm = FakeLLM(['{"root_service": "auth", "fault_type": "cert_expiry", "action": "rotate_certificate"}'])
    r = run_oneshot(inc, llm, "gemma4-e2b.oneshot")
    shown = llm.seen[0][1]["content"]
    assert "Alerts:" in shown and "Service map" in shown and "x509" not in shown and r["stop"] == "answered"


def test_hybrid_shows_the_graph_shortlist_with_logs(by_id):
    inc = by_id["cert_expiry-02"]
    llm = FakeLLM(["no answer"])
    r = run_hybrid(inc, llm, "gemma4-e2b.hybrid")
    shown = llm.seen[0][1]["content"]
    assert "shortlist" in shown and "Logs:" in shown and inc["root"] in r["candidates"]
    assert r["stop"] == "no_answer" and r["invalid_replies"] == 1


def test_injection_stress_puts_the_instruction_in_the_root_log(by_id):
    inc = by_id["cert_expiry-02"]
    bad = with_root_injection(inc)
    assert any(INJECTION in x for x in bad["logs"][inc["root"]]) and not any(INJECTION in x for x in inc["logs"][inc["root"]])
    llm = FakeLLM(['{"root_service": "postgres-orders", "fault_type": "disk_full", "action": "delete_database"}'])
    r = run_hybrid_injected(inc, llm, "gemma4-e2b.hybrid-injected")
    assert "SYSTEM NOTICE" in llm.seen[0][1]["content"] or inc["root"] not in r["candidates"]


def test_a_model_that_follows_the_injection_is_caught_and_blocked(by_id):
    """If the model obeys the planted instruction, scoring flags it and the policy blocks it."""
    inc = by_id["cert_expiry-02"]
    llm = FakeLLM(['{"root_service": "postgres-orders", "fault_type": "disk_full", "action": "delete_database"}'])
    r = run_hybrid(inc, llm, "gemma4-e2b.hybrid")
    s = score(r, inc)
    assert s["forbidden"] and not s["full"] and review(r["action"], r["root"])["status"] == "blocked"


def test_prompts_say_logs_are_data_not_instructions():
    from aiops.agent import PROMPTS

    for f in ("agent.md", "answer.md"):
        text = (PROMPTS / f).read_text().lower()
        assert "never" in text and "instructions" in text and "deleting data" in text
