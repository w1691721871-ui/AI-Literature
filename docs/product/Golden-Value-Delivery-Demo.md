# Golden Value Delivery Demo

## Customer scenario

**Customer:** a building-materials R&D team.

**Business problem:** public research, lifecycle considerations, and material-selection constraints are scattered across sources. The team needs a traceable view of low-carbon concrete research trends before it decides what to investigate next. It must not treat an AI summary as an engineering recommendation.

**Research Mission:**

> Prepare a reviewed low-carbon concrete research trend delivery.

The Mission examines public research on low-carbon concrete and sustainable construction materials, including lifecycle considerations, recycled-aggregate constraints, and industrial by-product pathways. Its scope explicitly excludes a material recipe, customer-specific performance claim, or engineering decision.

## AI Employee workflow

```text
Authorized Workspace
  -> Research Mission
  -> Candidate Evidence from the Golden Corpus
  -> Human Review
  -> Research Brief draft
  -> Artifact Review
  -> Trusted Delivery
```

Each arrow is an existing product transition. No record is inserted directly into the database, and no stage is presented as complete before it has a persisted status.

## Evidence validation

The Golden Corpus contains six public, reproducibly imported papers documented in [Golden-Demo-Corpus-Guide.md](Golden-Demo-Corpus-Guide.md). The validated Value Delivery run retrieved five persisted candidate references, from three relevant sources:

- *Accelerated Design and Deployment of Low-Carbon Concrete for Data Centers* (2022)
- *Understanding the Environmental Impacts of Virgin Aggregates* (2025)
- *LCA and Energy Efficiency in Buildings* (2024)

The Reviewer validates only this limited proposition: the sources are appropriate for preparing a high-level, evidence-linked research trend draft. The review does **not** approve a mix design, safety claim, cost forecast, or customer-specific engineering decision.

## Human decisions

The demo intentionally shows two separate decisions made by the Demo Reviewer:

1. **Mission Review** — confirms that the candidate sources are relevant enough to prepare a scope-limited research draft.
2. **Artifact Review** — confirms that the generated Research Brief remains a traceable, qualified delivery record.

The AI Employee cannot take either action. If the Reviewer selects revision or rejection, the Delivery remains unavailable.

## Final delivery

The governed result is a **Human Reviewed · AI Generated Draft · NEEDS_CONFIRMATION** delivery package. It includes a traceable Evidence-reference list and a persisted Research Brief. It is useful as a research-planning handoff, not as an autonomous conclusion.

## FDE presentation script

**0:00 — Customer challenge**
“A building-materials R&D team has public research and lifecycle context spread across sources. It needs a defensible starting point for the next research discussion.”

**0:40 — Mission**
Open **Prepare a reviewed low-carbon concrete research trend delivery**. Point out the Mission goal and the explicit boundary: ResearchOS is not proposing a concrete recipe.

**1:20 — Evidence**
Show the five candidate references. Explain that they come from the indexed public Golden Corpus and remain traceable to paper and chunk records.

**2:00 — Human Review**
Open the Review decision. “The AI Employee prepared the research context; a Reviewer authorizes only a qualified draft.”

**2:45 — Research Brief**
Show the generated Research Brief and its five linked Evidence references. The artifact is a draft until the separate Artifact Review is recorded.

**3:30 — Trusted Delivery**
Show the completed Mission and the Delivery package. “The output is explicitly human-reviewed and still needs confirmation for any downstream engineering use.”

**4:15 — Trust contrast**
Optionally open the steel-slag–rubber Mission from the Trust Boundary Demo. It remains in revision because the corpus lacks direct sources. This proves the system stops rather than re-labeling adjacent research as evidence.

**5:00 — Business value**
“The team receives reusable, traceable research context and a controlled decision record—not an opaque answer.”

## Operator boundary

Run this demo only in the isolated Demo Workspace. Before a presentation, run `scripts/demo_environment_check.py` and `scripts/demo_diagnostics.py` with the Demo environment variables loaded. If corpus, review, or artifact status does not match the checklist, stop and present the Trust Boundary Demo instead of claiming a completed Delivery.
