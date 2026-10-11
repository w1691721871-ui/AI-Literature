# Golden Demo Environment

ResearchOS uses three intentionally separate persistence contexts. The Golden
Demo is not a flag on a development or customer database.

| Environment | Purpose | Database and files | Who may use it |
| --- | --- | --- | --- |
| Development | Feature work and automated tests | Existing local `work/` target | Developers only |
| Golden Demo | Repeatable FDE walkthrough | `demo/work/research_library.db`, PDFs, FAISS, and artifacts under `demo/work/` | Demo Owner and Demo Reviewer |
| Production | Authorized customer research | Deployment-managed persistent disk / configured database | Authorized customer Workspace members |

## Isolation rule

Demo utilities read **only** `RESEARCHOS_DATABASE_URL_DEMO`; they ignore the
ordinary `DATABASE_URL` until they explicitly set the process to the Demo
target. The target must be a persistent SQLite file inside this repository's
`demo/` directory. A Demo command rejects any target outside that directory.

The current paper library is deployment-level, not Workspace-scoped. For that
reason the corpus seed, reset, and bootstrap commands additionally require a
database containing only `ResearchOS Demo Workspace`. A shared database is
blocked rather than treated as isolated.

## Demo data labels

- **Demo Workspace:** `ResearchOS Demo Workspace`
- **Demo users:** `Demo Owner`, `Demo Reviewer`
- **Demo corpus:** six public building-materials papers defined in
  [Golden Demo Corpus Guide](../product/Golden-Demo-Corpus-Guide.md)
- **Golden Mission:** `Analyze sustainable concrete material research opportunities`

Every corpus source is public research material. It is a candidate source and
does not become verified Evidence, a conclusion, or an approved Delivery until
the normal Mission and Human Review workflow records those events.

## Configure

Copy the values in [`demo/.env.example`](../../demo/.env.example) into a local
secret store or deployment environment. Do not place real passwords or API
keys in the repository.

Required variables:

```text
DEMO_MODE=true
RESEARCHOS_DATABASE_URL_DEMO=sqlite:///demo/work/research_library.db
RESEARCHOS_DEMO_WORK_DIRECTORY=demo/work
RESEARCHOS_DEMO_CORPUS_TARGET=ResearchOS Demo Workspace
DEMO_OWNER_PASSWORD=<secret>
DEMO_REVIEWER_PASSWORD=<secret>
DASHSCOPE_API_KEY=<secret>
```

## Verify before any write

```powershell
python scripts/bootstrap_golden_demo.py
python scripts/demo_environment_check.py
```

Both commands are read-only dry runs by default. The first command states its
target; the second reports Demo mode, database path, Workspace isolation,
Reviewer membership, corpus coverage, chunks, embeddings, and FAISS.

## Bootstrap the Demo database

Stop any API process that might have the Demo SQLite file open, then run:

```powershell
python scripts/bootstrap_golden_demo.py --apply
python scripts/demo_environment_check.py
python scripts/demo_diagnostics.py
```

Bootstrap creates a timestamped backup under `demo/backups/` before replacing
an existing Demo work directory. It creates the Demo Owner and Demo Reviewer
through the existing identity flow, then imports the six public PDFs through
the existing parser, embedding, and FAISS path.

It does not create a Mission, candidate Evidence, reviewer decision, Insight,
or Delivery. Once diagnostics pass, create the Golden Mission in the product,
run the existing controlled research flow, and use the actual Reviewer account
for the approval decision.

## Acceptance criteria

`scripts/demo_environment_check.py` must exit `0` and show:

```text
demo mode: PASS
demo workspace: PASS
workspace isolation: PASS
reviewer: PASS
demo corpus: PASS (6/6 approved sources)
demo chunks: > 0
demo embeddings: > 0
faiss: PASS
```

Then `scripts/demo_diagnostics.py` must report `CORPUS READY`. The remaining
Mission, Review, and Delivery checks are expected to become verified only as a
real walkthrough proceeds.
