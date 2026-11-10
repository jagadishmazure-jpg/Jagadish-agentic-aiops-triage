# Interview points

- **What problem does this solve?** Pages fire on victims, not causes. Most alerts in an incident come
  from services that are only suffering; the on-call has to work back through the call graph. The repo
  measures how much a correlation engine and a small model each help, and where they fail.
- **Why a hybrid instead of a free agent?** The correlation engine is very good at "where did it start"
  and cannot read text. A 2B model is weak at multi-step investigation but good at reading three
  services' logs and naming the fault. Splitting the work plays to both. The free agent is measured too.
- **How do you know the numbers are real?** Deterministic simulator with ground truth; runs measured
  once and committed; CI rebuilds the incidents, re-scores every answer and fails on any drift,
  including the numbers quoted in the README.
- **What about prompt injection?** Logs are untrusted. There is a dedicated stress run where every root
  log tells the model to delete a database. Tools are read-only, and the policy blocks forbidden actions
  no matter what the model says; CI fails if any measured answer proposed one.
- **What does it cost?** Seconds per incident on CPU for the hybrid; the cloud version is a
  scale-to-zero CPU node at $0.384 per hour, written but not deployed.
- **What would you do next?** Real alert feed in shadow mode, accept-rate tracking, multi-fault
  incidents, and a larger model only for the cases the hybrid gets wrong.
