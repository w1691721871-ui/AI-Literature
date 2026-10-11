# AI Research Employee First Impression Optimization

## Scope

This update is frontend-only. It does not change APIs, database records,
runtime behavior, AI Employee capabilities, or product data.

## Home Hero

The opening message now answers the first-visit questions directly:

- **What is it?** AI Research Employee.
- **Who is it for?** Enterprise research teams.
- **What does it solve?** Evidence organization, human Review, and trusted
  research Delivery.

The Mission input remains the primary action. Solution Showcase and material
upload remain secondary, so the first decision is still to describe an outcome
to achieve.

## AI Employee Identity Card

Before a first Mission exists, Home now shows a static product identity card:

- Role — research teammate;
- Capability — evidence-led research work;
- Working style — mission-focused;
- Trust boundary — humans retain consequential decisions.

These are product-positioning statements only. The card does not report a
synthetic status, progress measure, result, or learning event.

## Research Timeline

Mission Room now exposes a five-stage visual Research Timeline mapped solely
from existing Mission state:

1. Understand Goal
2. Plan Research
3. Collect Evidence
4. Human Review
5. Delivery

The timeline does not create percentage completion, fabricated activity, or
time estimates. Existing Work Journal, Evidence, Review, Delivery, and Next
Action remain the authoritative sources of user-visible work status.

## Presentation Mode

Presentation Mode maintains the existing FDE narrative:

**Customer Challenge → AI Solution → Trust Governance → Business Value →
Delivery Workflow**.

The four presentation cards now receive subtle sequence markers. They are
visual ordering only and do not imply execution progress or live results.

## Cache update

The static shell cache is now **researchos-workspace-v174**. Runtime
configuration remains excluded from cache storage.

## Verification

- `node --check frontend/app.js`
- `node --check frontend/service-worker.js`
- `git diff --check`
