"""Service map of Velmora Fresh's platform. An edge A -> B means A calls B (A depends on B)."""

from __future__ import annotations

APP = ["edge-gateway", "web-frontend", "auth", "catalog", "search", "cart", "checkout", "payments",
       "orders", "inventory", "notifications"]
DATA = ["postgres-orders", "postgres-catalog", "redis-cache", "event-bus"]
INFRA = ["dns"]
SERVICES = APP + DATA + INFRA

CALLS = {
    "edge-gateway": ["web-frontend", "auth"],
    "web-frontend": ["auth", "catalog", "search", "cart", "checkout"],
    "auth": ["redis-cache"],
    "catalog": ["redis-cache", "postgres-catalog"],
    "search": ["catalog"],
    "cart": ["redis-cache", "inventory"],
    "checkout": ["payments", "orders", "inventory"],
    "payments": [],
    "orders": ["postgres-orders", "event-bus"],
    "inventory": ["postgres-catalog"],
    "notifications": ["event-bus"],
    "postgres-orders": [], "postgres-catalog": [], "redis-cache": [], "event-bus": [], "dns": [],
}
# Every application service resolves names through dns.
for _s in APP:
    CALLS[_s] = [*CALLS[_s], "dns"]


def callees(service: str) -> list[str]:
    return list(CALLS[service])


def callers(service: str) -> list[str]:
    return [s for s in SERVICES if service in CALLS[s]]


def upstream(service: str) -> dict[str, int]:
    """Every service that (transitively) depends on `service`, with its hop distance."""
    out, frontier, d = {}, [service], 0
    while frontier:
        d += 1
        nxt = []
        for s in frontier:
            for c in callers(s):
                if c not in out and c != service:
                    out[c] = d
                    nxt.append(c)
        frontier = nxt
    return out


def downstream(service: str) -> set[str]:
    seen, stack = set(), list(CALLS[service])
    while stack:
        s = stack.pop()
        if s not in seen:
            seen.add(s)
            stack.extend(CALLS[s])
    return seen
