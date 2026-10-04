# ResearchOS FDE Solution Showcase

## Customer background

A building-materials R&D team needs to identify credible low-carbon material
opportunities while working across public research, authorized internal
material, expert review, and delivery deadlines. Their knowledge is valuable,
but it is commonly spread across projects and difficult to reuse safely.

## Business challenge

- Research sources are scattered and take time to assess.
- Candidate sources can be mistaken for verified Evidence.
- Innovation opportunities need expert review before they inform a decision or
  delivery.
- Lessons from one Mission should become Workspace-scoped knowledge, not remain
  in an isolated report.

## Solution design

ResearchOS positions one **AI Employee** inside an authorized Workspace. The
customer describes the desired outcome; ResearchOS creates a Mission and runs
the existing governed path:

1. **Mission** — Frame the business or research outcome in the customer
   Workspace.
2. **AI Worker** — Prepare a bounded plan using only authorized context and
   available Skills.
3. **Evidence** — Keep source candidates separate from trusted Evidence.
4. **Review** — Route material Evidence, decision, Computer, and delivery
   actions to an authorized human reviewer.
5. **Artifact** — Prepare a versioned, traceable delivery draft.
6. **Organizational Intelligence** — Surface only persisted Mission, Evidence,
   Review, Artifact, and Research Memory records from that Workspace.

This is not an autonomous scientific-decision claim. The product does not turn
unreviewed source candidates into approved Evidence or release a delivery
without its required human decision.

## Technical architecture

The showcase reuses the customer execution path rather than a presentation
runtime:

`Identity → Workspace → Mission → AI Worker → Skill → Evidence / Review → Artifact`

Workspace isolation and role-based permissions remain active at every API
boundary. The Computer Worker stays controlled: high-risk actions require
approval, actions are verified, and recovery is bounded. Prompts, chain of
thought, credentials, and raw private material are not presented in the
showcase.

## Business value

- **Research efficiency:** Teams keep goal, source review, and delivery work in
  one accountable path instead of fragmented handoffs.
- **Knowledge assets:** Approved Evidence, reviewed deliveries, and Research
  Memory can be reused within the same Workspace.
- **Trusted decision support:** Conclusions remain connected to their Evidence
  and an explicit human Review boundary.
- **Delivery readiness:** An Artifact retains its Mission, version, Evidence,
  and review status through Delivery.

No quantitative benefit is claimed unless it is measured from a customer’s
actual deployment data.

## Five-minute FDE presentation flow

1. Open **Solution Showcase** from the Workspace header.
2. Establish the building-materials R&D customer scenario and its research
   challenge.
3. Show the six-step governed flow from Mission to Organizational Intelligence.
4. Open the live Mission to show its AI Worker activity, Evidence boundary,
   review state, and next action.
5. Open a controlled Computer workflow when appropriate; explain that it is
   approval-aware and verified rather than unrestricted automation.
6. Open Delivery to show the Artifact’s review-aware status.
7. Return to the showcase and explain that its organizational figures appear
   only when the active Workspace contains real persisted records.

## Delivery flow

The customer receives a reviewable delivery path, not a black-box conclusion:

`Customer goal → Mission → Evidence-backed work → Human Review → Artifact → Delivery`

For production handover, pair this showcase with the permission matrix,
deployment documentation, risk boundary, and final release checklist.
