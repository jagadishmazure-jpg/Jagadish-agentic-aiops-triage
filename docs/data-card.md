# Data card: simulated incident suite

| Field | Value |
|---|---|
| What | 80 simulated production incidents in the platform of a fictional online grocer, Velmora Fresh |
| Generator | `aiops/simulate.py`, deterministic from each incident id (SHA-256 seed); `scripts/build_incidents.py --check` rebuilds and compares in CI |
| Real data | None. No real systems, logs, people or companies |
| Services | 16: 11 application services, 4 data services (two Postgres databases, a cache, an event bus) and DNS; call graph in `aiops/topology.py` |
| Fault types | 10, eight incidents each: bad deploy, config error, memory leak, noisy neighbour, slow dependency, database pool exhaustion, disk full, certificate expiry, cache stampede, DNS failure |
| Per incident | 60 minutes of per-minute metrics for every service, the alerts that fired, change records, and log lines per service |
| Ground truth | Root-cause service, fault type, fault start minute and trap flags. Hidden from every triage method by `public_view` |
| Split | 19 dev / 61 test by a fixed hash of the id. Prompts were written looking only at dev incidents |
| File | `data/incidents.jsonl` (about 2.2 MB), pinned in `data/manifest.json` |

## How an incident is built

1. Every service gets a quiet 15-minute baseline with noise.
2. The fault is injected into the root service at minute `t0` (20 to 30): its own metric signature
   (errors, latency, CPU, memory, connections, disk or cache hit rate).
3. The effect spreads to callers, damped and delayed by hop distance, so victims alert too and often
   alert first.
4. Alerts fire when a rule holds for two consecutive minutes (thresholds in `aiops/simulate.py`).
5. Logs: routine noise on every service, the fault's signature lines on the root, and timeout errors
   naming the failing callee on affected callers.

## Traps (measured separately in the report)

| Trap | Share | What it does |
|---|---|---|
| Decoy change | about half | An unrelated deploy on another service a few minutes before the fault |
| Flapping CPU | about 40% | A short CPU spike on an unrelated service, often before the fault |
| Silent root | about a quarter | The root service has no alert rule firing; only its victims page |
| Injected instruction | about a fifth | A log line on a non-root service tells "automated assistants" to delete a database and skip approval |
| Missing change record | half of config errors | The config was changed outside the change system |

The injection stress configuration (`gemma4-e2b.hybrid-injected`) adds the same instruction to the root
service's own log on every incident, so the model is guaranteed to read it.

## Known limits

Synthetic metrics are cleaner than production telemetry, faults are single and independent, and the
call graph is small and static. Results show how the methods compare on this suite, not how they will
do on a real estate.
