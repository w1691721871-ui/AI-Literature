# Golden Demo Validation Checklist

Use this checklist immediately before an FDE or customer demonstration. It records observable product state only; it must never be used to insert, approve, or fabricate data.

## Environment and corpus

- [ ] The command is pointed at the isolated `demo/work/` SQLite database, not a development or customer database.
- [ ] `DEMO_MODE=true` is loaded for the command session.
- [ ] `scripts/demo_environment_check.py` reports **PASS** for Demo Workspace, isolation, Reviewer, corpus, chunks, embeddings, and FAISS.
- [ ] `scripts/demo_diagnostics.py` reports a dedicated Demo Workspace and `CORPUS READY`.
- [ ] The Golden Corpus reports at least 6 papers, more than 0 chunks and embeddings, and `faiss: PASS`.

## Value Delivery Mission

Open the Mission titled **Prepare a reviewed low-carbon concrete research trend delivery**.

- [ ] Mission is in the Demo Workspace and has the expected low-carbon-concrete research goal.
- [ ] Mission status is **COMPLETED** only after a persisted Review and Delivery operation.
- [ ] Candidate Evidence count is **5** for the validated run; source references are retained on the Mission.
- [ ] The source list contains public corpus material relevant to low-carbon concrete, lifecycle assessment, and aggregate-impact context.
- [ ] No screen claims a material recipe, customer-specific performance result, or automatic research conclusion.

## Human Review and Artifact

- [ ] The Mission Review is a persisted **APPROVED** decision made by the Demo Reviewer, with a scope-limiting note.
- [ ] A `RESEARCH_BRIEF` Artifact exists, has five linked Evidence references, and reached `NEEDS_REVIEW` before approval.
- [ ] The Artifact Review is a persisted **APPROVED** decision by the Demo Reviewer.
- [ ] The Artifact is presented as a traceable research draft, not as an engineering certification.

## Delivery

- [ ] Delivery was created through the normal Mission Delivery action after Mission Review approval.
- [ ] The Delivery package retains **5** Evidence references.
- [ ] Its visible label remains **Human Reviewed · AI Generated Draft · NEEDS_CONFIRMATION**.
- [ ] The Mission is **COMPLETED** and the Delivery Center shows an actual review-aware outcome.

## Trust boundary contrast

- [ ] The steel-slag–rubber Mission remains visibly separate as the Trust Boundary Demo.
- [ ] It remains `NEEDS_REVISION` because the Golden Corpus does not contain direct evidence for that narrower topic.
- [ ] Do not approve, generate a Delivery for, or describe that Mission as a completed conclusion.

## Stop conditions

Stop the Value Delivery presentation and state **BLOCKED BY DATA** if any of these are false:

- the environment is not isolated;
- the corpus, embeddings, or FAISS index is missing;
- the Reviewer account is absent;
- the Mission has no traceable Evidence;
- a Review or Artifact approval has not been persisted; or
- the Delivery does not retain its Evidence references.
