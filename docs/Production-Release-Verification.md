# Production Release Verification

Verification performed against the public services on 2026-10-07. This record distinguishes observable managed state from local repository state.

## GitHub commit

| Check | Result |
|---|---|
| Local HEAD | `f2df747899035f602c79ecbeb2d70f9101971aba` |
| `origin/main` | `f2df747899035f602c79ecbeb2d70f9101971aba` |
| GitHub synchronization | PASS |

## Render frontend

| Check | Result |
|---|---|
| `release-info.json` | HTTP 200 |
| Frontend version | `v169` |
| Frontend release label | `release-closure-v169` |
| Static release status | PASS |

## Render backend

| Check | Result |
|---|---|
| `/api/version` | HTTP 200 |
| Service | `researchos-api` |
| Backend version | `api-2026.10` |
| Frontend version reported by API | `v169` |
| Release | `local-unlabeled` |
| Commit | `not-configured` |
| Environment | `unlabeled` |
| Backend deployment identity | NOT VERIFIED |

The public API contains the release endpoints, but its Render environment variables do not identify the deployed Git commit. It must not be claimed to be running `f2df747` until `RESEARCHOS_RELEASE`, `RESEARCHOS_COMMIT`, and `RESEARCHOS_ENVIRONMENT` are configured and the service is redeployed.

## API and data state

| Check | Result |
|---|---|
| `/api/release/demo-readiness` | HTTP 200, `NOT_READY` |
| Database | PASS — records can be read |
| Demo Workspace / members | BLOCKED — not provisioned |
| Papers | `0` |
| Chunks | `0` |
| Embeddings | `0` |
| FAISS | missing |
| Research / Evidence / Artifact readiness | BLOCKED — no real indexed corpus or reviewed output |
| `/researchos/diagnostics` anonymous request | HTTP 401 — protected admin compatibility route |

The corpus has **not** recovered on the managed service. No Evidence, Insight, Review, or Artifact is claimed as production-verified.

## Remaining blockers

1. Configure the Render release identity environment variables with the deployed commit.
2. Attach and verify a Persistent Disk at `/var/data`.
3. Create the Demo Workspace and seed the approved real-paper corpus.
4. Verify non-zero chunks and embeddings plus a readable FAISS index.
5. Use an authorized administrator session to inspect `/researchos/diagnostics`.
6. Run the Golden Demo and managed restart persistence verification.
