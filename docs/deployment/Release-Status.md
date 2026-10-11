# ResearchOS Release Status

| Release gate | Status | Verified evidence |
|---|---|---|
| Code | PASS | Release Candidate code is committed locally. |
| Tests | PASS | 387 automated tests pass locally. |
| GitHub | PASS | Local `f39286d` matched `origin/main` at the final sync check. |
| Frontend | PASS | Public frontend serves `v169`, release information, and the `v169` service worker. |
| Backend | WAITING USER ACTION | Public API has not yet deployed the release endpoints. |
| Persistent disk | BLOCKED BY ENVIRONMENT | Render Dashboard configuration is outside this environment. |
| `/var/data` persistence | NOT VERIFIED | Code supports the required paths; managed disk persistence has not been tested. |
| Demo corpus | WAITING USER ACTION | Managed API diagnostics previously reported no papers, chunks, embeddings, or FAISS index. |
| Golden Demo | WAITING USER ACTION | Requires deployed backend, persistent disk, real corpus, human review, and Artifact flow. |
| Managed restart | BLOCKED BY ENVIRONMENT | Requires an operator-controlled Render restart after persistence setup. |

Only the statuses above are release claims. No local result is treated as a managed-production result.
