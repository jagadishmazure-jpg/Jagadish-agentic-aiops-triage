"""Service map sanity: the graph the correlation engine walks."""

from aiops.topology import APP, CALLS, DATA, SERVICES, callees, callers, downstream, upstream


def test_every_app_service_resolves_names_through_dns():
    assert all("dns" in CALLS[s] for s in APP) and set(callers("dns")) == set(APP)


def test_data_stores_and_dns_call_nothing():
    assert all(CALLS[s] == [] for s in [*DATA, "dns"])


def test_callers_is_the_inverse_of_callees():
    for s in SERVICES:
        for c in callees(s):
            assert s in callers(c)


def test_graph_has_no_cycles():
    assert all(s not in downstream(s) for s in SERVICES)


def test_upstream_reports_hop_distance():
    up = upstream("postgres-orders")
    assert up["orders"] == 1 and up["checkout"] == 2 and up["web-frontend"] == 3 and up["edge-gateway"] == 4


def test_edges_only_name_known_services():
    assert set(CALLS) == set(SERVICES) and all(c in SERVICES for v in CALLS.values() for c in v)
