# Deployment Guide

## Runtime

Run the API with the configured environment:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render reads `PYTHON_VERSION=3.14` from `render.yaml`; the build command installs the runtime dependencies before starting Uvicorn. Keep all secrets in the deployment provider's secret manager; never put keys, session tokens or passwords in an image, source file or browser bundle.

At startup, ResearchOS initializes its SQLite tables and, when `DEMO_MODE=true`, prepares the isolated Demo Workspace. The startup routine never creates research papers, chunks, embeddings, or FAISS entries.

## Public frontend and API connection

Deploy the repository root to a static hosting service. `vercel.json` builds
`frontend/runtime-config.js` and serves `frontend/` as the static output
directory; its rewrite sends all browser paths back to `index.html`.

For the current Render Static Site, configure these build settings:

```text
Build Command=node scripts/build-runtime-config.mjs
Publish Directory=frontend
RESEARCHOS_API_URL=https://ai-literature-109.onrender.com
```

`RESEARCHOS_API_URL` is a non-secret Static Site build variable. It must be
available to the build command; the committed `frontend/runtime-config.js`
intentionally remains empty. Vercel deployments use the same build variable:

```text
RESEARCHOS_API_URL=https://ai-literature-109.onrender.com
```

Then set the exact Vercel origin in Render (no wildcard):

```text
CORS_ALLOWED_ORIGINS=https://<your-vercel-project>.vercel.app,http://localhost:5173
```

The browser loads the generated runtime config, sends protected requests to the configured Render base URL, and attaches its opaque session token in the request authorization header. Tokens are never written into the generated config.

## Identity

Authentication is enabled by default. A browser must obtain a session from `POST /api/identity/sessions` and present its issued session credential on protected requests. The session token is stored only as a hash on the server and expires after the configured session lifetime.

## Demo deployment

Demo identity seeding is disabled by default. To provision an isolated demo workspace, set all of the following in the deployment environment:

```text
DEMO_MODE=true
DEMO_OWNER_PASSWORD=<deployment-secret>
DEMO_REVIEWER_PASSWORD=<deployment-secret>
```

Optionally set demo emails. Do not enable this option in a customer or production workspace.

## Production checklist

- Confirm HTTPS and allowed browser origins.
- Use managed secrets for model and demo credentials.
- A free Render web service has ephemeral local storage. For a durable public demo, attach a paid Render Persistent Disk at `/var/data`. The included Render configuration maps `WORK_DIRECTORY`, `DATABASE_URL`, and `STORAGE_ROOT` there, keeping SQLite, FAISS, and generated artifacts together. The ignored local `work/` corpus is not deployed automatically; import an approved corpus backup before claiming the hosted diagnostics contain the 7-paper library.
- Verify `/health` and `/researchos/diagnostics` after deployment.
- Confirm that the initial owner has an authorized Workspace membership.
- Verify `POST /api/identity/demo-session`, `GET /api/identity/me`, and `GET /api/missions` with the returned session. A Demo session must receive `403` from `GET /api/organizations`.
