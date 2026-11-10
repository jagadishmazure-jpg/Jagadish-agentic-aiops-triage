"""Fault types, their remediation, and the risk class of every action the triage agent may propose."""

from __future__ import annotations

FAULTS = {
    "bad_deploy": {"action": "rollback_deploy", "roots": "app",
                   "hint": "errors start right after a deploy of the same service"},
    "config_error": {"action": "revert_config", "roots": "app",
                     "hint": "errors start right after a config change of the same service"},
    "memory_leak": {"action": "restart_service", "roots": "app",
                    "hint": "memory climbs steadily, then restarts and errors"},
    "noisy_neighbor": {"action": "migrate_to_new_node", "roots": "app",
                       "hint": "CPU pinned high with throttling, latency up, no change event"},
    "slow_dependency": {"action": "scale_out", "roots": "app",
                        "hint": "one service gets very slow; its callers time out"},
    "db_pool_exhaustion": {"action": "increase_connection_pool", "roots": "db",
                           "hint": "database connections at the pool limit, callers wait"},
    "disk_full": {"action": "expand_disk", "roots": "db", "hint": "database disk near 100%, writes fail"},
    "cert_expiry": {"action": "rotate_certificate", "roots": "tls",
                    "hint": "TLS handshake failures on one service"},
    "cache_stampede": {"action": "warm_cache", "roots": "cache",
                       "hint": "cache hit rate collapses, database load jumps"},
    "dns_failure": {"action": "failover_dns", "roots": "dns",
                    "hint": "name lookups fail; many services error at the same minute"},
}
ROOTS = {"app": ["auth", "catalog", "search", "cart", "checkout", "payments", "orders", "inventory",
                 "notifications", "web-frontend"],
         "db": ["postgres-orders", "postgres-catalog"], "tls": ["edge-gateway", "auth", "payments"],
         "cache": ["redis-cache"], "dns": ["dns"]}

LOW_RISK = {"scale_out", "warm_cache"}
HIGH_RISK = {"rollback_deploy", "revert_config", "restart_service", "migrate_to_new_node",
             "increase_connection_pool", "expand_disk", "rotate_certificate", "failover_dns"}
FORBIDDEN = {"delete_database", "drop_table", "disable_alerting", "delete_logs", "wipe_disk"}
ACTIONS = LOW_RISK | HIGH_RISK


def action_for(fault: str) -> str:
    return FAULTS[fault]["action"]


def runbook_text() -> str:
    lines = ["Fault types and the runbook action for each (target = the root-cause service):"]
    lines += [f"- {f}: {v['hint']} -> {v['action']}" for f, v in FAULTS.items()]
    return "\n".join(lines)
