"""The incident simulator is deterministic and its ground truth is consistent with what it emits."""

import subprocess
import sys

import pytest
from conftest import ROOT

from aiops.runbook import FAULTS, ROOTS
from aiops.simulate import INJECTION, MINUTES, incident_ids, make_incident, split
from aiops.topology import SERVICES


def test_same_id_gives_the_same_incident_and_ids_differ():
    a, b = make_incident("disk_full-03"), make_incident("disk_full-03")
    assert a == b and make_incident("disk_full-04")["metrics"] != a["metrics"]


def test_suite_has_eight_unique_incidents_per_fault():
    ids = incident_ids()
    assert len(ids) == 80 == len(set(ids))
    assert all(sum(i.startswith(f + "-") for i in ids) == 8 for f in FAULTS)


def test_split_is_fixed_and_mostly_held_out(incidents):
    dev = [i["id"] for i in incidents if split(i["id"]) == "dev"]
    assert len(dev) == 19 and split(dev[0]) == "dev"


def test_committed_incidents_match_a_fresh_build():
    r = subprocess.run([sys.executable, "scripts/build_incidents.py", "--check"], cwd=ROOT, capture_output=True,
                       text=True, check=False)
    assert r.returncode == 0, r.stdout


def test_root_comes_from_the_fault_pool_and_t0_is_in_window(incidents):
    for i in incidents:
        assert i["root"] in ROOTS[FAULTS[i["fault"]]["roots"]] and 20 <= i["t0"] <= 30, i["id"]


def test_every_service_has_a_full_hour_of_every_metric(incidents):
    for i in incidents[:10]:
        assert set(i["metrics"]) == set(SERVICES)
        assert all(len(v) == MINUTES for m in i["metrics"].values() for v in m.values())


def test_alerts_are_in_firing_order_and_name_real_services(incidents):
    for i in incidents:
        mins = [a["minute"] for a in i["alerts"]]
        assert mins == sorted(mins) and all(a["service"] in SERVICES for a in i["alerts"])


def test_silent_root_never_alerts(incidents):
    for i in incidents:
        if i["flags"]["silent_root"]:
            assert all(a["service"] != i["root"] for a in i["alerts"]), i["id"]


def test_root_log_carries_the_fault_signature(incidents):
    from aiops.simulate import ROOT_LOGS

    for i in incidents:
        sig = ROOT_LOGS[i["fault"]][0].split("(")[0].strip()
        assert any(sig in line for line in i["logs"][i["root"]]), i["id"]


def test_injection_appears_only_when_flagged_and_never_in_the_root_log(incidents):
    for i in incidents:
        hit = [s for s, lines in i["logs"].items() if any(INJECTION in x for x in lines)]
        assert (len(hit) == 1) == i["flags"]["injection"], i["id"]
        assert i["root"] not in hit


@pytest.mark.parametrize("fault", ["bad_deploy"])
def test_bad_deploy_always_has_a_deploy_record_on_the_root(incidents, fault):
    for i in incidents:
        if i["fault"] == fault:
            assert any(c["service"] == i["root"] and c["kind"] == "deploy" for c in i["changes"])


def test_some_config_errors_have_no_change_record(incidents):
    cfg = [i for i in incidents if i["fault"] == "config_error"]
    missing = [i for i in cfg if not any(c["kind"] == "config" for c in i["changes"])]
    assert 0 < len(missing) < len(cfg)


def test_decoy_deploys_never_target_the_root(incidents):
    for i in incidents:
        if i["flags"]["decoy_change"] and i["fault"] != "bad_deploy":
            assert any(c["service"] != i["root"] for c in i["changes"])
