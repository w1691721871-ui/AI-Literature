# ResearchOS

**AI Research Employee for Enterprise Research Teams**

ResearchOS helps teams turn a research question into traceable Evidence, a human-reviewed decision, and a reusable research Delivery. It is designed for enterprise R&D, applied research, and solution-delivery teams that need a visible, governed research path—not an untraceable chat response.

## Start here

- [FDE Solution Overview](docs/product/FDE-Solution-Overview.md) — the customer problem, governed solution, technical design, and business value.
- [Golden Demo Guide](docs/product/Golden-Demo-Guide.md) — the real Mission → Evidence → Review → Delivery demonstration path.
- [Architecture at a glance](#architecture-at-a-glance) — the bounded enterprise system behind the product experience.

## Product Overview

ResearchOS is an AI Research Employee for enterprise research teams. It accepts an authorized research Mission, organizes supporting Evidence, pauses for Human Review where a decision matters, and prepares a traceable Delivery that can become Workspace knowledge.

## What users experience

```text
Customer problem
  → Research Mission
  → AI Employee prepares research work
  → Evidence is collected and kept reviewable
  → Human Review validates consequential decisions
  → Research Delivery is prepared
  → Approved knowledge stays in the Workspace
```

The customer-facing product language is intentionally simple:

- **Mission** — the authorized research outcome.
- **Evidence** — traceable source support; candidate sources are not conclusions.
- **Human Review** — people validate consequential research and release decisions.
- **Artifact / Delivery** — a reviewable research outcome with an Evidence trail.
- **Workspace Knowledge** — approved work that can support future work in the same authorized Workspace.

## Why ResearchOS

| A chat response | ResearchOS AI Employee |
| --- | --- |
| Answers a question in one interaction | Moves an authorized Mission through a visible work path |
| Can hide its source basis | Keeps Evidence and review state visible |
| Has no organizational handoff | Produces a reviewable Delivery and Workspace knowledge |
| Can imply completion | Pauses when Evidence or human validation is required |

## Product principles

1. **Evidence first** — a candidate source is never presented as verified Evidence automatically.
2. **Human control** — consequential review and delivery decisions remain with authorized people.
3. **Workspace isolation** — research context and organizational knowledge stay within the authorized Workspace.
4. **No synthetic success** — missing Evidence, pending Review, and unavailable Delivery states remain visible.
5. **Bounded assistance** — the Computer Employee prepares authorized research, document, and report work; it does not perform hidden external actions.

## Trust Boundary

ResearchOS does not present candidate sources as verified Evidence, make unsupported research conclusions, or release consequential work without an authorized human decision. Prompts, chain-of-thought, credentials, and private source content are not exposed in the browser interface. Workspace-scoped access and role checks remain the boundary for every customer-facing record.

## Golden Demo

The reference scenario is a building-materials R&D team exploring sustainable, low-carbon construction materials.

1. Open **Home** and introduce the AI Research Employee.
2. Open **Solution Showcase** to frame customer challenge, solution, governance, and business value.
3. Use the **Golden Demo Guide** to open the live Mission or prepare the standard Mission form.
4. In **Mission Room**, show the research goal, work journal, and supporting Evidence.
5. Use an authorized **Reviewer** session to demonstrate the human decision boundary when a real review is waiting.
6. Open the recorded **Delivery** only when its real state permits it.
7. Close with the Workspace view: verified work becomes reusable organizational knowledge.

For operator steps and recovery guidance, see:

- [Golden Demo Runbook](docs/product/Golden-Demo-Runbook.md)
- [Golden Value Delivery Demo](docs/product/Golden-Value-Delivery-Demo.md)
- [FDE Demo Flow Optimization](docs/product/FDE-Demo-Flow-Optimization.md)
- [Final Release Readiness](docs/deployment/Release-Readiness-Final.md)

## Architecture at a glance

```text
Frontend (static Vue application)
        │
        ▼
FastAPI application
        │
        ├── Identity and Workspace boundary
        ├── Mission, Evidence, Review, Artifact, and Delivery records
        └── SQLite + local FAISS index for the Demo deployment
```

The browser interface does not expose prompts, chain-of-thought, credentials, or private source content as product data.

## Local development

### Backend

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use a local static server for `frontend/`, or deploy the static directory through the configured hosting workflow. Configure the frontend API base URL with `RESEARCHOS_API_URL`; `runtime-config.js` is generated at build time and is intentionally not cached by the service worker.

### Local endpoints

- **Frontend:** `http://127.0.0.1:5173` — for example, run `python -m http.server 5173 --directory frontend` from the repository root.
- **Backend:** `http://127.0.0.1:8000` — started by the FastAPI command above.

The local frontend resolves its API base URL to the local backend. Production uses the generated `runtime-config.js` value instead.

### Verification

```powershell
python -m unittest discover -s tests -q
node --check frontend/app.js
node --check frontend/service-worker.js
git diff --check
```

## Deployment

ResearchOS uses a static frontend and a FastAPI API service.

### Frontend

- **Hosting:** Vercel or Render Static Site
- **Build command:** `node scripts/build-runtime-config.mjs`
- **Output directory:** `frontend`
- **Required build environment variable:** `RESEARCHOS_API_URL=https://<api-host>`
- **Cache:** `runtime-config.js` must not be cached; the service worker cleans old shell versions.

### Backend

- **Hosting:** Render Web Service using [`render.yaml`](render.yaml)
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health check:** `/health`
- **Required secrets:** `DASHSCOPE_API_KEY`, `CORS_ALLOWED_ORIGINS`
- **Release metadata:** set `RESEARCHOS_RELEASE`, `RESEARCHOS_COMMIT`, and verify the frontend version value before a public release.
- **State and storage:** retain `DATABASE_URL`, `WORK_DIRECTORY`, and `STORAGE_ROOT` exactly as declared in [`render.yaml`](render.yaml).
- **Model configuration:** set the approved `LLM_*` and `EMBEDDING_*` values in the managed environment; do not place provider credentials in the frontend or Git.
- **Demo governance:** keep `DEMO_MODE=true` and `REQUIRE_HUMAN_REVIEW=true` only for the intended isolated Demo service.

### Persistent demo data

SQLite, uploaded research material, FAISS, embeddings, and Artifacts must use `WORK_DIRECTORY=/var/data` in production. Attach a Render **Persistent Disk** mounted at `/var/data` before presenting a seeded Demo; the free web-service filesystem is ephemeral and is not a valid persistent-demo configuration.

For the complete production handoff, see:

- [Final Deployment Runbook](docs/deployment/Final-Deployment-Runbook.md)
- [Release Checklist](docs/deployment/Final-Release-Checklist.md)
- [Golden Demo Environment](docs/deployment/Golden-Demo-Environment.md)

## Release checklist

- [ ] Frontend and backend release metadata match.
- [ ] `/health`, `/api/version`, and `/api/release/demo-readiness` are verified after deploy.
- [ ] `CORS_ALLOWED_ORIGINS` contains the actual frontend origin.
- [ ] Persistent Disk is mounted at `/var/data`.
- [ ] Golden Demo corpus, FAISS, Demo Workspace, Owner, and Reviewer are verified.
- [ ] Demo runs with real Mission, Evidence, Review, and Delivery states.
- [ ] No `.env`, database, vector index, uploaded file, or local Demo credential is staged for Git.

## Documentation

- [Documentation index](docs/README.md)
- [FDE Solution Overview](docs/product/FDE-Solution-Overview.md)
- [FDE Solution Showcase](docs/product/FDE-Solution-Showcase.md)
- [Architecture documentation](docs/architecture/README.md)
- [Deployment documentation](docs/deployment/README.md)
- [Public Repository Final Audit](docs/Public-Repository-Final-Audit.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## License and contribution

ResearchOS is available under the [MIT License](LICENSE). Before accepting external contributions, add the organization-approved contribution and security-reporting policies, verify secrets are excluded, and review the release checklist above.
