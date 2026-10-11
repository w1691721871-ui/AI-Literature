# Unified Workspace Context

ResearchOS runs one controlled AI Employee workflow over a finite set of approved capabilities:

```text
Identity Session → Workspace → Project → Mission → Knowledge → Research Memory
                                      ↓
                         Authorized capability selection
                                      ↓
                    Observation → Evaluation → Human Review / Delivery
```

## Context boundary

`WorkspaceContextService` is the sole projection prepared before Mission work begins. It contains only:

- Session-derived identity and role;
- the authorized Workspace and member count;
- the linked project and Mission summary;
- traceable Evidence references and counts of approved knowledge assets and decisions;
- compact Research Memory summaries scoped to the Workspace.

It never contains prompts, chain-of-thought, credentials, source-document bodies, or cross-Workspace records. A mismatched Session Workspace is rejected before work is prepared.

## Research Memory

Research Memory is a reviewable product layer, not a hidden global store. It has four scopes: `WORKSPACE`, `USER`, `MISSION`, and `KNOWLEDGE`.

- Users can save their own compact, non-sensitive preferences.
- The system records a compact Mission history after controlled work.
- Every record has a source type, timestamp, Workspace ownership and an explanation endpoint.
- The owner may remove personal memory; authorized Workspace roles can remove shared memory.
- Sensitive content markers, prompts and reasoning traces are rejected before persistence.

## Capability coordination

The coordination layer is not a separate user-facing product. It selects only approved research, digital-assistance, delivery-preparation, and review-support capabilities after matching the Mission Workspace Context. The capability catalog declares permitted inputs, outputs, and required permissions without exposing model internals.

## Human control

Context injection does not widen permissions. Computer changes, Artifact release, external connector use, evidence trust and consequential decisions continue to use the existing RBAC, Policy, Diff, Verification, Rollback and Approval boundaries.
