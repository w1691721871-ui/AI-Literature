# Golden Demo Activation Report

**Activation date:** 2026-10-09
**Scope:** isolated Golden Demo environment only. No development database,
ordinary Workspace, Mission, Evidence, Review, Insight, or Artifact was
modified or fabricated.

## Final

## READY — Golden Demo environment is activated

The dedicated Demo store passed environment and corpus diagnostics. The live
Mission → Evidence → Review → Delivery sequence remains deliberately
unexecuted: it must be produced in the product through the normal governed
flow during the presentation or preflight walkthrough.

## Initialization

| Check | Status | Verified result |
| --- | --- | --- |
| Demo mode | PASS | `DEMO_MODE=true` |
| Bootstrap target | PASS | `demo/work/research_library.db` |
| Process database target | PASS | `DATABASE_URL` was set to the isolated Demo target before bootstrap |
| Work directory target | PASS | `WORK_DIRECTORY=demo/work` |
| Development database protection | PASS | Bootstrap uses `RESEARCHOS_DATABASE_URL_DEMO` and the dedicated Demo directory; no ordinary database was selected. |
| Embedding configuration | PASS | Embedding credential was present during bootstrap. |
| Bootstrap outcome | PASS | Demo identity and real public corpus were created through the guarded bootstrap. |

The local `demo/.env` contains only local Demo configuration and generated
Demo login passwords. It is ignored by Git and is not a code or deployment
secret source.

## Workspace and roles

| Item | Status |
| --- | --- |
| Demo Workspace | PASS |
| Demo Workspace ID | `40b7715d-1077-40b5-bd92-17306457bfc1` |
| Workspace isolation | PASS — no non-Demo Workspace was found |
| Owner | PASS — `Demo Owner` has `OWNER` membership |
| Reviewer | PASS — `Demo Reviewer` has `REVIEWER` membership |

## Corpus and retrieval foundation

| Item | Result |
| --- | --- |
| Public Demo Dataset papers | 6 / 6 scenario sources |
| Chunks | 131 |
| Embeddings | 131 |
| FAISS | PASS |
| Scenario alignment | PASS |
| Papers directory | `demo/work/papers` |
| Vector directory | `demo/work/vector_index` |

The six sources are public building-materials research PDFs. They were
ingested through the existing paper-library, chunking, embedding, and FAISS
path. They are research candidates, not automatically approved Evidence.

## Diagnostic results

```text
demo environment: PASS
demo workspace: PASS
workspace isolation: PASS
reviewer: PASS (1 reviewer membership)
demo corpus: PASS (6/6 approved sources)
demo chunks: 131
demo embeddings: 131
faiss: PASS
```

`scripts/demo_diagnostics.py` exited `0` and reported `CORPUS READY`.
Its broader release-readiness summary remains `BLOCKED` because there is no
live Mission, human Review, or Delivery yet. This is expected and truthful:
the activation process must not fabricate those business events.

## Mission Flow Ready

| Stage | State | Meaning |
| --- | --- | --- |
| Mission | READY TO RUN | Create the Golden Mission through the normal Mission experience. |
| Candidate Evidence | READY TO RUN | Existing corpus retrieval can produce only real source candidates. |
| Human Review | READY TO RUN | A separately authenticated Demo Reviewer exists and is required for the decision. |
| Delivery | READY TO RUN | Generate only after a real approved Mission output exists. |

**Not pre-created:** Mission, candidate Evidence, Reviewer decision, Insight,
and Delivery. Their absence is intentional and prevents a false completion
state.

## Operator action before the FDE interview

1. Sign in as Demo Owner and open `ResearchOS Demo Workspace`.
2. Create or open the Golden Mission:
   `Analyze sustainable concrete material research opportunities`.
3. Run the normal bounded research workflow and confirm actual candidate
   Evidence is returned from the Demo Dataset.
4. Sign in separately as Demo Reviewer and make the real review decision.
5. Show Delivery only at its actual state after the governed approval path.
6. Before the interview, rerun:

   ```powershell
   & .\.venv\Scripts\python.exe scripts/demo_environment_check.py
   & .\.venv\Scripts\python.exe scripts/demo_diagnostics.py
   ```

If either command fails, pause the live evidence walkthrough. Do not repair
the state by direct database edits, manual Evidence insertion, simulated
review, or synthetic Delivery creation.
