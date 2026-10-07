# ResearchOS Final Deployment Runbook

## 1. GitHub Sync

```text
git push origin main
```

Confirm the local commit equals `origin/main` before deploying. Do not deploy a locally unpushed release.

## 2. Render Backend Deploy

Service: `https://ai-literature-109.onrender.com` (`researchos-api`)

1. Open the Render Web Service.
2. Confirm it is connected to the intended GitHub repository and `main` branch.
3. Choose **Manual Deploy → Deploy latest commit**.
4. Confirm Render uses:

```text
Build: pip install -r requirements.txt
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health: /health
```

## 3. Persistent Disk

Use a Render plan that supports a Persistent Disk.

```text
Mount Path: /var/data
WORK_DIRECTORY=/var/data
DATABASE_URL=sqlite:////var/data/research_library.db
STORAGE_ROOT=/var/data/runtime_storage
```

After deployment, the following must be verified on the mounted disk:

- SQLite database
- uploaded PDF sources
- FAISS index and mapping
- embedding metadata
- generated Artifacts

The current code maps those locations beneath `/var/data`; mounting the disk remains a Render environment action.

## 4. Seed Demo Corpus

Create a Demo Session once, then open a Render Shell for the API service and run:

```text
python scripts/seed_demo_corpus.py
python scripts/check_demo_corpus.py
```

The second command must report:

```text
papers: 5 or more
chunks: greater than 0
embeddings: greater than 0
faiss: PASS
```

The seed imports only the specified public PDFs through the existing parser, chunking, embedding, and FAISS pipeline. It never creates synthetic Evidence, reviews, insights, or Artifacts.

## 5. Backend Verification

Confirm HTTP 200 responses from:

```text
/health
/api/version
/api/release/demo-readiness
/researchos/diagnostics
```

`/api/version` must identify the deployed release without exposing secrets. `/api/release/demo-readiness` must report real persisted counts and must not report READY until the actual corpus is indexed.

## 6. Restart Verification

1. Create a real Demo Mission and retain its ID, runtime checkpoint, Evidence count, Review state, Artifact state, and FAISS count.
2. Restart the Render API service.
3. Sign in again and confirm the same Mission, checkpoint, Evidence, Review, Artifact, and FAISS records remain.

Only this managed-service test verifies persistence. A local restart rehearsal is not a substitute.
