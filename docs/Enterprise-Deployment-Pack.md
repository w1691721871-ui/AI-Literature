# Enterprise Deployment Pack

This handoff package describes the supported ResearchOS v2.0 deployment
boundary. It does not turn a demo SQLite deployment into a multi-region
production service.

## Architecture

```text
Browser / Static frontend
        │ opaque session token
        ▼
FastAPI API ── Identity / Workspace / RBAC / Audit
        │
        ├── Unified AI Worker Runtime → Review boundary
        ├── SQLite state + FAISS index on persistent storage
        └── Worker process → bounded queued Mission work
```

The frontend is never authoritative for identity, Workspace, role or approval.
All protected APIs resolve those from the server-side session.

## Docker quick start

1. Copy `.env.example` to a private `.env`.
2. Set only deployment-managed secrets in `.env` or the container platform's
   secret store. Do not insert real values into source or images.
3. Start the controlled local stack:

   ```text
   docker compose up --build
   ```

4. Open `http://localhost:8080`, then verify `http://localhost:8000/health`.
5. Before demo acceptance, check `/researchos/diagnostics` against the real
   deployed corpus. A fresh state volume may intentionally have no papers,
   chunks or FAISS entries.

`docker-compose.yml` starts a frontend, backend and bounded worker against the
same mounted `researchos_state` volume. The optional PostgreSQL service is a
future boundary only; the active runtime remains SQLite-compatible.

## Environment categories

| Category | Variables | Handling |
| --- | --- | --- |
| State | `DATABASE_URL`, `WORK_DIRECTORY`, `STORAGE_ROOT`, `STORAGE_PROVIDER` | Persistent, access-controlled storage |
| Identity | `TOKEN_EXPIRE`, `SECRET_KEY` | Secret manager; sessions are opaque and hashed server-side |
| Model | `DASHSCOPE_API_KEY`, `LLM_*`, `EMBEDDING_*` | Secret manager; never expose to frontend |
| Demo | `DEMO_MODE`, `DEMO_*` | Isolated non-customer environment only |
| Network | `CORS_ALLOWED_ORIGINS`, `RESEARCHOS_API_URL` | Exact frontend origins; no wildcard CORS |
| Limits | `RUNTIME_MAX_RETRIES`, `WORKER_POLL_SECONDS`, `REQUIRE_HUMAN_REVIEW` | Bounded operational configuration |

See `.env.example` for the complete template. `RESEARCHOS_API_URL` belongs to
the static-site build environment and is intentionally absent from the checked
in runtime configuration.

## Release checks

- [ ] `/health` returns the actual API/storage/worker/vector status.
- [ ] `/researchos/diagnostics` reports the actual corpus; do not claim sample
  counts unless they are present on the persistent volume.
- [ ] Login, registration and Demo Session all resolve `/api/identity/me`.
- [ ] A Demo session cannot access organization or administrator APIs.
- [ ] Mission creation, Evidence review, Artifact review and controlled
  Computer approval are exercised with a Workspace-scoped session.
- [ ] Public research discovery returns candidate metadata only; no candidate
  is represented as approved Evidence without validation.
- [ ] Backups cover SQLite state, artifact storage and FAISS assets together.

## Operational ownership

| Responsibility | Owner |
| --- | --- |
| Organization and member administration | OWNER / ADMIN |
| Mission execution and controlled recovery | OWNER / ADMIN / MANAGER / MEMBER |
| Evidence and Artifact review | OWNER / ADMIN / MANAGER / REVIEWER |
| Runtime, diagnostics and audit investigation | OWNER / ADMIN |

Refer to [Permission-Matrix.md](Permission-Matrix.md) for the enforced role
matrix and [Risk-Boundary.md](Risk-Boundary.md) for AI execution limits.
