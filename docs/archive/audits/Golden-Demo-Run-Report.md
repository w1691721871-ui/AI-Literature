# Golden Demo Run Report

**Run date:** 2026-10-10
**Environment:** isolated `ResearchOS Demo Workspace`
**Scenario type:** real governed Mission run; no direct database write, simulated
Evidence, simulated Review, or synthetic Delivery was used.

## Demonstration goal

**Customer:** building-materials R&D team

**Business question:** assess the research trend and evidence boundary for
steel slag–rubber composite materials in low-carbon building applications,
before deciding the next experimental direction.

**Mission title:** `Analyze steel slag-rubber composite material trends for
low-carbon building applications`

**Mission boundary:** the task explicitly instructed the system not to make a
material recommendation without directly relevant, human-reviewed evidence.

## User operation path and actual states

| Step | Operator action | Actual result | Expected product presentation |
| --- | --- | --- | --- |
| 1. Owner access | Demo Owner authenticated through the normal session endpoint | PASS — authenticated | Home / Command Center can identify the authorized Demo Workspace. |
| 2. Workspace context | Owner requested Workspace Context and Mission Context | PASS — both returned HTTP 200 and their Workspace ID matched the Owner session | Mission Room can use only the current Workspace context. |
| 3. Create Mission | Owner created the stated research Mission through `POST /api/missions` | PASS — HTTP 201 | Mission Room shows the genuine goal and planning state. |
| 4. Run research work | Owner started the bounded Mission through `POST /api/missions/{id}/run` | PASS — HTTP 200 | Work Journal records real planning, retrieval, and review-boundary events. |
| 5. Candidate retrieval | Runtime retrieved references from the indexed Demo Corpus | PASS — 5 saved candidate references | Evidence area can show source candidates and the need for human validation. |
| 6. Review boundary | Mission stopped at human review | PASS — it first entered `WAITING_REVIEW` | Review area asked for a genuine human decision; no automatic approval was shown. |
| 7. Reviewer access and decision | Demo Reviewer opened the Mission and selected `NEEDS_REVISION` | PASS — HTTP 200; reason recorded | Reviewer required direct steel-slag/rubber sources before any conclusion. |
| 8. Delivery boundary | Owner requested Delivery after the revision decision | PASS — HTTP 400 | Delivery remains withheld until a real approved review exists; no release was created. |

## Persisted Mission facts

| Field | Value |
| --- | --- |
| Mission ID | `49c786c8-f6d9-478b-a5d1-ddeec71ac068` |
| Current status | `NEEDS_REVISION` |
| Current stage | Human Review |
| Work-journal events | 11 |
| Candidate source references | 5 |
| Reviewer decision | `NEEDS_REVISION` — direct scenario sources required |
| Delivery | Not created; correctly blocked before review |

The Mission timeline recorded creation, planning, requirement analysis, source
retrieval, five retrieved references, and the final human-review boundary.
This is a real persisted workflow record in the isolated Demo database.

## Evidence integrity result

The five candidate references came from the actual Demo Corpus, primarily:

- `dixit_2024_building_lca_energy_efficiency.pdf`
- `ge_2022_low_carbon_concrete.pdf`

These are valid public sources for building lifecycle and low-carbon concrete
context. They are **not** direct evidence for steel slag–rubber composite
materials.

No candidate was approved as verified Evidence. The real Demo Reviewer recorded
`NEEDS_REVISION` because the corpus lacks direct scenario sources. No insight
or Delivery was created. This is the correct trust behavior for the scenario.

## Current blocker

### High — Scenario corpus mismatch

The active Golden Corpus has six public low-carbon-building-material sources,
but no direct source on either steel slag utilization or rubber composite
materials. The runtime can retrieve related low-carbon-concrete context, yet
that does not establish evidence for the requested composite-material trend.

Therefore:

- the Reviewer should **not approve** a material recommendation from this run;
- Delivery must remain withheld for this specific business question;
- the scenario must not be presented as a completed research conclusion.

This is a data-coverage blocker, not an application failure.

### Resolved — Mission review visibility in diagnostics

The read-only Demo diagnostics now derive the `reviews` count from persisted
Mission review states within the isolated Demo Workspace. It distinguishes
`PENDING`, `NEEDS_REVISION`, `APPROVED`, and `REJECTED`; it does not create a
review record or reinterpret a candidate source as approved Evidence.

For this run, diagnostics reports one `NEEDS_REVISION` decision. The normal
Reviewer endpoint still remains the only way to make that decision, and the
Owner's Delivery request remains blocked until a later real approval.

## Page presentation effect

For this run, the product receives genuine state suitable for the enterprise
views:

- **Mission Room:** shows the customer goal, a real research-work timeline,
  five candidate sources, and **Evidence needs your decision**.
- **Evidence area:** may show the retrieved public-source candidates, but must
  retain their candidate / human-validation status.
- **Review area:** has a real Reviewer account and a recorded revision request.
- **Delivery Center:** correctly shows no released Delivery before approval.

For the FDE walkthrough, use the Mission Room's persisted status, timeline,
five candidate-source references, and Reviewer note as the proof of the real
review decision. The Mission Room now explains this revision boundary in
plain language: what the AI Employee completed, why it stopped, and what
human decision is required next.

No backend behavior was changed. The presentation remains driven by the
persisted Mission state and reviewer note.

## Golden Demo modes

### Trust Boundary Demo

Use the persisted steel-slag–rubber Mission when the goal is to demonstrate
trust. The AI Employee retrieves only related public material, records five
candidate sources, and stops at `NEEDS_REVISION` because direct evidence is
missing. The reviewer asks for direct scenario sources; Delivery stays
blocked. This is the correct mode for explaining that ResearchOS does not
turn adjacent sources into an unsupported conclusion.

### Value Delivery Demo

Use a corpus-aligned Mission such as the low-carbon concrete scenario when
the goal is to demonstrate a complete Delivery path. The operator must still
run the normal Mission flow, review the actual candidate Evidence, and approve
only evidence that supports the stated goal. A Research Brief can be prepared
only after that real approval. This mode is not pre-approved or pre-completed;
it is a governed walkthrough of the existing workflow.

## FDE interview recommendation

Use this run to demonstrate the trust boundary:

> ResearchOS found related public context, but it did not turn adjacent
> low-carbon-concrete sources into a claim about steel slag–rubber composites.
> It paused for human review and withheld Delivery.

For a completed Delivery walkthrough, use the existing corpus-aligned
low-carbon concrete scenario, or first add publicly verifiable steel-slag and
rubber-composite sources through the approved Demo Corpus process. Do not
approve this Mission or create a Delivery until direct, reviewable evidence is
available.

## Validation conclusion

| Area | Result |
| --- | --- |
| Workspace Context | PASS |
| Isolated Corpus retrieval | PASS |
| Candidate Evidence generation | PASS — 5 real references |
| Human Review boundary | PASS |
| Reviewer access and revision decision | PASS — `NEEDS_REVISION` recorded |
| Delivery governance | PASS — blocked before review |
| Scenario-specific Evidence sufficiency | BLOCKED |
| Completed Delivery | NOT CREATED BY DESIGN |

The governed workflow is functioning correctly. The requested steel
slag–rubber scenario is not ready for a conclusion or Delivery because the
current real corpus does not directly support it.
