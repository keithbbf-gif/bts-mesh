# BTS Mesh

Multi-model orchestration on one workstation. Six AI families, thirteen lanes, a spend
ledger per lane, and a queue that runs jobs unattended.

**Reviewers start with `QA_BRIEF.md` in the review bundle.** It lists this system's
measured failure classes. Findings against those are worth far more than style notes.

## Layout
- `BTS_MESH/` one module per lane, plus the fan-out, queue runner and health checks
- `ROLD/` the registry (`rails.toml`), the governance documents, and the verifiers

## What is deliberately absent
No credentials, no ledgers, no case material. The publisher works from an allowlist and
re-scans for live key shapes before every commit.
