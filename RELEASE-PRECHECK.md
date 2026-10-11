# ResearchOS Public Release Precheck — v200

**Audited commit:** `35fc0eb8709e141c6fa66124242660905acab476`
**Release identity:** `researchos-demo-v200` / frontend `v200` / environment `demo`

This document separates source-controlled readiness from managed-environment
verification. A managed deployment is not represented as ready until its
live checks have passed.

## PASS

- **Release identity:** The frontend release metadata and the backend defaults
  both identify `researchos-demo-v200` and `v200`. The guarded Demo startup
  rejects a frontend/backend version mismatch.
- **Deploy revision identity:** The API prefers an explicit
  `RESEARCHOS_COMMIT` and otherwise uses Render's deploy-provided
  `RENDER_GIT_COMMIT`; no static SHA is embedded in `render.yaml`.
- **Frontend configuration safety:** The committed `runtime-config.js` has an
  empty API URL. The deployment build injects `RESEARCHOS_API_URL`; no local
  LAN address is published. Both Vercel and the Nginx static configuration
  mark `runtime-config.js` as non-cacheable, and the service worker fetches it
  with `no-store`.
- **Demo/development isolation:** `demo/.env` and all `demo/work/` state are
  ignored. The isolated launcher validates that Demo SQLite and workspace
  paths remain under `demo/work/` before importing the application.
- **Persistent-path support in code:** The configured production paths place
  SQLite at `/var/data/research_library.db` and storage, PDFs, FAISS,
  embeddings, Artifacts, authorized uploads, and the controlled research
  workspace beneath `/var/data`.
- **Secret and artifact hygiene:** No tracked database, vector index, upload,
  local environment file, PDF, private-key file, or file larger than 5 MB was
  found. `.gitignore` also excludes Demo backups and common binary/vector
  artifacts.
- **CORS implementation:** Browser origins are an explicit comma-separated
  allowlist with no wildcard fallback. Managed deployments do not admit
  localhost unless an operator explicitly enables the development-only flag;
  credentials are not enabled. A controlled preflight returned `200` and the
  exact allow-origin header for an approved HTTPS origin, and `400` for
  `http://localhost:5173` when the local flag was disabled.
- **Local release gate:** The isolated Golden Demo release check previously
  passed with a real six-paper corpus, 131 chunks, 131 embeddings, readable
  FAISS, Demo Owner/Reviewer memberships, persisted review state, and
  persisted Artifacts.

## BLOCKED — managed deployment actions

- **Persistent Disk:** `render.yaml` currently selects Render's `free` plan
  and declares no persistent disk. A durable public Demo requires a
  single-instance paid Render service with a Persistent Disk mounted at
  `/var/data`. Do not seed the hosted corpus before this is attached.
- **Deployment secrets:** In the Render service, set
  `DASHSCOPE_API_KEY`, `DEMO_OWNER_PASSWORD`, and
  `DEMO_REVIEWER_PASSWORD`. These values are intentionally `sync: false` and
  cannot be verified from Git.
- **Exact CORS origin:** Set `CORS_ALLOWED_ORIGINS` to the exact HTTPS frontend
  origin or origins. The manifest intentionally leaves this service-specific
  value uncommitted.
- **Frontend host:** Build the static frontend with
  `RESEARCHOS_API_URL=https://<api-host>` and verify that its served
  `runtime-config.js` is non-empty, HTTPS, and points only to the released
  API. The Docker Nginx image can serve static files but does not run the
  runtime-config build script; use Vercel/Render Static build or generate the
  file before creating an immutable image.
- **Live release verification:** Deploy the Git commit, then confirm
  `/health`, `/api/version`, `/api/release/demo-readiness`, and
  `/researchos/diagnostics`. Verify the actual deployed SHA, `v200`, the
  Demo Workspace, corpus, FAISS, and a restart-persistence check.

## FAIL

None in the source-controlled release configuration.

## Required operator sequence

1. Review and commit the release configuration; do not commit ignored Demo
   data or local secrets.
2. In Render, use a single-instance plan with a Persistent Disk at
   `/var/data`; set the blocked secrets and explicit `CORS_ALLOWED_ORIGINS`.
3. Deploy the release commit, verify the live release endpoints, then seed the
   real public corpus once into the dedicated Demo service.
4. Build/deploy the frontend with the released API URL, validate CORS from its
   exact origin, and run the live release check.

## Commit decision

The repository changes are safe to review and commit. This precheck does
**not** mark the public release as complete: managed deployment validation is
still blocked by the actions above.
