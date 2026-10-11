# FDE Demo Readiness Audit

**Scope:** Frontend presentation and Demo-flow readiness only. This audit does not
change API contracts, persistence, AI execution, Evidence rules, or approval
boundaries.

**Assessment date:** 2026-10-11
**Current score:** **95 / 100 — isolated local Demo release gate passes**

> **Status update — v200 closure:** The guarded isolated Demo stack now
> passes `scripts/demo_release_check.py`: database, corpus, FAISS, Owner /
> Reviewer memberships, recorded reviewed Artifacts, API identity, frontend
> identity, and Workspace alignment all pass. Use
> [Final Demo Runbook](../FINAL-DEMO-RUNBOOK.md) for the current operator
> procedure. The observations below retain the original audit findings for
> presentation risk awareness.

## A. What was verified

| Area | Result | Evidence |
| --- | --- | --- |
| First-use path | Improved | The sign-in screen now identifies the product, intended team, trust model, and direct Demo Workspace action. |
| Demo navigation | Improved | Golden Demo calls now open the prefilled Mission draft instead of silently only changing a goal field. |
| Mission safety | Improved | The live Demo Mission action is visible only before a Mission is selected and explicitly says it creates and runs a real Mission. |
| Demo corpus (isolated environment) | Pass | Read-only diagnostics found 6 scenario papers, 131 chunks, 131 embeddings, and an available FAISS index. |
| Reviewer setup (isolated environment) | Pass | Environment check found one persisted reviewer membership. |
| Recorded governance history | Pass | Diagnostics found 2 approved and 1 needs-revision Mission review records. |
| API release identity | Pass (guarded Demo stack) | The guarded Demo API reports `researchos-demo-v200`, the current release commit, `v200`, and `demo`. |
| Live delivery walkthrough | Pass (recorded state) | The isolated Demo database contains two Artifact-backed Missions and two approved Mission reviews. |
| Demo-mode launch | Pass | `demo_environment_check.py` reports Demo mode, Workspace isolation, Reviewer, corpus, embeddings, and FAISS as `PASS`. |

## B. Top 10 interview risks

1. **Use the guarded Demo launcher.** An ordinary development API can still point to non-Demo data. Start the presentation stack with `scripts/run_demo_server.py`, not a generic development command.
2. **Release identity must move with the final commit.** The guarded local launcher derives it from Git, and Render uses `RENDER_GIT_COMMIT`. Verify the value after each deployment.
3. **The live Mission → Evidence → Review → Delivery path must be preserved.** The isolated Demo database contains recorded governed results; rehearse the intended presentation path before the interview.
4. **A reviewer must be authenticated separately.** A normal Demo Owner session cannot truthfully demonstrate a reviewer decision.
5. **The browser depends on the external Vue CDN (`unpkg.com`).** Test the venue network or warm the required asset before presenting.
6. **Service workers are not available on normal HTTP LAN origins.** The site still works, but offline cache behavior is not part of the LAN demonstration.
7. **Network changes can invalidate the LAN address.** Reconfirm the laptop address, `0.0.0.0` listeners, and firewall state on site.
8. **No corpus must never be hidden.** The product correctly pauses at the Evidence boundary; this is a trust demonstration, not a failure to mask.
9. **Avoid creating multiple live Missions during the talk.** Reuse the prepared Mission or open the safe Golden Mission draft. Creating a new Mission is an explicit, real operation.
10. **Do not promise a completed delivery from a pending review.** Show only the persisted Review and Delivery status shown by the product.

## C. Automatically fixed for this audit

- Reframed the sign-in view as a concise product entry point: **AI Research Employee for enterprise teams**, its Evidence-first workflow, and the Demo Workspace action are visible before authentication.
- Added an explicit description of the safe Demo path: **Mission → Evidence → Review → Delivery**.
- Made all no-Mission Golden Demo entry points open the prefilled Mission draft, eliminating a button that appeared to act but only filled an off-screen field.
- Clarified that creating and running a live Demo Mission is a real action, and hid that action after a Mission is already selected.
- Updated frontend cache identity to **v200**. Old service-worker caches matching the ResearchOS cache family will be deleted on activation; runtime configuration remains network-only.

## D. Required manual preparation

1. Launch the backend with `scripts/run_demo_server.py`; it selects `DEMO_MODE=true` and persistence beneath `demo/work/` before importing FastAPI.
2. Run `python scripts/demo_environment_check.py`, `python scripts/demo_diagnostics.py`, and `python scripts/demo_release_check.py`; each must pass.
3. Sign in once as Demo Owner and once in a separate browser profile as Demo Reviewer. Confirm that the prepared Mission, its real Evidence, and its stored review decision are visible.
4. After a release deployment, confirm `/api/version` reports its actual Git SHA; do not supply a stale static `RESEARCHOS_COMMIT` in Render.
5. On the presentation network, load the product once and confirm the Vue CDN, backend health, and Demo session request complete. If presenting over LAN, reconfirm the laptop IP and firewall.

## E. Recommended five-minute FDE path

| Time | Screen | Story to tell |
| --- | --- | --- |
| 00:00 | Sign-in / Home | “ResearchOS is an AI Research Employee for enterprise research teams—not a chat answer.” Open the labeled Demo Workspace. |
| 00:30 | Solution Showcase | Frame the building-materials customer challenge: scattered research, slow validation, and knowledge that does not compound. |
| 01:00 | Mission Room | Open the prepared Mission. Show its goal, current focus, and work journal as recorded work, not simulated progress. |
| 02:00 | Evidence | Show source quality and explain that candidate sources require Human Review before conclusions become trusted knowledge. |
| 03:00 | Review | Switch to the prepared Reviewer session. Explain the decision boundary and show the persisted decision or requested revision. |
| 04:00 | Delivery | Show the Research Brief/Artifact only at its recorded status. Tie it to supporting Evidence and the next accountable action. |
| 04:40 | Workspace / Solution Showcase | Close with Organizational Learning: completed work becomes reusable, reviewable team knowledge. |

## Final call

**Local Demo release gate: READY.** Managed deployment, venue networking, and the final committed release hash remain operator-controlled checks. The product does not fabricate readiness or research outcomes.
