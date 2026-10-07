# Backend Deployment Recovery

## Current backend problem

The public frontend is current (`v169`), but the Render API at `https://ai-literature-109.onrender.com` is an older backend release. During the latest verification it returned HTTP 404 for both `/api/version` and `/api/release/demo-readiness`.

This is not an endpoint implementation failure: both endpoints exist in the current repository. The API service must deploy the current GitHub `main` commit after GitHub synchronization succeeds.

## Why the frontend works while the backend is old

The frontend is deployed as a separate static service and has already rebuilt its `v169` assets. The API service has not redeployed the same release. The browser can still obtain a Demo Session from the old API, but it cannot verify the new release identity or Demo readiness gates.

## Required Render action

1. Confirm GitHub `main` contains the intended release commit. The required commit at this recovery step is `6cc8a75` or a later documented release-closure commit.
2. In Render, open the **Web Service** at `ai-literature-109.onrender.com` (`researchos-api`).
3. Select **Manual Deploy → Deploy latest commit**.
4. Restart only after deployment completes if Render does not restart the process automatically.
5. Verify these public endpoints return HTTP 200:

```text
/health
/api/version
/api/release/demo-readiness
/researchos/diagnostics
```

6. Confirm `/api/version` identifies `researchos-api`, the deployed commit, `frontend_version: v169`, and no secret values.

Do not mark the backend deployment as current until the public endpoints—not the Render dashboard alone—confirm it.
