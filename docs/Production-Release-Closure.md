# Production Release Closure

This is a release gate, not a product capability claim. Each row is intentionally limited to **PASS**, **BLOCKED**, or **NOT VERIFIED**.

| Release gate | Status | Current evidence / required verification |
|---|---|---|
| Local HEAD | PASS | Local repository has the release-closure changes; record the final commit after commit creation. |
| Remote HEAD | BLOCKED | `origin/main` is behind the local release chain and must be updated manually by an authorized operator. |
| Managed deployment identity | BLOCKED | Public service has not yet served the new `/api/version` identity endpoint. |
| Frontend version | BLOCKED | Public frontend previously served `app.js?v=153`; expected active asset version is `v169`. |
| Backend version | NOT VERIFIED | Verify `/api/version` after managed deploy and set the release environment variables. |
| Service Worker cache | PASS | Local active shell is `researchos-workspace-v169`; navigation is network-first, activation removes prior shell caches, and runtime config is network-only. |
| Database type | PASS | SQLite. |
| Database persistence | BLOCKED | Current managed `free` service has no declared Persistent Disk. Configure `/var/data` as described in `Render-Production-Setup.md`. |
| Source PDF persistence | PASS | Source PDFs now use `WORK_DIRECTORY/papers`, alongside SQLite, FAISS and generated artifacts. |
| Demo corpus | BLOCKED | The managed diagnostics previously reported zero papers, chunks, embeddings and FAISS entries. Seed the approved public corpus on persistent storage. |
| Papers | BLOCKED | Require at least five real, authorized public PDFs. |
| Chunks / embeddings / FAISS | BLOCKED | Require successful existing parser, chunker, embedding provider and FAISS build. |
| Research readiness | BLOCKED | Real indexed corpus is required; no synthetic research result is allowed. |
| Evidence readiness | NOT VERIFIED | Requires a real Mission and candidate Evidence followed by human review. |
| Review readiness | NOT VERIFIED | Requires a live reviewer action. |
| Artifact readiness | NOT VERIFIED | Requires approved Evidence and a real reviewable Artifact draft. |
| Failure Demo | PASS | Local bounded insufficient-evidence recovery is covered by the release drill and does not manufacture an insight. |
| Golden Demo | BLOCKED | Requires all real corpus, Evidence, human review and Artifact gates above. |
| Managed live restart | BLOCKED | The platform restart test cannot be claimed until persistent disk is attached and the managed service is restarted during a live Mission. |
| P0 | PASS | 0 confirmed P0 issues in the local release drill. |
| P1 | BLOCKED | Deployment freshness, managed persistence and Demo corpus remain P1 blockers. |
| P2 | NOT VERIFIED | Reassess only after the P1 managed-release gates pass. |

## Acceptance order

1. Deploy the release commit to the existing Render service and verify frontend/backend identity.
2. Attach the Persistent Disk at `/var/data` and redeploy.
3. Run `python scripts/seed_demo_corpus.py` on the deployed service with the real embedding credential.
4. Confirm `/researchos/diagnostics` and `/api/release/demo-readiness` show real corpus readiness.
5. Run the complete Golden Demo: Mission → AI Worker → candidate Evidence → human review → evidence-bound insight → Research Brief → artifact review.
6. Restart the managed service mid-Mission and confirm the persisted Mission/checkpoint/Review state.

Until every required row is PASS, **PRODUCTION READY is BLOCKED**.
