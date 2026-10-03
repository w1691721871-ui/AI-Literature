# ResearchOS Autonomous Development Loop

ResearchOS is an evolving enterprise AI Workspace, not a project with a final
"done" state. Every commit is an audited evolution point rather than a finish
line.

## Continuous engineering loop

After each completed module and commit, the engineering owner must:

1. Re-scan the active architecture, user workflow, test suite, and product
   boundaries.
2. Identify the largest remaining gap to a trustworthy enterprise AI
   Workspace.
3. Select the highest-value improvement that fits the current safety model.
4. Implement it by extending existing contracts and adapters before creating
   new concepts.
5. Add or update focused tests, then run the relevant and full regression
   suites.
6. Commit the verified change with a concise evolution record.
7. Immediately begin the next scan.

## Non-negotiable boundaries

- Workspace identity, RBAC, approval and audit boundaries remain server-side.
- RAG, Evidence validation, FAISS and source provenance are never weakened to
  make a demo look complete.
- No prompt, chain-of-thought, credential, raw source body, or internal model
  trace is persisted in product context or user-visible timelines.
- Computer work remains controlled, approval-gated, verified and rollbackable.
- Product claims must distinguish real capability from demo-only capability.

## Permitted stopping conditions

Work may pause only for an unresolved technical blocker, a product decision
that materially changes scope, or an irreversible architectural risk. A
successful commit alone is not a stopping condition.

