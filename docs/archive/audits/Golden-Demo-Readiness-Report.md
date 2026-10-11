# Golden Demo Readiness Report

**Assessment date:** 2026-10-09
**Assessment scope:** Demo isolation, bootstrap safety, public corpus,
governed five-minute walkthrough, and operator recovery.
**Assessment method:** static review of the Demo utilities and read-only
preflight against the configured isolated Demo target. No Mission, Evidence,
Review, Insight, or Delivery was fabricated for this assessment.

### Read-only preflight result

The project virtual environment was used for the actual preflight:

```text
bootstrap_golden_demo.py (dry run): exit 0
demo_environment_check.py: exit 2 — missing database
demo_diagnostics.py: exit 2 — DEMO ENVIRONMENT NOT INITIALIZED
```

The system-wide `python` command does not currently have SQLAlchemy installed
and cannot run the Demo utilities. Operators must use
`& .\.venv\Scripts\python.exe` locally (or the dependency-complete Python
environment in a managed deployment).

## Verdict

## NOT READY — Demo environment initialization is blocked by missing Demo data

The Golden Demo tooling is designed to create and validate an isolated,
repeatable environment. The current configured Demo database
`demo/work/research_library.db` does not exist, so no current live proof is
available for the Demo Workspace, Owner/Reviewer memberships, corpus chunks,
embeddings, FAISS index, Mission, Review, or Delivery.

This is a deployment-data blocker, not evidence that the product should claim
failure. It must be resolved before an FDE interview walkthrough.

## Current readiness matrix

| Area | Status | Evidence / reason |
| --- | --- | --- |
| Demo database isolation design | PASS | Demo utilities ignore normal `DATABASE_URL`, require `RESEARCHOS_DATABASE_URL_DEMO`, and reject targets outside `demo/`. |
| Development database protection | PASS | Demo bootstrap selects the isolated target before importing application services; the verified dry run made no changes. |
| Bootstrap repeatability | PASS WITH OPERATOR GATE | `bootstrap_golden_demo.py --apply` backs up only the existing Demo work directory, recreates Demo identities, imports the public corpus through normal ingestion, then invokes the environment check. It fails rather than continuing on an identity, corpus, or readiness error. |
| Demo data labeling | PASS | The fixed names are `ResearchOS Demo Workspace`, `Demo Owner`, `Demo Reviewer`, and public **Demo Dataset** sources. |
| Operator Python environment | PASS WITH REQUIRED INVOCATION | The repository `.venv` imports the Demo utilities; the system Python lacks SQLAlchemy and is not valid for the preflight. |
| Current isolated Demo database | BLOCKED | The configured `demo/work/research_library.db` is missing. |
| Dedicated Demo Workspace | NOT VERIFIED | It cannot exist in the missing Demo database. |
| Owner / Reviewer availability | NOT VERIFIED | Bootstrap has not populated the isolated Demo database. |
| Golden Corpus persistence | BLOCKED | The six prescribed public PDFs have not been imported into the isolated Demo target. |
| Chunks / embeddings / FAISS | BLOCKED | No isolated corpus exists to index or inspect. |
| Golden Mission | NOT VERIFIED | Bootstrap deliberately does not manufacture a Mission. It must be created through the product. |
| Candidate evidence | NOT VERIFIED | Candidate evidence requires a real Mission retrieval result. |
| Human review | NOT VERIFIED | A Reviewer decision must be performed through the normal product flow. |
| Delivery | NOT VERIFIED | Delivery is valid only after a real approval and normal delivery generation. |

## Bootstrap review

### Repeatability

`scripts/bootstrap_golden_demo.py` is repeatable for the dedicated target:

1. A dry run validates required mode, credentials, target naming, and the
   exact Demo database path without writing data.
2. `--apply` creates a timestamped backup under `demo/backups/` before it
   removes the existing Demo work directory.
3. It provisions the named Demo Owner, Demo Reviewer, and Demo Workspace
   using the existing identity path.
4. It invokes the idempotent corpus importer and then the read-only
   environment check.
5. A failed prerequisite returns a blocked outcome rather than a partial
   success claim.

The bootstrap is intentionally not a complete scripted demo. It does **not**
create a Mission, approve Evidence, create an Insight, or generate an
Artifact. Those must be generated through the governed user flow.

### Development-data safety

The Demo environment helper reads only
`RESEARCHOS_DATABASE_URL_DEMO`; it does not reuse ordinary `DATABASE_URL`.
It accepts only persistent SQLite targets located below `demo/`. The corpus
importer additionally refuses to run if the target contains any Workspace
other than `ResearchOS Demo Workspace`, because the existing paper library is
deployment-level.

### Recoverability

Before destructive Demo reinitialization, the bootstrap copies the existing
Demo work directory to a UTC-timestamped `demo/backups/` location. This is a
Demo-only recovery mechanism. It is not permission to reset a shared,
development, or customer store.

## Dataset review

The Golden Corpus is a fixed set of **six** public arXiv PDFs, all within the
requested six-to-ten source range. It is reproducible through
`scripts/seed_demo_corpus.py` and stored through the normal paper-library,
chunking, embedding, and FAISS paths in the dedicated Demo work directory.

| Public source | Focus relevant to the Golden Mission |
| --- | --- |
| *Accelerated Design and Deployment of Low-Carbon Concrete for Data Centers* (arXiv:2204.05397) | Low-carbon concrete deployment context. |
| *Assessing the Impact of Contact Time on Leachate Chemistry from Recycled Concrete Aggregates* (arXiv:2510.03344) | Recycled concrete aggregate considerations. |
| *Understanding the Environmental Impacts of Virgin Aggregates* (arXiv:2501.10457) | Lifecycle assessment and aggregate trade-offs. |
| *Valorization of Incinerator Bottom Ash for Resource-Efficient Eco-Friendly Concrete* (arXiv:2104.12497) | Industrial by-product reuse in concrete. |
| *Learning to Sieve: Prediction of Grading Curves from Images of Concrete Aggregate* (arXiv:2204.03333) | Aggregate-quality context. |
| *LCA and Energy Efficiency in Buildings* (arXiv:2409.00065) | Building lifecycle assessment context. |

These sources are not pre-approved Evidence, are not fictional papers, and do
not encode a prewritten research conclusion. The importer validates that each
download is a PDF, records a content hash, skips an unchanged source on repeat
execution, and blocks replacement if a public source changes until a person
reviews it.

**Data acceptance gate after import:** all six named sources exist; chunks and
embeddings are above zero; every scenario chunk has an embedding; FAISS and
its mapping pass; and no non-Demo Workspace exists in the database.

## Golden user-flow validation plan

The following steps become a PASS only when conducted in the running product
against the isolated Demo environment.

| Flow step | Input | Required real state | Expected page / state | Current result |
| --- | --- | --- | --- | --- |
| Owner access | Demo Owner signs in | Owner membership in Demo Workspace | Home / AI Employee Command Center | NOT VERIFIED |
| Mission | Open or create `Analyze sustainable concrete material research opportunities` | Mission belongs to Demo Workspace | Mission Room shows real goal, focus, and next action | NOT VERIFIED |
| Retrieval | Run the bounded Mission research action | Diagnostics corpus gate passes | Evidence area shows actual candidate sources | NOT VERIFIED |
| Evidence boundary | Open candidates | Candidate material exists | Source quality and required human validation are visible | NOT VERIFIED |
| Reviewer access | Sign in separately as Demo Reviewer | Reviewer membership and pending review exist | Review controls are available | NOT VERIFIED |
| Review | Approve or request revision | Authorized reviewer records a real decision | Mission state changes only according to the action | NOT VERIFIED |
| Delivery | Open Delivery after approval | Actual approved result and generated delivery exist | Delivery Center reports its genuine status | NOT VERIFIED |
| Executive close | Open Solution Showcase | No additional source assertion | Customer challenge, governance, value, and workflow are visible | NOT VERIFIED |

## Failure-safety review

| Failure condition | Required product / operator behavior | Validation result |
| --- | --- | --- |
| Corpus missing | Diagnostics blocks readiness and the operator must not demonstrate live evidence retrieval. | PASS BY DESIGN; currently active blocker. |
| PDF import or embedding failure | Seed/bootstrap exits nonzero; diagnostics cannot claim corpus readiness. Preserve the error and restore/reseed the dedicated Demo target. | PASS BY DESIGN; live execution NOT VERIFIED. |
| Reviewer absent | Environment check marks reviewer blocked; an approval cannot be truthfully shown. Present `Waiting for review` rather than bypassing the control. | PASS BY DESIGN; live execution NOT VERIFIED. |
| Evidence insufficient | Mission must stop at the evidence boundary and request further work or human direction; it must not create an unsupported conclusion. | PASS BY GOVERNANCE DESIGN; live execution NOT VERIFIED. |
| Delivery not approved | Present the real pending status. Do not claim an approved or delivered report. | PASS BY GOVERNANCE DESIGN; live execution NOT VERIFIED. |

## Release gate: actions required before the interview

1. Configure the dedicated Demo variables and required credentials in the
   Demo deployment or local Demo shell. Keep development and customer
   `DATABASE_URL` values out of this process.
2. Run `& .\.venv\Scripts\python.exe scripts/bootstrap_golden_demo.py --apply` against the isolated
   Demo target. Confirm it completes without a blocked message.
3. Run `& .\.venv\Scripts\python.exe scripts/demo_environment_check.py`; require exit `0`.
4. Run `& .\.venv\Scripts\python.exe scripts/demo_diagnostics.py`; require exit `0`, six scenario
   sources, nonzero chunks and embeddings, and FAISS pass.
5. Create the Golden Mission through the UI, use actual retrieval, and retain
   the candidate Evidence state.
6. Verify the Demo Reviewer login in a separate session; perform or retain a
   real review decision according to the intended presentation segment.
7. Verify the Delivery shown in the UI is its real state. Run the normal
   delivery flow only after the real approval.
8. Execute the 30-minute and five-minute checks in
   [Golden Demo Operator Checklist](../../product/Golden-Demo-Operator-Checklist.md).

## Risk assessment and interview recommendation

| Risk | Level | Recommendation |
| --- | --- | --- |
| Missing isolated Demo database | High | Do not schedule the live evidence walkthrough until bootstrap, corpus indexing, and diagnostics complete. |
| External public-PDF or embedding availability | High | Seed and validate at least 30 minutes before the interview; never depend on an import occurring live. |
| Missing Reviewer session | High | Validate a separate Reviewer login before the interview. Show waiting-for-review if it becomes unavailable. |
| Live retrieval produces insufficient evidence | Medium | Treat it as a trust boundary and use the product's real pause/review state; do not invent conclusions. |
| Browser/session/cache issue | Medium | Use the five-minute preflight, current application version, and prepared tabs. |

**Interview recommendation:** The product narrative may be presented now, but
the full five-minute governed Golden Demo must be treated as **not ready**
until the isolated database, public corpus, Reviewer, Mission, and actual
review/delivery path pass the release gate above.
