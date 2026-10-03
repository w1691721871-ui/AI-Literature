# Deployment Guide

## Runtime

Run the API with the configured environment and a persistent data volume:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The repository also includes container configuration for frontend, backend, worker runtime, database and vector storage. Keep all secrets in the deployment provider's secret manager; never put keys, session tokens or passwords in an image, source file or browser bundle.

## Identity

Authentication is enabled by default. A browser must obtain a session from `POST /api/identity/sessions` and present `Authorization: Bearer <session token>` on protected requests. The session token is stored only as a hash on the server and expires after the configured session lifetime.

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
- Persist database, artifacts and vector index outside ephemeral containers.
- Verify `/health` and `/researchos/diagnostics` after deployment.
- Confirm that the initial owner has an authorized Workspace membership.
