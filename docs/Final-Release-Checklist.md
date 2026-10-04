# ResearchOS Final Enterprise Demo Release Checklist

## Build and regression

- [ ] Run `python -m compileall app` using the project virtual environment.
- [ ] Run `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
- [ ] Run `node --check frontend/app.js`.
- [ ] Run `node --check frontend/service-worker.js`.
- [ ] Run `git diff --check`.

## Empty-environment startup

- [ ] Start with an empty database and no browser storage.
- [ ] Confirm database initialization completes on application startup.
- [ ] Register a user and confirm a Workspace owner membership is created.
- [ ] Create a Mission and confirm the AI Worker shows an Evidence-required state when no approved Evidence exists.
- [ ] Start a Demo Session and confirm it creates or reuses only the isolated Demo Workspace.

## Identity and permissions

- [ ] Anonymous requests to protected APIs return `401`.
- [ ] A Demo Member cannot open Admin Console or compatibility endpoints.
- [ ] A Viewer can read permitted resources but cannot execute Computer work or approve deliveries.
- [ ] A Reviewer can review permitted resources but cannot execute Missions.
- [ ] An Owner or Admin can access the governed administration surface.
- [ ] Cross-Workspace Mission, Artifact, Knowledge, and Computer access returns `403`.

## Product demonstration

- [ ] Home explains AI Worker → Evidence → Review → Delivery within 30 seconds.
- [ ] Solution Demo Mode presents the customer problem, approach, and reviewable result.
- [ ] Mission Room explains the current stage and next human action without technical logs.
- [ ] Computer Worker shows only controlled, approval-aware work and never claims unrestricted access.
- [ ] Candidate sources are never shown as approved Evidence.
- [ ] Artifacts visibly retain Evidence and review state before release.

## Deployment

- [ ] `DATABASE_URL`, `WORK_DIRECTORY`, `DEMO_MODE`, token settings, and CORS origins are supplied through deployment environment variables.
- [ ] The frontend receives the deployed API base URL through `runtime-config.js`.
- [ ] `runtime-config.js` is not cached by the service worker.
- [ ] `/health` returns an operational status without secrets.
- [ ] Production demo credentials, if enabled, are set only in deployment environment variables.

## Release decision

Release only when every required check above is complete. A missing Evidence review, cross-Workspace access result, or failed startup check blocks the enterprise demonstration release.
