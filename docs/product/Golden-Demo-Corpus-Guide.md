# Golden Demo Corpus Guide

## Purpose and scenario boundary

This guide defines the only repeatable public corpus for the Golden Demo. It
supports a **building-materials R&D team** evaluating evidence-backed
strategies for lower-carbon building applications.

**Golden Mission**

> Analyze sustainable construction material strategies for low-carbon building applications.

The corpus provides public research context. It is not a substitute for a
customer's engineering specification, local code requirement, material test,
or final investment decision.

## Approved public source manifest

All six records below are openly accessible arXiv preprints. Each source is
downloaded as a PDF by the existing authorized paper-library ingestion path.
“Preprint” is intentionally visible in this guide: a source candidate must
still be reviewed before it becomes verified Evidence.

| Public source | Year | Topic in the Golden Mission | Research relevance |
| --- | ---: | --- | --- |
| [Accelerated Design and Deployment of Low-Carbon Concrete for Data Centers](https://arxiv.org/abs/2204.05397) | 2022 | Low-carbon concrete | Connects concrete design and deployment choices to carbon-aware material selection. |
| [Assessing the Impact of Contact Time on Leachate Chemistry from Recycled Concrete Aggregates](https://arxiv.org/abs/2510.03344) | 2025 | Recycled materials | Adds an environmental-quality boundary for recycled concrete aggregate use. |
| [Understanding the Environmental Impacts of Virgin Aggregates: Critical Literature Review and Primary Comprehensive Life Cycle Assessments](https://arxiv.org/abs/2501.10457) | 2025 | Material lifecycle assessment | Establishes lifecycle-assessment context for aggregate choices. |
| [Valorization of Incinerator Bottom Ash for the Production of Resource-Efficient Eco-Friendly Concrete: Performance and Toxicological Characterization](https://arxiv.org/abs/2104.12497) | 2021 | Industrial by-product valorization | Relates industrial residue use to concrete performance and environmental constraints. |
| [Learning to Sieve: Prediction of Grading Curves from Images of Concrete Aggregate](https://arxiv.org/abs/2204.03333) | 2022 | Aggregate quality | Illustrates material variability that a research plan must consider when comparing aggregate strategies. |
| [LCA and Energy Efficiency in Buildings: Mapping More Than Twenty Years of Research](https://arxiv.org/abs/2409.00065) | 2024 | Building-level lifecycle assessment | Places material choices in a building lifecycle and energy-efficiency research context. |

Steel-slag utilization remains an approved *future* topic for the scenario,
but it is deliberately not indexed until an operator selects a stable,
openly licensed full-text source and records its provenance. This avoids
claiming a source that has not been verified for the Golden corpus.

## Why this corpus supports the Mission

The source set is intentionally complementary rather than a list of papers
about one material:

- **Strategy options:** low-carbon concrete and industrial by-product
  valorization provide candidate material pathways.
- **Decision criteria:** lifecycle assessment sources frame carbon and system
  boundary questions.
- **Practical constraints:** aggregate quality and recycled-aggregate
  environmental behavior prevent the Mission from presenting a material
  choice as universally safe or suitable.

The AI Employee may organize these sources into candidate Evidence. It must
not infer a universal recipe, customer-specific performance claim, or approved
innovation direction without evidence review and a human decision.

## Evidence and delivery boundary

```text
Public PDF
  -> Paper library ingestion
  -> Parser and chunks
  -> Embeddings and FAISS index
  -> Candidate Evidence
  -> Human validation
  -> Verified Evidence
  -> Reviewed Research Brief / Delivery
```

The corpus seed creates only public-paper records through the normal library
path. It does **not** insert Evidence, Insight, Review, Artifact, or a
favorable conclusion. Those records must arise through the existing governed
Mission flow.

## Repeatable preparation

Use a provisioned Demo environment with persistent storage and a real
embedding credential. Do not seed an unapproved customer Workspace.

### Deployment safety gate

The existing `Paper` model is a **deployment-level** paper library; it does
not carry a Workspace foreign key. The seed script therefore provides a hard
operational boundary instead of pretending that a paper record is
Workspace-scoped. It refuses to import unless all of these are true:

- `DEMO_MODE=true`;
- `RESEARCHOS_DEMO_CORPUS_TARGET=ResearchOS Demo Workspace` is supplied as an
  explicit operator confirmation;
- the named Demo Workspace is provisioned; and
- the database contains no other Workspace.

This means the Golden corpus may be seeded only into a dedicated Demo
deployment and persistent disk. The script does not update, delete, or
overwrite any existing paper: a repeated matching source is skipped, while a
changed upstream source stops for manual review.

1. Attach the persistent disk at `/var/data` and set
   `WORK_DIRECTORY=/var/data`.
2. Ensure Demo identity configuration and the separately authenticated
   Reviewer identity are available. Configure the seed guard:

   ```text
   DEMO_MODE=true
   RESEARCHOS_DEMO_CORPUS_TARGET=ResearchOS Demo Workspace
   ```
3. Run the normal, idempotent import route:

   ```powershell
   & .\.venv\Scripts\python.exe scripts/seed_demo_corpus.py
   ```

   In a managed deployment shell, use the environment's `python` command
   instead. The script downloads the six public PDFs, checks that each payload
   is a PDF, preserves the source hash, and delegates parsing/indexing to the
   existing paper library.
4. Run the read-only readiness check:

   ```powershell
   & .\.venv\Scripts\python.exe scripts/check_demo_corpus.py
   ```

   It must report all of the following before a live evidence walkthrough:

   ```text
   papers: >= 6
   chunks: > 0
   embeddings: > 0
   faiss: PASS
   scenario papers: 6/6
   scenario chunks: > 0
   scenario embeddings: > 0
   scenario alignment: PASS
   demo workspace: available
   workspace safety: dedicated demo deployment
   ```
5. Create the Golden Mission through the normal Mission experience. Let the
   existing workflow create candidate Evidence; use a real Reviewer for any
   approval and create a Delivery only through its normal governed route.

The seed is safe to repeat only when the downloaded content hash still matches
the persisted public source. A changed upstream PDF stops the process for
manual review rather than silently replacing an approved source.

## FDE explanation

Use this concise explanation in a demonstration:

> The employee does not turn a web search into a recommendation. It starts
> with authorized public research, preserves source provenance, keeps
> candidate Evidence separate from verified Evidence, and waits for a human
> decision before a research delivery is released.

This makes the demo about a real R&D question—material strategy under carbon,
lifecycle, and material-quality constraints—rather than an AI technology
showcase.

## Operator recovery rule

If the readiness check reports `scenario alignment: missing`, do not present
the existing index as the building-materials Golden Dataset. Run the approved
seed in the persistent Demo environment, resolve any source or embedding
failure, and repeat the read-only check. If that cannot be completed, use the
Solution Showcase only as a narrative and state that a live research record is
not available.
