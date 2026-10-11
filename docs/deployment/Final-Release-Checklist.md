# Final Release Checklist

| Gate | Current status |
|---|---|
| GitHub | WAITING USER ACTION — v200 release changes require reviewed commit and push. |
| Frontend | PASS (local) — `v200` assets and release identity are available. |
| Backend | PASS (local) — guarded Demo API exposes the release endpoints with v200 identity. |
| Persistent storage | WAITING ENVIRONMENT — requires Render Persistent Disk at `/var/data`. |
| Demo corpus | PASS (local) — 6 papers, 131 chunks, 131 embeddings, FAISS available. |
| Golden Demo | PASS (local) — isolated release check validates corpus, roles, recorded review and Artifact flow. |
| Failure Demo | PASS locally — insufficient Evidence remains bounded and review-gated. |
| Pause / resume | PASS locally — persisted checkpoint recovery is covered by automated tests. |

The release is not production-ready until every managed gate is independently verified.
