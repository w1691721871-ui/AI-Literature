# Golden Demo Scenario Alignment Report

**Assessment date:** 2026-10-09
**Scenario:** Building-materials R&D team
**Golden Mission:** “Analyze sustainable construction material strategies for low-carbon building applications.”

## What changed

- Replaced the previous AI/RAG research-paper manifest in
  `scripts/seed_demo_corpus.py` with six public, scenario-aligned
  building-materials sources.
- Preserved the existing authorized ingestion route: PDF validation, source
  hashing, parser, chunking, embeddings, and FAISS are all performed by the
  real paper-library workflow.
- Strengthened `scripts/check_demo_corpus.py` so a non-empty index cannot be
  presented as the Golden Dataset unless all six documented source filenames
  are present.
- Documented source provenance, evidence boundaries, the operator procedure,
  and the FDE explanation in
  [Golden Demo Corpus Guide](../../product/Golden-Demo-Corpus-Guide.md).

## Current local observation

The read-only check on the current local data returned:

```text
database: available
papers: 7
chunks: 180
embeddings: 180
faiss: PASS
scenario papers: 0/6
scenario alignment: missing
demo workspace: available
workspace safety: shared deployment blocked
```

This is an honest failure of **scenario alignment**, not a parser, embedding,
or FAISS failure. The current indexed papers predate this scenario manifest.
The local store is also shared, so the seed is intentionally blocked rather
than adding global papers beside other Workspaces. No seed was run during this
assessment, so no local database data was changed.

## Readiness scores

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Data authenticity | 25/25 | The manifest uses public arXiv PDFs; all six PDF URLs returned HTTP 200 during this assessment. The seed validates PDF content and source hashes. |
| Scenario consistency | 8/25 | The planned manifest matches the building-materials Mission, but the current local corpus contains 0/6 manifest sources. |
| Demonstration flow | 18/20 | Existing Mission, Evidence, Review, and Delivery steps remain governed and are documented for a five-minute walkthrough. |
| Recovery clarity | 15/15 | The readiness checker, persistent-storage rule, and explicit stop condition provide a repeatable recovery path. |
| Enterprise credibility | 15/15 | Candidate sources remain separate from verified Evidence; the seed creates no Evidence, Review, Artifact, or conclusion. |
| **Current Golden Demo readiness** | **81/100** | **Not ready for a live building-materials evidence walkthrough until the scenario seed passes.** |

## Required operator action

In a dedicated persistent Demo environment—not an arbitrary customer
Workspace—configure the safety gate and run:

```text
DEMO_MODE=true
RESEARCHOS_DEMO_CORPUS_TARGET=ResearchOS Demo Workspace
python scripts/seed_demo_corpus.py
python scripts/check_demo_corpus.py
```

The second command must report `scenario papers: 6/6` and `scenario alignment:
PASS`, plus `workspace safety: dedicated demo deployment`. Then create the
Golden Mission through the normal Mission flow, allow candidate Evidence to be
created by that flow, and use the prepared Reviewer identity for a real
decision. Do not insert Evidence, Review, or Artifact data manually to make
the demo look complete.

## Presentation boundary

Until that check passes, the Solution Showcase may be used to explain the
customer scenario and trust model, but the indexed local corpus must not be
described as a live building-materials research record.
