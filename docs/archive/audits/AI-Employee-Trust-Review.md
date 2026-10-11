# AI Employee Trust Collaboration Review

## Scope

This frontend-only refinement uses existing Mission, Evidence, review, delivery, and timeline data. It does not create an API, alter a permission rule, write data, or change AI behavior.

## Trust status layer

Home and Mission Room now share one presentation mapping for a selected Mission. The layer exposes five user-facing facts:

1. **Current stage** — derived from the recorded Mission status and available Evidence references.
2. **Current focus** — the persisted current Mission step.
3. **Completed work** — a recorded work-journal entry, or an explicit statement that no work is recorded.
4. **Waiting for user** — the actual review or revision condition, when one exists.
5. **Next recommended action** — paired with a plain-language explanation of why the action matters.

No percentage progress, simulated timestamps, or invented completion states are shown in this layer.

## State interpretation

| Recorded condition | Customer-facing stage | Collaboration meaning |
| --- | --- | --- |
| Mission exists with no Evidence references | Building research foundation | The AI Employee needs traceable support before forming an insight. |
| `WAITING_REVIEW` | Waiting for human validation | A person must validate candidate Evidence before it can support insight. |
| `APPROVED` | Preparing delivery review | Reviewed work can become a traceable delivery draft, but is not released automatically. |
| `NEEDS_REVISION` | Preparing a reviewed revision | The next action is limited to the direction supplied by a reviewer. |
| `COMPLETED` | Research delivery completed | The recorded result remains available for review and reuse. |
| Other active Mission state | Research Work in progress | The AI Employee continues only inside the authorized Mission boundary. |

## Human–AI collaboration

Mission Room now shows **AI Employee needs your decision** only when the actual Mission requires review or revision. The card describes:

- work recorded as completed;
- what the AI Employee needs from a person;
- what can happen after that approval.

This makes the control boundary explicit: AI performs bounded Research Work; people validate Evidence, direct revisions, and approve consequential delivery steps.

## Decision explanation

The existing recommended-action panel now includes a **Why** explanation sourced from the same recorded state interpretation. For example, Evidence review explains that candidate sources cannot support a research insight until a human validates them. This explanation is not a model rationale and contains no prompts, hidden reasoning, technical state, or internal logs.

## Data boundary

The UI reads only existing client-side Mission records and their already-loaded context. It neither infers missing Evidence nor marks any item complete. When there is no Mission, the interface remains clear that the AI Employee is ready rather than working.
