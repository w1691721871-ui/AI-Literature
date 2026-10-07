# Render production setup

This procedure makes the existing `researchos-api` Render web service a durable, single-instance Demo deployment. It does not claim a hosted release is ready until the verification steps pass.

## 1. Select the service

In Render, open the **Web Service** serving `https://ai-literature-109.onrender.com` (the service name in `render.yaml` is `researchos-api`). Confirm its connected repository and branch are the branch containing the release-closure commit.

## 2. Build and start commands

Set the following exact commands:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

The service listens on Render's assigned `$PORT`; do not set a fixed port.

## 3. Persistent Disk (required for a durable Demo)

Render free web services have ephemeral filesystems. Upgrade the single-instance service to a plan that supports a Persistent Disk, then add one disk with:

```text
Name: researchos-data
Mount path: /var/data
Size: 1 GB or larger
```

Do not enable horizontal scaling with SQLite. A Persistent Disk plus SQLite is appropriate only for this one-instance Demo. A later multi-instance deployment requires PostgreSQL and shared object storage.

## 4. Environment variables

Set these values on the same Render web service. Keep credentials secret and do not place them in `render.yaml` or Git.

```text
DATABASE_URL=sqlite:////var/data/research_library.db
WORK_DIRECTORY=/var/data
STORAGE_PROVIDER=LOCAL
STORAGE_ROOT=/var/data/runtime_storage
DEMO_MODE=true
REQUIRE_HUMAN_REVIEW=true
TOKEN_EXPIRE=43200
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=1024
DASHSCOPE_API_KEY=<secret>
CORS_ALLOWED_ORIGINS=https://ai-literature-13.onrender.com
RESEARCHOS_RELEASE=release-closure-v169
RESEARCHOS_COMMIT=<the deployed Git commit>
RESEARCHOS_FRONTEND_VERSION=v169
RESEARCHOS_BACKEND_VERSION=api-2026.10
```

Use the actual frontend origin in `CORS_ALLOWED_ORIGINS`. Add a second comma-separated origin only when another deployed frontend must call this API.

## 5. Deploy and confirm identity

Choose **Manual Deploy → Deploy latest commit**. When deployment completes, verify:

```text
GET /health
GET /api/version
GET /api/release/demo-readiness
GET /researchos/diagnostics
```

`/api/version` must identify the deployed commit and report `frontend_version: v169`. The frontend static host must serve `/release-info.json` with the same frontend version. If either still reports an older version, the deployment is stale; redeploy before accepting the release.

## 6. Seed the real public-paper corpus once

First create the isolated Demo Workspace by using **Try Demo** once, or issue `POST /api/identity/demo-session`. With the Persistent Disk and embedding key configured, open a Render Shell for this service and run:

```text
python scripts/seed_demo_corpus.py
```

The script imports six specified public arXiv PDFs through the existing PDF → chunk → embedding → FAISS path. It is idempotent: a matching filename and SHA-256 source hash is skipped; a changed source stops for manual review. It never creates Evidence, approvals, insights or artifacts.

After it succeeds, `/researchos/diagnostics` must show real papers, chunks, embedded chunks and FAISS `PASS`; `/api/release/demo-readiness` must no longer report the corpus or research checks as `BLOCKED`.

## 7. Verify persistence

Create a live Mission, let it reach a visible bounded state, then restart the Render service. Sign in again and confirm the Mission, checkpoint, review state and artifact references remain. Record the result in `Production-Release-Closure.md`; do not mark the live restart test as PASS without this managed-service test.
