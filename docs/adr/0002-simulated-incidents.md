# ADR 0002: Simulated incidents with known ground truth

**Status:** accepted

**Context.** Root-cause accuracy needs incidents where the real cause is known. Real incident data is
private, rarely labelled well, and cannot be published.

**Decision.** A deterministic simulator injects one known fault per incident into a 16-service call
graph, propagates it to callers with damping and delay, fires alerts from fixed rules, and writes logs.
Traps that fool simple methods (decoy deploys, CPU flaps, silent roots, missing change records,
injected instructions) are added on purpose and reported separately.

**Consequences.** Every answer can be scored exactly and the suite can be rebuilt byte for byte.
Synthetic telemetry is cleaner than production, so absolute numbers will not transfer; the comparison
between methods is the point.
