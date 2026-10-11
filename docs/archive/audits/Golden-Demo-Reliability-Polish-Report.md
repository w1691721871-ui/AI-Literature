# Golden Demo Reliability Polish Report

**Date:** 2026-10-10
**Scope:** diagnostics, Demo documentation, and Mission Room presentation only.

## Changes made

### Read-only review diagnostics

`scripts/demo_diagnostics.py` now counts persisted Mission review states in
the isolated Demo Workspace instead of relying only on the legacy approval
queue. The report exposes the following real states:

- `PENDING`
- `NEEDS_REVISION`
- `APPROVED`
- `REJECTED`

It is Workspace-scoped and read-only. It does not write a review, approve
Evidence, generate an Artifact, or alter a Mission.

### Mission Room revision boundary

When a real Mission status is `NEEDS_REVISION`, the Mission Room now says
**Evidence needs your decision** and shows:

1. what the AI Employee completed;
2. why work stopped, using the persisted reviewer note when available; and
3. the human decision needed to prepare a revised draft.

The existing revision action remains human initiated. The interface does not
approve evidence or create a Delivery automatically.

### Two Golden Demo modes

- **Trust Boundary Demo:** demonstrates a safe stop when the scenario lacks
  direct evidence. The current steel-slag–rubber Mission is the reference
  case.
- **Value Delivery Demo:** demonstrates the ordinary governed delivery path
  using a corpus-aligned Mission, real candidate Evidence, real review, and a
  later human approval.

## Verification standard

The isolated Demo environment should report the actual Mission review count,
including `NEEDS_REVISION`. A completed Delivery must still be absent until
the normal review workflow records a real approval.

## Known constraint

The current Golden Corpus does not contain direct steel-slag–rubber composite
sources. That Mission remains a Trust Boundary Demo, not a completed research
conclusion. No data has been fabricated to change this result.
