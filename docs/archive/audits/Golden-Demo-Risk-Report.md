# Golden Demo Risk Report

## Scope

This is a frontend-only audit of the five-minute FDE presentation path. It
does not alter Mission, Evidence, Review, Artifact, identity, or permission
behavior.

## Recommended Five-Minute Path

1. Open **Try Demo** and confirm the Demo Workspace banner.
2. Open **Solution Demo** to introduce the customer challenge, AI solution,
   trust boundary, business value, and delivery workflow.
3. Select the Research step. It now opens a prefilled **Mission** form; it
   does not silently create a Mission or synthetic outcome.
4. Create the Mission and use the Mission Room to explain the real sequence:
   Understand Goal → Plan Research → Collect Evidence → Human Review →
   Delivery.
5. Show supporting sources or the explicit Evidence boundary.
6. Explain that a Reviewer, not a Demo Member, resolves Evidence and Delivery
   decisions.
7. Open **Research Delivery Center** to show Draft → Review → Approved →
   Delivered and the real empty state when no Artifact exists.

## Risk Matrix

| Checkpoint | Current behavior | Risk | Presenter action |
| --- | --- | --- | --- |
| First visit | Login, account creation, and Try Demo are visible. | Low | Use Try Demo for the isolated Workspace. |
| Demo identity | Demo uses a MEMBER role and hides Admin Console. | Low / expected | State that the isolation is intentional. |
| Mission creation | A prefilled live-demo Mission may be created from the Mission Room. | Low | Confirm creation explicitly; it is never automatic. |
| AI Employee status | Status and timeline come from recorded Mission state. | Low | Do not describe a planned step as complete. |
| Evidence | Live research requires indexed, authorized sources. | Medium | If none are indexed, show the Evidence boundary as the trust feature. |
| Review | Demo Member cannot approve Evidence or release a Delivery. | Medium / expected | Use a Reviewer session for a full approval walkthrough. |
| Delivery | A delivery appears only after the governed workflow produces one. | Medium | Use the Delivery Center empty state when no real Artifact exists. |
| Solution Showcase | Product narrative is independent of corpus volume. | Low | Use it to keep the presentation coherent when live data is sparse. |

## Fixes Applied During This Audit

- The Demo Workspace banner now explains the actual Review and Delivery role
  boundary and reports whether indexed sources are available.
- The Solution Demo Research action opens a prefilled Mission form instead of
  returning to Home.
- The Mission action now says **Create live demo Mission**, making the real
  data-creating consequence clear.
- The Demo startup error is presented in customer language rather than exposing
  a raw backend message.
- Frontend static assets were advanced to `v182`; runtime configuration remains
  excluded from the cache.

## Blocking Dependencies for a Full Live End-to-End Walkthrough

The following are not frontend issues and must be available before claiming a
completed live Evidence → Review → Delivery demo:

1. An indexed, authorized corpus in the Demo Workspace.
2. A Reviewer or higher-role session to approve Evidence and Delivery actions.
3. A reachable backend identity session and Mission API.

Without those conditions, ResearchOS correctly pauses at the Evidence or
Review boundary. This is a governed outcome, not a demo failure.

## Presenter Readiness Checklist

- Confirm the Demo Workspace banner and current role before the meeting.
- Confirm that at least one authorized source is indexed if live Evidence is
  part of the presentation.
- Keep a Reviewer session available if actual approval and delivery release
  will be demonstrated.
- Use Solution Showcase as the stable narrative backbone; use live Mission
  records only to demonstrate states that are genuinely present.
