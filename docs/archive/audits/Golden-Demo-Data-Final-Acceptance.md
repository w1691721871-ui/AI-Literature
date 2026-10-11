# Golden Demo Data Final Acceptance

**Scope:** Golden Demo data, scripts, and operator documentation only.
**Golden Mission:** “Analyze sustainable construction material strategies for low-carbon building applications.”

## Verdict

**Do not run the corpus seed in the current local data store.** The current
read-only check reports a healthy historical index but none of the approved
building-materials sources. The seed is now safe to run only in a dedicated
Demo deployment after its safety gate is configured.

## Seed-script audit

| Check | Result | Evidence |
| --- | --- | --- |
| Idempotency | PASS | Existing filenames are read before insertion. A matching persisted PDF hash is skipped. |
| Duplicate prevention | PASS | Repeat runs retain one record per manifest filename; a matching source is skipped rather than inserted again. |
| Overwrite prevention | PASS | If an upstream PDF hash changes, the script stops for manual review. It never replaces the stored paper. |
| Customer-Workspace protection | PASS, with an operational boundary | The script requires `DEMO_MODE=true`, explicit target confirmation, a provisioned Demo Workspace, and a database containing no other Workspace. Otherwise it refuses to write. |
| True per-Workspace paper binding | NOT AVAILABLE IN CURRENT SCHEMA | `Paper` has no `workspace_id`; the library is deployment-level. The script deliberately rejects shared deployments instead of claiming false Workspace isolation. |
| Evidence / Insight / Artifact seeding | PASS | The script calls only the existing paper-library import. It does not create Evidence, Insight, Review, Artifact, or approval records. |

## Public-source relevance review

| Source | Abstract-level fit with the Mission | Acceptance |
| --- | --- | --- |
| [Low-Carbon Concrete for Data Centers](https://arxiv.org/abs/2204.05397) | Reports lower-carbon concrete formulation work subject to engineering-performance requirements and lifecycle data. | Direct strategy source. |
| [Recycled Concrete Aggregate Leachate](https://arxiv.org/abs/2510.03344) | Examines pH, alkalinity, and leaching considerations for recycled concrete aggregate. | Constraint and environmental-risk source. |
| [Virgin Aggregate Life Cycle Assessments](https://arxiv.org/abs/2501.10457) | Discusses aggregate environmental footprints and the importance of consistent LCA system boundaries. | Decision-criterion source. |
| [Incinerator Bottom Ash Eco-Friendly Concrete](https://arxiv.org/abs/2104.12497) | Studies bottom ash and recycled demolition aggregate in concrete, including performance and leaching behavior. | Industrial-by-product strategy source. |
| [Concrete Aggregate Grading](https://arxiv.org/abs/2204.03333) | Addresses aggregate grading, a material-quality input relevant to comparing construction-material strategies. | Material-quality context source. |
| [LCA and Energy Efficiency in Buildings](https://arxiv.org/abs/2409.00065) | Maps building LCA and energy-efficiency research over time. | Building-level context source. |

The six sources are real public research material, but several are arXiv
preprints. They are suitable as **candidate** research sources—not as an
automatic engineering recommendation or approval.

### Source ingestion preflight

Each of the six fixed HTTPS source URLs returned a valid PDF and was parsed in
memory with the existing PDF extractor during this audit. Extracted text
lengths ranged from 43,222 to 120,058 characters. This validates public
access and parser compatibility without saving a paper, generating an
embedding, or mutating the database.

## Real-data boundary

The approved seed causes the established pipeline to run:

```text
Verified public PDF -> parser -> persisted chunks -> embeddings -> FAISS
```

The readiness check now validates that all six source filenames are present,
that their own chunks have embeddings, and that the global FAISS index is
readable. It does not fabricate or infer any of the following:

- Evidence;
- Research Insight;
- Reviewer decision;
- Artifact or Delivery;
- Mission completion.

Candidate Evidence becomes quoteable only after a real Mission retrieves the
persisted source content and the normal governed Evidence flow produces a
candidate. Verified Evidence requires human review. A successful corpus seed
alone is not Evidence validation.

## Current read-only local result

```text
papers: 7
chunks: 180
embeddings: 180
faiss: PASS
scenario papers: 0/6
scenario alignment: missing
```

The existing index is technically usable but is not the approved
building-materials Golden corpus. No seed was run during this audit, so no
database data was added or changed.

## Required seed command and acceptance standard

Run only in a dedicated Demo deployment with a persistent disk:

```text
DEMO_MODE=true
RESEARCHOS_DEMO_CORPUS_TARGET=ResearchOS Demo Workspace
python scripts/seed_demo_corpus.py
python scripts/check_demo_corpus.py
```

Accept the corpus only if the second command reports:

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

Then, and only then, create a Mission through the normal product flow, show
real candidate Evidence, use a separately authenticated Reviewer for a real
decision, and show a Delivery only if the governed Artifact path actually
created one.

## FDE presentation risks

| Risk | Status | Operator response |
| --- | --- | --- |
| Old AI/RAG corpus remains indexed | Present locally | Do not describe it as a building-materials research record; seed the approved corpus in the dedicated Demo deployment. |
| Shared database contains customer Workspaces | Present locally; prevented by script | The seed stops. Provision a dedicated Demo database/disk; do not override the guard. |
| Seed has not produced embedded chunks | Not yet verified | Run the read-only check; resolve parsing, embedding, or FAISS failures before the interview. |
| Candidate Evidence has not been produced | Expected until Mission runs | Explain the Evidence boundary; never fabricate a cited result. |
| Reviewer is unavailable | Expected if only Demo Member is open | Use the prepared Reviewer session; do not bypass role separation. |
| Delivery does not exist | Expected until approved Artifact path runs | Show the governed lifecycle, not a claimed final report. |

## FDE first-impression conclusion

The prepared narrative correctly presents ResearchOS as an **AI Research
Employee**: it works from a Mission, preserves source provenance, pauses for
human review, and creates a reusable Delivery only through a real governed
path. It is not presented as a generic RAG search demo. That claim remains
credible only when the live scenario corpus and review session satisfy the
acceptance standard above.
