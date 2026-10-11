# ResearchOS Release Status

| Release gate | Status | Verified evidence |
|---|---|---|
| Code | PASS | v200 release configuration and guarded Demo scripts are present locally. |
| Tests | PASS | 395 automated tests pass locally. |
| GitHub | NOT VERIFIED | The current release changes still require an explicit reviewed commit and push. |
| Frontend | PASS (local) | Local static frontend serves `v200` release information and the `v200` service worker. |
| Backend | PASS (local) | The guarded isolated Demo API passes `/health`, `/api/version`, and `/api/release/demo-readiness`. |
| Persistent disk | BLOCKED BY ENVIRONMENT | Render Dashboard configuration is outside this environment. |
| `/var/data` persistence | NOT VERIFIED | Code supports the required paths; managed disk persistence has not been tested. |
| Demo corpus | PASS (local) | Isolated Demo storage contains 6 public papers, 131 chunks, 131 embeddings, and FAISS `PASS`. |
| Golden Demo | PASS (local) | The release check confirms recorded Artifact, approved Mission review, roles, and Workspace alignment. |
| Managed restart | BLOCKED BY ENVIRONMENT | Requires an operator-controlled Render restart after persistence setup. |

Only the statuses above are release claims. No local result is treated as a managed-production result.
