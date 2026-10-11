# Golden Demo Operator Checklist

This is the on-site operating checklist for the ResearchOS Golden Demo. It
does not create research results, approve evidence, or bypass a human review.
Use it only with the dedicated `ResearchOS Demo Workspace` and the public
**Demo Dataset**.

## Scenario

- **Customer context:** building-materials R&D team
- **Mission:** `Analyze sustainable concrete material research opportunities`
- **Research goal:** examine opportunities for recycled materials in
  low-carbon concrete applications using public, traceable sources.
- **Trust boundary:** AI prepares research work; a Reviewer validates the
  evidence and delivery decision.

## 30 minutes before the interview

### 1. Confirm the isolated environment

- [ ] Use the Demo deployment or local Demo environment, never the
  development or customer database.
- [ ] Confirm `DEMO_MODE=true`.
- [ ] Confirm `RESEARCHOS_DATABASE_URL_DEMO` targets
  `demo/work/research_library.db` (or the dedicated deployment equivalent).
- [ ] Confirm `RESEARCHOS_DEMO_WORK_DIRECTORY` targets the matching dedicated
  Demo storage.
- [ ] Confirm `RESEARCHOS_DEMO_CORPUS_TARGET=ResearchOS Demo Workspace`.

Run the non-mutating check:

```powershell
& .\.venv\Scripts\python.exe scripts/demo_environment_check.py
```

**Pass condition:** exit code `0`; `demo workspace`, `workspace isolation`,
`reviewer`, `demo corpus`, and `faiss` all show `PASS`.

### 2. Confirm real corpus readiness

```powershell
& .\.venv\Scripts\python.exe scripts/demo_diagnostics.py
```

- [ ] The command exits `0`.
- [ ] It identifies the dedicated Demo database, not a development path.
- [ ] The corpus shows six scenario sources, chunks and embeddings above zero,
  and `faiss: PASS`.
- [ ] Keep the command output available as operational evidence; it is not a
  substitute for an in-product human review.

If the isolated database has not been provisioned, bootstrap it only before
the interview window and only with valid Demo credentials and an embedding
credential:

```powershell
& .\.venv\Scripts\python.exe scripts/bootstrap_golden_demo.py --apply
& .\.venv\Scripts\python.exe scripts/demo_environment_check.py
& .\.venv\Scripts\python.exe scripts/demo_diagnostics.py
```

Bootstrap backs up the existing Demo store before recreating it. It creates
the Demo identities and imports public PDFs, but it intentionally does not
fabricate a Mission, Evidence, Review, Insight, or Delivery.

### 3. Confirm the people and governed workflow

- [ ] Sign in as **Demo Owner** and confirm the visible Demo Workspace label.
- [ ] Confirm a separately authenticated **Demo Reviewer** account is ready.
- [ ] Create or open the Golden Mission through the normal product flow.
- [ ] Verify that current Mission status is genuine; do not narrate a phase
  that has not occurred.
- [ ] Retrieve source candidates through the Mission, then show candidate
  evidence as candidates rather than verified conclusions.
- [ ] Keep the Reviewer decision pending until the Human Review portion of
  the presentation.
- [ ] Confirm the current Delivery status. Only claim delivery after a real
  approval and normal delivery generation.

### 4. Record recovery information

- [ ] Record the latest `demo/backups/` timestamp if a reset or bootstrap was
  performed.
- [ ] Confirm API service, browser session, and persistent Demo storage are
  available.
- [ ] Keep the Solution Showcase open in a second tab as a narrative fallback,
  not as a substitute for live data.

## Five minutes before the interview

- [ ] Re-run `& .\.venv\Scripts\python.exe scripts/demo_environment_check.py`; do not reset or seed
  during the final five minutes.
- [ ] Re-run `& .\.venv\Scripts\python.exe scripts/demo_diagnostics.py`.
- [ ] Open the Owner session, Mission Room, Evidence area, Review area,
  Delivery Center, and Solution Showcase in known tabs.
- [ ] Confirm the browser has the current application version and no stale
  service-worker cache prompt.
- [ ] Confirm both Owner and Reviewer credentials work without exposing the
  credentials in slides or screen sharing.
- [ ] Confirm no other Workspace exists in the Demo database. A shared store
  invalidates the corpus-isolation guarantee.

## Live Golden User Flow

| Step | Operator input / action | Required real state | Expected product view |
| --- | --- | --- | --- |
| 1. Owner sign-in | Sign in as Demo Owner | Demo Owner has an Owner membership in `ResearchOS Demo Workspace` | Home / AI Employee Command Center identifies the Demo environment and a real Workspace. |
| 2. Frame the work | Open the Golden Mission or create it with the stated title and goal | Mission belongs to the Demo Workspace | Mission Room shows the actual goal, current focus, and next action. |
| 3. Research work | Start or continue the normal bounded research action | Seeded corpus passes diagnostics | Mission Room and Evidence area show only actual source candidates returned for the Mission. |
| 4. Evidence boundary | Open the candidate evidence list | Candidate sources exist; none is presented as automatically verified | Evidence view explains source quality and the need for human validation. |
| 5. Reviewer sign-in | Open a separate Reviewer session and select the review item | Reviewer has a `REVIEWER` membership and a real item awaits review | Review view shows the AI-prepared work, supporting evidence, and an actual decision control. |
| 6. Human decision | Approve or request revision through the normal review control | The reviewer is authorized; the decision is recorded | Mission state advances only according to the real decision. |
| 7. Delivery | Open Delivery Center after approval | An actual approved item and generated delivery exist | Delivery shows its real status and evidence support. If pending, present it as pending. |
| 8. Executive close | Open Solution Showcase | No extra data requirement | Customer challenge, trust governance, business value, and the governed delivery workflow are visible. |

## Exception handling during the demonstration

| Condition | Truthful operator response | Do not do |
| --- | --- | --- |
| Corpus missing or diagnostics fail | Stop the live evidence walkthrough. State that the Demo Dataset is not ready, show the readiness boundary, and restore/reseed before a later demo. | Do not claim source retrieval, evidence, or an insight occurred. |
| Embedding/import failure | Stop at the corpus boundary and preserve the bootstrap/seed output for investigation. The seeded PDFs may not be presented as searchable evidence until diagnostics pass. | Do not manually insert embeddings, edit a database, or substitute invented results. |
| Reviewer is unavailable | Show the genuine `Waiting for review` state and explain that the AI cannot self-approve. Resume delivery only when an authorized Reviewer is available. | Do not use an Owner account to imitate a Reviewer or change status directly. |
| Evidence is insufficient | Explain that ResearchOS pauses before producing an unsupported conclusion. Continue bounded research if the product offers it, or request a human decision. | Do not describe a trend, opportunity, or delivery as supported. |
| Backend/browser problem | Pause the live workflow, capture the visible user-facing reason, then continue with Solution Showcase only as the product narrative. Re-run preflight after recovery. | Do not reveal credentials, internal logs, prompts, or hidden system data. |

## Non-negotiable demo rules

- Do not run seed, bootstrap, or reset commands against a shared or customer
  deployment.
- Do not use direct database edits to prepare a review or delivery state.
- Do not label candidate sources as approved Evidence.
- Do not present a Delivery as approved unless the normal Reviewer action and
  delivery flow actually occurred.
- Treat an incomplete state as a trust demonstration: ResearchOS stops rather
  than creates unsupported research output.
