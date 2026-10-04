# Golden Demo Guide

## Purpose

This five-minute demonstration shows one governed AI Employee path, not a
pre-generated research result:

```text
Demo Workspace → Mission → AI Worker → Candidate Evidence → Human Review
→ Insight → Research Brief draft → Delivery review
```

The isolated Workspace is named **ResearchOS Demo Workspace**. It is marked
Demo, receives a MEMBER session, and cannot access administration or customer
Workspaces.

## Five-minute flow

1. Choose **Try Demo**. Confirm the Demo Workspace banner is visible.
2. On Home enter: `Analyze future research opportunities in low-carbon building
   materials using traceable evidence.` Select **Start Mission**.
3. Open the Mission and explain the AI Worker plan. It prepares only bounded
   Skills from the current Workspace context.
4. Create a controlled Computer task only when a reviewer-approved task is
   needed. The task shows observation, plan, approval, execution and
   verification. No external login, upload or unapproved modification occurs.
5. Review Candidate Evidence. A candidate is not a research conclusion; only
   the existing validation and human review flow can approve it.
6. When traceable Evidence is available, open the Research Insight and create
   a Research Brief draft. The draft remains **Needs review** until a reviewer
   approves release.

## Expected states

| Stage | Real expected state | Next action |
|---|---|---|
| Mission created | Planning / bounded AI Worker plan | Run the Mission |
| No corpus Evidence | Waiting for review or evidence | Attach or validate authorized sources; do not claim insight |
| Candidate sources found | Candidate Evidence | Reviewer validates sources |
| Evidence approved | Reviewable Insight | Create Research Brief draft |
| Artifact generated | Needs review | Reviewer approves, requests revision, or rejects |

## Recovery notes

- If the deployment has no approved corpus, the demo correctly stops at the
  Evidence boundary. Import approved demo sources before claiming a completed
  research result.
- If a Computer task needs a modification, the correct next state is approval,
  not automatic execution.
- If a reviewer account is unavailable, show the pending-review state; do not
  bypass it using the Demo MEMBER session.
