# Executive Experience Review

## Scope

This is a frontend-only, role-aware presentation improvement. It adds no Agent, backend logic, database model, API call, or synthetic metric. It uses the existing Workspace dashboard, organizational intelligence, Mission, Evidence, Review, Artifact, and Research Memory data already loaded by the product.

## Audience boundary

The Executive Overview and Manager Summary appear only when the existing Workspace role is `OWNER`, `ADMIN`, or `MANAGER`.

Researcher, Reviewer, and Viewer experiences are unchanged: they continue to see the existing operational Workspace and Mission experience without executive-only summaries.

## Workspace Executive Overview

The Workspace page now provides a management-level summary with five real-state signals:

| Signal | Existing data used | Empty-state behaviour |
| --- | --- | --- |
| Active Missions | `workspaceExperience.active_missions` | Shows zero and states that no active Missions are recorded. |
| Evidence Progress | `organizationIntelligence.metrics.approved_evidence` | Shows zero and explains that no approved Evidence is recorded. |
| Review Queue | Workspace pending review count, then the existing approval list as fallback | States whether a human decision is waiting. |
| Delivery Status | Existing Workspace Artifact count, then organizational Artifact count as fallback | States that no delivery Artifact is recorded. |
| Organizational Learning | Existing Research Memory metric, then existing Workspace memory count as fallback | States that reusable learning is not yet recorded. |

If neither Workspace dashboard nor organizational intelligence has loaded, the overview displays a transparent no-data state rather than inferred metrics.

## Manager Mission Summary

The Mission Room now offers a concise Manager Summary above the stage progression. It expresses:

- **Goal** — the existing Mission objective or goal.
- **Current Status** — the existing current Mission step.
- **Business Impact** — the persisted employee-report completion reason when present; otherwise a clear statement that impact is not yet established.
- **Risk or Waiting Reason** — the existing activity next action or worker waiting action.
- **Expected Delivery** — the existing delivery label or contract output when present; otherwise a clear no-delivery-yet state.

This structure improves decision visibility without claiming business value, risk, or delivery when the Mission has not recorded it.

## Visual system

The overview uses the existing premium dark surface system with a restrained executive accent, compact decision cards, and responsive layouts:

- Desktop: five management signals in one readable row.
- Tablet: three-column hierarchy.
- Phone: single-column decision cards without clipping.

## Verification

- `node --check frontend/app.js`
- `node --check frontend/service-worker.js`
- `git diff --check`

No backend or database validation is required because no backend or database change was made.
