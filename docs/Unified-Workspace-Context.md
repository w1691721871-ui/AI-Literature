# Unified AI Worker Context

ResearchOS runs one AI Worker product role over four existing, controlled Skills:

```text
Identity Session → Workspace → Project → Mission → Knowledge → Research Memory
                                      ↓
                         AI Team Orchestrator → approved Skills
                                      ↓
                    Observation → Evaluation → Human Review / Delivery
```

## Context boundary

`WorkspaceContextService` is the sole projection prepared before a Mission Runtime snapshot or execution. It contains only:

- Session-derived identity and role;
- the authorized Workspace and member count;
- the linked project and Mission summary;
- traceable Evidence references and counts of approved knowledge assets and decisions;
- compact Research Memory summaries scoped to the Workspace.

It never contains prompts, chain-of-thought, credentials, source-document bodies, or cross-Workspace records. A mismatched Session Workspace is rejected before Skills are planned.

## Research Memory

Research Memory is a reviewable product layer, not a hidden global store. It has four scopes: `WORKSPACE`, `USER`, `MISSION`, and `KNOWLEDGE`.

- Users can save their own compact, non-sensitive preferences.
- The runtime records a compact Mission history after controlled execution.
- Every record has a source type, timestamp, Workspace ownership and an explanation endpoint.
- The owner may remove personal memory; authorized Workspace roles can remove shared memory.
- Sensitive content markers, prompts and reasoning traces are rejected before persistence.

## Skill coordination

`AITeamOrchestrator` is an orchestration layer, not another Agent. It only selects the existing finite `Research`, `Computer`, `Delivery`, and `Review` Skills after matching the Mission Workspace Context. The capability catalog declares each Skill's permitted inputs, outputs and required permission without exposing model internals.

## Human control

Context injection does not widen permissions. Computer changes, Artifact release, external connector use, evidence trust and consequential decisions continue to use the existing RBAC, Policy, Diff, Verification, Rollback and Approval boundaries.
