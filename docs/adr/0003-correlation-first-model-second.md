# ADR 0003: Correlation engine first, model second (hybrid)

**Status:** accepted

**Context.** A small model asked to find the root cause from raw alerts tends to blame the loudest or
first alert. A topology-aware correlation engine is fast and good at finding where an anomaly started,
but cannot read logs, so it misses faults that are only visible in text and is fooled by unrelated
early spikes.

**Decision.** The main configuration lets the correlation engine shortlist three candidates (earliest
anomaly not explained by an anomalous dependency), then gives the model the metrics, topology and logs
of just those three. The free tool-using agent and a page-only one-shot answer are measured as
alternatives with the same model.

**Consequences.** The model's job becomes reading and confirming, which suits a 2B model. The hybrid can
never do better than its shortlist; the report shows how often the shortlist contains the root.
