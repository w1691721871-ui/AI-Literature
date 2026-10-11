# ResearchOS Golden Demo — FDE Final Audit

**Audit scope:** customer-facing frontend, existing Demo Workspace flow, seeded-corpus readiness checks, and the five-minute FDE walkthrough.
**Audit date:** 2026-10-09
**Product position:** AI Research Employee for enterprise research teams.

## Product score: 90 / 100

The primary product path now communicates a focused enterprise proposition: a team frames a Mission, the AI Employee performs bounded research work, Evidence stays distinct from conclusions, a person makes the important decision, and a traceable Delivery follows. The score reflects the product presentation and code path only; it is not a claim that a production deployment or a seed dataset has been verified in this checkout.

## Five-minute walkthrough

| Time | Presenter action | Customer takeaway | Live-state boundary |
| --- | --- | --- | --- |
| 00:00 | Open **Home** | ResearchOS is an AI Research Employee for research teams. | Home does not imply work has occurred before a Mission exists. |
| 00:45 | Open **Solution Demo** | A building-materials R&D team has fragmented sources and hard-to-trace decisions. | This is an explanation of the existing product path, not a generated result. |
| 01:30 | Open or create the sustainable construction materials Mission | A single goal governs the work. | The Mission is created through the normal workflow. |
| 02:30 | Open the Mission Room | The AI Employee exposes its current focus and work journal. | Journal items and status derive from recorded Mission data. |
| 03:15 | Review supporting Evidence | Sources are not treated as conclusions. | If no source is indexed, the experience explicitly pauses at the Evidence boundary. |
| 04:00 | Perform or explain Human Review | A person controls consequential decisions. | Reviewer actions remain permission-bound. |
| 04:40 | Open Deliveries | The outcome is a traceable draft, review, approval, or delivered Artifact. | A Delivery is not presented until its recorded state supports it. |

## Top ten FDE risks and dispositions

1. **Mixed Golden Demo wording** — The Home shortcut, Solution Demo, and Mission creator previously described adjacent but different low-carbon scenarios. **Fixed:** all visible Golden Demo entry points now use: `Analyze sustainable construction material strategies for low-carbon building applications.`
2. **First-screen value statement was too broad** — “Trusted decisions” did not identify the enterprise audience or concrete outcome. **Fixed:** Home now makes the audience, Evidence, human decision, and Delivery explicit in one sentence.
3. **Solution Demo lacked a visible presenter path** — A presenter had to narrate the route from memory. **Fixed:** the Demo Workspace now exposes a four-step, five-minute customer walkthrough with a live-data boundary.
4. **Risk of overstating data availability** — A polished Demo can imply an Evidence result even when corpus data is absent. **Mitigated:** the walkthrough states that ResearchOS pauses at the Evidence boundary when no indexed source is available.
5. **Cache/release ambiguity** — `release-info.json` lagged the HTML and service-worker resource version. **Fixed:** all presentation assets and release metadata are now synchronized at `v187`; runtime configuration remains intentionally network-fetched.
6. **Mission details could feel technical** — Older implementation surfaces exist in the source. **Mitigated:** the active Mission Room keeps its customer-facing hierarchy to goal, work journal, Evidence, human review, and Delivery; legacy computer/implementation panels are already hidden from that path.
7. **Demo data dependency** — Local validation previously reported that the six-paper Golden corpus had not been seeded into the active database. **Open operational risk:** seed only a dedicated Demo database/Workspace and validate the corpus before the interview; do not use a shared database.
8. **Reviewer handoff** — The Story requires a reviewer-capable session for the approval step. **Open operational risk:** prepare Owner/Researcher/Reviewer accounts and sessions before presenting.
9. **No data can look like a failure** — Empty research states can be mistaken for a broken product. **Mitigated:** active customer surfaces explain that the AI Employee is building the research foundation or waiting for a decision, without inventing results.
10. **Network availability** — the presentation depends on the deployed API for identity and live Workspace records. **Open operational risk:** verify the deployed Demo Workspace and complete one browser rehearsal immediately before the interview.

## Changes made in this audit

- Sharpened the Home promise and primary/secondary calls to action around an enterprise research outcome.
- Aligned the Golden Demo goal across the Home shortcut, Product Demo route, and live demo Mission creator.
- Added a Demo-Workspace-only presenter guide to Solution Demo. It contains no synthetic status, counts, or results.
- Added responsive styles for the guide at desktop, tablet, and mobile widths.
- Advanced the static cache and release metadata to `v187`, while preserving the existing no-store behavior for `runtime-config.js`.

## FDE presentation boundary

Present ResearchOS as a governed research-work system, not a chatbot and not an autonomous decision-maker:

`Customer goal → Mission → AI Employee work → Evidence → Human Review → Delivery`

Do not claim that a source is validated, a conclusion is reached, or a Delivery is released unless the live Workspace record shows that state.

## Required rehearsal gates

- Sign in to the dedicated Demo Workspace and confirm the Demo banner is visible.
- Confirm the six designated public sources have been seeded into the dedicated Demo database; validate PDF, chunk, embedding, and FAISS readiness with the corpus check script.
- Confirm the Golden Mission can be created, opens in Mission Room, and exposes any recorded Evidence.
- Confirm a Reviewer session can reach the appropriate Review action without receiving a permission error.
- Confirm Deliveries renders a stateful Artifact or its honest guided empty state.
- Hard-refresh once after deployment and verify frontend release `v187` to eliminate an old service-worker shell.
