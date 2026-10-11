# Final Release Validation

## Current version

| Item | Status | Verified value |
|---|---|---|
| Local / GitHub commit | PASS | `main` matched `origin/main` during this validation; use the deployed Git commit value when configuring Render. |
| Frontend release | PASS | Public frontend serves `v169` assets, `release-info.json`, and `researchos-workspace-v169`. |
| Backend endpoint availability | PASS | Public API serves `/api/version` and `/api/release/demo-readiness`. |
| Backend release identity | NOT VERIFIED | Public `/api/version` reports `local-unlabeled`, `not-configured`, and `unlabeled`; Render release variables are not configured. |

## Passed items

- FastAPI health endpoint returned HTTP 200 with database and storage reachable.
- Demo identity, Workspace initialization, Mission creation, AIWorkerRuntime execution, and runtime snapshot were exercised on the managed API.
- With no corpus, the managed Mission reached `WAITING_REVIEW` and returned `INSUFFICIENT_EVIDENCE`; no trusted Insight was claimed.
- Frontend navigation documents use network-first loading; `runtime-config.js` is network-only; active cache cleanup removes previous ResearchOS shell caches.
- Code paths place SQLite, PDFs, FAISS data, Artifacts, and runtime storage beneath `WORK_DIRECTORY` when deployed with `/var/data`.
- Final release gate tests cover legacy-route isolation, the single AIWorkerRuntime gateway, Computer permission boundaries, evidence/review boundaries, workspace isolation declarations, and persistent storage declarations.

## Unverified or blocked items

| Item | Status | Reason |
|---|---|---|
| Persistent Disk | BLOCKED BY ENVIRONMENT | Render Dashboard disk configuration cannot be inspected or changed here. |
| `/var/data` restart persistence | NOT VERIFIED | A managed restart with persisted state has not been performed. |
| Corpus | NOT VERIFIED | Managed readiness reports 0 papers, 0 chunks, 0 embeddings, and no FAISS index. |
| Evidence / human review | NOT VERIFIED | Requires real indexed sources and an authorized reviewer action. |
| Artifact release | NOT VERIFIED | Requires approved Evidence and a real reviewable Artifact. |
| Golden Demo | NOT VERIFIED | Requires the persisted real corpus, review, and delivery path. |

## Pre-release manual steps

1. In the Render API service, set `RESEARCHOS_RELEASE`, `RESEARCHOS_COMMIT=<deployed Git commit>`, and the documented production environment variables.
2. Attach a paid Render Persistent Disk at `/var/data`, then redeploy the API service.
3. Create a Demo Session and seed the approved real corpus with `python scripts/seed_demo_corpus.py`.
4. Confirm `python scripts/check_demo_corpus.py` reports at least five papers, non-zero chunks and embeddings, and `faiss: PASS`.
5. Recheck `/api/version`, `/api/release/demo-readiness`, and `/researchos/diagnostics` with an authorized administrator session.
6. Execute the Golden Demo and a managed restart persistence test before any production-ready claim.
