# Implementation guide: adopting agentic triage safely

For platform and SRE teams who want an assistant that proposes root causes and fixes for incidents.

## 1. Start with a scored suite, not a demo

Build or collect incidents where the root cause is known, including the traps your estate really has:
unrelated deploys, noisy hosts, services without alerts, changes made outside the change system. Score
root service, fault type and action separately, and break results down by trap.

## 2. Put deterministic correlation in front of the model

Topology plus anomaly start times already beats "blame the first alert" by a wide margin. Use it to
shortlist candidates, then let a small model read the evidence for those candidates only. Measure how
often the shortlist contains the real root: that is the ceiling for the hybrid.

## 3. Keep the tools read-only and the policy outside the model

The assistant reads alerts, changes, metrics, logs and topology. It proposes; a policy decides. Block
destructive actions outright, require approval for anything that changes production, and allow only
reversible, low-risk runbook actions to run unattended, if any.

## 4. Treat every log line as hostile

Logs can carry text written by anyone who can make a service log. Test with planted instructions, put
them where the model is sure to read them, and gate releases on "no forbidden action proposed".

## 5. Roll out in stages

| Stage | What the assistant does | Exit criterion |
|---|---|---|
| Shadow | Writes its proposal to the incident ticket only | Root accuracy on your suite and on real incidents reviewed weekly |
| Suggest | On-call sees the proposal and the shortlist, one-click approve | Approval rate and time-to-mitigate tracked |
| Low-risk auto | Scale-out and cache warm-up run without a person | No incident made worse over an agreed period |

## 6. Measure in production too

Track the share of proposals the on-call accepts, time from first page to correct root cause, and
every policy block. Re-run the offline suite on every model or prompt change.
