# Production Failure and Security Drill

**Scope:** local, deterministic production-failure and security drill against
the persisted Mission, Runtime, Identity, Workspace, Evidence, Review, and
Artifact boundaries. No synthetic browser result, Evidence approval, Artifact
release, or background identity bypass was used.

| Drill | Result | Evidence / outcome |
| --- | --- | --- |
| 1. Mission crash | PASS | A persisted checkpoint retains phase, objective, next action, observation, evaluation, recovery counters, and resume policy across a new Worker instance. |
| 2. Unknown action state | PASS | `ACTION_STARTED` after restart becomes `WAITING_REVIEW`; it is neither assumed successful nor replayed. |
| 3. Read-only recovery | PASS, conservative | Verified read-only work is never repeated. An interrupted read-only action is preserved as uncertain and requires an explicit reviewer decision before a fresh bounded action; this is safer than fabricating verification. |
| 4. Completed Mission | PASS | Completed checkpoints are not selected for recovery and direct runtime execution is denied at the completion boundary. |
| 5. Waiting Review | PASS | Startup preserves the review boundary; direct execution cannot bypass it. |
| 6. Paused Mission | PASS | The Mission lifecycle status wins over a stale active checkpoint; startup retains `PAUSED` and does not execute it. |
| 7. Workspace isolation attack | PASS | Existing permission tests cover cross-workspace Mission, Artifact, Computer, Knowledge, Memory, and Approval access denial. Checkpoint snapshots also reject a different Workspace. |
| 8. Identity attack | PASS | Existing Identity and route tests reject missing or invalid session context with 401. Startup recovery never creates an actor or executes on behalf of a user. |
| 9. Approval bypass attack | PASS | Runtime accepts only runnable lifecycle states; `WAITING_REVIEW`, failure, rejection, and completion cannot be executed directly. |
| 10. Lease collision | PASS | A live Worker lease blocks a second claim; an expired lease can be safely claimed after loading current persistence. |
| 11. Duplicate execution | PASS | A verified step has a checkpoint action key and is not re-issued; review/complete states are execution gates. |
| 12. Execution ceilings | PASS | Durable total-step ceiling is five; recovery is capped at two; existing adaptive replan and browser query/adjustment limits remain covered. Restart does not reset checkpoint counts. |
| 13. Memory safety | PASS | One experience stays LOW confidence; only repeated controlled outcomes reach MEDIUM/HIGH and can suggest an otherwise safe route. Experience cannot bypass review or permissions. |
| 14. Evidence integrity | PASS | Existing tests retain Candidate Evidence separation; no unvalidated candidate becomes approved Evidence or a grounded conclusion. |
| 15. Artifact integrity | PASS | Existing Artifact tests retain evidence/review requirements and prevent unreviewed release. |
| 16. Deployment restart | PASS — local lifecycle drill | The startup recovery path was exercised with a new persistent service instance. This workspace has no managed production process to kill/restart, so this is not a claim of live-host validation. |
| 17. UI security | PASS | The Mission Room receives only safe employee-report language. It does not render checkpoint, lease, worker, raw state, prompt, CoT, or payload identifiers. |
| 18. Multi-Mission stress | PASS | Checkpoint and lease tests use isolated Mission identifiers; the full suite retains workspace and lifecycle isolation coverage. |

## P0 discovered and fixed during this drill

`AIWorkerRuntime.execute()` previously accepted a direct call after a Mission
had reached `WAITING_REVIEW`. Although normal product routing already presented
review controls, this created an avoidable second path at the runtime boundary.
The runtime now accepts only `CREATED`, `PLANNING`, `NEEDS_REVISION`,
`ADAPTIVE_REPLANNING`, or `APPROVED`. A paused, review-bound, failed, rejected,
or completed Mission returns a controlled error and performs no Skill action.

## Reviewed continuation

When a reviewer approves a Mission after an interrupted action, persistence
does not reinterpret the unknown action as success. It clears only the stale
action intent and permits a **new**, bounded, approved action. This keeps the
reviewer in control while avoiding a permanent recovery deadlock.

## Regression coverage

Added / extended coverage covers checkpoint survival, unknown action handling,
paused/reviewed lifecycle precedence, lease collision and expiry, verified-step
idempotency, total-step enforcement, reviewed continuation, direct review-bound
execution denial, and workspace isolation. The full local suite passes with
**383 tests** after this drill.

## Residual limitations

- The browser boundary is deliberately structured public HTTPS extraction, not
  authenticated or visual browser automation.
- The deployment restart item is a local lifecycle drill. A managed-host
  rehearsal remains an operational release check, not an application claim.
- SQLite leasing is appropriate for the current single-process bounded
  deployment profile. Multi-node worker deployment needs a separately approved
  database and scheduler decision.

## Production readiness conclusion

**PASS for the declared Durable AI Employee boundary.** No open P0 remains and
no P1 blocks the governed Mission → Evidence → Review → Artifact experience.
The next work should be deployment rehearsal and customer validation, not
additional product capability.
