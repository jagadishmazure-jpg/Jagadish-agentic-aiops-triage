"""The agent's tools are read-only, budgeted, and never leak the answer."""

import json

import pytest

from aiops.agent import public_view
from aiops.tools import OUTPUT_CAP, IncidentTools, cap


@pytest.fixture
def tools(by_id):
    return IncidentTools(public_view(by_id["db_pool_exhaustion-01"]), max_calls=3)


def test_public_view_hides_the_answer(by_id):
    v = public_view(by_id["db_pool_exhaustion-01"])
    assert not {"fault", "root", "t0", "flags"} & set(v)


def test_no_tool_output_mentions_the_fault_label(tools, by_id):
    fault = by_id["db_pool_exhaustion-01"]["fault"]
    outs = [tools.call("get_alerts", {}), tools.call("get_changes", {}), tools.call("get_metrics", {"service": "orders"})]
    assert all(fault not in o for o in outs)


def test_budget_is_enforced_but_submit_always_works(tools):
    for _ in range(3):
        tools.call("get_alerts", {})
    assert "budget used up" in tools.call("get_alerts", {})
    assert json.loads(tools.call("submit", {"root_service": "x"}))["submitted"] and tools.calls == 3


def test_unknown_tool_and_bad_arguments_are_errors_not_crashes(tools):
    assert "unknown tool" in tools.call("rm_rf", {})
    assert "bad arguments" in tools.call("get_metrics", {"svc": "orders"})
    assert "unknown service" in tools.call("get_logs", {"service": "mainframe"})
    assert [x["ok"] for x in tools.log] == [False, False, False]


def test_topology_tool_lists_both_directions(tools):
    out = tools.call("get_topology", {"service": "orders"})
    assert "postgres-orders" in out and "checkout" in out


def test_metrics_tool_marks_anomalies(by_id):
    inc = by_id["db_pool_exhaustion-01"]
    t = IncidentTools(public_view(inc))
    assert "ANOMALY" in t.call("get_metrics", {"service": inc["root"]})


def test_logs_are_returned_verbatim_including_untrusted_text(by_id):
    inc = next(i for i in by_id.values() if i["flags"]["injection"])
    svc = next(s for s, lines in inc["logs"].items() if any("SYSTEM NOTICE" in x for x in lines))
    assert "SYSTEM NOTICE" in IncidentTools(public_view(inc)).call("get_logs", {"service": svc})


def test_long_output_is_capped():
    assert len(cap("x" * 5000)) <= OUTPUT_CAP and cap("short") == "short"


def test_submit_truncates_summary(tools):
    tools.call("submit", {"root_service": "a", "fault_type": "b", "action": "c", "summary": "s" * 1000})
    assert len(tools.submission["summary"]) == 400
