# Security policy

This is a portfolio project. Nothing in it is deployed, and it holds no real data: the company
(Velmora Fresh) is fictional and every incident, metric and log line is simulated.

## Report a vulnerability

Please report privately to the repository owner through GitHub (the **Security** tab, **Report a
vulnerability**, when available). Please do not open a public issue. First reply within a week.

## Controls in place

- The triage tools are read-only; no tool can change a service.
- Every proposed action goes through `aiops/policy.py`: forbidden actions are blocked, unknown actions
  and targets are rejected, high-risk actions wait for a person, and only two low-risk runbook actions
  may run unattended.
- Log text is treated as data; an injection stress run is part of the measured results, and the CI gate
  fails if any measured answer proposed a forbidden action.
- Tool-call, turn, token and output-size budgets on every incident.
- Model output is scrubbed of real brand names before it is stored or scored; the brand check excludes
  no file.
- gitleaks over the full git history in CI.
- Dependabot version updates for pip and GitHub Actions.
- Every GitHub Action pinned to a commit SHA; workflow tokens are read-only.
- The deploy workflow is manual, gated by `DEPLOY_ENABLED`, and logs in with OIDC (no client secret).
- Model weights come from pinned revisions and are checked by SHA-256; GGUF only, never pickle files.
- The incident suite and measured runs are checked against a hash manifest.

## Not active while the repository is private

- **Code scanning (CodeQL)**: the workflow is in `.github/workflows/codeql.yml` but the job is skipped
  while the repository is private, because code scanning needs GitHub Code Security on private
  repositories.
- **Branch rules** on `main` (no force-push or deletion, required CI checks) are not enforced on a
  private repository on the current plan. They are applied once the repository is public or the plan
  allows it.
