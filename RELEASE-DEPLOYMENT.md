# ResearchOS v200 Public Demo Deployment

This is the deployment procedure for the isolated public Golden Demo. It does
not authorize deploying Demo data into a customer workspace or a shared
database.

## 1. Render backend

Create or update the Render Web Service defined by `render.yaml`:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check: /health
```

Deploy one instance only. SQLite is appropriate for this single-instance Demo;
do not enable horizontal scaling.

## 2. Persistent Disk

Use a Render plan that supports a Persistent Disk and attach a disk at:

```text
Mount path: /var/data
```

The deployment must retain these paths across restart:

| Data | Required path |
| --- | --- |
| SQLite | `/var/data/research_library.db` |
| Source PDFs | `/var/data/papers/` |
| FAISS index and mapping | `/var/data/vector_index/` |
| Research Artifacts | `/var/data/artifacts/` |
| Authorized uploaded files | `/var/data/enterprise_inputs/` |
| Controlled research workspace | `/var/data/research_workspace/` |
| Runtime storage | `/var/data/runtime_storage/` |

Set the backend variables:

```text
DATABASE_URL=sqlite:////var/data/research_library.db
WORK_DIRECTORY=/var/data
STORAGE_PROVIDER=LOCAL
STORAGE_ROOT=/var/data/runtime_storage
```

Do not seed the Golden Corpus until the disk is mounted. A free Render service
uses ephemeral storage and is not a valid durable Demo target.

## 3. Managed environment variables

Set secrets only in the Render dashboard:

```text
DASHSCOPE_API_KEY=<managed secret>
DEMO_OWNER_PASSWORD=<managed secret>
DEMO_REVIEWER_PASSWORD=<managed secret>
```

Set non-secret release and governance configuration:

```text
DEMO_MODE=true
REQUIRE_HUMAN_REVIEW=true
CORS_ALLOWED_ORIGINS=https://<your-frontend-host>
RESEARCHOS_ALLOW_LOCAL_CORS=false
RESEARCHOS_RELEASE=researchos-demo-v200
RESEARCHOS_FRONTEND_VERSION=v200
RESEARCHOS_ENVIRONMENT=demo
```

Do not hardcode `RESEARCHOS_COMMIT` in Render. The API uses Render's managed
`RENDER_GIT_COMMIT` value as its deploy identity. The exact CORS origin must
be HTTPS and must match the frontend host; do not use a wildcard.

## 4. Frontend build and static host

Build the static frontend with a host-specific environment variable:

```text
RESEARCHOS_API_URL=https://<your-render-api-host>
node scripts/build-runtime-config.mjs
```

Use Vercel or a Render Static Site build that runs the command above and
publishes `frontend/`. `runtime-config.js` is intentionally fetched without
caching by the service worker and has an explicit no-cache static-host rule.
Do not commit a generated public or private deployment URL into
`frontend/runtime-config.js`.

## 5. Seed and validate the Demo

After the API has started and the Persistent Disk is available, provision the
dedicated Demo Workspace and seed only the documented public corpus:

```text
python scripts/seed_demo_corpus.py
python scripts/release_smoke_test.py --api-url https://<your-render-api-host>
```

The smoke test is read-only. It must report `PASS` for every endpoint before
an FDE presentation. It verifies:

```text
/health
/api/version
/api/release/demo-readiness
/researchos/diagnostics
```

`/researchos/diagnostics` is a protected legacy compatibility diagnostic. By
default the smoke test passes only when it returns `401` or `403`, proving it
is not publicly exposed; real Demo corpus readiness is verified through
`/api/release/demo-readiness`. Supply `--admin-session-token` only for an
authorized compatibility-administration verification.

Finally restart the Render service once and run the smoke test again. Verify
that the Demo Workspace, corpus, FAISS, review records, and Artifacts remain
available before marking the public Demo as ready.
