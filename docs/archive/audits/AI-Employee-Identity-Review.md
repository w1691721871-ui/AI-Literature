# AI Employee Identity Review

## Scope

This review covers the existing Home, Workspace, and Mission Room experience. It changes only the frontend presentation; it introduces no new API, storage, automated action, or generated activity.

## Product finding

The product already had the records needed to make the AI Employee feel present: a selected Mission, persisted progress, the Mission timeline, Evidence references, review state, and delivery state. The prior presentation distributed those records across dashboard cards and operational surfaces. A first-time user could understand the product category, but could not immediately tell what the AI Employee was doing for *their* Workspace.

## Changes made

### Home: AI Employee identity

Home now places an AI Employee identity surface directly below the mission entry point when a real Mission is selected. It presents only persisted Mission data:

- current work goal from the selected Mission;
- current status from the recorded Mission step;
- recorded work from the Mission timeline;
- the user's next decision from the existing activity or waiting-action summary.

The state chip is intentionally conservative. It animates only for a real Mission that is neither complete nor paused for review or revision. When no Mission exists, Home instead says: **“Your AI Employee is ready for a new research mission.”** It does not simulate activity.

### Workspace: organization context

The existing Workspace view remains the organization context for active Missions, reusable Research Memory, reviewable artifacts, and role-gated executive information. This preserves the distinction between an individual Mission and the authorized Workspace it belongs to. No cross-Workspace information is introduced.

### Mission Room: AI Employee desk

The Mission Room already uses the available Mission data as an AI work desk:

1. AI Employee header — current state, focus, and the next human decision.
2. AI Work Journal — each persisted event explains what happened, why it matters, and the currently recorded next action.
3. Supporting sources — Evidence is described as support for the Mission, with its review state visible.
4. Human Review — consequential decisions remain visibly human-controlled.
5. Delivery preparation — AI-prepared output remains a reviewable draft until release.

This sequence replaces the mental model of a task-management screen with a clear collaboration model: the AI Employee performs bounded Research Work; people make meaningful decisions.

## Language decisions

Core customer-facing Home and Mission paths use **AI Employee**, **Research Work**, **Evidence**, **Review**, **Artifact**, and **Delivery**. The identity surface does not show internal identifiers, hidden reasoning, prompts, runtime records, or technical logs.

## Data and trust boundary

All identity, status, timeline, Evidence, review, and delivery content is drawn from existing client state populated by the current APIs. Missing data stays visibly missing. The frontend does not infer progress, fabricate completed work, or turn candidate sources into Evidence.

## Remaining presentation boundary

Legacy compatibility and administrator-only interfaces may retain technical terminology for operational users. They are not part of the normal Home, Workspace, or Mission Room product path.
