# ResearchOS Release Readiness — v200

## Score

**96 / 100 — local Golden Demo release gate approved.**

The customer-facing product is ready for an FDE demonstration and an enterprise solution walkthrough when the deployment gates below are completed. This score does not claim a completed public deployment.

## What is ready

- **Product narrative:** AI Research Employee for enterprise research teams.
- **Governed workflow:** Mission → Evidence → Human Review → Delivery → Workspace knowledge.
- **Golden Demo path:** customer challenge, Mission, supporting Evidence, reviewer decision, Delivery, and organizational learning.
- **Static release coherence:** `index.html`, `service-worker.js`, `release-info.json`, and Render frontend metadata are all aligned to **v200**.
- **Safety hygiene:** no tracked `.env`, database, SQLite, FAISS, embedding, PEM, or key files were found during the release scan.
- **Verification:** the repository test suite completed with **395 passing tests**; frontend syntax and `git diff --check` pass.

## Known limitations

1. The current Render definition uses a free web-service plan. Its filesystem is ephemeral; it is not suitable for a durable seeded Demo by itself.
2. A Render Persistent Disk must be provisioned and mounted at `/var/data` before hosting SQLite, PDFs, FAISS, embeddings, and Artifacts.
3. The actual production environment has to supply its secrets and release identity values. They are deliberately not stored in Git.
4. The Golden Demo must be seeded in its isolated Demo Workspace before an interview. A clean Workspace is correctly shown as empty rather than fabricating research progress.

## Deployment steps

1. Review the working tree and stage only intended source, documentation, frontend, and deployment configuration files. Do **not** use `git add .`.
2. Push the reviewed commit to GitHub.
3. In Render, deploy the API service from the intended commit and set:
   - `DASHSCOPE_API_KEY`
   - `CORS_ALLOWED_ORIGINS`
   - `RESEARCHOS_RELEASE`
   - `RESEARCHOS_COMMIT`
4. Attach a Persistent Disk mounted at `/var/data`; retain `WORK_DIRECTORY=/var/data`, `DATABASE_URL=sqlite:////var/data/research_library.db`, and `STORAGE_ROOT=/var/data/runtime_storage`.
5. Seed the isolated Demo corpus and run the Demo diagnostics before enabling the public Demo.
6. Deploy the static frontend with `RESEARCHOS_API_URL` set to the approved API origin. Confirm the browser receives static release **v200**.
7. Verify `/health`, `/api/version`, `/api/release/demo-readiness`, and `/researchos/diagnostics` without exposing credentials or internal logs.

## Demo preparation

1. Use the isolated building-materials Golden Demo Workspace.
2. Confirm the Demo Owner and Reviewer accounts are available in separate sessions.
3. Confirm corpus diagnostics report paper, chunk, embedding, and FAISS availability.
4. Start at **Home**, then show **Solution Showcase**, **Mission Room**, **Evidence**, **Human Review**, **Delivery**, and **Workspace knowledge**.
5. Never simulate approval, Evidence, or Delivery. If a prerequisite is unavailable, explain the real review or data boundary and use the documented recovery path.

## Release scope

This document covers release preparation only. It does not authorize changing the AI runtime, Mission logic, evidence rules, data model, or customer access boundaries.
