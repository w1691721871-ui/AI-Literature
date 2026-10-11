# Golden Value Delivery Demo Report

**Validation date:** 2026-10-10
**Environment:** isolated `ResearchOS Demo Workspace` only
**Result:** **PASS — VALUE DELIVERY DEMO READY**

> **Readiness-signal caveat:** the local `/api/release/demo-readiness` snapshot remains `BLOCKED` when deployment release/commit identifiers are absent. It also intentionally leaves live Review, Artifact, and Computer walkthroughs as non-verified or blocked rather than inferring them from records. That conservative release signal does not create or erase the separately validated Value Delivery records below. Do not represent the endpoint as fully green until deployment identifiers are configured and its own checks pass.

## Scenario selected

The completed-delivery scenario is **low-carbon concrete research trend analysis for sustainable construction materials**. It replaces the narrower steel-slag–rubber request for the Delivery walkthrough because the existing Golden Corpus directly supports low-carbon-concrete, lifecycle, and aggregate-impact context.

The steel-slag–rubber Mission remains available as a separate Trust Boundary Demo. It is not reused or re-labeled as a completed delivery.

## Real persisted walkthrough

| Step | Actual persisted result |
| --- | --- |
| Isolated Workspace | `ResearchOS Demo Workspace` was the only Workspace in the Demo database. |
| Corpus | 6 public papers, 131 chunks, 131 embeddings, and a passing FAISS index. |
| Mission | `Prepare a reviewed low-carbon concrete research trend delivery` created through the normal Mission endpoint. |
| Research | The normal controlled research flow entered `WAITING_REVIEW` with 5 candidate Evidence references. |
| Mission Review | Demo Reviewer recorded an `APPROVED` decision limited to preparing a qualified research draft. |
| Artifact | A real `RESEARCH_BRIEF` was generated, with 5 linked persisted Evidence references and status `NEEDS_REVIEW`. |
| Artifact Review | Demo Reviewer recorded `APPROVED`; the Artifact release status is `APPROVED`. |
| Delivery | The normal Mission Delivery action returned HTTP 200, recorded 5 Evidence references, and completed the Mission. |

**Validated Mission ID:** `08fdf36d-9d03-476d-8775-9b4b29856dab`
**Validated Research Brief ID:** `1df96dc1-fe80-490e-bd5c-b76493023926`

The IDs are a record of this isolated run, not a substitute for the status checks after a Demo reset.

## Data integrity boundary

No seed script inserted Evidence, Review, Insight, Artifact, or Delivery data. Public PDFs entered through the existing paper-library path. Candidate Evidence came from actual stored paper/chunk references. Reviews were recorded through the normal Reviewer endpoints after source and Artifact inspection. The Delivery was requested only after the persisted Mission Review approval.

The result is deliberately labeled **Human Reviewed · AI Generated Draft · NEEDS_CONFIRMATION**. It is appropriate for research planning and FDE demonstration, not for a customer engineering decision.

## Presentation effect

Mission Room language now uses customer-facing terms at the key handoffs:

- **Begin research work** instead of implementation-oriented action language.
- **Research Work Journal** for the persisted history.
- **Prepared research outcome** at the review boundary.
- **Research delivery completed** only after the real Delivery transition.
- **Research Outcome** for the visible delivery package.

These are label-only frontend changes. They do not alter the Mission, Evidence, Review, Artifact, or Delivery state machines.

## Remaining operating requirements

Before every presentation, load the Demo environment variables, validate the isolated store and corpus, and check the persisted statuses using the [Golden Demo Validation Checklist](../../product/Golden-Demo-Validation-Checklist.md). If the data is absent after a reset, recreate it through the governed workflow. Do not copy IDs, approve records automatically, or present an unreviewed draft as a Delivery.
