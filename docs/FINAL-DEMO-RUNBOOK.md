# ResearchOS Final Demo Runbook

This runbook prepares the isolated Golden Demo environment for a five-minute
enterprise demonstration. It never asks an operator to create synthetic
Evidence, approve a Review automatically, or present an unrecorded Delivery.

## 1. Release identity

The current Demo release identity is:

```text
frontend_version=v200
release=researchos-demo-v200
commit=<current Git commit>
environment=demo
```

The guarded local launcher resolves the commit from `git rev-parse HEAD` when
`RESEARCHOS_COMMIT` is empty. Render supplies its deploy SHA through
`RENDER_GIT_COMMIT`. Do not hardcode a commit in `render.yaml`; the Demo
startup guard rejects a backend/frontend version mismatch.

## 2. Prepare the isolated environment

1. Copy `demo/.env.example` to ignored `demo/.env`.
2. Set strong local values for `DEMO_OWNER_PASSWORD` and
   `DEMO_REVIEWER_PASSWORD`. Do not commit this file.
3. Set `DASHSCOPE_API_KEY` when corpus creation or embeddings are needed.
4. Confirm these values remain unchanged:

   ```text
   DEMO_MODE=true
   DATABASE_URL=sqlite:///demo/work/research_library.db
   WORK_DIRECTORY=demo/work
   RESEARCHOS_DATABASE_URL_DEMO=sqlite:///demo/work/research_library.db
   RESEARCHOS_DEMO_WORK_DIRECTORY=demo/work
   RESEARCHOS_DEMO_CORPUS_TARGET=ResearchOS Demo Workspace
   RESEARCHOS_RELEASE=researchos-demo-v200
   RESEARCHOS_FRONTEND_VERSION=v200
   RESEARCHOS_ENVIRONMENT=demo
   RESEARCHOS_RELEASE_GUARD=true
   RESEARCHOS_ALLOW_LOCAL_CORS=true
   ```

The Demo database and all associated paper, vector, and artifact files must
remain below `demo/work/`. Do not point either database setting at `work/`,
`/var/data`, or a customer environment.

## 3. Bootstrap or validate corpus

Bootstrap is the only intentionally mutating Demo setup command. It backs up
and recreates **only** the isolated Demo work directory, creates the Demo
Owner and Demo Reviewer, and imports the documented public corpus. It does
not create a Mission, Evidence, Review, or Delivery.

```powershell
.venv\Scripts\python.exe scripts\bootstrap_golden_demo.py --apply
.venv\Scripts\python.exe scripts\demo_environment_check.py
.venv\Scripts\python.exe scripts\demo_diagnostics.py
```

Expected preflight signals: Demo mode, Workspace isolation, Owner/Reviewer,
papers, chunks, embeddings, and FAISS all pass. A missing corpus is a reason
to stop; it is never replaced by placeholder research content.

## 4. Start the Demo stack

Start the API using the guarded Demo entry point. It reads only ignored
`demo/.env`, refuses non-Demo persistence targets, and then starts the normal
FastAPI application:

```powershell
.venv\Scripts\python.exe scripts\run_demo_server.py --host 127.0.0.1 --port 8000
```

In a second terminal, generate the local runtime configuration and serve the
frontend. Use the local API URL for a laptop-only demonstration:

```powershell
$env:RESEARCHOS_API_URL = "http://127.0.0.1:8000"
node scripts\build-runtime-config.mjs
.venv\Scripts\python.exe -m http.server 5173 --bind 127.0.0.1 --directory frontend
```

Run the read-only release gate after both services are listening:

```powershell
.venv\Scripts\python.exe scripts\demo_release_check.py
```

It must print `DEMO RELEASE CHECK: PASS`. A failure means the services are
not serving the same isolated Demo state; do not begin the presentation.

## 5. Demo accounts

| Role | Use in the demonstration | Credential source |
| --- | --- | --- |
| Demo Owner | Open the Workspace, explain the Mission and Evidence | `demo/.env` |
| Demo Reviewer | Record or show the real Human Review decision | `demo/.env`, separate browser profile |

Keep the passwords off screen. Use two browser profiles or devices so the
role boundary is visible without exposing session details.

## 6. Five-minute presentation

1. **0:00 — Home:** Position ResearchOS as an AI Research Employee for an
   enterprise building-materials team.
2. **0:30 — Workspace:** State the customer question and open the prepared
   Mission. Do not create a duplicate Mission unless the operator intends to
   demonstrate the real creation flow.
3. **1:20 — Mission:** Show current focus and recorded work journal.
4. **2:00 — Evidence:** Explain source quality and why candidate Evidence is
   not a conclusion.
5. **3:00 — Human Review:** Switch to Demo Reviewer. Show the persisted
   decision or request for revision; never approve merely for presentation.
6. **4:00 — Delivery:** Open only a persisted, reviewable Research Brief or
   Artifact and connect it to its Evidence.
7. **4:40 — Organizational learning:** Return to Workspace or Solution
   Showcase and close on reusable, governed research knowledge.

## 7. Troubleshooting

| Symptom | Meaning | Safe response |
| --- | --- | --- |
| API will not start | Release identity or Demo environment does not pass the guard | Compare `demo/.env`, `frontend/release-info.json`, and `git rev-parse HEAD`. |
| `DEMO RELEASE CHECK: FAIL` | API, frontend, or local Demo database do not align | Read the failing row; do not reseed a shared or development database. |
| Corpus/FAISS failure | The public corpus is incomplete or unavailable | Re-run bootstrap only after confirming the isolated Demo target. |
| No review action | Reviewer is not authenticated or no real review is recorded | Use the Reviewer profile or show the existing waiting/revision state truthfully. |
| No Delivery | A Review has not reached the state required by the product | Present the trust boundary; do not manufacture a Delivery. |

## 8. Managed deployment note

For Render, keep SQLite, PDFs, FAISS, embeddings, and artifacts on a single
Persistent Disk. Configure the same public release identity and run the
release gate against the deployed API/frontend URLs before presenting.
