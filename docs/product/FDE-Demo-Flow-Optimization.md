# ResearchOS FDE Demo Flow Optimization

## Objective

Deliver a five-minute enterprise conversation—not a feature tour. The Demo path uses the existing Demo Workspace, live Mission state, Evidence, Human Review, and Delivery records. It does not create synthetic activity or bypass a reviewer.

## Recommended live sequence

| Time | Surface | What to say | What the audience should see | Next action |
| --- | --- | --- | --- | --- |
| 00:00–00:30 | **Home** | “ResearchOS is an AI Research Employee for enterprise research teams.” | The product promise: research goal → Evidence → Human Review → Delivery. | Select **Start guided walkthrough** in a Demo Workspace. |
| 00:30–01:10 | **Solution Showcase** | “The problem is scattered research knowledge and slow evidence validation—not a lack of chat answers.” | Customer Challenge, Enterprise AI Solution, Trust & Governance, Business Value. | Use **Open live Mission** / **Prepare Golden Mission**. |
| 01:10–01:50 | **Golden Demo guide** | “This is the standard low-carbon building-materials scenario, backed by the Demo Workspace’s live records.” | Four steps and the live status / next-step pair. | Open the real Mission Room. |
| 01:50–02:45 | **Mission Room** | “This is the employee’s work desk: goal, recorded work, and the sources it can support.” | Current focus, Research Work Journal, supporting Evidence. | Move from Evidence to the visible Human Review panel. |
| 02:45–03:35 | **Human Review** | “AI prepares research support; an authorized person decides what can move forward.” | The current real review state. If it is waiting, use the separate Reviewer session. | Continue only when the recorded state allows Delivery preparation. |
| 03:35–04:25 | **Delivery** | “The output is a traceable research outcome, not an unreviewed answer.” | Evidence count, review state, and Delivery package / Delivery Center. | Open the Workspace context. |
| 04:25–05:00 | **Workspace / Solution Showcase** | “Verified work becomes reusable organizational knowledge within this Workspace.” | Approved Evidence, Delivery history, and Workspace-scoped knowledge, only when real records exist. | Close with the governance boundary. |

## Changes in this pass

1. **Demo Workspace banner:** added one explicit `Start guided walkthrough` action. A first-time presenter no longer has to infer where the customer story begins.
2. **Golden Demo guide:** the primary action now adapts to real state:
   - With an existing Mission: `Open live Mission`.
   - Without one: `Prepare Golden Mission` opens the existing Mission form with the standard goal; it does not create or run a Mission automatically.
3. **Live handoff panel:** Golden Demo now states the current recorded Mission status, why it matters, and the next real step beside the four presentation stages.
4. **Responsive presentation:** the new banner action and live handoff stack on smaller screens instead of compressing controls.

## Navigation decision

No new top-level Demo navigation is needed. The current path is deliberately linear:

`Home → Solution Showcase → Golden Demo guide → Mission Room → Evidence / Human Review → Delivery`

Adding another persistent Demo destination would introduce a second product path and increase the risk of a presenter opening an empty or non-Demo view.

## Demo safety and recovery

| Situation | Correct demonstration behavior |
| --- | --- |
| No selected Mission | Use **Prepare Golden Mission**. It pre-fills the real Mission form; the presenter still confirms creation. |
| No indexed sources | Explain the visible Evidence boundary: ResearchOS does not claim a conclusion without support. Do not improvise a result. |
| Review waiting | Switch to the separately authenticated Reviewer session, or use the state to explain the human-control boundary. |
| Reviewer is unavailable | Do not simulate approval. Continue with the Trust Boundary narrative and show why Delivery remains review-aware. |
| Delivery is not ready | Show the recorded status and return to Evidence / Review. A Delivery appears only once the normal workflow has reached that state. |
| Network or API unavailable | Use the visible connection state; do not claim the Demo is current. Restore the Demo environment before restarting the presentation. |

## Presenter checklist

- Sign in to the isolated Demo Workspace before the conversation begins.
- Confirm the Demo banner states whether indexed sources are available.
- Open Solution Showcase first; do not start on a dense Workspace page.
- Use the prepared Golden Mission or its stateful guide action.
- Keep the Owner / Researcher / Reviewer handoff explicit.
- Only show approval or Delivery using recorded data and the correct authorized session.

## Data integrity boundary

This optimization uses existing UI state only. It does not create Demo Evidence, auto-approve a review, create an Artifact, or change any Mission, Evidence, Review, Delivery, or permission behavior.
