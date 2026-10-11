# Final Release Checklist

| Gate | Current status |
|---|---|
| GitHub | BLOCKED — latest local commit requires a successful push after network recovery. |
| Frontend | PASS — public `v169` assets and release identity are available. |
| Backend | WAITING DEPLOYMENT — current public API is older and returns 404 for release endpoints. |
| Persistent storage | WAITING ENVIRONMENT — requires Render Persistent Disk at `/var/data`. |
| Demo corpus | WAITING SEED — no managed papers, chunks, embeddings, or FAISS index yet. |
| Golden Demo | WAITING DATA — only run after current backend, persistent storage and corpus checks pass. |
| Failure Demo | PASS locally — insufficient Evidence remains bounded and review-gated. |
| Pause / resume | PASS locally — persisted checkpoint recovery is covered by automated tests. |

The release is not production-ready until every managed gate is independently verified.
