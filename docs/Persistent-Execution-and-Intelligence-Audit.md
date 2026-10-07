# Persistent Execution and Intelligence Audit

## Architecture at this release

ResearchOS has one normal user path:

`Identity → Workspace → Mission → AIWorkerRuntime → bounded Skill → Evidence / Review → Artifact`

The durable layer augments that path. It does not create another Agent or a
second Runtime. SQLite remains the system of record for the current deployment
profile.

## Durable Mission execution

`MissionExecutionCheckpoint` stores a compact, workspace-scoped work boundary:
the goal summary, current objective, next action, completed step summaries,
latest user-readable observation and evaluation, retry/recovery counts, waiting
reason, resume policy, and safe action lifecycle. It excludes prompts,
chain-of-thought, secrets, cookies, tokens, raw tool payloads, complete web
pages, and file bodies.

`MissionExecutionLease` is a short-lived claim used only to avoid concurrent
workers. The Mission, its contract, Runtime state, Review state, Evidence, and
Artifact data remain the business facts. A stale lease can expire and be safely
claimed by a later Worker.

## Checkpoint and crash recovery

Each bounded AI Worker Skill action now follows this persisted boundary:

`ACTION_PLANNED / ACTION_STARTED → ACTION_OBSERVED → ACTION_VERIFIED / ACTION_FAILED`

On application startup, the recovery scan classifies active checkpoints but
does **not** autonomously execute them. This deliberately preserves the
authenticated Workspace actor, current RBAC, and approval boundary:

- a checkpoint interrupted before an action began becomes `RECOVERING` and is
  `RESUME_ELIGIBLE` for an authorized Workspace member;
- an `ACTION_STARTED` result is unknown after a crash, so it becomes
  `WAITING_REVIEW` rather than being assumed successful or automatically
  replayed;
- exhausted recovery limits become `WAITING_REVIEW`;
- paused, completed, and existing review boundaries remain unchanged.

This provides durable continuation without a daemon thread, in-memory queue, or
unbounded startup loop. The current product intentionally requires an
authorized user to initiate resumed work; a service process never impersonates
a user to execute a Mission.

## Idempotency

The checkpoint creates a bounded action key from Mission, checkpoint, step, and
action type. A previously `ACTION_VERIFIED` step is not re-executed on resume.
An interrupted action is treated as uncertain, not duplicated. This is more
conservative than claiming generic external idempotency where an underlying
source cannot prove it.

## Browser capability and safety

Current Browser capability is **Level 2 — structured public HTTPS extraction**:

- public HTTPS metadata discovery and safe navigation;
- source candidates, titles, URLs, provider metadata, quality evaluation, and
  verification status;
- no browser login, credential handling, form submission, purchases,
  publishing, deletes, private network access, localhost access, or visual
  browser / Computer Vision claim.

Browser candidates stay separate from Evidence. They must pass the existing
Evidence validation and human review flow before they can support Knowledge,
Insight, or an Artifact.

## Memory and organizational learning

Workspace Context selects only relevant, authorized Workspace Memory and
approved Artifact summaries. Selection records use so it is traceable and
never retrieves a hidden global memory. Computer reflection only saves compact,
non-sensitive task experience when an existing controlled Computer outcome is
available. Historical experience is a planning signal only: it cannot grant a
permission, bypass Human Review, or turn a candidate into Evidence.

Organizational learning remains anchored in the existing Mission → Evidence →
Review → Artifact → Workspace Memory lifecycle. A memory is not promoted to a
truth claim merely because it was used once.

## Validation

The test suite now covers:

- durable checkpoint reuse across a new Worker instance;
- no replay after a verified action;
- safe review boundary for an interrupted started action;
- paused/completed checkpoint non-recovery;
- duplicate live-worker claim denial and lease expiry recovery;
- resumable safe boundary classification;
- workspace-isolated checkpoint access.

The full local suite currently passes with **375 tests**.

## Remaining P1 / P2

- **P1:** a truly unattended durable worker requires an explicit service
  identity, scheduling policy, observability, and customer-approved execution
  ownership. It is intentionally not faked with a background thread.
- **P1:** visual browser control is absent. The product must continue to state
  public, read-only structured-browser capability only.
- **P2:** confidence-calibrated strategy learning needs real repeated reviewed
  customer outcomes and a retention policy before it can be automated.
- **P2:** multi-node deployment needs a database with robust cross-process
  leasing semantics and operational monitoring; SQLite is suitable for the
  current bounded deployment profile.

## Next-stage recommendation

Do not add more Agent types. Validate this durable boundary in a deployment
rehearsal: interruption during a read-only action, review-bound recovery, and
an authorized user continuation. Only after that should the team make an
infrastructure decision about unattended worker ownership.
