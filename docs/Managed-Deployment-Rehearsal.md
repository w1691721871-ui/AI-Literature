# Managed Deployment Rehearsal

**Date:** 2026-10-07  
**Scope:** deployment, persistence, interruption, and Golden Demo verification.

## Deployment environment

| Item | Result | Classification |
| --- | --- | --- |
| Local HEAD before rehearsal | `ec2e766` | VERIFIED |
| `origin/main` at inspection | `1eb510b` | VERIFIED |
| Public frontend | `https://ai-literature-13.onrender.com` returned HTTP 200 | VERIFIED |
| Public frontend assets | references `app.js?v=153`; local source uses v169 | VERIFIED — stale deployment |
| Public backend | `https://ai-literature-109.onrender.com/health` returned HTTP 200 | VERIFIED |
| Managed deployed commit | not exposed by host | BLOCKED BY ENVIRONMENT |

## Database persistence

`render.yaml` configures SQLite at `/var/data/research_library.db`, but declares the Render free plan and no persistent-disk resource. Repository deployment documentation also states that free Render local storage is ephemeral. The live health endpoint proves writable storage, not storage that survives redeploy.

**Result: BLOCKED BY ENVIRONMENT / P1.** The durable application layer is real, but the currently evidenced managed persistence substrate is not durable. A Render Persistent Disk (or an approved managed persistence design) is required before claiming hosted restart persistence.

## Live managed interruption

**BLOCKED BY ENVIRONMENT.** No Render dashboard or process-control access is available here, so a managed service cannot be terminated or restarted. This is not reported as a live PASS.

## Local production-like interruption rehearsal

**VERIFIED.** The current application ran as Uvicorn against a separate temporary SQLite work directory. A Workspace owner registered via the real HTTP identity API, created a Mission, and ran the actual Mission endpoint.

Before forceful termination, the Mission stopped truthfully at an evidence-insufficient review boundary:

- Mission state: `WAITING_ADAPTIVE_REVIEW`.
- Checkpoint phase: `WAITING_REVIEW`.
- Next action: Human review required.
- Observation: no traceable Evidence was found.
- Evaluation: `NEEDS_EVIDENCE`.
- Resume policy: `NEEDS_REVIEW`.
- Timeline count: one bounded Skill action.

After killing Uvicorn and restarting the same application against the same SQLite directory, a fresh login returned the same Workspace, Mission, checkpoint, observation, evaluation, and review boundary. A direct Mission run returned HTTP 400. No second Skill action, Evidence, Artifact, or approval was created.

## Pause and resume rehearsal

**VERIFIED.** A second Mission was paused through the real HTTP API, the process was killed and restarted, and the Mission remained `PAUSED` with its saved reason. Direct execution was denied. An authorized resume continued its saved lifecycle into the existing review boundary without creating a second Mission.

## Integrity boundaries

| Boundary | Result | Classification |
| --- | --- | --- |
| Mission/checkpoint recovery | survives process restart | VERIFIED locally |
| Lease collision and expiry | second active Worker denied; expired claim recoverable | VERIFIED BY TEST |
| Unknown action | review-bound; never assumed successful | VERIFIED BY TEST |
| Verified action idempotency | prior verified checkpoint step cannot replay | VERIFIED BY TEST |
| Candidate Evidence | no candidate became approved Evidence | VERIFIED locally |
| Review | direct run at review boundary denied | VERIFIED locally |
| Artifact | no Artifact created without Evidence and Review | VERIFIED locally and by tests |
| Workspace isolation | Mission, Artifact, Computer, Knowledge, Memory checks | VERIFIED BY TEST |

## Golden Demo validation

### Failure path

**PASS.** With no indexed corpus, the real Mission produced no traceable Evidence, no fabricated Insight, and no Artifact. It stopped at Human Review.

### Full Evidence-to-Artifact path

**BLOCKED BY DATA.** Live diagnostics reported zero papers, chunks, embeddings, and FAISS entries. No authorized demo corpus was supplied locally, so a complete Evidence → approved Insight → reviewable Research Brief was not faked.

### Pause/Resume and security path

**PASS locally / by regression.** The direct review-bound execution path is denied. Identity, RBAC, cross-workspace, Computer approval, and Artifact review regressions remain covered.

## UX observation and repair

The Mission projection contains current work, next action, Evidence boundary, and review requirement without checkpoint IDs, lease IDs, Worker IDs, prompts, or chain-of-thought. This rehearsal found one P1 wording defect: an ordinary evidence-insufficient review boundary was described as an interruption. It was repaired so recovery language appears only for a real `ACTION_STARTED` interruption.

## Readiness summary

| Area | Status |
| --- | --- |
| Local production-like recovery | PASS |
| Failure-path Golden Demo | PASS |
| Pause / Resume Golden Demo | PASS |
| Full success-path Golden Demo | BLOCKED BY DATA |
| Live managed interruption | BLOCKED BY ENVIRONMENT |
| Managed persistent storage | P1 — NOT VERIFIED |
| Deployed version parity | P1 — STALE / NOT SYNCHRONIZED |

## Evidence-limited demo score

These scores describe the currently verified environment, not a desired future
state. A blocked validation lowers the score rather than being assumed to pass.

| Dimension | Score / 5 | Reason |
| --- | ---: | --- |
| First impression | 3 | Public UI is available but stale relative to the local release. |
| Goal understanding | 4 | Real Mission goal and next action were persisted and readable. |
| AI Employee feel | 4 | Current work, review boundary, and resume state were user-readable. |
| Research quality | 2 | No approved indexed corpus was available for a full research result. |
| Evidence traceability | 4 | Candidate scarcity correctly stopped insight generation. |
| Human Review | 5 | Real API run stopped at review; direct bypass was denied. |
| Recovery | 4 | Real local process interruption preserved state; managed interruption is blocked. |
| Persistence | 2 | Local SQLite rehearsal passed; managed durable storage is unverified. |
| Artifact quality | 1 | Full Artifact flow is blocked by missing authorized Evidence. |
| Security | 4 | Local authorization boundary and regression coverage passed. |
| UX continuity | 3 | API continuity passed; a current deployed-browser walkthrough remains blocked by version drift. |
| Business value | 3 | Trustworthy failure path is clear, but the success delivery story needs real demo data. |

## Required external release actions

1. Push the audited commit set and redeploy frontend and backend.
2. Attach durable storage at `/var/data`, then repeat the managed interruption rehearsal.
3. Import an approved persistent demo corpus and run the full Evidence → Review → Artifact Golden Demo.
4. Recheck public asset cache version and backend version after deployment.

Until these actions are complete, ResearchOS is **not approved for a managed-production durability claim**, although the local production-like rehearsal passes.
