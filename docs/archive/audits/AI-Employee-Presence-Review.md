# AI Employee Presence Layer Review

## Scope

This change is a frontend expression upgrade for Mission Room. It introduces no Agent, Runtime, Skill, backend endpoint, database field, or execution path. Every displayed state is derived from the existing selected Mission, timeline, activity timeline, Evidence references, Review state, and delivery object.

## What changed

### AI Employee status area

Mission Room now begins with an **AI Employee** presence surface that communicates:

- **Working on** — the real selected Mission title.
- **Current focus** — the persisted current Mission step, or an explicit absence of a current focus.
- **Next** — the existing activity timeline next action or existing worker waiting action.
- **Your next decision** — a status-aware human action derived from the real Mission status.

It never claims active work when the Mission is waiting for review, complete, or awaiting revision. A subtle pulse appears only for active Mission states and respects reduced-motion preferences.

### AI Work Journal

The primary Mission timeline is now framed as an **AI Work Journal**. For every persisted timeline entry, the UI presents:

1. What happened — the saved action and result.
2. Why it matters — whether the saved step added traceable Evidence or recorded governed progress.
3. Next action — the current persisted activity next action, or an explicit message that no next action is available.
4. When — the saved event time.

No model reasoning, hidden prompt, tool trace, or synthetic event is shown.

### Evidence experience

The Evidence panel now states that these are sources found to support the Mission. Each real reference shows the available source quality/status and a verification statement grounded in the Mission state. If no Evidence exists, the UI clearly says that the AI will not form a research conclusion.

### Review and Delivery

- Waiting Review and Revision states explicitly ask for the user’s decision and explain its impact.
- The delivery surface now clearly states **AI-prepared output** and that human approval remains required before release.

### Empty state

When no Mission is selected, Mission Room now says: **“Your AI Employee is ready.”** It guides the user to create a Mission instead of presenting a generic no-data state.

## Visual treatment

- Presence surface uses the existing premium dark SaaS language.
- Active work uses a restrained pulse; no decorative activity is simulated.
- Work Journal and Evidence areas use progressive visual hierarchy so the user can identify work, trust basis, and decision boundary quickly.
- Responsive rules stack presence cards and review controls cleanly below tablet width.

## Verification

Required frontend checks:

- `node --check frontend/app.js`
- `node --check frontend/service-worker.js`
- `git diff --check`

No backend validation is required because this is a UI-only change.
