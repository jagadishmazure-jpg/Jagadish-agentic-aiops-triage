"""Action policy: forbidden actions are blocked, high-risk ones wait for a person."""

import pytest

from aiops.policy import mentions_forbidden, review
from aiops.runbook import ACTIONS, FAULTS, FORBIDDEN, HIGH_RISK, LOW_RISK, action_for


@pytest.mark.parametrize("action", sorted(FORBIDDEN))
def test_forbidden_actions_are_blocked_even_on_a_valid_target(action):
    r = review(action, "postgres-orders")
    assert r["status"] == "blocked" and not r["executed"]


@pytest.mark.parametrize("action", sorted(HIGH_RISK))
def test_high_risk_actions_wait_for_approval(action):
    r = review(action, "orders")
    assert r["status"] == "pending_approval" and not r["executed"]


def test_only_low_risk_actions_execute():
    assert all(review(a, "cart")["executed"] for a in LOW_RISK)


def test_unknown_target_and_unknown_action_are_rejected():
    assert review("scale_out", "mainframe")["status"] == "rejected"
    assert review("reboot_everything", "cart")["status"] == "rejected"
    assert review(None, None) == {"status": "no_action", "executed": False}


def test_risk_classes_are_disjoint_and_cover_every_runbook_action():
    assert not (LOW_RISK & HIGH_RISK) and not (ACTIONS & FORBIDDEN)
    assert {action_for(f) for f in FAULTS} == ACTIONS


def test_mentions_forbidden():
    assert mentions_forbidden("then run delete_database now") and not mentions_forbidden("rollback_deploy on cart")
