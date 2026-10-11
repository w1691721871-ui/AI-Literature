# Persistent AI Employee & Controlled Browser Audit

## Scope and principle

This upgrade reuses the existing AI Worker Runtime, Mission lifecycle,
Workspace Context, Computer Skill, Evidence, Review, Artifact, and Memory
systems. It adds no Agent, Runtime, Mission model, Memory model, or unbounded
background loop.

## Current capability

### Persistent Mission state

ResearchOS persists two complementary, workspace-bound state projections:

- `MissionControlState` retains pause intent, the prior Mission status, pause
  reason, and bounded recovery count.
- `RuntimeExecutionState` retains the current user-readable phase, current
  Worker area, latest observation, evaluation, next action, and stop reason.
- `RuntimeExecution` retains an ordered, user-readable history of bounded
  Skill actions without prompts, chain-of-thought, secrets, raw tool payloads,
  or source bodies.

The resulting state expresses active work, pause, recovery, review, and
completion without adding a parallel persistence model.

### Pause and resume

`MissionLifecycleService.pause()` stops the Mission at a persisted boundary;
no further Skill action can be initiated while status is `PAUSED`.

The public resume endpoint now calls `AIWorkerRuntime.resume()` after the
existing lifecycle transition. Before continuation, it reloads:

1. the persisted Mission,
2. the current RuntimeExecutionState,
3. fresh, authorization-checked Workspace Context, and
4. the latest Mission status and approval boundary.

Only runnable states (`CREATED`, `PLANNING`, `NEEDS_REVISION`,
`ADAPTIVE_REPLANNING`, `APPROVED`) can continue. Waiting review, failed,
rejected, and completed states are restored as a visible boundary rather than
restarted or bypassed. Resume is therefore a trusted continuation, not a new
Mission.

### Bounded recovery

- Research Evidence insufficiency can trigger one adaptive read-only follow-up
  inside the existing finite policy. The initial action is recorded as
  `REPLANNING`; the follow-up is a distinct auditable execution record.
- A second insufficiency, an exception, a Computer change, approval-gated
  work, permission failure, or review requirement stays at Human Review.
- `MissionLifecycleService` limits explicit recovery preparation to two.
- `ComputerRecoveryService` limits safe Computer recovery to two attempts and
  refuses unexpected environment changes.

### Controlled Browser boundary

`BrowserAdapter` and `ComputerExecutionEngine` provide real public HTTPS
metadata discovery with allow-listed actions: search, navigate, extract, and
verify. The adapter rejects HTTP, localhost, private addresses, credentialed
flows, and side-effecting actions. Browser candidates are not Evidence and are
not written into Memory directly; the existing Evidence validation workflow
remains mandatory.

`ResearchBrowserWorker` enforces maximum query and adjustment counts, scores
candidate source quality, and returns `NEEDS_REVIEW` after bounded coverage
attempts. It does not claim Computer Vision or unrestricted browser control.

## Context and Memory influence

Context retrieval is not only a display projection:

- `WorkspaceContextService.build()` is called before execution, after each
  Skill, and before resume. It rejects cross-workspace actors and retrieves
  only authorized, current-Workspace summaries.
- `ContextSelectionService` ranks Memory and approved Artifact summaries using
  Mission relevance, trust/lifecycle, current-Mission history, and task value.
  Selected Memory is marked as used through `WorkspaceMemoryService`.
- `AITeamOrchestrator` uses the refreshed Workspace Context to validate the
  Workspace and order only currently permitted Skills.
- `ComputerStrategyService` uses authorized Evidence and current controlled
  Mission state to choose only existing, review-bounded routes; approved
  delivery and safe Computer experience metadata remain visible planning
  signals. Historical experience never grants permission.

This is real state influence within the present deterministic policy model;
it is not a claim of open-ended semantic preference learning. Richer learned
strategy would need a separately evaluated product decision rather than a
hidden heuristic.

## Completion detection and employee report

The Employee Report is now a work-result projection, not just a status label.
It includes current work, next action, latest grounded finding, completion
state, completion reason, completed work, evidence boundary, artifacts, and
unresolved human action.

Completion distinguishes `COMPLETED`, `PARTIALLY_COMPLETED`,
`WAITING_REVIEW`, `NEEDS_REVIEW`, and `IN_PROGRESS`. A completed function call
cannot by itself produce a completed Mission claim: the report requires the
recorded delivery state, evidence/review conditions, and absence of an
unresolved runtime stop reason.

## Mission Room continuity

The Mission Room now makes the continuing employee state visible through an
**AI Employee at work** panel:

- current work,
- current goal,
- latest evidence finding,
- required human action, and
- a user-readable completion reason.

The existing Pause / Continue / Prepare recovery controls are visible again as
product controls, not hidden technical state. No runtime IDs, planner state,
raw action JSON, or debug payload is added to the normal-user view.

## Validation

Targeted coverage added or retained:

- resume reloads context and only continues a runnable Mission;
- recovered Evidence runs one bounded read-only follow-up;
- report explains persisted work and a completion boundary without internal
  reasoning fields;
- workspace isolation, finite adaptive execution, Computer review boundaries,
  and lifecycle limits remain covered by the existing suite.

## Remaining P1/P2 gaps and why they are not expanded here

1. **P1 — durable queued execution across server restarts.** The current
   synchronous bounded runtime is correct for the demo and avoids inventing a
   background job platform. A durable queue requires operational deployment,
   retry ownership, and observability decisions beyond this controlled pass.
2. **P1 — full browser operator.** ResearchOS has a real restricted public
   browser path, not visual desktop control. Adding browser login, cookie
   handling, screen interpretation, or external write capabilities would
   materially change its safety posture and is intentionally deferred.
3. **P2 — deeper learned strategy.** Memory is trusted, scoped, lifecycle
   managed, and used in context/strategy selection. Learning model-derived
   preferences needs customer data, evaluation, and retention policy before it
   can be responsibly automated.
4. **P2 — real-time collaboration and enterprise integrations.** These would
   add operational infrastructure rather than strengthen the current
   AI-Employee core path.

## Stop decision

For the current product boundary, there is no remaining P0 and no P1 that can
be safely closed without introducing a new infrastructure category or
overstating Computer capability. ResearchOS should now stop feature expansion
and move to FDE interview preparation, live demo rehearsal, and deployment
readiness validation.
