# AI Employee Proactive Experience Review

## Scope

This is a frontend-only product layer. It reads existing Mission, approval queue, Organizational Intelligence, Artifact, Evidence, and Workspace Memory state. It does not create a Mission, run research, alter permissions, or generate a research conclusion.

## AI Employee Daily Brief

Home now presents an **AI Employee Daily Brief** as a current summary of recorded Workspace work, not a fabricated daily report.

| Brief area | Existing data used |
| --- | --- |
| Completed | Recorded Mission work-journal entry, if one exists |
| Attention needed | Current pending approvals and the selected Mission review state |
| Recommended next step | Existing Mission state interpretation |
| Knowledge growth | Completed Missions, verified Evidence, Artifacts, and Research Memory from Organizational Intelligence |

When no record exists, the UI says so directly rather than manufacturing an activity or a completion.

## Research Opportunity

The **Potential research opportunity** card appears as a review suggestion only when the Workspace has a completed Mission, verified Evidence, or reusable Research Memory. Its language is deliberately bounded:

- it says that existing organizational knowledge can support a *human-reviewed follow-up question*;
- it gives the actual count basis used for that suggestion;
- it never creates a Mission, starts research, or asserts a research conclusion.

Without underlying records it says **“No research opportunity detected yet.”**

## Team working patterns

Workspace now describes real collaboration patterns only where corresponding records exist:

- Evidence-first review when verified Evidence exists;
- Human approval workflow when review activity or verified Evidence is present;
- Research delivery pattern when reviewable Deliveries exist;
- Reusable team context when Workspace-scoped Research Memory exists.

With no supporting records, the UI says **“Building collaboration patterns.”**

## Safety and data boundary

All summaries are calculated on the client from already loaded, Workspace-scoped data. They do not expose prompts, hidden reasoning, technical execution data, model memory, or other Workspaces' records. Suggested actions remain navigational and require the existing human approval path for meaningful decisions.
