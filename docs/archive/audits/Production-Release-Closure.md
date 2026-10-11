# Production Release Closure

This is a release gate, not a product capability claim. Each row is intentionally limited to **PASS**, **FAIL**, **NOT VERIFIED**, or **BLOCKED BY ENVIRONMENT**.

| Release gate | Status | Current evidence / required verification |
|---|---|---|
| Local HEAD | PASS | Release-closure repository tests and syntax checks pass locally. |
| GitHub | PASS | `origin/main` matched the local commit at the last synchronization check. |
| Managed deployment identity | FAIL | Public API at `ai-literature-109.onrender.com` returned HTTP 404 for `/api/version` during the latest verification. |
| Frontend version | PASS | Public frontend served `app.js?v=169`, `styles.css?v=169`, `runtime-config.js?v=169`, `release-info.json`, and `researchos-workspace-v169`. |
| Backend version | FAIL | The public API has not yet deployed the safe version endpoint or release identity. |
| Service Worker cache | PASS | Local active shell is `researchos-workspace-v169`; navigation is network-first, activation removes prior shell caches, and runtime config is network-only. |
| Database type | PASS | SQLite. |
| Database persistence | BLOCKED BY ENVIRONMENT | Current Render service persistence cannot be inspected or changed from this environment. Attach a Persistent Disk at `/var/data` and perform a managed restart test. |
| Source PDF persistence | PASS | Source PDFs now use `WORK_DIRECTORY/papers`, alongside SQLite, FAISS and generated artifacts. |
| Demo corpus | FAIL | Public diagnostics reported zero papers, chunks, embeddings and FAISS entries. Seed the approved public corpus on persistent storage. |
| Papers | FAIL | Public count is 0; the release gate requires at least five real, authorized public PDFs. |
| Chunks / embeddings / FAISS | FAIL | Public count is 0 / 0 / missing. |
| Demo readiness | FAIL | `/api/release/demo-readiness` returned HTTP 404 because the backend deployment is stale. |
| Research readiness | FAIL | A real indexed corpus is required; no synthetic research result is allowed. |
| Evidence readiness | NOT VERIFIED | Requires a real Mission and candidate Evidence followed by human review. |
| Review readiness | NOT VERIFIED | Requires a live reviewer action. |
| Artifact readiness | NOT VERIFIED | Requires approved Evidence and a real reviewable Artifact draft. |
| Failure Demo | PASS | Local bounded insufficient-evidence recovery is covered by the release drill and does not manufacture an insight. |
| Golden Demo | BLOCKED BY ENVIRONMENT | It cannot run until the current backend, Persistent Disk and real corpus are deployed. |
| Managed live restart | BLOCKED BY ENVIRONMENT | The platform restart test cannot be claimed until persistent disk is attached and the managed service is restarted during a live Mission. |
| P0 | PASS | 0 confirmed P0 issues in the local release drill. |
| P1 | FAIL | Backend deployment freshness, managed persistence and Demo corpus remain P1 blockers. |
| P2 | NOT VERIFIED | Reassess only after the P1 managed-release gates pass. |

## Acceptance order

1. Deploy the release commit to the existing Render service and verify frontend/backend identity.
2. Attach the Persistent Disk at `/var/data` and redeploy.
3. Run `python scripts/seed_demo_corpus.py` on the deployed service with the real embedding credential.
4. Confirm `/researchos/diagnostics` and `/api/release/demo-readiness` show real corpus readiness.
5. Run the complete Golden Demo: Mission → AI Worker → candidate Evidence → human review → evidence-bound insight → Research Brief → artifact review.
6. Restart the managed service mid-Mission and confirm the persisted Mission/checkpoint/Review state.

Until every required row is PASS, **PRODUCTION READY is NO**.
