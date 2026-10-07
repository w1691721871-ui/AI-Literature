# Persistence Verification

## Required managed configuration

The Demo uses a single-instance SQLite deployment. Render must provide a Persistent Disk on a paid plan; free-service local storage is not durable.

```text
Persistent Disk mount: /var/data
WORK_DIRECTORY=/var/data
DATABASE_URL=sqlite:////var/data/research_library.db
STORAGE_ROOT=/var/data/runtime_storage
```

## Persisted locations expected by the current code

| Asset | Location |
|---|---|
| SQLite state | `/var/data/research_library.db` |
| Source PDFs | `/var/data/papers/` |
| FAISS index and mapping | `/var/data/vector_index/` |
| Reviewable Artifacts | `/var/data/artifacts/` |
| Runtime-generated files | `/var/data/runtime_storage/` |

The paths are code-supported but **need deployment-environment verification**. This document does not claim that a Persistent Disk is currently mounted.

## Managed verification

1. Attach a Render Persistent Disk at `/var/data` and redeploy.
2. Run `python scripts/seed_demo_corpus.py` in the Render Shell.
3. Run `python scripts/check_demo_corpus.py`; it must report at least five papers, non-zero chunks/embeddings, and `faiss: PASS`.
4. Create a real Demo Mission and let it reach a persisted state.
5. Restart the API service, sign in again, and verify the corpus, Mission, checkpoint, review state and Artifact references remain.

Until step 5 is complete, managed persistence is **NOT VERIFIED**.
