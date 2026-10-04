# ResearchOS Enterprise Architecture

ResearchOS is an evidence-driven AI workspace. It keeps model planning separate from controlled execution and human approval.

```text
User session
  -> Identity / Workspace / RBAC
  -> Mission Contract
  -> Research Orchestrator
  -> Unified Mission Runtime
  -> Research | Computer | Delivery | Review skills
  -> Evidence / Approval / Artifact / Audit
```

The Research skill reuses the existing RAG, FAISS, embedding, evidence validation and conflict detection chain. The Computer skill is controlled execution: proposed source changes require a diff, approval, verification and rollback capability. The Delivery skill creates reviewable artifacts. The Review skill does not approve itself.

Only user-readable execution summaries, evidence references, approval decisions and audit events are persisted. Prompts, chain-of-thought, secrets and model-internal reasoning are not persisted.

## Single execution gateway

Enterprise user execution has one gateway: `POST /api/missions/{id}/run` and
`POST /api/runtime/missions/{id}/execute` both invoke `AIWorkerRuntime`. The
runtime alone selects the registered Research, Computer, Delivery and Review
Skills. Skills are adapters over existing services and never create a second
runtime. Historical `/researchos/*` and `/api/llm-runtime/*` endpoints are
administrator compatibility surfaces, not normal user execution paths.
